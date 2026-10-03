# BÁO CÁO PHÂN TÍCH FILE SCANNER HÁN VIỆT: `hanviet_1.md`
**Thời gian phân tích:** 2026-09-29  
**Đối tượng khảo sát:** [`scanner/hanviet/hanviet_1.md`](file:///D:/Coder/Python/Convert_File_V2/Convert_File_v2/scanner/hanviet/hanviet_1.md)  
**Quy mô mẫu:** 40 mục từ/cụm từ xuất hiện nhiều nhất (Top Frequency: 2.700 – 9.800 lần)

---

## 1. TỔNG QUAN KẾT QUẢ PHÂN TÍCH

| Phân loại | Số lượng | Tỷ lệ | Đánh giá |
| :--- | :---: | :---: | :--- |
| **Bắt CHÍNH XÁC (Hán Việt thô / Lỗi convert)** | **12 / 40** | **30%** | Các từ ngữ Hán Việt sượng, lượng từ dịch máy, từ convert 18+ đặc trưng cần thuần Việt hóa. |
| **Bắt NHẦM (Tiếng Việt chuẩn ghép tự do)** | **25 / 40** | **62.5%** | Các cụm hư từ, sở hữu, phủ định, đại từ tiếng Việt hoàn toàn tự nhiên và đúng ngữ pháp. |
| **Bắt NHẦM (Tên nhân vật / Lỗi xưng hô)** | **3 / 40** | **7.5%** | Tên riêng bị dính danh xưng hoặc tên thân mật (Phi nhi, Quân Như mẹ). |

---

## 2. BẢNG PHÂN TÍCH CHI TIẾT TỪNG MỤC TỪ (1 - 40)

### Nhóm 1: Thuật toán BẮT ĐÚNG (Cần giữ lại để biên tập / nạp từ điển)
Những từ này mang văn phong dịch máy tiếng Hán thô thiển, cần thay thế bằng từ thuần Việt:

| STT | ID | Từ gốc (Source) | Tần suất | Bản chất ngôn ngữ | Đề xuất thuần Việt (Target) |
| :---: | :--- | :--- | :---: | :--- | :--- |
| 1 | `hv_0003` | **một cái** | 8,922 | Lỗi dịch thô lượng từ `一个` (*"một cái cổ lão nông thôn"*) | một ngôi làng / một vùng |
| 2 | `hv_0004` | **tỷ tỷ** | 8,231 | Xưng hô convert tiếng Hán `姐姐` (*"Lâm Uyển Bích tỷ tỷ"*) | chị / chị gái |
| 3 | `hv_0009` | **cự mãng** | 6,706 | Hán Việt miêu tả ẩn dụ (*"nhất con cự mãng"*) | con trăn khổng lồ |
| 4 | `hv_0013` | **chính mình** | 4,868 | Tiếng Hán `自己` gượng gạo (*"tại chính mình dạ dày"*) | bản thân / mình |
| 5 | `hv_0014` | **chính là** | 4,510 | Tiếng Hán `就是` (*"đây chính là Chu Ngọc Mị"*) | chính là / là |
| 6 | `hv_0015` | **nhưng là** | 4,457 | Hư từ tiếng Hán `但是` (*"nhưng là nàng nước mắt"*) | nhưng / nhưng mà |
| 7 | `hv_0021` | **có chút** | 3,368 | Phó từ tiếng Hán `有点` (*"bao nhiêu có chút phiền chán"*) | hơi / có phần |
| 8 | `hv_0025` | **nam nhân** | 3,211 | Hán Việt thô `男人` (*"chán ghét nam nhân"*) | đàn ông / người đàn ông |
| 9 | `hv_0029` | **càng thêm** | 3,106 | Phó từ tiếng Hán `更加` (*"càng thêm quyến rũ"*) | càng / thêm phần |
| 10 | `hv_0030` | **nữ nhân** | 2,980 | Hán Việt thô `女人` (*"còn có một cái nữ nhân"*) | phụ nữ / người phụ nữ |
| 11 | `hv_0033` | **mỹ phụ** | 2,937 | Hán Việt thô `美妇` (*"thành thục mỹ phụ"*) | người phụ nữ đẹp / thiếu phụ |
| 12 | `hv_0035` | **dũng đạo** | 2,877 | Thuật ngữ convert 18+ (*"dũng đạo co rút"*) | đường hầm / lối vào / hoa đạo |
| 13 | `hv_0040` | **mê người** | 2,721 | Tính từ tiếng Hán `迷人` (*"mê người phong vận"*) | quyến rũ / mê đắm / hút hồn |

---

### Nhóm 2: Thuật toán BẮT NHẦM (False Positives - Cần LOẠI BỎ)
Đây là các cụm từ tiếng Việt tự nhiên 100%, không có bất kỳ lỗi Hán Việt nào nhưng bị bắt do thuật toán n-gram thiếu từ ghép ngữ pháp:

| STT | ID | Từ gốc (Source) | Tần suất | Lý do bắt nhầm |
| :---: | :--- | :--- | :---: | :--- |
| 1 | `hv_0005` | **không có** | 8,229 | Hư từ phủ định tiếng Việt chuẩn ghép từ `không` + `có`. |
| 2 | `hv_0006` | **của nàng** | 8,196 | Cụm sở hữu cách tiếng Việt chuẩn (`của` + `nàng`). |
| 3 | `hv_0007` | **của hắn** | 7,657 | Cụm sở hữu cách tiếng Việt chuẩn (`của` + `hắn`). |
| 4 | `hv_0008` | **cũng không** | 7,222 | Phó từ liên kết tiếng Việt chuẩn (`cũng` + `không`). |
| 5 | `hv_0010` | **rô i** | 5,648 | Lỗi vỡ font / tách ký tự của từ `"rồi"` trong file text gốc. |
| 6 | `hv_0011` | **không thể** | 5,425 | Cụm từ phủ định năng lực chuẩn tiếng Việt (`không` + `thể`). |
| 7 | `hv_0012` | **trong lòng** | 4,888 | Cụm từ chỉ tâm trạng quen thuộc trong văn học tiếng Việt. |
| 8 | `hv_0016` | **không được** | 4,444 | Cụm từ phủ định/khả năng chuẩn (`không` + `được`). |
| 9 | `hv_0018` | **đầu lưỡi** | 3,664 | Danh từ thuần Việt chỉ bộ phận cơ thể hoàn toàn chuẩn xác. |
| 10 | `hv_0019` | **không biết** | 3,505 | Cụm từ nhận thức phủ định chuẩn tiếng Việt. |
| 11 | `hv_0020` | **hai tay** | 3,392 | Cụm số đếm + danh từ thuần Việt bình thường. |
| 12 | `hv_0022` | **một tiếng** | 3,311 | Lượng từ âm thanh tiếng Việt thuần túy (*"cười một tiếng"*). |
| 13 | `hv_0023` | **một bên** | 3,239 | Cụm từ phương hướng tiếng Việt bình thường (*"ở một bên"*). |
| 14 | `hv_0024` | **không khỏi** | 3,226 | Phó từ liên kết chỉ cảm xúc tự nhiên trong văn học Việt Nam. |
| 15 | `hv_0026` | **không phải** | 3,183 | Hư từ phủ định nhận định tiếng Việt thông dụng. |
| 16 | `hv_0027` | **ánh mắt** | 3,146 | Danh từ thuần Việt hoàn toàn chuẩn mực. |
| 17 | `hv_0028` | **tuyết trắng** | 3,111 | Tính từ miêu tả màu sắc tự nhiên trong tiếng Việt. |
| 18 | `hv_0031` | **như thế nào** | 2,973 | Cụm từ nghi vấn chuẩn tiếng Việt. |
| 19 | `hv_0032` | **phát ra** | 2,965 | Cụm động từ chỉ nguồn âm thanh/hành động chuẩn. |
| 20 | `hv_0034` | **không cần** | 2,916 | Hư từ phủ định nhu cầu chuẩn tiếng Việt. |
| 21 | `hv_0036` | **cho nàng** | 2,787 | Giới từ + đại từ chỉ đối tượng (*"chiếu cố cho nàng"*). |
| 22 | `hv_0037` | **đối với** | 2,749 | Giới từ tiếng Việt chuẩn mực (*"đối với nàng"*). |
| 23 | `hv_0038` | **của mình** | 2,733 | Cụm từ sở hữu phản thân chuẩn tiếng Việt. |
| 24 | `hv_0039` | **cũng là** | 2,729 | Liên từ ghép tự do tiếng Việt bình thường. |

---

### Nhóm 3: Bắt NHẦM do dính Tên riêng & Danh xưng
| STT | ID | Từ gốc (Source) | Tần suất | Ngữ cảnh | Phân tích lỗi |
| :---: | :--- | :--- | :---: | :--- | :--- |
| 1 | `hv_0001` | **như mẹ** | 9,817 | *"quân như mẹ ôn hương"* | Cắt vụn từ tên mẹ là **Quân Như** + danh từ `"mẹ"`. |
| 2 | `hv_0002` | **quân như mẹ** | 9,744 | *"quân như mẹ ôn hương"* | Dính tên riêng **Quân Như** (mẹ nhân vật) + danh xưng `"mẹ"`. |
| 3 | `hv_0017` | **phi nhi** | 4,235 | *"Phi nhi, ngươi cứu hắn"* | Tên gọi thân mật của nhân vật chính **Long Kiếm Phi**. |

---

## 3. NGUYÊN NHÂN KỸ THUẬT (ROOT CAUSE)

1. **Đặc thù ngôn ngữ đơn lập của Tiếng Việt:**
   * Tiếng Việt ghép các từ đơn độc lập với nhau rất tự do (`không` + `có`, `của` + `hắn`, `trong` + `lòng`, `đối` + `với`).
   * Các từ điển từ vựng chuẩn (như `vietnamese_words.txt`, từ điển Hoàng Phê) chỉ lưu **từ đơn** (`không`, `có`) hoặc **từ ghép cố định** (`hạnh phúc`, `gia đình`), **không bao giờ lưu các cụm ghép ngữ pháp tự do** (`của hắn`, `cho nàng`, `cũng không`).
   * Khi thuật toán quét n-gram 2–3 chữ, hễ cụm từ không có trong từ điển là máy gán nhãn thành *"Cụm từ ngoài từ điển chuẩn"*, dẫn đến bắt nhầm hàng loạt cụm từ tiếng Việt bình thường.

2. **Chưa lọc Stopwords & Giới từ chức năng:**
   * Các hư từ ngữ pháp bắt đầu bằng `của`, `cho`, `với`, `trong`, `ở`, `tại`, `như` bị xem như cụm từ mới.

3. **Chưa liên kết bộ lọc tên riêng từ Character Scanner:**
   * Các tên riêng được gọi thân mật (`Phi nhi`) hoặc xưng hô gia tộc (`Quân Như mẹ`) chưa được loại trừ triệt để.

---

## 4. GIẢI PHÁP NÂNG CẤP THUẬT TOÁN ĐỂ LOẠI BỎ TRIỆT ĐỂ BẮT NHẦM

1. **Bổ sung Bộ lọc Ngữ pháp Chức năng (Function Words Filter):**
   * Nếu n-gram được tạo hoàn toàn từ các hư từ / đại từ / giới từ cơ bản (`không`, `có`, `của`, `hắn`, `nàng`, `mình`, `ta`, `ngươi`, `cho`, `với`, `trong`, `ở`, `hai`, `một`, `cũng`, `là`, `và`...), **lập tức bỏ qua**.
   * Bỏ qua các n-gram bắt đầu bằng giới từ: `của ...`, `cho ...`, `đối với ...`, `ở trong ...`.

2. **Bổ sung Bộ từ ghép Tiếng Việt thường gặp vào Whitelist:**
   * Đưa các từ thuần Việt thông dụng như `đầu lưỡi`, `hai tay`, `ánh mắt`, `tuyết trắng`, `phát ra` vào bộ nhớ từ điển tiếng Việt chuẩn.

3. **Loại trừ hậu tố xưng hô & tên thân mật (Suffix Filter):**
   * Tự động nhận diện hậu tố thân mật: `... nhi` (Phi nhi, Tuyết nhi), `... tỷ`, `... ca` nếu là tên riêng thì chuyển giao cho bộ lọc nhân vật xử lý.
