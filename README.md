<p align="center">
  <img src="sag-logo.png" alt="Sigma AI Guardian banner" width="67">
</p>

# Sigma AI Guardian

**Sigma AI Guardian (SAG)** là nền tảng quản lý phòng máy tích hợp AI, lấy cảm hứng từ các phần mềm như GoGuardian nhưng tập trung vào khả năng tự động hóa chủ động.

Thay vì chỉ giám sát và chặn nội dung, SAG có thể tự phân loại nội dung, phát hiện rủi ro, cảnh báo người dùng và thực hiện các tác vụ tự động thông qua AI.

## Tính năng

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

## Cau truc input_controller

Thu muc `src/utils/input_controller/` gom cac phan chinh:

* `__init__.py`: API public, tu chon backend theo he dieu hanh.
* `controller.py`: logic chung, timing, thu tu su kien va xu ly loi.
* `contracts.py`: hop dong cho backend control va kha nang runtime.
* `mapping.py`: chuan hoa phim, nut chuot va cac bang mapping.
* `linux_backend.py` va `windows_backend.py`: adapter phat su kien thap cap cho tung he dieu hanh.
* `linux_listener.py` va `windows_listener.py`: listener ban phim da chuan hoa.
* `keys.py` va `types.py`: hang so va kieu du lieu dung chung.

Luong dung thuong la `__init__.py` goi `controller.py`, con `controller.py` lam viec voi backend qua `contracts.py` va `mapping.py`.

## Mục tiêu
* Tu dong hoa trong viec chan hanh vi khong phu hop.
* Cung cap phan mem ma nguon mo minh bach.
* Hoat dong doc lap qua LAN trong phong may.

## Yêu cầu

* Windows 10/11 hoặc Ubuntu/Debian có GNOME chạy bằng Xorg.
* Python 3.13 (khuyến nghị; tối thiểu 3.11).
* Các thư viện Python trong `requirements.txt` cùng `Pillow`, `PyWinCtl` và
  `joblib` đang được mã nguồn import trực tiếp.

## Phần mềm và binary hệ thống

### Dùng chung

* **Python, pip và venv**: chạy mã nguồn và tạo môi trường `.pyvenv` độc lập.
* **Trình duyệt**: mở URL từ xa. Không cần WebDriver; SAG dùng trình duyệt mặc
  định hoặc Chrome, Edge, Firefox, Brave, Opera, Chromium, Vivaldi, Cốc Cốc,
  Tor Browser, Yandex hay Waterfox nếu binary tương ứng có trong `PATH`.

### Windows 10/11

* **`tasklist` và `taskkill`**: liệt kê và kết thúc process; có sẵn trong
  Windows.
* **Win32 `user32.dll`**: chặn bàn phím và chuột; có sẵn trong Windows.
* **Microsoft Edge**: trình duyệt mặc định thường có sẵn. Có thể thay bằng một
  trình duyệt được SAG hỗ trợ.

### Ubuntu/Debian GNOME

* **GNOME, GDM và Xorg**: cung cấp phiên desktop đồ họa cho khóa/chụp màn hình,
  clipboard và theo dõi cửa sổ. Hãy chọn phiên **GNOME on Xorg** tại màn hình
  đăng nhập; `xdotool`, `xclip` và backend theo dõi cửa sổ hiện chưa hỗ trợ đầy
  đủ phiên Wayland.
* **`xdotool`**: đọc cửa sổ active và danh sách cửa sổ đang mở.
* **`procps` (`ps`)**: liệt kê process.
* **`xclip`**: backend clipboard X11 cho `pyperclip`.
* **Tk, X11/XCB và `gnome-screenshot`**: hiển thị khóa màn hình và hỗ trợ chụp
  màn hình.
* **`evdev`, kernel `uinput` và các device `/dev/input/event*`, `/dev/uinput`**:
  nghe, chặn và giả lập input.
* **`build-essential`, header Python và Linux**: biên dịch `evdev` nếu pip không
  có wheel phù hợp.

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
.\.pyvenv\Scripts\python.exe -m pip install Pillow PyWinCtl joblib
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
sửa file `C:\Windows\System32\drivers\etc\hosts`. Các tính năng còn lại không
cần quyền Administrator.

### Ubuntu minimal

```bash
sudo apt update
sudo apt install -y \
  ubuntu-desktop-minimal gdm3 xorg gnome-session-xsession \
  python3 python3-venv python3-pip python3-tk python3-dev \
  build-essential linux-libc-dev procps xdotool xclip gnome-screenshot \
  libx11-6 libxfixes3 libxrandr2 \
  libxcb1 libxcb-randr0 libxcb-render0 libxcb-shm0 libxcb-xfixes0 \
  firefox
sudo systemctl enable --now gdm3
```

### Debian minimal

```bash
sudo apt update
sudo apt install -y \
  gnome-core gdm3 xorg gnome-session-xsession \
  python3 python3-venv python3-pip python3-tk python3-dev \
  build-essential linux-libc-dev procps xdotool xclip gnome-screenshot \
  libx11-6 libxfixes3 libxrandr2 \
  libxcb1 libxcb-randr0 libxcb-render0 libxcb-shm0 libxcb-xfixes0 \
  firefox-esr
sudo systemctl enable --now gdm3
```

Sau khi GNOME khởi động, đăng nhập bằng phiên **GNOME on Xorg**. Trên cả Ubuntu
và Debian, tạo môi trường Python từ thư mục gốc của dự án:

```bash
python3 -m venv .pyvenv
./.pyvenv/bin/python -m pip install --upgrade pip
./.pyvenv/bin/python -m pip install -r requirements.txt
./.pyvenv/bin/python -m pip install Pillow PyWinCtl joblib
```

#### Cấp quyền input trên Linux

Nạp `uinput`, tự động nạp module này lúc boot và cấp quyền device cho nhóm
`input`:

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

Dự án chưa có entry point hoàn chỉnh. Có thể kiểm tra classifier hiện có bằng:

```bash
./.pyvenv/bin/python tests/content_classifier/test_all_classifiers.py --help
```

Trên Windows, thay `./.pyvenv/bin/python` bằng
`.\.pyvenv\Scripts\python.exe`.

## Credits
