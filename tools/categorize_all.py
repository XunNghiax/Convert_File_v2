import json

with open("scanner/scanner_master.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Group targets into:
# 1. Địa danh / Quốc gia / Vùng miền
# 2. Cơ quan / Tổ chức / Doanh nghiệp / Bang hội
# 3. Tác phẩm / Giải thưởng / Đồ vật / Khái niệm / Danh từ chung
# 4. Từ cảm thán / Miêu tả tính từ / Động từ / Thành ngữ bị nhận diện nhầm
# 5. Lỗi ngữ pháp dính từ trước từ nhân xưng/quan hệ/hồ sơ (ví dụ: 'an ủi ngọc khanh', 'bóng đá thời điểm',...)
# 6. Nhân vật lịch sử / Điển tích / Nhân vật công chúng ngoài đời (không phải nhân vật trong cốt truyện)
# 7. Nhân vật hợp lệ trong truyện (cần giữ lại)

categories = {
    "1_dia_danh": [
        "Tô Châu", "Cổ Hy Lạp", "Thổ Nhĩ Kỳ", "Đông Hải", "Hà Đông", "Thái Sơn", "Lương Sơn",
        "Tây Môn", "Cao Hùng", "Vũ Hoa", "Hàn Quốc Nhật Bản", "Lạc Dương Nam Cung", "Lam Điền",
        "Đài Vũ Hoa", "Sơn Tây"
    ],
    "2_to_chuc_cong_ty": [
        "Vân Long", "Đại Trung Hoa", "Hoa Hạ Thần Châu", "Lăng Vân", "Phong Điền"
    ],
    "3_tac_pham_do_vat_khai_niem": [
        "Hồng Lâu Mộng", "Kim Bình Mai", "Kim Bôi", "Thái Thản Ni Khắc", "Kim Lợi",
        "Lưu Ly Cung", "Tống Triều", "Bách Linh"
    ],
    "4_tinh_tu_dong_tu_cam_than_mieu_ta": [
        "Ha Ha", "Mềm Mại", "Trắng Nõn", "Cổ Trắng", "Bảo Đảm", "Nhạc Nhạc", "Đại Hòa",
        "Thật Dài Rên Rỉ", "Cả Người Mềm Yếu", "Nổi Lên Phản Ứng", "Bóng Hình Xinh Đẹp",
        "Da Thịt", "Thái Hư", "Hầu Vương", "Hồng Hà", "Phương Hoa", "Loan Phượng",
        "Đúng Vậy A", "Thấu Xương Toan Ngứa", "Đại Từ Đại Bi", "Bảo Bối Nhi", "Thổ Khí Như Lan",
        "Hoa Cốc", "Nói Như", "Lơ Trên Mặt Đất", "Hứa Ly", "Đại Thụy", "Nam Nhân Không Xấu",
        "Như Thế Tán Tỉnh", "Thái Hòa"
    ],
    "5_loi_dinh_tu_ngu_phap": [
        "Hoàng Hậu Nữ Nhi", "Vương Phi Nữ Nhi", "Văn Nhân Thân Vương", "Thủ Tướng", "Ngoại Tướng",
        "Văn Tiền Tuyết Văn", "Râu Rậm Cẩn", "Thi Âm Nữ Nhi", "Tần Khả", "Diệp Ngọc Thiến Mẹ",
        "Đường Có Mỹ Nữ", "Hồng Tò Mò", "Chân Trước Mặt Chui", "Giường Ném Một Cái",
        "Rất Thư Thái", "Phải Là Như", "Tuyết Trắng Cổ Trắng", "Tiền Cá", "Văn Là Của Ngài",
        "Là Mỹ Tư Tư", "Gợi Cảm Mê", "Nhìn Không Chuyển Mắt", "Đạo Mạo Hạng", "Khưu Nguyễn",
        "Là Phải Nữ Nhân", "Hoàng Kiến", "Chu Kiệt", "Hạ Khưu", "Đại Hòa Nhỏ Yếu",
        "Là Nữ Nhân Mùa", "Trịnh Tú Nga Một", "Động Tình Ca Ngợi", "Lang Chức Nữ Vợ",
        "Sa Trong Quần Áo", "Rách Tiếng Nước Chảy", "Hoàng Dung Tiểu Long", "Long Đã Trở Thành",
        "Nam Nhân Khí Phách", "Văn Tuyết Văn Mẹ", "Xảo Tiếu Thiến Hề", "Phu Lý Đầu To",
        "Cường Tráng Trong Ngực", "Ẩn Núp Khát Vọng", "An Bài Như Yên", "Đôi Môi Công Kích",
        "Tốt Đẹp Như", "Hoàng Long", "Long Kiếm Phi Đối", "Yêu Trong Khoái", "Đại Đông",
        "Ngọt Ngào Như", "Khát Vọng Rung Động", "Hầu Hạ Hai Vị", "Lương Hiểu Tịnh Một",
        "Làm Nàng Hết Hồn", "Hạ Thân Chỗ Sâu", "Suy Nghĩ Không Gian", "Sinh Lý", "Mai Tình Nhân",
        "Cổ Đại Sẽ Có", "Nào Tuyết", "Hà Lan Tam", "Miệng Vào Không Lọt", "Bóng Đá Thời Điểm",
        "Thời Thượng Thời Điểm", "Như Khói Chuyện Cũ", "Dung Nhan Dịch Lão", "Tưởng Tượng",
        "Cao Hứng Nguyên Xuân", "An Ủi Ngọc Khanh"
    ],
    "6_nhan_vat_lich_su_dien_tich_dien_vien": [
        "Chu Nhuận Phát", "Vương Hy Chi", "Ngô Đạo Tử", "Tôn Ngộ", "Chu Thương", "Viêm Đế",
        "Đường Tăng", "Chư Cát Lượng", "Chu Du", "Trình Giảo Kim", "An Lộc Sơn", "Lưu Bang",
        "Tiêu Hà", "Hàn Tín", "Tào Tháo", "Mạnh Hoạch", "Tôn Trung Sơn", "Từ Hi", "Văn Thiên Tường",
        "Tôn Tử", "Lỗ Ban", "Mạnh Đức", "Trương Lương", "Lưu Thiên", "Chu Tự Thanh", "Cừu Thiên",
        "Lâm Đại Ngọc", "La Bá Đặc Ba", "La Bá Đặc", "Mã Lạp", "Thang Mỗ Khắc Lỗ", "Hàn Quốc Thái",
        "Võ Tòng", "Phương Văn", "Lôi Nhĩ", "Lạc Khắc", "Uất Trì"
    ]
}

# Collect all classified false positives
all_classified_fp = set()
for k, v in categories.items():
    all_classified_fp.update(v)

all_targets = set(item["target"] for item in data)
unclassified = all_targets - all_classified_fp

print(f"Total targets: {len(all_targets)}")
print(f"Total categorized non-person/invalid/external: {len(all_classified_fp)}")
print(f"Remaining valid characters: {len(unclassified)}")
print("\nValid character samples:", sorted(list(unclassified))[:25])
