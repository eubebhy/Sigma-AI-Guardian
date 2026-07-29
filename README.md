<p align="center">
  <img src="sag-logo.png" alt="Sigma AI Guardian banner" width="67">
</p>

# Sigma AI Guardian

**Sigma AI Guardian (SAG)** là nền tảng quản lý phòng máy tích hợp AI, lấy cảm hứng từ các phần mềm như GoGuardian nhưng tập trung vào khả năng tự động hóa chủ động.

Thay vì chỉ giám sát và chặn nội dung, SAG có thể tự phân loại nội dung, phát hiện rủi ro, cảnh báo người dùng và thực hiện các tác vụ tự động thông qua AI.

## Tầm nhìn sản phẩm

Các chức năng sau là định hướng của Sigma AI Guardian hoàn chỉnh; chúng chưa phải
capability của repository SAG Agent hiện tại.

- Tu dong phat hien va chặn các noi dung khong phu hop voi AI (porn, gore, game)
- Chan cac web site theo chu de va ho tro custom
- Chan cac chuong trinh nhu cmd, task manager, regedit,v.v
- Mo trang web tu xa
- Dieu khien va xem mang hinh tu xa tuong tu nhu anydesk
- Khoa mang hinh, ban phim, chuot.
- Goi lenh shell tu xa.

## Kiến trúc

* **Rule-based Engine**: phát hiện nhanh bằng từ khóa và luật.
* **Local AI Classifier**: mô hình học máy chạy hoàn toàn trên máy người dùng.

## SAG Agent hiện tại

Repository hiện là SAG Agent chạy cục bộ trên máy học sinh. Entry point là
`src/main.py`; hiện chỉ có command an toàn `status` để kiểm tra runtime:

```bash
./.pyvenv/bin/python src/main.py status
```

Agent chọn Windows hoặc Linux một lần khi khởi động, sau đó feature dùng adapter
platform chung. Server, Teacher Console, mạng LAN và remote desktop streaming chưa
thuộc repository hiện tại. Xem [tài liệu kiến trúc](docs/architecture.md).

## Cau truc input

Input duoc tach theo trach nhiem:

* `src/device_controler/input_controller/`: gui input va lifecycle virtual device.
* `src/utils/key_listener/`: lang nghe event va doc NumLock.

Chi tiet API, dieu kien platform va gioi han co tai
[`src/device_controler/input_controller/README.md`](src/device_controler/input_controller/README.md)
va [`src/utils/key_listener/README.md`](src/utils/key_listener/README.md).

## Tai lieu bao tri

Bao cao kien truc, rui ro, test strategy, ADR va backlog bao tri nam tai
[`ROI-reports/index.md`](ROI-reports/index.md). Tai lieu nay phan biet capability
hien tai cua SAG Agent voi dinh huong san pham trong tuong lai.

## Mục tiêu
* Tu dong hoa trong viec chan hanh vi khong phu hop.
* Cung cap phan mem ma nguon mo minh bach.
* Hoat dong doc lap qua LAN trong phong may sau khi co Server va transport; chua la
  capability cua SAG Agent hien tai.

## Yêu cầu

* Windows 10/11 hoặc Linux có desktop X11/Xorg. Linux input và window backend hiện
  chưa hỗ trợ đầy đủ Wayland.
* Python 3.13 (khuyến nghị; tối thiểu 3.11).
* Các thư viện Python runtime trong `requirements.txt`.

## Phần mềm và binary hệ thống

### Dùng chung

* **Python, pip và venv**: chạy mã nguồn và tạo môi trường `.pyvenv` độc lập.
* **Trình duyệt**: mở URL cục bộ trên máy đang chạy Agent. Không cần WebDriver; SAG dùng trình duyệt mặc
  định hoặc Chrome, Edge, Firefox, Brave, Opera, Chromium, Vivaldi, Cốc Cốc,
  Tor Browser, Yandex hay Waterfox nếu binary tương ứng có trong `PATH`.

### Windows 10/11

* **`tasklist` và `taskkill`**: liệt kê và kết thúc process; có sẵn trong
  Windows.
* **Win32 `user32.dll`**: chặn bàn phím và chuột; có sẵn trong Windows.
* **Microsoft Edge**: trình duyệt mặc định thường có sẵn. Có thể thay bằng một
  trình duyệt được SAG hỗ trợ.

### Linux desktop X11/Xorg

* **Desktop X11/Xorg**: cung cấp phiên desktop đồ họa cho khóa/chụp màn hình,
  clipboard và theo dõi cửa sổ. GNOME on Xorg là cấu hình đã được tài liệu hóa;
  `xdotool`, `xclip` và backend theo dõi cửa sổ hiện chưa hỗ trợ đầy đủ Wayland.
* **`xdotool`**: đọc cửa sổ active và danh sách cửa sổ đang mở.
* **`procps` (`ps`)**: liệt kê process.
* **`xclip`**: backend clipboard X11 cho `pyperclip`.
* **Tk và X11/XCB**: hiển thị khóa màn hình và hỗ trợ chụp màn hình.
* **`evdev`, kernel `uinput` và các device `/dev/input/event*`, `/dev/uinput`**:
  nghe, chặn và giả lập input.
* **Compiler C, header Python và Linux**: biên dịch `evdev` nếu pip không có wheel
  phù hợp.

### Công cụ chỉ dùng khi phát triển

* **Bash, Pyright và `jq`**: `scripts/clean_pyright_check.sh` dùng Bash để chạy
  Pyright strict mode rồi dùng `jq` rút gọn kết quả JSON. Chúng không cần thiết
  khi chỉ chạy tính năng của SAG.

## Cài đặt

Tải mã nguồn về máy, mở terminal tại thư mục gốc của dự án rồi làm theo hệ điều
hành tương ứng.

### Windows 10/11

Mở PowerShell và cài Python:

```powershell
winget install --exact --id Python.Python.3.13 --accept-package-agreements --accept-source-agreements
```

Mở lại PowerShell để cập nhật `PATH`, sau đó tạo môi trường và cài thư viện:

```powershell
py -3.13 -m venv .pyvenv
.\.pyvenv\Scripts\python.exe -m pip install --upgrade pip
.\.pyvenv\Scripts\python.exe -m pip install -r requirements.txt
```

Nếu máy không có trình duyệt, cài Edge:

```powershell
winget install --exact --id Microsoft.Edge --accept-package-agreements --accept-source-agreements
```

Nếu cần chạy script kiểm tra dành cho lập trình viên, cài Git Bash, Node.js,
Pyright và `jq`:

```powershell
winget install --exact --id Git.Git
winget install --exact --id OpenJS.NodeJS.LTS
winget install --exact --id jqlang.jq
npm install --global pyright
```

Chạy PowerShell bằng **Run as administrator** khi dùng tính năng chặn input hoặc
sửa file `C:\Windows\System32\drivers\etc\hosts`. `taskkill` cũng có thể bị từ
chối quyền khi process thuộc user hoặc privilege cao hơn. `ProcessKiller` lưu lỗi
scan/kill nền và caller gọi `raise_if_failed()` để nhận exception; nó vẫn không có
per-process result/history, nên xem backlog trong
[`ROI-reports/technical-debt.md`](ROI-reports/technical-debt.md) trước khi dùng
process guard như enforcement đáng tin cậy.

### Cài Python environment trên Linux

Trên distribution Linux bất kỳ, cài Python, `venv`, `pip`, Tk, Xorg, `ps`,
`xdotool`, `xinput`, `xclip`, compiler C và header Python/Linux bằng package manager
của distribution. Tên package và display manager khác nhau theo distribution; không
giả định `apt`, `systemctl`, GNOME hay GDM là chuẩn POSIX.

Ví dụ package cho Ubuntu:

```bash
sudo apt update
sudo apt install -y \
  ubuntu-desktop-minimal gdm3 xorg gnome-session-xsession \
  python3 python3-venv python3-pip python3-tk python3-dev \
   build-essential linux-libc-dev procps xdotool xinput xclip \
  libx11-6 libxfixes3 libxrandr2 \
  libxcb1 libxcb-randr0 libxcb-render0 libxcb-shm0 libxcb-xfixes0 \
  firefox
```

Khởi động desktop/display manager bằng init system của distribution, đăng nhập vào
phiên Xorg, rồi tạo môi trường Python từ thư mục gốc dự án:

```bash
python3 -m venv .pyvenv
./.pyvenv/bin/python -m pip install --upgrade pip
./.pyvenv/bin/python -m pip install -r requirements.txt
```

#### Cấp quyền input trên Linux

Nạp `uinput`, tự động nạp module này lúc boot và cấp quyền device cho nhóm `input`.
Các lệnh dưới đây dành cho Linux dùng systemd và udev; distribution dùng OpenRC hoặc
udev khác phải áp dụng quy tắc tương đương theo tài liệu của distribution:

```bash
sudo modprobe uinput
printf '%s\n' uinput | sudo tee /etc/modules-load.d/sag-uinput.conf
sudo groupadd --force input
sudo usermod -aG input "$USER"
printf '%s\n' \
  'KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"' \
  'SUBSYSTEM=="input", KERNEL=="event*", GROUP="input", MODE="0660"' \
  | sudo tee /etc/udev/rules.d/99-sag-input.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Đăng xuất hoàn toàn rồi đăng nhập lại để nhận group mới. Kiểm tra bằng:

```bash
id
ls -l /dev/uinput /dev/input/event*
```

Không chạy toàn bộ ứng dụng đồ họa bằng `sudo`. Riêng tính năng web blocker vẫn
cần quyền ghi `/etc/hosts`.

Nếu cần chạy script kiểm tra dành cho lập trình viên:

```bash
sudo apt install -y jq nodejs npm
sudo npm install --global pyright
```

### Kiểm tra môi trường

Entry point hiện tại của SAG Agent chỉ hỗ trợ command an toàn `status`:

```bash
./.pyvenv/bin/python src/main.py status
```

Có thể kiểm tra classifier hiện có bằng:

```bash
./.pyvenv/bin/python tests/test_classifier.py --info
```

Trên Windows, thay `./.pyvenv/bin/python` bằng
`.\.pyvenv\Scripts\python.exe`.

## Credits
