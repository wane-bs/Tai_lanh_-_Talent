"""
Report Generator Module — Tự động sinh báo cáo Markdown cho từng doanh nghiệp.

Đầu ra: File .md chứa:
1. Tổng kết rủi ro (Risk Level + Composite Score)
2. Kết quả các mô hình cổ điển (Altman, Beneish, Ohlson, Zmijewski)
3. Kết quả ML Engine (PD%, SHAP top contributors)
4. Phân tích Dòng tiền (DSCR, Liquidity Runway)
5. Khuyến nghị
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime


class ReportGenerator:
    """Sinh báo cáo Markdown tự động."""

    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    def generate_company_report(self,
                                ticker: str,
                                classified_df: pd.DataFrame,
                                calc_results: dict,
                                shap_df: pd.DataFrame = None,
                                industry: str = 'DEFAULT') -> str:
        """
        Tạo báo cáo Markdown cho 1 doanh nghiệp.

        Args:
            ticker: mã chứng khoán
            classified_df: DataFrame đã phân loại (cho ticker này)
            calc_results: dict kết quả Calculator
            shap_df: (optional) SHAP values DataFrame

        Returns:
            str: Nội dung Markdown
        """
        company_data = classified_df[classified_df['Ticker'] == ticker] if 'Ticker' in classified_df.columns else classified_df

        if company_data.empty:
            return f"# {ticker} — Không có dữ liệu\n"

        latest = company_data.sort_values('Year').iloc[-1]

        md = []
        md.append(f"# 📊 Báo cáo Rủi ro Phá sản — {ticker}")
        md.append(f"\n> Ngày tạo: {self.timestamp}")
        md.append(f"> Năm đánh giá mới nhất: {int(latest.get('Year', 0))}")
        md.append("")

        # ===== SECTION 1: TỔNG KẾT =====
        md.append("## 1. Tổng kết Rủi ro")
        md.append("")

        risk_emoji = latest.get('Risk_Emoji', '❓')
        risk_name = latest.get('Risk_Name', 'Unknown')
        risk_vn = latest.get('Risk_VN', '')
        composite = latest.get('Composite_Score', 0)
        pd_xgb = latest.get('PD_XGBoost', None)

        md.append(f"| Chỉ tiêu | Giá trị |")
        md.append(f"|---|---|")
        md.append(f"| **Mức rủi ro** | {risk_emoji} **{risk_name}** ({risk_vn}) |")
        md.append(f"| **Composite Score** | {composite:.1f} / 100 |")
        if pd_xgb is not None and not pd.isna(pd_xgb):
            md.append(f"| **PD (XGBoost)** | {pd_xgb:.1f}% |")
        md.append("")

        # Alert box
        risk_level = int(latest.get('Risk_Level', 0))
        if risk_level >= 4:
            md.append("> [!CAUTION]")
            md.append(f"> Doanh nghiệp {ticker} đang ở mức **{risk_name}** — cần hành động khẩn cấp.")
        elif risk_level >= 3:
            md.append("> [!WARNING]")
            md.append(f"> Doanh nghiệp {ticker} đang chịu **áp lực tài chính** — cần giám sát chặt.")
        elif risk_level >= 2:
            md.append("> [!IMPORTANT]")
            md.append(f"> Doanh nghiệp {ticker} nằm trong vùng **cảnh báo** — theo dõi các chỉ số.")
        else:
            md.append("> [!NOTE]")
            md.append(f"> Doanh nghiệp {ticker} hoạt động **ổn định** theo các mô hình đánh giá.")
        md.append("")

        # ===== SECTION 2: MÔ HÌNH CỔ ĐIỂN =====
        md.append("## 2. Mô hình Cổ điển")
        md.append("")

        # Altman Z-Score
        if 'altman' in calc_results and not calc_results['altman'].empty:
            alt = calc_results['altman']
            if industry == 'REAL_ESTATE':
                md.append("### 2.1. Altman Z''-Score (Hiệu chỉnh BĐS)")
                md.append("$$ Z'' = 3.25 + 6.56 \cdot \\frac{CA - Inv - CL}{TA} + 3.26 \cdot \\frac{RE}{TA} + 6.72 \cdot \\frac{EBIT}{TA} + 1.05 \cdot \\frac{BVE}{TL} $$")
                md.append("> *Ghi chú: $X_1$ được hiệu chỉnh bằng cách loại bỏ Hàng tồn kho ($Inv$) để phản ánh thanh khoản thực tế của DN Bất động sản.*")
            else:
                md.append("### 2.1. Altman Z''-Score")
                md.append("$$ Z'' = 3.25 + 6.56 \cdot \\frac{WC}{TA} + 3.26 \cdot \\frac{RE}{TA} + 6.72 \cdot \\frac{EBIT}{TA} + 1.05 \cdot \\frac{BVE}{TL} $$")
            
            md.append("")
            md.append("| Năm | WC/TA | RE/TA | EBIT/TA | Equity/TL | Z-Score | Vùng |")
            md.append("|-----|-------|-------|---------|-----------|---------|------|")
            for _, r in alt.iterrows():
                md.append(f"| {int(r['Year'])} | {r['WC_TA']:.3f} | {r['RE_TA']:.3f} | "
                         f"{r['EBIT_TA']:.3f} | {r['Equity_TL']:.3f} | "
                         f"**{r['Z_Score']:.2f}** | {r['Zone']} |")
            md.append("")

        # Beneish M-Score
        if 'beneish' in calc_results and not calc_results['beneish'].empty:
            ben = calc_results['beneish']
            md.append("### 2.2. Beneish M-Score")
            md.append("$$ M = -4.84 + 0.92 \cdot DSRI + 0.528 \cdot GMI + 0.404 \cdot AQI + 0.892 \cdot SGI + 0.115 \cdot DEPI - 0.172 \cdot SGAI + 4.679 \cdot TATA - 0.327 \cdot LVGI $$")
            md.append("")
            md.append("| Năm | DSRI | GMI | AQI | SGI | TATA | M-Score | Đánh giá |")
            md.append("|-----|------|-----|-----|-----|------|---------|----------|")
            for _, r in ben.iterrows():
                md.append(f"| {int(r['Year'])} | {r['DSRI']:.3f} | {r['GMI']:.3f} | "
                         f"{r['AQI']:.3f} | {r['SGI']:.3f} | {r['TATA']:.3f} | "
                         f"**{r['M_Score']:.2f}** | {r['Manipulation']} |")
            md.append("")

        # Ohlson O-Score
        if 'ohlson' in calc_results and not calc_results['ohlson'].empty:
            ohl = calc_results['ohlson']
            md.append("### 2.3. Ohlson O-Score")
            md.append("$$ O = -1.32 - 0.407 \cdot \ln(TA/10^6) + 6.03 \cdot \\frac{TL}{TA} - 1.43 \cdot \\frac{WC}{TA} + 0.0757 \cdot \\frac{CL}{CA} - 1.72 \cdot OENEG - 2.37 \cdot \\frac{NI}{TA} - 1.83 \cdot \\frac{CFO}{TL} + 0.285 \cdot INTWO - 0.521 \cdot CHIN $$")
            md.append("")
            md.append("| Năm | O-Score | PD (Ohlson) | Mức |")
            md.append("|-----|---------|-------------|-----|")
            for _, r in ohl.iterrows():
                md.append(f"| {int(r['Year'])} | {r['O_Score']:.3f} | {r['PD_Ohlson']:.1f}% | {r['Risk']} |")
            md.append("")

        # Zmijewski
        if 'zmijewski' in calc_results and not calc_results['zmijewski'].empty:
            zm = calc_results['zmijewski']
            md.append("### 2.4. Zmijewski Score")
            md.append("$$ X = -4.336 - 4.513 \cdot \\frac{NI}{TA} + 5.679 \cdot \\frac{TL}{TA} - 0.004 \cdot \\frac{CA}{CL} $$")
            md.append("")
            md.append("| Năm | X-Score | PD (Zmijewski) | Mức |")
            md.append("|-----|---------|-----------------|-----|")
            for _, r in zm.iterrows():
                md.append(f"| {int(r['Year'])} | {r['Zmijewski_X']:.3f} | {r['PD_Zmijewski']:.1f}% | {r['Risk']} |")
            md.append("")

        # ===== SECTION 3: ML ENGINE =====
        md.append("## 3. ML Engine — Dự báo PD%")
        md.append("")

        if 'PD_XGBoost' in company_data.columns:
            md.append("| Năm | PD (XGBoost) | Composite | Risk |")
            md.append("|-----|--------------|-----------|------|")
            for _, r in company_data.iterrows():
                pd_val = r.get('PD_XGBoost', None)
                pd_str = f"{pd_val:.1f}%" if pd_val is not None and not pd.isna(pd_val) else "N/A"
                comp_str = f"{r.get('Composite_Score', 0):.1f}"
                risk_str = f"{r.get('Risk_Emoji', '')} {r.get('Risk_Name', '')}"
                md.append(f"| {int(r['Year'])} | {pd_str} | {comp_str} | {risk_str} |")
            md.append("")

        # SHAP contributions
        if shap_df is not None and not shap_df.empty:
            md.append("### 3.1. SHAP — Đóng góp chỉ số (năm mới nhất)")
            md.append("")
            if len(shap_df) > 0:
                last_shap = shap_df.iloc[-1]
                sorted_shap = last_shap.abs().sort_values(ascending=False)
                md.append("| Chỉ số | SHAP Value | Tác động |")
                md.append("|--------|-----------|----------|")
                for feat in sorted_shap.head(8).index:
                    val = last_shap[feat]
                    impact = "↑ Tăng rủi ro" if val > 0 else "↓ Giảm rủi ro"
                    md.append(f"| {feat} | {val:.4f} | {impact} |")
                md.append("")

        # ===== SECTION 4: DÒNG TIỀN =====
        md.append("## 4. Phân tích Dòng tiền & Thanh khoản")
        md.append("")

        # DSCR
        if 'dscr' in calc_results and not calc_results['dscr'].empty:
            ds = calc_results['dscr']
            md.append("### 4.1. DSCR (Stressed)")
            md.append("")
            md.append("| Năm | EBITDA | Debt Service | DSCR Normal | DSCR Stressed | Trạng thái |")
            md.append("|-----|--------|-------------|-------------|---------------|-----------|")
            for _, r in ds.iterrows():
                md.append(f"| {int(r['Year'])} | {r['EBITDA']:,.0f} | {r['Debt_Service']:,.0f} | "
                         f"{r['DSCR_Normal']:.2f} | {r['DSCR_Stressed']:.2f} | {r['Coverage']} |")
            md.append("")

        # Liquidity Runway
        if 'runway' in calc_results and not calc_results['runway'].empty:
            rw = calc_results['runway']
            md.append("### 4.2. Liquidity Runway")
            md.append("")
            md.append("| Năm | Tiền mặt | CFO/năm | Runway (tháng) | Trạng thái |")
            md.append("|-----|---------|---------|----------------|-----------|")
            for _, r in rw.iterrows():
                runway_str = f"{r['Runway_Months']:.0f}" if not np.isinf(r['Runway_Months']) else "∞"
                md.append(f"| {int(r['Year'])} | {r['Cash']:,.0f} | {r['CFO_Annual']:,.0f} | "
                         f"{runway_str} | {r['Status']} |")
            md.append("")

        # Sloan Accruals
        if 'sloan' in calc_results and not calc_results['sloan'].empty:
            sl = calc_results['sloan']
            md.append("### 4.3. Sloan Accruals (Chất lượng Lợi nhuận)")
            md.append("")
            md.append("| Năm | Accruals (%) | Đánh giá |")
            md.append("|-----|-------------|----------|")
            for _, r in sl.iterrows():
                md.append(f"| {int(r['Year'])} | {r['Sloan_Pct']:.1f}% | {r['Quality']} |")
            md.append("")

        # ===== SECTION 4.5: ĐẶC THÙ BĐS =====
        if 'bds_metrics' in calc_results and not calc_results['bds_metrics'].empty:
            bds = calc_results['bds_metrics']
            md.append("## 4.5. Phân tích Đặc thù Bất động sản")
            md.append("")
            md.append("> [!IMPORTANT]")
            md.append("> Các chỉ số dưới đây sử dụng phương pháp **Trailing Twelve Months (TTM)** — lũy kế 4 quý gần nhất để làm phẳng tính mùa vụ của ngành BĐS.")
            md.append("")

            md.append("### Khối u Tài sản (Inventory vs Receivables)")
            md.append("")
            md.append("| Kỳ | Tồn Kho/TS (%) | Phải Thu/DT | CFO/Nợ NH | Khả năng trả lãi | Runway Lãi (Q) |")
            md.append("|-----|----------------|------------|----------|-------------------|---------------|")
            for _, r in bds.iterrows():
                period = r.get('Period', f"Y{int(r['Year'])}")
                inv = r.get('inventory_to_assets', 0) * 100
                recv = r.get('receivables_to_revenue', 0)
                recv_str = f"{recv:.2f}" if not np.isinf(recv) else "∞"
                cfo_sd = r.get('cfo_to_short_debt', 0)
                cfo_str = f"{cfo_sd:.2f}" if not np.isinf(cfo_sd) else "∞"
                int_cov = r.get('interest_coverage_cfo', 0)
                int_str = f"{int_cov:.2f}" if not np.isinf(int_cov) else "∞"
                runway = r.get('runway_interest', 0)
                run_str = f"{runway:.1f}" if not np.isinf(runway) else "∞"
                md.append(f"| {period} | {inv:.1f}% | {recv_str} | {cfo_str} | {int_str} | {run_str} |")
            md.append("")

            # Cảnh báo ngắt mạch
            latest_bds = bds.iloc[-1]
            if latest_bds.get('interest_coverage_cfo', np.inf) < 1 and latest_bds.get('CFO_TTM', 0) < 0:
                md.append("> [!CAUTION]")
                md.append("> **NGẮT MẠCH BĐS**: Dòng tiền hoạt động âm VÀ không đủ trả lãi vay — nguy cơ vỡ nợ cao.")
                md.append("")
            if latest_bds.get('inventory_to_assets', 0) > 0.5:
                md.append("> [!WARNING]")
                md.append(f"> Tồn kho chiếm **{latest_bds['inventory_to_assets']*100:.0f}%** tổng tài sản — rủi ro thanh khoản tài sản bất động sản nặng nề.")
                md.append("")

        # ===== BẢNG PHÂN TÍCH 5 NĂM GẦN NHẤT =====
        md.append("## 4.6. Bảng Phân Tích 5 Năm Gần Nhất (Chỉ số sinh tử)")
        md.append("")
        md.append("| Năm | Z''-Score (Hiệu chỉnh BĐS) | Thanh khoản ròng (WC_adj/TA) | Đòn bẩy (Equity/Total Debt) | Dòng tiền CFO TTM (Tỷ VND) | Khả năng trả lãi (ICR - TTM) | Tỷ lệ Tồn kho / TTS | Trạng thái rủi ro |")
        md.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|")
        
        last_5_years = sorted(company_data['Year'].unique())[-5:]
        for y in last_5_years:
            y_data = company_data[company_data['Year'] == y]
            if y_data.empty: continue
            r_comp = y_data.iloc[0]
            
            z_score = r_comp.get('Z_Score', 0)
            wc_ta = r_comp.get('wc_ta', 0)
            status = f"{r_comp.get('Risk_Emoji', '')} {r_comp.get('Risk_VN', '')}"

            y_bds = pd.DataFrame()
            if 'bds_metrics' in calc_results and not calc_results['bds_metrics'].empty:
                bds = calc_results['bds_metrics']
                y_bds = bds[bds['Year'] == y]

            if not y_bds.empty:
                latest_q = y_bds.iloc[-1]
                cfo_ttm = latest_q.get('CFO_TTM', 0) / 1e9
                icr = latest_q.get('interest_coverage_cfo', 0)
                inv_tts = latest_q.get('inventory_to_assets', 0) * 100
                leverage = latest_q.get('leverage_equity_debt', 0)
                
                lev_str = f"{leverage:.2f}" if not np.isinf(leverage) and not pd.isna(leverage) else "∞"
                icr_str = f"{icr:.2f}" if not np.isinf(icr) and not pd.isna(icr) else "∞"
            else:
                cfo_ttm = 0
                icr_str = "N/A"
                inv_tts = 0
                lev_str = "N/A"

            md.append(f"| **{int(y)}** | {z_score:.2f} | {wc_ta:.3f} | {lev_str} | {cfo_ttm:,.1f} | {icr_str} | {inv_tts:.1f}% | {status} |")
        md.append("")

        # ===== SECTION 5: KHUYẾN NGHỊ =====
        md.append("## 5. Khuyến nghị")
        md.append("")

        if risk_level >= 4:
            md.append("1. **Tái cấu trúc nợ khẩn cấp** — Đàm phán giãn nợ/chuyển đổi nợ thành vốn")
            md.append("2. **Thoái vốn tài sản không cốt lõi** — Tạo thanh khoản ngắn hạn")
            md.append("3. **Giám sát hàng tuần** — Theo dõi dòng tiền và DSCR")
            if self._is_real_estate(calc_results):
                md.append("4. **Thanh lý tồn kho BĐS** — Chiết khấu sản phẩm để giải phóng dòng tiền")
                md.append("5. **Dừng triển khai dự án mới** — Tập trung hoàn thiện dự án hiện hữu để bàn giao")
        elif risk_level >= 3:
            md.append("1. **Kiểm soát chi phí** — Rà soát và cắt giảm chi phí không cần thiết")
            md.append("2. **Đa dạng hóa nguồn thu** — Giảm phụ thuộc vào 1 nguồn doanh thu")
            md.append("3. **Giám sát hàng tháng** — Theo dõi Z-Score và Composite Score")
            if self._is_real_estate(calc_results):
                md.append("4. **Đàm phán gia hạn nợ** — Kéo dài thời hạn trả nợ gốc với ngân hàng")
        elif risk_level >= 2:
            md.append("1. **Duy trì thanh khoản** — Đảm bảo Current Ratio > 1.5")
            md.append("2. **Quản trị rủi ro lãi suất** — Hedge nợ vay biến động")
            md.append("3. **Đánh giá hàng quý** — Cập nhật mô hình rủi ro định kỳ")
        else:
            md.append("1. **Duy trì trạng thái tốt** — Tiếp tục chiến lược kinh doanh hiện tại")
            md.append("2. **Tối ưu hóa cấu trúc vốn** — Tận dụng chi phí vốn thấp")
            md.append("3. **Đánh giá bán kỳ** — Cập nhật mô hình 6 tháng/lần")

        md.append("")
        md.append("---")
        md.append(f"*Báo cáo tự động — Hệ thống Kiểm soát Rủi ro Phá sản v2.0 (BDS Enhanced)*")

        return "\n".join(md)

    def _is_real_estate(self, calc_results: dict) -> bool:
        """Kiểm tra xem có dữ liệu BĐS không."""
        return 'bds_metrics' in calc_results and not calc_results.get('bds_metrics', pd.DataFrame()).empty

    def generate_comparison_report(self,
                                   classified_df: pd.DataFrame) -> str:
        """
        Tạo báo cáo so sánh đối chiếu giữa nhiều doanh nghiệp.
        """
        if classified_df.empty:
            return "# So sánh — Không có dữ liệu\n"

        md = []
        md.append("# 📈 Báo cáo So sánh Đối chiếu Rủi ro")
        md.append(f"\n> Ngày tạo: {self.timestamp}")
        md.append("")

        # Summary table
        tickers = classified_df['Ticker'].unique()
        md.append("## 1. Bảng Tổng hợp")
        md.append("")
        md.append("| Doanh nghiệp | Năm | PD (XGBoost) | Composite | Risk |")
        md.append("|---|---|---|---|---|")

        for ticker in sorted(tickers):
            t_data = classified_df[classified_df['Ticker'] == ticker].sort_values('Year')
            latest = t_data.iloc[-1]
            pd_val = latest.get('PD_XGBoost', None)
            pd_str = f"{pd_val:.1f}%" if pd_val is not None and not pd.isna(pd_val) else "N/A"
            md.append(f"| **{ticker}** | {int(latest['Year'])} | {pd_str} | "
                     f"{latest.get('Composite_Score', 0):.1f} | "
                     f"{latest.get('Risk_Emoji', '')} {latest.get('Risk_Name', '')} |")

        md.append("")

        # Ranking
        md.append("## 2. Xếp hạng Rủi ro (Cao → Thấp)")
        md.append("")
        ranked = classified_df.sort_values('Year').groupby('Ticker').last()
        ranked = ranked.sort_values('Composite_Score', ascending=False)

        for i, (ticker, row) in enumerate(ranked.iterrows(), 1):
            emoji = row.get('Risk_Emoji', '')
            name = row.get('Risk_VN', '')
            comp = row.get('Composite_Score', 0)
            md.append(f"{i}. {emoji} **{ticker}** — {name} (Composite: {comp:.1f})")

        md.append("")
        md.append("---")
        md.append(f"*Báo cáo tự động — Hệ thống Kiểm soát Rủi ro Phá sản v1.0*")

        return "\n".join(md)

    def save_reports(self, classified_df: pd.DataFrame,
                     calc_results_all: dict,
                     out_dir: str,
                     shap_df: pd.DataFrame = None):
        """
        Lưu báo cáo cho tất cả DN.

        Args:
            classified_df: DataFrame đã phân loại
            calc_results_all: {ticker: calc_results}
            out_dir: thư mục đầu ra
            shap_df: (optional) SHAP values
        """
        os.makedirs(out_dir, exist_ok=True)

        tickers = classified_df['Ticker'].unique()

        for ticker in tickers:
            calc_res = calc_results_all.get(ticker, {})
            report = self.generate_company_report(
                ticker, classified_df, calc_res, shap_df
            )
            path = os.path.join(out_dir, f"{ticker}_report.md")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"  ✓ [{ticker}] Report saved to {path}")

        # Comparison report
        if len(tickers) > 1:
            comp_report = self.generate_comparison_report(classified_df)
            comp_path = os.path.join(out_dir, "comparison_report.md")
            with open(comp_path, 'w', encoding='utf-8') as f:
                f.write(comp_report)
            print(f"  ✓ Comparison report saved to {comp_path}")

    def generate_credit_report(self,
                               ticker: str,
                               latest_year_data,
                               credit_res: dict,
                               schedule_annuity: list,
                               schedule_eq_principal: list,
                               recommendation: dict,
                               rate: float,
                               tenor: int,
                               industry: str = 'DEFAULT',
                               score: int = None,
                               score_details: dict = None) -> str:
        """
        Tạo báo cáo Thẩm định Hạn mức Tín dụng & Kế hoạch Trả nợ cho 1 doanh nghiệp.
        """
        md = []
        md.append(f"# 🏦 Báo cáo Thẩm định Hạn mức & Phương án Trả nợ — {ticker}")
        md.append(f"\n> Ngày lập báo cáo: {self.timestamp}")
        md.append(f"> Năm tài chính đánh giá gần nhất: {int(latest_year_data.get('Year', 0))}")
        md.append("")

        # ===== PHẦN 1: TỔNG KẾT HẠN MỨC =====
        md.append("## 1. Kết quả Phê duyệt Hạn mức Tín dụng")
        md.append("")

        status = credit_res.get('Status', 'Chưa xác định')
        l_final = credit_res.get('L_final', 0.0)
        target_dscr = credit_res.get('Target_DSCR', 1.2)
        pmt_max = credit_res.get('PMT_max', 0.0)
        cfads = credit_res.get('CFADS', 0.0)

        # Trạng thái màu sắc/emoji
        status_emoji = "✅" if status == "Khả thi" else ("⚠️" if "Cắt giảm" in status else "❌")
        
        md.append(f"| Chỉ tiêu tín dụng | Giá trị đề xuất | Chi tiết trạng thái |")
        md.append(f"|---|---|---|")
        md.append(f"| **Hạn mức cấp tín dụng tối đa ($L_{{final}}$)** | **{l_final/1e9:,.2f} Tỷ VND** | {status_emoji} *{status}* |")
        md.append(f"| **Khả năng trả gốc/lãi tối đa mỗi năm ($PMT_{{max}}$)** | {pmt_max/1e9:,.2f} Tỷ VND | Dựa trên dòng tiền hoạt động |")
        md.append(f"| **Dòng tiền khả dụng trả nợ (CFADS)** | {cfads/1e9:,.2f} Tỷ VND | CFO lũy kế 4 quý gần nhất |")
        md.append(f"| **Hệ số DSCR mục tiêu ($DSCR_{{target}}$)** | {target_dscr:.2f}x | Đã bao gồm phạt rủi ro tài chính & AI |")
        md.append(f"| **Thông số khoản vay giả định** | Lãi suất: {rate*100:.1f}%/năm, Kỳ hạn: {tenor} năm | Dùng để lập lịch trả nợ |")
        md.append("")

        # Alert box warnings
        if status == "Từ chối":
            md.append("> [!CAUTION]")
            md.append(f"> **TỪ CHỐI CẤP TÍN DỤNG**: Doanh nghiệp {ticker} vi phạm các điều kiện ngắt mạch an toàn hoặc dòng tiền âm.")
            for w in credit_res.get('Warnings', []):
                md.append(f"> - *{w}*")
        elif "Cắt giảm" in status:
            md.append("> [!WARNING]")
            md.append(f"> **CẤP TÍN DỤNG CÓ ĐIỀU KIỆN (CẮT GIẢM)**: Hạn mức vay của doanh nghiệp {ticker} bị cắt giảm so với mức cơ sở.")
            for w in credit_res.get('Warnings', []):
                md.append(f"> - *{w}*")
        else:
            md.append("> [!NOTE]")
            md.append(f"> **PHÊ DUYỆT KHẢ THI**: Doanh nghiệp {ticker} đáp ứng tốt các chốt chặn an toàn về dòng tiền và đòn bẩy.")
        md.append("")

        # ===== PHẦN 2: CƠ SỞ LÝ LUẬN & TOÁN HỌC =====
        md.append("## 2. Cơ sở Lý luận & Khung Toán học Xác định Hạn mức")
        md.append("")
        md.append("Mô hình định mức tín dụng áp dụng triết lý **Thẩm định dựa trên Dòng tiền thực tế (Cash Flow-based Underwriting)** kết hợp **Trí tuệ nhân tạo (AI-driven Risk Adjustment)** theo các bước tuần tự:")
        md.append("")
        
        md.append("### Step 1: Tính toán Dòng tiền Khả dụng Trả nợ (CFADS)")
        md.append("Dòng tiền cốt lõi được lấy từ CFO TTM gần nhất:")
        md.append(r"$$ CFADS = \max(CFO_{TTM}, 0.0) $$")
        md.append("")

        md.append("### Step 2: Tính toán DSCR Mục tiêu Thích ứng (Target DSCR)")
        md.append("Hệ số an toàn dòng tiền được điều chỉnh tăng thêm (phạt rủi ro) dựa trên chất lượng tài sản ngắn hạn, đòn bẩy và xác suất vỡ nợ AI:")
        md.append(r"$$ DSCR_{target} = DSCR_{base} (1.20) + \Delta DSCR_{Inventory} + \Delta DSCR_{Capital} + \Delta DSCR_{WorkingCapital} + \Delta DSCR_{AI} $$")
        md.append("")
        
        # Bảng chi tiết tính toán DSCR cho doanh nghiệp
        md.append("**Chi tiết điều chỉnh phạt DSCR của doanh nghiệp:**")
        md.append("| Khoản điều chỉnh DSCR | Điều kiện áp dụng | Mức phạt | Trạng thái hiện tại |")
        md.append("|---|---|:---:|---|")
        
        # Trạng thái thực tế
        latest_inv = latest_year_data.get('inventory_to_assets', 0.0)
        latest_eq_debt = latest_year_data.get('leverage_equity_debt', np.nan)
        latest_wc_ta = latest_year_data.get('wc_ta', 0.0)
        pd_xgb = latest_year_data.get('PD_XGBoost', 0.0)

        inv_status = "Áp dụng" if latest_inv > 0.40 else "Không áp dụng"
        cap_status = "Áp dụng" if (not np.isnan(latest_eq_debt) and latest_eq_debt < 0.3) or latest_eq_debt == 0.0 else "Không áp dụng"
        wc_status = "Áp dụng" if latest_wc_ta < 0 else "Không áp dụng"
        
        md.append(fr"| $\Delta DSCR_{{Inventory}}$ (Tồn kho cao) | Tồn kho / TTS > 40% | +0.30 | {inv_status} (Tồn kho: {latest_inv*100:.1f}%) |")
        md.append(fr"| $\Delta DSCR_{{Capital}}$ (Đòn bẩy cao) | Equity / Total Debt < 0.30 | +0.30 | {cap_status} (Đòn bẩy: {latest_eq_debt:.2f}x) |")
        md.append(fr"| $\Delta DSCR_{{WorkingCapital}}$ (Vốn lưu động âm) | WC / TA < 0 | +0.20 | {wc_status} (WC/TA: {latest_wc_ta:.3f}) |")
        md.append(fr"| $\Delta DSCR_{{AI}}$ (Rủi ro AI) | Tuyến tính theo $PD_{{XGBoost}}$ | +{pd_xgb/100:.2f} | Áp dụng ($PD_{{XGB}}$: {pd_xgb:.1f}%) |")
        md.append("")

        md.append("### Step 3: Hiện giá hóa Hạn mức cơ sở (PV of Annuity)")
        md.append("Quy đổi khả năng trả nợ hàng năm thành quy mô khoản vay ban đầu:")
        md.append(r"$$ L_{base} = PMT_{max} \times \left[ \frac{1 - (1 + r)^{-n}}{r} \right] $$")
        md.append("")

        md.append("### Step 4: Chốt chặn Đòn bẩy Bảng Cân đối (Balance Sheet Leverage Cap)")
        md.append("Để bảo vệ cấu trúc tài sản sau giải ngân, doanh nghiệp phải duy trì tỷ lệ đệm vốn tự có tối thiểu 15% tổng dư nợ mới:")
        md.append("$$ L_{final} \\le \\max\\left(0.0, \\frac{Equity}{0.15} - Total\\ Debt\\right) $$")
        md.append("")

        # ===== PHẦN 3: ĐIỂM TÍN DỤNG DÒNG TIỀN (CASH FLOW SCORECARD) =====
        if score is not None and score_details is not None:
            md.append("## 3. Điểm Tín dụng Dòng tiền (Cash Flow Scorecard - BCTC)")
            md.append("")
            
            from cash_flow_scorer import BCTCCashFlowScorer
            scorer = BCTCCashFlowScorer()
            grade, decision, _ = scorer.get_decision(score)
            
            md.append(f"**Điểm tín dụng dòng tiền tổng hợp:** **{score} / 1000 điểm** (Xếp hạng rủi ro dòng tiền: **{grade}**)")
            md.append(f"> **Khuyến nghị phê duyệt tín dụng của AI:** *{decision}*")
            md.append("")
            
            md.append("### Bảng chi tiết chấm điểm các chỉ tiêu dòng tiền:")
            md.append("| Chỉ tiêu chấm điểm | Trọng số | Giá trị thực tế | Điểm thành phần | Phân hạng đánh giá |")
            md.append("|---|:---:|:---:|:---:|---|")
            
            names = {
                'cash_to_revenue': ('Chất lượng doanh thu (Cash-to-Revenue)', '20%'),
                'dscr': ('Khả năng trả nợ (DSCR CFO-based)', '25%'),
                'cash_buffer_days': ('Đệm thanh khoản (Cash Buffer Days)', '15%'),
                'revenue_volatility': ('Độ biến động doanh thu (Volatility CV)', '15%'),
                'equity_to_debt': ('Cấu trúc đòn bẩy (Equity/Debt)', '15%'),
                'cfo_growth_yoy': ('Xu hướng dòng tiền (CFO Growth YoY)', '10%')
            }
            
            for key, (vn_name, weight) in names.items():
                detail = score_details.get(key, {})
                val = detail.get('value', np.nan)
                pts = detail.get('points', 0)
                lbl = detail.get('label', 'N/A')
                
                if pd.isna(val):
                    val_str = "N/A"
                elif key in ['cash_to_revenue', 'revenue_volatility', 'cfo_growth_yoy']:
                    val_str = f"{val*100:.2f}%"
                elif key in ['dscr', 'equity_to_debt']:
                    val_str = f"{val:.2f}x"
                else:  # cash_buffer_days
                    val_str = f"{val:.1f} ngày"
                    
                md.append(f"| {vn_name} | {weight} | {val_str} | {pts:+.0f} | {lbl} |")
            md.append("")

        # ===== PHẦN 4: PHÂN TÍCH BỐI CẢNH & KHUYẾN NGHỊ PHƯƠNG ÁN TRẢ NỢ =====
        md.append("## 4. Phân tích Bối cảnh Doanh nghiệp & Đề xuất Trả nợ")
        md.append("")
        
        method_vn = recommendation.get('Method_VN', '')
        md.append(f"> **AI Khuyến nghị Phương án:** **{method_vn}**")
        md.append("")
        
        md.append("**Lập luận chi tiết từ bối cảnh doanh nghiệp:**")
        for reason in recommendation.get('Reasons', []):
            md.append(f"- {reason}")
        md.append("")

        # ===== PHẦN 5: SO SÁNH HAI PHƯƠNG ÁN TRẢ NỢ =====
        md.append("## 5. So sánh Tổng quan các Phương án Trả nợ")
        md.append("")
        
        if l_final > 0:
            total_interest_annuity = sum([x['Interest_Paid'] for x in schedule_annuity])
            total_payment_annuity = sum([x['Payment'] for x in schedule_annuity])
            max_pmt_annuity = schedule_annuity[0]['Payment']

            total_interest_eq = sum([x['Interest_Paid'] for x in schedule_eq_principal])
            total_payment_eq = sum([x['Payment'] for x in schedule_eq_principal])
            max_pmt_eq = schedule_eq_principal[0]['Payment']

            md.append(f"Dưới đây là bảng so sánh tổng hợp cho khoản vay **{l_final/1e9:,.2f} Tỷ VND**:")
            md.append("")
            md.append("| Chỉ tiêu so sánh | Phương án Niên kim đều | Phương án Gốc đều, lãi giảm dần | Chênh lệch (Gốc đều vs Niên kim) |")
            md.append("|---|:---:|:---:|:---:|")
            md.append(f"| **Tổng số tiền phải trả (Gốc + Lãi)** | {total_payment_annuity/1e9:,.2f} Tỷ | {total_payment_eq/1e9:,.2f} Tỷ | **{(total_payment_eq - total_payment_annuity)/1e9:+,.2f} Tỷ** |")
            md.append(f"| **Tổng chi phí lãi vay phải trả** | {total_interest_annuity/1e9:,.2f} Tỷ | {total_interest_eq/1e9:,.2f} Tỷ | **{(total_interest_eq - total_interest_annuity)/1e9:+,.2f} Tỷ** (Giảm chi phí) |")
            md.append(f"| **Áp lực dòng tiền năm đầu (PMT Max)** | {max_pmt_annuity/1e9:,.2f} Tỷ | {max_pmt_eq/1e9:,.2f} Tỷ | **{(max_pmt_eq - max_pmt_annuity)/1e9:+,.2f} Tỷ** (Năm đầu nặng hơn) |")
            md.append(f"| **Áp lực dòng tiền năm cuối (PMT Min)** | {schedule_annuity[-1]['Payment']/1e9:,.2f} Tỷ | {schedule_eq_principal[-1]['Payment']/1e9:,.2f} Tỷ | **{(schedule_eq_principal[-1]['Payment'] - schedule_annuity[-1]['Payment'])/1e9:,.2f} Tỷ** (Năm cuối nhẹ hơn) |")
            md.append("")
        else:
            md.append("> *Lưu ý: Hạn mức tín dụng tối đa là 0.0 Tỷ VND (Bị Từ Chối), do đó không có thông số so sánh lịch trả nợ.*")
            md.append("")

        # ===== PHẦN 6: CHI TIẾT LỊCH TRẢ NỢ =====
        md.append("## 6. Chi tiết Lịch trình Trả nợ")
        md.append("")

        if l_final > 0:
            md.append("### 6.1. Phương án Niên kim đều (Khuyên dùng cho DN chịu áp lực dòng tiền ngắn hạn)")
            md.append("")
            md.append("| Năm | Dư nợ đầu kỳ | Tổng số tiền trả | Trả gốc | Trả lãi | Dư nợ cuối kỳ |")
            md.append("|---|---|---|---|---|---|")
            for row in schedule_annuity:
                md.append(f"| {row['Year']} | {row['Beginning_Balance']/1e9:,.2f} Tỷ | {row['Payment']/1e9:,.2f} Tỷ | "
                          f"{row['Principal_Paid']/1e9:,.2f} Tỷ | {row['Interest_Paid']/1e9:,.2f} Tỷ | {row['Ending_Balance']/1e9:,.2f} Tỷ |")
            md.append("")

            md.append("### 6.2. Phương án Gốc đều, lãi giảm dần (Khuyên dùng để tiết kiệm chi phí lãi vay)")
            md.append("")
            md.append("| Năm | Dư nợ đầu kỳ | Tổng số tiền trả | Trả gốc | Trả lãi | Dư nợ cuối kỳ |")
            md.append("|---|---|---|---|---|---|")
            for row in schedule_eq_principal:
                md.append(f"| {row['Year']} | {row['Beginning_Balance']/1e9:,.2f} Tỷ | {row['Payment']/1e9:,.2f} Tỷ | "
                          f"{row['Principal_Paid']/1e9:,.2f} Tỷ | {row['Interest_Paid']/1e9:,.2f} Tỷ | {row['Ending_Balance']/1e9:,.2f} Tỷ |")
            md.append("")
        else:
            md.append("> *Doanh nghiệp không đủ điều kiện cấp tín dụng, không thể lập lịch trình trả nợ.*")
            md.append("")

        md.append("---")
        md.append(f"*Báo cáo tự động — Hệ thống Kiểm soát & Định mức Tín dụng v2.0*")

        return "\n".join(md)

