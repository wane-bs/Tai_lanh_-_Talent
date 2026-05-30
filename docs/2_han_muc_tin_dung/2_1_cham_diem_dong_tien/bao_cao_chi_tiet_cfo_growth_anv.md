# Báo Cáo Thống Kê Phân Tích Sự Suy Giảm Dòng Tiền Hoạt Động Kinh Doanh (CFO) của ANV

*   **Đối tượng phân tích:** Công ty Cổ phần Nam Việt (ANV)
*   **Kỳ phân tích:** Quý 1 năm 2026
*   **Ngày tạo báo cáo:** 27/05/2026
*   **Mô hình tính toán:** BCTCCashFlowScorer

---

## I. Tóm Tắt Kết Quả Thống Kê Dòng Tiền

Hệ thống chấm điểm tín dụng xác định chỉ tiêu **Tăng trưởng dòng tiền hoạt động (CFO Growth YoY)** của ANV đạt **-170.09%** (suy giảm mạnh, dưới ngưỡng cảnh báo rủi ro là -15%). Đây là chỉ tiêu duy nhất bị phạt điểm (**-10 điểm**) trong hệ thống 6 chỉ tiêu dòng tiền của doanh nghiệp, làm giảm điểm tín dụng của doanh nghiệp từ mức tối đa 1000 xuống **816 điểm** (hạng **Grade A**).

### Bảng 1: Số liệu dòng tiền hoạt động kinh doanh (CFO) qua các kỳ

| Kỳ báo cáo | Giá trị CFO thực tế (VND) | Loại số liệu | Giá trị CFO quy năm (VND) | Ghi chú |
| :--- | :---: | :---: | :---: | :--- |
| **Năm 2024** | 728,399,475,726 | Cả năm | 728,399,475,726 | Dòng tiền dương mạnh mẽ |
| **Năm 2025** | 997,997,131,068 | Cả năm | 997,997,131,068 | Tăng trưởng +37.01% so với năm 2024 |
| **Quý 1/2026** | -174,864,026,123 | 1 Quý | -699,456,104,492 | Âm nặng, quy năm để so sánh YoY |

---

## II. Phương Pháp Tính Toán Thống Kê Của Hệ Thống

1. **Thu thập số liệu**: CFO thực tế Quý 1/2026 của ANV là **-174,864,026,123 VND** (âm 174.86 tỷ VND).
2. **Quy đổi năm (Annualization)**: Vì đây là báo cáo giữa niên độ (chỉ có dữ liệu Quý 1), hệ thống áp dụng hệ số quy đổi năm để tránh so lệch quy mô dòng tiền giữa 1 quý và cả năm:
   $$\text{CFO}_{2026\text{ (Quy năm)}} = \text{CFO}_{Q1/2026} \times 4.0 = -699,456,104,492\text{ VND}$$
3. **Tính toán tỷ lệ tăng trưởng YoY**: So sánh dòng tiền quy năm của 2026 với dòng tiền thực tế cả năm 2025:
   $$\text{CFO Growth YoY} = \frac{\text{CFO}_{2026\text{ (Quy năm)}} - \text{CFO}_{2025}}{|\text{CFO}_{2025}|} = \frac{ -699,456,104,492 - 997,997,131,068 }{ 997,997,131,068 } = \mathbf{-170.09\%}$$

---

## III. Nguyên Nhân Gây Suy Giảm Dòng Tiền Hoạt Động Kinh Doanh (Q1/2026)

Mặc dù trong Quý 1/2026 ANV ghi nhận **Lợi nhuận sau thuế dương rất tốt là 195,357,833,650 VND**, dòng tiền thuần từ hoạt động kinh doanh (CFO) vẫn thâm hụt **-174.86 tỷ VND** do các biến động lớn trên Bảng cân đối kế toán giữa Q4/2025 và Q1/2026:

### Bảng 2: Biến động các khoản mục ảnh hưởng đến dòng tiền hoạt động (Q4/2025 vs Q1/2026)

| Khoản mục tài chính | Cuối Q4/2025 (VND) | Cuối Q1/2026 (VND) | Biến động số dư (VND) | Ảnh hưởng đến Dòng tiền | Tác động cụ thể |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Lợi nhuận sau thuế Q1/2026** | - | - | +195,357,833,650 | **+ Tiền vào** | Nguồn tạo dòng tiền tích cực từ hoạt động sản xuất kinh doanh cốt lõi. |
| **Thuế và các khoản phải nộp Nhà nước** | 151,281,511,184 | 39,585,782,737 | -111,695,728,447 | **- Tiền ra (Nặng nhất)** | ANV đã chi ra lượng tiền lớn để trả nợ thuế, làm giảm mạnh tiền mặt. |
| **Phải thu khách hàng ngắn hạn** | 1,044,635,313,575 | 1,144,047,741,571 | 99,412,427,996 | **- Tiền ra (Bị chiếm dụng)** | Doanh thu bán hàng tăng nhưng đối tác chậm thanh toán, vốn bị đọng ở công nợ. |
| **Phải trả người lao động** | 87,358,582,685 | 65,091,021,902 | -22,267,560,783 | **- Tiền ra** | Chi trả lương, thưởng và phúc lợi tích lũy cho nhân viên trong Q1. |
| **Trả trước cho người bán** | 190,812,192,261 | 205,953,101,703 | 15,140,909,442 | **- Tiền ra** | Ứng trước tiền mua nguyên vật liệu cho các nhà cung cấp đầu vào. |
| **Chi phí phải trả** | 29,012,941,756 | 16,714,058,115 | -12,298,883,641 | **- Tiền ra** | Thanh toán các chi phí trích trước từ kỳ trước. |
| **Hàng tồn kho** | 1,437,598,361,571 | 1,372,741,303,573 | -64,857,057,998 | **+ Tiền vào** | Giải phóng hàng tồn kho giúp thu hồi dòng tiền về bổ sung thanh khoản. |
| **Phải trả người bán ngắn hạn** | 315,489,462,981 | 336,695,245,054 | 21,205,782,073 | **+ Tiền vào** | Chiếm dụng thêm vốn từ nhà cung cấp, trì hoãn dòng tiền chi ra. |

### Phân tích tổng hợp:
1. **Các khoản chi tiêu/phải thu tăng (Dòng tiền ra):** 
   * Trả nợ thuế Nhà nước: **~111.70 tỷ VND**
   * Tăng khoản phải thu (khách hàng nợ tiền): **~99.41 tỷ VND**
   * Trả lương và phúc lợi nhân viên: **~22.27 tỷ VND**
   * Trả trước nhà cung cấp và thanh toán chi phí trích trước: **~27.44 tỷ VND**
   * **Tổng dòng tiền ra hoạt động ngoài lợi nhuận:** **~260.82 tỷ VND**
   
2. **Các khoản thu hồi/phải trả tăng (Dòng tiền vào):**
   * Thu hồi từ bán hàng tồn kho: **~64.86 tỷ VND**
   * Tăng nợ nhà cung cấp: **~21.21 tỷ VND**
   * **Tổng dòng tiền vào bổ sung hoạt động:** **~86.07 tỷ VND**
   
3. **Kết quả dòng tiền ròng hoạt động:**
   $$\text{CFO ròng} \approx \text{LNST} - \text{Dòng tiền ra} + \text{Dòng tiền vào} = 195.36 - 260.82 + 86.07 \approx \mathbf{-174.86}\text{ tỷ VND}$$

---

## IV. Kết Luận Và Khuyến Nghị

*   **Rủi ro kỹ thuật:** Việc dòng tiền CFO Growth YoY đạt mức -170.09% có một phần nguyên nhân do **hiệu ứng toán học quy năm (x4)** của số liệu Q1/2026. Nếu trong các quý tiếp theo của năm 2026, ANV thu hồi tốt các khoản phải thu thương mại và giảm tần suất trả thuế lớn, dòng tiền lũy kế thực tế cả năm sẽ được cải thiện đáng kể.
*   **Sức mạnh tài chính tổng thể:** Dù chỉ tiêu CFO Growth bị phạt điểm, ANV vẫn có **DSCR rất an toàn (2.44x)** và **lượng tiền mặt dự phòng dồi dào**, do đó điểm số chung vẫn đạt **816/1000 điểm (Grade A)**.
*   **Hành động khuyến nghị:** 
    *   Tiếp tục phê duyệt hạn mức tín dụng tự động.
    *   Yêu cầu bộ phận quản lý rủi ro tín dụng theo dõi chặt chẽ **Tỷ lệ Thu hồi nợ phải thu (Receivables Turnover)** trong Quý 2/2026 để đảm bảo khách hàng thanh toán đúng hạn và dòng tiền hoạt động quay lại mức dương.

