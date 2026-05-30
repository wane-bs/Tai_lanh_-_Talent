"""
BCTC-level Cash Flow Credit Scorer Module.
Computes credit scoring based on corporate financial statements (BCTC) using WOE weighting.
"""

import numpy as np
import pandas as pd

class BCTCCashFlowScorer:
    def __init__(self, base_score: int = 600, scaling_factor: float = 3.0):
        self.base_score = base_score
        self.scaling_factor = scaling_factor
        self.config = None
        
        import os, json
        config_path = os.path.join(os.path.dirname(__file__), "..", "optimized_scorecard_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error loading optimized_scorecard_config.json: {e}")

    def _interpolate_linear(self, val: float, x_min: float, x_max: float, y_min: float, y_max: float) -> float:
        """Nội suy tuyến tính thuận (val càng lớn y càng lớn)"""
        if pd.isna(val):
            return 0.0
        if val <= x_min:
            return float(y_min)
        if val >= x_max:
            return float(y_max)
        return float(y_min + (val - x_min) / (x_max - x_min) * (y_max - y_min))

    def _interpolate_inverse(self, val: float, x_min: float, x_max: float, y_min: float, y_max: float) -> float:
        """Nội suy tuyến tính nghịch (val càng nhỏ y càng lớn)"""
        if pd.isna(val):
            return 0.0
        if val <= x_min:
            return float(y_max)
        if val >= x_max:
            return float(y_min)
        return float(y_max - (val - x_min) / (x_max - x_min) * (y_max - y_min))

    def _get_dynamic_pts(self, feature: str, val: float, default_pts: float) -> float:
        """Returns dynamic points from config if available, using linear interpolation between bins."""
        if not self.config or 'features' not in self.config or feature not in self.config['features']:
            return float(default_pts)
            
        cfg = self.config['features'][feature]
        bins = cfg.get('bins', [])
        points_map = cfg.get('points', {})
        
        if pd.isna(val):
            return float(points_map.get("-1", 0))
            
        if not bins or not points_map:
            return float(default_pts)

        # Parse points map to float values
        pts = {}
        for k, v in points_map.items():
            try:
                pts[int(k)] = float(v)
            except ValueError:
                pass

        if not pts:
            return float(default_pts)

        n_bins = len(bins)

        # Calculate average for missing bins (ignoring NaN fallback index -1)
        valid_pts = [v for k, v in pts.items() if k != -1]
        avg_val = sum(valid_pts) / len(valid_pts) if valid_pts else sum(pts.values()) / len(pts)

        # Populate missing bin indices in the range [0, n_bins]
        for i in range(n_bins + 1):
            if i not in pts:
                pts[i] = avg_val

        if feature == 'revenue_volatility':
            # bins is sorted ascending: e.g. [0.15, 0.30, 0.45]
            if val <= bins[0]:
                return pts.get(0, 0.0)
            if val >= bins[-1]:
                return pts.get(n_bins, 0.0)
                
            for j in range(1, n_bins):
                if val >= bins[j-1] and val < bins[j]:
                    p_left = pts.get(j-1, 0.0)
                    p_right = pts.get(j, 0.0)
                    x_left = bins[j-1]
                    x_right = bins[j]
                    return float(p_left + (val - x_left) / (x_right - x_left) * (p_right - p_left))
        else:
            # bins is sorted descending: e.g. [2.0, 1.5, 1.25, 1.0, 0.75]
            if val >= bins[0]:
                return pts.get(0, 0.0)
            if val < bins[-1]:
                return pts.get(n_bins, 0.0)
                
            for j in range(1, n_bins):
                if val >= bins[j] and val < bins[j-1]:
                    p_left = pts.get(j, 0.0)
                    p_right = pts.get(j-1, 0.0)
                    x_left = bins[j]
                    x_right = bins[j-1]
                    return float(p_left + (val - x_left) / (x_right - x_left) * (p_right - p_left))

        return float(default_pts)

    def _find_col(self, df: pd.DataFrame, patterns: list[str], exclude: list[str] = None) -> str:
        """Helper to find column by a list of case-insensitive string patterns."""
        for c in df.columns:
            c_lower = str(c).lower()
            if exclude and any(x.lower() in c_lower for x in exclude):
                continue
            for p in patterns:
                if p.lower() in c_lower:
                    return c
        return None

    def calculate_metrics(self, ticker: str, etl) -> dict:
        """
        Calculates the 6 core metrics from BCTC sheets.
        Returns a dictionary of raw metrics.
        """
        annual = etl.get_annual_data(ticker)
        quarters = etl.get_ttm_data(ticker)

        df_bs = annual.get('BALANCE_SHEET', pd.DataFrame())
        df_is = annual.get('INCOME_STATEMENT', pd.DataFrame())
        df_cf = annual.get('CASH_FLOW', pd.DataFrame())

        metrics = {
            'cash_to_revenue': np.nan,
            'dscr': np.nan,
            'cash_buffer_days': np.nan,
            'revenue_volatility': np.nan,
            'equity_to_debt': np.nan,
            'cfo_growth_yoy': np.nan,
            'raw_values': {}
        }

        if df_bs.empty or df_is.empty or df_cf.empty:
            return metrics

        # 1. Column discovery
        rev_patterns = ['doanh thu thuần', 'doanh số thuần', 'doanh thu bán hàng']
        cash_patterns = ['tiền thu từ bán hàng', 'tiền thu bán hàng', 'thu từ bán hàng', 'thu từ cung cấp']
        cfo_patterns = ['lưu chuyển tiền thuần từ các hoạt động sản xuất', 'lưu chuyển tiền thuần từ hoạt động kinh doanh', 'lưu chuyển tiền thuần từ hđkd', 'lưu chuyển tiền thuần từ hoạt động sxkd']
        ie_patterns = ['chi phí lãi vay', 'lãi vay phải trả']
        std_patterns = ['vay và nợ thuê tài chính ngắn hạn', 'vay ngắn hạn']
        ltd_patterns = ['vay và nợ thuê tài chính dài hạn', 'vay dài hạn']
        cash_equiv_patterns = ['tiền và các khoản tương đương tiền', 'tiền và tương đương tiền', 'tiền mặt']
        cogs_patterns = ['giá vốn hàng bán', 'giá vốn']
        opex_sales_patterns = ['chi phí bán hàng']
        opex_admin_patterns = ['chi phí quản lý doanh nghiệp', 'chi phí quản lý']
        depr_patterns = ['khấu hao tscđ', 'khấu hao']
        ar_patterns = ['phải thu của khách hàng', 'phải thu ngắn hạn của khách hàng', 'phải thu ngắn hạn']
        eq_patterns = ['vốn chủ sở hữu']
        liab_patterns = ['nợ phải trả', 'tổng nợ']

        rev_col = self._find_col(df_is, rev_patterns)
        cash_col = self._find_col(df_cf, cash_patterns)
        cfo_col = self._find_col(df_cf, cfo_patterns)
        ie_col = self._find_col(df_is, ie_patterns)
        std_col = self._find_col(df_bs, std_patterns, exclude=['cho vay', 'phải thu'])
        ltd_col = self._find_col(df_bs, ltd_patterns, exclude=['cho vay', 'phải thu'])
        cash_equiv_col = self._find_col(df_bs, cash_equiv_patterns)
        cogs_col = self._find_col(df_is, cogs_patterns)
        opex_sales_col = self._find_col(df_is, opex_sales_patterns)
        opex_admin_col = self._find_col(df_is, opex_admin_patterns)
        depr_col = self._find_col(df_cf, depr_patterns)
        ar_col = self._find_col(df_bs, ar_patterns)
        eq_col = self._find_col(df_bs, eq_patterns)
        liab_col = self._find_col(df_bs, liab_patterns)

        # Helper to get last row value safely
        def get_last_val(df, col):
            if col and col in df.columns and len(df) > 0:
                val = df[col].iloc[-1]
                return float(val) if not pd.isna(val) else 0.0
            return 0.0

        # --- A1. Cash-to-Revenue Ratio ---
        latest_rev = get_last_val(df_is, rev_col)
        latest_cash_collected = get_last_val(df_cf, cash_col)
        
        if latest_rev > 0:
            if latest_cash_collected > 0:
                metrics['cash_to_revenue'] = latest_cash_collected / latest_rev
            elif ar_col and len(df_bs) >= 2:
                # Fallback: estimate using accounts receivable delta
                ar_t = df_bs[ar_col].iloc[-1]
                ar_t_1 = df_bs[ar_col].iloc[-2]
                delta_ar = ar_t - ar_t_1
                estimated_cash = latest_rev - delta_ar
                metrics['cash_to_revenue'] = estimated_cash / latest_rev
            else:
                metrics['cash_to_revenue'] = 1.0  # default
        else:
            metrics['cash_to_revenue'] = np.nan

        # --- B1. DSCR (CFO-based) ---
        latest_cfo = get_last_val(df_cf, cfo_col)
        # Use TTM cfo if available
        if quarters and 'CASH_FLOW' in quarters:
            q_cf = quarters['CASH_FLOW']
            q_cfo_col = self._find_col(q_cf, cfo_patterns)
            if q_cfo_col:
                matched_ttm = [c for c in q_cf.columns if q_cfo_col in c and '_TTM' in c]
                if matched_ttm:
                    latest_cfo = float(q_cf[matched_ttm[0]].iloc[-1])

        latest_ie = get_last_val(df_is, ie_col)
        std_debt = get_last_val(df_bs, std_col)
        ltd_debt = get_last_val(df_bs, ltd_col)
        total_debt = std_debt + ltd_debt
        
        if total_debt == 0.0 and liab_col:
            # Fallback to total liabilities if std/ltd debt is not found
            total_debt = get_last_val(df_bs, liab_col) * 0.5  # estimate interest-bearing debt as 50% of liabilities

        estimated_debt_service = latest_ie + (total_debt / 5)
        if estimated_debt_service > 0:
            metrics['dscr'] = max(0.0, latest_cfo) / estimated_debt_service
        else:
            metrics['dscr'] = np.nan

        # --- C1. Cash Buffer Days ---
        cash_equiv = get_last_val(df_bs, cash_equiv_col)
        cogs = get_last_val(df_is, cogs_col)
        opex_sales = get_last_val(df_is, opex_sales_col)
        opex_admin = get_last_val(df_is, opex_admin_col)
        depreciation = get_last_val(df_cf, depr_col)

        daily_cash_burn = (cogs + opex_sales + opex_admin - depreciation) / 365
        if daily_cash_burn > 0:
            metrics['cash_buffer_days'] = cash_equiv / daily_cash_burn
        else:
            metrics['cash_buffer_days'] = 999.0  # safe

        # --- D1. Revenue Volatility (CV last 8Q) ---
        if quarters and 'INCOME_STATEMENT' in quarters:
            q_is = quarters['INCOME_STATEMENT']
            q_rev_col = self._find_col(q_is, rev_patterns)
            if q_rev_col:
                recent_revs = q_is[q_rev_col].tail(8).dropna()
                if len(recent_revs) >= 4 and recent_revs.mean() > 0:
                    metrics['revenue_volatility'] = recent_revs.std() / recent_revs.mean()
        
        # Fallback to annual revenue CV if quarterly is missing
        if np.isnan(metrics['revenue_volatility']) and rev_col and len(df_is) >= 3:
            annual_revs = df_is[rev_col].dropna()
            if annual_revs.mean() > 0:
                metrics['revenue_volatility'] = annual_revs.std() / annual_revs.mean()

        # --- E1. Equity / Total Debt ---
        equity = get_last_val(df_bs, eq_col)
        if total_debt > 0:
            metrics['equity_to_debt'] = equity / total_debt
        else:
            metrics['equity_to_debt'] = np.nan

        # --- F1. CFO Growth (YoY) ---
        if cfo_col and len(df_cf) >= 2:
            cfo_t = df_cf[cfo_col].iloc[-1]
            cfo_t_1 = df_cf[cfo_col].iloc[-2]
            if abs(cfo_t_1) > 0:
                metrics['cfo_growth_yoy'] = (cfo_t - cfo_t_1) / abs(cfo_t_1)
            else:
                metrics['cfo_growth_yoy'] = 0.0
        else:
            # Không đủ dữ liệu (≥2 năm CF) — trả NaN để được chấm 0 điểm (không bị bias +5)
            metrics['cfo_growth_yoy'] = np.nan

        # Store raw values for presentation
        metrics['raw_values'] = {
            'revenue': latest_rev,
            'cash_collected': latest_cash_collected,
            'cfo_ttm': latest_cfo,
            'total_debt': total_debt,
            'interest_expense': latest_ie,
            'cash_equiv': cash_equiv,
            'daily_burn': daily_cash_burn,
            'equity': equity
        }

        return metrics

    def compute_score(self, metrics: dict) -> tuple[int, dict]:
        """
        Maps raw metrics to WOE points using linear interpolation and calculates final score and grade.
        Returns (total_score, score_details)
        """
        # --- Warning khi chưa calibrate ---
        if self.config is None:
            import warnings
            warnings.warn(
                "BCTCCashFlowScorer đang chạy ở EXPERT MODE (chưa calibrate). "
                "Scores dựa trên expert judgment, không phải thống kê. "
                "Chạy run_backtest.py để calibrate trước để có weighted points chính xác hơn.",
                UserWarning, stacklevel=2
            )

        details = {}
        total_points = 0.0

        # 1. Cash-to-Revenue
        ctr = metrics.get('cash_to_revenue', np.nan)
        if pd.isna(ctr):
            pts = 0.0
            label = "N/A"
        else:
            pts = self._interpolate_linear(ctr, 0.60, 0.95, -20.0, 20.0)
            if ctr >= 0.95:
                label = f"{ctr*100:.1f}% (Xuất sắc)"
            elif ctr >= 0.80:
                label = f"{ctr*100:.1f}% (Khá)"
            elif ctr >= 0.70:
                label = f"{ctr*100:.1f}% (Trung bình)"
            else:
                label = f"{ctr*100:.1f}% (Yếu - Rủi ro cao)"
            
        pts = self._get_dynamic_pts('cash_to_revenue', ctr, pts)
        details['cash_to_revenue'] = {'points': pts, 'value': ctr, 'label': label}
        total_points += pts

        # 2. DSCR
        dscr = metrics.get('dscr', np.nan)
        if pd.isna(dscr):
            pts = 0.0
            label = "N/A"
        else:
            pts = self._interpolate_linear(dscr, 0.50, 2.0, -25.0, 25.0)
            if dscr >= 2.0:
                label = f"{dscr:.2f}x (Rất an toàn)"
            elif dscr >= 1.5:
                label = f"{dscr:.2f}x (An toàn)"
            elif dscr >= 1.25:
                label = f"{dscr:.2f}x (Khá)"
            elif dscr >= 1.0:
                label = f"{dscr:.2f}x (Rủi ro nhẹ)"
            elif dscr >= 0.75:
                label = f"{dscr:.2f}x (Căng thẳng dòng tiền)"
            else:
                label = f"{dscr:.2f}x (Mất khả năng trả nợ)"
            
        pts = self._get_dynamic_pts('dscr', dscr, pts)
        details['dscr'] = {'points': pts, 'value': dscr, 'label': label}
        total_points += pts

        # 3. Cash Buffer Days
        cbd = metrics.get('cash_buffer_days', np.nan)
        if pd.isna(cbd):
            pts = 0.0
            label = "N/A"
        else:
            pts = self._interpolate_linear(cbd, 10.0, 90.0, -10.0, 15.0)
            if cbd >= 90:
                label = f"{cbd:.1f} ngày (Dồi dào)"
            elif cbd >= 45:
                label = f"{cbd:.1f} ngày (An toàn)"
            elif cbd >= 15:
                label = f"{cbd:.1f} ngày (Trung bình)"
            else:
                label = f"{cbd:.1f} ngày (Cạn kiệt - Rủi ro cao)"
            
        pts = self._get_dynamic_pts('cash_buffer_days', cbd, pts)
        details['cash_buffer_days'] = {'points': pts, 'value': cbd, 'label': label}
        total_points += pts

        # 4. Revenue Volatility
        vol = metrics.get('revenue_volatility', np.nan)
        if pd.isna(vol):
            pts = 0.0
            label = "N/A"
        else:
            pts = self._interpolate_inverse(vol, 0.15, 0.45, -10.0, 15.0)
            if vol < 0.15:
                label = f"{vol*100:.1f}% (Ổn định rất cao)"
            elif vol < 0.30:
                label = f"{vol*100:.1f}% (Ổn định tốt)"
            elif vol < 0.45:
                label = f"{vol*100:.1f}% (Biến động trung bình)"
            else:
                label = f"{vol*100:.1f}% (Biến động cực lớn)"
            
        pts = self._get_dynamic_pts('revenue_volatility', vol, pts)
        details['revenue_volatility'] = {'points': pts, 'value': vol, 'label': label}
        total_points += pts

        # 5. Equity to Debt
        eqd = metrics.get('equity_to_debt', np.nan)
        if pd.isna(eqd):
            pts = 0.0
            label = "N/A"
        else:
            pts = self._interpolate_linear(eqd, 0.20, 1.5, -15.0, 15.0)
            if eqd >= 1.5:
                label = f"{eqd:.2f}x (Đòn bẩy rất thấp)"
            elif eqd >= 1.0:
                label = f"{eqd:.2f}x (Đòn bẩy thấp)"
            elif eqd >= 0.5:
                label = f"{eqd:.2f}x (Đòn bẩy trung bình)"
            elif eqd >= 0.3:
                label = f"{eqd:.2f}x (Đòn bẩy tương đối cao)"
            else:
                label = f"{eqd:.2f}x (Đòn bẩy rất cao - Rủi ro)"
            
        pts = self._get_dynamic_pts('equity_to_debt', eqd, pts)
        details['equity_to_debt'] = {'points': pts, 'value': eqd, 'label': label}
        total_points += pts

        # 6. CFO Growth
        cg = metrics.get('cfo_growth_yoy', np.nan)
        if pd.isna(cg):
            pts = 0.0
            label = "N/A"
        else:
            pts = self._interpolate_linear(cg, -0.20, 0.20, -10.0, 10.0)
            if cg >= 0.15:
                label = f"{cg*100:+.1f}% (Tăng trưởng tốt)"
            elif cg >= 0.0:
                label = f"{cg*100:+.1f}% (Tăng trưởng nhẹ)"
            elif cg >= -0.15:
                label = f"{cg*100:+.1f}% (Suy giảm nhẹ)"
            else:
                label = f"{cg*100:+.1f}% (Suy giảm mạnh)"
            
        pts = self._get_dynamic_pts('cfo_growth_yoy', cg, pts)
        details['cfo_growth_yoy'] = {'points': pts, 'value': cg, 'label': label}
        total_points += pts

        # Score calculation
        if self.config and 'base_score' in self.config:
            # When calibrated, score is sum of points + base_score (offset is inside points)
            final_score = int(self.config['base_score'] + total_points)
        else:
            final_score = int(self.base_score + (total_points * self.scaling_factor))
            
        final_score = max(300, min(1000, final_score))  # Cap score

        return final_score, details

    def get_decision(self, score: int) -> tuple[str, str, str]:
        """
        Returns (Grade, Decision, Color) based on score.
        """
        if score >= 850:
            return "Grade A+", "Auto-approve, lãi suất ưu đãi", "#2ecc71"
        elif score >= 700:
            return "Grade A", "Auto-approve", "#2ecc71"
        elif score >= 600:
            return "Grade B", "Approve + Điều khoản kiểm soát dòng tiền bổ sung", "#3498db"
        elif score >= 500:
            return "Grade C", "Chuyển phê duyệt tay (Manual review bắt buộc), Haircut tối thiểu 20%", "#f39c12"
        else:
            return "Grade D", "TỪ CHỐI cấp hạn mức tín dụng (Rủi ro dòng tiền rất cao)", "#e74c3c"

    def get_normalized_points(self, details: dict) -> list[float]:
        """
        Quy đổi điểm thành phần của 6 tiêu chí về thang [0, 100] để vẽ Radar.
        Tự động điều chỉnh dải điểm dựa trên config (nếu đã calibrate) hoặc default.
        """
        features_order = [
            'cash_to_revenue',
            'dscr',
            'cash_buffer_days',
            'revenue_volatility',
            'equity_to_debt',
            'cfo_growth_yoy'
        ]
        
        # Default ranges in expert mode
        default_ranges = {
            'cash_to_revenue': (-20.0, 20.0),
            'dscr': (-25.0, 25.0),
            'cash_buffer_days': (-10.0, 15.0),
            'revenue_volatility': (-10.0, 15.0),
            'equity_to_debt': (-15.0, 15.0),
            'cfo_growth_yoy': (-10.0, 10.0)
        }
        
        norm_points = []
        for feat in features_order:
            pts = float(details.get(feat, {}).get('points', 0.0))
            
            # Determine min and max points for scaling
            if self.config and 'features' in self.config and feat in self.config['features']:
                points_map = self.config['features'][feat].get('points', {})
                valid_pts = [float(v) for k, v in points_map.items() if k != "-1"]
                if valid_pts:
                    min_p = min(valid_pts)
                    max_p = max(valid_pts)
                else:
                    min_p, max_p = default_ranges[feat]
            else:
                min_p, max_p = default_ranges[feat]
                
            # Normalize to 0-100
            if max_p > min_p:
                norm_val = (pts - min_p) / (max_p - min_p) * 100
            else:
                norm_val = 50.0  # fallback
            norm_points.append(max(0.0, min(100.0, norm_val)))
            
        return norm_points
