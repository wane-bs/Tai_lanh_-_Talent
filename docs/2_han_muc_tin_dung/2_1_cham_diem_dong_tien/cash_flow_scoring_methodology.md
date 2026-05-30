# Phương pháp luận Mô hình Credit Scoring dựa trên Dòng tiền

---

## 1. Triết lý thiết kế

Mô hình truyền thống hỏi: **"Anh đã trả nợ như thế nào trong quá khứ?"**

Mô hình này hỏi: **"Anh có khả năng tạo tiền để trả nợ trong tương lai không?"**

```
Traditional Scoring          Cash Flow Scoring
─────────────────────        ──────────────────────────
CIC history          →       Bank transaction patterns
Collateral value     →       Revenue generation capacity
Financial statements →       Real-time cash flow signals
Static snapshot      →       Dynamic, rolling window
```

---

## 2. Khung lý thuyết: 5C → 5CF

Tái diễn giải 5C truyền thống dưới góc nhìn dòng tiền:

| 5C Truyền thống | 5CF Cash Flow Version | Đo bằng gì |
|---|---|---|
| **Character** | Payment Behavior | Tần suất trễ hạn thanh toán nhà cung cấp, tiền thuê |
| **Capacity** | Debt Service Coverage | DSCR = OCF / Tổng nghĩa vụ nợ |
| **Capital** | Cash Buffer | Số ngày tiền mặt dự phòng trung bình |
| **Conditions** | Revenue Resilience | Mức độ phục hồi sau cú sốc mùa vụ |
| **Collateral** | Receivable Quality | Chất lượng và tính thanh khoản của khoản phải thu |

---

## 3. Kiến trúc Feature Engineering

Đây là phần **kỹ thuật cốt lõi** — biến raw transaction thành tín hiệu có ý nghĩa.

### 3.1 Phân loại giao dịch

```
Raw Transactions
       │
       ├── Inflow
       │     ├── Revenue inflow      (khách hàng trả tiền)
       │     ├── Loan inflow         (vay mới → loại khỏi revenue)
       │     └── Transfer inflow     (nội bộ → loại khỏi revenue)
       │
       └── Outflow
             ├── COGS payments       (nhà cung cấp)
             ├── Payroll             (lương)
             ├── Debt service        (trả nợ gốc + lãi)
             ├── Tax                 (thuế)
             └── Owner withdrawal    (rút vốn chủ)
```

> **Quan trọng:** Phải lọc sạch inter-account transfers và loan inflows trước khi tính bất kỳ metric nào.

### 3.2 Feature Groups

**GROUP A — Volume & Scale**
```
A1. Average Monthly Revenue (AMR)          = Mean(monthly_inflow, 6M)
A2. Revenue Run Rate                       = AMR × 12
A3. Peak-to-Average Ratio                  = max_month / AMR
A4. Minimum Monthly Revenue               = min(monthly_inflow, 6M)
```

**GROUP B — Stability & Predictability**
```
B1. Revenue Volatility                     = StdDev(monthly_inflow) / AMR
B2. Coefficient of Variation (CV)          = σ / μ  [target: CV < 0.4]
B3. Consecutive Positive Months           = streak của tháng có inflow > 0
B4. Inflow Regularity Score               = % tháng có inflow trong range [μ±1σ]
```

**GROUP C — Trend & Momentum**
```
C1. Revenue Growth Rate (MoM)             = (M0 - M-1) / M-1
C2. Revenue Growth Rate (YoY)             = (M0 - M-12) / M-12
C3. 3M vs 6M Trend                        = Avg(last 3M) / Avg(3M-6M ago) - 1
C4. Trend Direction Score                 = slope của linear regression trên 12M
```

**GROUP D — Debt Service Coverage**
```
D1. DSCR                                  = Operating CF / (Principal + Interest)
D2. Free Cash Flow Margin                 = (Inflow - OpEx - CapEx) / Inflow
D3. Debt Burden Ratio                     = Total debt payments / AMR
D4. Interest Coverage                     = EBITDA proxy / Interest expense
```

**GROUP E — Liquidity Behavior**
```
E1. Cash Buffer Days                      = Avg_balance / Daily_avg_outflow
E2. Minimum Balance / AMR                 = Safety cushion ratio
E3. Overdraft Frequency                   = Số lần số dư âm hoặc gần 0 / 6M
E4. Cash Conversion Cycle proxy           = Lag giữa outflow (mua hàng) và inflow (thu tiền)
```

**GROUP F — Counterparty Quality**
```
F1. Customer Concentration (HHI)          = Σ(revenue_share_i²) — thấp là tốt
F2. Top-1 Customer Share                  = % doanh thu từ khách lớn nhất
F3. Supplier Payment Timeliness           = % thanh toán đúng hạn
F4. New vs Returning Customer Ratio       = Tín hiệu về retention
```

**GROUP G — Integrity & Fraud Signals**
```
G1. Cross-source Consistency              = |Bank inflow - Invoice revenue| / Invoice revenue
G2. Round-number Transaction Rate         = % giao dịch là số tròn (10M, 50M,...) — dấu hiệu gian lận
G3. Self-transfer Ratio                   = Intra-owner transfers / Total inflow
G4. Timing Anomaly Score                  = Giao dịch bất thường trước ngày nộp hồ sơ
```

---

## 4. Xây dựng Scorecard

### 4.1 Lựa chọn mô hình theo giai đoạn

```
Giai đoạn 1 (cold start, <500 hồ sơ)
└── Logistic Regression + WOE/IV
    → Interpretable, dễ giải thích cho regulator và credit committee

Giai đoạn 2 (500-5000 hồ sơ)
└── Gradient Boosting (XGBoost / LightGBM)
    → Bắt được non-linear relationships

Giai đoạn 3 (>5000 hồ sơ + time-series data)
└── LSTM / Temporal Fusion Transformer
    → Model trực tiếp trên chuỗi giao dịch theo thời gian
```

### 4.2 Scorecard Design (Giai đoạn 1)

Dùng **WOE (Weight of Evidence)** để biến continuous features thành bins:

```
Ví dụ: Feature DSCR

DSCR Range     WOE      Điểm quy đổi
─────────────────────────────────────
≥ 2.0          +1.85    +25 điểm
1.5 – 2.0      +0.92    +15 điểm
1.25 – 1.5     +0.31    +8 điểm
1.0 – 1.25     -0.18    -3 điểm
0.75 – 1.0     -0.74    -12 điểm
< 0.75         -1.52    -25 điểm
```

### 4.3 Trọng số nhóm (đề xuất ban đầu)

| Feature Group | Weight |
|---|---|
| D. Debt Service Coverage | 25% |
| B. Stability & Predictability | 20% |
| C. Trend & Momentum | 15% |
| E. Liquidity Behavior | 15% |
| F. Counterparty Quality | 10% |
| A. Volume & Scale | 10% |
| G. Integrity Signals | 5% |
| **Total Score** | **0 – 1000** |

---

## 5. Phân khúc rủi ro & Quyết định

| Score Band | Risk Grade | PD Estimate | Quyết định |
|---|---|---|---|
| 850 – 1000 | A+ | < 1% | Auto-approve, rate ưu đãi |
| 700 – 849 | A | 1% – 3% | Auto-approve |
| 600 – 699 | B | 3% – 7% | Approve + điều kiện (tài sản bổ sung) |
| 500 – 599 | C | 7% – 15% | Manual review bắt buộc |
| < 500 | D | > 15% | Decline / yêu cầu thêm 3-6 tháng data |

---

## 6. Validation Framework

### 6.1 Các chỉ số đánh giá mô hình

```
Discrimination:   AUC-ROC  ≥ 0.75  (tốt), ≥ 0.85 (xuất sắc)
                  KS Stat  ≥ 0.30

Calibration:      Brier Score — đo độ chính xác của xác suất
                  Hosmer-Lemeshow Test — p > 0.05

Stability:        PSI (Population Stability Index) < 0.1 mỗi quý
                  CSI (Characteristic Stability Index) theo từng feature
```

### 6.2 Backtesting & Champion-Challenger

```
Champion Model  ──── 80% traffic ────►  Production decisions
                                         Monitor: actual default rate
Challenger Model ─── 20% traffic ────►  A/B test
                                         So sánh AUC sau 6 tháng
```

---

## 7. Vòng đời mô hình (Model Lifecycle)

```
         Data             Feature          Model           Deploy
        Ingestion    →   Engineering  →   Training    →   & Monitor
            │                │                │               │
        Làm sạch         WOE/IV          Train/Val/Test    PSI alert
        Phân loại        Selection       Cross-validate    Retrain trigger
        Audit trail      Correlation     Hyperparameter    Champion-challenger
```

**Trigger retrain** khi:
- PSI > 0.25 (population drift lớn)
- AUC giảm > 5% so với baseline
- Default rate thực tế lệch > 30% so với dự báo

---

## 8. Những quyết định thiết kế quan trọng

**Lookback window nên là bao lâu?**
Dùng **12 tháng** làm baseline; thêm **3 tháng gần nhất** với trọng số cao hơn để bắt momentum. Dưới 6 tháng thì không đủ tin cậy.

**Xử lý seasonality như thế nào?**
Chuẩn hóa bằng cách so sánh cùng kỳ năm trước (YoY), không phải tháng trước (MoM) đơn thuần, để tránh phạt sai các ngành có mùa vụ rõ ràng như nông nghiệp, bán lẻ.

**Doanh nghiệp mới dưới 12 tháng?**
Áp dụng **thin-file model** riêng: trọng số cao hơn cho Integrity signals và Counterparty Quality; hạn mức cho vay thấp hơn; review lại sau 6 tháng.
