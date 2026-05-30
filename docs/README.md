# CẨM NANG HƯỚNG DẪN & HỆ THỐNG HÓA TÀI LIỆU

Bộ tài liệu của hệ thống **Bankruptcy Risk Assessment & Credit Underwriting Pipeline (v2.0)** được tổ chức lại một cách khoa học để phục vụ việc quản lý, tra cứu và vận hành hệ thống.

---

Hệ thống đánh giá rủi ro phá sản và thẩm định hạn mức tín dụng được khởi xướng nhằm giải quyết bài toán tiếp cận vốn của các doanh nghiệp SME tại Việt Nam, nơi các phương pháp chấm điểm truyền thống dựa trên tài sản thế chấp đang bộc lộ nhiều hạn chế.

## BẢN ĐỒ TỔ CHỨC TÀI LIỆU (DOCUMENTATION TREE)

```
docs/
├── README.md (Tài liệu hướng dẫn này)
├── 1_phan_tich_pha_san/               # PHÂN HỆ PHÂN TÍCH PHÁ SẢN (BANKRUPTCY ANALYSIS)
│   ├── 1_1_ly_thuyet_va_phuong_phap_luan/
│   │   ├── ly_thuyet_du_bao_pha_san.md
│   │   └── nhan_dien_nguy_co_va_phap_ly_pha_san.md
│   └── 1_2_bao_cao_va_case_study/
│       ├── phan_tich_mo_hinh_tai_chinh_ban_le.md
│       ├── bao_cao_phan_tich_nvl.md
│       └── giai_phap_va_du_bao_nvl.md
├── 2_han_muc_tin_dung/                # PHÂN HỆ HẠN MỨC TÍN DỤNG (CREDIT UNDERWRITING)
│   ├── 2_1_cham_diem_dong_tien/
│   │   ├── cash_flow_scoring_methodology.md
│   │   ├── dien_giai_cham_diem_dong_tien_anv.md
│   │   ├── bao_cao_chi_tiet_cfo_growth_anv.md
│   │   └── he_thong_danh_gia_tin_dung_dong_tien.md
│   └── 2_2_tham_dinh_va_dinh_muc/
│       ├── credit_scoring_framework.md
│       ├── tham_dinh_han_muc_va_danh_gia.md
│       └── dien_giai_han_muc_va_tra_no_anv.md
└── 3_tong_quan_va_dinh_vi/            # CHUNG / TỔNG QUAN HỆ THỐNG
    ├── tong_quan_he_thong_va_dinh_muc_tin_dung.md
    ├── phuong_phap_luan_he_thong.md
    ├── dinh_vi_chuong_trinh_trong_buc_tranh_toan_canh.md
    ├── WHITEPAPER.md
    ├── ho_tro_ly_thuyet_myers_yescombe.md
    └── he_thong_du_lieu_xep_hang_tin_dung_the_gioi.md
```

---

## GIỚI THIỆU CHI TIẾT TỪNG TÀI LIỆU

### 📂 PHÂN HỆ 1: PHÂN TÍCH PHÁ SẢN (BANKRUPTCY ANALYSIS)
Chuyên biệt về việc đánh giá xác suất phá sản (PD), nhận diện dấu hiệu kiệt quệ tài chính bằng các mô hình toán học và học máy.

#### 1.1 Lý thuyết & Phương pháp luận
*   `ly_thuyet_du_bao_pha_san.md`: Cung cấp nền tảng lý thuyết về hệ thống chỉ số tài chính (thanh khoản, trả nợ, dòng tiền) và cơ chế hợp nhất giữa mô hình truyền thống với học máy (XGBoost).
*   `nhan_dien_nguy_co_va_phap_ly_pha_san.md`: Nhận diện nguy cơ kiệt quệ tài chính, khía cạnh pháp lý theo Luật Phá sản 2014 và các giải pháp tái cấu trúc doanh nghiệp.

#### 1.2 Báo cáo & Case Study thực tế
*   `phan_tich_mo_hinh_tai_chinh_ban_le.md`: Phân tích đặc thù của các mô hình chấm điểm khi áp dụng vào ngành Bán lẻ Việt Nam (vấn đề vốn lưu động âm do chiếm dụng vốn của nhà cung cấp).
*   `bao_cao_phan_tich_nvl.md`: Báo cáo thực tế về sức khỏe tài chính và rủi ro thanh khoản của Novaland (NVL) giai đoạn 2021-2025.
*   `giai_phap_va_du_bao_nvl.md`: Dự phóng kịch bản 2026 cho Novaland dựa trên cơ chế ngắt mạch BĐS và các đề xuất giải pháp tháo gỡ điểm nghẽn tồn kho.

---

### 📂 PHÂN HỆ 2: HẠN MỨC TÍN DỤNG (CREDIT UNDERWRITING)
Tập trung vào phương pháp luận chấm điểm dòng tiền và mô hình tính toán công suất nợ tối đa (Credit Sizing) cho doanh nghiệp.

#### 2.1 Chấm điểm dòng tiền (Cash Flow Scoring)
*   `cash_flow_scoring_methodology.md`: Đặc tả toán học cho thẻ điểm dòng tiền sử dụng kỹ thuật tối ưu hóa Weight of Evidence (WOE) cùng hiệu chuẩn hồi quy Logistic.
*   `dien_giai_cham_diem_dong_tien_anv.md`: Case study thực tế diễn giải cách chấm điểm dòng tiền chi tiết cho Thủy sản Nam Việt (ANV) theo quý.
*   `bao_cao_chi_tiet_cfo_growth_anv.md`: Báo cáo thống kê chuyên sâu phân tích sự suy giảm dòng tiền hoạt động kinh doanh (CFO) của ANV, chi tiết theo Bảng cân đối kế toán.
*   `he_thong_danh_gia_tin_dung_dong_tien.md`: Tổng hợp toàn cảnh, phương pháp luận chi tiết và case study thực tế (Minh Phát) của mô hình đánh giá tín dụng doanh nghiệp dựa trên dòng tiền.

#### 2.2 Thẩm định & Định mức hạn mức
*   `credit_scoring_framework.md`: Khung lý thuyết tổng quát về hệ thống chấm điểm tín dụng và phương thức tính toán định mức nợ vay.
*   `tham_dinh_han_muc_va_danh_gia.md`: Hướng dẫn thẩm định hạn mức vay thích ứng, giải trình chi tiết về công thức dòng tiền trả nợ khả dụng (CFADS), hệ số phạt Target DSCR và các chốt chặn ngắt mạch đòn bẩy.
*   `dien_giai_han_muc_va_tra_no_anv.md`: Báo cáo thẩm định chi tiết hạn mức cho vay tối đa và kế hoạch trả nợ (Niên kim đều vs Gốc đều) thực tế của Nam Việt (ANV).

---

### 📂 PHÂN HỆ 3: TỔNG QUAN & ĐỊNH VỊ (OVERVIEW & POSITIONING)
Các tài liệu mang tính hệ thống, cấu trúc tổng thể và định vị giải pháp phần mềm trên bản đồ công nghệ thế giới.

*   `tong_quan_he_thong_va_dinh_muc_tin_dung.md`: Tài liệu hướng dẫn toàn diện nhất về kiến trúc pipeline 7 bước, chi tiết luồng xử lý và cách vận hành Tab Định mức Hạn mức trên giao diện Streamlit.
*   `phuong_phap_luan_he_thong.md`: Hệ thống hóa khung lý thuyết khoa học và các nghiên cứu khoa học kinh điển hỗ trợ làm điểm tựa học thuật cho chương trình (Altman, Ohlson, Zmijewski, Sloan, Jensen & Meckling, Chen & Guestrin).
*   `dinh_vi_chuong_trinh_trong_buc_tranh_toan_canh.md`: Đối chiếu so sánh hệ thống hiện tại với các hệ thống Bureau truyền thống và các nền tảng AI/Cash Flow Underwriting hiện đại trên thế giới.
*   `WHITEPAPER.md`: Sách trắng kỹ thuật đặc tả các phương trình toán học, cơ chế xử lý ngoại lệ (missing values), và thuật toán xử lý dữ liệu báo cáo tài chính của doanh nghiệp BĐS.
*   `ho_tro_ly_thuyet_myers_yescombe.md`: Phân tích chi tiết về cơ sở hỗ trợ lý thuyết từ nghiên cứu của Stewart C. Myers (1977) và E. R. Yescombe (2002) cho mô hình hạn mức nợ vay thích ứng.
*   `he_thong_du_lieu_xep_hang_tin_dung_the_gioi.md`: Tổng quan thế giới về các nguồn dữ liệu thế hệ mới (Alternative Data, Open Banking) và các nhóm thế lực chính trên thị trường xếp hạng tín dụng toàn cầu.

---
*Tài liệu quản lý hệ thống lưu trữ — Bankruptcy Assessment & Credit Underwriting Pipeline v2.0*
