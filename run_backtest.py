import sys
import os
import pandas as pd
import numpy as np
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from etl import ETLProcessor
from backtest_engine import CreditBacktester
from cash_flow_scorer import BCTCCashFlowScorer

def main():
    print("="*60)
    print(" BCTC CASH FLOW SCORECARD - BACKTEST & CALIBRATION ENGINE ")
    print("="*60)

    # 1. Load Data
    print("1. Loading historical datasets...")
    data_dir = os.path.join(os.path.dirname(__file__), "data", "companies")
    etl = ETLProcessor(data_dir)
    etl.load_all()
    
    output_dir = os.path.join(os.path.dirname(__file__), "ket_qua_test", "bds_validation")
    feature_matrix_path = os.path.join(output_dir, "feature_matrix_bds.csv")
    if not os.path.exists(feature_matrix_path):
        print(f"ERROR: feature_matrix_bds.csv not found at {feature_matrix_path}")
        print("Please run validate_bds_model.py first to generate the feature matrix.")
        return
        
    features_df = pd.read_csv(feature_matrix_path)
    
    from calculator import BankruptcyCalculator
    print("2. Re-computing classical metrics (Z-score, etc)...")
    all_calc_results = {}
    for ticker in etl.companies.keys():
        annual = etl.get_annual_data(ticker)
        quarterly = etl.get_ttm_data(ticker)
        calc = BankruptcyCalculator(annual, ticker, industry='REAL_ESTATE')
        all_calc_results[ticker] = calc.run_all(quarterly_data=quarterly)
        
    print("\n3. Building Backtest Dataset & Labeling Defaults...")
    backtester = CreditBacktester(etl, all_calc_results, features_df)
    dataset = backtester.prepare_dataset()
    
    total = len(dataset)
    bads = dataset['Default'].sum()
    print(f"  -> Total observations: {total}")
    print(f"  -> Defaults (Bad): {bads} ({(bads/total)*100:.1f}%)")
    print(f"  -> Non-Defaults (Good): {total - bads} ({((total-bads)/total)*100:.1f}%)")
    
    print("\n4. Calculating Weight of Evidence (WOE)...")
    woe_dict = backtester.calculate_woe(dataset)
    for feature, bins_woe in woe_dict.items():
        # Formatting WOE output
        woe_str = ", ".join([f"bin{k}:{v:+.2f}" for k, v in bins_woe.items()])
        print(f"  - {feature:20s}: {woe_str}")
        
    print("\n5. Fitting Logistic Regression & Calibrating Scorecard...")
    optimized_config, X_woe, y, model = backtester.calibrate_weights(dataset, woe_dict)
    
    y_pred_prob = model.predict_proba(X_woe)[:, 1]
    
    # Reload scorer to use new config
    calibrated_scorer = BCTCCashFlowScorer()
    
    calibrated_scores = []
    expert_scores = []
    
    # Move config temp to get expert scorer
    config_path = os.path.join(os.path.dirname(__file__), "optimized_scorecard_config.json")
    config_tmp_path = os.path.join(os.path.dirname(__file__), "optimized_scorecard_config_tmp.json")
    os.rename(config_path, config_tmp_path)
    expert_scorer = BCTCCashFlowScorer()
    os.rename(config_tmp_path, config_path)
    
    for idx, row in dataset.iterrows():
        metrics = {k: row[k] for k in backtester.bins_config.keys()}
        c_score, _ = calibrated_scorer.compute_score(metrics)
        e_score, _ = expert_scorer.compute_score(metrics)
        calibrated_scores.append(c_score)
        expert_scores.append(e_score)
        
    dataset['Expert_Score'] = expert_scores
    dataset['Calibrated_Score'] = calibrated_scores
    
    print("\n6. Evaluating Scorecard Performance...")
    
    # For ROC and KS we use -Score because standard metrics expect higher score = higher risk
    # whereas Credit Score has higher score = lower risk.
    # We will use y_pred_prob (Probability of Bad) for AUC, and -Score for KS.
    
    c_auc, c_gini, c_ks = backtester.calculate_metrics(y, y_pred_prob, [-s for s in calibrated_scores])
    
    # Calculate performance for expert scorecard
    # We don't have exact probabilities for expert, so we just use -Expert_Score as the predictor
    e_auc, e_gini, e_ks = backtester.calculate_metrics(y, [-s for s in expert_scores], [-s for s in expert_scores])
    
    print("\n" + "-"*60)
    print(" PERFORMANCE METRICS COMPARISON ")
    print("-" * 60)
    print(f"               | {'Expert Scorecard':>20} | {'Calibrated (LogReg)':>20} | {'Goal':>10}")
    print(f"  ROC-AUC      | {e_auc:20.4f} | {c_auc:20.4f} | {'>= 0.75':>10}")
    print(f"  Gini         | {e_gini:20.4f} | {c_gini:20.4f} | {'>= 0.50':>10}")
    print(f"  KS Statistic | {e_ks*100:19.2f}% | {c_ks*100:19.2f}% | {'>= 35%':>10}")
    
    psi = backtester.calculate_psi(expert_scores, calibrated_scores, bins=10)
    print(f"\n  Population Stability Index (Expert -> Calibrated): {psi:.4f} (Goal < 0.25)")
    
    print("\n" + "-"*60)
    print(" CALIBRATION SUMMARY ")
    print("-" * 60)
    print("New Score points per bin saved to: optimized_scorecard_config.json")
    for feature, cfg in optimized_config['features'].items():
        pts_str = ", ".join([f"bin{k}: {v:3d} pts" for k, v in cfg['points'].items()])
        print(f"  {feature:20s} -> {pts_str}")

if __name__ == "__main__":
    main()
