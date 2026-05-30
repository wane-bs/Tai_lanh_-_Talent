"""
Pipeline Runner — Điều phối toàn bộ quy trình phân tích phá sản.

Stages:
1. ETL: Đọc và chuẩn hóa dữ liệu BCTC
2. Calculator: Tính các chỉ số cổ điển (Altman, Beneish, Ohlson, Zmijewski)
3. Feature Engineering: Xây dựng Feature Matrix
4. ML Engine: RF Selection → XGBoost PD → SHAP
5. Risk Classifier: Phân loại 5 mức rủi ro
6. Report Generator: Sinh báo cáo Markdown

Usage:
    python pipeline_runner.py --data-dir data/companies --train
    python pipeline_runner.py --data-dir data/companies --predict-only
"""

import os
import sys
import argparse
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from etl import ETLProcessor
from calculator import BankruptcyCalculator
from feature_engine import FeatureEngine
from model_engine import MLEngine
from risk_classifier import RiskClassifier
from report_generator import ReportGenerator


class PipelineRunner:
    """Chạy toàn bộ pipeline phân tích phá sản."""

    def __init__(self, base_dir: str = None, industry: str = 'DEFAULT'):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, "data", "companies")
        self.polish_dir = os.path.join(base_dir, "data", "polish")
        self.taiwanese_dir = os.path.join(base_dir, "data", "taiwanese")
        self.output_dir = os.path.join(base_dir, "output")
        self.model_dir = os.path.join(base_dir, "models")
        self.industry = industry

        # Module instances
        self.etl = None
        self.calculators = {}  # {ticker: BankruptcyCalculator}
        self.calc_results = {}  # {ticker: dict of results}
        self.feature_engine = FeatureEngine(industry=self.industry)
        self.ml_engine = MLEngine(model_dir=self.model_dir)
        self.risk_classifier = RiskClassifier(industry=self.industry)
        self.report_gen = ReportGenerator()

        # Data
        self.features_df = None
        self.classified_df = None

    def run_stage1_etl(self) -> dict:
        """Stage 1: ETL — Đọc và chuẩn hóa dữ liệu."""
        print("\n" + "=" * 60)
        print("📥 STAGE 1: ETL & Normalization")
        print("=" * 60)

        self.etl = ETLProcessor(self.data_dir)
        companies = self.etl.load_all()

        if not companies:
            print("  ✗ Không tìm thấy dữ liệu BCTC.")
            return {}

        # Lưu dữ liệu chuẩn hóa
        norm_dir = os.path.join(self.output_dir, "1_normalized")
        self.etl.save_normalized(norm_dir)

        return companies

    def run_stage2_calculator(self) -> dict:
        """Stage 2: Calculator — Tính các chỉ số cổ điển."""
        print("\n" + "=" * 60)
        print("🧮 STAGE 2: Classical Scores Calculator")
        print("=" * 60)

        if self.etl is None or not self.etl.companies:
            print("  ✗ Chạy Stage 1 trước.")
            return {}

        scores_dir = os.path.join(self.output_dir, "3_scores")

        for ticker in self.etl.companies:
            print(f"\n--- {ticker} ---")
            annual = self.etl.get_annual_data(ticker)
            calc = BankruptcyCalculator(annual, ticker, industry=self.industry)

            # BĐS: truyền dữ liệu quý (có TTM) cho real_estate_metrics()
            quarterly_data = None
            if self.industry == 'REAL_ESTATE':
                quarterly_data = self.etl.get_ttm_data(ticker)

            results = calc.run_all(quarterly_data=quarterly_data)
            calc.save_results(scores_dir)

            self.calculators[ticker] = calc
            self.calc_results[ticker] = results

        print(f"\n  ✓ Đã tính scores cho {len(self.calc_results)} doanh nghiệp")
        return self.calc_results

    def run_stage3_features(self) -> 'pd.DataFrame':
        """Stage 3: Feature Engineering — Xây dựng Feature Matrix."""
        import pandas as pd

        print("\n" + "=" * 60)
        print("🔧 STAGE 3: Feature Engineering")
        print("=" * 60)

        if self.etl is None or not self.calc_results:
            print("  ✗ Chạy Stage 1 & 2 trước.")
            return pd.DataFrame()

        all_features = []

        for ticker in self.etl.companies:
            annual = self.etl.get_annual_data(ticker)
            calc_res = self.calc_results.get(ticker, {})

            features = self.feature_engine.transform(
                annual, calc_res, ticker, normalize=False
            )
            if not features.empty:
                all_features.append(features)
                print(f"  ✓ [{ticker}] {len(features)} records, "
                      f"{len(features.columns) - 2} features")

        if not all_features:
            print("  ✗ Không tạo được Feature Matrix.")
            return pd.DataFrame()

        self.features_df = pd.concat(all_features, ignore_index=True)

        # Lưu features
        feat_dir = os.path.join(self.output_dir, "2_features")
        self.feature_engine.save_features(self.features_df, feat_dir)

        print(f"\n  ✓ Feature Matrix: {self.features_df.shape[0]} records × "
              f"{self.features_df.shape[1]} columns")

        return self.features_df

    def run_stage4_ml(self, train: bool = True,
                      dataset: str = 'polish') -> 'pd.DataFrame':
        """Stage 4: ML Engine — RF + XGBoost + SHAP."""
        import pandas as pd

        print("\n" + "=" * 60)
        print(f"🤖 STAGE 4: ML Engine (dataset={dataset})")
        print("=" * 60)

        if train:
            # Train trên dataset được chọn
            metrics = self.ml_engine.train_pipeline(
                data_dir=self.polish_dir,
                top_k_features=10,
                dataset=dataset,
                taiwanese_dir=self.taiwanese_dir
            )
        else:
            # Load pre-trained model
            self.ml_engine.load_model()

        # Predict cho doanh nghiệp VN
        if self.features_df is not None and not self.features_df.empty:
            self.features_df = self.ml_engine.predict(self.features_df)
            print(f"\n  ✓ Đã dự báo PD cho {len(self.features_df)} records")

            # SHAP explanation
            try:
                shap_df = self.ml_engine.explain_shap(self.features_df)
                # Lưu ML results
                ml_dir = os.path.join(self.output_dir, "4_ml_results")
                os.makedirs(ml_dir, exist_ok=True)
                self.features_df.to_csv(
                    os.path.join(ml_dir, "predictions.csv"), index=False
                )
                if not shap_df.empty:
                    shap_df.to_csv(
                        os.path.join(ml_dir, "shap_values.csv"), index=False
                    )
            except Exception as e:
                print(f"  ⚠ SHAP skipped: {e}")

        return self.features_df

    def run_stage5_classify(self) -> 'pd.DataFrame':
        """Stage 5: Risk Classifier — Phân loại 5 mức rủi ro."""
        import pandas as pd

        print("\n" + "=" * 60)
        print("🏷️ STAGE 5: Risk Classification")
        print("=" * 60)

        if self.features_df is None or self.features_df.empty:
            print("  ✗ Chạy Stage 3 & 4 trước.")
            return pd.DataFrame()

        # Classify từng ticker
        all_classified = []
        for ticker in self.features_df['Ticker'].unique():
            t_features = self.features_df[self.features_df['Ticker'] == ticker].copy()
            calc_res = self.calc_results.get(ticker, {})
            classified = self.risk_classifier.classify(t_features, calc_res)
            all_classified.append(classified)

        if all_classified:
            self.classified_df = pd.concat(all_classified, ignore_index=True)
        else:
            self.classified_df = pd.DataFrame()

        # Summary
        if not self.classified_df.empty:
            summary = self.risk_classifier.summary(self.classified_df)
            print("\n📋 Tổng kết Rủi ro:")
            print("-" * 60)
            for _, row in summary.iterrows():
                emoji = row.get('Risk_Emoji', '')
                ticker = row.get('Ticker', '')
                name = row.get('Risk_VN', '')
                comp = row.get('Composite_Score', 0)
                print(f"  {emoji} {ticker:10s} — {name:12s} (Score: {comp:.1f})")

            # Save
            risk_dir = os.path.join(self.output_dir, "4_ml_results")
            self.risk_classifier.save_classification(self.classified_df, risk_dir)

        return self.classified_df

    def run_stage6_report(self):
        """Stage 6: Report Generator — Sinh báo cáo Markdown."""
        print("\n" + "=" * 60)
        print("📝 STAGE 6: Report Generation")
        print("=" * 60)

        if self.classified_df is None or self.classified_df.empty:
            print("  ✗ Chạy Stage 5 trước.")
            return

        report_dir = os.path.join(self.output_dir, "5_reports")
        self.report_gen.save_reports(
            self.classified_df,
            self.calc_results,
            report_dir
        )

        print(f"\n  ✓ Báo cáo đã được tạo tại {report_dir}")

    def run_all(self, train: bool = True, dataset: str = 'polish'):
        """Chạy toàn bộ pipeline."""
        start = time.time()

        print("\n" + "🔥" * 30)
        print("  HỆ THỐNG KIỂM SOÁT & DỰ BÁO RỦI RO PHÁ SẢN")
        print(f"  Training dataset: {dataset.upper()}")
        print("🔥" * 30)

        self.run_stage1_etl()
        self.run_stage2_calculator()
        self.run_stage3_features()
        self.run_stage4_ml(train=train, dataset=dataset)
        self.run_stage5_classify()
        self.run_stage6_report()

        elapsed = time.time() - start
        print("\n" + "=" * 60)
        print(f"✅ Pipeline hoàn thành trong {elapsed:.1f}s")
        print("=" * 60)

        return self.classified_df


def main():
    parser = argparse.ArgumentParser(
        description="Hệ thống Dự báo Rủi ro Phá sản"
    )
    parser.add_argument(
        '--data-dir', type=str, default=None,
        help='Thư mục chứa file XLSX doanh nghiệp'
    )
    parser.add_argument(
        '--train', action='store_true', default=False,
        help='Huấn luyện model mới (mặc định: dùng model có sẵn)'
    )
    parser.add_argument(
        '--predict-only', action='store_true', default=False,
        help='Chỉ dự báo (dùng model đã train)'
    )
    parser.add_argument(
        '--industry', type=str, default='DEFAULT',
        help='Mã ngành: DEFAULT, RETAIL, REAL_ESTATE (để sử dụng luật chuyên biệt BĐS)'
    )
    parser.add_argument(
        '--dataset', type=str, default='polish',
        choices=['polish', 'taiwanese', 'combined'],
        help='Dataset huấn luyện: polish (mặc định), taiwanese, combined (gộp cả 2)'
    )

    args = parser.parse_args()

    runner = PipelineRunner(industry=args.industry)
    if args.data_dir:
        runner.data_dir = args.data_dir

    if args.predict_only:
        runner.run_all(train=False, dataset=args.dataset)
    else:
        runner.run_all(train=args.train, dataset=args.dataset)


if __name__ == "__main__":
    main()
