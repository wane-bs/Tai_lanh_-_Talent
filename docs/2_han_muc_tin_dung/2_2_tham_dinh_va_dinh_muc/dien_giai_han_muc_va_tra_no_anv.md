# Báo Cáo Thẩm Định Hạn Mức Tín Dụng & Phương Án Trả Nợ Dự Kiến (ANV)

*   **Doanh nghiệp thẩm định:** Công ty Cổ phần Nam Việt (ANV)
*   **Kỳ phân tích báo cáo:** Quý 1 năm 2026 (Số liệu TTM lũy kế hoặc quy năm)
*   **Module tính toán:** `CreditUnderwriter` trong [credit_model.py](file:///f:/mo_hinh_danh_gia_pha_san/phan_tich_pha_san_clone/src/credit_model.py)
*   **Hạn mức đề xuất cuối cùng (L_final):** **1,812,296,026,719 VND** (Làm tròn: **1,812.30 Tỷ VND**)
*   **Quyết định phê duyệt:** **Phê duyệt có điều kiện (Cắt giảm 15% AI Haircut)** ⚠️

---

## I. Số Liệu Đầu Vào Dùng Cho Thẩm Định (ANV - 2026)

Các chỉ số tài chính cơ bản được trích xuất từ dữ liệu báo cáo tài chính thực tế và được xử lý qua pipeline:

1.  **Dòng tiền từ hoạt động kinh doanh (CFO TTM):** `719,167,553,023` VND (~719.17 Tỷ VND)
2.  **Khả năng trả lãi (ICR - Interest Coverage Ratio):** `10.36x`
3.  **Tỷ lệ Hàng tồn kho trên Tổng tài sản (Inventory/TA):** `22.37%`
4.  **Tấm đệm đòn bẩy Vốn chủ sở hữu / Tổng nợ phải trả (Equity/Debt):** `1.59x`
    *   *Vốn chủ sở hữu (Equity):* `3,722,226,541,056` VND (~3,722.23 Tỷ VND)
    *   *Tổng nợ phải trả (Total Liabilities):* `2,343,418,004,168` VND (~2,343.42 Tỷ VND)
5.  **Tỷ lệ Vốn lưu động trên Tổng tài sản (WC/TA):** `0.0133` (Dương, thể hiện trạng thái thanh khoản lành mạnh)
6.  **Xác suất vỡ nợ dự báo từ AI (PD XGBoost):** `7.86%`
7.  **Nhóm phân hạng rủi ro tổng hợp (Risk Level):** `Level 2 (Watch - Cảnh báo)`
8.  **Điểm rủi ro tổng hợp (Composite Score):** `23.43 / 100`

---

## II. Quy Trình Tính Toán Định Mức Tín Dụng Thích Ứng

Mô hình tính toán dựa trên triết lý **Thẩm định dựa trên Dòng tiền thực tế (Cash Flow-based)** kết hợp các chốt chặn rủi ro AI để điều chỉnh biên an toàn:

### Step 1: Xác định Dòng tiền Khả dụng Trả nợ (CFADS)
Dòng tiền hoạt động kinh doanh dương được dùng làm gốc để chi trả gốc và lãi vay mới:
$$\text{CFADS} = \max(\text{CFO TTM}, 0.0) = 719,167,553,023 \text{ VND}$$

### Step 2: Tính toán Hệ số DSCR Mục tiêu Thích ứng (Target DSCR)
DSCR mục tiêu được cấu thành từ mức nền an toàn cơ bản và các khoản phạt rủi ro tài chính & AI:
$$\text{Target DSCR} = \text{DSCR}_{base} + \Delta\text{DSCR}_{Inventory} + \Delta\text{DSCR}_{Capital} + \Delta\text{DSCR}_{WorkingCapital} + \Delta\text{DSCR}_{AI}$$

*   **$\text{DSCR}_{base}$ (Nền tảng):** `1.20`
*   **$\Delta\text{DSCR}_{Inventory}$ (Phạt ứ đọng tồn kho):** `0.0` (Do tỷ lệ tồn kho 22.37% < 40%)
*   **$\Delta\text{DSCR}_{Capital}$ (Phạt đòn bẩy yếu):** `0.0` (Do đòn bẩy Equity/Debt 1.59x > 0.30)
*   **$\Delta\text{DSCR}_{WorkingCapital}$ (Phạt thâm hụt thanh khoản):** `0.0` (Do WC/TA 0.0133 > 0)
*   **$\Delta\text{DSCR}_{AI}$ (Phạt rủi ro dự báo AI):** $+0.0786$ (Tính bằng $\frac{\text{PD XGBoost}}{100} = \frac{7.86\%}{100}$)

$$\text{Target DSCR} = 1.20 + 0.0 + 0.0 + 0.0 + 0.0786 = \mathbf{1.2786}$$

> [!NOTE]
> Chỉ số DSCR mục tiêu được điều chỉnh tăng lên mức **1.2786** (so với mức nền 1.20) do có yếu tố bù đắp rủi ro vỡ nợ tiềm ẩn 7.86% từ mô hình XGBoost.

### Step 3: Tính số tiền gốc và lãi trả nợ hàng năm tối đa (PMT_max)
$$\text{PMT}_{max} = \frac{\text{CFADS}}{\text{Target DSCR}} = \frac{719,167,553,023}{1.2786} \approx \mathbf{562,446,030,944 \text{ VND / Năm}}$$

### Step 4: Tính toán Hạn mức Cơ sở ($L_{base}$) theo công thức Niên kim
Giả định lãi suất cho vay kỳ vọng là $r = 10.0\%$ và kỳ hạn vay tối đa là $n = 5$ năm. Hệ số hiện giá của dòng tiền đều (PV of Annuity factor):
$$\text{PV Factor} = \frac{1 - (1 + r)^{-n}}{r} = \frac{1 - (1.10)^{-5}}{0.10} \approx 3.7908$$
$$\text{L}_{base} = \text{PMT}_{max} \times \text{PV Factor} = 562,446,030,944 \times 3.7908 \approx \mathbf{2,132,112,972,611 \text{ VND}}$$

---

## III. Áp Dụng Chốt Chặn Rủi Ro & Chiết Khấu Tín Dụng

### 1. Quét bộ Chốt chặn Ngắt mạch (Circuit Breakers)
*   **AI Circuit Breaker ($\text{PD} > 55\%$ hoặc $\text{Risk Level} \ge 4$):** Vượt qua (PD = 7.86%, Risk Level = 2).
*   **ICR Breaker ($\text{ICR} < 1.0$):** Vượt qua (ICR thực tế đạt 10.36x, rất an toàn).
*   **Vốn chủ sở hữu âm ($\text{Equity} \le 0$):** Vượt qua (Equity dương lớn đạt 3,722 Tỷ VND).
*   **Dòng tiền âm ($\text{CFADS} \le 0$):** Vượt qua (CFO dương lớn đạt 719.17 Tỷ VND).

### 2. Chiết khấu Rủi ro AI (AI Haircut)
Do ANV thuộc nhóm phân hạng rủi ro **Level 2 (Watch - Cảnh báo)** trên hệ thống cảnh báo rủi ro phá sản, mô hình áp dụng cơ chế chiết khấu an toàn **15%** để dự phòng rủi ro biến động:
$$\text{L}_{final} = \text{L}_{base} \times (1 - 0.15) = 2,132,112,972,611 \times 0.85 = \mathbf{1,812,296,026,719 \text{ VND}}$$

### 3. Chốt chặn Đòn bẩy Bảng cân đối (Leverage Cap)
Đảm bảo duy trì tấm đệm Vốn tự có tối thiểu đạt 15% trên quy mô tổng nợ vay dự kiến:
$$\text{Leverage Cap} = \frac{\text{Equity}}{0.15} - \text{Total Liabilities} = \frac{3,722,226,541,056}{0.15} - 2,343,418,004,168 \approx \mathbf{22,471,425,602,872 \text{ VND}}$$

Vì $\text{L}_{final} (1,812,296,026,719 \text{ VND}) < \text{Leverage Cap}$, hạn mức không bị giới hạn thêm bởi cấu trúc bảng cân đối kế toán.

> [!IMPORTANT]
> **HẠN MỨC PHÊ DUYỆT CUỐI CÙNG (L_final):** **1,812,296,026,719 VND** (~1,812.30 Tỷ VND).

---

## IV. Phương Án Trả Nợ Chi Tiết Dự Kiến

Hệ thống AI đề xuất áp dụng phương thức **Niên kim đều (Equal Annual Payment)** làm phương án chính.

> [!TIP]
> **Lý do đề xuất Niên kim đều:** 
> Do chỉ số DSCR của ANV thực tế nằm ở mức vừa phải (không quá dư thừa), phương thức Niên kim giúp giữ cho tổng nghĩa vụ thanh toán (gốc + lãi) hàng năm ở mức cố định, thấp hơn trong các năm đầu so với phương pháp gốc đều, bảo vệ dòng tiền hoạt động kinh doanh cốt lõi của doanh nghiệp khỏi bị thâm hụt nặng nề đột biến.

Dưới đây là so sánh chi tiết giữa hai phương án trả nợ dựa trên hạn mức cấp phát **1,812.30 Tỷ VND** với lãi suất giả định **10%/năm** trong **5 năm**:

### Phương án 1: Niên kim đều (Phương án AI Khuyến nghị)
*Tổng số tiền thanh toán hàng năm cố định ở mức **478,079,126,303 VND** (~478.08 Tỷ VND).*

| Năm | Dư nợ đầu kỳ (VND) | Tổng trả hàng năm (VND) | Trả Nợ Gốc (VND) | Trả Lãi Vay (VND) | Dư nợ cuối kỳ (VND) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 1,812,296,026,719 | 478,079,126,303 | 296,849,523,631 | 181,229,602,672 | 1,515,446,503,088 |
| **2** | 1,515,446,503,088 | 478,079,126,303 | 326,534,475,994 | 151,544,650,309 | 1,188,912,027,094 |
| **3** | 1,188,912,027,094 | 478,079,126,303 | 359,187,923,593 | 118,891,202,709 | 829,724,103,501 |
| **4** | 829,724,103,501 | 478,079,126,303 | 395,106,715,953 | 82,972,410,350 | 434,617,387,548 |
| **5** | 434,617,387,548 | 478,079,126,303 | 434,617,387,548 | 43,461,738,755 | 0 |
| **Tổng**| | **2,390,395,631,514**| **1,812,296,026,719**| **578,099,604,795**| |

### Phương án 2: Trả nợ gốc đều, lãi giảm dần (Phương án So sánh)
*Số tiền gốc cố định hàng năm: **362,459,205,344 VND** (~362.46 Tỷ VND). Tổng trả giảm dần qua các năm.*

| Năm | Dư nợ đầu kỳ (VND) | Tổng trả hàng năm (VND) | Trả Nợ Gốc (VND) | Trả Lãi Vay (VND) | Dư nợ cuối kỳ (VND) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 1,812,296,026,719 | 543,688,808,016 | 362,459,205,344 | 181,229,602,672 | 1,449,836,821,375 |
| **2** | 1,449,836,821,375 | 507,442,887,481 | 362,459,205,344 | 144,983,682,138 | 1,087,377,616,031 |
| **3** | 1,087,377,616,031 | 471,196,966,947 | 362,459,205,344 | 108,737,761,603 | 724,918,410,688 |
| **4** | 724,918,410,688 | 434,951,046,413 | 362,459,205,344 | 72,491,841,069 | 362,459,205,344 |
| **5** | 362,459,205,344 | 398,705,125,878 | 362,459,205,344 | 36,245,920,534 | 0 |
| **Tổng**| | **2,355,984,834,735**| **1,812,296,026,719**| **543,688,808,016**| |

### Đánh giá so sánh hiệu quả tài chính:
1.  **Tiết kiệm lãi vay:** Phương án **Trả gốc đều** có tổng số tiền lãi phải trả là **543.69 Tỷ VND**, thấp hơn **34.41 Tỷ VND** so với phương án Niên kim đều (**578.10 Tỷ VND**).
2.  **Áp lực dòng tiền năm đầu:** 
    *   Niên kim đều yêu cầu thanh toán năm đầu là **478.08 Tỷ VND**.
    *   Gốc đều yêu cầu thanh toán năm đầu lên tới **543.69 Tỷ VND** (cao hơn ~65.61 Tỷ VND).
    *   Với dòng tiền CFO hiện tại là ~719 Tỷ VND, ANV hoàn toàn đủ sức đáp ứng cả hai phương án. Tuy nhiên, việc lựa chọn Niên kim sẽ giúp doanh nghiệp giữ lại nhiều thặng dư thanh khoản hơn cho hoạt động kinh doanh trong các năm đầu phục hồi.

---

## V. Khuyến Nghị & Giám Sát Sau Cho Vay

1.  **Chốt hạn mức vay tối đa:** Không giải ngân vượt quá **1,812.30 Tỷ VND** nhằm kiểm soát tỷ số nợ vay và hệ số DSCR ở ngưỡng an toàn đã điều chỉnh.
2.  **Giám sát dòng tiền hoạt động kinh doanh (CFO):** Do chỉ tiêu tăng trưởng dòng tiền CFO Growth YoY của ANV đang âm sâu (-170.1%), cần theo dõi tiến độ thu hồi nợ phải thu của doanh nghiệp hàng quý để đảm bảo dòng tiền CFO TTM thực tế không sụt giảm dưới mức **562.45 Tỷ VND** (ngưỡng trả nợ gốc và lãi tối đa).
3.  **Điều khoản bổ sung:** Căn cứ theo xếp hạng rủi ro **Level 2 (Watch)** từ mô hình XGBoost, tổ chức tín dụng nên bổ sung điều khoản giám sát dòng tiền thu từ bán hàng qua tài khoản chuyên dụng mở tại ngân hàng cho vay để kiểm soát nguồn thu nợ chủ động.

---
*Báo cáo được tự động khởi tạo bởi Module Credit Sizing & Repayment Capacity Assessment.*
