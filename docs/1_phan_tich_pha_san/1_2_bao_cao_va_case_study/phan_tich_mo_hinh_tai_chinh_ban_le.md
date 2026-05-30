### **1\. Mô hình Altman Z''-Score (Emerging Markets)**

**Cơ sở khoa học:** Phương pháp phân tích biệt thức đa biến (Multivariate Discriminant Analysis \- MDA).

**Đặc thù ứng dụng tại Việt Nam & Ngành Bán lẻ:**

* **Vấn đề Vốn lưu động ($X\_1$):** Các doanh nghiệp bán lẻ lớn (như MWG, WinCommerce) thường chiếm dụng vốn của nhà cung cấp, dẫn đến **Vốn lưu động (Working Capital) âm**. Trong mô hình Altman, điều này làm giảm điểm số $Z''$ đáng kể, dễ đẩy doanh nghiệp vào "Vùng xám" dù dòng tiền hoạt động vẫn rất mạnh.  
* **Cấu trúc vốn:** Tại Việt Nam, các nhà bán lẻ đang trong giai đoạn mở rộng thường có tỷ lệ nợ vay cao để tài trợ cho hàng tồn kho và điểm bán. Chỉ số $X\_4$ (Vốn chủ sở hữu/Tổng nợ) sẽ bị kéo thấp, gây ra sai số về "nguy cơ phá sản" nếu không xét đến tốc độ quay vòng hàng tồn kho.  
* **Đề xuất:** Hiệu chỉnh trọng số $X\_1$ bằng cách cộng ngược các khoản phải trả người bán ngắn hạn nếu doanh nghiệp có quyền thương lượng lớn.

### **2\. Mô hình Beneish M-Score**

**Cơ sở khoa học:** Lý thuyết Kế toán tích cực (Positive Accounting Theory) và phân tích các biến số tích lũy (Accruals).

**Đặc thù ứng dụng tại Việt Nam & Ngành Bán lẻ:**

* **Chỉ số SGI (Sales Growth Index):** Ngành bán lẻ Việt Nam có tính tăng trưởng nóng. Một chỉ số $SGI$ cao thường được Beneish coi là dấu hiệu của thao túng doanh thu, nhưng trong bối cảnh thị trường đang mở rộng (Penetration), đây là tăng trưởng thực.  
* **Chỉ số DSRI (Days Sales in Receivables Index):** Ngành bán lẻ chủ yếu thu tiền mặt/chuyển khoản ngay. Nếu $DSRI$ tăng bất thường, đây là tín hiệu cực kỳ nhạy bén cho thấy doanh nghiệp đang đẩy hàng cho các đại lý ảo hoặc ghi nhận doanh thu trước (Channel Stuffing) để làm đẹp báo cáo IPO hoặc phát hành trái phiếu.  
* **Thách thức:** Hệ thống kế toán Việt Nam (VAS) cho phép vốn hóa một số chi phí thuê mặt bằng, có thể làm biến dạng chỉ số $AQI$ (Asset Quality Index).

### **3\. Mô hình Ohlson O-Score**

**Cơ sở khoa học:** Phương pháp hồi quy Logistic (Logit), tính toán xác suất phá sản $P(D)$.

**Đặc thù ứng dụng tại Việt Nam & Ngành Bán lẻ:**

* **Biến quy mô ($SIZE$):** Ohlson sử dụng $log(Total Assets)$. Tại Việt Nam, do lạm phát và định giá lại tài sản không thường xuyên, biến $SIZE$ có thể không phản ánh đúng vị thế thị trường của nhà bán lẻ so với các đối thủ ngoại.  
* **Độ trễ của dữ liệu:** Mô hình Ohlson rất nhạy với biến $CL/CA$ (Nợ ngắn hạn/Tài sản ngắn hạn). Với đặc thù bán lẻ Việt Nam sử dụng đòn bẩy ngắn hạn lớn để tài trợ tài sản dài hạn (mismatch kỳ hạn), xác suất $P(D)$ thường cao hơn thực tế do mô hình không tính đến khả năng tái cấp vốn (Refinancing) của ngân hàng nội địa.

### **4\. Mô hình Zmijewski Score**

**Cơ sở khoa học:** Mô hình Probit dựa trên tỷ suất sinh lời, đòn bẩy và thanh khoản.

**Đặc thù ứng dụng tại Việt Nam & Ngành Bán lẻ:**

* **Tính ổn định cao:** Đây là mô hình "khắt khe" nhất. Với 3 biến đơn giản (ROA, Leverage, Liquidity), nó loại bỏ được hiện tượng đa cộng tuyến thường gặp ở các báo cáo tài chính có chất lượng kiểm toán trung bình tại Việt Nam.  
* **Hạn chế ngành:** Mô hình này bỏ qua biến doanh thu và hàng tồn kho \- hai "mạch máu" chính của bán lẻ. Do đó, Zmijewski chỉ nên đóng vai trò là **mỏ neo (baseline)** để xác nhận kết quả từ Altman, thay vì là công cụ dự báo độc lập cho ngành này.

### ---

**Bảng tổng hợp phương pháp luận hiệu chỉnh**

| Mô hình | Trọng tâm phân tích | Rủi ro sai lệch tại VN | Đề xuất hiệu chỉnh (Vibe Coding/Python) |
| :---- | :---- | :---- | :---- |
| **Altman Z''** | Sức mạnh bảng cân đối | Vốn lưu động âm do chiếm dụng vốn | Sử dụng dòng tiền từ HĐKD (CFO) để thay thế một phần biến $X\_1$ |
| **Beneish M** | Gian lận lợi nhuận | Tăng trưởng nóng gây tín hiệu giả | Kết hợp với chỉ số vòng quay hàng tồn kho (Inventory Turnover) |
| **Ohlson O** | Xác suất phá sản | Sai số quy mô tài sản | Hiệu chỉnh $SIZE$ theo sức mua tương đương hoặc giá trị vốn hóa |
| **Zmijewski** | Khả năng thanh toán | Quá đơn giản, bỏ qua biên lợi nhuận | Chỉ dùng làm ngưỡng chặn dưới (Floor threshold) |

### **Phương pháp luận đề xuất (Scientific Approach)**

Để tối ưu hóa việc đánh giá doanh nghiệp bán lẻ Việt Nam, nên áp dụng **Phương pháp xếp hạng hỗn hợp (Hybrid Scoring)**:

1. **Bước 1:** Chuẩn hóa dữ liệu theo chuẩn mực IFRS 16 (đưa các khoản thuê mặt bằng ngoại bảng vào bảng cân đối).  
2. **Bước 2:** Chạy song song 4 mô hình trên môi trường Python (sử dụng thư viện pandas và scikit-learn để xử lý outlier).  
3. **Bước 3:** Áp dụng trọng số tùy chỉnh (Weighting) dựa trên quy mô thị phần thay vì chỉ dựa trên số liệu tài chính tĩnh.

Việc sử dụng **Local AI** để tự động hóa việc thu thập dữ liệu từ CafeF và tính toán các chỉ số này sẽ giúp loại bỏ sai số nhập liệu thủ công và cho phép phân tích theo thời gian thực (Real-time Financial Forensic).

---

*Dữ liệu được phân tích dựa trên bối cảnh tài chính Việt Nam giai đoạn 2024-2026.*