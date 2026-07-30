# Cach src/agent hoat dong
Luu y: tai lieu nay duoc viet o thoi diem **hien tai** cua code.
Tai lieu nay co the tro nen loi thoi ve mat vi du trong tuong lai.

Tai lieu giai thich theo huong "tracback" cach hoat dong tu main.py


khi src/main.py duoc chay, no se tao object agent runtime va goi cac api tu object
do:

```python
# src/main.py
from agent.runtime import create_runtime

def main(argv: Sequence[str] | None = None) -> int:
    """Chạy command Agent an toàn hiện có."""

    arguments = _build_parser().parse_args(argv) # su ly args
    runtime = create_runtime() # tao object agent runtime
    try:
        if arguments.command == "status":
            print(runtime.status()) # goi api on dinh
            return 0
        return 1
    finally:
        runtime.shutdown()
```

ham create runtime chiu trach nhiem tao object agent runtime on dinh theo platform
hien tai.

```python
# src/agent/runtime.py
from agent.platform import PlatformServices, create_platform_services

"""
Khong nen de AgentRuntime tu su ly PlatformServices va dependencies cho cac tinh nang.
Muc dinh la de de test, dependencies dong se de test hon.
"""


@dataclass
class AgentRuntime:
    """Obj Agent su dung trong runtime, cung cap cac main API on dinh khong phan biet
    platform dang chay la gi.

    vi du: Agent.status()

    services: PlatformServices la obj cung cap adapter operations the feature su
    dung, no khong cung cap truc tiep logic cua feature.
    Time hieu them: src/agent/platform/__init__.py
    """

    services: PlatformServices

    def status(self) -> str:
        """Trả capability status của Agent mà không đụng desktop thật."""

        return self.services.capabilities.format_status()

    def shutdown(self) -> None:
        """Kết thúc runtime; feature hiện có tự quản lý lifecycle của chúng."""


def create_runtime(platform_name: str | None = None) -> AgentRuntime:
    """Tạo runtime Agent với adapter platform được chọn một lần."""
    return AgentRuntime(services=create_platform_services(platform_name))
```

Trong doan code tren de su dung ham create_platform_services tu module src/agent/platform
ham nay chiu trach nhiem cung cap cac operations chung cho cac he dieu hanh.
khi chay, dua vao moi truong, no se tao ra adapter cung cap cac operations chung cho
cac feature se duoc su dung. Nhung KHONG chua logic cu the cua feature.

vi du:

```python
def kill_process(name: str)
    name = PlatformServices_obj.find_process(name)
    pid = PlatformServices_obj.get_pid(name)
    PlatformServices_obj.kill_process(pid)
```

kill_process khong biet:
linux hay window?
dung pkill hay taskkill?

vi vay:
  PlatformServices = apdater operations theo platform
  cac feature chi la tap hop cac logic goi PlatformServices
  Agent thi lai goi feature, quan ly lifecycle.
