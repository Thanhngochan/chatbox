# Hướng dẫn chạy website Megan Goh và chat box

Dự án gồm hai phần chạy cùng nhau:

- `website/`: website React của Megan Goh (tư vấn mua bán, cho thuê nhà và logistics).
- `server/` + `widget/`: chat box AI (Claude). Máy chủ chat phục vụ file `widget.js`, website tự nhúng chat box vào góc phải bên dưới.

## Cần cài trước

- Node.js 18 trở lên: <https://nodejs.org>
- Python 3.10 trở lên: <https://www.python.org>
- Khóa API Claude (`ANTHROPIC_API_KEY`): <https://console.anthropic.com>

## Chạy trên máy: một lệnh (macOS)

1. Mở Terminal, vào thư mục dự án (thư mục có file `start.sh`), ví dụ:
   ```bash
   cd ~/Desktop/personal_web/megan-goh-website
   ```
2. Chạy:
   ```bash
   ./start.sh
   ```
3. Lần đầu, lệnh sẽ tạo file `server/.env` rồi dừng lại. Mở file đó (`open -e server/.env`), thay `sk-ant-...` ở dòng `ANTHROPIC_API_KEY=` bằng khóa API Claude của bạn, lưu lại, rồi chạy lại `./start.sh`.
   (Nếu báo `permission denied`, chạy `bash start.sh` thay cho `./start.sh`.)
4. Khi thấy dòng `Local: http://localhost:5173/`, mở địa chỉ đó trong trình duyệt. Nút chat tròn màu xanh nằm ở góc phải bên dưới.

Nhấn `Ctrl+C` trong Terminal để tắt cả hai.

## Chạy từng phần (nếu không dùng start.sh)

Cửa sổ Terminal 1, máy chủ chat (để cửa sổ này mở suốt):

```bash
cd ~/Desktop/personal_web/megan-goh-website/server
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # rồi dán ANTHROPIC_API_KEY vào file .env
.venv/bin/python -m uvicorn app:app --env-file .env --port 8000
```

Cửa sổ Terminal 2, website (lưu ý `cd` vào thư mục `website` từ thư mục gốc, không phải từ `server`):

```bash
cd ~/Desktop/personal_web/megan-goh-website/website
npm install
npm run dev
```

## Không thấy chat box?

- Chat box chỉ hiện khi máy chủ chat đang chạy. Mở <http://localhost:8000/api/health> trong trình duyệt: phải thấy chữ `"ok"`. Nếu không mở được, máy chủ chat chưa chạy; xem lỗi ở cửa sổ Terminal của máy chủ.
- `command not found: pip` hoặc `uvicorn`: dùng các lệnh `.venv/bin/...` như trên, hoặc dùng `./start.sh`.
- Chat box hiện nhưng trả lời "Có lỗi khi kết nối trợ lý": khóa API trong `server/.env` sai hoặc hết hạn mức.
- Trên trình duyệt, nhấn `Cmd+Option+J` để mở Console: nếu có dòng `Chat box: could not load ...` thì máy chủ chat chưa chạy.

## Thay thông tin của Megan

- Email, WhatsApp, WeChat: sửa trong `website/src/config.js` (để trống thì website hiện "Coming soon").
- Danh sách nhà: thay `listings.csv` bằng dữ liệu thật (giữ nguyên tên cột).
- Kiến thức cho chat box: sửa `projects.md`, `buying_faq.md`, hoặc thêm file `.md`/`.txt` vào thư mục `docs/`.

Khởi động lại máy chủ chat sau khi đổi dữ liệu.

## Đưa lên mạng

1. Máy chủ chat: đưa lên Render, Railway hoặc Fly.io bằng `Dockerfile` có sẵn, thêm biến môi trường `ANTHROPIC_API_KEY` và `ALLOWED_ORIGINS` (địa chỉ website).
2. Website: xem phần "Publish online" trong `website/README.md` (GitHub Pages, Vercel hoặc Netlify), đặt `VITE_CHAT_SERVER` là địa chỉ máy chủ chat.

Chi tiết kỹ thuật của chat box: `README.md`.
