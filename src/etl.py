"""
ETL Module — Đọc và chuẩn hóa dữ liệu BCTC đa doanh nghiệp.

Dữ liệu đầu vào:
  - Format vertical: mỗi hàng = 1 quý, mỗi cột = 1 chỉ tiêu (chuẩn gốc)
  - Format horizontal: mỗi hàng = 1 chỉ tiêu, mỗi cột = 1 quý (BĐS / CafeF format)
Đầu ra: dict {ticker: {sheet_name: DataFrame}} với DataFrame chuẩn hóa.
"""

import pandas as pd
import numpy as np
import os
import glob
import re


class ETLProcessor:
    """Đọc và chuẩn hóa dữ liệu BCTC từ nhiều file XLSX."""

    SHEET_MAP = {
        'BS': 'BALANCE_SHEET',
        'IS': 'INCOME_STATEMENT',
        'CF': 'CASH_FLOW',
    }

    # Các cột IS/CF cần tính TTM (Trailing Twelve Months)
    TTM_IS_PATTERNS = [
        'Doanh số thuần', 'Lãi gộp', 'Chi phí bán hàng',
        'Chi phí quản lý', 'Lãi/(lỗ) thuần sau thuế',
        'Chi phí lãi vay', 'EBIT', 'EBITDA', 'Giá vốn hàng bán',
    ]
    TTM_CF_PATTERNS = [
        'Lưu chuyển tiền thuần từ các hoạt động sản xuất',
        'Khấu hao TSCĐ',
        'Tiển trả các khoản đi vay',
    ]

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.companies = {}  # {ticker: {sheet: DataFrame}}

    def discover_files(self) -> list[str]:
        """Quét tất cả file .xlsx trong thư mục dữ liệu."""
        pattern = os.path.join(self.data_dir, "*.xlsx")
        files = [f for f in glob.glob(pattern) if not os.path.basename(f).startswith('~$')]
        return sorted(files)

    # =================================================================
    # LOAD: Format dọc (vertical — chuẩn gốc)
    # =================================================================
    def _load_vertical(self, xls: pd.ExcelFile, ticker: str) -> dict[str, pd.DataFrame]:
        """Đọc file XLSX dạng dọc (mỗi hàng = 1 quý)."""
        sheets = {}
        for raw_name, canonical in self.SHEET_MAP.items():
            actual = None
            for sn in xls.sheet_names:
                if sn.strip().upper() == raw_name.upper():
                    actual = sn
                    break
            if actual is None:
                print(f"  [{ticker}] Cảnh báo: không tìm thấy sheet '{raw_name}'")
                continue

            df = pd.read_excel(xls, sheet_name=actual)

            first_col = df.columns[0]
            df = df.rename(columns={first_col: 'Period'})
            df['Period'] = df['Period'].astype(str).str.strip()

            df = df[df['Period'].str.match(r'^Q\d\s+\d{4}$', na=False)].copy()

            df['Year'] = df['Period'].apply(lambda x: int(x.split()[-1]))
            df['Quarter'] = df['Period'].apply(lambda x: int(re.search(r'Q(\d)', x).group(1)))
            df['YearQuarter'] = df['Year'].astype(str) + 'Q' + df['Quarter'].astype(str)

            data_cols = [c for c in df.columns if c not in ['Period', 'Year', 'Quarter', 'YearQuarter']]
            for col in data_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

            df = df.sort_values(['Year', 'Quarter']).reset_index(drop=True)
            sheets[canonical] = df

        return sheets

    # =================================================================
    # LOAD: Format ngang (horizontal — CafeF / BĐS format)
    # =================================================================
    def _load_horizontal(self, xls: pd.ExcelFile, ticker: str) -> dict[str, pd.DataFrame]:
        """Đọc file XLSX dạng ngang (cột = quý, hàng = chỉ tiêu) và transpose."""
        sheets = {}
        for raw_name, canonical in self.SHEET_MAP.items():
            if raw_name not in xls.sheet_names:
                # Tìm gần đúng
                found = False
                for sn in xls.sheet_names:
                    if sn.strip().upper() == raw_name.upper():
                        raw_name = sn
                        found = True
                        break
                if not found:
                    print(f"  [{ticker}] Cảnh báo: không tìm thấy sheet '{raw_name}'")
                    continue

            df = pd.read_excel(xls, sheet_name=raw_name)
            df.dropna(how='all', axis=1, inplace=True)

            # Cột đầu tiên = tên chỉ tiêu
            first_col = df.columns[0]
            df = df.rename(columns={first_col: 'CHỈ TIÊU'})
            df['CHỈ TIÊU'] = df['CHỈ TIÊU'].fillna('Unknown')

            # Deduplicate tên chỉ tiêu
            s = df['CHỈ TIÊU']
            counts = s.groupby(s).cumcount()
            df['CHỈ TIÊU'] = s + counts.astype(str).replace('0', '').replace(
                r'^[1-9]+', r' \g<0>', regex=True)

            # Transpose: cột → hàng
            df.set_index('CHỈ TIÊU', inplace=True)
            df_t = df.T
            df_t.reset_index(inplace=True)
            df_t.rename(columns={'index': 'Period'}, inplace=True)

            # Parse Year / Quarter (format: 'Q1 2023')
            df_t['Period'] = df_t['Period'].astype(str).str.strip()
            df_t = df_t[df_t['Period'].str.contains('Q', na=False)].copy()

            if df_t.empty:
                continue

            df_t['Year'] = df_t['Period'].apply(lambda x: int(x.split()[-1]))
            df_t['Quarter'] = df_t['Period'].apply(
                lambda x: int(x.split('Q')[1].split()[0]))
            df_t['YearQuarter'] = df_t['Year'].astype(str) + 'Q' + df_t['Quarter'].astype(str)

            for col in df_t.columns:
                if col not in ['Period', 'Year', 'Quarter', 'YearQuarter']:
                    df_t[col] = pd.to_numeric(df_t[col], errors='coerce').fillna(0.0)

            df_t = df_t.sort_values(['Year', 'Quarter']).reset_index(drop=True)
            sheets[canonical] = df_t

        return sheets

    # =================================================================
    # AUTO-DETECT FORMAT
    # =================================================================
    def _detect_format(self, xls: pd.ExcelFile) -> str:
        """Tự động nhận dạng format file: 'vertical' hoặc 'horizontal'."""
        for sn in xls.sheet_names:
            if sn.strip().upper() in [k.upper() for k in self.SHEET_MAP.keys()]:
                df_peek = pd.read_excel(xls, sheet_name=sn, nrows=5)
                first_col = df_peek.columns[0]
                first_vals = df_peek[first_col].astype(str).str.strip()
                # Vertical: cột đầu chứa 'Q1 2023' pattern
                if first_vals.str.match(r'^Q\d\s+\d{4}$').any():
                    return 'vertical'
                # Horizontal: cột đầu chứa tên chỉ tiêu dài (như 'TỔNG TÀI SẢN')
                if first_vals.str.len().mean() > 10:
                    return 'horizontal'
                # Kiểm tra xem header có chứa Q pattern không
                for c in df_peek.columns[1:]:
                    if re.match(r'^Q\d\s+\d{4}$', str(c).strip()):
                        return 'horizontal'
                break
        return 'vertical'  # mặc định

    def load_company(self, filepath: str) -> tuple:
        """Đọc 1 file XLSX (1 doanh nghiệp), tự động detect format."""
        ticker = os.path.splitext(os.path.basename(filepath))[0].upper()
        xls = pd.ExcelFile(filepath)

        fmt = self._detect_format(xls)
        if fmt == 'horizontal':
            print(f"  [{ticker}] Detected: horizontal format (CafeF)")
            sheets = self._load_horizontal(xls, ticker)
        else:
            sheets = self._load_vertical(xls, ticker)

        return ticker, sheets

    def load_all(self) -> dict:
        """Đọc tất cả file trong thư mục dữ liệu."""
        files = self.discover_files()
        if not files:
            print(f"Không tìm thấy file .xlsx nào trong {self.data_dir}")
            return {}

        print(f"Phát hiện {len(files)} file doanh nghiệp:")
        for f in files:
            ticker, sheets = self.load_company(f)
            self.companies[ticker] = sheets
            total_rows = sum(len(df) for df in sheets.values())
            print(f"  ✓ {ticker}: {len(sheets)} sheets, {total_rows} records")

        # Tự động tính TTM cho tất cả doanh nghiệp
        self._apply_ttm_all()

        return self.companies

    # =================================================================
    # TTM ROLLING (Trailing Twelve Months — Lũy kế 4 Quý)
    # =================================================================
    def calculate_ttm_rolling(self, ticker: str):
        """
        Tính TTM (Lũy kế 4 Quý gần nhất) cho IS và CF của 1 doanh nghiệp.
        Tạo cột mới có hậu tố _TTM cho mỗi biến flow.
        """
        if ticker not in self.companies:
            return

        sheets = self.companies[ticker]

        # IS: tính TTM cho các cột flow
        if 'INCOME_STATEMENT' in sheets:
            df_is = sheets['INCOME_STATEMENT']
            for pattern in self.TTM_IS_PATTERNS:
                matched_cols = [c for c in df_is.columns if pattern.lower() in c.lower()
                                and '_TTM' not in c]
                for col in matched_cols:
                    ttm_col = f"{col}_TTM"
                    if ttm_col not in df_is.columns:
                        df_is[ttm_col] = df_is[col].rolling(window=4, min_periods=4).sum()

        # CF: tính TTM
        if 'CASH_FLOW' in sheets:
            df_cf = sheets['CASH_FLOW']
            for pattern in self.TTM_CF_PATTERNS:
                matched_cols = [c for c in df_cf.columns if pattern.lower() in c.lower()
                                and '_TTM' not in c]
                for col in matched_cols:
                    ttm_col = f"{col}_TTM"
                    if ttm_col not in df_cf.columns:
                        df_cf[ttm_col] = df_cf[col].rolling(window=4, min_periods=4).sum()

    def _apply_ttm_all(self):
        """Tính TTM cho tất cả doanh nghiệp đã load."""
        for ticker in self.companies:
            self.calculate_ttm_rolling(ticker)

    def get_ttm_data(self, ticker: str) -> dict[str, pd.DataFrame]:
        """
        Trả về dữ liệu quý kèm cột TTM (dùng cho phân tích BĐS theo quý).
        Lọc bỏ các hàng đầu chưa có đủ 4 quý cho TTM.
        """
        if ticker not in self.companies:
            return {}
        return self.companies[ticker]

    # =================================================================
    # ANNUAL DATA (tổng hợp năm)
    # =================================================================
    def get_annual_data(self, ticker: str) -> dict[str, pd.DataFrame]:
        """
        Tổng hợp dữ liệu quý thành hàng năm.
        - BS: lấy giá trị Q4 (cuối năm) 
        - IS/CF: cộng dồn 4 quý
        """
        if ticker not in self.companies:
            return {}

        annual = {}
        for sheet_name, df in self.companies[ticker].items():
            years = sorted(df['Year'].unique())
            rows = []

            for year in years:
                year_data = df[df['Year'] == year]
                if year_data.empty:
                    continue

                # Loại bỏ cột TTM khi tổng hợp annual (tránh cộng dồn TTM)
                data_cols = [c for c in df.columns
                             if c not in ['Period', 'Year', 'Quarter', 'YearQuarter']
                             and '_TTM' not in c]

                # --- Detect partial year (chưa đủ 4 quý) ---
                quarters_available = sorted(year_data['Quarter'].unique())
                num_quarters = len(quarters_available)
                is_partial = (4 not in quarters_available) or (num_quarters < 4)

                if sheet_name == 'BALANCE_SHEET':
                    # Lấy Q4 (hoặc quý cuối cùng có dữ liệu)
                    q4 = year_data[year_data['Quarter'] == 4]
                    if q4.empty:
                        q4 = year_data.iloc[[-1]]
                    row = q4.iloc[0][data_cols].to_dict()
                else:
                    # IS, CF: cộng dồn các quý có sẵn
                    raw_sum = year_data[data_cols].sum().to_dict()
                    if is_partial and num_quarters > 0:
                        # Annualize: scale lên 4 quý để tránh understate revenue/EBITDA
                        scale = 4 / num_quarters
                        row = {k: v * scale for k, v in raw_sum.items()}
                        print(f"  [{ticker}] ⚠ {year}: partial year {quarters_available} "
                              f"→ IS/CF annualized x{scale:.2f}")
                    else:
                        row = raw_sum

                row['Year'] = year
                row['Is_Partial_Year'] = is_partial
                rows.append(row)

            annual[sheet_name] = pd.DataFrame(rows)

        return annual

    def save_normalized(self, out_dir: str):
        """Lưu dữ liệu đã chuẩn hóa ra CSV."""
        os.makedirs(out_dir, exist_ok=True)

        for ticker, sheets in self.companies.items():
            ticker_dir = os.path.join(out_dir, ticker)
            os.makedirs(ticker_dir, exist_ok=True)

            for sheet_name, df in sheets.items():
                path = os.path.join(ticker_dir, f"{sheet_name}.csv")
                df.to_csv(path, index=False)

            # Cũng lưu annual
            annual = self.get_annual_data(ticker)
            for sheet_name, df in annual.items():
                path = os.path.join(ticker_dir, f"{sheet_name}_ANNUAL.csv")
                df.to_csv(path, index=False)

        print(f"Đã lưu dữ liệu chuẩn hóa vào {out_dir}")


if __name__ == "__main__":
    etl = ETLProcessor("../data/clean")
    etl.load_all()
    etl.save_normalized("../output/1_normalized")
