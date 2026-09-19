# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Thái Hữu Tuấn

**MSSV:** 2A202602465

**Nhóm:** [Cần bổ sung]

**Ngày:** 19/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**

Hai vector embedding hướng gần giống nhau, vì vậy hai đoạn văn có khả năng gần nhau về ngữ nghĩa. Giá trị càng gần 1 thì mức tương đồng theo hướng càng cao.

**Ví dụ có độ tương tự CAO:**
- Câu A: Ký túc xá đóng cửa lúc 22 giờ.
- Câu B: Sinh viên phải trở về khu nội trú trước 22:00.
- Tại sao tương đồng: Cả hai cùng diễn đạt giới hạn thời gian ra vào khu nội trú.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Ký túc xá cấm gây ồn sau 22:30.
- Câu B: Hồ sơ cần giấy xác nhận cư trú.
- Tại sao khác: Hai câu thuộc hai chủ đề khác nhau, một câu về nội quy sinh hoạt và một câu về hồ sơ đăng ký.

**Tại sao độ tương tự cosine được ưu tiên hơn khoảng cách Euclid cho text embeddings?**

Cosine tập trung vào hướng của vector, tức mẫu ngữ nghĩa, và ít bị ảnh hưởng bởi độ lớn vector. Khoảng cách Euclid phụ thuộc cả hướng lẫn độ lớn nên có thể đánh giá hai văn bản cùng nghĩa là xa nhau chỉ vì chuẩn vector khác nhau.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10.000 ký tự, `chunk_size=500`, `overlap=50`. Bao nhiêu chunks?**

`step = 500 - 50 = 450`. Số chunk là `ceil((10.000 - 500) / 450) + 1 = 23`.

**Nếu độ chồng chéo tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**

Khi `overlap=100`, `step=400`, nên số chunk là `ceil(9.500 / 400) + 1 = 25`. Overlap lớn hơn giúp giữ ngữ cảnh ở ranh giới chunk, nhưng làm tăng số vector, bộ nhớ và thời gian truy xuất.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk` — hướng tiếp cận:**

Tôi dùng regex `(?:(?<=[.!?])[ \t]+|(?<=\.)\r?\n+)` để tách sau dấu `.`, `!`, `?` khi có khoảng trắng, hoặc sau dấu chấm ở cuối dòng. Các câu rỗng bị loại bỏ, khoảng trắng được chuẩn hóa, rồi các câu được gom theo `max_sentences_per_chunk`; văn bản rỗng trả về danh sách rỗng.

**`RecursiveChunker.chunk` / `_split` — hướng tiếp cận:**

Thuật toán thử các dấu phân cách theo thứ tự ưu tiên `\n\n`, `\n`, `. `, khoảng trắng, rồi ký tự. Nếu đoạn đã không vượt `chunk_size` thì trả về ngay; nếu không còn separator phù hợp thì cắt cứng theo kích thước. Các mảnh nhỏ được ghép lại đến sát giới hạn để giảm số chunk nhưng vẫn ưu tiên giữ ranh giới đoạn, dòng và câu.

**`HeadingChunker.chunk` — chiến lược cá nhân:**

Tôi tách tài liệu tại tiêu đề Markdown và các tiêu đề dạng văn bản pháp quy như `Điều`, `Chương` hoặc số La Mã. Tiêu đề được lặp lại khi một mục dài phải chia tiếp bằng `RecursiveChunker`, nhờ đó mỗi chunk vẫn mang tên điều/mục để dễ hiểu và truy vết.

### Lớp EmbeddingStore

**`add_documents` + `search` — hướng tiếp cận:**

Mỗi `Document` được chuyển thành một record gồm id, nội dung, metadata và embedding rồi lưu trong danh sách trong RAM. Khi tìm kiếm, query được embed một lần, tính tích vô hướng với các embedding đã chuẩn hóa, sắp xếp giảm dần theo score và lấy `top_k` kết quả.

**`search_with_filter` + `delete_document` — hướng tiếp cận:**

Metadata được lọc trước khi tính similarity để chỉ xếp hạng các record đúng phạm vi, vừa giảm tính toán vừa tránh tài liệu sai đối tượng. Khi xóa, store loại toàn bộ chunk có `metadata.doc_id` trùng với id tài liệu và trả về `True` nếu kích thước collection giảm.

### Tác tử KnowledgeBaseAgent

**`answer` — hướng tiếp cận:**

Agent lấy `top_k` chunk, đánh số từng nguồn rồi ghép thành phần `Context`. Prompt yêu cầu LLM chỉ dùng ngữ cảnh được cung cấp, trả lời không tìm thấy nếu thiếu dữ liệu và trích dẫn bằng số như `[1]`; nếu retrieval rỗng thì trả về thông báo ngay mà không gọi LLM.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

### Kết Quả Kiểm Thử (Test Results)

```text
platform win32 -- Python 3.11.15, pytest-9.1.1
rootdir: D:\Projects\Lab Projects\K4A-DAY07-ThaiHuuTuan-2A202602465
collected 42 items

tests/test_solution.py .......................................... [100%]

============================= 42 passed in 0.11s =============================
```

Kết quả đầy đủ được lưu trong `pytest_output.txt`.

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-------|-------|---------|---------------|-------|
| 1 | Ký túc xá đóng cửa lúc 22 giờ. | Sinh viên phải trở về khu nội trú trước 22:00. | Cao | 0,4764 | Có |
| 2 | Sinh viên cần nộp bản sao căn cước. | Hồ sơ đăng ký nội trú bao gồm CCCD. | Cao | 0,3364 | Không hoàn toàn |
| 3 | Sinh viên vắng mặt quá một ngày phải báo ban quản lý. | Ký túc xá có nhiều cây xanh và khu sinh hoạt chung. | Thấp | 0,2761 | Có |
| 4 | Người khuyết tật được ưu tiên xét chỗ ở. | Sinh viên mồ côi thuộc nhóm ưu tiên nội trú. | Cao | 0,4900 | Có |
| 5 | Ký túc xá cấm gây ồn sau 22:30. | Hồ sơ cần giấy xác nhận cư trú. | Thấp | 0,1012 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**

Cặp 2 thấp hơn dự đoán dù “căn cước” và “CCCD” gần như cùng nghĩa. Điều này cho thấy mô hình embedding nhẹ có thể xử lý chưa tốt từ viết tắt tiếng Việt; similarity còn chịu ảnh hưởng của cách diễn đạt và ngữ cảnh chứ không chỉ ý nghĩa mà con người nhận ra.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Thiết lập: `HeadingChunker`, `chunk_size=800`, embedding `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 8 tài liệu và 190 chunks.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? | Câu trả lời của Agent (tóm tắt) |
|---|-----------------|--------------------------------------|------------|---------------------|----------------------------------|
| 1 | Ký túc xá mở cửa và đóng cửa lúc mấy giờ? | `ktx-quy-dinh-sinh-hoat-ung-xu#3`: Điều 1 ghi giờ mở 05:00, đóng 22:00 | 0,7163 | Có | Benchmark chỉ đo retrieval, không gọi LLM; top-1 chứa đủ đáp án 05:00–22:00. |
| 2 | Sinh viên đang bị kỷ luật từ mức nào thì không được đăng ký ở Ký túc xá TDTU? | `quy-che-hssv-noi-tru#0`: chỉ là tiêu đề Thông tư 27/2011 | 0,7555 | Không | Không sinh câu trả lời; top-3 không có điều kiện “từ mức khiển trách trở lên”. |
| 3 | Sinh viên vắng mặt tại khu nội trú quá bao lâu thì phải báo Ban quản lý? | `quy-che-hssv-noi-tru#24`: Điều 6, vắng quá 1 ngày phải báo | 0,7544 | Có | Benchmark không gọi LLM; top-1 chứa đủ đáp án “quá 1 ngày”. |
| 4 | Hồ sơ đăng ký nội trú TDTU cần những giấy tờ cơ bản nào? | `ktx-tdtu-dang-ky-noi-tru#4`: phiếu đăng ký, bản sao CCCD/CC và giấy minh chứng | 0,6801 | Có | Benchmark không gọi LLM; top-1 chứa danh sách giấy tờ cơ bản. |
| 5 | Những đối tượng nào được ưu tiên xét chỗ ở? | `ktx-noi-quy#10`: nghĩa vụ trật tự, vệ sinh KTX | 0,5520 | Không | Không sinh câu trả lời; top-3 sau lọc `audience=student` vẫn chưa có mục ưu tiên. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 3 / 5

**Phân tích lỗi nổi bật:**

Ở câu 2, đáp án thực sự có trong `ktx-tdtu-dang-ky-noi-tru.md` và nằm ở chunk `ktx-tdtu-dang-ky-noi-tru#3`, nhưng chỉ xếp hạng 44 với score khoảng 0,4982. Câu trả lời nằm gần cuối một chunk dài chứa nhiều điều kiện, vì vậy MiniLM ưu tiên các chunk có từ ngữ chung về “kỷ luật” và “ký túc xá” hơn; đây là lỗi xếp hạng/chunking, không phải corpus thiếu dữ liệu.

Ở câu 5, filter `audience=student` loại được tài liệu nhà công vụ dành cho cán bộ khỏi kết quả, nhưng chunk đúng `quy-che-hssv-noi-tru#19` vẫn không vào top-3. Filter cải thiện đúng phạm vi đối tượng nhưng không thay thế được chất lượng semantic ranking.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**

[Cần bổ sung sau demo]

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 6 / 10 |
| **Tổng phần cá nhân** | **56 / 60** |
