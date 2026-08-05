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


## Bo sung: feature co the chay doc lap

Feature co hai cach nhan platform operations:

```python
# Cach 1: runtime hoac caller truyen services ro rang
open_tab(url, platform_services=runtime.services)

# Cach 2: feature tu lay services mac dinh cua process
open_tab(url)
```

`get_default_platform_services()` la compatibility entry point cho cach thu hai.
Ham nay lazy-create mot `PlatformServices` theo OS hien tai va cache lai trong
process. Nhung lan goi sau se dung lai cung object services do.

```text
feature khong duoc truyen services
    |
    v
get_default_platform_services()
    |
    v
PlatformServices cua OS hien tai
    |
    v
Linux adapter hoac Windows adapter
```

Muc dich cua ham nay la de feature van co the duoc goi doc lap tu CLI, test nho hoac
caller cu ma khong bat buoc moi caller phai tu tao `AgentRuntime`. Ham nay khong chua
logic feature va khong thay the `AgentRuntime` trong luong chay chinh cua Agent.

Khi co `AgentRuntime`, uu tien truyen `runtime.services` vao feature. Cach nay lam
dependency hien ro, dung dung adapter da duoc runtime tao va de test bang fake de hon.
`get_default_platform_services()` chu yeu danh cho compatibility va feature API can
tu chay khong qua runtime.


## Cach tu build mot feature theo kien truc hien tai

Vi du nen doc: `browser_tab`.

Doc theo thu tu:

1. `src/device_controller/browser_tab/__init__.py`
2. `src/agent/contracts.py`
3. `src/agent/platform/__init__.py`
4. `src/agent/platform/linux/browser.py`
5. `src/agent/platform/windows/browser.py`
6. `src/agent/runtime.py`

Luon doc feature chung truoc, sau do doc contract, object gom services, adapter tung
OS va cuoi cung la runtime tao dependency nhu the nao.

Luong cua `browser_tab`:

```text
browser_tab.open_tab(url, platform_services)
    |
    +-- logic chung: validate URL, chon browser, fallback
    |
    +-- platform_services.processes
    |
    `-- platform_services.browser
             |
             +-- Linux browser adapter
             `-- Windows browser adapter
```

`browser_tab` khong can biet dang chay tren Linux hay Windows. No chi biet cac
operation trong `ProcessOperations` va `BrowserOperations`. Phan khac nhau giua cac OS
nam trong `src/agent/platform/linux/browser.py` va
`src/agent/platform/windows/browser.py`.

Khi tu them feature moi, co the dung checklist sau:

1. Viet logic chung cua feature trong package feature.
2. Xac dinh operation ma feature can trong `src/agent/contracts.py`.
3. Them operation vao `PlatformServices` neu day la capability cua OS.
4. Tao adapter cho Linux va Windows trong package platform tuong ung.
5. Cho feature nhan `PlatformServices` tu caller; fallback default chi dung khi can
   compatibility.
6. Doc `runtime.py` de dam bao runtime tao services mot lan va owner lifecycle ro rang.
7. Test feature bang fake operation, khong goi OS that trong safe test.

## Cach de tu build mot service moi
1. Dau tien, viet contract trong contracts.py qui dinh input, output, apis, cua service do
2. viet adapter rieng cho tung os trong linux/ & window/
3. Bo xung service moi vo create_serivce() cua linux/__init__ & window/__init__
