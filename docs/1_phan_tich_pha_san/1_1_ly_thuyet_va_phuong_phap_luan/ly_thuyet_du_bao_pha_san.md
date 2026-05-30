# BÁO CÁO CƠ SỞ LÝ THUYẾT: DỰ BÁO NGUY CƠ PHÁ SẢN DOANH NGHIỆP

Tài liệu này trình bày khung lý thuyết cốt lõi được áp dụng trong hệ thống **phan_tich_pha_san_clone**, phân tách thành các nhóm chỉ số tài chính, phi tài chính và phương pháp luận mô hình hóa rủi ro.

---

## I. HỆ THỐNG CHỈ SỐ TÀI CHÍNH (FINANCIAL INDICATORS)

Trong quản trị rủi ro tín dụng hiện đại, sức khỏe doanh nghiệp được đánh giá qua 06 nhóm chỉ tiêu cơ bản. Trong đó, hệ thống đặc biệt nhấn mạnh vào khả năng tồn tại dòng tiền thông qua 3 trụ cột được highlight dưới đây:

### **1. Nhóm chỉ tiêu Thanh khoản (Liquidity) [HIGHLIGHT]**
*   **Tên thông dụng:** Hệ số thanh toán hoặc Vốn lưu động ròng.
*   **Cách tính:** 
    *   $\text{Current Ratio} = \frac{\text{Tài sản ngắn hạn}}{\text{Nợ ngắn hạn}}$
    *   $\text{Quick Ratio} = \frac{\text{Tiền} + \text{Đầu tư ngắn hạn} + \text{Phải thu}}{\text{Nợ ngắn hạn}}$
    *   **Hiệu chỉnh BĐS:** $X_1 = \frac{(\text{Tài sản ngắn hạn} - \text{Hàng tồn kho}) - \text{Nợ ngắn hạn}}{\text{Tổng Tài sản}}$
*   **Ý nghĩa:** Đo lường khả năng đáp ứng các nghĩa vụ nợ đến hạn ngay lập tức mà không cần vay thêm vốn mới.

### **2. Nhóm chỉ tiêu Khả năng trả nợ (Debt Service) [HIGHLIGHT]**
*   **Tên thông dụng:** Hệ số bao phủ lãi vay (ICR) hoặc DSCR.
*   **Cách tính:** 
    *   $\text{ICR} = \frac{\text{EBIT}}{\text{Chi phí lãi vay}}$
    *   $\text{DSCR} = \frac{\text{EBITDA}}{\text{Gốc vay} + \text{Lãi vay}}$
*   **Ý nghĩa:** Xác định liệu lợi nhuận và dòng tiền từ hoạt động kinh doanh cốt lõi có đủ để bù đắp chi phí sử dụng vốn và nghĩa vụ hoàn nợ gốc hay không.

### **3. Nhóm chỉ tiêu Dòng tiền (Cash Flow) [HIGHLIGHT]**
*   **Tên thông dụng:** CFO TTM hoặc Khả năng chi trả bằng tiền mặt.
*   **Cách tính:** 
    *   $\text{CFO to Debt} = \frac{\text{Dòng tiền từ HĐKD (TTM)}}{\text{Tổng nợ}}$
    *   $\text{Runway Interest} = \frac{\text{Tiền \& Tương đương tiền}}{\text{Chi phí lãi vay hàng quý}}$
*   **Ý nghĩa:** Đây là "mạch máu" thực của doanh nghiệp. Một doanh nghiệp có thể có lãi trên sổ sách nhưng vẫn phá sản nếu dòng tiền CFO bị đứt gãy liên tục.

### 4. Nhóm chỉ tiêu Đòn bẩy (Leverage)
*   **Cách tính:** $D/E = \frac{\text{Tổng nợ}}{\text{Vốn chủ sở hữu}}$
*   **Ý nghĩa:** Đo lường mức độ rủi ro cơ cấu tài chính và sức chịu đựng trước các biến động lãi suất.

### 5. Nhóm chỉ tiêu Sinh lời (Profitability)
*   **Cách tính:** $\text{ROA} = \frac{\text{LNST}}{\text{Tổng tài sản}}$; $\text{ROE} = \frac{\text{LNST}}{\text{Vốn chủ}}$
*   **Ý nghĩa:** Khả năng tự tích lũy vốn và hiệu quả sử dụng nguồn lực để chống lại sự bào mòn vốn.

### 6. Nhóm chỉ tiêu Hiệu suất (Efficiency)
*   **Cách tính:** $\text{Inventory Turnover} = \frac{\text{Giá vốn hàng bán}}{\text{Hàng tồn kho bình quân}}$
*   **Ý nghĩa:** Tốc độ lưu thông hàng hóa và khả năng chuyển hóa tài sản thành tiền.

---

## II. HỆ THỐNG CHỈ SỐ PHI TÀI CHÍNH (NON-FINANCIAL INDICATORS)

Bên cạnh các con số định lượng, hệ thống còn xem xét các yếu tố định tính để hiệu chỉnh dự báo cuối cùng:

1.  **Chất lượng Quản trị (Corporate Governance):** Tính minh bạch của Hội đồng quản trị, cấu trúc sở hữu chéo, và các giao dịch với bên liên quan.
2.  **Vị thế Ngành (Industry Position):** Lợi thế cạnh tranh, rào cản gia nhập ngành, và chu kỳ kinh tế của ngành (Ví dụ: Chu kỳ đóng băng của BĐS).
3.  **Yếu tố Vĩ mô (Macro Factors):** Biến động tỷ giá, chính sách tiền tệ (Lãi suất điều hành), và sự thay đổi về khung pháp lý (Luật Đất đai, Luật Kinh doanh BĐS).
4.  **ESG (Môi trường - Xã hội - Quản trị):** Sự tuân thủ các quy chuẩn về bền vững, giúp giảm thiểu rủi ro pháp lý và danh tiếng.
5.  **Lịch sử Tín dụng:** Các sự kiện vi phạm cam kết nợ (Covenant defaults) hoặc nợ xấu quá hạn trong quá khứ.

---

## III. MÔ HÌNH DỰ BÁO TỔNG HỢP

Hệ thống **phan_tich_pha_san_clone** vận hành dựa trên sự kết hợp giữa các mô hình dự báo kinh điển và trí tuệ nhân tạo, lấy 3 chỉ số tài chính trọng yếu làm nòng cốt để đảm bảo tính chính xác và khả năng giải thích cao.

### 1. Các Mô hình Truyền thống & Ngưỡng Kiểm soát (Traditional Benchmarks)
Đây là lớp phòng vệ đầu tiên, giúp xác định tình trạng sức khỏe tài chính dựa trên các công thức đã được chứng minh qua thời gian.

| Mô hình | Phương pháp tiếp cận | Vai trò trong hệ thống (Static Check) |
| :--- | :--- | :--- |
| **Altman Z-Score** | Hồi quy MDA (Multiple Discriminant Analysis) | Cung cấp điểm số nền tảng để phân loại nhanh doanh nghiệp vào vùng An toàn (Safe), Cảnh báo (Grey), hoặc Nguy hiểm (Distress). |
| **Hệ thống Ngưỡng (Thresholds)** | Kiểm tra các chỉ số Thanh toán hiện hành & Thanh toán nhanh | Đóng vai trò là **"Lá chắn đầu tiên"** để lọc các doanh nghiệp có nguy cơ mất thanh khoản ngay lập tức. |
| **Phân tích Xu hướng (Trend Analysis)** | So sánh biến động CFO và ICR qua các kỳ (TTM) | Phát hiện sự suy giảm hệ thống của dòng tiền và khả năng trả nợ trước khi DN thực sự lâm vào tình trạng vỡ nợ. |

### 2. Phối hợp Mô hình Kinh điển & Học máy (Hybrid Pillar Strategy)
Sự kết hợp này cho phép hệ thống vừa giữ được tính kỷ luật của các quy tắc tài chính truyền thống, vừa tận dụng khả năng nhận diện các mối quan hệ phi tuyến phức tạp của AI.

| Trụ cột Trọng yếu | Cơ chế Ngắt mạch (Kinh điển - Logic) | Sức mạnh Học máy (AI/ML - XGBoost/SHAP) |
| :--- | :--- | :--- |
| **Thanh khoản (Liquidity)** | Nếu hệ số Thanh khoản nhanh < 0.5 $\rightarrow$ Gán nhãn rủi ro **"Danger"** ngay lập tức. | Tìm kiếm sự tương tác giữa Thanh khoản tài sản và Hiệu suất hàng tồn kho để xác định rủi ro "bẫy thanh khoản" tiềm ẩn. |
| **Trả nợ (Debt Service)** | Nếu ICR < 1 liên tục trong 2 quý $\rightarrow$ Kích hoạt ngắt mạch, xếp loại **"Critical"**. | Đánh giá mức độ nhạy cảm của xác suất vỡ nợ trước các biến động lãi suất và cấu trúc đòn bẩy tài chính. |
| **Dòng tiền (Cash Flow)** | Nếu CFO âm liên tục $\rightarrow$ Trừ điểm nặng toàn hệ thống bất chấp lợi nhuận kế toán. | **XAI (SHAP Values):** Cô lập và định lượng chính xác % đóng góp của sự đứt gãy dòng tiền vào tổng xác suất phá sản. |

> [!IMPORTANT]
> **Cơ chế Hợp nhất:** Một doanh nghiệp chỉ được coi là "An toàn" khi vượt qua cả bộ lọc Ngưỡng kinh điển và có xác suất dự báo từ mô hình ML (XGBoost) dưới 20%. Nếu có sự xung đột (ví dụ: Z-Score tốt nhưng ML báo rủi ro cao), hệ thống sẽ ưu tiên kết quả của ML vì khả năng phát hiện "ma thuật kế toán" qua các biến tương tác.

---
*© 2026 — Tài liệu Cơ sở Lý thuyết Hệ thống Dự báo Phá sản*
