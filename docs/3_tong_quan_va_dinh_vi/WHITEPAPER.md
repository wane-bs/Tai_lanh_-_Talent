# WHITEPAPER - BẢN NHÁNH BẤT ĐỘNG SẢN (REAL ESTATE)

# Hệ thống Kiểm soát & Dự báo Rủi ro Phá sản Doanh nghiệp (Phiên bản Bất động sản)
### *Enterprise Bankruptcy Risk Control & Prediction System - Real Estate Variant*

---

**Phiên bản:** 2.0 (Real Estate Fine-tuned)  
**Ngày xuất bản:** Tháng 4, 2026  
**Phân loại:** Tài liệu Kỹ thuật — Công khai  

---

## MỤC LỤC

1. [Tóm tắt Điều hành](#1-tóm-tắt-điều-hành)
2. [Bối cảnh & Động lực Ngành Bất Động Sản](#2-bối-cảnh--động-lực-ngành-bất-động-sản)
3. [Kiến trúc Toán học & Dòng chảy Dữ liệu](#3-kiến-trúc-toán-học--dòng-chảy-dữ-liệu)
4. [Phương pháp luận Kinh điển (Classical Baseline)](#4-phương-pháp-luận-kinh-điển-classical-baseline)
5. [Cấu trúc Chỉ số Sinh tử Bất Động Sản](#5-cấu-trúc-chỉ-số-sinh-tử-bất-động-sản)
6. [Động cơ Machine Learning Cốt lõi](#6-động-cơ-machine-learning-cốt-lõi)
7. [Hệ thống Phân loại Rủi ro Tổng hợp (Ngắt Mạch BĐS)](#7-hệ-thống-phân-loại-rủi-ro-tổng-hợp-ngắt-mạch-bđs)
8. [Dashboard & Giao diện Báo cáo](#8-dashboard--giao-diện-báo-cáo)
9. [Cơ sở Dữ liệu & Kiểm định](#9-cơ-sở-dữ-liệu--kiểm-định)
10. [Hướng dẫn Triển khai](#10-hướng-dẫn-triển-khai)
11. [Mô hình Định mức Tín dụng (Credit Sizing)](#11-mô-hình-định-mức-tín-dụng-credit-sizing)

---

## 1. Tóm tắt Điều hành

**`phan_tich_pha_san_clone` (Bản nhánh Bất động sản)** là phiên bản tái kiến trúc chuyên sâu của hệ thống phân tích rủi ro phá sản, được tinh chỉnh hoàn toàn cho ngành **Bất động sản (Real Estate)** tại Việt Nam.

Khác với phân tách truyền thống dựa trên Vốn lưu động (áp dụng cho Bán lẻ/Sản xuất), hệ thống định nghĩa lại cấu trúc rủi ro qua lăng kính **Khuyết đứt Dòng tiền (Cash Flow Insolvency)** và **Sức ép Đòn bẩy**.

| Chỉ tiêu | Giá trị |
|:---|:---|
| **Đặc tả hệ thống** | Tùy chỉnh (Fine-tuned) cho ngành Bất động sản (`--industry REAL_ESTATE`) |
| **Kiến trúc Dữ liệu** | Extract dữ liệu Quý (Quarterly), chuyển đổi làm phẳng qua hàm Lũy kế 4 Quý (TTM) |
| **Cơ cấu trọng số** | XGBoost (40%), Altman (20%), Ohlson (15%), Sloan Accruals (15%), Zmijewski (5%), DSCR (5%) |
| **Phân loại rủi ro** | Thang 5 mức (Safe → Watch → Stress → Danger → Critical) + Hệ thống **Circuit Breakers** |
| **Tái cấu trúc Baseline**| Loại bỏ hoàn toàn nhiễu `Beneish M-Score` trong BĐS, đè nặng hệ số `Sloan Accruals`. |

---

## 2. Bối cảnh & Động lực Ngành Bất Động Sản

Trong Báo cáo Tài chính của ngành BĐS Việt Nam, **"Lợi nhuận sổ sách"** cực kỳ phân kỳ với **"Lưu lượng tiền mặt cốt lõi"**. Vấn đề này sinh ra từ 3 đặc thù điểm ngoặt:

1. **Chu kỳ bùng nổ Doanh thu:** Lợi nhuận P&L thường tăng dốc theo từng đoạn ngắt quãng (Pha bàn giao dự án), do đó các biểu thức tăng trưởng truyền thống (Sales Growth Index) dễ đưa ra báo động giả (False Positives).
2. **Khối U Tài sản (Illiquid Assets):** Vốn liên tục bị ép thành các loại tài sản không có tính thanh khoản (Hàng tồn kho dở dang, Phải thu của công ty sân sau), tạo ra lợi nhuận trên giấy nhưng gây âm dòng tiền (CFO).
3. **Cơn ác mộng Khát Vay (Leverage Trap):** Áp lực gốc và lãi làm đứt gãy khả năng sinh tồn của công ty dài trước khi tổng vốn chủ sở hữu bị bào mòn nhỏ hơn 0.

---

## 3. Kiến trúc Toán học & Dòng chảy Dữ liệu

Dưới góc nhìn Kinh tế lượng (Econometrics), hệ thống phân tích BĐS vận hành như một **Mạng lưới Đối soát và Tự Sửa Lỗi (Self-Correcting Network)** đi từ cơ sở tham số đến phi tham số.

```mermaid
graph TD
    classDef baseline fill:#f9f871,stroke:#333,stroke-width:2px,color:#000;
    classDef quality fill:#ffc75f,stroke:#333,stroke-width:2px,color:#000;
    classDef breaker fill:#ff9671,stroke:#333,stroke-width:2px,color:#000;
    classDef modern fill:#ff6f91,stroke:#333,stroke-width:2px,color:#000;
    classDef data fill:#00c9a7,stroke:#333,stroke-width:2px,color:#000;
    classDef output fill:#845ec2,stroke:#333,stroke-width:2px,color:#fff;
    classDef cross fill:#008f7a,stroke:#333,stroke-width:2px,color:#fff;
    classDef credit fill:#0089ba,stroke:#333,stroke-width:2px,color:#fff;

    Data[("Dữ liệu BCTC Quý (Raw TTM)")] ::: data

    subgraph L2 [Lớp 2: Kiểm soát & Gian lận]
        S["Sloan Accruals (CF Anomaly)"] ::: quality
    end

    subgraph L1 [Lớp 1: Baseline Kinh điển]
        Alt["Altman Z'' Score"] ::: baseline
        Ohl["Ohlson O-Score"] ::: baseline
        Zmi["Zmijewski Score"] ::: baseline
    end

    subgraph L4 [Lớp 4: Lõi Hiện Đại ML]
        RF["Random Forest (Gini Rank)"] ::: modern
        XGB["XGBoost PD% (Non-linear)"] ::: modern
        XAI["SHAP Values"] ::: modern
    end

    subgraph L3 [Lớp 3: Tín hiệu Ngắt mạch BĐS]
        LR["Runway Interest"] ::: breaker
        DSCR["Hard Rule: CFO_TTM < 0"] ::: breaker
    end
    
    CrossCheck{"Khối Đối soát Chéo (Divergence)"} ::: cross

    Data --> L2
    Data --> L1
    Data --> L4
    Data --> L3

    L2 -- "Trừ điểm sổ sách" --> L1
    L1 -- "Xác suất rủi ro Tĩnh" --> Comp{"Composite Score"}
    L4 -- "Xác suất phi tuyến Động" --> Comp
    L2 -- "Tín hiệu Lợi nhuận Ảo" --> Comp
    
    L1 -. "Tín hiệu Tĩnh" .-> CrossCheck
    L4 -. "Tín hiệu Động" .-> CrossCheck
    CrossCheck -. "Rủi ro Vùng Khuyết" .-> Comp
    
    L3 -- "Cưỡng chế Ngắt Mạch Nợ Vay" --> Final(("Phân Xếp loại Rủi ro 1-5")) ::: output
    Comp --> Final

    subgraph L5 [Lớp 5: Định mức Tín dụng & Đánh giá]
        CreditEngine["Credit Underwriter (Định mức Hạn mức Vay)"] ::: credit
        L_final(("Hạn mức Tối đa (L_final)")) ::: output
    end

    Data --> CreditEngine
    Final --> CreditEngine
    XGB --> CreditEngine
    CreditEngine --> L_final
```

### Tiền xử lý dữ liệu (Tính Lũy kế TTM)
Hàm mục tiêu cốt lõi của Lớp 1 (ETL) là làm phẳng đi tính mùa vụ bằng cách sử dụng phép tổng di động qua 4 Quý (Trailing Twelve Months):
$$Var_{TTM}^{(t)} = \sum_{k=0}^{3} Var_{Quarter}^{(t - k)}$$
Việc này được áp dụng nghiêm ngặt cho `CFO_TTM`, `Interest_TTM`, và `Revenue_TTM`.

---

## 4. Phương pháp luận Kinh điển (Classical Baseline)

Lớp Baseline cung cấp phân vị không gian tĩnh, kết hợp giữa hồi quy tuyến tính, Logistic và Probit.

### 4.1. Altman Z''-Score (Thị trường mới nổi, Phi Sản xuất)
Nhằm khống chế sự thiên lệch vốn lưu động quá tải, hệ thống sử dụng thuật toán Z'' (Altman 2005) trích xuất siêu phẳng trong Discriminant Analysis:
$$Z'' = 3.25 + 6.56X_1 + 3.26X_2 + 6.72X_3 + 1.05X_4$$
- $X_1$: **Vốn lưu động ròng** / Tổng tài sản *(Thanh khoản thực tế)*
  > **BĐS Fine-tuned:** $X_1 = \frac{(TSNH - Hàng\ tồn\ kho) - Nợ\ ngắn\ hạn}{Tổng\ tài\ sản}$
  > 
  > Hàng tồn kho BĐS (dự án dở dang, đất nền, nhà xây thô) có tính thanh khoản cực thấp và thường bị đóng băng bởi rủi ro pháp lý / thị trường. Loại bỏ HTK khỏi TSNH giúp $X_1$ phản ánh đúng khả năng "xoay tiền" thực tế — tập trung vào tiền mặt, đầu tư ngắn hạn và phải thu có khả năng thu hồi.
- $X_2$: Lãi chưa phân phối / Tổng tài sản *(Tính tích lũy vốn)*
- $X_3$: EBIT / Tổng tài sản *(ROA)*
- $X_4$: Vốn chủ sở hữu / Tổng Nợ *(Đệm vốn tín dụng)*

### 4.2. Ohlson O-Score (Hồi quy Logistic)
Sử dụng phân phối xác suất hình Sigmoid (giới hạn $0 \to 1$) để né phương sai sai số, cung cấp xác suất Baseline:
$$O = -1.32 - 0.407 \ln\!\left(\frac{TA}{10^6}\right) + 6.03 \left(\frac{TL}{TA}\right) - 1.43 \left(\frac{WC}{TA}\right) \dots - 1.83 \left(\frac{CFO}{TL}\right)$$
$$P_{Ohlson} = \frac{1}{1 + e^{-O}} \times 100\%$$

### 4.3. Zmijewski (Hồi quy Probit)
Phân phối dựa trên tích lũy phân phối chuẩn tắc (Gaussian CDF):
$$X = -4.336 - 4.513\left(\frac{NI}{TA}\right) + 5.679\left(\frac{TL}{TA}\right) - 0.004\left(\frac{CA}{CL}\right)$$
$$P_{Zmijewski} = \Phi(X)$$

### 4.4. Thay cực Beneish bằng Sloan Accruals
*(Beneish M-Score bị loại bỏ do SGI (Tăng trưởng doanh thu) bùng nổ theo quý làm mất giá trị dự báo BĐS).* 
**Sloan Accruals** đo đạc khối u "Lợi nhuận Kế toán" so với "Dòng thu thực sự":
$$Accruals\ \% = \frac{Net\ Income - CFO_{TTM}}{Average\ Total\ Assets} \times 100$$
> **Ngưỡng biên độ:** $|Accruals| > 25\% \Rightarrow$ Cảnh báo Đặc biệt (Vênh lệch thao túng sổ sách cực độ).

---

## 5. Cấu trúc Chỉ số Sinh tử Bất Động Sản

Mô-đun `calculator.py` cấy ghép vào khung điểm số các thông số đo lường sống còn.

| Đặc trưng | Thuật toán / Công thức tính | Giải nghĩa trong ngành BĐS |
|:---|:---|:---|
| **Dòng tiền đáo hạn** | `CFO_to_Short_Debt` = $\frac{CFO_{TTM}}{Nợ\ ngắn\ hạn}$ | Đánh giá trực tiếp khả năng CFO lũy kế 4 quý có đủ che lấp số nợ phình to trước mắt. |
| **Bao phủ khối Lãi** | `Interest_Coverage_CFO` = $\frac{CFO_{TTM}}{Chi\ phí\ lãi\ vay_{TTM}}$ | Nếu tỉ lệ < 1, công ty đang phát hành thêm Nợ / Móc nối vốn mới để trả ròng khối lãi tĩnh. |
| **An toàn Căng Thẳng** | `DSCR_Stressed` = $\frac{EBITDA\ \times\ (1 - 30\%)}{Lãi\ vay{TTM} + Gốc\ Vay}$ | Basel Stress-Test: Cho doanh nghiệp rơi vào khủng hoảng vĩ mô (trừ hao 30% doanh thu). |
| **Tồn kho Chết** | `Inventory_to_Assets` = $\frac{Hàng\ Tồn\ Kho}{Tổng\ Tài\ sản}$ | Theo dõi tốc độ hóa thành tảng đất trống / dự án kẹt pháp lý đóng băng bảng Cân đối. |
| **Biến thiên Runway**| `Runway_Interest` = $\frac{Tiền\ Mặt\ \&\ Tương\ đương}{Chi\ phí\ Lãi\ vay\ (Q)}$ | Giới hạn Cạn kiệt: Ước lượng số lượng Quý tiếp theo công ty duy trì trả nổi lãi vay bằng tiền mặt. |

---

## 6. Động cơ Machine Learning Cốt lõi

Vì dữ liệu phá sản Bất động sản Việt Nam bị hạn chế do hiện tượng "Zombie thoi thóp" (chưa chịu phá sản), hệ thống sử dụng Kỹ thuật Huấn luyện trước qua Đóng gói Cây Quyết Định lên tập dữ liệu chéo của Châu Âu (Ba Lan - UCI 365), sau đó ánh xạ bằng độ dời ngành.

### 6.1. Random Forest Classifier (Chọn lọc Đặc trưng)
Tuyển lựa ra các features khách quan bằng hàm làm sạch Entropy:
$$G(t) = 1 - \sum_{i} p_i^2$$
$\Rightarrow Gini\ Impurity$ đào thải các biến dư thừa ở bảng Cân đối và đưa các tỷ số CFO/Đòn bẩy lên đầu rank.

### 6.2. Gradient Boosting (XGBoost Classifier)
Giải quyết hiện tượng *Multicollinearity* mà Ohlson và Altman hay gặp (VD: tương quan nghịch cực mạnh giữa CFO và Nợ).

**Hàm mục tiêu Binary Logistic vắt kiệt mất cân bằng (Imbalanced Loss):**
$$\mathcal{L}(\theta) = -\sum_{i} \left[ y_i \log(\hat{p}_i) + (1-y_i)\log(1-\hat{p}_i) \right] \times \text{scale\_pos\_weight} + \Omega(\theta)$$
Với khoản phạt Cắt tỉa (Regularization term): $\Omega(\theta) = \alpha \|\theta\|_1 + \lambda \|\theta\|_2^2$ nhằm chống Over-fitting khi dự báo ngược trên môi trường BĐS hữu hạn.

### 6.3. Khối Diễm giải (SHAP TreeExplainer - XAI)
Toán học Trò chơi Hợp tác được cấy vào báo cáo xuất Markdown, tính toán đóng góp cận biên (Marginal Contribution):
$$\phi_i = \sum_{S \subseteq N \setminus \{i\}} \frac{|S|!(|N|-|S|-1)!}{|N|!} \left[ v(S \cup \{i\}) - v(S) \right]$$
**Diễn dịch nội tại:** Thay vì trả báo cáo *"PD_XGBoost = 82%"*, hệ thống trả nguyên do: *"+35% từ lực cản Tồn kho, +22% từ Cạn kiệt CFO, -10% từ Đệm tiền mặt."*

---

## 7. Hệ thống Phân loại Rủi ro Tổng hợp (Ngắt Mạch BĐS)

### 7.1. Cấu trúc Trọng số (Composite Weights Formulation)
Hệ số rủi ro $Score_{Composite}$ (thang 0-100) được thay đổi trục tọa độ đối với ngành BĐS:
$$Score_{Comp} = 40\%(XGBoost) + 20\%(\textbf{Altman}_{signal}) + 15\%(Ohlson) + \dots$$
$$ \dots + 15\%(\textbf{Sloan Accruals}_{signal}) + 5\%(Zmijewski) + 5\%(DSCR_{signal})$$
(*Beneish M-Score = 0% trên Bản nhánh BĐS*)

### 7.2. Circuit Breakers (Luật Cưỡng chế Ngắt Mạch Đặc Thù)
Để né sập "Bẫy điểm cao giả" (Mô hình tuyến tính chấm đẹp vì giá trị sổ sách To), Khối `risk_classifier.py` ban hành mệnh lệnh ghi đè cưỡng bức rủi ro dựa trên Dòng tiền thực tế:

```python
# RULE 1: CƯỠNG CHẾ VỠ NỢ LÃI VAY KẾP
IF (CFO_TTM < 0 LIÊN TỤC >= 2 QUÝ) AND (Interest_Coverage_CFO < 1.0):
    => Vô hiệu hóa mọi Score an toàn. Ép Risk_Level = 4 (Danger / Nguy hiểm)

# RULE 2: CẠN KIỆT RUNWAY TÍN DỤNG XUYÊN THẤU
IF Runway_Interest < 1.0 (Số dư Tiền mặt đủ trả lãi < 1 Quý):
    => Rơi xuống vực thẳm tài chính. Ép Risk_Level = 5 (Critical / Nghiêm trọng)
```
*Điều kiện trên đảm bảo không một hệ số ảo nào che chở được tình nguyện vay mượn nợ mới để duy trì lãi nợ cũ.*

---

## 8. Dashboard & Giao diện Báo cáo

Màn hiển thị Streamlit App tích hợp 4 lăng kính Quản trị viên:
1. **Divergence Line Charts (Đứt gãy Sinh lời):** Biểu đồ Line theo dõi song song mảng P&L Lợi nhuận Kế toán (Xanh) vs Dòng thu CFO (Đỏ). Phản ánh nguy cơ chế tác lợi nhuận.
2. **Bar Chart "Khối U Tài Sản":** Phân rã dạng phân lớp cột với tỷ trọng lớn phình ra cho Tồn Kho / Phải Thu của dự án sân sau.
3. **Runway Gauge (Đồng hồ đếm ngược sinh tồn):** Biểu diễn đo cung Quý (Màu đỏ chói nếu dưới cảnh báo sống sót < 2 Kỳ).
4. **Auto-Markdown Output:** Hệ thống trích dẫn các hệ số ra văn bản tường minh hỗ trợ chèn vào bản Cáo bạch Phân Tích (Equity Research Report).

---

## 9. Cơ sở Dữ liệu & Kiểm định

- **Xử lý Thời Gian (Time-Series Validate):** Việc Cross-Validation áp dụng Kỹ thuật trượt thời gian (Chặn rò rỉ quá khứ học tương lai). `Fold(T-1) -> Validate(T)`.
- **Dữ liệu Nhập thô:** `data/companies/` yêu cầu tệp tin .xlsx theo chiều dọc/ngang nhưng bắt buộc cột chu kỳ sở hữu tiền tố thời gian Quý (`Q1 2022`, `Q2-23`).

---

## 10. Hướng dẫn Triển khai

**Khởi tạo Môi trường:**
```bash
python -m venv .venv
source .venv/bin/activate  # Đối với Linux/Mac
# .venv\Scripts\activate   # Đối với Windows
pip install -r requirements.txt
```

**Thực thi Auto-Pipeline cho BĐS:**
```bash
# Phân rã, làm phẳng TTM, trích XGBOOST, chấm Hard Constraint
python pipeline_runner.py --industry REAL_ESTATE

# Giao diện Phân tích trực tuyến (Streamlit Server)
streamlit run src/app.py
```
> Kết quả dạng bảng tổng soát Tín dụng và Giải thích XAI sẽ đổ bộ tại tệp `output/5_reports/portfolio_summary.md`.

---

## 11. Mô hình Định mức Tín dụng (Credit Sizing)

Mục tiêu của lớp này là dịch chuyển từ kết quả xếp loại rủi ro (Risk Level 1-5) và Xác suất vỡ nợ (XGBoost PD%) sang **Hạn mức Tín dụng vay vốn tối đa khả thi ($L_{final}$)**.

Mô hình hoạt động qua hai bộ lọc chính:
1. **Underwriting Dòng tiền (CFADS & DSCR):**
   - **CFADS:** Lấy dòng tiền CFO TTM làm gốc (nếu $\le 0$, hạn mức lập tức bằng 0).
   - **DSCR mục tiêu thích ứng:** Hệ số nền $1.2x$ sẽ bị cộng thêm các khoản phạt nếu doanh nghiệp có rủi ro tài chính tĩnh (vốn lưu động ròng âm, đòn bẩy cao, tỷ lệ tồn kho lớn) hoặc rủi ro AI động ($\Delta \text{DSCR} = \text{PD}_{XGBoost} / 100$).
   - **PMT tối đa:** $\text{PMT}_{max} = \text{CFADS} / \text{DSCR}_{target}$.
   - **Hạn mức cơ sở ($L_{base}$):** Hiện giá của niên kim đều của $\text{PMT}_{max}$ theo lãi suất vay ($r$) và kỳ hạn ($n$).
2. **Hệ thống Chốt chặn (Circuit Breakers) & Chiết khấu (Haircuts):**
   - **Từ chối hoàn toàn ($L_{final} = 0$):** Nếu xảy ra sự kiện ngắt mạch (ICR < 1.0, Vốn chủ $\le 0$, CFO TTM $\le 0$) hoặc rủi ro AI vượt giới hạn ($\text{PD}_{XGBoost} > 55\%$ hoặc Risk Level $\ge 4$).
   - **AI Haircuts:** Giảm $15\%$ hạn mức đối với nhóm rủi ro *Watch* (Level 2) và giảm $40\%$ đối với nhóm rủi ro *Stress* (Level 3).
   - **Leverage Cap (Chốt chặn đòn bẩy):** Đảm bảo an toàn đệm vốn tự có tối thiểu $15\%$, tức $Equity / (Total Debt + L_{final}) \ge 0.15 \Rightarrow L_{final} \le (Equity / 0.15) - Total Debt$.

Chi tiết lý thuyết và hướng dẫn vận hành chuyên sâu được trình bày chi tiết trong tài liệu bổ sung [tham_dinh_han_muc_va_danh_gia.md](file:///f:/mo_hinh_danh_gia_pha_san/phan_tich_pha_san_clone/docs/tham_dinh_han_muc_va_danh_gia.md).

---
**© 2026 — Hệ thống Phân tích Phá sản Nhánh Bất Động Sản**
*Kiến tạo định vị kinh tế lượng từ Ohlson / Altman và Trí tuệ nhận thức Gini/XGBoost*
