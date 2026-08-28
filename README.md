# TV Automation

Source Python được khôi phục từ ứng dụng TV Automation. Ứng dụng sử dụng
[NiceGUI](https://nicegui.io/) và chạy web UI cục bộ tại cổng `8081`.

## Yêu cầu hệ thống

- Windows 10/11 64-bit.
- Python 3.12 64-bit bản đầy đủ.
- Python phải có `venv` và `tkinter`; không dùng bản embeddable.
- Google Chrome cho các chức năng Selenium.
- FFmpeg và FFprobe cho các chức năng xử lý media.
- Kết nối mạng cho các chức năng truy cập dịch vụ ngoài hoặc tải ChromeDriver.

Kiểm tra Python và Tkinter:

```powershell
py -3.12 --version
py -3.12 -c "import tkinter; print(tkinter.TkVersion)"
```

## Cài đặt

Clone repository:

```powershell
git clone https://github.com/duykhanh8386/tool_vippro.git
cd tool_vippro
```

Tạo và kích hoạt virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Nếu PowerShell chặn activation script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Cài dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
```

## FFmpeg và FFprobe

Đảm bảo hai công cụ resolve được trong `PATH`:

```powershell
ffmpeg -version
ffprobe -version
```

Nếu cài FFmpeg thủ công, thêm thư mục `bin` vào `PATH`. Ví dụ cho terminal
hiện tại:

```powershell
$env:PATH = "C:\path\to\ffmpeg\bin;" + $env:PATH
```

## Chạy ứng dụng

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

Sau khi server khởi động, mở:

```text
http://127.0.0.1:8081
```

Dừng server bằng `Ctrl+C`. Không chạy nhiều instance cùng lúc vì ứng dụng sử
dụng cố định cổng `8081`.

Kiểm tra cổng trước khi chạy:

```powershell
Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue
```

## Chrome và ChromeDriver

Ứng dụng cần Google Chrome cho các luồng Selenium. `webdriver-manager` tìm
ChromeDriver trong cache hoặc tải driver khi chức năng tương ứng được gọi. Lần
chạy đầu có thể cần mạng và quyền ghi vào cache người dùng.

Chrome không được mở chỉ bằng thao tác cài dependencies; nó chỉ được sử dụng
khi người dùng gọi chức năng cần Selenium.

## Dữ liệu runtime

Ứng dụng có thể tạo dữ liệu dưới:

```text
%APPDATA%\TVAutomation\
```

Các dữ liệu này có thể gồm database kênh, application state, thông tin kích
hoạt và dữ liệu phiên làm việc. Media đầu vào, overlay, output và CSV log do
người dùng chọn hoặc được tạo khi chạy. Không commit chúng lên Git.

## Kiểm tra source nhanh

Compile source mà không khởi động ứng dụng:

```powershell
python -m compileall -q app.py src web
```

Kiểm tra dependencies:

```powershell
python -m pip check
```

## Lưu ý

- `VERSION` là resource runtime cần thiết cho updater.
- Không commit `.venv`, database, log, cookies, license state hoặc thông tin
  đăng nhập.
- Upload, xóa video và chỉnh sửa audio có thể tác động dữ liệu thật. Nên thử
  bằng tài khoản/kênh test và sao lưu trước.
- Không đưa launcher test hoặc mock authentication vào bản phát hành.
