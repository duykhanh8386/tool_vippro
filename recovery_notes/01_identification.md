# 01 — Nhận diện executable

## Phạm vi và nguyên tắc an toàn

- Mẫu thực tế trong workspace là `TVAutomation_Setup.exe`; không có file tên `TV Automation.exe` ở thư mục gốc.
- Toàn bộ kết quả dưới đây đến từ đọc metadata/bytes, phân tích PE và giải nén archive bằng công cụ tĩnh.
- Không khởi chạy `TVAutomation_Setup.exe`, `TV Automation.exe`, `Uninstall.exe`, DLL hay bất kỳ payload nào.
- Không sửa executable, không can thiệp license/authentication.

## Kết luận nhanh

`TVAutomation_Setup.exe` là installer **InstallForge 1.6.1**, PE32/x86 Windows GUI, chứa payload nén 7-Zip trong PE overlay. Payload được trích xuất tĩnh và có `TV Automation.exe`, một executable PE32+/x86-64 được đóng gói theo chế độ **PyInstaller onedir** với thư mục nội dung `_internal`. Runtime đi kèm là **CPython 3.12.11 x64** (`python312.dll`).

PyInstaller không lưu số phiên bản chính xác trong cookie/archive. Các dấu vết `pyi-contents-directory _internal`, `_PYI_ARCHIVE_FILE` và `PYINSTALLER_RESET_ENVIRONMENT` cho phép nhận diện chắc chắn dòng **PyInstaller 6.x**, và riêng `PYINSTALLER_RESET_ENVIRONMENT` đặt cận dưới ở **6.10**. Vì vậy kết luận an toàn là **PyInstaller >= 6.10; exact version chưa xác định**.

## 1. Installer ngoài: `TVAutomation_Setup.exe`

| Thuộc tính | Giá trị |
|---|---|
| Kích thước | 44,612,420 bytes |
| SHA-256 | `da3eb6734258959c83ac3feffd1e51249adcdcb07eca6633167c753314a4d705` |
| MD5 | `0b03cd5abd550cae0cc154c7502860b9` |
| Authenticode | Không ký (`NotSigned`) |
| Version resource | `TV Automation Setup`, version `v1.0.1` |
| File type | PE32 Windows executable |
| Kiến trúc | x86 / I386 |
| Subsystem | Windows GUI |
| Image base | `0x400000` |
| Entry point RVA | `0x10a943` |
| PE timestamp | `2025-12-23T13:20:04Z` (chỉ là header value, không coi là bằng chứng thời gian tuyệt đối) |

### Compiler/runtime và installer framework

Các chuỗi tĩnh trực tiếp trong PE stub:

- `Created with InstallForge 1.6.1`
- `{InstallForgeSetup}`
- `GCC: (i686-win32-dwarf-rev2, Built by MinGW-W64 project) 12.2.0`
- `libarchive 3.6.2`
- `archive_read_support_format_7zip`

Kết luận: installer được tạo bằng **InstallForge 1.6.1**; stub là native x86, build bằng **GCC/MinGW-w64 12.2.0**, dùng **libarchive 3.6.2** để đọc payload.

### Sections và packer/archive

| Section | Raw size | Entropy |
|---|---:|---:|
| `.text` | 1,093,120 | 6.6037 |
| `.rdata` | 167,936 | 5.7957 |
| `.data` | 54,272 | 3.5159 |
| `.eh_fram` | 22,528 | 4.9463 |
| `.rsrc` | 9,216 | 5.9227 |
| `.reloc` | 31,232 | 6.7103 |

- PE image kết thúc tại offset `0x150c00` (1,379,328).
- Overlay dài 43,233,092 bytes, entropy `8.0000`.
- Header 7-Zip hợp lệ bắt đầu tại offset `0x150c15` (overlay + 21 bytes).
- Archive liệt kê và giải nén tĩnh thành công: 4,102 archive entries, tương ứng 3,701 file thật + 401 directory marker; tổng file thật 127,627,760 bytes.
- Không có bằng chứng UPX packing đáng tin cậy. Một byte sequence `UPX!` xuất hiện bên trong dữ liệu nén của installer là trùng hợp, vì không có section `UPX0`/`UPX1`, trong khi archive 7-Zip được xác nhận trực tiếp.

Payload đã được đặt tại:

- Raw names: `recovery_staging/installer_payload_raw/`
- Tên đã decode Base64 + UTF-16LE: `recovery_staging/installer_payload/`

Hai file cấp cao nhất sau decode:

- `TV Automation.exe` — 17,382,851 bytes
- `Uninstall.exe` — 1,060,864 bytes

## 2. Application bên trong: `TV Automation.exe`

| Thuộc tính | Giá trị |
|---|---|
| Kích thước | 17,382,851 bytes |
| SHA-256 | `83ff27be3e64c5e8c58cfac74a96706c32934d50265571e4f9c025ff86cc8be9` |
| MD5 | `4f8fbedf3a906f2964fc46c66a38893c` |
| File type | PE32+ Windows executable |
| Kiến trúc | x86-64 / AMD64 |
| Subsystem | Windows console |
| Image base | `0x140000000` |
| Entry point RVA | `0xd6c0` |
| PE timestamp | `2026-07-10T10:24:30Z` (header value, có thể được toolchain đặt lại) |
| Imports trực tiếp | `USER32.dll`, `KERNEL32.dll`, `ADVAPI32.dll` |
| Packager | PyInstaller onedir |
| PyInstaller version | 6.x, **>= 6.10**; exact version không được encode |
| Python ABI | CPython 3.12 x64 |
| Python runtime chính xác | 3.12.11 (`_internal/python312.dll`) |

### Sections và embedded CArchive

| Section | Raw size | Entropy |
|---|---:|---:|
| `.text` | 187,392 | 6.4827 |
| `.rdata` | 81,408 | 5.7459 |
| `.data` | 3,584 | 1.8095 |
| `.pdata` | 10,240 | 5.3078 |
| `.fptable` | 512 | 0.0000 |
| `.rsrc` | 6,144 | 6.2437 |
| `.reloc` | 2,048 | 5.2339 |

PE image kết thúc ở `0x47600` (292,352). Từ đúng offset này đến cuối file là PyInstaller CArchive:

| Trường cookie/archive | Giá trị |
|---|---|
| Package start | `0x47600` |
| Package length | 17,090,499 bytes (`0x104c7c3`) |
| PYZ start | `0x4dfc7` |
| TOC absolute offset | `0x1093abb` |
| TOC length | 688 bytes (`0x2b0`) |
| Cookie offset | `0x1093d6b` |
| Cookie size | 88 bytes (`0x58`) |
| Cookie magic | `MEI 0c 0b 0a 0b 0e` |
| Python version field | `312` → Python 3.12 |
| Python library field | `python312.dll` |

Cookie kết thúc đúng tại EOF (`0x1093dc3`), TOC parse kết thúc đúng sau 15 entries và PYZ offset trong TOC khớp byte marker `PYZ\0` ở file offset `0x4dfc7`.

### PyInstaller TOC

| # | Type | Compressed | Name |
|---:|:---:|:---:|---|
| 0 | `m` | yes | `struct` |
| 1 | `m` | yes | `pyimod01_archive` |
| 2 | `m` | yes | `pyimod02_importers` |
| 3 | `m` | yes | `pyimod03_ctypes` |
| 4 | `m` | yes | `pyimod04_pywin32` |
| 5 | `s` | yes | `pyiboot01_bootstrap` |
| 6 | `s` | yes | `pyi_rth_inspect` |
| 7 | `s` | yes | `pyi_rth_pkgutil` |
| 8 | `s` | yes | `pyi_rth_multiprocessing` |
| 9 | `s` | yes | `pyi_rth_setuptools` |
| 10 | `s` | yes | `pyi_rth_traitlets` |
| 11 | `s` | yes | `pyi_rth__tkinter` |
| 12 | `s` | yes | `app` |
| 13 | `o` | no | `pyi-contents-directory _internal` |
| 14 | `z` | no | `PYZ.pyz` |

Entry `app` là entry script bytecode chính. `PYZ.pyz` dài 17,062,644 bytes và sẽ là nguồn chính để phục hồi module/package trong bước tiếp theo.

### Marker PyInstaller xác nhận trực tiếp

Các marker sau xuất hiện trong bootloader/CArchive của chính `TV Automation.exe`:

- `PyInstaller` / `PYINSTALLER`
- `PYZ` và `PYZ\0`
- `_MEIPASS`
- `_PYI_ARCHIVE_FILE`
- `_PYI_APPLICATION_HOME_DIR`
- `_PYI_PARENT_PROCESS_LEVEL`
- `PYINSTALLER_RESET_ENVIRONMENT`
- `PYINSTALLER_STRICT_UNPACK_MODE`
- `python312.dll`
- PyInstaller cookie magic `MEI\x0c\x0b\x0a\x0b\x0e`

## 3. Tự kiểm tra bước 1

- [x] Không chạy executable/payload.
- [x] Xác định outer file type và architecture: PE32 x86 GUI.
- [x] Xác định inner application type và architecture: PE32+ x64 console.
- [x] Xác định installer/compiler: InstallForge 1.6.1, GCC/MinGW-w64 12.2.0.
- [x] Xác định archive/compression: payload 7-Zip trong outer overlay.
- [x] Xác định PyInstaller bằng cookie, TOC và marker độc lập.
- [x] Xác định mode: onedir, contents directory `_internal`.
- [x] Xác định Python: CPython 3.12.11 x64.
- [x] Parse CArchive TOC thành công, đúng 15 entries và kết thúc đúng boundary.
- [x] Xác định entry script `app` và archive code `PYZ.pyz`.
- [x] Ghi nhận giới hạn: không thể suy ra exact PyInstaller patch version chỉ từ artifact hiện có; cận dưới đáng tin cậy là 6.10.

## 4. Artefact hỗ trợ tái lập

- `recovery_tools/static_identify.py`: parser PE/imports/sections/overlay/marker/cookie candidates chỉ đọc file.
- `recovery_tools/decode_payload_paths.py`: decode an toàn các path component Base64/UTF-16LE của payload InstallForge.
- `recovery_staging/installer_payload/`: payload đã giải nén tĩnh, chưa chạy.

Tham chiếu cho suy luận version range: PyInstaller 6.0 đưa nội dung onedir vào `_internal`; PyInstaller 6.10 giới thiệu `PYINSTALLER_RESET_ENVIRONMENT` trong bootloader.
