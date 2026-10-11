# Hướng dẫn chạy website Megan Goh và chat box

Dự án gồm hai phần chạy cùng nhau:

- `website/`: website React của Megan Goh (tư vấn mua bán, cho thuê nhà và logistics).
- `server/` + `widget/`: chat box AI (Claude). Máy chủ chat phục vụ file `widget.js`, website tự nhúng chat box vào góc phải bên dưới.

## Cần cài trước

- Node.js 18 trở lên: <https://nodejs.org>
- Python 3.10 trở lên: <https://www.python.org>
- Khóa API Claude (`ANTHROPIC_API_KEY`): <https://console.anthropic.com>

## Chạy trên máy (mở 2 cửa sổ dòng lệnh)

**Cửa sổ 1: máy chủ chat**

```bash
cd server
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
# mở file .env và dán ANTHROPIC_API_KEY của bạn vào
uvicorn app:app --env-file .env --port 8000
```

**Cửa sổ 2: website**

```bash
cd website
npm install
npm run dev
```

Mở địa chỉ mà lệnh `npm run dev` in ra (thường là <http://localhost:5173>). Chat box nằm ở góc phải bên dưới; nút "Ask a question" cũng mở chat.

## Thay thông tin của Megan

- Email, WhatsApp, WeChat: sửa trong `website/src/config.js` (để trống thì website hiện "Coming soon").
- Danh sách nhà: thay `listings.csv` bằng dữ liệu thật (giữ nguyên tên cột).
- Kiến thức cho chat box: sửa `projects.md`, `buying_faq.md`, hoặc thêm file `.md`/`.txt` vào thư mục `docs/`.

Khởi động lại máy chủ chat sau khi đổi dữ liệu.

## Đưa lên mạng

1. Máy chủ chat: đưa lên Render, Railway hoặc Fly.io bằng `Dockerfile` có sẵn, thêm biến môi trường `ANTHROPIC_API_KEY` và `ALLOWED_ORIGINS` (địa chỉ website).
2. Website: xem phần "Publish online" trong `website/README.md` (GitHub Pages, Vercel hoặc Netlify), đặt `VITE_CHAT_SERVER` là địa chỉ máy chủ chat.

Chi tiết kỹ thuật của chat box: `README.md`.
