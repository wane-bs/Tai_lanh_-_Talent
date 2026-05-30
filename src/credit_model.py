import numpy as np

class CreditUnderwriter:
    """Mô hình tính toán Hạn mức Tín dụng dựa trên dòng tiền và chốt chặn Bảng cân đối."""

    def __init__(self):
        self.base_target_dscr = 1.2
        self.min_leverage_ratio = 0.15 # Equity / (Total Debt + L) >= 0.15

    def calculate_capacity(self, cfo_ttm: float, icr: float, inventory_ta: float, 
                           equity_debt: float, wc_ta: float, equity: float, 
                           total_debt: float, rate: float, tenor: int,
                           pd_xgboost: float = 0.0, risk_level: int = 1, 
                           composite_score: float = 0.0) -> dict:
        """
        Tính toán hạn mức vay khả thi tối đa.
        """
        # 1. CFADS (Nếu nan thì xem như 0)
        cfads = cfo_ttm if not np.isnan(cfo_ttm) and cfo_ttm > 0 else 0.0

        # 2. Target DSCR adjustments
        target_dscr = self.base_target_dscr
        if not np.isnan(inventory_ta) and inventory_ta > 0.40:
            target_dscr += 0.3
        if not np.isnan(equity_debt) and equity_debt < 0.3:
            target_dscr += 0.3
        if not np.isnan(wc_ta) and wc_ta < 0:
            target_dscr += 0.2
            
        # AI Penalty: Tăng DSCR tuyến tính dựa trên XGBoost PD%
        if not np.isnan(pd_xgboost) and pd_xgboost > 0:
            target_dscr += (pd_xgboost / 100.0)

        # 3. PMT max
        pmt_max = cfads / target_dscr if target_dscr > 0 else 0.0

        # 4. L base (PV of Annuity)
        if rate > 0 and tenor > 0:
            pv_factor = (1 - (1 + rate) ** (-tenor)) / rate
            l_base = pmt_max * pv_factor
        else:
            l_base = 0.0

        # 5. Circuit Breakers (Chốt chặn)
        l_final = l_base
        status = "Khả thi"
        warnings = []
        ai_impact = "Không"

        # AI Circuit Breaker (Ngưỡng tử thần)
        if pd_xgboost > 55.0 or risk_level >= 4:
            l_final = 0.0
            status = "Từ chối"
            warnings.append(f"AI Circuit Breaker: Từ chối do rủi ro phá sản nghiêm trọng (PD: {pd_xgboost:.1f}%, Risk Level: {risk_level}).")
            ai_impact = "Từ chối hoàn toàn"

        # Chặn ICR
        if not np.isnan(icr) and icr < 1.0 and status != "Từ chối":
            l_final = 0.0
            status = "Từ chối"
            warnings.append("Khả năng trả lãi (ICR) < 1.0: Không đủ khả năng thanh toán nợ hiện tại.")

        # AI Haircut (Chiết khấu hạn mức) cho các mức rủi ro còn lại
        if status != "Từ chối":
            if risk_level == 3: # Stress
                l_final *= 0.60
                status = "Cắt giảm (AI Haircut 40%)"
                warnings.append("AI Haircut: Cắt giảm 40% hạn mức do thuộc nhóm rủi ro Căng thẳng (Stress).")
                ai_impact = "-40%"
            elif risk_level == 2: # Watch
                l_final *= 0.85
                status = "Cắt giảm (AI Haircut 15%)"
                warnings.append("AI Haircut: Cắt giảm 15% hạn mức do thuộc nhóm rủi ro Cảnh báo (Watch).")
                ai_impact = "-15%"

        # Chặn Đòn bẩy
        if equity > 0 and total_debt >= 0 and status != "Từ chối":
            # E / (D + L) >= 0.15 => D + L <= E / 0.15 => L <= E / 0.15 - D
            leverage_cap = (equity / self.min_leverage_ratio) - total_debt
            leverage_cap = max(0.0, leverage_cap)
            
            if l_final > leverage_cap:
                l_final = leverage_cap
                if "Cắt giảm" not in status:
                    status = "Cắt giảm (Haircut Đòn bẩy)"
                warnings.append(f"Chốt chặn đòn bẩy: Giới hạn dư nợ mới không vượt quá {leverage_cap/1e9:,.1f} Tỷ VND.")
        elif equity <= 0 and status != "Từ chối":
            l_final = 0.0
            status = "Từ chối"
            warnings.append("Vốn chủ sở hữu âm: Tình trạng mất vốn.")

        if cfads == 0 and status != "Từ chối":
            status = "Từ chối"
            warnings.append("Dòng tiền CFO âm hoặc bằng 0: Không có thặng dư trả nợ mới.")

        return {
            'CFADS': cfads,
            'Target_DSCR': target_dscr,
            'PMT_max': pmt_max,
            'L_base': l_base,
            'L_final': l_final,
            'Status': status,
            'Warnings': warnings,
            'AI_Impact': ai_impact
        }

    def generate_sensitivity_curve(self, current_params, rates: list) -> list:
        """Sinh dữ liệu độ nhạy cho biểu đồ."""
        curve = []
        for r in rates:
            res = self.calculate_capacity(
                cfo_ttm=current_params.get('cfo_ttm', 0),
                icr=current_params.get('icr', np.nan),
                inventory_ta=current_params.get('inventory_ta', np.nan),
                equity_debt=current_params.get('equity_debt', np.nan),
                wc_ta=current_params.get('wc_ta', np.nan),
                equity=current_params.get('equity', 0),
                total_debt=current_params.get('total_debt', 0),
                rate=r,
                tenor=current_params.get('tenor', 5),
                pd_xgboost=current_params.get('pd_xgboost', 0.0),
                risk_level=current_params.get('risk_level', 1),
                composite_score=current_params.get('composite_score', 0.0)
            )
            curve.append({'Rate': r, 'L_final': res['L_final']})
        return curve

    def generate_repayment_schedule(self, principal: float, rate: float, tenor: int, method: str = "annuity") -> list:
        """
        Tính lịch trả nợ (gốc và lãi) theo năm.
        method: 'annuity' (niên kim đều) hoặc 'equal_principal' (gốc đều)
        """
        schedule = []
        if principal <= 0 or tenor <= 0:
            return schedule

        remaining_principal = principal

        if method == "annuity":
            # PMT = L * [r * (1 + r)^n] / [(1 + r)^n - 1]
            if rate > 0:
                pmt = principal * (rate * (1 + rate) ** tenor) / ((1 + rate) ** tenor - 1)
            else:
                pmt = principal / tenor
            
            for t in range(1, tenor + 1):
                beg_bal = remaining_principal
                if beg_bal <= 0:
                    break
                interest = beg_bal * rate
                principal_paid = pmt - interest
                if t == tenor or principal_paid > beg_bal:
                    principal_paid = beg_bal
                    pmt = principal_paid + interest
                
                ending_bal = beg_bal - principal_paid
                schedule.append({
                    'Year': t,
                    'Beginning_Balance': beg_bal,
                    'Payment': pmt,
                    'Principal_Paid': principal_paid,
                    'Interest_Paid': interest,
                    'Ending_Balance': max(0.0, ending_bal)
                })
                remaining_principal = ending_bal

        elif method == "equal_principal":
            # Gốc đều
            p_const = principal / tenor
            for t in range(1, tenor + 1):
                beg_bal = remaining_principal
                if beg_bal <= 0:
                    break
                interest = beg_bal * rate
                principal_paid = min(p_const, beg_bal)
                if t == tenor:
                    principal_paid = beg_bal
                pmt = principal_paid + interest
                ending_bal = beg_bal - principal_paid
                schedule.append({
                    'Year': t,
                    'Beginning_Balance': beg_bal,
                    'Payment': pmt,
                    'Principal_Paid': principal_paid,
                    'Interest_Paid': interest,
                    'Ending_Balance': max(0.0, ending_bal)
                })
                remaining_principal = ending_bal

        return schedule

    def recommend_repayment_method(self, risk_level: int, dscr: float, inventory_ta: float, industry: str) -> dict:
        """
        Đề xuất phương án trả nợ phù hợp dựa trên bối cảnh rủi ro doanh nghiệp.
        """
        reasons = []
        grace_period_recommended = False
        
        # 1. Check industry and inventory
        if industry == 'REAL_ESTATE' and not np.isnan(inventory_ta) and inventory_ta > 0.40:
            reasons.append("Tỷ lệ Hàng tồn kho / Tổng tài sản cao (> 40%) đặc thù ngành Bất động sản. Dòng tiền thường bị kẹt ở dự án chưa bàn giao.")
            grace_period_recommended = True

        # 2. Check risk and DSCR
        if risk_level >= 3:
            recommended_method = "annuity"
            reasons.append("Doanh nghiệp thuộc nhóm rủi ro cao (Stress/Danger). Phương thức Niên kim đều giúp cố định nghĩa vụ trả nợ hàng năm ở mức thấp hơn trong những năm đầu so với Gốc đều, tránh gây áp lực dòng tiền đột biến có thể dẫn đến mất khả năng thanh toán.")
        elif not np.isnan(dscr) and dscr < 1.3:
            recommended_method = "annuity"
            reasons.append("Chỉ số DSCR khả dụng tương đối thấp (< 1.3x). Doanh nghiệp cần dòng tiền ổn định và dàn trải đều qua các năm.")
        else:
            recommended_method = "equal_principal"
            reasons.append("Doanh nghiệp ở trạng thái an toàn (Safe/Watch), dòng tiền dồi dào. Phương pháp Gốc đều, lãi giảm dần giúp giảm nhanh dư nợ gốc, tối thiểu hóa tổng chi phí lãi vay phải trả và giải phóng hạn mức tín dụng nhanh hơn.")
            
        if grace_period_recommended:
            reasons.append("Đề xuất kết hợp thêm ân hạn nợ gốc (Grace Period) từ 1-2 năm đầu để hỗ trợ doanh nghiệp hoàn thiện pháp lý và xây dựng dự án trước khi phát sinh nghĩa vụ trả nợ gốc.")

        method_vn = "Niên kim đều (Equal Annual Payment)" if recommended_method == "annuity" else "Gốc đều, lãi giảm dần (Equal Principal Payment)"
        
        return {
            'Method': recommended_method,
            'Method_VN': method_vn,
            'Reasons': reasons,
            'Grace_Period_Recommended': grace_period_recommended
        }

