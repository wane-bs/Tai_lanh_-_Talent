"""
ML Engine Module — Random Forest Feature Selection + XGBoost PD + SHAP Explainer.

Pipeline:
1. Tải dữ liệu huấn luyện (Polish Bankruptcy Dataset hoặc labeled data)
2. RF Feature Selection (Gini Impurity ranking → top-K features)
3. XGBoost Binary Logistic → Probability of Default (PD%)
4. SHAP TreeExplainer → Feature contribution per sample
5. Dự báo cho doanh nghiệp Việt Nam (transfer inference)

Input:  Feature Matrix (từ FeatureEngine)
Output: PD%, SHAP values, Feature importance rankings
"""

import pandas as pd
import numpy as np
import os
import joblib
import warnings

from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import (
    classification_report, precision_recall_curve,
    average_precision_score, roc_auc_score, confusion_matrix
)
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings('ignore')


class MLEngine:
    """
    ML Engine cho dự báo xác suất phá sản.

    Hai chế độ:
    - train_mode: Huấn luyện trên Polish Bankruptcy Dataset (có nhãn)
    - predict_mode: Dự báo PD% cho doanh nghiệp VN (transfer learning)
    """

    # Features mapping giữa Polish dataset và features VN
    POLISH_FEATURE_MAP = {
        'Attr1': 'ni_ta',          # net profit / total assets
        'Attr2': 'tl_ta',          # total liabilities / total assets
        'Attr3': 'wc_ta',          # working capital / total assets
        'Attr4': 'ca_cl',          # current assets / short-term liabilities
        'Attr6': 're_ta',          # retained earnings / total assets
        'Attr7': 'ebit_ta',        # EBIT / total assets
        'Attr8': 'bv_eq_tl',       # book value of equity / total liabilities
        'Attr9': 'asset_turnover', # sales / total assets
        'Attr21': 'revenue_growth', # sales (n) / sales (n-1)
    }

    # Features mapping giữa Taiwanese dataset và features VN
    # UCI ID=572 — Taiwan Economic Journal (1999–2009), 6819 samples, 95 features
    TAIWANESE_FEATURE_MAP = {
        ' Net Income to Total Assets': 'ni_ta',                  # [85] NI / TA
        ' Debt ratio %': 'tl_ta',                                # [36] TL / TA
        ' Working Capital to Total Assets': 'wc_ta',             # [53] WC / TA
        ' Current Ratio': 'ca_cl',                               # [32] CA / CL
        ' Retained Earnings to Total Assets': 're_ta',           # [67] RE / TA
        ' ROA(A) before interest and % after tax': 'ebit_ta',    # [1]  EBIT proxy / TA
        ' Equity to Liability': 'bv_eq_tl',                      # [94] Equity / TL
        ' Total Asset Turnover': 'asset_turnover',               # [44] Sales / TA
        ' After-tax Net Profit Growth Rate': 'revenue_growth',   # [25] Growth proxy
        ' Cash Flow to Liability': 'cf_td',                      # [80] CFO / TD ★ bonus
    }

    # Top features cho mô hình phá sản (từ nghiên cứu)
    DEFAULT_FEATURES = [
        'wc_ta', 're_ta', 'ebit_ta', 'bv_eq_tl',
        'cf_td', 'ni_ta', 'ca_cl', 'tl_ta',
        'asset_turnover', 'revenue_growth'
    ]

    # BĐS-specific features (bổ sung bao phủ dòng tiền)
    REAL_ESTATE_FEATURES = [
        'wc_ta', 're_ta', 'ebit_ta', 'bv_eq_tl',
        'cf_td', 'ni_ta', 'ca_cl', 'tl_ta',
        'cfo_to_short_debt', 'interest_coverage_cfo',
    ]

    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.rf_model = None
        self.xgb_model = None
        self.ensemble_model = None
        self.scaler = StandardScaler()
        self.selected_features = []
        self.shap_values = None
        self.training_metrics = {}

    # =================================================================
    # 1. LOAD TRAINING DATA (Polish Bankruptcy Dataset)
    # =================================================================
    def load_polish_data(self, data_dir: str = None) -> tuple:
        """
        Tải Polish Bankruptcy Dataset.
        Ưu tiên đọc từ file ARFF local, fallback sang UCI API.

        Returns:
            (X, y) — Feature matrix và labels
        """
        print("🇵🇱 Đang tải Polish Bankruptcy Dataset...")

        # Ưu tiên 1: Đọc từ ARFF local (tránh timeout mạng)
        if data_dir and os.path.isdir(data_dir):
            arff_files = sorted([
                f for f in os.listdir(data_dir)
                if f.endswith('.arff')
            ])
            if arff_files:
                return self._load_polish_from_arff(data_dir, arff_files)

        # Ưu tiên 2: Tải từ UCI API
        try:
            from ucimlrepo import fetch_ucirepo
            print("  → Tải từ UCI ML Repository (ID=365)...")
            dataset = fetch_ucirepo(id=365)
            X_raw = dataset.data.features
            y = dataset.data.targets.iloc[:, 0]

            # Thực hiện mapping và đổi tên cột
            print(f"  → Ánh xạ đặc trưng ({len(self.POLISH_FEATURE_MAP)} chỉ số)...")
            X = X_raw[list(self.POLISH_FEATURE_MAP.keys())].copy()
            X = X.rename(columns=self.POLISH_FEATURE_MAP)

            print(f"  ✓ Loaded & Renamed: {X.shape[0]} samples, {X.shape[1]} features")
            print(f"  ✓ Class distribution: {dict(y.value_counts())}")
            return X, y
        except Exception as e:
            print(f"  ✗ Không thể tải từ UCI: {e}")
            print("  → Tạo synthetic data cho demo...")
            return self._generate_synthetic_data()

    def _load_polish_from_arff(self, data_dir: str, arff_files: list) -> tuple:
        """Đọc Polish dataset từ các file ARFF local."""
        from scipy.io import arff as arff_io

        all_X, all_y = [], []
        for fname in arff_files:
            fpath = os.path.join(data_dir, fname)
            print(f"  → Đọc {fname}...")
            try:
                data, meta = arff_io.loadarff(fpath)
                df = pd.DataFrame(data)

                # Cột cuối là label ('class')
                label_col = df.columns[-1]
                y_part = df[label_col].astype(int)
                X_part = df.drop(columns=[label_col])

                # Rename columns: Attr1 → Attr1 (giữ nguyên tên gốc)
                # Các cột trong ARFF đã là Attr1, Attr2, ...
                all_X.append(X_part)
                all_y.append(y_part)
            except Exception as e:
                print(f"    ⚠ Lỗi đọc {fname}: {e}")
                continue

        if not all_X:
            print("  ✗ Không đọc được file ARFF nào.")
            return self._generate_synthetic_data()

        X_raw = pd.concat(all_X, ignore_index=True)
        y = pd.concat(all_y, ignore_index=True)

        # Mapping features
        available_cols = [c for c in self.POLISH_FEATURE_MAP.keys()
                         if c in X_raw.columns]
        if not available_cols:
            print(f"  ✗ Không tìm thấy cột Attr trong ARFF. Cột có: {list(X_raw.columns[:5])}...")
            return self._generate_synthetic_data()

        X = X_raw[available_cols].copy()
        X = X.rename(columns={k: v for k, v in self.POLISH_FEATURE_MAP.items()
                              if k in available_cols})

        print(f"  ✓ Loaded from ARFF: {X.shape[0]} samples, {X.shape[1]} features")
        print(f"  ✓ Class distribution: {dict(y.value_counts())}")
        return X, y

    # =================================================================
    # 1b. LOAD TRAINING DATA (Taiwanese Bankruptcy Dataset)
    # =================================================================
    def load_taiwanese_data(self, data_dir: str = None) -> tuple:
        """
        Tải Taiwanese Bankruptcy Prediction Dataset.
        Ưu tiên đọc từ file CSV local, fallback sang UCI API.

        UCI ID=572 — Taiwan Economic Journal (1999–2009)
        6,819 samples, 95 features, ~3.2% bankrupt

        Returns:
            (X, y) — Feature matrix (mapped to system features) và labels
        """
        print("\n🇹🇼 Đang tải Taiwanese Bankruptcy Dataset...")

        X_raw, y = None, None

        # Ưu tiên 1: Đọc từ CSV local (tránh timeout mạng)
        if data_dir:
            csv_features = os.path.join(data_dir, 'features.csv')
            csv_targets = os.path.join(data_dir, 'targets.csv')
            csv_combined = os.path.join(data_dir, 'taiwanese_bankruptcy.csv')

            if os.path.exists(csv_combined):
                print(f"  → Đọc từ file local: {csv_combined}")
                df = pd.read_csv(csv_combined)
                y = df['Bankrupt?']
                X_raw = df.drop(columns=['Bankrupt?'])
            elif os.path.exists(csv_features) and os.path.exists(csv_targets):
                print(f"  → Đọc từ file local: {csv_features}")
                X_raw = pd.read_csv(csv_features)
                y = pd.read_csv(csv_targets).iloc[:, 0]

        # Ưu tiên 2: Tải từ UCI API
        if X_raw is None:
            try:
                from ucimlrepo import fetch_ucirepo
                print("  → Tải từ UCI ML Repository (ID=572)...")
                dataset = fetch_ucirepo(id=572)
                X_raw = dataset.data.features
                y = dataset.data.targets.iloc[:, 0]
            except Exception as e:
                print(f"  ✗ Không thể tải Taiwanese dataset: {e}")
                return pd.DataFrame(), pd.Series(dtype=int)

        # Mapping features
        available_tw_cols = [c for c in self.TAIWANESE_FEATURE_MAP.keys()
                            if c in X_raw.columns]
        if not available_tw_cols:
            print(f"  ✗ Không tìm thấy cột tương thích trong dataset.")
            print(f"    Cột dataset: {list(X_raw.columns[:5])}...")
            return pd.DataFrame(), pd.Series(dtype=int)

        print(f"  → Ánh xạ đặc trưng ({len(available_tw_cols)}/{len(self.TAIWANESE_FEATURE_MAP)} chỉ số)...")
        X = X_raw[available_tw_cols].copy()
        rename_map = {k: v for k, v in self.TAIWANESE_FEATURE_MAP.items()
                      if k in available_tw_cols}
        X = X.rename(columns=rename_map)

        print(f"  ✓ Loaded & Renamed: {X.shape[0]} samples, {X.shape[1]} features")
        print(f"  ✓ Class distribution: {dict(y.value_counts())}")
        print(f"  ✓ Features: {list(X.columns)}")
        return X, y

    # =================================================================
    # 1c. LOAD COMBINED DATA (Polish + Taiwanese)
    # =================================================================
    def load_combined_data(self, polish_dir: str = None,
                           taiwanese_dir: str = None) -> tuple:
        """
        Gộp cả Polish và Taiwanese datasets để huấn luyện ensemble.
        Chỉ giữ các features chung giữa 2 datasets.

        Returns:
            (X, y) — Combined feature matrix và labels
        """
        print("\n🌏 Đang gộp dữ liệu Polish + Taiwanese...")

        X_pl, y_pl = self.load_polish_data(polish_dir)
        X_tw, y_tw = self.load_taiwanese_data(taiwanese_dir)

        datasets = []
        if not X_pl.empty if isinstance(X_pl, pd.DataFrame) else len(X_pl) > 0:
            datasets.append((X_pl, y_pl, 'Polish'))
        if not X_tw.empty if isinstance(X_tw, pd.DataFrame) else len(X_tw) > 0:
            datasets.append((X_tw, y_tw, 'Taiwanese'))

        if not datasets:
            print("  ✗ Không có dataset nào khả dụng.")
            return self._generate_synthetic_data()

        if len(datasets) == 1:
            name = datasets[0][2]
            print(f"  ⚠ Chỉ có {name} dataset, dùng đơn lẻ.")
            return datasets[0][0], datasets[0][1]

        # Tìm features chung
        common_features = list(
            set(datasets[0][0].columns) & set(datasets[1][0].columns)
        )
        common_features.sort()

        print(f"  → Features chung: {common_features}")

        # Gộp với cùng cột
        X_combined = pd.concat(
            [d[0][common_features] for d in datasets],
            ignore_index=True
        )
        y_combined = pd.concat(
            [d[1].reset_index(drop=True) for d in datasets],
            ignore_index=True
        )

        # Shuffle
        idx = np.random.permutation(len(X_combined))
        X_combined = X_combined.iloc[idx].reset_index(drop=True)
        y_combined = y_combined.iloc[idx].reset_index(drop=True)

        print(f"  ✓ Combined: {X_combined.shape[0]} samples, {X_combined.shape[1]} features")
        print(f"  ✓ Class distribution: {dict(y_combined.value_counts())}")
        for name, x, _ in [(d[2], d[0], d[1]) for d in datasets]:
            print(f"    • {name}: {len(x)} samples")

        return X_combined, y_combined

    def _generate_synthetic_data(self, n_samples: int = 2000) -> tuple:
        """Tạo dữ liệu mẫu cho demo khi không có dữ liệu thực."""
        np.random.seed(42)
        n_bankrupt = int(n_samples * 0.05)  # 5% bankrupt
        n_healthy = n_samples - n_bankrupt

        # Healthy companies
        h = pd.DataFrame({
            'wc_ta': np.random.normal(0.3, 0.15, n_healthy),
            're_ta': np.random.normal(0.2, 0.1, n_healthy),
            'ebit_ta': np.random.normal(0.1, 0.05, n_healthy),
            'bv_eq_tl': np.random.normal(1.5, 0.5, n_healthy),
            'cf_td': np.random.normal(0.15, 0.08, n_healthy),
            'ni_ta': np.random.normal(0.08, 0.04, n_healthy),
            'ca_cl': np.random.normal(2.0, 0.6, n_healthy),
            'tl_ta': np.random.normal(0.4, 0.15, n_healthy),
            'asset_turnover': np.random.normal(0.8, 0.3, n_healthy),
            'revenue_growth': np.random.normal(0.05, 0.1, n_healthy),
        })

        # Bankrupt companies (distressed ratios)
        b = pd.DataFrame({
            'wc_ta': np.random.normal(-0.2, 0.2, n_bankrupt),
            're_ta': np.random.normal(-0.3, 0.15, n_bankrupt),
            'ebit_ta': np.random.normal(-0.1, 0.08, n_bankrupt),
            'bv_eq_tl': np.random.normal(0.2, 0.3, n_bankrupt),
            'cf_td': np.random.normal(-0.05, 0.1, n_bankrupt),
            'ni_ta': np.random.normal(-0.15, 0.08, n_bankrupt),
            'ca_cl': np.random.normal(0.6, 0.3, n_bankrupt),
            'tl_ta': np.random.normal(0.85, 0.15, n_bankrupt),
            'asset_turnover': np.random.normal(0.3, 0.2, n_bankrupt),
            'revenue_growth': np.random.normal(-0.2, 0.15, n_bankrupt),
        })

        X = pd.concat([h, b], ignore_index=True)
        y = pd.Series([0] * n_healthy + [1] * n_bankrupt)

        # Shuffle
        idx = np.random.permutation(len(X))
        X = X.iloc[idx].reset_index(drop=True)
        y = y.iloc[idx].reset_index(drop=True)

        print(f"  ✓ Synthetic data: {len(X)} samples")
        return X, y

    # =================================================================
    # 2. RANDOM FOREST — FEATURE SELECTION
    # =================================================================
    def select_features(self, X: pd.DataFrame, y: pd.Series,
                        top_k: int = 10) -> list:
        """
        Sử dụng Random Forest Gini Impurity để xếp hạng feature importance.

        G = 1 - Σ(pi²)  (Gini Impurity)

        Returns:
            List of top-K feature names
        """
        print("\n📊 Stage 4a: Random Forest Feature Selection")
        print("=" * 50)

        self.rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )

        # Xử lý NaN/Inf
        X_clean = X.copy()
        X_clean = X_clean.replace([np.inf, -np.inf], np.nan)
        X_clean = X_clean.fillna(X_clean.median())

        self.rf_model.fit(X_clean, y)

        # Feature importance ranking
        importances = pd.Series(
            self.rf_model.feature_importances_,
            index=X_clean.columns
        ).sort_values(ascending=False)

        print("\nFeature Importance (Gini):")
        for feat, imp in importances.head(top_k).items():
            bar = "█" * int(imp * 50)
            print(f"  {feat:25s} {imp:.4f} {bar}")

        self.selected_features = importances.head(top_k).index.tolist()
        return self.selected_features

    # =================================================================
    # 3. XGBOOST — PD ENGINE
    # =================================================================
    def train_xgboost(self, X: pd.DataFrame, y: pd.Series,
                      features: list = None) -> dict:
        """
        Huấn luyện XGBoost Binary Logistic cho dự báo PD%.

        - objective: binary:logistic
        - scale_pos_weight: tự động tính (xử lý class imbalance)
        - Validation: Time-series expanding window split
        - Metric: PR-AUC
        """
        try:
            import xgboost as xgb
        except ImportError:
            print("  ✗ XGBoost chưa được cài đặt. Chuyển sang Ensemble fallback.")
            return self.train_ensemble_fallback(X, y, features)

        print("\n🚀 Stage 4b: XGBoost PD Engine")
        print("=" * 50)

        if features is None:
            features = self.selected_features if self.selected_features else X.columns.tolist()

        from sklearn.model_selection import train_test_split as _tts

        X_sel = X[features].copy()
        X_sel = X_sel.replace([np.inf, -np.inf], np.nan)
        X_sel = X_sel.fillna(X_sel.median())

        # --- Stratified train/test split TRƯỚC khi scale (tránh data leakage) ---
        try:
            X_train_raw, X_test_raw, y_train, y_test = _tts(
                X_sel, y, test_size=0.2, random_state=42, stratify=y
            )
        except ValueError:
            print("  ⚠ Không đủ positive samples để stratify — dùng random split")
            X_train_raw, X_test_raw, y_train, y_test = _tts(
                X_sel, y, test_size=0.2, random_state=42
            )

        # Fit scaler CHỈ trên train (tránh data leakage từ future data)
        X_train_sc = pd.DataFrame(
            self.scaler.fit_transform(X_train_raw), columns=features,
            index=X_train_raw.index
        )
        X_test_sc = pd.DataFrame(
            self.scaler.transform(X_test_raw), columns=features,
            index=X_test_raw.index
        )

        # Class imbalance
        n_neg = (y_train == 0).sum()
        n_pos = (y_train == 1).sum()
        scale_pos = n_neg / max(n_pos, 1)

        self.xgb_model = xgb.XGBClassifier(
            objective='binary:logistic',
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            scale_pos_weight=scale_pos,
            eval_metric='aucpr',
            use_label_encoder=False,
            random_state=42,
            reg_alpha=1.0,
            reg_lambda=2.0,
            subsample=0.8,
            colsample_bytree=0.8,
        )

        # Time-Series Split CV trên TRAIN — lọc fold không có positive samples
        tscv = TimeSeriesSplit(n_splits=5)
        valid_cv = [
            (tr_idx, val_idx)
            for tr_idx, val_idx in tscv.split(X_train_sc)
            if y_train.iloc[val_idx].sum() >= 1
        ]

        if valid_cv:
            cv_scores = cross_val_score(
                self.xgb_model, X_train_sc, y_train,
                cv=valid_cv, scoring='average_precision'
            )
            print(f"\n  📊 [CV TRAIN] PR-AUC ({len(valid_cv)}-fold TS Split): "
                  f"{cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
        else:
            cv_scores = np.array([np.nan])
            print("  ⚠ Không có fold nào đủ positive samples — CV bỏ qua")

        # Final training trên toàn bộ train set
        self.xgb_model.fit(X_train_sc, y_train)

        # Evaluate trên TEST SET (held-out 20%) — không bị inflate
        y_proba_test = self.xgb_model.predict_proba(X_test_sc)[:, 1]
        y_pred_test = self.xgb_model.predict(X_test_sc)

        has_both_classes = len(y_test.unique()) > 1
        roc = roc_auc_score(y_test, y_proba_test) if has_both_classes else 0.0
        pr_auc = average_precision_score(y_test, y_proba_test) if has_both_classes else 0.0
        report = classification_report(y_test, y_pred_test, output_dict=True,
                                       zero_division=0)

        print(f"  ✅ [TEST SET - Held-out 20%] ROC-AUC: {roc:.4f}")
        print(f"  ✅ [TEST SET - Held-out 20%] PR-AUC:  {pr_auc:.4f}")
        print(f"  Precision (Bankrupt): {float(report.get('1', {}).get('precision', 0)):.4f}")
        print(f"  Recall (Bankrupt):    {float(report.get('1', {}).get('recall', 0)):.4f}")

        self.training_metrics = {
            'pr_auc_cv': float(np.nanmean(cv_scores)),
            'pr_auc_cv_std': float(np.nanstd(cv_scores)),
            'roc_auc': float(roc),
            'pr_auc': float(pr_auc),
            'accuracy': float(report.get('accuracy', 0)),
            'precision_bankrupt': float(report.get('1', {}).get('precision', 0)),
            'recall_bankrupt': float(report.get('1', {}).get('recall', 0)),
        }

        return self.training_metrics

    # =================================================================
    # 4. SHAP EXPLAINER
    # =================================================================
    def explain_shap(self, X: pd.DataFrame,
                     features: list = None) -> pd.DataFrame:
        """
        Sử dụng SHAP TreeExplainer để giải thích dự báo.

        Returns:
            DataFrame chứa SHAP values cho mỗi observation/feature
        """
        try:
            import shap
        except ImportError:
            print("  ✗ SHAP chưa được cài đặt.")
            return pd.DataFrame()

        if self.xgb_model is None:
            print("  ✗ Chưa có model. Hãy train trước.")
            return pd.DataFrame()

        print("\n🔍 Stage 4c: SHAP Explainability")
        print("=" * 50)

        if features is None:
            features = self.selected_features

        X_sel = X[features].copy()
        X_sel = X_sel.replace([np.inf, -np.inf], np.nan)
        X_sel = X_sel.fillna(X_sel.median())
        X_scaled = pd.DataFrame(
            self.scaler.transform(X_sel),
            columns=features
        )

        explainer = shap.TreeExplainer(self.xgb_model)
        shap_values = explainer.shap_values(X_scaled)

        self.shap_values = shap_values

        # Tổng hợp mean |SHAP| per feature
        mean_shap = pd.DataFrame({
            'Feature': features,
            'Mean_SHAP': np.abs(shap_values).mean(axis=0)
        }).sort_values('Mean_SHAP', ascending=False)

        print("\nTop SHAP Feature Contributions:")
        for _, row in mean_shap.head(10).iterrows():
            bar = "█" * int(row['Mean_SHAP'] * 30)
            print(f"  {row['Feature']:25s} {row['Mean_SHAP']:.4f} {bar}")

        # DataFrame SHAP values per sample
        shap_df = pd.DataFrame(shap_values, columns=features)
        
        # Gắn lại metadata (Ticker, Year) nếu có trong X ban đầu
        if 'Ticker' in X.columns and 'Year' in X.columns:
            shap_df.insert(0, 'Ticker', X['Ticker'].values)
            shap_df.insert(1, 'Year', X['Year'].values)
            
        # Thêm Base Value (E[f(x)]) làm tham chiếu cho Waterfall plot
        shap_df['Base_Value'] = float(explainer.expected_value)

        return shap_df

    # =================================================================
    # 5. DỰ BÁO CHO DOANH NGHIỆP VN
    # =================================================================
    def predict(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Dự báo PD% cho doanh nghiệp VN.

        Args:
            features_df: Feature Matrix từ FeatureEngine (có cột Year, Ticker)

        Returns:
            DataFrame với thêm cột PD_XGBoost, PD_RF (%)
        """
        if self.xgb_model is None:
            print("  ✗ Chưa có model. Vui lòng train trước.")
            return features_df

        result = features_df.copy()

        # Lấy features đã chọn khi train — PHẢI khớp với scaler
        feats = self.selected_features if self.selected_features else self.DEFAULT_FEATURES
        available_feats = [f for f in feats if f in result.columns]

        # BĐS: chỉ dùng REAL_ESTATE_FEATURES nếu chúng nằm trong selected_features
        # (tránh lỗi scaler mismatch khi train trên dataset khác)
        if 'cfo_to_short_debt' in result.columns and 'cfo_to_short_debt' in feats:
            bds_feats = [f for f in self.REAL_ESTATE_FEATURES if f in result.columns and f in feats]
            if len(bds_feats) > len(available_feats):
                available_feats = bds_feats

        if not available_feats:
            print("  ✗ Không tìm thấy features phù hợp.")
            print(f"    Selected features: {feats}")
            print(f"    Available in data: {[c for c in result.columns if c not in ['Year', 'Ticker']]}")
            return result

        X = result[available_feats].copy()
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(X.median())

        # Scale
        X_scaled = pd.DataFrame(
            self.scaler.transform(X),
            columns=available_feats
        )

        # XGBoost prediction
        result['PD_XGBoost'] = self.xgb_model.predict_proba(X_scaled)[:, 1] * 100

        # RF prediction (if available)
        if self.rf_model is not None:
            # RF cần toàn bộ features gốc, nên chỉ dự báo nếu phù hợp
            try:
                result['PD_RF'] = self.rf_model.predict_proba(X)[:, 1] * 100
            except Exception:
                result['PD_RF'] = np.nan

        return result

    # =================================================================
    # 6. ENSEMBLE FALLBACK (Logit + MLP + SVM)
    # =================================================================
    def train_ensemble_fallback(self, X: pd.DataFrame, y: pd.Series,
                                features: list = None) -> dict:
        """
        Ensemble VotingClassifier khi XGBoost không khả dụng
        hoặc dữ liệu quá nhỏ.
        """
        print("\n🔄 Stage 4d: Ensemble Fallback (Logit + MLP + SVM)")
        print("=" * 50)

        if features is None:
            features = X.columns.tolist()

        X_sel = X[features].copy()
        X_sel = X_sel.replace([np.inf, -np.inf], np.nan)
        X_sel = X_sel.fillna(X_sel.median())
        X_scaled = pd.DataFrame(
            self.scaler.fit_transform(X_sel),
            columns=features
        )

        self.ensemble_model = VotingClassifier(
            estimators=[
                ('logit', LogisticRegression(
                    max_iter=1000, class_weight='balanced', random_state=42)),
                ('mlp', MLPClassifier(
                    hidden_layer_sizes=(64, 32), max_iter=500, random_state=42)),
                ('svm', SVC(
                    kernel='rbf', probability=True,
                    class_weight='balanced', random_state=42)),
            ],
            voting='soft'
        )

        self.ensemble_model.fit(X_scaled, y)

        y_pred = self.ensemble_model.predict(X_scaled)
        y_proba = self.ensemble_model.predict_proba(X_scaled)[:, 1]

        report = classification_report(y, y_pred, output_dict=True,
                                       zero_division=0)
        roc = roc_auc_score(y, y_proba) if len(y.unique()) > 1 else 0.0

        self.training_metrics = {
            'model_type': 'ensemble_fallback',
            'roc_auc': float(roc),
            'accuracy': float(report.get('accuracy', 0)),
        }

        print(f"  ROC-AUC: {roc:.4f}")
        print(f"  Accuracy: {report.get('accuracy', 0):.4f}")

        return self.training_metrics

    # =================================================================
    # SAVE / LOAD MODEL
    # =================================================================
    def save_model(self, path: str = None):
        """Lưu models đã train."""
        if path is None:
            path = self.model_dir
        os.makedirs(path, exist_ok=True)

        if self.xgb_model:
            joblib.dump(self.xgb_model, os.path.join(path, "xgb_model.joblib"))
        if self.rf_model:
            joblib.dump(self.rf_model, os.path.join(path, "rf_model.joblib"))
        if self.ensemble_model:
            joblib.dump(self.ensemble_model, os.path.join(path, "ensemble_model.joblib"))
        joblib.dump(self.scaler, os.path.join(path, "scaler.joblib"))
        joblib.dump(self.selected_features, os.path.join(path, "selected_features.joblib"))

        print(f"  ✓ Models saved to {path}")

    def load_model(self, path: str = None):
        """Tải models đã train."""
        if path is None:
            path = self.model_dir

        try:
            self.xgb_model = joblib.load(os.path.join(path, "xgb_model.joblib"))
            print("  ✓ XGBoost model loaded")
        except FileNotFoundError:
            pass

        try:
            self.rf_model = joblib.load(os.path.join(path, "rf_model.joblib"))
            print("  ✓ RF model loaded")
        except FileNotFoundError:
            pass

        try:
            self.ensemble_model = joblib.load(os.path.join(path, "ensemble_model.joblib"))
            print("  ✓ Ensemble model loaded")
        except FileNotFoundError:
            pass

        try:
            self.scaler = joblib.load(os.path.join(path, "scaler.joblib"))
            self.selected_features = joblib.load(os.path.join(path, "selected_features.joblib"))
        except FileNotFoundError:
            pass

    # =================================================================
    # FULL TRAINING PIPELINE
    # =================================================================
    def train_pipeline(self, data_dir: str = None,
                       top_k_features: int = 10,
                       dataset: str = 'polish',
                       taiwanese_dir: str = None) -> dict:
        """
        Pipeline đầy đủ: Load Data → RF Selection → XGBoost Train → Save.

        Args:
            data_dir: Thư mục dữ liệu Polish (hoặc chung)
            top_k_features: Số features chọn bởi RF
            dataset: Nguồn dữ liệu huấn luyện:
                - 'polish': Chỉ Polish Bankruptcy Dataset (mặc định)
                - 'taiwanese': Chỉ Taiwanese Bankruptcy Dataset
                - 'combined': Gộp cả Polish + Taiwanese (ensemble)
            taiwanese_dir: Thư mục dữ liệu Taiwanese (nếu dùng)

        Returns:
            Training metrics dict
        """
        print("\n" + "=" * 60)
        print("🏭 ML ENGINE — TRAINING PIPELINE")
        print(f"   Dataset: {dataset.upper()}")
        print("=" * 60)

        # 1. Load data theo dataset được chọn
        if dataset == 'taiwanese':
            X, y = self.load_taiwanese_data(taiwanese_dir or data_dir)
        elif dataset == 'combined':
            X, y = self.load_combined_data(
                polish_dir=data_dir,
                taiwanese_dir=taiwanese_dir
            )
        else:  # 'polish' (mặc định)
            X, y = self.load_polish_data(data_dir)

        if isinstance(X, pd.DataFrame) and X.empty:
            print("  ✗ Không tải được dữ liệu. Dùng synthetic data.")
            X, y = self._generate_synthetic_data()

        # 2. Feature selection
        selected = self.select_features(X, y, top_k=top_k_features)

        # 3. Train XGBoost
        metrics = self.train_xgboost(X, y, features=selected)

        # Ghi nhận dataset đã dùng
        metrics['training_dataset'] = dataset
        metrics['training_samples'] = len(X)

        # 4. Save
        self.save_model()

        print("\n" + "=" * 60)
        print("✅ Training pipeline hoàn thành!")
        print("=" * 60)

        return metrics
