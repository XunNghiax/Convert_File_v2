# TIẾN TRÌNH THỰC HIỆN DỰ ÁN CHARACTER SCANNER

- **Bắt đầu**: 2026-09-26
- **Trạng thái**: Đã hoàn thiện tài liệu thiết kế kỹ thuật (Spec Complete)

## Danh sách công việc (Roadmap & Checkpoints)

- [x] **Giai đoạn 1**: Khảo sát dữ liệu mẫu (`exam.txt`, `file_nhan_vat.json`, các file `filters/`, `prompt.md`).
- [x] **Giai đoạn 2**: Thống nhất định hướng phương án Heuristic đa tầng và quy cách thư mục `scanner/`.
- [x] **Giai đoạn 3**: Hoàn thiện tài liệu thiết kế kỹ thuật (`superpowers/design_character_scanner.md`):
  - [x] Phần 1: Kiến trúc tổng thể và luồng dữ liệu (Data Flow & Block Schema).
  - [x] Phần 2: Chi tiết các thuật toán nhận diện (Heuristic Rules, Trimming, Scoring).
  - [x] Phần 3: Xử lý ngữ cảnh trung tâm (Context Expander) và Phân mảnh xuất bản (Chunk Exporter).
  - [x] Phần 4 & 5: Xử lý ngoại lệ, khử trùng lặp và chiến lược kiểm thử đối chiếu `file_nhan_vat.json`.
- [ ] **Giai đoạn 4**: Người dùng phê duyệt thiết kế và chuyển sang lập kế hoạch thực hiện chi tiết (Implementation Plan).
- [ ] **Giai đoạn 5**: Lập trình cài đặt thuật toán (TDD & code implementation).
- [ ] **Giai đoạn 6**: Kiểm thử và đối chiếu độ khớp với `file_nhan_vat.json` trên tập mẫu `exam.txt`.
