# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** [Cần bổ sung]

**Thành viên:** Thái Hữu Tuấn (2A202602465); [Cần bổ sung các thành viên khác]

**Ngày:** 19/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Dịch vụ, thủ tục và quy định ký túc xá đại học.

**Tại sao nhóm chọn chủ đề này?**

Thông tin ký túc xá nằm rải rác trong hướng dẫn đăng ký, nội quy và văn bản pháp quy nên phù hợp với bài toán RAG. Các câu hỏi có đáp án kiểm chứng được, đồng thời corpus có cấu trúc điều/mục rõ ràng để so sánh ảnh hưởng của nhiều chiến lược chunking.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|---------------|--------------------|-----------------------|------------|-----------------|
| 1 | Nội quy và quy định Ký túc xá HUMG | https://ktx.humg.edu.vn/ky-tuc-xa/Pages/noi-quy-quy-dinh.aspx?ItemID=6950 | 19/09/2026 / không nêu | 16.238 | `doc_id`, `title`, `source_url`, `audience`, `department`, `category`, `language` |
| 2 | Hướng dẫn tân sinh viên KTX TP.HCM | https://huongdan.ktxhcm.edu.vn/huong-dan/tan-sinh-vien | 19/09/2026 / không nêu | 8.700 | như trên |
| 3 | Nội quy Ký túc xá TDTU Bảo Lộc | https://baoloc.tdtu.edu.vn/noi-quy-ky-tuc-xa | 19/09/2026 / không nêu | 6.685 | như trên |
| 4 | Quy định sinh hoạt, học tập và ứng xử nội trú | https://baoloc.tdtu.edu.vn/quy-dinh-sinh-hoat-hoc-tap-ung-xu-noi-tru-ky-tuc-xa | 19/09/2026 / không nêu | 6.225 | như trên |
| 5 | Hướng dẫn đăng ký nội trú TDTU | https://dormitory.tdtu.edu.vn/huong-dan/dang-ky-noi-tru | 19/09/2026 / không nêu | 5.119 | như trên |
| 6 | Nội dung vi phạm và khung xử lý kỷ luật KTX | https://baoloc.tdtu.edu.vn/noi-dung-vi-pham-va-khung-xu-ly-ky-luat | 19/09/2026 / không nêu | 6.911 | như trên |
| 7 | Nhà công vụ ĐHQG-HCM cho giảng viên và viên chức | https://ipsc.edu.vn/nha-cong-vu/ | 19/09/2026 / không nêu | 5.506 | như trên; `audience=faculty` |
| 8 | Thông tư 27/2011/TT-BGDĐT — Quy chế HSSV nội trú | https://luatvietnam.vn/giao-duc/thong-tu-27-2011-tt-bgddt-bo-giao-duc-va-dao-tao-62739-d1.html | 19/09/2026 / 27/2011/TT-BGDĐT | 18.865 | như trên; `document_version=27/2011/TT-BGDĐT` |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Corpus chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` hoặc ngày hiệu lực trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất? |
|-----------------|------|---------------|-------------------------------|
| `doc_id` | string | `ktx-tdtu-dang-ky-noi-tru` | Định danh ổn định để nhóm/xóa toàn bộ chunk của một tài liệu. |
| `title` | string | `Hướng dẫn đăng ký nội trú Ký túc xá` | Hiển thị nguồn dễ hiểu và hỗ trợ truy vết. |
| `source_url` | string | `https://dormitory.tdtu.edu.vn/...` | Kiểm chứng nguồn và trích dẫn. |
| `retrieved_at` | date/string | `2026-09-19` | Biết thời điểm thu thập dữ liệu. |
| `document_version` | string | `27/2011/TT-BGDĐT` | Phân biệt phiên bản hoặc hiệu lực của văn bản. |
| `audience` | string | `student`, `faculty`, `all` | Lọc đúng nhóm đối tượng, tránh trộn KTX sinh viên với nhà công vụ. |
| `department` | string | `dormitory-management` | Giới hạn tìm kiếm theo đơn vị quản lý. |
| `category` | string | `registration`, `rules`, `discipline` | Thu hẹp retrieval theo loại nội dung. |
| `language` | string | `vi` | Chọn mô hình và dữ liệu đúng ngôn ngữ. |
| `chunk_index` | integer | `4` | Xác định vị trí chunk trong tài liệu. |
| `chunking_strategy` | string | `heading` | Theo dõi chiến lược tạo chunk để benchmark. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

### Phân tích đường cơ sở (Baseline Analysis)

Thiết lập so sánh: `chunk_size=800`.

| Tài liệu | Chiến lược | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|------------|----------------|-------------------|---------------------------|
| `ktx-quy-dinh-sinh-hoat-ung-xu.md` | FixedSize (`fixed_size`) | 8 | 781,1 | Trung bình; có thể cắt giữa từ/câu. |
| `ktx-quy-dinh-sinh-hoat-ung-xu.md` | Sentence (`by_sentences`) | 18 | 325,2 | Tốt ở ranh giới câu nhưng chunk nhỏ. |
| `ktx-quy-dinh-sinh-hoat-ung-xu.md` | Recursive (`recursive`) | 9 | 655,4 | Tốt; ưu tiên đoạn, dòng rồi câu. |
| `ktx-tdtu-dang-ky-noi-tru.md` | FixedSize (`fixed_size`) | 7 | 733,6 | Trung bình; đôi lúc cắt danh sách. |
| `ktx-tdtu-dang-ky-noi-tru.md` | Sentence (`by_sentences`) | 16 | 299,4 | Tốt ở cấp câu nhưng phân mảnh nhiều. |
| `ktx-tdtu-dang-ky-noi-tru.md` | Recursive (`recursive`) | 7 | 690,7 | Tốt; cân bằng kích thước và ngữ nghĩa. |
| `quy-che-hssv-noi-tru.md` | FixedSize (`fixed_size`) | 25 | 788,8 | Trung bình; dễ cắt ngang điều khoản. |
| `quy-che-hssv-noi-tru.md` | Sentence (`by_sentences`) | 65 | 282,6 | Giữ câu nhưng tạo nhiều chunk nhỏ. |
| `quy-che-hssv-noi-tru.md` | Recursive (`recursive`) | 27 | 686,0 | Tốt; giữ phần lớn ranh giới tự nhiên. |

### Chiến lược của từng thành viên

**Thành viên 1 — Thái Hữu Tuấn**
- **Loại chiến lược:** Custom `HeadingChunker`
- **Mô tả & lý do chọn:** Tách theo heading Markdown và tiêu đề pháp quy (`Điều`, `Chương`, số La Mã), sau đó dùng recursive splitting nếu mục vượt 800 ký tự. Corpus chủ yếu là nội quy và quy chế có cấu trúc rõ nên cách này giữ tên điều/mục trong chunk, giúp người đọc kiểm chứng kết quả nhanh hơn.
- **Ý tưởng cài đặt:**

```python
matches = list(HEADING_PATTERN.finditer(text))
for each_heading_section in sections:
    chunks.extend(split_section_with_heading_prefix(each_heading_section))
```

**Thành viên 2 — [Cần bổ sung]**
- **Loại chiến lược:** [Cần bổ sung]
- **Mô tả & lý do chọn:** [Cần bổ sung]
- **Code snippet (nếu custom):** [Cần bổ sung]

**Thành viên 3 — [Cần bổ sung]**
- **Loại chiến lược:** [Cần bổ sung]
- **Mô tả & lý do chọn:** [Cần bổ sung]
- **Code snippet (nếu custom):** [Cần bổ sung]

### So Sánh Giữa Các Thành Viên / Chiến Lược Đã Chạy

| Người chạy | Chiến lược | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|------------|------------|-----------------------|-----------|----------|
| Thái Hữu Tuấn | Heading | 6/10 | Chunk bám điều/mục, dễ đọc và truy vết nguồn. | Tạo 190 chunks; heading ngắn có thể được xếp hạng cao dù thiếu nội dung. |
| [Cần bổ sung người phụ trách] | Fixed | 6/10 | Ít chunk hơn heading (106), đơn giản và nhanh. | Có thể cắt giữa từ, câu hoặc danh sách. |
| [Cần bổ sung người phụ trách] | Recursive | 6/10 | Cân bằng độ dài với ranh giới ngữ nghĩa; 102 chunks. | Không bảo toàn rõ tên điều/mục như heading. |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**

Ba chiến lược cùng đạt 6/10 nên chưa thể kết luận heading tốt hơn theo độ chính xác benchmark. Nhóm chọn heading cho corpus quy định vì kết quả dễ giải thích và mỗi chunk giữ được tên điều/mục; tuy nhiên cần xử lý heading đứng riêng và chia nhỏ các mục dài hơn để cải thiện ranking.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-----------------|---------------------------------|---------------------------|
| 1 | Ký túc xá mở cửa và đóng cửa lúc mấy giờ? | Mở cửa 05:00, đóng cửa 22:00. | `ktx-quy-dinh-sinh-hoat-ung-xu#3` (heading). |
| 2 | Sinh viên đang bị kỷ luật từ mức nào thì không được đăng ký ở Ký túc xá TDTU? | Đang thi hành kỷ luật cấp trường từ mức khiển trách trở lên thì không được đăng ký. | `ktx-tdtu-dang-ky-noi-tru#3` (heading). |
| 3 | Sinh viên vắng mặt tại khu nội trú quá bao lâu thì phải báo Ban quản lý? | Vắng mặt quá 1 ngày phải báo Ban quản lý khu nội trú. | `quy-che-hssv-noi-tru#24` (heading). |
| 4 | Hồ sơ đăng ký nội trú TDTU cần những giấy tờ cơ bản nào? | Phiếu đăng ký, bản sao CCCD/CC, giấy minh chứng diện ưu tiên nếu có và giấy xác nhận cư trú khi cần. | `ktx-tdtu-dang-ky-noi-tru#4` (heading). |
| 5 | Những đối tượng nào được ưu tiên xét chỗ ở? | Diện chính sách, người khuyết tật, mồ côi, hộ nghèo/cận nghèo hoặc vùng có điều kiện khó khăn. | `quy-che-hssv-noi-tru#19` (heading); lọc `audience=student`. |

### Tổng hợp chất lượng truy xuất của nhóm

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|---------------------------------|-------------------------------|---------|
| 1 | Giờ mở/đóng cửa | Heading | Có | Heading đạt top-1 score 0,7163 và chứa đủ hai mốc giờ. |
| 2 | Mức kỷ luật không được đăng ký | Recursive | Có với recursive | Heading để chunk đúng ở hạng 44; lỗi ranking, không phải thiếu dữ liệu. |
| 3 | Thời gian vắng mặt phải báo | Fixed / Heading | Có | Heading đưa đúng Điều 6 lên top-1 với score 0,7544. |
| 4 | Giấy tờ đăng ký nội trú | Fixed / Heading | Có | Heading đưa danh sách hồ sơ lên top-1 với score 0,6801. |
| 5 | Đối tượng ưu tiên | Chưa có chiến lược đạt yêu cầu | Không | Filter đúng audience nhưng chunk ưu tiên vẫn ngoài top-3. |

**Tổng điểm retrieval theo từng lần chạy:** Fixed `6/10`, Recursive `6/10`, Heading `6/10`.

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**

Câu 5 dùng `audience=student`. Filter loại các chunk nhà công vụ có `audience=faculty` đang chiếm thứ hạng cao khi không lọc, nên kết quả đúng phạm vi hơn; tuy vậy semantic ranking vẫn chưa đưa chunk chứa danh sách ưu tiên vào top-3.

**Phân tích A/B và failure cases:**

Với câu 5, khi không lọc metadata, kết quả heading có hai chunk `nha-cong-vu-can-bo` ở top-2; khi lọc, cả hai bị loại. Với câu 2, dữ liệu đáp án có sẵn ở dòng 29 của tài liệu TDTU nhưng nằm gần cuối một chunk 662 ký tự và chỉ đạt khoảng 0,4982, hạng 44; cần tách mục điều kiện đăng ký nhỏ hơn hoặc dùng embedding/reranker phù hợp tiếng Việt.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
- Heading tạo nhiều chunk hơn nhưng giúp kết quả có nhãn điều/mục rõ ràng và dễ giải thích.
- Điểm retrieval bằng nhau không có nghĩa chất lượng chunk giống nhau; cần xem cả khả năng truy vết và failure case.
- Metadata filtering loại nhiễu sai đối tượng, nhưng không thể tự sửa lỗi semantic ranking trong tập kết quả còn lại.

**Bài học rút ra khi so sánh trong nhóm:**

[Cần bổ sung sau khi các thành viên thảo luận/demo. Hiện ba lần chạy Fixed, Recursive và Heading đều đạt 6/10 nhưng thất bại ở các câu khác nhau.]

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu?**

Nhóm sẽ chuẩn hóa các mục dài thành các tiểu mục tự đủ nghĩa, bổ sung metadata `institution` và `topic`, đồng thời thử embedding tiếng Việt tốt hơn hoặc reranker nhẹ. Bộ câu hỏi cũng nên mở rộng để tránh kết luận từ chỉ năm truy vấn.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10 |
| Thiết kế chiến lược (Strategy Design) | 15 / 15 |
| Chất lượng truy xuất (Retrieval Quality) | 6 / 10 |
| Thuyết trình (Demo) | [Cần bổ sung] / 5 |
| **Tổng phần nhóm** | **[Cần bổ sung sau demo] / 40** |
