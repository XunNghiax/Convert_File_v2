# Thiết Kế Cấu Trúc Menu Phân Cấp (Hierarchical CLI Menu) Cho `run_cli.py`

## 1. Mục tiêu & Vấn đề hiện tại
- **Vấn đề:** File `run_cli.py` hiện có tới 16 chức năng phẳng từ `[0]` đến `[15]` dồn hết vào một menu chính duy nhất, số thứ tự nhảy cóc (`15, 1, 2, 3, 4, 5, 10, 11, 12, 13, 14, 6, 7, 9, 8, 0`), gây khó quan sát và dễ chọn nhầm.
- **Mục tiêu:**
  - Tái cấu trúc thành mô hình **Menu Phân Cấp 2 Tầng (Hierarchical Two-tier Menu)**: 1 Menu Cha điều hướng 6 Menu Con.
  - Tách các khối lệnh xử lý thành các hàm riêng biệt (Modular Sub-menus), giúp code ngắn gọn, dễ bảo trì và dễ viết test.
  - Bảo toàn 100% các chức năng hiện có, không làm gãy bất kỳ câu lệnh hay tham số nào.

---

## 2. Kiến trúc Menu Phân Cấp

```
                     ┌───────────────────────────────────┐
                     │       MENU CHÍNH (MAIN MENU)      │
                     │  - Trạng thái từ điển (Stats)     │
                     │  - 6 Nhóm chức năng chính         │
                     └─────────────────┬─────────────────┘
                                       │
     ┌──────────────┬──────────────┬───┴──────────┬──────────────┬──────────────┐
     ▼              ▼              ▼              ▼              ▼              ▼
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ Nhóm 1  │   │ Nhóm 2  │   │ Nhóm 3  │   │ Nhóm 4  │   │ Nhóm 5  │   │ Nhóm 6  │
│ Dịch AI │   │ Quét    │   │ Quét    │   │ Quản lý │   │ Thay thế│   │ Hệ thống│
│ Ollama  │   │ Tên NV  │   │ Hán     │   │ Từ điển │   │ Văn bản │   │ & Tests │
│ Colab   │   │ Gemini  │   │ Việt    │   │         │   │         │   │         │
└─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

---

## 3. Chi tiết các Tầng Menu

### 3.1. Menu Cha (Main Menu)
```text
====================================================================
      HỆ THỐNG QUÉT NHÂN VẬT & BIÊN TẬP TỪ ĐIỂN DỊCH THUẬT V2
====================================================================
  📊 TRẠNG THÁI DỮ LIỆU HIỆN TẠI:
     • character_dict.json : X mục (Tên nhân vật)
     • common_dict.json    : Y mục (Từ ngữ chung / Thành ngữ)
     • samples/import.json : Z mục (Sẵn sàng nạp)
--------------------------------------------------------------------
  [1] 🌐 Dịch thuật AI (Ollama Qwen2.5 / Google Colab)
  [2] 👥 Quét & Xử lý Tên Nhân vật (Character Scanner)
  [3] 🏮 Quét & Xử lý Từ Hán Việt / Cụm từ lạ (Hanviet Scanner)
  [4] 📖 Quản lý Từ điển & Nạp Dữ liệu (Dictionary Manager)
  [5] 🔄 Thay thế Văn bản & Hậu kỳ (Replace Engine)
  [6] 🛠️ Công cụ Hệ thống & Kiểm thử (System & Tests)
  [0] ❌ Thoát chương trình
====================================================================
```

### 3.2. Menu Con Chi Tiết (Sub-menus)

#### Nhóm [1]: Dịch thuật AI (`menu_ai_translation`)
- `[1]` 🌐 Dịch tiểu thuyết raw bằng Ollama Qwen2.5 (Colab Server)
- `[2]` 📡 Kiểm tra kết nối nhanh máy chủ Colab / Ollama
- `[0]` ↩️ Quay lại menu chính

#### Nhóm [2]: Quét & Xử lý Tên Nhân vật (`menu_character_scanner`)
- `[1]` 🚀 Toàn trình: Quét nhân vật + Tự động gửi Gemini -> `samples/import.json`
- `[2]` 🔍 Chỉ quét nhân vật (Xuất scanner/ gồm .md & master JSON)
- `[3]` 🌐 Chỉ gửi các file trong scanner/ lên Gemini -> `samples/import.json`
- `[4]` 🎯 Lọc nhanh scanner/ theo số lần xuất hiện (min-count)
- `[5]` ♻️ Đặt lại tiến trình (Reset progress) gửi Gemini
- `[0]` ↩️ Quay lại menu chính

#### Nhóm [3]: Quét & Xử lý Từ Hán Việt / Cụm từ lạ (`menu_hanviet_scanner`)
- `[1]` 🏮 Toàn trình: Quét Hán Việt + Gửi Gemini -> `samples/import_hanviet.json`
- `[2]` 🔍 Chỉ quét từ Hán Việt & Cụm từ bất thường (Xuất scanner/hanviet/)
- `[3]` 🌐 Chỉ gửi các file trong scanner/hanviet/ lên Gemini -> `samples/import_hanviet.json`
- `[4]` 🎯 Lọc nhanh scanner/hanviet/ theo số lần xuất hiện (min-count)
- `[0]` ↩️ Quay lại menu chính

#### Nhóm [4]: Quản lý Từ điển & Nạp Dữ liệu (`menu_dictionary_manager`)
- `[1]` 📥 Nạp `samples/import.json` vào từ điển (Tự động phân bổ theo `is_character`)
- `[2]` 📥 Nạp `samples/import_hanviet.json` vào `hanviet_dict.json`
- `[3]` 📥 Nạp các từ mới thu hoạch (`samples/suggested_terms.json`) vào từ điển
- `[4]` ✍️ Nhập thủ công từng từ vào từ điển (Interactive mode)
- `[0]` ↩️ Quay lại menu chính

#### Nhóm [5]: Thay thế Văn bản & Hậu kỳ (`menu_replace_engine`)
- `[1]` 🔄 Thay thế văn bản bằng từ điển (Single-Pass Longest Match)
- `[2]` 🛡️ Quét & Thay thế các lỗi de-convert tên riêng (`deconvert_dict.json`)
- `[0]` ↩️ Quay lại menu chính

#### Nhóm [6]: Công cụ Hệ thống & Kiểm thử (`menu_system_tools`)
- `[1]` 🧪 Chạy toàn bộ Unit Tests hệ thống (`pytest`)
- `[2]` 📊 Xem chi tiết đường dẫn và số lượng file tài nguyên
- `[0]` ↩️ Quay lại menu chính

---

## 4. Thiết kế Kỹ thuật (Technical Implementation)

1. **Hàm hiển thị thống nhất (`print_sub_banner(title: str)`):**
   Mỗi menu con sẽ có banner tiêu đề riêng để người dùng luôn biết mình đang ở khu vực chức năng nào.
2. **Xử lý vòng lặp Menu con (`while True:`):**
   Mỗi menu con là một vòng lặp độc lập. Khi bấm `[0]`, hàm `return` để trở về vòng lặp của Menu chính (`main_menu()`).
3. **Bảo tồn bắt ngoại lệ (`KeyboardInterrupt`):**
   Nhấn Ctrl+C ở bất kỳ menu con nào đều trở về an toàn mà không làm crash terminal.
4. **Kiểm thử tự động (`tests/test_run_cli.py`):**
   Viết unit tests kiểm tra:
   - Tất cả các hàm menu con đều callable.
   - Luồng chọn `0` quay lại an toàn.
   - Toàn bộ suite test 94+ vẫn pass 100%.
