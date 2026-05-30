# KẾT QUẢ DỰ BÁO VÀ KỊCH BẢN DUY TRÌ (2025 - 2026)

## Luận giải: Bóc tách Phương pháp Thủ công vs. Thiết chế "Ngắt mạch BĐS"
Để thiết lập cơ sở vững chắc cho dự phóng kịch bản 2026 và các giải pháp quản trị, cần phân tích sự đối lập gay gắt giữa góc nhìn sổ sách và thực trạng dòng tiền trong Bảng Phân Tích (2021-2025):

1. **Góc nhìn Kế toán thủ công (Khía cạnh thiếu vắng "Ngắt mạch"):** 
   Quan sát Bảng cân đối lịch sử, Z-Score của NVL đã có dấu hiệu "phục hồi kỹ thuật" (tăng từ 2.37 của năm 2024 lên 2.75 vào 2025 nhờ nỗ lực giãn nợ và tăng vốn). Đồng thời, xác suất vỡ nợ dự báo chuẩn (PD% XGBoost) của NVL tính ra rất thấp, chỉ quanh **4.4% - 6.5%**. **Nếu KHÔNG có cơ chế Ngắt mạch BĐS chuyên biệt**, sự hòa trộn trọng số giữa PD thấp và Z-Score > 2.6 sẽ giúp doanh nghiệp đạt Điểm Rủi Ro Tổng Hợp cực kỳ khả quan, đưa trực tiếp về mốc **🟢 An toàn (Safe)** trên hệ thống chuẩn. Điều này tạo ra một "ảo giác sổ sách" cực kỳ nguy hiểm.
   
2. **Góc nhìn Máy học Thực tiễn (Bản lề định hình rủi ro):**
   Hệ thống kiểm soát BĐS đã can thiệp thông qua Cơ chế Ngắt Mạch. Nó đối chiếu mốc Z-Score với việc **CFO_TTM** duy trì âm sâu và giãn nở liên tục suốt 3 năm (-3,182 tỷ năm 2023 ➔ -6,145 tỷ năm 2025). Thêm vào đó, thanh khoản ròng (`WC_adj`) bị đóng băng hoàn toàn bởi 61% Tồn Kho khổng lồ. Thuật toán tự động (CFO < 0 liên tiếp và ICR < 1) bóp nghẹt toàn bộ đà phục hồi kỹ thuật, đánh tụt tín nhiệm thẳng xuống **🔴 Nguy hiểm**.

*Kết luận cấu trúc:* Việc hệ thống định lượng triệt tiêu điểm phục hồi hình thức đã chứng minh rủi ro thanh khoản của NVL không thể hóa giải bằng bút toán kế toán. Sự thật này là tiền đề trực tiếp để xây dựng Kịch bản duy trì và đề xuất dứt điểm nhắm vào Tồn Kho & Đảo Nợ dưới đây.

---

## 1. Kịch bản duy trì hiện trạng (Status Quo)
Dữ liệu kiểm định lịch sử cho thấy sự xói mòn tài chính nghiêm trọng khi dòng tiền CFO suy giảm mạnh từ mức âm **3.182 tỷ VND (2023)** xuống âm khoảng **5.971 tỷ VND (2024)**. Nếu duy trì trạng thái này trong kịch bản dự phóng 2026:
*   **Vòng lặp thâm hụt kéo dài:** Mức CFO năm 2025 (hiện tại) tiếp tục duy trì ở mức âm 6.145 tỷ VND, kịch bản dự phóng 2026 sẽ tiếp tục chịu rủi ro thâm hụt tương tự hoặc nghiêm trọng hơn. 
*   **Áp lực trả lãi & DSCR:** Hệ số Khả năng trả nợ (DSCR Stressed) chạm mức **-0.071** (2024) và tỷ lệ bao phủ lãi vay (ICR) âm sâu tới **-41.39** vào năm 2025. Nghĩa là thu nhập hoạt động hoàn toàn không có khả năng trang trải bất kỳ khoản nợ/lãi vay nào. Dù chỉ số **Runway Lãi vay** bề ngoài có dấu hiệu dư thừa về mặt kỹ thuật, nhưng áp lực dòng tiền thật (Cash Flow) đè nặng liên tiếp cảnh báo về hệ thống cho chu kỳ 2026.
*   **Rủi ro Technical Insolvency (Mất khả năng thanh toán kỹ thuật):** Ngay cả khi Z''-Score có dao động hồi phục nhẹ quanh 2.75 tại năm 2025, thực chất đó là biến động viền quanh lằn ranh "Căng thẳng". Nếu không giải quyết được biến số ngắt mạch (CFO âm liên tiếp), sự phục hồi bề mặt kỹ thuật trên giấy tờ vẫn có thể nhanh chóng bị bóp nghẹt nếu một nút thắt thanh khoản đột ngột bị kéo lại trong năm 2026.

### BẢNG SO SÁNH KỊCH BẢN DUY TRÌ (2025 vs 2026) DỰA TRÊN MÔ PHỎNG MÁY HỌC
| Chỉ tiêu (Đơn vị: VND/Hệ số) | 2025 (Hiện tại) | 2026 (Dự phóng Status Quo) | Biến động |
| :--- | :---: | :---: | :---: |
| **Z''-Score (Hiệu chỉnh BĐS)** | 2.75 | **2.68** | -0.07 |
| **PD% Xác suất Phá sản (XGBoost)**| 4.44% | **4.57%** | +0.13% |
| **Thanh khoản ròng (WC_adj/TA)** | -0.170 | **-0.186** | -0.02 |
| **Dòng tiền CFO TTM (Tỷ VND)** | -6145 | **-7627** | -1482 |
| **Tỷ lệ Tồn kho / TTS** | 61.4% | **62.5%** | Tăng nhẹ (Cạn kiệt Total Assets) |
| **Trạng thái rủi ro** | 🔴 Nguy hiểm | ⚫ Nghiêm trọng | Báo động đỏ |

## 2. Những điểm trọng yếu cần tập trung cải thiện
Dựa trên kết quả phân tích độ nhạy của chỉ số đóng góp mức độ phá sản (SHAP Feature Importance Analysis) từ kiểm định mô hình, dưới đây là các gốc rễ tối quan trọng cần khắc phục có cơ sở toán học rõ ràng:

*   **Mở khóa Hàng tồn kho (Lõi rủi ro số 1 - 146.000 tỷ VND):** Tồn kho chiếm mức báo động trên 61% tổng tài sản. Căn cứ từ SHAP cho thấy biến số tỷ lệ Tài sản siêu ngắn hạn / Nợ nợ ngắn hạn (`ca_cl`) nằm ở top 3 lực cản lớn nhất. Việc loại bỏ trực tiếp Tồn kho không thanh khoản ra khỏi mô hình (CA - Inv) là nguyên nhân chính khiến vốn khả dụng của NVL bị gọt dũa. Rã đông tồn kho thành dòng tài chính là chìa khóa sống còn.
*   **Đảo chiều dòng tiền CFO:** Nhằm cải thiện độ tin cậy của chỉ số Dòng tiền / Tổng Nợ (`cf_td`) - một chỉ báo luôn nằm trong top 10 có tính chất giảm trừ nguy cơ vỡ nợ (PD). Quan trọng nhất là doanh nghiệp cần chặn đứng chuỗi CFO < 0 liên tiếp để không rơi vào vùng bị kích ứng còi báo động "Ngắt mạch BĐS".
*   **Vá vỡ Vốn lưu động chuẩn bị (WC_adj):** Trọng tâm nằm ở việc phục hồi số âm của tỷ lệ `wc_ta` (một biến thuộc top nhạy cảm nhất về cấu trúc lỏng). Các thanh khoản ngắn hạn phải có thể trực tiếp mang sang đắp vào nợ đến hạn để cởi trói gánh nặng vốn lưu động ảo mà doanh nghiệp đang mang.

---

# KIẾN NGHỊ VÀ GIẢI PHÁP QUẢN TRỊ CHIẾN LƯỢC

### **Cấp bách (Short-term):**
1.  **Hạ chuẩn thanh lý tồn kho:** Chấp nhận bán chiết khấu sâu để thu hồi dòng tiền mặt ngay lập tức, ưu tiên cứu chỉ số WC_adj.
2.  **Đàm phán hoán đổi nợ (Debt-to-Asset Swap):** Giảm áp lực lãi vay bằng cách chuyển nhượng cổ phần dự án cho chủ nợ.

### **Chiến lược (Mid-term):**
1.  **Mô hình "Light Asset":** Giảm dần tỷ trọng tồn kho/tổng tài sản xuống mức <40% để tăng tính linh hoạt.
2.  **Cơ chế Ngắt mạch (Circuit Breakers):** Tuyệt đối không đầu tư dự án mới nếu Runway Lãi vay (Tiền mặt/Lãi vay quý) nhỏ hơn 4 quý.

### **Kết luận từ mô hình:**
Hệ thống xác định trạng thái của NVL là **"Cảnh báo Đỏ (High Alert)"**. Sự phục hồi của Z-Score hiện tại (2025) chỉ mang tính kỹ thuật; sức khỏe thực sự trong năm dự phóng 2026 phụ thuộc hoàn toàn vào tốc độ giải phóng 146 ngàn tỷ VND hàng tồn kho.

---
*Người thực hiện: Antigravity AI Consultant — Hệ thống Kiểm soát v2.0 (BDS Enhanced)*
