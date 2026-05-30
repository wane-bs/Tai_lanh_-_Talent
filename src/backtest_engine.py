import numpy as np
import pandas as pd
import json
import os
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from cash_flow_scorer import BCTCCashFlowScorer
from risk_classifier import RiskClassifier

class CreditBacktester:
    """
    Backtesting & Calibration Engine for Cash Flow Scorecard.
    """
    def __init__(self, etl, calc_results, features_df):
        self.etl = etl
        self.calc_results = calc_results
        self.features_df = features_df
        self.scorer = BCTCCashFlowScorer()
        self.risk_classifier = RiskClassifier(industry='REAL_ESTATE')
        
        # Bins matching cash_flow_scorer.py
        self.bins_config = {
            'cash_to_revenue': [0.95, 0.80, 0.70],
            'dscr': [2.0, 1.5, 1.25, 1.0, 0.75],
            'cash_buffer_days': [90, 45, 15],
            'revenue_volatility': [0.15, 0.30, 0.45], # Note: inverse logic (< is better)
            'equity_to_debt': [1.5, 1.0, 0.5, 0.3],
            'cfo_growth_yoy': [0.15, 0.0, -0.15]
        }
        
    def _get_bin_index(self, feature, value):
        if pd.isna(value):
            return -1
            
        bins = self.bins_config[feature]
        if feature == 'revenue_volatility':
            for i, b in enumerate(bins):
                if value < b:
                    return i
            return len(bins)
        else:
            for i, b in enumerate(bins):
                if value >= b:
                    return i
            return len(bins)
            
    def prepare_dataset(self):
        """Build historical dataset with raw metrics and default labels."""
        dataset = []
        for ticker in self.etl.companies.keys():
            t_feat = self.features_df[self.features_df['Ticker'] == ticker].copy()
            t_calc = self.calc_results.get(ticker, {})
            
            for _, row in t_feat.iterrows():
                year = int(row['Year'])
                
                # Fetch raw cash flow metrics for the year
                metrics = self._calculate_metrics_for_year(ticker, year)
                if not metrics or pd.isna(metrics.get('dscr')):
                    continue
                    
                # Define Default Label (1: Bad/Default, 0: Good/Non-Default)
                is_default = self._label_default(row, t_calc, year)
                
                record = {
                    'Ticker': ticker,
                    'Year': year,
                    'Default': 1 if is_default else 0
                }
                
                for k in self.bins_config.keys():
                    record[k] = metrics.get(k, np.nan)
                    record[f'{k}_bin'] = self._get_bin_index(k, metrics.get(k, np.nan))
                    
                dataset.append(record)
                
        return pd.DataFrame(dataset)
        
    def _calculate_metrics_for_year(self, ticker, target_year):
        """Simulate metrics calculation for a historical year."""
        annual = self.etl.get_annual_data(ticker)
        # Filter to simulated time point
        annual_cut = {k: v[v['Year'] <= target_year] for k, v in annual.items()}
        
        quarters = self.etl.get_ttm_data(ticker)
        quarters_cut = {}
        for k, v in quarters.items():
            if 'Year' in v.columns:
                quarters_cut[k] = v[v['Year'] <= target_year]
                
        # Patch etl temporarily for the scorer
        class MockETL:
            def get_annual_data(self, t): return annual_cut
            def get_ttm_data(self, t): return quarters_cut
            
        return self.scorer.calculate_metrics(ticker, MockETL())

    def _label_default(self, row, t_calc, year):
        """
        Label Default dựa HOÀN TOÀN trên financial statement signals.
        KHÔNG dùng PD_XGBoost để tránh circular labeling.

        Dấu hiệu Default (Bad):
          Rule 1: runway_interest < 1 quý → tiền mặt không đủ trả lãi 1 quý
          Rule 2: interest_coverage_cfo < 0.5 VÀ Z-Score < 1.1
                  → CFO suy kiệt + vùng nguy hiểm Altman
          Rule 3: Ohlson PD > 50% VÀ Z-Score < 1.1
                  → 2 mô hình cổ điển đồng thuận phá sản

        Lưu ý (Q1-A): Ngưỡng Z-Score < 1.1 và Ohlson > 50% giữ nguyên theo giá trị
        Altman/Ohlson gốc. Ngưỡng này đị nh theo thị trường Mỹ nhưng được giữ
        nguyên để nhất quán với bộ ngưỡng đang dùng trong risk_classifier.py.
        """
        # 1. Altman Z-Score
        z_score = np.nan
        if 'altman' in t_calc and not t_calc['altman'].empty:
            match = t_calc['altman'][t_calc['altman']['Year'] == year]
            if not match.empty:
                z_score = float(match['Z_Score'].iloc[0])

        # 2. Ohlson PD (xác suất phá sản, 0-100%)
        ohlson_pd = np.nan
        if 'ohlson' in t_calc and not t_calc['ohlson'].empty:
            match = t_calc['ohlson'][t_calc['ohlson']['Year'] == year]
            if not match.empty:
                ohlson_pd = float(match['PD_Ohlson'].iloc[0]) / 100  # % → ratio

        # 3. BDS metrics
        bds = t_calc.get('bds_metrics', pd.DataFrame())
        int_cov, runway = np.nan, np.nan
        if isinstance(bds, pd.DataFrame) and not bds.empty and 'Year' in bds.columns:
            match = bds[bds['Year'] == year]
            if not match.empty:
                last_q = match.iloc[-1]
                int_cov = float(last_q.get('interest_coverage_cfo', np.nan))
                runway = float(last_q.get('runway_interest', np.nan))

        # === Hard Rules (không dùng PD_XGBoost) ===
        # Rule 1: Tiền mặt < 1 quý lãi vay → kỹ thuật mất khả năng thanh toán
        if not np.isnan(runway) and runway < 1:
            return True

        # Rule 2: CFO không đủ trả nửa lãi vay VÀ Altman vùng nguy hiểm
        if (not np.isnan(int_cov) and int_cov < 0.5 and
                not np.isnan(z_score) and z_score < 1.1):
            return True

        # Rule 3: Ohlson và Altman đồng thuận phá sản
        if (not np.isnan(ohlson_pd) and ohlson_pd > 0.5 and
                not np.isnan(z_score) and z_score < 1.1):
            return True

        return False
        
    def calculate_woe(self, df):
        """Calculate WOE với Bayesian smoothing ổn định khi n_bad nhỏ."""
        woe_dict = {}
        total_good = len(df[df['Default'] == 0])
        total_bad = len(df[df['Default'] == 1])

        MIN_BIN_SIZE = 3  # Số quan sát tối thiểu mỗi bin để WOE ổn định
        # Smoothing tỷ lệ với mức imbalance: bad rate thấp → smooth nhiều hơn
        imbalance_ratio = total_good / max(total_bad, 1)
        smooth = max(0.5, imbalance_ratio * 0.01)

        for feature in self.bins_config.keys():
            woe_dict[feature] = {}
            bin_col = f'{feature}_bin'

            for b in df[bin_col].unique():
                b_df = df[df[bin_col] == b]
                good = len(b_df[b_df['Default'] == 0])
                bad = len(b_df[b_df['Default'] == 1])

                if len(b_df) < MIN_BIN_SIZE:
                    print(f"  ⚠ WOE [{feature} bin={b}]: {len(b_df)} obs < {MIN_BIN_SIZE} — WOE có thể không ổn định")

                # Bayesian smoothing: tỷ lệ với tổng good/bad
                pct_good = (good + smooth) / (total_good + smooth * 2)
                pct_bad = (bad + smooth) / (total_bad + smooth * 2)

                woe = np.log(pct_good / pct_bad) if pct_bad > 0 else 0.0
                woe_dict[feature][str(b)] = round(woe, 4)

        return woe_dict
        
    def calibrate_weights(self, df, woe_dict):
        """Fit Logistic Regression trên WOE variables với stratified split + threshold tuning."""
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import precision_recall_curve

        X_woe = pd.DataFrame()
        for feature in self.bins_config.keys():
            X_woe[f'{feature}_woe'] = df[f'{feature}_bin'].astype(str).map(woe_dict[feature])

        y = df['Default']

        # --- Stratified train-test split (20% test) ---
        try:
            X_tr, X_te, y_tr, y_te = train_test_split(
                X_woe, y, test_size=0.2, random_state=42, stratify=y
            )
        except ValueError:
            # Quá ít bad samples để stratify — dùng random split
            print("  ⚠ Không đủ bad samples để stratify split — dùng random split")
            X_tr, X_te, y_tr, y_te = train_test_split(
                X_woe, y, test_size=0.2, random_state=42
            )

        # --- Fit model trên train set để tìm optimal threshold ---
        model_tune = LogisticRegression(class_weight='balanced', max_iter=1000)
        model_tune.fit(X_tr, y_tr)

        # Threshold tuning: tìm ngưỡng tối ưu theo F1 trên PR curve
        optimal_threshold = 0.5  # default
        if y_te.sum() > 0 and (1 - y_te).sum() > 0:
            y_prob_te = model_tune.predict_proba(X_te)[:, 1]
            prec, rec, thr = precision_recall_curve(y_te, y_prob_te)
            f1 = 2 * prec * rec / (prec + rec + 1e-9)
            if len(thr) > 0:
                optimal_threshold = float(thr[np.argmax(f1[:-1])])
        print(f"  → Optimal classification threshold: {optimal_threshold:.3f} (mặc định 0.5)")

        # --- Final model trên toàn bộ data (dùng để tính Points) ---
        model = LogisticRegression(class_weight='balanced', max_iter=1000)
        model.fit(X_woe, y)
        model.optimal_threshold_ = optimal_threshold  # lưu để dùng sau

        # Calculate Points
        # Factor = PDO / ln(2). PDO = 50 => Factor = 72.13
        # Offset = TargetScore - Factor * ln(TargetOdds). TargetScore = 600, Odds = 50 => Offset = 317.9
        FACTOR = 50 / np.log(2)
        OFFSET = 600 - FACTOR * np.log(50)
        
        n_features = len(self.bins_config)
        beta_0 = model.intercept_[0]
        betas = model.coef_[0]
        
        optimized_config = {
            'base_score': 0, # Since we distribute offset to features
            'features': {}
        }
        
        for idx, feature in enumerate(self.bins_config.keys()):
            beta_i = betas[idx]
            feature_cfg = {
                'bins': self.bins_config[feature],
                'points': {}
            }
            
            for b_str, woe_val in woe_dict[feature].items():
                point = -(woe_val * beta_i + beta_0/n_features) * FACTOR + OFFSET/n_features
                feature_cfg['points'][b_str] = round(point)
                
            optimized_config['features'][feature] = feature_cfg
            
        # Export
        out_path = os.path.join(os.path.dirname(__file__), "..", "optimized_scorecard_config.json")
        with open(out_path, 'w') as f:
            json.dump(optimized_config, f, indent=4)
            
        return optimized_config, X_woe, y, model
        
    def calculate_metrics(self, y_true, y_pred_prob, scores):
        """Calculate Gini, KS."""
        auc = roc_auc_score(y_true, y_pred_prob)
        gini = 2 * auc - 1
        
        # KS Statistic
        df = pd.DataFrame({'score': scores, 'target': y_true})
        df = df.sort_values('score')
        df['cum_good'] = (1 - df['target']).cumsum() / (1 - df['target']).sum()
        df['cum_bad'] = df['target'].cumsum() / df['target'].sum()
        ks = np.max(np.abs(df['cum_good'] - df['cum_bad']))
        
        return auc, gini, ks

    def calculate_psi(self, expected_scores, actual_scores, bins=10):
        """Calculate PSI between two distributions of scores."""
        exp_counts, bin_edges = np.histogram(expected_scores, bins=bins)
        act_counts, _ = np.histogram(actual_scores, bins=bin_edges)
        
        exp_pct = exp_counts / sum(exp_counts)
        act_pct = act_counts / sum(act_counts)
        
        # Prevent division by zero
        exp_pct = np.where(exp_pct == 0, 0.0001, exp_pct)
        act_pct = np.where(act_pct == 0, 0.0001, act_pct)
        
        psi = np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct))
        return psi
