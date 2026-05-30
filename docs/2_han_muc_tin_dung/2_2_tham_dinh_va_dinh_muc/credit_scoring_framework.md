# Khung Chấm Điểm Tín Dụng Dòng Tiền (BCTC Cash Flow Scorecard)

Tài liệu này mô tả chi tiết khung chấm điểm tín dụng dựa trên dòng tiền của doanh nghiệp từ Báo cáo tài chính (BCTC) được lập trình trong hệ thống. Khung chấm điểm hỗ trợ hai chế độ: **Chế độ Chuyên gia (Expert Mode)** mặc định và **Chế độ Hiệu chuẩn (Calibrated Mode)** khi có cấu hình tối ưu hóa từ Backtest.

---

## 1. Công Thức Tính Điểm Tổng Hợp

Điểm tín dụng cuối cùng nằm trong khoảng **`[300, 1000]`** điểm, được xác định như sau:

### Chế độ Chuyên gia (Expert Mode - Mặc định)
$$\text{Score} = \text{Base Score} + (\text{Total Points} \times \text{Scaling Factor})$$

*   **Base Score (Điểm cơ bản)**: `600`
*   **Scaling Factor (Hệ số quy đổi)**: `4.0`
*   **Total Points**: Tổng điểm cộng/trừ của 6 chỉ tiêu cốt lõi (tối đa $+100$ điểm, tối thiểu $-90$ điểm). Do đó, điểm thô dao động từ $+400$ đến $-360$ điểm xung quanh mức cơ bản 600.

### Chế độ Hiệu chuẩn (Calibrated Mode)
$$\text{Score} = \text{Base Score} (\text{config}) + \text{Total Points} (\text{weighted/WOE})$$

*   Điểm số của từng chỉ tiêu và điểm cơ bản được lấy động từ cấu hình tối ưu hóa `optimized_scorecard_config.json` sau khi chạy hiệu chuẩn qua `run_backtest.py`.

---

## 2. Bảng Chỉ Tiêu và Thang Điểm (Expert Mode)

Dưới đây là chi tiết 6 chỉ tiêu cốt lõi cấu thành nên hệ thống điểm dòng tiền:

| STT | Chỉ Tiêu Tài Chính | Trọng Số Điểm | Ngưỡng Phân Loại | Diễn Giải & Định Nghĩa Kỹ Thuật |
| :--- | :--- | :---: | :--- | :--- |
| **1** | **Cash-to-Revenue Ratio** <br>*(Tỷ lệ Tiền mặt / Doanh thu)* | **20** | <ul><li>$\ge 95\%$: **+20** *(Xuất sắc)*</li><li>$[80\%, 95\%)$: **+10** *(Khá)*</li><li>$[70\%, 80\%)$: **0** *(Trung bình)*</li><li>$< 70\%$: **-20** *(Yếu - Rủi ro)*</li></ul> | $$\frac{\text{Tiền thu từ bán hàng}}{\text{Doanh thu thuần}}$$ <br> **Chú giải**: Đánh giá hiệu quả thu hồi tiền mặt. Nếu dòng tiền thu không khớp, hệ thống tự động fallback ước tính qua biến động khoản phải thu khách hàng ($\text{Doanh thu} - \Delta\text{Phải thu}$). |
| **2** | **DSCR (CFO-based)** <br>*(Khả năng trả nợ từ CFO)* | **25** | <ul><li>$\ge 2.0x$: **+25** *(Rất an toàn)*</li><li>$[1.5x, 2.0x)$: **+15** *(An toàn)*</li><li>$[1.25x, 1.5x)$: **+8** *(Khá)*</li><li>$[1.0x, 1.25x)$: **-3** *(Rủi ro nhẹ)*</li><li>$[0.75x, 1.0x)$: **-12** *(Căng thẳng dòng tiền)*</li><li>$< 0.75x$: **-25** *(Mất khả năng trả nợ)*</li></ul> | $$\frac{\max(0, \text{CFO TTM})}{\text{Chi phí lãi vay} + \frac{\text{Tổng nợ vay}}{5}}$$ <br> **Chú giải**: Khả năng dòng tiền từ hoạt động kinh doanh (CFO) bao phủ gốc lãi vay dài hạn (ước tính phân bổ nợ gốc đều 5 năm). |
| **3** | **Cash Buffer Days** <br>*(Số ngày đệm tiền mặt)* | **15** | <ul><li>$\ge 90$ ngày: **+15** *(Dồi dào)*</li><li>$[45, 90)$ ngày: **+10** *(An toàn)*</li><li>$[15, 45)$ ngày: **+5** *(Trung bình)*</li><li>$< 15$ ngày: **-10** *(Cạn kiệt - Rủi ro cao)*</li></ul> | $$\frac{\text{Tiền và tương đương tiền}}{\text{Chi phí hoạt động hàng ngày}}$$ <br> *Chi phí hoạt động ngày = (Giá vốn + Chi phí bán hàng + Chi phí quản lý - Khấu hao) / 365*. Nếu chi phí ngày $\le 0$, mặc định nhận điểm tối đa (**999 ngày - Dồi dào**). |
| **4** | **Revenue Volatility** <br>*(Độ biến động Doanh thu)* | **15** | <ul><li>$< 15\%$: **+15** *(Ổn định rất cao)*</li><li>$[15\%, 30\%)$: **+10** *(Ổn định tốt)*</li><li>$[30\%, 45\%)$: **0** *(Trung bình)*</li><li>$\ge 45\%$: **-10** *(Biến động cực lớn)*</li></ul> | $$\text{CV} = \frac{\text{Độ lệch chuẩn Doanh thu (8 Quý)}}{\text{Doanh thu trung bình (8 Quý)}}$$ <br> **Chú giải**: Hệ số biến thiên (CV) của doanh thu trong 8 quý gần nhất. Đánh giá sự ổn định của quy mô kinh doanh. Nếu thiếu dữ liệu quý, sẽ dùng dữ liệu năm thay thế. |
| **5** | **Equity to Debt** <br>*(Tỷ lệ Vốn chủ / Nợ vay)* | **15** | <ul><li>$\ge 1.5x$: **+15** *(Đòn bẩy rất thấp)*</li><li>$[1.0x, 1.5x)$: **+10** *(Đòn bẩy thấp)*</li><li>$[0.5x, 1.0x)$: **+5** *(Đòn bẩy trung bình)*</li><li>$[0.3x, 0.5x)$: **-5** *(Đòn bẩy tương đối cao)*</li><li>$< 0.3x$: **-15** *(Đòn bẩy rất cao)*</li></ul> | $$\frac{\text{Vốn chủ sở hữu}}{\text{Tổng nợ vay có chịu lãi}}$$ <br> **Chú giải**: Đo lường lá chắn bảo vệ của vốn chủ sở hữu đối với các khoản nợ vay. Nợ vay có lãi bao gồm vay ngắn hạn và dài hạn. |
| **6** | **CFO Growth (YoY)** <br>*(Tăng trưởng dòng tiền CFO)* | **10** | <ul><li>$\ge 15\%$: **+10** *(Tăng trưởng tốt)*</li><li>$[0\%, 15\%)$: **+5** *(Tăng trưởng nhẹ)*</li><li>$[-15\%, 0\%)$: **-5** *(Suy giảm nhẹ)*</li><li>$< -15\%$: **-10** *(Suy giảm mạnh)*</li></ul> | $$\frac{\text{CFO}_t - \text{CFO}_{t-1}}{\|\text{CFO}_{t-1}\|}$$ <br> **Chú giải**: Tốc độ tăng trưởng dòng tiền hoạt động kinh doanh hàng năm. Yêu cầu tối thiểu có 2 năm dữ liệu để so sánh, nếu thiếu sẽ nhận **0 điểm**. |

---

## 3. Khung Xếp Hạng & Quyết Định Tín Dụng

Điểm tổng hợp sau khi quy đổi ra thang `[300, 1000]` sẽ được phân loại thành các Hạng (Grade) đi kèm quyết định tín dụng tự động:

| Khoảng Điểm | Xếp Hạng (Grade) | Quyết Định Tín Dụng Áp Dụng | Màu Sắc Chỉ Thị |
| :--- | :--- | :--- | :---: |
| **$\ge 850$** | **Grade A+** | **Auto-approve**: Phê duyệt tự động, áp dụng chính sách lãi suất ưu đãi. | **Xanh lá sáng** (`#2ecc71`) |
| **$[700, 850)$** | **Grade A** | **Auto-approve**: Phê duyệt tự động với điều khoản lãi suất thông thường. | **Xanh lá** (`#2ecc71`) |
| **$[600, 700)$** | **Grade B** | **Conditional Approve**: Phê duyệt tự động đi kèm điều khoản bổ sung về kiểm soát dòng tiền/tài khoản thu hộ. | **Xanh dương** (`#3498db`) |
| **$[500, 600)$** | **Grade C** | **Manual Review**: Chuyển phê duyệt tay bắt buộc từ Hội đồng tín dụng, đồng thời áp dụng mức giảm hạn mức (Haircut) tối thiểu 20%. | **Màu cam** (`#f39c12`) |
| **$< 500$** | **Grade D** | **Reject (Từ chối)**: Từ chối cấp hạn mức tín dụng tự động do rủi ro dòng tiền rất cao. | **Màu đỏ** (`#e74c3c`) |

---

## 4. Ghi Chú và Chốt Chặn Bổ Sung (Circuit Breakers)

Hệ thống kết hợp các chốt chặn cứng độc lập với điểm số để kiểm soát rủi ro hệ thống:
1. **AI Circuit Breaker**: Nếu mô hình XGBoost dự báo xác suất phá sản (PD) $> 55.0\%$ hoặc mức rủi ro (Risk Level) đạt cấp độ 4 (Nguy cấp), hồ sơ sẽ bị **Từ chối thẳng** bất chấp Điểm số dòng tiền đạt mức nào.
2. **ICR Circuit Breaker**: Nếu Khả năng trả lãi vay (Interest Coverage Ratio - ICR) từ dòng tiền $< 1.0x$, hồ sơ sẽ bị chuyển thành **Từ chối cấp hạn mức**.
3. **CFO Circuit Breaker**: Nếu dòng tiền hoạt động kinh doanh lũy kế 4 quý gần nhất ($\text{CFO TTM}$) $\le 0$, hồ sơ bị **Từ chối** với lý do *"Không có thặng dư dòng tiền để trả nợ mới"*.
4. **Leverage Cap**: Đảm bảo đòn bẩy an toàn sau khi cấp khoản vay mới:
   $$\text{Vốn chủ sở hữu} / (\text{Tổng nợ hiện tại} + \text{Hạn mức mới}) \ge 15\%$$
   If vượt quá, hạn mức mới sẽ bị cắt giảm (Haircut đòn bẩy) tương ứng.
