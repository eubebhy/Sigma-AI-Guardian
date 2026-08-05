"""Quản lý policy web block bền vững của một SAG Agent.

File path: `src/device_controler/web_blocker/manager.py`.
Input: category đóng gói, custom block/allow domain và path state JSON.
Output: `WebBlockResult` và `WebBlockPolicy` immutable cho caller Agent.
Nguyên lý: category được stream thẳng vào marker hosts một lần; state chỉ lưu policy
nhỏ nên custom allow/block tra cứu bằng set, không nạp category list vào RAM.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import ContextManager, cast

from device_controler import web_blocker


@dataclass(frozen=True)
class WebBlockPolicy:
    """Policy runtime hiện tại của một Agent."""

    blocked_categories: frozenset[str]
    custom_blocked_domains: frozenset[str]
    custom_allowed_domains: frozenset[str]


@dataclass(frozen=True)
class WebBlockStatus:
    """Trạng thái web policy dành cho Agent, Service và UI giáo viên."""

    blocked_categories: frozenset[str]
    blocked_domains: frozenset[str]
    allowed_domains: frozenset[str]


@dataclass(frozen=True)
class WebBlockResult:
    """Kết quả thay đổi hosts của một action web block."""

    changed: bool
    blocked_domains: int = 0
    unblocked_domains: int = 0
    skipped_domains: int = 0


class WebBlocker:
    """Áp dụng category và custom policy vào các marker hosts riêng của SAG."""

    def __init__(
        self,
        hosts_path: Path | None = None,
        state_path: Path | None = None,
        category_paths: Mapping[str, Path] | None = None,
    ) -> None:
        self._hosts_path = hosts_path or Path(web_blocker.DEFAULT_HOSTS_PATH)
        self._state_path = state_path or (
            Path(__file__).resolve().parents[3] / "data/webblocker/policy.json"
        )
        self._category_paths = dict(category_paths or web_blocker.CATEGORY_PATHS)
        self._policy = self._load_policy()
        self._is_reconciled = False

    def get_status(self) -> WebBlockStatus:
        """Trả trạng thái policy hiện tại để UI hiển thị."""

        with self._policy_lock():
            self._policy = self._load_policy()
            return WebBlockStatus(
                blocked_categories=self._policy.blocked_categories,
                blocked_domains=self._policy.custom_blocked_domains,
                allowed_domains=self._policy.custom_allowed_domains,
            )

    def block_category(self, category: str) -> WebBlockResult:
        """Block category vào marker riêng nếu category chưa active."""

        return self._run_locked(lambda: self._block_category(category))

    def _block_category(self, category: str) -> WebBlockResult:
        path = self._category_path(category)
        if category in self._policy.blocked_categories:
            if web_blocker.marker_exists(self._hosts_path, self._category_marker(category)):
                return WebBlockResult(changed=False)
            count = web_blocker.block_file(
                path,
                self._category_marker(category),
                self._policy.custom_allowed_domains,
                self._hosts_path,
            )
            return WebBlockResult(changed=True, blocked_domains=count)
        policy = self._new_policy(
            blocked_categories=self._policy.blocked_categories | {category},
        )
        count = self._update_policy(
            policy,
            lambda: web_blocker.block_file(
                path,
                self._category_marker(category),
                self._policy.custom_allowed_domains,
                self._hosts_path,
            ),
        )
        return WebBlockResult(changed=True, blocked_domains=count)

    def unblock_category(self, category: str) -> WebBlockResult:
        """Gỡ nguyên marker category mà không duyệt source list."""

        return self._run_locked(lambda: self._unblock_category(category))

    def _unblock_category(self, category: str) -> WebBlockResult:
        self._category_path(category)
        if category not in self._policy.blocked_categories:
            return WebBlockResult(changed=False)
        policy = self._new_policy(
            blocked_categories=self._policy.blocked_categories - {category},
        )
        count = self._update_policy(
            policy,
            lambda: web_blocker.unblock(self._category_marker(category), self._hosts_path),
        )
        return WebBlockResult(changed=True, unblocked_domains=count)

    def block_domain(self, domain: str) -> WebBlockResult:
        """Thêm một website do giáo viên chọn vào custom block list."""

        return self._run_locked(lambda: self._block_domains((domain,)))

    def _block_domains(self, domains: Iterable[str]) -> WebBlockResult:
        normalized = self._normalize_domains(domains)
        blocked = self._policy.custom_blocked_domains
        allowed = self._policy.custom_allowed_domains
        additions = normalized - blocked - allowed
        if not additions:
            if blocked and not web_blocker.marker_exists(self._hosts_path, "custom:block"):
                web_blocker.replace_marker(
                    self._hosts_path,
                    "custom:block",
                    sorted(blocked),
                )
                return WebBlockResult(changed=True, blocked_domains=len(blocked))
            return WebBlockResult(changed=False, skipped_domains=len(normalized))
        new_blocked = blocked | additions
        policy = self._new_policy(custom_blocked_domains=new_blocked)
        self._update_policy(
            policy,
            lambda: web_blocker.replace_marker(
                self._hosts_path,
                "custom:block",
                sorted(new_blocked),
            ),
        )
        return WebBlockResult(
            changed=True,
            blocked_domains=len(additions),
            skipped_domains=len(normalized) - len(additions),
        )

    def allow_domain(self, domain: str) -> WebBlockResult:
        """Cho phép một website, kể cả khi category đang block website đó."""

        return self._run_locked(lambda: self._allow_domains((domain,)))

    def _allow_domains(self, domains: Iterable[str]) -> WebBlockResult:
        normalized = self._normalize_domains(domains)
        additions = normalized - self._policy.custom_allowed_domains
        new_allowed = self._policy.custom_allowed_domains | additions
        new_blocked = self._policy.custom_blocked_domains - additions
        policy = self._new_policy(
            custom_allowed_domains=new_allowed,
            custom_blocked_domains=new_blocked,
        )
        count = self._update_policy(
            policy,
            lambda: web_blocker.remove_domains(self._hosts_path, additions),
        )
        return WebBlockResult(
            changed=bool(additions or count),
            unblocked_domains=count,
            skipped_domains=len(normalized) - len(additions),
        )

    def remove_allowed_domain(self, domain: str) -> WebBlockResult:
        """Gỡ website khỏi custom allow list mà không tự block lại."""

        return self._run_locked(lambda: self._remove_allowed_domains((domain,)))

    def _remove_allowed_domains(self, domains: Iterable[str]) -> WebBlockResult:
        normalized = self._normalize_domains(domains)
        removals = normalized & self._policy.custom_allowed_domains
        if not removals:
            return WebBlockResult(changed=False, skipped_domains=len(normalized))
        policy = self._new_policy(
            custom_allowed_domains=self._policy.custom_allowed_domains - removals,
        )
        self._update_policy(policy, lambda: 0)
        return WebBlockResult(changed=True, skipped_domains=len(normalized) - len(removals))

    def clear_all(self) -> WebBlockResult:
        """Gỡ toàn bộ website SAG block và xóa custom policy."""

        return self._run_locked(self._reset)

    def _reset(self) -> WebBlockResult:
        empty_policy = WebBlockPolicy(frozenset(), frozenset(), frozenset())
        had_policy = self._policy != empty_policy
        count = self._update_policy(
            empty_policy,
            lambda: web_blocker.remove_all_markers(self._hosts_path),
        )
        return WebBlockResult(changed=had_policy or bool(count), unblocked_domains=count)

    def _reconcile(self) -> WebBlockResult:
        blocked_count = 0
        unblocked_count = 0
        expected_markers = {
            self._category_marker(category)
            for category in self._policy.blocked_categories
        }
        if self._policy.custom_blocked_domains:
            expected_markers.add("custom:block")
        current_markers = web_blocker.marker_names(self._hosts_path)
        for marker in current_markers - expected_markers:
            unblocked_count += web_blocker.unblock(marker, self._hosts_path)
        for category in sorted(self._policy.blocked_categories):
            marker = self._category_marker(category)
            if marker in current_markers:
                continue
            blocked_count += web_blocker.block_file(
                self._category_path(category),
                marker,
                self._policy.custom_allowed_domains,
                self._hosts_path,
            )
        if self._policy.custom_blocked_domains and "custom:block" not in current_markers:
            web_blocker.replace_marker(
                self._hosts_path,
                "custom:block",
                sorted(self._policy.custom_blocked_domains),
            )
            blocked_count += len(self._policy.custom_blocked_domains)
        if self._policy.custom_allowed_domains:
            unblocked_count = web_blocker.remove_domains(
                self._hosts_path,
                self._policy.custom_allowed_domains,
            )
        return WebBlockResult(
            changed=bool(blocked_count or unblocked_count),
            blocked_domains=blocked_count,
            unblocked_domains=unblocked_count,
        )

    def _category_path(self, category: str) -> Path:
        path = self._category_paths.get(category)
        if path is None:
            raise ValueError(f"Unsupported web block category: {category}")
        return path

    def _new_policy(
        self,
        blocked_categories: frozenset[str] | None = None,
        custom_blocked_domains: frozenset[str] | None = None,
        custom_allowed_domains: frozenset[str] | None = None,
    ) -> WebBlockPolicy:
        return WebBlockPolicy(
            blocked_categories=(
                self._policy.blocked_categories
                if blocked_categories is None
                else blocked_categories
            ),
            custom_blocked_domains=(
                self._policy.custom_blocked_domains
                if custom_blocked_domains is None
                else custom_blocked_domains
            ),
            custom_allowed_domains=(
                self._policy.custom_allowed_domains
                if custom_allowed_domains is None
                else custom_allowed_domains
            ),
        )
    def _run_locked(self, action: Callable[[], WebBlockResult]) -> WebBlockResult:
        with self._policy_lock():
            self._policy = self._load_policy()
            recovered = WebBlockResult(changed=False)
            if not self._is_reconciled:
                recovered = self._reconcile()
                self._is_reconciled = True
            result = action()
            return WebBlockResult(
                changed=recovered.changed or result.changed,
                blocked_domains=(
                    recovered.blocked_domains + result.blocked_domains
                ),
                unblocked_domains=(
                    recovered.unblocked_domains + result.unblocked_domains
                ),
                skipped_domains=result.skipped_domains,
            )

    def _update_policy(
        self,
        policy: WebBlockPolicy,
        hosts_action: Callable[[], int],
    ) -> int:
        previous_policy = self._policy
        self._save_policy(policy)
        self._policy = policy
        try:
            return hosts_action()
        except Exception:
            self._save_policy(previous_policy)
            self._policy = previous_policy
            raise

    def _policy_lock(self) -> ContextManager[None]:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        return web_blocker.file_lock(self._state_path)

    def _load_policy(self) -> WebBlockPolicy:
        if not self._state_path.exists():
            return WebBlockPolicy(frozenset(), frozenset(), frozenset())
        try:
            payload = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Cannot read web block policy: {error}") from error
        if not isinstance(payload, dict):
            raise ValueError("Web block policy must be a JSON object")
        typed_payload = cast(dict[str, object], payload)
        categories = self._read_domain_set(typed_payload, "blocked_categories")
        unsupported = categories - self._category_paths.keys()
        if unsupported:
            raise ValueError(f"Unsupported web block policy categories: {sorted(unsupported)}")
        return WebBlockPolicy(
            blocked_categories=categories,
            custom_blocked_domains=self._read_domain_set(
                typed_payload,
                "custom_blocked_domains",
            ),
            custom_allowed_domains=self._read_domain_set(
                typed_payload,
                "custom_allowed_domains",
            ),
        )

    def _save_policy(self, policy: WebBlockPolicy) -> None:
        payload = {
            "blocked_categories": sorted(policy.blocked_categories),
            "custom_blocked_domains": sorted(policy.custom_blocked_domains),
            "custom_allowed_domains": sorted(policy.custom_allowed_domains),
        }
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self._state_path.parent,
            prefix=f".{self._state_path.name}.",
            delete=False,
        ) as file:
            json.dump(payload, file, sort_keys=True)
            temp_path = Path(file.name)
        try:
            temp_path.replace(self._state_path)
        finally:
            temp_path.unlink(missing_ok=True)

    @staticmethod
    def _normalize_domains(domains: Iterable[str]) -> frozenset[str]:
        return frozenset(
            domain
            for value in domains
            if (domain := web_blocker.normalize_domain(value)) is not None
        )

    @staticmethod
    def _read_domain_set(payload: dict[str, object], key: str) -> frozenset[str]:
        values = payload.get(key, [])
        if not isinstance(values, list):
            raise ValueError(f"Invalid web block policy value: {key}")
        typed_values = cast(list[object], values)
        if not all(isinstance(value, str) for value in typed_values):
            raise ValueError(f"Invalid web block policy value: {key}")
        return WebBlocker._normalize_domains(cast(list[str], typed_values))

    @staticmethod
    def _category_marker(category: str) -> str:
        return f"category:{category}"
