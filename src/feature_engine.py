"""
Feature Engineering Module — Xây dựng Feature Matrix cho mô hình ML.

Chức năng:
1. Trích xuất đặc trưng tài chính từ dữ liệu BCTC và Calculator scores
2. Xử lý Skewness (Log10 / Sqrt)
3. Outlier capping (IQR)
4. Missing value imputation (Median)
5. StandardScaler normalization

Input:  annual_data (từ ETL), calculator results (từ Calculator)
Output: Feature DataFrame sẵn sàng cho ML Engine
"""

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler


class FeatureEngine:
    """Xây dựng và biến đổi Feature Matrix."""

    # Danh sách đặc trưng cốt lõi cần trích xuất
    CORE_FEATURES = [
        'wc_ta', 're_ta', 'ebit_ta', 'bv_eq_tl',       # Altman components
        'cf_td', 'ni_ta', 'ca_cl', 'tl_ta',             # Solvency / Leverage
        'sloan_accruals', 'z_score', 'm_score',          # Forensic scores
        'o_score', 'zmijewski_x',                         # PD models
        'dscr_stressed', 'runway_months',                  # Survival
        'revenue_growth', 'asset_turnover', 'roe',        # Performance
        # BĐS-specific (Real Estate)
        'cfo_to_short_debt', 'interest_coverage_cfo',
        'inventory_to_assets', 'receivables_to_revenue',
        'runway_interest',
    ]

    def __init__(self, industry: str = 'DEFAULT'):
        self.scaler = StandardScaler()
        self.feature_stats = {}  # Lưu thống kê cho transform mới
        self.industry = industry

    # =================================================================
    # 1. TRÍCH XUẤT ĐẶC TRƯNG TỪ DỮ LIỆU THÔ
    # =================================================================
    def extract_features(self, annual_data: dict, calc_results: dict,
                         ticker: str = "", industry: str = None) -> pd.DataFrame:
        """
        Kết hợp dữ liệu BCTC thô và kết quả Calculator thành 1 Feature Matrix.

        Args:
            annual_data: dict {BALANCE_SHEET/INCOME_STATEMENT/CASH_FLOW: DataFrame}
            calc_results: dict từ BankruptcyCalculator.run_all()
            ticker: mã chứng khoán

        Returns:
            DataFrame với 1 hàng = 1 năm, các cột = features
        """
        bs = annual_data.get('BALANCE_SHEET', pd.DataFrame())
        is_df = annual_data.get('INCOME_STATEMENT', pd.DataFrame())
        cf = annual_data.get('CASH_FLOW', pd.DataFrame())

        if bs.empty or is_df.empty:
            return pd.DataFrame()

        # --- Validate minimum data requirement ---
        n_years = len(bs)
        if n_years < 1:
            print(f"  [{ticker}] ✗ Không có dữ liệu năm — bỏ qua.")
            return pd.DataFrame()
        if n_years < 2:
            import warnings
            warnings.warn(
                f"[{ticker}] Chỉ có {n_years} năm dữ liệu — "
                f"features cần ≥2 năm (revenue_growth, Beneish, Sloan, CFO growth) "
                f"sẽ là NaN và không ảnh hưởng tới scoring.",
                UserWarning, stacklevel=2
            )
        # Tiếp tục tính các features 1-năm được (Altman, Zmijewski, v.v.)

        years = bs['Year'].values
        n = len(years)
        features = pd.DataFrame({'Year': years, 'Ticker': ticker})

        # --- Ratio tính trực tiếp từ BCTC ---
        _industry = industry or self.industry
        ta = self._col(bs, 'TỔNG TÀI SẢN').replace(0, np.nan)
        ca = self._col(bs, 'TÀI SẢN NGẮN HẠN')
        cl = self._col(bs, 'Nợ ngắn hạn').replace(0, np.nan)
        tl = self._col(bs, 'NỢ PHẢI TRẢ').replace(0, np.nan)
        vcsh = self._col(bs, 'VỐN CHỦ SỞ HỮU')
        re = self._col(bs, 'Lãi chưa phân phối', 'LNST chưa phân phối')
        ni = self._col(is_df, 'Lãi/(lỗ) thuần sau thuế')
        ebit = self._col(is_df, 'EBIT')
        rev = self._col(is_df, 'Doanh số thuần')
        inventory = self._col(bs, 'Hàng tồn kho')

        # WC / TA — BĐS: loại bỏ HTK để tập trung dòng tiền
        if _industry == 'REAL_ESTATE':
            # WC ròng = (CA - Hàng tồn kho) - CL
            features['wc_ta'] = (ca - inventory - cl.fillna(0)) / ta
        else:
            features['wc_ta'] = (ca - cl.fillna(0)) / ta
        features['re_ta'] = re / ta
        features['ebit_ta'] = ebit / ta
        features['bv_eq_tl'] = vcsh / tl
        features['ni_ta'] = ni / ta
        features['ca_cl'] = ca / cl
        features['tl_ta'] = tl.fillna(0) / ta
        features['asset_turnover'] = rev / ta
        features['roe'] = ni / vcsh.replace(0, np.nan)

        # CFO / Total Debt
        if not cf.empty:
            cfo = self._col(cf, 'Lưu chuyển tiền thuần từ các hoạt động sản xuất')
            features['cf_td'] = cfo / tl
        else:
            features['cf_td'] = 0.0

        # Revenue growth (YoY)
        rev_vals = rev.values.astype(float)
        growth = np.full(n, np.nan)
        for i in range(1, n):
            if rev_vals[i - 1] != 0:
                growth[i] = (rev_vals[i] - rev_vals[i - 1]) / abs(rev_vals[i - 1])
        features['revenue_growth'] = growth

        # --- Tích hợp kết quả Calculator ---
        # Altman Z-Score
        if 'altman' in calc_results and not calc_results['altman'].empty:
            alt = calc_results['altman'][['Year', 'Z_Score']].copy()
            alt.columns = ['Year', 'z_score']
            features = features.merge(alt, on='Year', how='left')
        else:
            features['z_score'] = np.nan

        # Beneish M-Score
        if 'beneish' in calc_results and not calc_results['beneish'].empty:
            ben = calc_results['beneish'][['Year', 'M_Score']].copy()
            ben.columns = ['Year', 'm_score']
            features = features.merge(ben, on='Year', how='left')
        else:
            features['m_score'] = np.nan

        # Ohlson O-Score
        if 'ohlson' in calc_results and not calc_results['ohlson'].empty:
            ohl = calc_results['ohlson'][['Year', 'O_Score']].copy()
            ohl.columns = ['Year', 'o_score']
            features = features.merge(ohl, on='Year', how='left')
        else:
            features['o_score'] = np.nan

        # Zmijewski
        if 'zmijewski' in calc_results and not calc_results['zmijewski'].empty:
            zm = calc_results['zmijewski'][['Year', 'Zmijewski_X']].copy()
            zm.columns = ['Year', 'zmijewski_x']
            features = features.merge(zm, on='Year', how='left')
        else:
            features['zmijewski_x'] = np.nan

        # Sloan Accruals
        if 'sloan' in calc_results and not calc_results['sloan'].empty:
            sl = calc_results['sloan'][['Year', 'Sloan_Pct']].copy()
            sl.columns = ['Year', 'sloan_accruals']
            features = features.merge(sl, on='Year', how='left')
        else:
            features['sloan_accruals'] = np.nan

        # DSCR Stressed
        if 'dscr' in calc_results and not calc_results['dscr'].empty:
            ds = calc_results['dscr'][['Year', 'DSCR_Stressed']].copy()
            ds.columns = ['Year', 'dscr_stressed']
            features = features.merge(ds, on='Year', how='left')
        else:
            features['dscr_stressed'] = np.nan

        # Liquidity Runway
        if 'runway' in calc_results and not calc_results['runway'].empty:
            rw = calc_results['runway'][['Year', 'Runway_Months']].copy()
            rw.columns = ['Year', 'runway_months']
            features = features.merge(rw, on='Year', how='left')
        else:
            features['runway_months'] = np.nan

        # --- BĐS Metrics (Real Estate) ---
        if 'bds_metrics' in calc_results and not calc_results['bds_metrics'].empty:
            bds = calc_results['bds_metrics'].copy()
            bds_cols = ['Year', 'cfo_to_short_debt', 'interest_coverage_cfo',
                        'inventory_to_assets', 'receivables_to_revenue', 'runway_interest']
            available_bds = [c for c in bds_cols if c in bds.columns]
            if available_bds:
                # Nếu có dữ liệu quý, lấy giá trị cuối năm (Q4) để merge với annual features
                if 'Quarter' in bds.columns:
                    bds_annual = bds.sort_values(['Year', 'Quarter']).groupby('Year').last().reset_index()
                else:
                    bds_annual = bds
                features = features.merge(bds_annual[available_bds], on='Year', how='left')

        return features

    # =================================================================
    # 2. XỬ LÝ SKEWNESS (từ Bankruptcy-Prediction ML reference)
    # =================================================================
    def correct_skewness(self, df: pd.DataFrame,
                         feature_cols: list = None) -> pd.DataFrame:
        """
        Xử lý độ lệch (skewness) cho các cột features.
        - Skew > 2:  Log10 transform
        - 0 < Skew ≤ 2:  Sqrt transform
        - Skew ≤ 0:  Giữ nguyên (đã cân bằng)

        Xử lý giá trị âm bằng cách dịch chuyển (shift) trước khi transform.
        """
        if feature_cols is None:
            feature_cols = [c for c in df.columns
                           if c not in ['Year', 'Ticker']]

        result = df.copy()

        for col in feature_cols:
            series = result[col].dropna()
            if len(series) < 3:
                continue

            skew = series.skew()

            # BĐS đặc biệt: inventory_to_assets cực kỳ right-skewed
            if col in ('inventory_to_assets', 'receivables_to_revenue') and skew > 1:
                shift = abs(series.min()) + 1 if series.min() < 0 else 0
                result[col] = np.log1p(result[col] + shift)
                continue

            if skew > 2:
                # Log10 transform (shift nếu có giá trị âm)
                shift = abs(series.min()) + 1 if series.min() < 0 else 1
                result[col] = np.log10(result[col] + shift)
            elif skew > 0:
                # Sqrt transform (shift nếu có giá trị âm)
                shift = abs(series.min()) + 1 if series.min() < 0 else 1
                result[col] = np.sqrt(result[col] + shift)
            # skew ≤ 0: giữ nguyên

        return result

    # =================================================================
    # 3. XỬ LÝ OUTLIERS (IQR Capping)
    # =================================================================
    def cap_outliers(self, df: pd.DataFrame,
                     feature_cols: list = None,
                     iqr_factor: float = 1.5) -> pd.DataFrame:
        """
        Giới hạn giá trị ngoại lai bằng phương pháp IQR capping.
        Thay vì xóa, giới hạn giá trị trong [Q1 - 1.5*IQR, Q3 + 1.5*IQR].
        """
        if feature_cols is None:
            feature_cols = [c for c in df.columns
                           if c not in ['Year', 'Ticker']]

        result = df.copy()

        for col in feature_cols:
            series = result[col].dropna()
            if len(series) < 4:
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - iqr_factor * iqr
            upper = q3 + iqr_factor * iqr

            result[col] = result[col].clip(lower=lower, upper=upper)

        return result

    # =================================================================
    # 4. MISSING VALUE IMPUTATION (Median)
    # =================================================================
    def impute_missing(self, df: pd.DataFrame,
                       feature_cols: list = None) -> pd.DataFrame:
        """
        Điền giá trị thiếu bằng Expanding Median (chỉ dùng dữ liệu quá khứ).

        Tránh data leakage: tại thời điểm t chỉ dùng median(t0..t),
        không dùng thông tin của năm tương lai t+1, t+2...

        Fallback cuối: nếu toàn cột NaN, dùng global median của cột đó.
        """
        if feature_cols is None:
            feature_cols = [c for c in df.columns
                           if c not in ['Year', 'Ticker']]

        result = df.copy()
        for col in feature_cols:
            if col not in result.columns:
                continue
            # Expanding window: median tại năm t = median(t0..t)
            result[col] = result[col].fillna(result[col].expanding().median())
            # Fallback cuối: nếu vẫn còn NaN (VD: cột NaN ngay từ row đầu)
            global_median = result[col].median()
            if not pd.isna(global_median):
                result[col] = result[col].fillna(global_median)

        return result

    # =================================================================
    # 5. CHUẨN HÓA (StandardScaler)
    # =================================================================
    def normalize(self, df: pd.DataFrame,
                  feature_cols: list = None,
                  fit: bool = True) -> pd.DataFrame:
        """
        Chuẩn hóa features bằng StandardScaler (z-score normalization).
        """
        if feature_cols is None:
            feature_cols = [c for c in df.columns
                           if c not in ['Year', 'Ticker']]

        result = df.copy()
        valid_cols = [c for c in feature_cols if c in result.columns]

        if not valid_cols:
            return result

        if fit:
            result[valid_cols] = self.scaler.fit_transform(result[valid_cols])
        else:
            result[valid_cols] = self.scaler.transform(result[valid_cols])

        return result

    # =================================================================
    # FULL PIPELINE
    # =================================================================
    def transform(self, annual_data: dict, calc_results: dict,
                  ticker: str = "",
                  normalize: bool = False) -> pd.DataFrame:
        """
        Pipeline đầy đủ: Extract → Impute → (Normalize).

        Returns:
            DataFrame với features đã xử lý, sẵn sàng cho ML Engine.
        """
        # Step 1: Trích xuất features
        features = self.extract_features(annual_data, calc_results, ticker)
        if features.empty:
            return features

        feature_cols = [c for c in features.columns
                        if c not in ['Year', 'Ticker']]

        # (Đã loại bỏ Step 2: Cap outliers và Step 3: Xử lý skewness)
        # Việc áp dụng các hàm này trên tập kiểm thử (inference) làm biến dạng 
        # số liệu thực tế so với thang đo lúc huấn luyện mô hình.

        # Step 4: Impute missing values
        features = self.impute_missing(features, feature_cols)

        # Step 5: (Tùy chọn) Chuẩn hóa
        if normalize:
            features = self.normalize(features, feature_cols)

        return features

    def transform_multi(self, etl_processor, calculator_class,
                        normalize: bool = False) -> pd.DataFrame:
        """
        Xử lý tất cả doanh nghiệp từ ETL → Feature Matrix chung.

        Args:
            etl_processor: ETLProcessor instance đã load dữ liệu
            calculator_class: class BankruptcyCalculator
            normalize: có chuẩn hóa không

        Returns:
            DataFrame gộp tất cả DN (mỗi hàng = 1 DN/năm)
        """
        all_features = []

        for ticker in etl_processor.companies:
            annual = etl_processor.get_annual_data(ticker)
            calc = calculator_class(annual, ticker)
            calc_results = calc.run_all()
            features = self.transform(annual, calc_results, ticker, normalize=False)
            if not features.empty:
                all_features.append(features)

        if not all_features:
            return pd.DataFrame()

        combined = pd.concat(all_features, ignore_index=True)

        # Normalize trên toàn bộ dữ liệu kết hợp
        if normalize:
            feature_cols = [c for c in combined.columns
                            if c not in ['Year', 'Ticker']]
            combined = self.normalize(combined, feature_cols, fit=True)

        return combined

    # =================================================================
    # Utility
    # =================================================================
    def _col(self, df, *patterns) -> pd.Series:
        """Tìm cột khớp với patterns."""
        for pat in patterns:
            for c in df.columns:
                if pat.lower() in c.lower():
                    return pd.to_numeric(df[c], errors='coerce').fillna(0.0)
        return pd.Series([0.0] * len(df), index=df.index)

    def save_features(self, df: pd.DataFrame, out_dir: str):
        """Lưu Feature Matrix ra CSV."""
        import os
        os.makedirs(out_dir, exist_ok=True)

        # Lưu theo ticker
        for ticker in df['Ticker'].unique():
            ticker_df = df[df['Ticker'] == ticker]
            path = os.path.join(out_dir, f"{ticker}_features.csv")
            ticker_df.to_csv(path, index=False)

        # Lưu toàn bộ
        combined_path = os.path.join(out_dir, "all_features.csv")
        df.to_csv(combined_path, index=False)
        print(f"Đã lưu Feature Matrix ({len(df)} records) vào {out_dir}")
