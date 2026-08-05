"""Compatibility API cho key listener qua platform service mặc định."""

from utils.key_listener import (
    get_num_lock_state,
    listen_keys,
    listen_mice,
)

__all__ = ["get_num_lock_state", "listen_keys", "listen_mice"]
