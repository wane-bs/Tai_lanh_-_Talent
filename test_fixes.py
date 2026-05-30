"""
test_fixes.py — Script kiểm thử tự động sau khi apply các sửa đổi.

Chạy: python test_fixes.py
Tất cả 7 test phải PASS để xác nhận các sửa đổi hoạt động đúng.
"""
import sys
import os
import warnings
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((name, condition, detail))
    print(f"  {status}  {name}")
    if detail:
        print(f"          {detail}")
    return condition


print("=" * 65)
print("  TEST SUITE — Kiểm tra các sửa đổi mô hình phá sản")
print("=" * 65)


# ===================================================================
# T1: ETL — Partial year annualization
# ===================================================================
print("\n[T1] ETL Partial Year Annualization")
try:
    from etl import ETLProcessor

    # Tạo dummy quarterly data giả (Q1+Q2+Q3 của 1 năm)
    rows_3q = []
    for q in [1, 2, 3]:
        rows_3q.append({'Period': f'Q{q} 2023', 'Year': 2023, 'Quarter': q,
                        'YearQuarter': f'2023Q{q}',
                        'Doanh số thuần': 100.0,
                        'Lãi/(lỗ) thuần sau thuế': 10.0})
    df_3q = pd.DataFrame(rows_3q)

    rows_4q = []
    for q in [1, 2, 3, 4]:
        rows_4q.append({'Period': f'Q{q} 2023', 'Year': 2023, 'Quarter': q,
                        'YearQuarter': f'2023Q{q}',
                        'Doanh số thuần': 100.0,
                        'Lãi/(lỗ) thuần sau thuế': 10.0})
    df_4q = pd.DataFrame(rows_4q)

    # Giả lập ETLProcessor để test get_annual_data
    etl = ETLProcessor.__new__(ETLProcessor)
    etl.data_dir = ""
    etl.companies = {
        'TEST_3Q': {'INCOME_STATEMENT': df_3q},
        'TEST_4Q': {'INCOME_STATEMENT': df_4q},
    }

    annual_3q = etl.get_annual_data('TEST_3Q')
    annual_4q = etl.get_annual_data('TEST_4Q')

    # 3 quý → sum = 300, annualized x(4/3) = 400
    is_3q = annual_3q.get('INCOME_STATEMENT', pd.DataFrame())
    is_4q = annual_4q.get('INCOME_STATEMENT', pd.DataFrame())

    if not is_3q.empty and not is_4q.empty:
        rev_3q = float(is_3q[is_3q['Year'] == 2023]['Doanh số thuần'].iloc[0])
        rev_4q = float(is_4q[is_4q['Year'] == 2023]['Doanh số thuần'].iloc[0])
        is_partial_3q = bool(is_3q[is_3q['Year'] == 2023]['Is_Partial_Year'].iloc[0])
        is_partial_4q = bool(is_4q[is_4q['Year'] == 2023]['Is_Partial_Year'].iloc[0])

        t1_annualized = abs(rev_3q - 400.0) < 1.0  # 3*100 * (4/3) = 400
        t1_full_year = abs(rev_4q - 400.0) < 1.0   # 4*100 = 400
        t1_flag_3q = is_partial_3q == True
        t1_flag_4q = is_partial_4q == False

        check("T1a: 3Q revenue annualized = 400", t1_annualized, f"Got: {rev_3q}")
        check("T1b: 4Q revenue sum = 400", t1_full_year, f"Got: {rev_4q}")
        check("T1c: Is_Partial_Year=True cho 3Q", t1_flag_3q, f"Got: {is_partial_3q}")
        check("T1d: Is_Partial_Year=False cho 4Q", t1_flag_4q, f"Got: {is_partial_4q}")
    else:
        check("T1: ETL partial year", False, "Annual data rỗng")
except Exception as e:
    check("T1: ETL partial year", False, f"Exception: {e}")


# ===================================================================
# T2: Feature Engine — Min 2 năm warning + UserWarning
# ===================================================================
print("\n[T2] Feature Engine — Min 2 năm warning")
try:
    from feature_engine import FeatureEngine

    fe = FeatureEngine()

    # Tạo BS chỉ có 1 năm
    bs_1yr = pd.DataFrame([{
        'Year': 2023, 'Quarter': 4, 'YearQuarter': '2023Q4', 'Period': 'Q4 2023',
        'TỔNG TÀI SẢN': 1000.0, 'TÀI SẢN NGẮN HẠN': 400.0,
        'Nợ ngắn hạn': 200.0, 'NỢ PHẢI TRẢ': 500.0,
        'VỐN CHỦ SỞ HỮU': 500.0, 'Lãi chưa phân phối': 100.0,
        'Hàng tồn kho': 50.0,
    }])
    is_1yr = pd.DataFrame([{
        'Year': 2023, 'Quarter': 4, 'YearQuarter': '2023Q4', 'Period': 'Q4 2023',
        'Doanh số thuần': 500.0, 'Lãi/(lỗ) thuần sau thuế': 50.0,
        'EBIT': 70.0, 'Chi phí lãi vay': 20.0, 'EBITDA': 90.0,
    }])

    annual_data = {'BALANCE_SHEET': bs_1yr, 'INCOME_STATEMENT': is_1yr}

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        features = fe.extract_features(annual_data, {}, ticker='TEST_1YR')
        user_warnings = [x for x in w if issubclass(x.category, UserWarning)]

    t2_warning = len(user_warnings) > 0
    t2_not_empty = not features.empty  # Vẫn trả về features (không skip)
    t2_revenue_growth_nan = features['revenue_growth'].isna().all() if not features.empty else True

    check("T2a: UserWarning raised khi 1 năm data", t2_warning,
          f"Got {len(user_warnings)} warnings")
    check("T2b: Features không rỗng (vẫn tính 1-năm features)", t2_not_empty)
    check("T2c: revenue_growth = NaN (cần ≥2 năm)", t2_revenue_growth_nan)
except Exception as e:
    check("T2: Feature Engine min 2 năm", False, f"Exception: {e}")


# ===================================================================
# T3: Cash Flow Scorer — CFO growth fallback = NaN
# ===================================================================
print("\n[T3] Cash Flow Scorer — CFO growth fallback")
try:
    from cash_flow_scorer import BCTCCashFlowScorer

    scorer = BCTCCashFlowScorer()

    # Tạo BCTC chỉ có 1 năm CF
    bs_1 = pd.DataFrame([{
        'Year': 2023,
        'Vay và nợ thuê tài chính ngắn hạn': 100.0,
        'Vay và nợ thuê tài chính dài hạn': 200.0,
        'Tiền và các khoản tương đương tiền': 50.0,
        'Vốn chủ sở hữu': 300.0,
        'Nợ phải trả': 300.0,
    }])
    is_1 = pd.DataFrame([{
        'Year': 2023,
        'Doanh số thuần': 500.0,
        'Chi phí lãi vay': 20.0,
        'Giá vốn hàng bán': 300.0,
        'Chi phí bán hàng': 30.0,
        'Chi phí quản lý doanh nghiệp': 20.0,
    }])
    cf_1 = pd.DataFrame([{
        'Year': 2023,
        'Lưu chuyển tiền thuần từ các hoạt động sản xuất': 80.0,
    }])

    annual = {'BALANCE_SHEET': bs_1, 'INCOME_STATEMENT': is_1, 'CASH_FLOW': cf_1}

    class MockETL:
        def get_annual_data(self, t): return annual
        def get_ttm_data(self, t): return annual

    metrics = scorer.calculate_metrics('TEST', MockETL())
    t3_cfo_nan = pd.isna(metrics.get('cfo_growth_yoy'))
    check("T3a: cfo_growth_yoy = NaN khi chỉ có 1 năm CF", t3_cfo_nan,
          f"Got: {metrics.get('cfo_growth_yoy')}")

    # Test UserWarning khi expert mode
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        scorer_no_config = BCTCCashFlowScorer.__new__(BCTCCashFlowScorer)
        scorer_no_config.base_score = 600
        scorer_no_config.scaling_factor = 4.0
        scorer_no_config.config = None
        scorer_no_config.compute_score(metrics)
        expert_warnings = [x for x in w if issubclass(x.category, UserWarning)]

    t3_warning = len(expert_warnings) > 0
    check("T3b: UserWarning raised khi expert mode (chưa calibrate)", t3_warning,
          f"Got {len(expert_warnings)} warnings")
except Exception as e:
    check("T3: Cash Flow Scorer", False, f"Exception: {e}")


# ===================================================================
# T4: Backtest Engine — Không còn PD_XGBoost trong _label_default
# ===================================================================
print("\n[T4] Backtest Engine — No circular labeling")
try:
    import inspect
    from backtest_engine import CreditBacktester

    source = inspect.getsource(CreditBacktester._label_default)
    # Kiểm tra code LOGIC không dùng PD_XGBoost, không phải toàn bộ source (bao gồm docstring)
    # Tìm các pattern truy cập giá trị: row.get('PD_XGBoost') hoặc row['PD_XGBoost']
    t4_no_pd_xgb = (
        "row.get('PD_XGBoost'" not in source and
        "row['PD_XGBoost']" not in source and
        'pd_xgb = row' not in source
    )
    check("T4a: _label_default không truy cập row['PD_XGBoost']", t4_no_pd_xgb,
          "Tìm thấy code truy cập PD_XGBoost trong logic" if not t4_no_pd_xgb else "")

    # Test với dữ liệu giả — trường hợp runway < 1 → phải label default
    dummy_etl = type('E', (), {
        'companies': {'X': {}},
        'get_annual_data': lambda s, t: {},
        'get_ttm_data': lambda s, t: {},
    })()
    dummy_features = pd.DataFrame({'Ticker': ['X'], 'Year': [2023]})
    dummy_calc = {
        'X': {
            'bds_metrics': pd.DataFrame([{
                'Year': 2023, 'Quarter': 4,
                'interest_coverage_cfo': 0.3,  # < 0.5
                'runway_interest': 0.5,          # < 1 → Rule 1 trigger
            }]),
            'altman': pd.DataFrame([{'Year': 2023, 'Z_Score': 0.8}]),
            'ohlson': pd.DataFrame([{'Year': 2023, 'PD_Ohlson': 30.0}]),
        }
    }

    backtester = CreditBacktester.__new__(CreditBacktester)
    backtester.etl = dummy_etl
    backtester.calc_results = dummy_calc
    backtester.features_df = dummy_features
    backtester.bins_config = {}
    from cash_flow_scorer import BCTCCashFlowScorer
    from risk_classifier import RiskClassifier
    backtester.scorer = BCTCCashFlowScorer()
    backtester.risk_classifier = RiskClassifier()

    row = pd.Series({'Year': 2023, 'Ticker': 'X'})
    t_calc = dummy_calc['X']
    result = backtester._label_default(row, t_calc, 2023)
    check("T4b: runway<1 → label Default=True", result == True, f"Got: {result}")
except Exception as e:
    check("T4: Backtest Engine circular labeling", False, f"Exception: {e}")


# ===================================================================
# T5: WOE stability — Không có NaN/Inf
# ===================================================================
print("\n[T5] WOE Stability — Không có NaN/Inf")
try:
    from backtest_engine import CreditBacktester

    # Tạo dataset nhỏ (giả lập ít bad samples)
    np.random.seed(42)
    n = 30
    data = {
        'Default': [0]*27 + [1]*3,  # 10% bad rate
        'cash_to_revenue_bin': np.random.randint(0, 3, n),
        'dscr_bin': np.random.randint(0, 5, n),
        'cash_buffer_days_bin': np.random.randint(0, 3, n),
        'revenue_volatility_bin': np.random.randint(0, 4, n),
        'equity_to_debt_bin': np.random.randint(0, 4, n),
        'cfo_growth_yoy_bin': np.random.randint(0, 3, n),
    }
    df_test = pd.DataFrame(data)

    backtester = CreditBacktester.__new__(CreditBacktester)
    backtester.bins_config = {
        'cash_to_revenue': [0.95, 0.80, 0.70],
        'dscr': [2.0, 1.5, 1.25, 1.0, 0.75],
        'cash_buffer_days': [90, 45, 15],
        'revenue_volatility': [0.15, 0.30, 0.45],
        'equity_to_debt': [1.5, 1.0, 0.5, 0.3],
        'cfo_growth_yoy': [0.15, 0.0, -0.15],
    }

    woe_dict = backtester.calculate_woe(df_test)

    all_woe_vals = []
    for feature, bins in woe_dict.items():
        all_woe_vals.extend(bins.values())

    t5_no_nan = not any(np.isnan(v) for v in all_woe_vals)
    t5_no_inf = not any(np.isinf(v) for v in all_woe_vals)
    check("T5a: Không có NaN trong WOE", t5_no_nan,
          f"NaN count: {sum(np.isnan(v) for v in all_woe_vals)}")
    check("T5b: Không có Inf trong WOE", t5_no_inf,
          f"Inf count: {sum(np.isinf(v) for v in all_woe_vals)}")
except Exception as e:
    check("T5: WOE stability", False, f"Exception: {e}")


# ===================================================================
# T6: Model Engine — Test ROC không inflate bằng train ROC
# ===================================================================
print("\n[T6] Model Engine — Held-out test set (không inflate)")
try:
    # Test logic: sau khi train, scaler phải fit chỉ trên train
    # và evaluate trên test set riêng biệt
    import inspect
    from model_engine import MLEngine

    source = inspect.getsource(MLEngine.train_xgboost)

    t6_has_split = 'train_test_split' in source
    t6_test_set_label = '[TEST SET - Held-out' in source
    t6_no_train_eval = 'X_scaled, y' not in source  # Không evaluate trên full dataset

    check("T6a: Có train_test_split trong train_xgboost", t6_has_split)
    check("T6b: Output ghi rõ [TEST SET - Held-out]", t6_test_set_label)
    check("T6c: Không evaluate trên toàn bộ train set", t6_no_train_eval)
except Exception as e:
    check("T6: Model Engine held-out", False, f"Exception: {e}")


# ===================================================================
# T7: Feature Engine — Expanding imputation không dùng future data
# ===================================================================
print("\n[T7] Feature Engine — Expanding median imputation")
try:
    from feature_engine import FeatureEngine

    fe = FeatureEngine()

    # Tạo data với NaN ở giữa
    df_test = pd.DataFrame({
        'Year': [2020, 2021, 2022, 2023],
        'Ticker': ['X', 'X', 'X', 'X'],
        'ebit_ta': [0.1, np.nan, 0.15, 0.2],
        'wc_ta':   [0.3, 0.25, np.nan, 0.35],
    })

    feature_cols = ['ebit_ta', 'wc_ta']
    result = fe.impute_missing(df_test, feature_cols)

    # 2021 ebit_ta NaN → expanding median của [2020] = 0.1 (chỉ dùng dữ liệu trước)
    ebit_2021 = result.loc[result['Year'] == 2021, 'ebit_ta'].values[0]
    t7_expanding = abs(ebit_2021 - 0.1) < 0.01  # median([0.1]) = 0.1

    # 2022 wc_ta NaN → expanding median của [0.3, 0.25] = 0.275
    wc_2022 = result.loc[result['Year'] == 2022, 'wc_ta'].values[0]
    t7_expanding_2 = abs(wc_2022 - 0.275) < 0.01

    t7_no_nan = not result[feature_cols].isna().any().any()

    check("T7a: 2021 ebit_ta imputed = 0.1 (median chỉ dùng 2020)", t7_expanding,
          f"Got: {ebit_2021:.4f}")
    check("T7b: 2022 wc_ta imputed = 0.275 (median 2020+2021)", t7_expanding_2,
          f"Got: {wc_2022:.4f}")
    check("T7c: Không còn NaN sau imputation", t7_no_nan)
except Exception as e:
    check("T7: Expanding imputation", False, f"Exception: {e}")


# ===================================================================
# SUMMARY
# ===================================================================
print("\n" + "=" * 65)
print("  KẾT QUẢ TỔNG HỢP")
print("=" * 65)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"\n  {passed}/{total} tests PASS\n")

for name, ok, detail in results:
    status = PASS if ok else FAIL
    print(f"  {status}  {name}")

if passed == total:
    print(f"\n  🎉 TẤT CẢ {total} TESTS PASS — Các sửa đổi hoạt động đúng!")
else:
    failed = [(n, d) for n, ok, d in results if not ok]
    print(f"\n  ⚠ {len(failed)} test(s) FAIL:")
    for name, detail in failed:
        print(f"    - {name}: {detail}")
    sys.exit(1)
