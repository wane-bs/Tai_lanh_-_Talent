# Bankruptcy Risk Assessment & Credit Underwriting Pipeline (v2.0)
## Hệ thống Đánh giá Rủi ro Phá sản và Thẩm định Hạn mức Tín dụng (v2.0)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue)](requirements.txt)
[![Streamlit App](https://img.shields.io/badge/Streamlit-1.30%2B-red)](src/app.py)

---

## 🏆 Project Achievements & Credentials / Thành tích & Thông tin Dự án
- **Award / Giải thưởng:** Giải Nhất cuộc thi Nghiên cứu Khoa học Ứng dụng Chuyển đổi số Khoa Tài chính - Kế toán (*Tài trí hội tụ*, 04/2026 - 05/2026).
- **Development Team / Nhóm thực hiện:** Nhóm **Tài lanh & Talent**
- **Members / Các thành viên:**
  - Nguyễn Trung Hiếu
  - Nguyễn Đăng Thiên Lý
  - Bùi Gia Huy
  - Nguyễn Minh Đạt
  - Lê Nguyễn Khánh Vy
  - Huỳnh Hoàng Su Chinh

---

## 📌 Project Overview / Tổng quan Dự án

### [English]
This system represents a comprehensive, modern approach to corporate credit assessment in Vietnam. Traditional models fail to capture the dynamic liquidity of thin-file SMEs and under-report the risks of capital-heavy industries (like Real Estate) due to static inventory valuations. 

To overcome these, this project implements a **Hybrid Cash-Flow Underwriting Pipeline (v2.0)**:
1. **Classical Baseline Filter:** Runs adapted financial formulas (Altman Z'', Beneish M, Ohlson O, Zmijewski, and Sloan Accruals Anomaly).
2. **Machine Learning Predictor:** Resolves multi-collinearity and non-linear patterns using an optimized **XGBoost Classifier** with SHAP explainability.
3. **Adaptive Underwriter:** Translates risk indicators into cash-flow-based credit lines ($L_{final}$) under Basel III constraints (Leverage Cap, Adaptive Target DSCR, AI Haircuts, and Circuit Breakers).

### [Tiếng Việt]
Hệ thống này cung cấp một phương pháp tiếp cận hiện đại và toàn diện trong việc thẩm định tín dụng doanh nghiệp tại Việt Nam. Các mô hình truyền thống thường bỏ lọt rủi ro của các doanh nghiệp "hồ sơ mỏng" (SMEs) hoặc đánh giá sai lệch các ngành đặc thù (như Bất động sản) do coi hàng tồn kho xây dựng dở dang là tài sản ngắn hạn thanh khoản cao.

Để giải quyết vấn đề đó, dự án triển khai **Quy trình Thẩm định Dòng tiền Hỗn hợp (Hybrid) v2.0**:
1. **Màng lọc Logic Thô:** Tính toán các chỉ số kinh điển hiệu chỉnh (Altman Z'' đã trừ tồn kho BĐS, Beneish M-Score phát hiện gian lận dồn tích, Ohlson, Zmijewski, và Sloan Accruals).
2. **Động cơ Ước lượng AI:** Sử dụng **XGBoost Classifier** để ước lượng xác suất vỡ nợ ngắn hạn (PD) phi tuyến tính và giải thích minh bạch bằng cơ chế SHAP.
3. **Thẩm định Hạn mức Thích ứng:** Quy đổi điểm rủi ro thành hạn mức tín dụng bằng tiền mặt ($L_{final}$) dựa trên dòng tiền cốt lõi (CFADS) và các chốt chặn an toàn Basel III.

---

## 🗺️ Documentation Mapping / Sơ đồ Tài liệu chi tiết
To maintain readability, detailed mathematical formulations, theoretical justifications, and business rules are organized inside the [docs/](docs) directory. Click the links below to access specific document chapters:

*   **System Overview & Pipeline Steps:** Read [tong_quan_he_thong_va_dinh_muc_tin_dung.md](docs/3_tong_quan_va_dinh_vi/tong_quan_he_thong_va_dinh_muc_tin_dung.md) for a full overview of the 7-step pipeline.
*   **Scientific Methodology & Literature Review:** Learn about the mathematical foundations of Altman Z'', Ohlson O-Score, Zmijewski, and Sloan Accruals in [phuong_phap_luan_he_thong.md](docs/3_tong_quan_va_dinh_vi/phuong_phap_luan_he_thong.md).
*   **Bankruptcy Theory & XGBoost Logic:** Read [ly_thuyet_du_bao_pha_san.md](docs/1_phan_tich_pha_san/1_1_ly_thuyet_va_phuong_phap_luan/ly_thuyet_du_bao_pha_san.md) and [WHITEPAPER.md](docs/3_tong_quan_va_dinh_vi/WHITEPAPER.md).
*   **Adaptive Underwriting & Credit Sizing Formula:** Detailed credit limit calculations, Target DSCR penalties, and Leverage Cap logic are explained in [tham_dinh_han_muc_va_danh_gia.md](docs/2_han_muc_tin_dung/2_2_tham_dinh_va_dinh_muc/tham_dinh_han_muc_va_danh_gia.md).
*   **Cash Flow Scorecard Calibration:** Read the Weight of Evidence (WOE) scorecard design in [cash_flow_scoring_methodology.md](docs/2_han_muc_tin_dung/2_1_cham_diem_dong_tien/cash_flow_scoring_methodology.md).
*   **Case Studies:**
    *   **Novaland (NVL) Bankruptcy Risk & Real Estate Adjustment:** [bao_cao_phan_tich_nvl.md](docs/1_phan_tich_pha_san/1_2_bao_cao_va_case_study/bao_cao_phan_tich_nvl.md) & [giai_phap_va_du_bao_nvl.md](docs/1_phan_tich_pha_san/1_2_bao_cao_va_case_study/giai_phap_va_du_bao_nvl.md).
    *   **Nam Viet Corp (ANV) Cash Flow & Annuity Amortization Plan:** [dien_giai_cham_diem_dong_tien_anv.md](docs/2_han_muc_tin_dung/2_1_cham_diem_dong_tien/dien_giai_cham_diem_dong_tien_anv.md) & [dien_giai_han_muc_va_tra_no_anv.md](docs/2_han_muc_tin_dung/2_2_tham_dinh_va_dinh_muc/dien_giai_han_muc_va_tra_no_anv.md).

---

## 💻 Project Structure / Cấu trúc Dự án
```
.
├── data/                           # Data Storage / Thư mục dữ liệu
│   ├── companies/                  # Corporate Financial Statements (XLSX) / Dữ liệu báo cáo tài chính doanh nghiệp
│   ├── polish/                     # Polish Corporate Bankruptcy Database (UCI) / Dữ liệu phá sản doanh nghiệp Ba Lan
│   └── taiwanese/                  # Taiwanese Corporate Bankruptcy Database (Kaggle) / Dữ liệu phá sản doanh nghiệp Đài Loan
├── docs/                           # Comprehensive Academic & Technical Docs / Hệ thống tài liệu học thuật & kỹ thuật
├── models/                         # Pre-trained ML Models (joblib) / File nhị phân lưu trữ mô hình ML đã train
├── src/                            # Source Code / Mã nguồn hệ thống
│   ├── app.py                      # Main Streamlit Dashboard Application / File chạy giao diện chính Streamlit
│   ├── etl.py                      # ETL Processor (Quarterly & TTM Calculations) / Xử lý ETL và lũy kế di động
│   ├── calculator.py               # Classical Model Calculators / Tính toán mô hình cổ điển
│   ├── cash_flow_scorer.py         # Cash Flow Scorecard Algorithm / Chấm điểm dòng tiền WOE
│   ├── credit_model.py             # Underwriting & Credit Sizing Engine / Động cơ tính hạn mức & trả nợ
│   ├── feature_engine.py           # Feature Engineering & Imputation / Xử lý đặc trưng & Điền khuyết dữ liệu
│   ├── model_engine.py             # XGBoost Training & SHAP Explainer / Huấn luyện mô hình & giải thích SHAP
│   ├── risk_classifier.py          # Risk Categorization & Overrides / Phân hạng rủi ro & Rule cứng
│   └── scenario_simulator.py       # Stress Testing Scenario Engine / Giả lập kịch bản chịu đựng rủi ro
├── .gitignore                      # Git Ignore Settings / File cấu hình Git
├── LICENSE                         # License (Apache 2.0) / Bản quyền mã nguồn mở
├── pipeline_runner.py              # Run Full Pipeline locally / Script chạy toàn bộ pipeline
├── requirements.txt                # Dependencies / File danh sách thư viện yêu cầu
├── run_backtest.py                 # Run Backtesting Suite / Script chạy backtest
├── run_retrain_full.py             # Retrain ML Models on raw datasets / Script train lại mô hình học máy
├── run_simulation.py               # Run Scenario Stress Test Simulation / Script giả lập stress test
└── test_fixes.py                   # Automated Test Suite / Bộ kiểm thử tự động phục vụ CI
```

---

## 🛠️ Installation & Setup / Cài đặt & Khởi tạo

### 1. Prerequisites / Yêu cầu hệ thống
- **Python 3.10** or higher / phiên bản 3.10 trở lên.
- **Git** installed / Đã cài đặt Git.

### 2. Clone the Repository / Tải mã nguồn về máy
```bash
git clone https://github.com/yourusername/mo-hinh-danh-gia-pha-san.git
cd mo-hinh-danh-gia-pha-san
```

### 3. Create a Virtual Environment / Khởi tạo môi trường ảo
* **Windows (PowerShell / Command Prompt):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\activate
  ```
* **macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 4. Install Dependencies / Cài đặt các thư viện
```bash
pip install -r requirements.txt
```

---

## 🚀 Execution & Usage Guide / Hướng dẫn Vận hành

### 1. Launch the Streamlit Dashboard / Chạy ứng dụng Dashboard
Run the Streamlit application to open the interactive risk analysis dashboard:
```bash
streamlit run src/app.py
```
*The app will automatically open in your default browser at `http://localhost:8501`.*

### 2. Run Local Automatic Tests / Chạy bộ kiểm thử tự động
Ensure code integrity by running the test suite (used by GitHub Actions CI):
```bash
python test_fixes.py
```
Expected output: `🎉 TẤT CẢ 7 TESTS PASS — Các sửa đổi hoạt động đúng!`

### 3. Train Models from Scratch / Huấn luyện lại mô hình học máy
To retrain XGBoost and Random Forest on Polish & Taiwanese datasets and regenerate files in `models/`:
```bash
python run_retrain_full.py
```

### 4. Run Backtesting & Simulations / Chạy Backtest & Giả lập
- **Run Backtesting Suite:**
  ```bash
  python run_backtest.py
  ```
- **Run Stress Testing Simulation:**
  ```bash
  python run_simulation.py
  ```

---

## 🔒 Security & Data Privacy / Bảo mật & Bản quyền Dữ liệu
All corporate data included in the `data/companies/` directory contains public information extracted from official financial reports of listed companies on the Vietnamese stock market (HOSE/HNX). No private, proprietary, or client-sensitive data is stored in this repository.

---

## 📄 License / Bản quyền
This project is open-source and licensed under the terms of the [Apache License 2.0](LICENSE).
