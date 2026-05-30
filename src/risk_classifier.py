"""
Risk Classifier Module — Phân loại 5 mức rủi ro phá sản.

Composite Score = weighted combination of PD% + Altman Z + Beneish M + Ohlson + Zmijewski

| Mức | Tên      | PD%     | Altman Z     | Beneish M  |
|-----|----------|---------|--------------|------------|
|  1  | 🟢 Safe     | < 5%    | > 2.6        | < -2.22    |
|  2  | 🟡 Watch    | 5-20%   | 1.1-2.6      | ≤ -2.22    |
|  3  | 🟠 Stress   | 20-40%  | 1.1-2.6      | > -2.22    |
|  4  | 🔴 Danger   | 40-70%  | < 1.1        | Any        |
|  5  | ⚫ Critical | > 70%   | < 1.1        | > -2.22    |
"""

import pandas as pd
import numpy as np


class RiskClassifier:
    """Phân loại rủi ro phá sản 5 mức."""

    RISK_LEVELS = {
        1: {'name': 'Safe',     'emoji': '🟢', 'vn': 'An toàn',   'color': '#2ECC71'},
        2: {'name': 'Watch',    'emoji': '🟡', 'vn': 'Cảnh báo',  'color': '#F1C40F'},
        3: {'name': 'Stress',   'emoji': '🟠', 'vn': 'Căng thẳng','color': '#E67E22'},
        4: {'name': 'Danger',   'emoji': '🔴', 'vn': 'Nguy hiểm', 'color': '#E74C3C'},
        5: {'name': 'Critical', 'emoji': '⚫', 'vn': 'Nghiêm trọng','color': '#2C3E50'},
    }

    def __init__(self, industry: str = 'DEFAULT'):
        self.classifications = {}
        self.industry = industry
        
        if self.industry == 'RETAIL':
            self.WEIGHTS = {
                'pd_xgboost': 0.40,
                'pd_ohlson': 0.15,
                'pd_zmijewski': 0.05,
                'altman_signal': 0.25,
                'beneish_signal': 0.10,
                'dscr_signal': 0.05,
            }
        elif self.industry == 'REAL_ESTATE':
            # BĐS: Thay beneish bằng sloan, tăng XGBoost
            self.WEIGHTS = {
                'pd_xgboost': 0.40,
                'pd_ohlson': 0.15,
                'pd_zmijewski': 0.05,
                'altman_signal': 0.20,
                'sloan_signal': 0.15,
                'dscr_signal': 0.05,
            }
        else:
            self.WEIGHTS = {
                'pd_xgboost': 0.35,
                'pd_ohlson': 0.15,
                'pd_zmijewski': 0.15,
                'altman_signal': 0.20,
                'beneish_signal': 0.10,
                'dscr_signal': 0.05,
            }

    def _normalize_pd(self, value: float) -> float:
        """Chuẩn hóa PD về [0, 100]."""
        return max(0.0, min(100.0, float(value)))

    def _altman_to_signal(self, z: float) -> float:
        """
        Chuyển Altman Z-Score thành tín hiệu rủi ro [0, 100].
        Z > 2.6 → 0 (an toàn)
        Z < 1.1 → 100 (nguy hiểm)
        """
        if pd.isna(z):
            return 50.0  # Uncertain
        if z > 2.6:
            return 0.0
        elif z < 1.1:
            return 100.0
        else:
            # Linear interpolation trong grey zone
            return (2.6 - z) / (2.6 - 1.1) * 100

    def _beneish_to_signal(self, m: float) -> float:
        """
        Chuyển Beneish M-Score thành tín hiệu rủi ro [0, 100].
        M < -2.22 → 0 (bình thường)
        M > -1.78 → 100 (nghi ngờ cao)
        """
        if pd.isna(m):
            return 20.0  # Mặc định thấp
        if m < -2.22:
            return 0.0
        elif m > -1.78:
            return 100.0
        else:
            return (m + 2.22) / (-1.78 + 2.22) * 100

    def _dscr_to_signal(self, dscr: float) -> float:
        """
        Chuyển DSCR thành tín hiệu rủi ro [0, 100].
        DSCR > 1.5 → 0 (an toàn)
        DSCR < 1.0 → 100 (không đủ)
        """
        if pd.isna(dscr) or np.isinf(dscr):
            return 30.0
        if dscr > 1.5:
            return 0.0
        elif dscr < 1.0:
            return 100.0
        else:
            return (1.5 - dscr) / 0.5 * 100

    def _sloan_to_signal(self, sloan_pct: float) -> float:
        """
        Chuyển Sloan Accruals % thành tín hiệu rủi ro [0, 100].
        |Sloan| < 10% → 0 (chất lượng tốt)
        |Sloan| > 25% → 100 (lợi nhuận ảo nghiêm trọng)
        """
        if pd.isna(sloan_pct):
            return 30.0
        abs_sloan = abs(sloan_pct)
        if abs_sloan < 10:
            return 0.0
        elif abs_sloan > 25:
            return 100.0
        else:
            return (abs_sloan - 10) / 15 * 100

    def classify_single(self, row: dict) -> dict:
        """
        Phân loại rủi ro cho 1 observation (1 DN / 1 năm).

        Args:
            row: dict chứa các trường:
                - PD_XGBoost (%), PD_Ohlson (%), PD_Zmijewski (%)
                - Z_Score, M_Score, DSCR_Stressed
                - Year, Ticker

        Returns:
            dict: {composite_score, risk_level, risk_name, signals, ...}
        """
        signals = {}

        # PD signals
        pd_xgb = self._normalize_pd(row.get('PD_XGBoost', 50))
        pd_ohl = self._normalize_pd(row.get('PD_Ohlson', 50))
        pd_zm = self._normalize_pd(row.get('PD_Zmijewski', 50))

        signals['pd_xgboost'] = pd_xgb
        signals['pd_ohlson'] = pd_ohl
        signals['pd_zmijewski'] = pd_zm

        # Classical model signals
        signals['altman_signal'] = self._altman_to_signal(row.get('Z_Score', None))
        signals['beneish_signal'] = self._beneish_to_signal(row.get('M_Score', None))
        signals['dscr_signal'] = self._dscr_to_signal(row.get('DSCR_Stressed', None))

        # Sloan signal (dùng cho REAL_ESTATE thay beneish)
        signals['sloan_signal'] = self._sloan_to_signal(row.get('Sloan_Pct', None))

        # Composite Score (weighted average)
        composite = 0.0
        total_weight = 0.0
        for key, weight in self.WEIGHTS.items():
            if key in signals and not pd.isna(signals[key]):
                composite += signals[key] * weight
                total_weight += weight

        if total_weight > 0:
            composite = composite / total_weight  # Renormalize if some signals missing

        # Classify into 5 tiers
        if composite < 15:
            level = 1
        elif composite < 35:
            level = 2
        elif composite < 55:
            level = 3
        elif composite < 75:
            level = 4
        else:
            level = 5

        # Override rules (hard constraints)
        # Rule 1: PD > 70% → always Critical
        if pd_xgb > 70:
            level = max(level, 5)
        # Rule 2: Altman Z < 1.1 AND PD > 40% → at least Danger
        if row.get('Z_Score', 99) < 1.1 and pd_xgb > 40:
            level = max(level, 4)
        # Rule 3: Beneish > -2.22 AND PD > 20% → at least Stress
        if row.get('M_Score', -99) > -2.22 and pd_xgb > 20:
            level = max(level, 3)
            
        # RETAIL Rule
        if self.industry == 'RETAIL' and row.get('DSRI', 0) > 1.2:
            level = max(level, 4)

        # =====================================================================
        # REAL ESTATE HARD RULES (Ngắt mạch BĐS)
        # =====================================================================
        if self.industry == 'REAL_ESTATE':
            # RULE_REAL_ESTATE_1: CFO âm liên tục + không đủ trả lãi → Danger
            cfo_ttm = row.get('CFO_TTM', None)
            int_cov = row.get('interest_coverage_cfo', None)
            consecutive_neg = row.get('_consecutive_neg_cfo', 0)
            if (cfo_ttm is not None and cfo_ttm < 0 and
                    consecutive_neg >= 2 and
                    int_cov is not None and int_cov < 1):
                level = max(level, 4)

            # RULE_REAL_ESTATE_2: Runway interest < 1 quý → Critical
            runway_int = row.get('runway_interest', np.inf)
            if runway_int is not None and not np.isinf(runway_int) and runway_int < 1:
                level = max(level, 5)

        risk_info = self.RISK_LEVELS[level]

        return {
            'Composite_Score': round(composite, 2),
            'Risk_Level': level,
            'Risk_Name': risk_info['name'],
            'Risk_Emoji': risk_info['emoji'],
            'Risk_VN': risk_info['vn'],
            'Risk_Color': risk_info['color'],
            'Signals': signals,
        }

    def classify(self, features_df: pd.DataFrame,
                 calc_results: dict = None) -> pd.DataFrame:
        """
        Phân loại rủi ro cho toàn bộ Feature Matrix.

        Args:
            features_df: DataFrame có cột PD_XGBoost, Year, Ticker, ...
            calc_results: (optional) dict từ Calculator để bổ sung Z/M scores

        Returns:
            DataFrame gốc + thêm cột Risk
        """
        result = features_df.copy()

        # Tích hợp calculator results nếu có
        if calc_results:
            # Altman Z-Score
            if 'altman' in calc_results and not calc_results['altman'].empty:
                alt = calc_results['altman'][['Year', 'Z_Score']].copy()
                result = result.merge(alt, on='Year', how='left')
            # Beneish M-Score (có thể rỗng cho BĐS)
            if 'beneish' in calc_results and not calc_results['beneish'].empty:
                cols_to_get = ['Year', 'M_Score']
                if 'DSRI' in calc_results['beneish'].columns:
                    cols_to_get.append('DSRI')
                ben = calc_results['beneish'][cols_to_get].copy()
                result = result.merge(ben, on='Year', how='left')
            # Ohlson PD
            if 'ohlson' in calc_results and not calc_results['ohlson'].empty:
                ohl = calc_results['ohlson'][['Year', 'PD_Ohlson']].copy()
                result = result.merge(ohl, on='Year', how='left')
            # Zmijewski PD
            if 'zmijewski' in calc_results and not calc_results['zmijewski'].empty:
                zm = calc_results['zmijewski'][['Year', 'PD_Zmijewski']].copy()
                result = result.merge(zm, on='Year', how='left')
            # DSCR
            if 'dscr' in calc_results and not calc_results['dscr'].empty:
                ds = calc_results['dscr'][['Year', 'DSCR_Stressed']].copy()
                result = result.merge(ds, on='Year', how='left')
            # Sloan Accruals (cho REAL_ESTATE sloan_signal)
            if 'sloan' in calc_results and not calc_results['sloan'].empty:
                sl = calc_results['sloan']
                if 'Sloan_Pct' in sl.columns:
                    result = result.merge(sl[['Year', 'Sloan_Pct']].copy(), on='Year', how='left')
            # BĐS metrics (cho hard rules)
            if 'bds_metrics' in calc_results and not calc_results['bds_metrics'].empty:
                bds = calc_results['bds_metrics']
                bds_cols = ['Year', 'CFO_TTM', 'interest_coverage_cfo', 'runway_interest']
                available_bds = [c for c in bds_cols if c in bds.columns]
                cols_to_merge = [c for c in available_bds if c not in result.columns or c == 'Year']
                if len(cols_to_merge) > 1:
                    # Lấy Q4 cuối năm cho merge
                    if 'Quarter' in bds.columns:
                        bds_annual = bds.sort_values(['Year', 'Quarter']).groupby('Year').last().reset_index()
                    else:
                        bds_annual = bds
                    result = result.merge(bds_annual[cols_to_merge], on='Year', how='left')

        # Classify each row
        risk_rows = []

        # BĐS: track CFO âm liên tục cho Hard Rule 1
        consecutive_neg_cfo = 0

        for _, row in result.iterrows():
            row_dict = row.to_dict()

            # BĐS: đếm CFO âm liên tục
            if self.industry == 'REAL_ESTATE':
                cfo_val = row_dict.get('CFO_TTM', row_dict.get('cfo_to_short_debt', None))
                if cfo_val is not None and cfo_val < 0:
                    consecutive_neg_cfo += 1
                else:
                    consecutive_neg_cfo = 0
                row_dict['_consecutive_neg_cfo'] = consecutive_neg_cfo

            classification = self.classify_single(row_dict)
            risk_rows.append({
                'Year': row.get('Year'),
                'Ticker': row.get('Ticker', ''),
                'Composite_Score': classification['Composite_Score'],
                'Risk_Level': classification['Risk_Level'],
                'Risk_Name': classification['Risk_Name'],
                'Risk_Emoji': classification['Risk_Emoji'],
                'Risk_VN': classification['Risk_VN'],
                'Risk_Color': classification['Risk_Color'],
            })

        risk_df = pd.DataFrame(risk_rows)
        # Merge back
        result = result.merge(risk_df, on=['Year', 'Ticker'], how='left',
                              suffixes=('', '_new'))

        # Clean up duplicate columns
        for col in result.columns:
            if col.endswith('_new'):
                result.drop(col, axis=1, inplace=True)

        return result

    def summary(self, classified_df: pd.DataFrame) -> pd.DataFrame:
        """
        Tạo bảng tóm tắt rủi ro cho tất cả DN.

        Returns:
            DataFrame: Ticker | Latest_Year | PD% | Risk_Level | Risk_Name
        """
        if classified_df.empty:
            return pd.DataFrame()

        # Lấy năm gần nhất cho mỗi DN
        latest = classified_df.sort_values('Year').groupby('Ticker').last()
        summary_cols = ['Year', 'Composite_Score', 'Risk_Level',
                        'Risk_Name', 'Risk_Emoji', 'Risk_VN']
        available = [c for c in summary_cols if c in latest.columns]

        if 'PD_XGBoost' in latest.columns:
            available.append('PD_XGBoost')

        return latest[available].sort_values(
            'Risk_Level', ascending=False
        ).reset_index()

    def save_classification(self, classified_df: pd.DataFrame, out_dir: str):
        """Lưu kết quả phân loại ra CSV."""
        import os
        os.makedirs(out_dir, exist_ok=True)

        # Per ticker
        for ticker in classified_df['Ticker'].unique():
            t_df = classified_df[classified_df['Ticker'] == ticker]
            path = os.path.join(out_dir, f"{ticker}_risk.csv")
            t_df.to_csv(path, index=False)

        # All
        all_path = os.path.join(out_dir, "all_risk_classification.csv")
        classified_df.to_csv(all_path, index=False)
        print(f"  ✓ Lưu phân loại rủi ro ({len(classified_df)} records) vào {out_dir}")
