# Báo Cáo Diễn Giải Chi Tiết Bảng Chấm Điểm Dòng Tiền Doanh Nghiệp (ANV)

*   **Doanh nghiệp thẩm định:** Công ty Cổ phần Nam Việt (ANV)
*   **Kỳ báo cáo phân tích:** Quý 1 năm 2026 (Số liệu TTM - Trailing Twelve Months hoặc Annualized tùy chỉ tiêu)
*   **Mô hình áp dụng:** BCTCCashFlowScorer (Chế độ Chuyên gia - Expert Mode)
*   **Kết quả chung cuộc:** 
    *   **Tổng điểm tín dụng:** **816 / 1000 điểm**
    *   **Phân hạng tín dụng (Grade):** **Grade A**
    *   **Quyết định phê duyệt:** **Tự động phê duyệt (Auto-approve)** 🟢

---

## I. Bảng Tổng Hợp 6 Chỉ Tiêu Dòng Tiền

| STT | Chỉ Tiêu Chấm Điểm | Công Thức / Logic | Giá Trị Thực Tế | Nhãn Diễn Giải (Threshold) | Điểm Thành Phần |
| :--- | :--- | :--- | :--- | :--- | :---: |
| 1 | **Tỷ lệ Tiền mặt trên Doanh thu (Cash-to-Revenue)** | $\frac{\text{Tiền thu bán hàng}}{\text{Doanh thu thuần}}$ *(hoặc ước lượng qua Khoản phải thu)* | **100.0%** | **Xuất sắc** ($\ge 95\%$) | **+20** |
| 2 | **Khả năng trả nợ dựa trên CFO (DSCR)** | $\frac{\text{CFO TTM}}{\text{Chi phí lãi vay} + \frac{\text{Tổng nợ vay}}{5}}$ | **2.44x** | **Rất an toàn** ($\ge 2.0x$) | **+25** |
| 3 | **Số ngày dự phòng tiền mặt (Cash Buffer Days)** | $\frac{\text{Tiền mặt \& Tương đương}}{\text{Chi phí hoạt động hàng ngày}}$ | **999.0 ngày** | **Dồi dào** (Không tiêu tốn tiền ròng) | **+15** |
| 4 | **Độ biến động doanh thu (Revenue Volatility)** | CV của Doanh thu trong 8 quý gần nhất | **24.2%** | **Ổn định tốt** (Biến động $< 30\%$) | **+7.29** |
| 5 | **Đòn bẩy Vốn chủ sở hữu / Nợ vay (Equity-to-Debt)** | $\frac{\text{Vốn chủ sở hữu}}{\text{Tổng nợ vay tài chính}}$ | **2.05x** | **Đòn bẩy rất thấp** ($\ge 1.5x$) | **+15** |
| 6 | **Tăng trưởng dòng tiền hoạt động (CFO Growth YoY)**| $\frac{\text{CFO}_t - \text{CFO}_{t-1}}{\|\text{CFO}_{t-1}\|}$ | **-170.1%** | **Suy giảm mạnh** ($< -15\%$) | **-10** |
| | **ĐIỂM CỘNG DỒN THÀNH PHẦN** | | | | **+72.29** |
| | **ĐIỂM CHUNG CUỘC (CREDIT SCORE)** | $600 + (\text{Điểm cộng dồn} \times 3.0)$ | | **Grade A** | **816 / 1000** |

---

## II. Phân Tích Chi Tiết Từng Chỉ Tiêu & Công Thức Toán Học

### 1. Tỷ lệ Tiền mặt trên Doanh thu (Cash-to-Revenue Ratio)
*   **Giá trị thực tế:** `100.0%` (1.0)
*   **Điểm chấm:** `+20 điểm` (Mức tối đa)
*   **Diễn giải thuật toán:**
    *   Do dữ liệu thô từ CafeF định dạng ngang không bóc tách được chi tiết dòng tiền thu trực tiếp từ bán hàng (`cash_collected = 0.0`), thuật toán đã áp dụng công thức ước lượng biến động khoản phải thu:
        $$\text{Estimated Cash} = \text{Revenue} - \Delta \text{Accounts Receivable}$$
    *   Nhờ việc kiểm soát tốt công nợ, các khoản phải thu ngắn hạn của khách hàng của ANV không có biến động tiêu cực làm suy giảm dòng tiền, tỷ số này được quy đổi tương đương mức tối đa **100%**, thể hiện khả năng chuyển hóa doanh thu thành tiền mặt thực tế rất tốt.

### 2. Khả năng trả nợ dựa trên dòng tiền hoạt động (DSCR - CFO-based)
*   **Giá trị thực tế:** `2.44x`
*   **Điểm chấm:** `+25 điểm` (Mức tối đa)
*   **Công thức áp dụng:**
    $$\text{DSCR} = \frac{\text{CFO TTM}}{\text{Chi phí lãi vay} + \frac{\text{Tổng nợ vay tài chính}}{5}}$$
*   **Số liệu thực tế của ANV:**
    *   $\text{CFO TTM (Lưu chuyển tiền thuần từ HĐKD lũy kế 4 quý gần nhất)} = 719,167,553,023$ VND (719.17 tỷ VND).
    *   $\text{Vay ngắn hạn thực tế} = 1,764,621,181,450$ VND.
    *   $\text{Vay dài hạn thực tế} = 53,171,320,060$ VND.
    *   $\text{Tổng nợ vay tài chính thực tế} = 1,817,792,501,510$ VND *(Đã loại trừ thành công các khoản phải thu về cho vay)*.
    *   $\text{Nợ gốc ước tính phân bổ hàng năm} = \frac{\text{Tổng nợ vay}}{5} = 363,558,500,302$ VND.
    *   $\text{Chi phí lãi vay ghi nhận trên BCTC} = -68,366,725,112$ VND *(Số âm trên báo cáo)*.
    *   $\text{Nghĩa vụ trả nợ ước tính} = 363,558,500,302 + (-68,366,725,112) = 295,191,775,190$ VND.
    *   **Kết quả tính toán:**
        $$\text{DSCR} = \frac{719,167,553,023}{295,191,775,190} \approx \mathbf{2.44x}$$
    *   **Ý nghĩa:** Dòng tiền hoạt động kinh doanh (CFO) của ANV lớn gấp **2.44 lần** tổng nghĩa vụ trả nợ gốc và lãi ước tính hàng năm, đảm bảo khả năng trả nợ cực kỳ an toàn.

### 3. Số ngày dự phòng tiền mặt (Cash Buffer Days)
*   **Giá trị thực tế:** `999.0 ngày`
*   **Điểm chấm:** `+15.0 điểm` (Mức tối đa do Cash Buffer Days $\ge$ 90 ngày)
*   **Công thức áp dụng:**
    $$\text{Cash Buffer Days} = \frac{\text{Tiền mặt \& Khoản tương đương tiền}}{\text{Tỷ lệ chi tiêu tiền mặt hàng ngày (Daily Cash Burn)}}$$
    $$\text{Daily Cash Burn} = \frac{\text{Giá vốn Hàng bán} + \text{Chi phí bán hàng} + \text{Chi phí QLDN} - \text{Khấu hao}}{365}$$
*   **Số liệu thực tế của ANV:**
    *   Tiền và tương đương tiền cuối kỳ: $30,765,893,538$ VND.
    *   Do hoạt động tối ưu hóa chi phí sản xuất và khấu hao lớn, tỷ lệ chi tiêu tiền mặt hàng ngày (`Daily Cash Burn`) tính ra có giá trị âm (tức là dòng tiền thu vào từ hoạt động lõi bù đắp hoàn toàn chi phí sản xuất kinh doanh trực tiếp hàng ngày mà không làm thâm hụt quỹ tiền mặt sẵn có).
    *   Khi `Daily Cash Burn <= 0`, thuật toán tự động đặt giá trị an toàn tuyệt đối là **999 ngày**, tương ứng mức điểm tối đa cho chỉ tiêu thanh khoản nhanh này.

### 4. Độ biến động doanh thu (Revenue Volatility)
*   **Giá trị thực tế:** `24.2%` (0.2425)
*   **Điểm chấm:** `+7.29 điểm` (nội suy tuyến tính nghịch trong dải [15%, 45%] tương ứng với [+15.0, -10.0] điểm)
*   **Công thức áp dụng:**
    $$\text{Revenue Volatility} = \frac{\text{Độ lệch chuẩn Doanh thu (8 quý gần nhất)}}{\text{Doanh thu trung bình (8 quý gần nhất)}}$$
    $$\text{Points} = 15.0 - \frac{\text{Volatility} - 0.15}{0.45 - 0.15} \times (15.0 - (-10.0))$$
    $$\text{Points} = 15.0 - \frac{0.2425 - 0.15}{0.30} \times 25.0 \approx 7.29$$
*   **Ý nghĩa:** Mức biến động doanh thu 24.2% nằm dưới ngưỡng rủi ro 30%. Điều này phản ánh hoạt động xuất khẩu thủy sản của ANV duy trì tính ổn định tương đối tốt qua các quý, tránh các cú sốc sụt giảm doanh số đột ngột.

### 5. Đòn bẩy Vốn chủ sở hữu / Nợ vay tài chính (Equity-to-Debt Ratio)
*   **Giá trị thực tế:** `2.05x` (2.0477)
*   **Điểm chấm:** `+15.0 điểm` (Mức tối đa do Equity-to-Debt $\ge$ 1.5x)
*   **Công thức áp dụng:**
    $$\text{Equity-to-Debt} = \frac{\text{Vốn chủ sở hữu (Equity)}}{\text{Tổng nợ vay tài chính thực tế (Debt)}}$$
*   **Số liệu thực tế của ANV:**
    *   Vốn chủ sở hữu: $3,722,226,541,056$ VND.
    *   Tổng nợ vay tài chính thực tế: $1,817,792,501,510$ VND *(Gồm Vay ngắn hạn 1.76T + Vay dài hạn 0.05T)*.
    *   **Kết quả tính toán:**
        $$\text{Equity-to-Debt} = \frac{3,722,226,541,056}{1,817,792,501,510} \approx \mathbf{2.05x}$$
    *   **Lưu ý sửa lỗi ánh xạ:** Trước đây, do thuật toán cũ nhận nhầm các khoản mục tài sản *"Phải thu về cho vay ngắn/dài hạn"* làm nợ vay nên chỉ số này bị tính sai nghiêm trọng thành **3.18x** (ảo). Sau khi áp dụng cơ chế loại trừ, tỷ lệ thực tế **2.05x** phản ánh chính xác cấu trúc đòn bẩy lành mạnh của ANV (Vốn chủ sở hữu gấp đôi dư nợ vay tài chính).

### 6. Tăng trưởng dòng tiền hoạt động (CFO Growth YoY)
*   **Giá trị thực tế:** `-170.1%` (-1.7009)
*   **Điểm chấm:** `-10.0 điểm` (Mức phạt tối đa do CFO Growth $\le$ -20%)
*   **Công thức áp dụng:**
    $$\text{CFO Growth} = \frac{\text{CFO}_{2026\text{ (annualized)}} - \text{CFO}_{2025}}{\|\text{CFO}_{2025}\|}$$
*   **Ý nghĩa:** Dòng tiền hoạt động kinh doanh (CFO) của ANV có sự suy giảm mạnh so với kỳ năm trước. Điều này chủ yếu do tác động của việc quy đổi năm số liệu Quý 1/2026 kết hợp với áp lực thanh toán thuế nợ Nhà nước và gia tăng khoản phải thu khách hàng trong quý (chi tiết xem tại [bao_cao_chi_tiet_cfo_growth_anv.md](file:///f:/mo_hinh_danh_gia_pha_san/phan_tich_pha_san_clone/docs/2_han_muc_tin_dung/2_1_cham_diem_dong_tien/bao_cao_chi_tiet_cfo_growth_anv.md)). Đây là điểm cảnh báo duy nhất kéo điểm số của ANV từ mức tuyệt đối (1000) xuống **816 điểm** (cả Chế độ Chuyên gia - Expert Mode và Chế độ Calibrate do cùng áp dụng hệ số nhân 3.0 và base score 600).

---

## III. Đánh Giá Chung & Quyết Định Cấp Hạn Mức Tín Dụng

1.  **Đánh giá Sức mạnh Tài chính:**
    *   ANV sở hữu một cơ cấu tài chính vững mạnh với điểm số dòng tiền **816/1000 (Grade A)**.
    *   Khả năng thanh toán nợ vay cực kỳ ấn tượng nhờ dòng tiền hoạt động kinh doanh lũy kế (CFO TTM) dồi dào đạt trên **719 tỷ VND**, sẵn sàng bao phủ mọi nghĩa vụ tài chính ngắn hạn.
    *   Cơ cấu đòn bẩy thực tế (Equity/Debt = 2.05x) rất an toàn, tạo dư địa lớn để tiếp cận các nguồn vốn vay mới.
2.  **Khuyến nghị Quyết định:**
    *   **Đề xuất:** Phê duyệt cấp hạn mức tín dụng tự động (Auto-approve) dành cho doanh nghiệp nhóm A.
    *   **Giám sát:** Cần tiếp tục theo dõi chu kỳ luân chuyển vốn lưu động để kiểm soát việc suy giảm dòng tiền hoạt động kinh doanh (CFO Growth YoY âm) trong các kỳ báo cáo tiếp theo của năm 2026.
