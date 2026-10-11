# Chat box tư vấn bất động sản

Chat box AI (dùng Claude) để tư vấn bất động sản, **nhúng được vào bất kỳ website cá nhân nào chỉ bằng một dòng `<script>`**.

- Tìm tin đăng theo điều kiện (khu vực, giá, số phòng ngủ, pháp lý...) và hiện dạng thẻ.
- Trả lời về dự án và thủ tục mua nhà bằng **RAG**: mỗi câu hỏi được tìm các đoạn liên quan trong tài liệu của bạn (`du_an.md`, `hoi_dap_mua_nha.md`, thư mục `tai_lieu/`) rồi mới đưa cho Claude, nên không bịa thông tin.
- Gõ không dấu vẫn hiểu ("thu tuc sang ten", "q7", "thu duc").
- Chữ hiện dần (streaming), giao diện tự co giãn trên điện thoại, CSS không ảnh hưởng website chủ.

```
server/      Backend FastAPI: gọi Claude, giữ API key bí mật
widget/      property-chat.js — file JS nhúng vào website
demo/        Trang web mẫu đã nhúng chat box
du_an.md, hoi_dap_mua_nha.md, tin_dang.csv   Dữ liệu (thay bằng dữ liệu thật của bạn)
tai_lieu/    Bỏ thêm file .md/.txt vào đây, chat box tự tìm trong đó
tests/       Kiểm thử tự động (dùng Claude giả lập, không tốn tiền API)
rag_chatbot.ipynb                            Notebook học tập RAG (giữ nguyên)
```

## Chạy thử trên máy

```bash
cd server
pip install -r requirements.txt
cp .env.example .env        # rồi dán ANTHROPIC_API_KEY vào file .env
uvicorn app:app --env-file .env --reload --port 8000
```

Mở <http://localhost:8000> để xem trang demo có chat box.

## Nhúng vào website cá nhân

Sau khi đưa server lên mạng (xem phần Triển khai), dán đoạn sau vào trước thẻ `</body>` của website:

```html
<script src="https://chat.ten-mien-cua-ban.com/widget.js"
        data-title="Tư vấn nhà đất"
        data-color="#0f766e"
        data-contact="tel:0900000000"
        defer></script>
```

Dùng được với HTML thuần, WordPress (plugin chèn code header/footer), Wix/Webflow (custom code), Next.js/React (`<Script>`)...

### Tuỳ chọn

| Thuộc tính | Ý nghĩa | Mặc định |
|---|---|---|
| `data-api` | Địa chỉ server nếu khác nơi chứa `widget.js` | lấy theo `src` |
| `data-title` / `data-subtitle` | Tiêu đề, dòng phụ | "Tư vấn bất động sản" |
| `data-color` | Màu chủ đạo | `#0f766e` |
| `data-position` | `right` hoặc `left` | `right` |
| `data-greeting` | Lời chào đầu tiên | có sẵn |
| `data-suggestions` | Câu hỏi gợi ý, cách nhau bằng `\|` | 3 câu mẫu |
| `data-contact` / `data-contact-label` | Link liên hệ (`tel:`, Zalo, Messenger) | ẩn |
| `data-open` | `true` để mở sẵn khi tải trang | `false` |

### Điều khiển từ website

```js
PropertyChat.open();
PropertyChat.close();
PropertyChat.ask("Có căn nào dưới 2 tỷ không?"); // mở và hỏi luôn
```

Ví dụ nút "Hỏi về căn này" trên trang tin đăng: `onclick="PropertyChat.ask('Cho mình xem chi tiết tin T003')"`.

## Chat box trả lời thế nào (RAG)

1. **Tìm (Retrieval)**: tài liệu được cắt thành đoạn theo từng mục `##` (mục dài được cắt nhỏ). Khi khách hỏi, server tìm các đoạn liên quan nhất bằng BM25, có bỏ dấu tiếng Việt và ưu tiên cụm hai từ ("sổ hồng", "đặt cọc"). Câu hỏi nối tiếp ngắn ("còn phí quản lý thì sao?") được ghép với câu trước để tìm đúng.
2. **Bổ sung (Augmented)**: các đoạn tìm được gắn kèm câu hỏi gửi cho Claude.
3. **Trả lời (Generation)**: Claude chỉ trả lời dựa trên các đoạn đó. Nếu chưa đủ, Claude tự gọi công cụ `tra_cuu_tai_lieu` để tìm lại với câu hỏi khác; tin đăng thì gọi `tim_tin_dang` để lọc chính xác theo giá, khu vực, số phòng...

Cách tìm này chạy thuần Python, không cần tải model embedding, nên server nhẹ và chạy được trên gói hosting miễn phí. Khi tài liệu lên tới hàng nghìn trang có thể thay bằng tìm kiếm ngữ nghĩa như trong `rag_chatbot.ipynb` (chỉ cần sửa `server/kho_tai_lieu.py`).

## Thay dữ liệu thật

- `tin_dang.csv`: giữ nguyên tên cột, thêm/bớt dòng tuỳ ý. Mở/lưu bằng Excel cũng được; giá viết `3.2` hay `3,2` đều hiểu, dòng sai định dạng bị bỏ qua và in cảnh báo.
- `du_an.md`, `hoi_dap_mua_nha.md`: viết tự do theo mục `##`, mỗi mục một chủ đề.
- Tài liệu khác: bỏ file `.md`/`.txt` vào thư mục `tai_lieu/` (xem `tai_lieu/README.md`).
- Khởi động lại server sau khi sửa dữ liệu. `GET /api/health` cho biết số tin và số đoạn tài liệu đã đọc.

## Cấu hình server (`server/.env`)

| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `ANTHROPIC_API_KEY` | API key Claude (bắt buộc, chỉ để ở server) | — |
| `CLAUDE_MODEL` | Model | `claude-sonnet-5-5` |
| `CLAUDE_EFFORT` | Mức suy nghĩ `low`/`medium`/`high` | `low` |
| `ALLOWED_ORIGINS` | Website được phép nhúng, cách nhau bằng dấu phẩy | `*` |
| `RATE_LIMIT_PER_MINUTE` | Số câu hỏi tối đa mỗi phút cho mỗi IP | `15` |
| `RAG_SO_DOAN` | Số đoạn tài liệu đưa cho Claude mỗi câu hỏi | `4` |

Khi chạy thật nên đặt `ALLOWED_ORIGINS` đúng tên miền của bạn để website khác không dùng ké API key.
Server bật sẵn `fallbacks: "default"`: nếu bộ lọc an toàn từ chối nhầm, API tự trả lời bằng model dự phòng.

## Kiểm thử

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium   # lần đầu
python -m pytest tests
```

Bộ kiểm thử chạy server thật với một Claude giả lập nên không cần API key: lọc tin đăng, tìm tài liệu (có dấu/không dấu), API (lỗi Claude, mất kết nối, từ chối, sai tham số, giới hạn lượt hỏi, CORS, thiếu API key) và widget trong Chromium (máy tính, điện thoại, nhúng vào website khác tên miền, chống chèn mã HTML). GitHub Actions tự chạy khi có pull request.

## Triển khai

Có sẵn `Dockerfile`, chạy được trên Render, Railway, Fly.io, Google Cloud Run...

```bash
docker build -t property-chat .
docker run -p 8000:8000 --env-file server/.env property-chat
```

Trên các dịch vụ trên: trỏ tới repo, chọn build bằng Dockerfile, thêm biến môi trường `ANTHROPIC_API_KEY` và `ALLOWED_ORIGINS`. Server phải chạy HTTPS nếu website của bạn dùng HTTPS.

## API

`POST /api/chat` nhận `{"messages": [{"role": "user", "content": "..."}]}` (lịch sử hội thoại, tối đa 20 tin) và trả về Server-Sent Events:
`text` (từng đoạn chữ), `listings` (danh sách tin đăng để vẽ thẻ), `error`, `done`.
`GET /api/health` để kiểm tra server.
