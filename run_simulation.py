import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from etl import ETLProcessor
from calculator import BankruptcyCalculator
from feature_engine import FeatureEngine
from model_engine import MLEngine
from risk_classifier import RiskClassifier
from scenario_simulator import generate_2026_status_quo

def main():
    ticker = 'NVL'
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "data", "companies")
    
    # 1. Load Data
    etl = ETLProcessor(data_dir)
    etl.load_all()
    
    annual = etl.get_annual_data(ticker)
    quarterly = etl.get_ttm_data(ticker)
    
    # 2. Simulate 2026
    sim_annual, sim_quarterly, cfo_2026 = generate_2026_status_quo(ticker, annual, quarterly)
    
    # 3. Calculate metrics
    calc = BankruptcyCalculator(sim_annual, ticker, industry='REAL_ESTATE')
    results = calc.run_all(quarterly_data=sim_quarterly)
    
    fe = FeatureEngine(industry='REAL_ESTATE')
    features = fe.transform(sim_annual, results, ticker, normalize=False)
    
    ml = MLEngine(model_dir=os.path.join(base_dir, "ket_qua_test", "bds_validation", "models"))
    X_train, y_train = ml.load_polish_data(os.path.join(base_dir, "data", "polish"))
    selected_features = ml.select_features(X_train, y_train, top_k=9)
    ml.train_xgboost(X_train, y_train, features=selected_features)
    
    X_bds = features[selected_features].copy()
    X_bds = X_bds.fillna(X_bds.median())
    
    X_bds_scaled = pd.DataFrame(ml.scaler.transform(X_bds), columns=selected_features)
    features['PD_XGBoost'] = ml.xgb_model.predict_proba(X_bds_scaled)[:, 1] * 100
    
    # Extract comparison
    rc = RiskClassifier(industry='REAL_ESTATE')
    
    metrics_2025 = {}
    metrics_2026 = {}
    
    for _, row in features.tail(2).iterrows():
        year = int(row['Year'])
        rd = row.to_dict()
        
        # Enrich from results
        for mk, cm in [('altman', 'Z_Score'), ('dscr', 'DSCR_Stressed')]:
            if mk in results and not results[mk].empty:
                r_df = results[mk]
                y_df = r_df[r_df['Year'] == year]
                if not y_df.empty and cm in y_df.columns:
                    rd[cm] = y_df[cm].iloc[0]
                    
        if 'bds_metrics' in results and not results['bds_metrics'].empty:
            bds = results['bds_metrics']
            b_y = bds[bds['Year'] == year]
            if not b_y.empty:
                last_q = b_y.iloc[-1]
                for c in ['interest_coverage_cfo', 'runway_interest', 'inventory_to_assets', 'CFO_TTM']:
                    rd[c] = last_q.get(c, np.nan)
        
        cfo_val = rd.get('CFO_TTM', -6000e9)
        rd['_consecutive_neg_cfo'] = 4 if cfo_val < 0 else 0
        cl = rc.classify_single(rd)
        rd['Risk_Level'] = cl['Risk_Level']
        rd['Risk_Emoji'] = cl['Risk_Emoji']
        rd['Risk_VN'] = cl['Risk_VN']
        
        if year == 2025:
            metrics_2025 = rd
        elif year == 2026:
            metrics_2026 = rd
            
    # Print markdown table
    print("\n\n### BẢNG SO SÁNH KỊCH BẢN DUY TRÌ (2025 vs 2026)")
    print(f"| Chỉ tiêu (Đơn vị: VND/Hệ số) | 2025 (Hiện tại) | 2026 (Dự phóng Status Quo) | Biến động |")
    print(f"| :--- | :---: | :---: | :---: |")
    
    def fmt_num(v, f=".2f"):
        if pd.isna(v) or v is None: return "N/A"
        return f"{v:{f}}"
        
    def diff_str(v26, v25):
        if pd.isna(v26) or pd.isna(v25): return "-"
        d = v26 - v25
        return f"{d:+.2f}"
        
    z_25 = metrics_2025.get('Z_Score')
    z_26 = metrics_2026.get('Z_Score')
    
    wc_25 = metrics_2025.get('wc_ta')
    wc_26 = metrics_2026.get('wc_ta')
    
    cfo_25 = cfo_2025 = -6145e9 # hardcode check if needed, but get from metrics
    cfo_25 = metrics_2025.get('CFO_TTM')
    cfo_26 = metrics_2026.get('CFO_TTM')
    cfod_25 = cfo_25/1e9 if pd.notna(cfo_25) else 0
    cfod_26 = cfo_26/1e9 if pd.notna(cfo_26) else 0
    
    pd_25 = metrics_2025.get('PD_XGBoost')
    pd_26 = metrics_2026.get('PD_XGBoost')
    
    inv_25 = metrics_2025.get('inventory_to_assets')
    inv_26 = metrics_2026.get('inventory_to_assets')
    
    print(f"| **Z''-Score (Hiệu chỉnh BĐS)** | {fmt_num(z_25)} | **{fmt_num(z_26)}** | {diff_str(z_26, z_25)} |")
    print(f"| **PD% Xác suất Phá sản (XGBoost)**| {fmt_num(pd_25)}% | **{fmt_num(pd_26)}%** | {diff_str(pd_26, pd_25)}% |")
    print(f"| **Thanh khoản ròng (WC_adj/TA)** | {fmt_num(wc_25, '.3f')} | **{fmt_num(wc_26, '.3f')}** | {diff_str(wc_26, wc_25)} |")
    print(f"| **Dòng tiền CFO TTM (Tỷ VND)** | {fmt_num(cfod_25, '.0f')} | **{fmt_num(cfod_26, '.0f')}** | {(cfod_26-cfod_25):+.0f} |")
    print(f"| **Tỷ lệ Tồn kho / TTS** | {fmt_num(inv_25*100 if inv_25 else np.nan, '.1f')}% | **{fmt_num(inv_26*100 if inv_26 else np.nan, '.1f')}%** | - |")
    print(f"| **Trạng thái rủi ro** | {metrics_2025.get('Risk_Emoji')} {metrics_2025.get('Risk_VN')} | {metrics_2026.get('Risk_Emoji')} {metrics_2026.get('Risk_VN')} | Báo động đỏ |")
    
if __name__ == "__main__":
    main()
