# CHANGELOG

Tất cả các thay đổi quan trọng của dự án Pizza10_OS sẽ được ghi lại tại đây.

Dự án tuân theo Semantic Versioning.

---

## [v1.2-inventory-api] - 2026-06-28

Added:
- POS365 Inventory API integration via GET /api/products
- Inventory value
- Low stock detection
- Overstock detection
- Stockout risk detection
- Inventory health score

---

# [v1.0] - 2026-06-27

## 🎉 First Stable Release

Phiên bản MVP đầu tiên của Pizza10_OS.

## Added

### POS365 Integration
- Kết nối POS365 read-only.
- Lấy dữ liệu bán hàng.
- Lấy chi tiết đơn hàng.
- Lấy thông tin sản phẩm.
- Không ghi hoặc thay đổi dữ liệu POS365.

### Sales Intelligence
- Doanh thu.
- Số đơn.
- AOV.
- So sánh với ngày trước.
- Xu hướng 7 ngày.
- Xu hướng 30 ngày.
- Phân tích theo giờ.
- Peak Hour.
- Dead Hour.

### Product Intelligence
- Product Performance.
- Revenue Ranking.
- Quantity Ranking.
- Revenue Share.
- ABC Analysis.
- Pareto Analysis.
- Product Trend.
- Product Dependency.
- Slow Moving Products.
- Menu Health Score.

### Finance Intelligence Framework
- Cash Position.
- Supplier Health.
- Purchase Trend.
- Cash Health Score.

### Inventory Intelligence Framework
- Inventory Snapshot.
- Stock Health.
- Low Stock.
- Overstock.
- Stockout Risk.
- Inventory Days.

### Rule Engine
- Rule Engine v2 với HIGH / MEDIUM / LOW.
- Rule cho doanh thu, số đơn, peak hour, dead shift, supplier health, menu dependency, inventory health.

### Decision Engine
- Tổng hợp rule.
- Tính Priority Score.
- Xếp hạng vấn đề.
- Gán Owner.
- Sinh Decision Package.

### AI Advisor
- Phân tích Decision Package.
- Sinh Executive Summary.
- Sinh đề xuất hành động.
- Không gửi dữ liệu nhạy cảm.
- Fallback khi chưa cấu hình OpenAI.
- Xử lý lỗi quota/API an toàn.

### Owner Brief
- Báo cáo ngắn cho chủ doanh nghiệp.
- Có kết quả kinh doanh, ưu tiên hôm nay, cảnh báo chính, AI Advisor.
- Mục tiêu đọc trong 30 giây.

### Telegram Integration
- Gửi Owner Brief lên Telegram.
- Hỗ trợ --brief.
- Hỗ trợ --send.
- Không crash khi thiếu cấu hình.

### Git
- Khởi tạo Git repository.
- Commit đầu tiên.
- Tag v1.0.
- Push GitHub thành công.

## Security
- Không commit .env.
- Không commit data/.
- Không commit .venv/.
- Không gửi token hoặc mật khẩu sang AI.

## Known Limitations
- Chưa có dữ liệu thật cho phiếu thu.
- Chưa có dữ liệu thật cho phiếu chi.
- Chưa có dữ liệu thật cho dòng tiền.
- Chưa có dữ liệu thật cho nhập hàng.
- Chưa có dữ liệu thật cho tồn kho chi tiết.

Finance và Inventory đã có framework, sẽ kết nối nguồn dữ liệu thật ở các phiên bản sau.

## Next Version - v1.1
Dự kiến:
- Scheduler chạy tự động hằng ngày.
- Phân tích xu hướng nhiều ngày.
- Phát hiện bất thường.
- Dự báo doanh thu.
- Dự báo nhu cầu nhập hàng.
- Inventory Intelligence nâng cao.
- Decision Engine v2.
