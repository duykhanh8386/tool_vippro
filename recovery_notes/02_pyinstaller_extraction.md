# 02 — Extract PyInstaller archive

## Phạm vi an toàn

- Chỉ chạy `pyinstxtractor-ng` như một parser/extractor dữ liệu.
- Không chạy `TV Automation.exe`, `TVAutomation_Setup.exe`, `Uninstall.exe`, DLL/PYD hay Wine.
- Input: `recovery_staging/installer_payload/TV Automation.exe`.
- Output cuối cùng: `work/extracted/`.

## Công cụ

`pyinstxtractor-ng` không có sẵn trong môi trường. Đã cài cục bộ vào workspace:

- `pyinstxtractor-ng 2026.7.3`
- `xdis 6.3.0`
- `pycryptodome 3.17`
- Tool root: `work/tools/pyinstxtractor_ng/`

Kết quả `--help` của phiên bản này:

```text
usage: pyinstxtractor_ng.py [-h] [-d] [-i] filename

positional arguments:
  filename       Path to the file to extract

options:
  -h, --help     show this help message and exit
  -d, --one-dir  One directory mode, extracts the pyz in the same directory as
                 the executable
  -i, --info     Shows archive information only without extracting
```

## Kết quả `--info`

```text
PyInstaller generation: 2.1+
Python version: 3.12
Length of package: 17,090,499 bytes
CArchive files: 15
PYZ archive present: Yes
Encrypted: No
Packages: 0
Python scripts: 8
Total compressed size: 17,089,723 bytes
Total uncompressed size: 17,119,157 bytes
```

Entry points được tool báo cáo:

- `pyiboot01_bootstrap`
- `pyi_rth_inspect`
- `pyi_rth_pkgutil`
- `pyi_rth_multiprocessing`
- `pyi_rth_setuptools`
- `pyi_rth_traitlets`
- `pyi_rth__tkinter`
- `app` — entry script của ứng dụng

Ghi chú: chuỗi `PyInstaller generation: 2.1+` là tên format cookie/archive mà tool sử dụng, không phủ định kết luận phiên bản bootloader `>= 6.10` ở bước 1.

## Extraction

Extraction hoàn tất với exit code `0`:

```text
Found 15 files in CArchive
Found 2894 files in PYZ archive
Successfully extracted pyinstaller archive
```

Tool mặc định tạo `work/TV Automation.exe_extracted/`; thư mục này đã được đổi tên nguyên vẹn thành `work/extracted/` theo yêu cầu.

### Thống kê output

| Chỉ số | Giá trị |
|---|---:|
| Tổng file | 2,908 |
| Tổng dung lượng | 57,027,338 bytes |
| File `.pyc` | 2,907 |
| File lấy từ `PYZ.pyz` | 2,894 |
| File zero-byte thực tế | 0 |
| Python bytecode magic | `cb0d0d0a` (Python 3.12) |
| `.pyc` có cùng magic | 2,907 / 2,907 |

Các file cấp cao nhất gồm:

- `app.pyc`
- `PYZ.pyz`
- `PYZ.pyz_extracted/`
- `struct.pyc`
- `pyimod01_archive.pyc` … `pyimod04_pywin32.pyc`
- PyInstaller bootstrap/runtime-hook `.pyc`

### Kiểm tra integrity của PYZ

PYZ gốc được xác định trong executable tại offset `319,431`, dài `17,062,644` bytes.

| Dữ liệu | SHA-256 |
|---|---|
| Byte range PYZ nhúng trong `TV Automation.exe` | `2e31bd4e6a013fbcc0496dc7f37bfdd69320368bd8fff4672c1899dfc385e4b2` |
| `work/extracted/PYZ.pyz` | `2e31bd4e6a013fbcc0496dc7f37bfdd69320368bd8fff4672c1899dfc385e4b2` |

So sánh byte-for-byte: **khớp hoàn toàn**.

### Cảnh báo empty module

Tool báo tám empty entries:

- `setuptools/_distutils/compilers.pyc`
- `setuptools/_distutils/compilers/C.pyc`
- `setuptools/_vendor.pyc`
- `setuptools/_vendor/jaraco.pyc`
- `src.pyc`
- `src/module.pyc`
- `web.pyc`
- `web/components.pyc`

Mỗi file output vẫn dài 16 byte và chứa header `.pyc` Python 3.12 hợp lệ. Đây là các package/namespace marker không có code body, không phải lỗi decompression hay file bị thiếu.

## Module ứng dụng tìm thấy

Ngoài `app.pyc`, đã nhận diện 17 entry dưới `src` và 20 entry dưới `web`.

### `src`

```text
src/channel_refresh.pyc
src/channel_scanner.pyc
src/channel_store.pyc
src/cookie_utils.pyc
src/license_manager.pyc
src/module/audio_module.pyc
src/module/base.pyc
src/module/delete_video_module.pyc
src/module/list_videos_module.pyc
src/module/model.pyc
src/module/upload_video_module.pyc
src/paths.pyc
src/route_manager.pyc
src/state_manager.pyc
src/updater.pyc
src/utils.pyc
```

`src/module.pyc` là package marker 16 byte.

### `web`

```text
web/nicegui_patches.pyc
web/components/add_audio_flow.pyc
web/components/audio.pyc
web/components/auth.pyc
web/components/common.pyc
web/components/delete_back_flow.pyc
web/components/delete_video.pyc
web/components/delete_video_controller.pyc
web/components/drawer.pyc
web/components/remove_audio.pyc
web/components/settings.pyc
web/components/studio.pyc
web/views/__init__.pyc
web/views/audio.pyc
web/views/auth.pyc
web/views/delete_back_flow.pyc
web/views/delete_video.pyc
web/views/settings.pyc
web/views/studio.pyc
```

`web/components.pyc` là package marker 16 byte.

## Tự kiểm tra bước 2

- [x] Đã ưu tiên và sử dụng `pyinstxtractor-ng` hỗ trợ Python 3.12.
- [x] Đã tự kiểm tra cú pháp bằng `--help`.
- [x] `--info` nhận diện CArchive/PYZ, Python 3.12 và trạng thái không mã hóa.
- [x] Extraction kết thúc thành công với exit code `0`.
- [x] Số entry PYZ output khớp số tool báo cáo: 2,894.
- [x] Tất cả `.pyc` có cùng magic Python 3.12.
- [x] PYZ extract khớp SHA-256 và byte-for-byte với PYZ nhúng.
- [x] Toàn bộ output nằm dưới `work/extracted/`.
- [x] Không khởi chạy executable mục tiêu.
