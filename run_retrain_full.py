"""
Script Huấn luyện lại Mô hình + Chạy lại Backtest + Kiểm tra Hạn mức Tín dụng
trên toàn bộ 9 doanh nghiệp (bao gồm ANV mới bổ sung).

Pipeline:
  1. Nạp dữ liệu 9 DN BĐS từ data/companies/ (bao gồm ANV)
  2. Huấn luyện lại XGBoost trên bộ dữ liệu kết hợp Polish + Taiwanese
  3. Tính toán Feature Matrix cho 9 DN
  4. Dự báo PD% mới cho toàn bộ portfolio
  5. Chạy lại Cash Flow Scorecard cho từng DN
  6. Chạy lại Backtest & Calibration trên bộ dữ liệu mới
  7. In bảng tổng hợp Hạn mức Tín dụng - tìm DN đủ điều kiện cấp hạn mức
"""

import sys
import os
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from etl import ETLProcessor
from calculator import BankruptcyCalculator
from feature_engine import FeatureEngine
from model_engine import MLEngine
from risk_classifier import RiskClassifier
from cash_flow_scorer import BCTCCashFlowScorer
from credit_model import CreditUnderwriter
from backtest_engine import CreditBacktester

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data", "companies")
POLISH_DIR = os.path.join(BASE_DIR, "data", "polish")
TAIWANESE_DIR = os.path.join(BASE_DIR, "data", "taiwanese")
OUTPUT_DIR = os.path.join(BASE_DIR, "ket_qua_test", "bds_validation")
MODEL_DIR = os.path.join(OUTPUT_DIR, "models")
INDUSTRY = "REAL_ESTATE"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def separator(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def main():
    # =================================================================
    # STAGE 1: ETL — Nạp dữ liệu 9 DN
    # =================================================================
    separator("STAGE 1: ETL — Nạp dữ liệu DN (bao gồm ANV mới)")
    
    etl = ETLProcessor(DATA_DIR)
    companies = etl.load_all()
    
    print(f"\n📊 Tổng số doanh nghiệp: {len(companies)}")
    for ticker in sorted(companies.keys()):
        sheets = companies[ticker]
        total_q = sum(len(df) for df in sheets.values())
        print(f"  {'★ ' if ticker == 'ANV' else '  '}{ticker}: {len(sheets)} sheets, {total_q} records")

    # =================================================================
    # STAGE 2: Calculator — Tính toán các mô hình kinh điển
    # =================================================================
    separator("STAGE 2: Calculator — Tính toán mô hình cổ điển cho 9 DN")
    
    all_calc_results = {}
    for ticker in sorted(companies.keys()):
        annual = etl.get_annual_data(ticker)
        quarterly = etl.get_ttm_data(ticker)
        calc = BankruptcyCalculator(annual, ticker, industry=INDUSTRY)
        results = calc.run_all(quarterly_data=quarterly)
        all_calc_results[ticker] = results
        
        models_ok = [k for k, v in results.items() if isinstance(v, pd.DataFrame) and not v.empty]
        print(f"  [{ticker}] ✓ Mô hình tính toán thành công: {len(models_ok)}")

    # =================================================================
    # STAGE 3: Feature Engine — Xây dựng Feature Matrix
    # =================================================================
    separator("STAGE 3: Feature Engine — Xây dựng Feature Matrix")
    
    fe = FeatureEngine(industry=INDUSTRY)
    all_features = []
    
    for ticker in sorted(companies.keys()):
        annual = etl.get_annual_data(ticker)
        features = fe.transform(annual, all_calc_results[ticker], ticker, normalize=False)
        if not features.empty:
            all_features.append(features)
            print(f"  [{ticker}] Features: {features.shape[1]-2} chỉ số x {len(features)} năm")
    
    feature_matrix = pd.concat(all_features, ignore_index=True) if all_features else pd.DataFrame()
    
    # Clean inf
    for c in feature_matrix.select_dtypes(include=[np.number]).columns:
        feature_matrix[c] = feature_matrix[c].replace([np.inf, -np.inf], np.nan)
    
    print(f"\n📊 Feature Matrix tổng hợp: {feature_matrix.shape[0]} obs x {feature_matrix.shape[1]} cols")
    feature_matrix.to_csv(os.path.join(OUTPUT_DIR, "feature_matrix_bds.csv"), index=False)
    
    # =================================================================
    # STAGE 4: ML Engine — Huấn luyện lại trên Polish + Taiwanese
    # =================================================================
    separator("STAGE 4: ML Engine — Huấn luyện lại XGBoost trên COMBINED (Polish + Taiwanese)")
    
    ml = MLEngine(model_dir=MODEL_DIR)
    
    # Huấn luyện trên bộ dữ liệu kết hợp
    training_metrics = ml.train_pipeline(
        data_dir=POLISH_DIR,
        taiwanese_dir=TAIWANESE_DIR,
        dataset='combined',
        top_k_features=9
    )
    
    print(f"\n📊 Kết quả huấn luyện:")
    print(f"  Training dataset: {training_metrics.get('training_dataset', 'N/A').upper()}")
    print(f"  Training samples: {training_metrics.get('training_samples', 0):,}")
    print(f"  ROC-AUC: {training_metrics.get('roc_auc', 0):.4f}")
    print(f"  PR-AUC:  {training_metrics.get('pr_auc', 0):.4f}")

    # =================================================================
    # STAGE 5: Dự báo PD% mới cho 9 DN VN
    # =================================================================
    separator("STAGE 5: Dự báo PD% mới cho toàn bộ Portfolio")
    
    selected_features = ml.selected_features
    predict_feats = [f for f in selected_features if f in feature_matrix.columns]
    missing_feats = [f for f in selected_features if f not in feature_matrix.columns]
    if missing_feats:
        print(f"  ⚠ Features thiếu (fill 0): {missing_feats}")
        for mf in missing_feats:
            feature_matrix[mf] = 0.0
    
    X_bds = feature_matrix[selected_features].copy()
    X_bds = X_bds.replace([np.inf, -np.inf], np.nan)
    X_bds = X_bds.fillna(X_bds.median())
    
    X_bds_scaled = pd.DataFrame(ml.scaler.transform(X_bds), columns=selected_features)
    feature_matrix['PD_XGBoost'] = ml.xgb_model.predict_proba(X_bds_scaled)[:, 1] * 100
    
    # Per-company latest PD
    print(f"\n📊 PD% mới nhất theo DN (Năm gần nhất):")
    for ticker in sorted(companies.keys()):
        t_data = feature_matrix[feature_matrix['Ticker'] == ticker]
        if not t_data.empty:
            latest = t_data.iloc[-1]
            pd_val = latest['PD_XGBoost']
            year = int(latest['Year'])
            flag = " ★ MỚI" if ticker == 'ANV' else ""
            status = "🟢 Thấp" if pd_val < 20 else ("🟡 TB" if pd_val < 40 else ("🟠 Cao" if pd_val < 70 else "🔴 Rất cao"))
            print(f"  {ticker}: PD = {pd_val:6.2f}% (Năm {year}) {status}{flag}")
    
    # =================================================================
    # STAGE 6: Cash Flow Scorecard cho từng DN
    # =================================================================
    separator("STAGE 6: Cash Flow Scorecard — Chấm điểm Tín dụng Dòng tiền")
    
    # Xóa config cũ để dùng Expert scorer trước, rồi calibrate lại sau
    config_path = os.path.join(BASE_DIR, "optimized_scorecard_config.json")
    if os.path.exists(config_path):
        os.remove(config_path)
    
    scorer = BCTCCashFlowScorer()
    scorecard_results = {}
    
    print(f"\n  {'Ticker':>8} | {'Score':>6} | {'Grade':>10} | {'Quyết định':40s}")
    print(f"  {'─'*8}─┼─{'─'*6}─┼─{'─'*10}─┼─{'─'*40}")
    
    for ticker in sorted(companies.keys()):
        metrics = scorer.calculate_metrics(ticker, etl)
        score, details = scorer.compute_score(metrics)
        grade, decision, color = scorer.get_decision(score)
        scorecard_results[ticker] = {
            'score': score, 'grade': grade, 'decision': decision,
            'metrics': metrics, 'details': details
        }
        flag = " ★" if ticker == 'ANV' else ""
        print(f"  {ticker:>8} | {score:>6} | {grade:>10} | {decision[:40]}{flag}")

    # =================================================================
    # STAGE 7: Định mức Tín dụng — Tìm DN đủ điều kiện cấp hạn mức
    # =================================================================
    separator("STAGE 7: Định mức Tín dụng — Tìm DN có khả năng cấp Hạn mức")
    
    rc = RiskClassifier(industry=INDUSTRY)
    credit_results = []
    
    for ticker in sorted(companies.keys()):
        t_data = feature_matrix[feature_matrix['Ticker'] == ticker]
        if t_data.empty:
            continue
        
        latest = t_data.iloc[-1].to_dict()
        
        # Enrich from calc results
        t_calc = all_calc_results.get(ticker, {})
        year = int(latest['Year'])
        
        for model_key, col_map in [
            ('altman', {'Z_Score': 'Z_Score'}),
            ('ohlson', {'PD_Ohlson': 'PD_Ohlson'}),
            ('dscr', {'DSCR_Stressed': 'DSCR_Stressed'}),
        ]:
            if model_key in t_calc and not t_calc[model_key].empty:
                src = t_calc[model_key]
                match = src[src['Year'] == year]
                if not match.empty:
                    for src_col, dst_col in col_map.items():
                        if src_col in match.columns:
                            val = float(match[src_col].iloc[0])
                            if np.isfinite(val):
                                latest[dst_col] = val
        
        # BDS metrics
        if 'bds_metrics' in t_calc and not t_calc[t_calc.__class__.__name__ if False else 'bds_metrics'].empty:
            bds = t_calc['bds_metrics']
            bds_yr = bds[bds['Year'] == year] if 'Year' in bds.columns else pd.DataFrame()
            if not bds_yr.empty:
                last_q = bds_yr.iloc[-1]
                for col in ['CFO_TTM', 'interest_coverage_cfo', 'runway_interest', 'inventory_to_assets']:
                    val = float(last_q.get(col, np.nan))
                    if np.isfinite(val):
                        latest[col] = val
        
        # Risk classification
        classification = rc.classify_single(latest)
        risk_level = classification['Risk_Level']
        
        # Credit underwriting
        sc = scorecard_results.get(ticker, {})
        cf_score = sc.get('score', 0)
        cf_grade = sc.get('grade', 'N/A')
        
        # Try credit sizing
        try:
            cw = CreditUnderwriter()
            annual = etl.get_annual_data(ticker)
            
            # Extract required parameters from BCTC
            scorer_inst = BCTCCashFlowScorer()
            raw_metrics = scorer_inst.calculate_metrics(ticker, etl)
            raw_vals = raw_metrics.get('raw_values', {})
            
            cfo_ttm = raw_vals.get('cfo_ttm', 0.0)
            equity_val = raw_vals.get('equity', 0.0)
            total_debt_val = raw_vals.get('total_debt', 0.0)
            
            icr_val = latest.get('interest_coverage_cfo', np.nan)
            inv_ta_val = latest.get('inventory_to_assets', np.nan)
            eq_debt_val = raw_metrics.get('equity_to_debt', np.nan)
            wc_ta_val = latest.get('wc_ta', np.nan)
            
            res = cw.calculate_capacity(
                cfo_ttm=cfo_ttm,
                icr=icr_val,
                inventory_ta=inv_ta_val,
                equity_debt=eq_debt_val,
                wc_ta=wc_ta_val,
                equity=equity_val,
                total_debt=total_debt_val,
                rate=0.10,
                tenor=5,
                pd_xgboost=latest.get('PD_XGBoost', 100),
                risk_level=risk_level,
                composite_score=classification.get('Composite_Score', 0.0)
            )
            l_final = res.get('L_final', 0.0)
            status = res.get('Status', 'N/A')
        except Exception as e:
            l_final = 0.0
            status = f"Error: {e}"
        
        credit_results.append({
            'Ticker': ticker,
            'Year': year,
            'PD_XGBoost': latest.get('PD_XGBoost', np.nan),
            'Risk_Level': risk_level,
            'Risk_VN': classification['Risk_VN'],
            'CF_Score': cf_score,
            'CF_Grade': cf_grade,
            'L_final_Ty': l_final / 1e9 if l_final > 0 else 0.0,
            'Status': status,
        })
    
    # Print credit results
    print(f"\n  {'Ticker':>8} | {'PD%':>7} | {'Risk':>12} | {'CF Score':>8} | {'Grade':>8} | {'Hạn mức (Tỷ)':>13} | {'Trạng thái':15s}")
    print(f"  {'─'*8}─┼─{'─'*7}─┼─{'─'*12}─┼─{'─'*8}─┼─{'─'*8}─┼─{'─'*13}─┼─{'─'*15}")
    
    approved_count = 0
    for cr in sorted(credit_results, key=lambda x: x['L_final_Ty'], reverse=True):
        flag = " ★" if cr['Ticker'] == 'ANV' else ""
        is_approved = cr['L_final_Ty'] > 0
        if is_approved:
            approved_count += 1
        print(f"  {cr['Ticker']:>8} | {cr['PD_XGBoost']:>6.1f}% | {cr['Risk_VN']:>12} | {cr['CF_Score']:>8} | {cr['CF_Grade']:>8} | {cr['L_final_Ty']:>12.2f} | {cr['Status'][:15]}{flag}")
    
    print(f"\n  📊 Tóm tắt: {approved_count}/{len(credit_results)} DN đủ điều kiện cấp hạn mức tín dụng")
    
    # =================================================================
    # STAGE 8: Chạy lại Backtest & Calibration
    # =================================================================
    separator("STAGE 8: Backtest & Calibration trên bộ dữ liệu mới (9 DN)")
    
    backtester = CreditBacktester(etl, all_calc_results, feature_matrix)
    dataset = backtester.prepare_dataset()
    
    total = len(dataset)
    if total == 0:
        print("  ⚠ Không đủ dữ liệu cho backtest. Bỏ qua.")
    else:
        bads = dataset['Default'].sum()
        print(f"  -> Total observations: {total}")
        print(f"  -> Defaults (Bad): {bads} ({(bads/total)*100:.1f}%)")
        
        woe_dict = backtester.calculate_woe(dataset)
        optimized_config, X_woe, y, model = backtester.calibrate_weights(dataset, woe_dict)
        
        y_pred_prob = model.predict_proba(X_woe)[:, 1]
        auc, gini, ks = backtester.calculate_metrics(y, y_pred_prob, [-s for s in y_pred_prob])
        
        print(f"\n  Calibrated Scorecard Metrics:")
        print(f"    ROC-AUC:      {auc:.4f}")
        print(f"    Gini:         {gini:.4f}")
        print(f"    KS Statistic: {ks*100:.2f}%")
        print(f"\n  ✓ Cấu hình bảng điểm tối ưu đã lưu: optimized_scorecard_config.json")

    separator("HOÀN TẤT — Huấn luyện lại + Backtest + Kiểm tra Hạn mức")


if __name__ == "__main__":
    main()
