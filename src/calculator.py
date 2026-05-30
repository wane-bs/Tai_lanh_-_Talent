"""
Calculator Module — Tính toán các chỉ số đánh giá phá sản cổ điển.

Input: Dữ liệu BCTC hàng năm (từ ETL) cho 1 doanh nghiệp.
Output: DataFrame chứa các scores (Altman, Beneish, Ohlson, Zmijewski, Sloan, DSCR, Liquidity Runway).
"""

import pandas as pd
import numpy as np


class BankruptcyCalculator:
    """Tính toán các mô hình đánh giá phá sản cổ điển."""

    def __init__(self, annual_data: dict[str, pd.DataFrame], ticker: str = "", industry: str = "DEFAULT"):
        """
        annual_data: dict với keys BALANCE_SHEET, INCOME_STATEMENT, CASH_FLOW
        Mỗi DataFrame có cột Year + các chỉ tiêu tài chính.
        """
        self.bs = annual_data.get('BALANCE_SHEET', pd.DataFrame())
        self.is_df = annual_data.get('INCOME_STATEMENT', pd.DataFrame())
        self.cf = annual_data.get('CASH_FLOW', pd.DataFrame())
        self.ticker = ticker
        self.industry = industry
        self.results = {}

    def _safe_get(self, df: pd.DataFrame, col: str, default=0.0) -> pd.Series:
        """Lấy giá trị cột một cách an toàn."""
        if col in df.columns:
            return pd.to_numeric(df[col], errors='coerce').fillna(default)
        # Tìm tên cột gần đúng
        for c in df.columns:
            if col.lower() in c.lower():
                return pd.to_numeric(df[c], errors='coerce').fillna(default)
        return pd.Series([default] * len(df), index=df.index)

    def _col(self, df, *patterns, exclude: list[str] = None) -> pd.Series:
        """Tìm cột khớp với patterns (ưu tiên pattern đầu tiên)."""
        for pat in patterns:
            for c in df.columns:
                c_lower = c.lower()
                if exclude and any(x.lower() in c_lower for x in exclude):
                    continue
                if pat.lower() in c_lower:
                    return pd.to_numeric(df[c], errors='coerce').fillna(0.0)
        return pd.Series([0.0] * len(df), index=df.index)

    # =====================================================================
    # ALTMAN Z''-SCORE (Emerging Markets, non-manufacturing)
    # Z'' = 3.25 + 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4
    # =====================================================================
    def altman_z_score(self) -> pd.DataFrame:
        """Tính Altman Z''-Score cho từng năm."""
        bs, is_df = self.bs, self.is_df
        if bs.empty or is_df.empty:
            return pd.DataFrame()

        years = bs['Year'].values

        # Components
        ta = self._col(bs, 'TỔNG TÀI SẢN')
        ca = self._col(bs, 'TÀI SẢN NGẮN HẠN')
        cl = self._col(bs, 'Nợ ngắn hạn')
        tl = self._col(bs, 'NỢ PHẢI TRẢ')
        vcsh = self._col(bs, 'VỐN CHỦ SỞ HỮU')
        ebit = self._col(is_df, 'EBIT')
        re = self._col(bs, 'Lãi chưa phân phối', 'LNST chưa phân phối')
        inventory = self._col(bs, 'Hàng tồn kho')

        wc = ca - cl
        if self.industry == 'REAL_ESTATE':
            # BĐS: Loại bỏ hàng tồn kho khỏi TSNH trước khi tính vốn lưu động
            # WC_ròng = (CA - Inventory) - CL
            # Lý do: Hàng tồn kho BĐS (dự án dở dang, đất nền) cực kỳ kém
            # thanh khoản, không phản ánh khả năng thanh toán dòng tiền thực tế.
            # Việc loại bỏ HTK tập trung X₁ vào tài sản ngắn hạn có tính lỏng cao
            # (tiền mặt, đầu tư ngắn hạn, phải thu ngắn hạn).
            wc = (ca - inventory) - cl
            print(f"  [{self.ticker}] Altman X₁: WC ròng (loại bỏ HTK) = CA({ca.iloc[-1]:,.0f}) - HTK({inventory.iloc[-1]:,.0f}) - CL({cl.iloc[-1]:,.0f})")
        elif self.industry == 'RETAIL':
            phai_tra_nguoi_ban = self._col(bs, 'Phải trả người bán ngắn hạn').replace(0, np.nan).fillna(0)
            wc = wc + phai_tra_nguoi_ban

        ta_safe = ta.replace(0, np.nan)
        tl_safe = tl.replace(0, np.nan)

        x1 = wc / ta_safe  # WC / TA
        x2 = re / ta_safe   # RE / TA (proxy: lãi chưa phân phối)
        x3 = ebit / ta_safe  # EBIT / TA
        x4 = vcsh / tl_safe  # BV Equity / Total Liabilities

        z_score = 3.25 + 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4

        result = pd.DataFrame({
            'Year': years,
            'WC_TA': x1.values,
            'RE_TA': x2.values,
            'EBIT_TA': x3.values,
            'Equity_TL': x4.values,
            'Z_Score': z_score.values,
            'Zone': pd.cut(z_score, bins=[-np.inf, 1.1, 2.6, np.inf],
                          labels=['Nguy hiểm', 'Cảnh báo', 'An toàn'])
        })

        self.results['altman'] = result
        return result

    # =====================================================================
    # BENEISH M-SCORE
    # M = -4.84 + 0.92*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI
    #     + 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI
    # =====================================================================
    def beneish_m_score(self) -> pd.DataFrame:
        """Tính Beneish M-Score (cần t và t-1).
        Lưu ý: Vô hiệu hóa cho ngành BĐS vì doanh thu bàn giao dự án
        đột biến gây false positive trên chỉ số SGI.
        """
        # BĐS: Skip Beneish, sử dụng Sloan Accruals thay thế
        if self.industry == 'REAL_ESTATE':
            print(f"  [{self.ticker}] Beneish M-Score: SKIPPED (BĐS — dùng Sloan thay thế)")
            self.results['beneish'] = pd.DataFrame()
            return pd.DataFrame()

        bs, is_df, cf = self.bs, self.is_df, self.cf
        if bs.empty or is_df.empty:
            return pd.DataFrame()

        rows = []
        for i in range(1, len(bs)):
            try:
                year = bs['Year'].iloc[i]

                # Current & Previous year values
                rev_c = float(self._col(is_df, 'Doanh số thuần').iloc[i])
                rev_p = float(self._col(is_df, 'Doanh số thuần').iloc[i-1])
                recv_c = float(self._col(bs, 'Các khoản phải thu').iloc[i])
                recv_p = float(self._col(bs, 'Các khoản phải thu').iloc[i-1])
                cogs_c = abs(float(self._col(is_df, 'Giá vốn hàng bán').iloc[i]))
                cogs_p = abs(float(self._col(is_df, 'Giá vốn hàng bán').iloc[i-1]))
                ta_c = float(self._col(bs, 'TỔNG TÀI SẢN').iloc[i])
                ta_p = float(self._col(bs, 'TỔNG TÀI SẢN').iloc[i-1])
                ca_c = float(self._col(bs, 'TÀI SẢN NGẮN HẠN').iloc[i])
                ca_p = float(self._col(bs, 'TÀI SẢN NGẮN HẠN').iloc[i-1])
                ppe_c = float(self._col(bs, 'Tài sản cố định').iloc[i])
                ppe_p = float(self._col(bs, 'Tài sản cố định').iloc[i-1])
                depr_c = abs(float(self._col(cf, 'Khấu hao TSCĐ').iloc[i])) if not cf.empty else 0
                depr_p = abs(float(self._col(cf, 'Khấu hao TSCĐ').iloc[i-1])) if not cf.empty else 0
                sga_c = abs(float(self._col(is_df, 'Chi phí bán hàng').iloc[i])) + \
                         abs(float(self._col(is_df, 'Chi phí quản lý').iloc[i]))
                sga_p = abs(float(self._col(is_df, 'Chi phí bán hàng').iloc[i-1])) + \
                         abs(float(self._col(is_df, 'Chi phí quản lý').iloc[i-1]))
                ni_c = float(self._col(is_df, 'Lãi/(lỗ) thuần sau thuế').iloc[i])
                ocf_c = float(self._col(cf, 'Lưu chuyển tiền thuần từ các hoạt động sản xuất').iloc[i]) if not cf.empty else 0
                cl_c = float(self._col(bs, 'Nợ ngắn hạn').iloc[i])
                cl_p = float(self._col(bs, 'Nợ ngắn hạn').iloc[i-1])
                ltl_c = float(self._col(bs, 'Nợ dài hạn').iloc[i])
                ltl_p = float(self._col(bs, 'Nợ dài hạn').iloc[i-1])

                # Calculate components
                dsri = ((recv_c / rev_c) / (recv_p / rev_p)) if rev_c and rev_p and recv_p else 1.0
                gm_p = (rev_p - cogs_p) / rev_p if rev_p else 0
                gm_c = (rev_c - cogs_c) / rev_c if rev_c else 0
                gmi = gm_p / gm_c if gm_c else 1.0
                aq_c = 1 - (ca_c + ppe_c) / ta_c if ta_c else 0
                aq_p = 1 - (ca_p + ppe_p) / ta_p if ta_p else 0
                aqi = aq_c / aq_p if aq_p else 1.0
                sgi = rev_c / rev_p if rev_p else 1.0
                
                if self.industry == 'RETAIL' and sgi > 1.0:
                    inv_c = abs(float(self._col(bs, 'Hàng tồn kho').iloc[i]))
                    inv_p = abs(float(self._col(bs, 'Hàng tồn kho').iloc[i-1]))
                    avg_inv_c = (inv_c + inv_p) / 2 if (inv_c + inv_p) > 0 else 1.0
                    inv_turnover_c = cogs_c / avg_inv_c
                    if inv_turnover_c > 1.0:
                        sgi = 1.0

                dep_p = depr_p / (ppe_p + depr_p) if (ppe_p + depr_p) else 0
                dep_c = depr_c / (ppe_c + depr_c) if (ppe_c + depr_c) else 0
                depi = dep_p / dep_c if dep_c else 1.0
                sga_r_c = sga_c / rev_c if rev_c else 0
                sga_r_p = sga_p / rev_p if rev_p else 0
                sgai = sga_r_c / sga_r_p if sga_r_p else 1.0
                tata = (ni_c - ocf_c) / ta_c if ta_c else 0
                lev_c = (cl_c + ltl_c) / ta_c if ta_c else 0
                lev_p = (cl_p + ltl_p) / ta_p if ta_p else 0
                lvgi = lev_c / lev_p if lev_p else 1.0

                m_score = (-4.84 + 0.92*dsri + 0.528*gmi + 0.404*aqi + 0.892*sgi
                          + 0.115*depi - 0.172*sgai + 4.679*tata - 0.327*lvgi)

                rows.append({
                    'Year': year,
                    'DSRI': round(dsri, 4), 'GMI': round(gmi, 4),
                    'AQI': round(aqi, 4), 'SGI': round(sgi, 4),
                    'DEPI': round(depi, 4), 'SGAI': round(sgai, 4),
                    'TATA': round(tata, 4), 'LVGI': round(lvgi, 4),
                    'M_Score': round(m_score, 4),
                    'Manipulation': 'Nghi ngờ' if m_score > -2.22 else 'Bình thường'
                })
            except Exception as e:
                continue

        result = pd.DataFrame(rows)
        self.results['beneish'] = result
        return result

    # =====================================================================
    # OHLSON O-SCORE
    # O = -1.32 - 0.407*ln(TA) + 6.03*(TL/TA) - 1.43*(WC/TA)
    #     + 0.0757*(CL/CA) - 1.72*OENEG - 2.37*(NI/TA)
    #     - 1.83*(CFO/TL) + 0.285*INTWO - 0.521*CHIN
    # =====================================================================
    def ohlson_o_score(self) -> pd.DataFrame:
        """Tính Ohlson O-Score."""
        bs, is_df, cf = self.bs, self.is_df, self.cf
        if bs.empty or is_df.empty:
            return pd.DataFrame()

        rows = []
        for i in range(1, len(bs)):
            try:
                year = bs['Year'].iloc[i]

                ta = float(self._col(bs, 'TỔNG TÀI SẢN').iloc[i])
                tl = float(self._col(bs, 'NỢ PHẢI TRẢ').iloc[i])
                ca = float(self._col(bs, 'TÀI SẢN NGẮN HẠN').iloc[i])
                cl = float(self._col(bs, 'Nợ ngắn hạn').iloc[i])
                ni = float(self._col(is_df, 'Lãi/(lỗ) thuần sau thuế').iloc[i])
                ni_p = float(self._col(is_df, 'Lãi/(lỗ) thuần sau thuế').iloc[i-1])
                cfo = float(self._col(cf, 'Lưu chuyển tiền thuần từ các hoạt động sản xuất').iloc[i]) if not cf.empty else 0

                wc = ca - cl
                ta_safe = ta if ta > 0 else 1.0
                tl_safe = tl if tl > 0 else 1.0

                # OENEG: 1 if total liabilities > total assets
                oeneg = 1.0 if tl > ta else 0.0
                # INTWO: 1 if NI was negative for last 2 years
                intwo = 1.0 if ni < 0 and ni_p < 0 else 0.0
                # CHIN: change in NI
                chin = (ni - ni_p) / (abs(ni) + abs(ni_p)) if (abs(ni) + abs(ni_p)) > 0 else 0.0

                o_score = (-1.32
                          - 0.407 * np.log(ta_safe / 1_000_000)  # Scale TA in millions
                          + 6.03 * (tl / ta_safe)
                          - 1.43 * (wc / ta_safe)
                          + 0.0757 * (cl / max(ca, 1.0))
                          - 1.72 * oeneg
                          - 2.37 * (ni / ta_safe)
                          - 1.83 * (cfo / tl_safe)
                          + 0.285 * intwo
                          - 0.521 * chin)

                # Xác suất phá sản từ O-Score
                prob = 1 / (1 + np.exp(-o_score))

                rows.append({
                    'Year': year,
                    'O_Score': round(o_score, 4),
                    'PD_Ohlson': round(prob * 100, 2),
                    'Risk': 'Cao' if prob > 0.5 else ('Trung bình' if prob > 0.3 else 'Thấp')
                })
            except Exception:
                continue

        result = pd.DataFrame(rows)
        self.results['ohlson'] = result
        return result

    # =====================================================================
    # ZMIJEWSKI SCORE (Probit Model)
    # X = -4.336 - 4.513*(NI/TA) + 5.679*(TL/TA) - 0.004*(CA/CL)
    # =====================================================================
    def zmijewski_score(self) -> pd.DataFrame:
        """Tính Zmijewski Score."""
        bs, is_df = self.bs, self.is_df
        if bs.empty or is_df.empty:
            return pd.DataFrame()

        ta = self._col(bs, 'TỔNG TÀI SẢN').replace(0, np.nan)
        tl = self._col(bs, 'NỢ PHẢI TRẢ')
        ca = self._col(bs, 'TÀI SẢN NGẮN HẠN')
        cl = self._col(bs, 'Nợ ngắn hạn').replace(0, np.nan)
        ni = self._col(is_df, 'Lãi/(lỗ) thuần sau thuế')

        x = -4.336 - 4.513 * (ni / ta) + 5.679 * (tl / ta) - 0.004 * (ca / cl)
        prob = 1 / (1 + np.exp(-x))  # Probit → approximate logistic

        result = pd.DataFrame({
            'Year': bs['Year'].values,
            'Zmijewski_X': x.values,
            'PD_Zmijewski': (prob * 100).values,
            'Risk': pd.cut(prob, bins=[-np.inf, 0.3, 0.5, np.inf],
                          labels=['Thấp', 'Trung bình', 'Cao'])
        })

        self.results['zmijewski'] = result
        return result

    # =====================================================================
    # SLOAN ACCRUALS
    # Accruals = (NI - CFO) / Avg(TA)
    # =====================================================================
    def sloan_accruals(self) -> pd.DataFrame:
        """Tính Sloan Accruals Ratio."""
        bs, is_df, cf = self.bs, self.is_df, self.cf
        if bs.empty or is_df.empty or cf.empty:
            return pd.DataFrame()

        rows = []
        for i in range(1, len(bs)):
            try:
                year = bs['Year'].iloc[i]
                ni = float(self._col(is_df, 'Lãi/(lỗ) thuần sau thuế').iloc[i])
                cfo = float(self._col(cf, 'Lưu chuyển tiền thuần từ các hoạt động sản xuất').iloc[i])
                ta_c = float(self._col(bs, 'TỔNG TÀI SẢN').iloc[i])
                ta_p = float(self._col(bs, 'TỔNG TÀI SẢN').iloc[i-1])
                avg_ta = (ta_c + ta_p) / 2

                sloan = (ni - cfo) / avg_ta * 100 if avg_ta != 0 else 0

                rows.append({
                    'Year': year,
                    'Sloan_Pct': round(sloan, 2),
                    'Quality': ('Nghiêm trọng' if abs(sloan) > 25
                               else ('Cảnh báo' if abs(sloan) > 10
                                     else 'Tốt'))
                })
            except Exception:
                continue

        result = pd.DataFrame(rows)
        self.results['sloan'] = result
        return result

    # =====================================================================
    # DSCR — Debt Service Coverage Ratio (stressed)
    # DSCR = EBITDA * (1 - stress%) / (Interest + Principal)
    # =====================================================================
    def dscr_analysis(self, stress_pct: float = 0.3) -> pd.DataFrame:
        """Tính DSCR (Stressed)."""
        is_df, cf, bs = self.is_df, self.cf, self.bs
        if is_df.empty or bs.empty:
            return pd.DataFrame()

        ebitda = self._col(is_df, 'EBITDA')
        interest = self._col(is_df, 'Chi phí lãi vay', 'Chi phí tài chính').abs()
        # Nợ gốc = Tiền trả các khoản đi vay (CF)
        principal = self._col(cf, 'Tiển trả các khoản đi vay').abs() if not cf.empty else pd.Series([0] * len(is_df))

        debt_service = interest + principal
        debt_service_safe = debt_service.replace(0, np.nan)

        dscr_normal = ebitda / debt_service_safe
        dscr_stress = ebitda * (1 - stress_pct) / debt_service_safe

        result = pd.DataFrame({
            'Year': bs['Year'].values[:len(dscr_normal)],
            'EBITDA': ebitda.values,
            'Debt_Service': debt_service.values,
            'DSCR_Normal': dscr_normal.values,
            'DSCR_Stressed': dscr_stress.values,
            'Coverage': pd.cut(dscr_stress, bins=[-np.inf, 1.0, 1.5, np.inf],
                              labels=['Không đủ', 'Vừa đủ', 'An toàn'])
        })

        self.results['dscr'] = result
        return result

    # =====================================================================
    # LIQUIDITY RUNWAY (số tháng tồn tại)
    # Runway = Cash / abs(avg monthly operating cash outflow)
    # =====================================================================
    def liquidity_runway(self) -> pd.DataFrame:
        """Tính số tháng doanh nghiệp có thể cầm cự."""
        bs, cf = self.bs, self.cf
        if bs.empty or cf.empty:
            return pd.DataFrame()

        cash = self._col(bs, 'Tiền và tương đương tiền')
        cfo = self._col(cf, 'Lưu chuyển tiền thuần từ các hoạt động sản xuất')

        # Align lengths: take the shorter of the two, from the end (latest data)
        min_len = min(len(cash), len(cfo), len(bs))
        cash = cash.iloc[-min_len:].reset_index(drop=True)
        cfo = cfo.iloc[-min_len:].reset_index(drop=True)
        years = bs['Year'].values[-min_len:]

        # Tháng: nếu CFO âm, tính số tháng cầm cự = Cash / |CFO/12|
        monthly_burn = cfo / 12
        monthly_burn_safe = monthly_burn.replace(0, np.nan)

        # Chỉ tính khi CFO âm (doanh nghiệp đang "cháy tiền")
        runway_months = np.where(
            monthly_burn < 0,
            cash / monthly_burn.abs(),
            np.inf  # CFO dương = không cháy tiền
        )

        result = pd.DataFrame({
            'Year': years,
            'Cash': cash.values,
            'CFO_Annual': cfo.values,
            'Runway_Months': runway_months,
            'Status': ['Tốt' if r > 24 else ('Cầm cự' if r > 6 else 'Nguy hiểm')
                       for r in runway_months]
        })

        self.results['runway'] = result
        return result

    # =====================================================================
    # REAL ESTATE METRICS (Chuyên biệt BĐS)
    # =====================================================================
    def real_estate_metrics(self, quarterly_data: dict = None) -> pd.DataFrame:
        """
        Tính các chỉ số sinh tử chuyên biệt cho ngành BĐS.

        Sử dụng dữ liệu quý kèm TTM (nếu có) hoặc annual data.
        Các chỉ số:
        - cfo_to_short_debt: CFO TTM / Nợ ngắn hạn
        - interest_coverage_cfo: CFO TTM / Chi phí lãi vay TTM
        - inventory_to_assets: Hàng tồn kho / Tổng tài sản
        - receivables_to_revenue: Khoản phải thu / Doanh thu TTM
        - runway_interest: Tiền mặt / Chi phí lãi vay 1 quý
        """
        # Ưu tiên quarterly_data (có TTM), fallback sang annual
        if quarterly_data is not None:
            bs = quarterly_data.get('BALANCE_SHEET', pd.DataFrame())
            is_df = quarterly_data.get('INCOME_STATEMENT', pd.DataFrame())
            cf = quarterly_data.get('CASH_FLOW', pd.DataFrame())
        else:
            bs, is_df, cf = self.bs, self.is_df, self.cf

        if bs.empty or is_df.empty or cf.empty:
            return pd.DataFrame()

        rows = []
        for i in range(len(bs)):
            try:
                period = bs['Period'].iloc[i] if 'Period' in bs.columns else f"Y{int(bs['Year'].iloc[i])}"
                year = int(bs['Year'].iloc[i])
                quarter = int(bs['Quarter'].iloc[i]) if 'Quarter' in bs.columns else 4

                # Balance Sheet values
                ta = float(self._col(bs, 'TỔNG TÀI SẢN').iloc[i])
                inventory = float(self._col(bs, 'Hàng tồn kho').iloc[i])
                receivables = float(self._col(bs, 'Các khoản phải thu').iloc[i])
                cash = float(self._col(bs, 'Tiền và tương đương tiền').iloc[i])
                short_debt = float(self._col(bs, 'Nợ ngắn hạn').iloc[i])

                # TTM columns (nếu có) hoặc annual
                cfo_ttm_col = [c for c in cf.columns if 'TTM' in c and
                               'lưu chuyển tiền thuần từ các hoạt động sản xuất' in c.lower()]
                if cfo_ttm_col:
                    cfo_ttm = float(cf[cfo_ttm_col[0]].iloc[i])
                else:
                    cfo_ttm = float(self._col(cf, 'Lưu chuyển tiền thuần từ các hoạt động sản xuất').iloc[i])

                interest_ttm_col = [c for c in is_df.columns if 'TTM' in c and
                                    'chi phí lãi vay' in c.lower()]
                if interest_ttm_col:
                    interest_ttm = abs(float(is_df[interest_ttm_col[0]].iloc[i]))
                else:
                    interest_ttm = abs(float(self._col(is_df, 'Chi phí lãi vay', 'Chi phí tài chính').iloc[i]))

                # Interest single quarter
                interest_single_cols = [c for c in is_df.columns
                                        if 'chi phí lãi vay' in c.lower() and 'TTM' not in c]
                interest_single_q = abs(float(is_df[interest_single_cols[0]].iloc[i])) if interest_single_cols else interest_ttm / 4 if interest_ttm > 0 else 0.0

                # Revenue TTM
                rev_ttm_col = [c for c in is_df.columns if 'TTM' in c and
                               'doanh số thuần' in c.lower()]
                if rev_ttm_col:
                    rev_ttm = float(is_df[rev_ttm_col[0]].iloc[i])
                else:
                    rev_ttm = float(self._col(is_df, 'Doanh số thuần').iloc[i])

                # CFO quarterly
                cfo_q_col = [c for c in cf.columns
                             if 'lưu chuyển tiền thuần từ các hoạt động sản xuất' in c.lower()
                             and 'TTM' not in c]
                cfo_quarterly = float(cf[cfo_q_col[0]].iloc[i]) if cfo_q_col else cfo_ttm

                # === Khai phá cột nợ vay trực tiếp ===
                debt_cols = [c for c in bs.columns if any(p in c.lower() for p in ['vay', 'nợ thuê', 'nợ vay'])
                             and not any(x in c.lower() for x in ['cho vay', 'phải thu'])]
                total_debt = 0
                for c in debt_cols:
                    total_debt += float(bs[c].iloc[i])
                if total_debt == 0:
                    short_d = float(self._col(bs, 'Vay ngắn hạn', 'Vay và nợ', exclude=['cho vay', 'phải thu']).iloc[i])
                    long_d = float(self._col(bs, 'Vay dài hạn', 'Nợ dài hạn', exclude=['cho vay', 'phải thu']).iloc[i])
                    total_debt = short_d + long_d
                
                equity = float(self._col(bs, 'Vốn chủ sở hữu').iloc[i])
                leverage = equity / total_debt if total_debt > 0 else np.inf

                # === Compute BDS ratios ===
                inv_to_assets = inventory / ta if ta > 0 else 0
                recv_to_revenue = receivables / rev_ttm if rev_ttm > 0 else (np.inf if receivables > 0 else 0)
                interest_cov = cfo_ttm / interest_ttm if interest_ttm > 0 else (
                    np.inf if cfo_ttm > 0 else -np.inf)
                cfo_to_short = cfo_ttm / short_debt if short_debt > 0 else (
                    np.inf if cfo_ttm > 0 else -np.inf)
                runway_int = cash / interest_single_q if interest_single_q > 0 else np.inf

                # Kiểm tra NaN từ TTM chưa đủ 4 quý
                if np.isnan(cfo_ttm):
                    continue

                rows.append({
                    'Period': period,
                    'Year': year,
                    'Quarter': quarter,
                    'Total_Assets': ta,
                    'Inventory': inventory,
                    'Receivables': receivables,
                    'Cash': cash,
                    'CFO_TTM': cfo_ttm,
                    'CFO_Quarterly': cfo_quarterly,
                    'Interest_Quarterly': interest_single_q,
                    'Interest_TTM': interest_ttm,
                    'Short_Debt': short_debt,
                    'Revenue_TTM': rev_ttm,
                    'inventory_to_assets': round(inv_to_assets, 4),
                    'receivables_to_revenue': round(recv_to_revenue, 4),
                    'interest_coverage_cfo': round(interest_cov, 4),
                    'cfo_to_short_debt': round(cfo_to_short, 4),
                    'runway_interest': round(runway_int, 4),
                    'leverage_equity_debt': round(leverage, 4) if not np.isinf(leverage) else np.inf,
                })
            except Exception:
                continue

        result = pd.DataFrame(rows)
        self.results['bds_metrics'] = result
        return result

    # =====================================================================
    # RUN ALL
    # =====================================================================
    def run_all(self, quarterly_data: dict = None) -> dict[str, pd.DataFrame]:
        """Chạy tất cả các mô hình."""
        print(f"  [{self.ticker}] Tính Altman Z''-Score...")
        self.altman_z_score()
        print(f"  [{self.ticker}] Tính Beneish M-Score...")
        self.beneish_m_score()
        print(f"  [{self.ticker}] Tính Ohlson O-Score...")
        self.ohlson_o_score()
        print(f"  [{self.ticker}] Tính Zmijewski Score...")
        self.zmijewski_score()
        print(f"  [{self.ticker}] Tính Sloan Accruals...")
        self.sloan_accruals()
        print(f"  [{self.ticker}] Tính DSCR (Stressed)...")
        self.dscr_analysis()
        print(f"  [{self.ticker}] Tính Liquidity Runway...")
        self.liquidity_runway()

        # BĐS: tính thêm chỉ số chuyên biệt
        if self.industry == 'REAL_ESTATE':
            print(f"  [{self.ticker}] Tính Real Estate Metrics (BĐS)...")
            self.real_estate_metrics(quarterly_data)

        return self.results

    def save_results(self, out_dir: str):
        """Lưu kết quả các scores ra CSV."""
        import os
        ticker_dir = os.path.join(out_dir, self.ticker)
        os.makedirs(ticker_dir, exist_ok=True)

        for name, df in self.results.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                path = os.path.join(ticker_dir, f"{name}.csv")
                df.to_csv(path, index=False)
