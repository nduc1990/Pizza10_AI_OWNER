# Pizza10_AI_OWNER

Project Python read-only để làm AI Reporting / AI Owner Dashboard cho chuỗi Pizza 10 Điểm.

## Mục tiêu

- Lấy dữ liệu POS365 qua API read-only.
- Tổng hợp KPI bằng Python.
- Gửi dữ liệu tổng hợp sang OpenAI API để viết nhận xét quản trị.
- Gửi báo cáo về Telegram cho chủ cửa hàng.

Project này không tạo phiếu, không sửa dữ liệu POS365, không dùng browser automation.

## Cài đặt

```powershell
pip install -r requirements.txt
```

## Tạo `.env`

Copy `.env.example` thành `.env`, sau đó điền thông tin thật:

```text
POS365_BASE_URL=https://pizza10.pos365.vn
POS365_USERNAME=
POS365_PASSWORD=

OPENAI_API_KEY=
AI_MODEL=gpt-4o-mini

TELEGRAM_BOT_TOKEN=
TELEGRAM_OWNER_CHAT_ID=
```

Lưu ý: `.env` chứa mật khẩu và token nên không được commit. File này đã nằm trong `.gitignore`.

## Chạy báo cáo

```powershell
python daily_job.py
python daily_job.py --date 2026-06-20
python daily_job.py --date yesterday
```

Nếu thiếu `OPENAI_API_KEY`, phần AI sẽ hiển thị `AI chưa cấu hình`.

Nếu thiếu `TELEGRAM_BOT_TOKEN` hoặc `TELEGRAM_OWNER_CHAT_ID`, báo cáo sẽ được in ra console thay vì crash.

## Gửi Telegram

Tạo bot Telegram, lấy `TELEGRAM_BOT_TOKEN`, lấy `TELEGRAM_OWNER_CHAT_ID`, rồi điền vào `.env`.
Khi chạy `daily_job.py`, hệ thống sẽ gửi nội dung owner report qua Telegram Bot API.

## Endpoint POS365 đang dùng

- `/api/json/reply/Authenticate`
- `/api/json/reply/ProductList?Take=1000`
- `/api/json/reply/OrderList?Take=1000`
- `/api/json/reply/OrderGetDetail?OrderId=<id>`

Tất cả endpoint trên chỉ dùng để đọc dữ liệu.
