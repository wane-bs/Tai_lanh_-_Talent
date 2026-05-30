"""
Streamlit Dashboard — Hệ thống Kiểm soát & Dự báo Rủi ro Phá sản.

5 Tabs:
1. Tổng quan Rủi ro (Heatmap DN × Năm theo PD%)
2. Mô hình Cổ điển (Altman / Beneish / Ohlson / Zmijewski)
3. ML Engine (XGBoost PD%, SHAP, Feature Importance)
4. So sánh Đối chiếu (Classical vs ML)
5. Báo cáo (Auto-generate per company)

Usage:
    streamlit run src/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))

from etl import ETLProcessor
from calculator import BankruptcyCalculator
from feature_engine import FeatureEngine
from model_engine import MLEngine
from risk_classifier import RiskClassifier
from report_generator import ReportGenerator
from credit_model import CreditUnderwriter

# =====================================================================
# PAGE CONFIG
# =====================================================================
st.set_page_config(
    page_title="Hệ thống Dự báo Rủi ro Phá sản",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# CUSTOM CSS
# =====================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .main-header h1 {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        background: linear-gradient(90deg, #f8cdda, #1d2b64);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .main-header p {
        color: #b8b8d0;
        margin: 0.5rem 0 0 0;
        font-size: 0.95rem;
    }

    .risk-card {
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        text-align: center;
        color: white;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        transition: transform 0.2s;
    }
    .risk-card:hover {
        transform: translateY(-2px);
    }
    .risk-card .ticker { font-size: 1.3rem; }
    .risk-card .score { font-size: 2rem; font-weight: 700; }
    .risk-card .label { font-size: 0.85rem; opacity: 0.9; }

    .metric-box {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        padding: 1.2rem;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.08);
        color: white;
        text-align: center;
    }
    .metric-box .value {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-box .label {
        font-size: 0.8rem;
        color: #8899aa;
        margin-top: 0.3rem;
    }

    div[data-testid="stTabs"] button {
        font-weight: 600;
        font-size: 0.95rem;
    }

    .stDataFrame { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# =====================================================================
# STATE MANAGEMENT
# =====================================================================
@st.cache_data(show_spinner="Đang tải dữ liệu...")
def load_pipeline_data(data_dir: str, industry: str = 'DEFAULT'):
    """Chạy ETL + Calculator cho tất cả DN."""
    etl = ETLProcessor(data_dir)
    companies = etl.load_all()

    calc_results = {}
    for ticker in companies:
        annual = etl.get_annual_data(ticker)
        calc = BankruptcyCalculator(annual, ticker, industry=industry)

        # BĐS: truyền dữ liệu quý (có TTM) cho real_estate_metrics()
        quarterly_data = None
        if industry == 'REAL_ESTATE':
            try:
                quarterly_data = etl.get_ttm_data(ticker)
            except Exception:
                pass

        results = calc.run_all(quarterly_data=quarterly_data)
        calc_results[ticker] = results

    return etl, calc_results


@st.cache_data(show_spinner="Đang tải dữ liệu SHAP...")
def load_shap_data(output_dir: str):
    """Tải dữ liệu SHAP đã lưu."""
    path = os.path.join(output_dir, "4_ml_results", "shap_values.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner="Đang xây dựng Feature Matrix...")
def build_features(_etl, _calc_results, industry: str = 'DEFAULT'):
    """Build Feature Matrix."""
    fe = FeatureEngine(industry=industry)
    all_features = []

    for ticker in _etl.companies:
        annual = _etl.get_annual_data(ticker)
        calc_res = _calc_results.get(ticker, {})
        features = fe.transform(annual, calc_res, ticker)
        if not features.empty:
            all_features.append(features)

    if all_features:
        return pd.concat(all_features, ignore_index=True)
    return pd.DataFrame()


@st.cache_resource(show_spinner="Đang tải ML Engine...")
def load_ml_engine(model_dir: str):
    """Load hoặc train ML Engine."""
    engine = MLEngine(model_dir=model_dir)
    try:
        engine.load_model()
        if engine.xgb_model is not None:
            return engine, True
    except Exception:
        pass

    # Train nếu chưa có model
    engine.train_pipeline(top_k_features=10)
    return engine, True


def get_risk_color(level: int) -> str:
    colors = {1: '#2ECC71', 2: '#F1C40F', 3: '#E67E22', 4: '#E74C3C', 5: '#2C3E50'}
    return colors.get(level, '#95A5A6')


def render_composite_metric(ticker_data: pd.DataFrame):
    """Hiển thị biểu ngữ Điểm tổng hợp cho doanh nghiệp."""
    if ticker_data.empty:
        return

    latest = ticker_data.sort_values('Year').iloc[-1]
    ticker = latest.get('Ticker', '')
    score = latest.get('Composite_Score', 0)
    level = int(latest.get('Risk_Level', 0))
    name = latest.get('Risk_VN', '')
    emoji = latest.get('Risk_Emoji', '')

    bg = get_risk_bg(level)

    st.markdown(f"""
    <div style="background: {bg}; padding: 1.5rem; border-radius: 12px; color: white; display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.2);">
        <div>
            <div style="font-size: 0.9rem; opacity: 0.8; text-transform: uppercase; letter-spacing: 1px;">Chỉ số Rủi ro Tổng hợp (Latest)</div>
            <div style="font-size: 2.2rem; font-weight: 800;">{ticker} — {emoji} {name}</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 3rem; font-weight: 900; line-height: 1;">{score:.1f}</div>
            <div style="font-size: 0.8rem; opacity: 0.8;">Composite Score / 100</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def get_risk_bg(level: int) -> str:
    bgs = {
        1: 'linear-gradient(135deg, #11998e, #38ef7d)',
        2: 'linear-gradient(135deg, #F2994A, #F2C94C)',
        3: 'linear-gradient(135deg, #e65c00, #F9D423)',
        4: 'linear-gradient(135deg, #cb2d3e, #ef473a)',
        5: 'linear-gradient(135deg, #232526, #414345)',
    }
    return bgs.get(level, 'linear-gradient(135deg, #bdc3c7, #2c3e50)')


def render_vital_signs_chart(ticker_data: pd.DataFrame, calc_results: dict):
    """
    Biểu đồ Combo hợp nhất các "Chỉ số sinh tử" (Mục 4.6).
    """
    if ticker_data.empty:
        return

    ticker = ticker_data['Ticker'].iloc[0]
    # Lấy 5 năm gần nhất
    years = sorted(ticker_data['Year'].unique())[-5:]
    plot_df = ticker_data[ticker_data['Year'].isin(years)].copy()
    plot_df['Year'] = plot_df['Year'].astype(int)
    plot_df = plot_df.sort_values('Year')

    # Kết hợp dữ liệu BĐS nếu có
    bds_metrics = calc_results.get('bds_metrics', pd.DataFrame())
    if not bds_metrics.empty:
        # Cast Year to int to ensure merge works
        bds_copy = bds_metrics.copy()
        bds_copy['Year'] = bds_copy['Year'].astype(int)
        
        bds_annual = bds_copy[bds_copy['Year'].isin(years)].groupby('Year').last().reset_index()
        
        available_cols = ['Year', 'CFO_TTM', 'leverage_equity_debt', 'interest_coverage_cfo', 'inventory_to_assets']
        actual_cols = [c for c in available_cols if c in bds_annual.columns]
        
        # Merge và ưu tiên lấy dữ liệu từ bds_annual (giá trị thô chưa qua scale)
        merged_df = pd.merge(plot_df, bds_annual[actual_cols], on='Year', how='left', suffixes=('', '_bds'))
        
        # Ưu tiên lấy cột từ bds nếu có overlap
        for col in ['CFO_TTM', 'leverage_equity_debt', 'interest_coverage_cfo', 'inventory_to_assets']:
            bds_col = f"{col}_bds"
            if bds_col in merged_df.columns:
                merged_df[col] = merged_df[bds_col].combine_first(merged_df.get(col, pd.Series([np.nan]*len(merged_df))))
    else:
        merged_df = plot_df
        for col in ['CFO_TTM', 'leverage_equity_debt', 'interest_coverage_cfo', 'inventory_to_assets']:
            if col not in merged_df.columns:
                merged_df[col] = np.nan

    st.markdown(f"#### 🧬 Biểu đồ Hợp nhất Chỉ số sinh tử (Vital Signs Combo) — {ticker}")
    
    # Tạo Figure với trục tung kép
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. CFO TTM (Bars - Secondary Axis)
    # Chia cho 1e9 để ra Tỷ VND đồng bộ với bảng 4.6
    if 'CFO_TTM' in merged_df.columns:
        cfo_values = merged_df['CFO_TTM'].fillna(0)
        cfo_bn = cfo_values / 1e9
    else:
        cfo_bn = pd.Series([0]*len(merged_df))
        
    fig.add_trace(
        go.Bar(
            x=merged_df['Year'], y=cfo_bn, 
            name="Dòng tiền CFO TTM (Tỷ VND)",
            marker_color='rgba(52, 152, 219, 0.5)', 
            hovertemplate='%{y:,.1f} Tỷ VND'
        ),
        secondary_y=True
    )

    # 2. Z-Score (Line - Primary Axis)
    fig.add_trace(
        go.Scatter(
            x=merged_df['Year'], y=merged_df['Z_Score'],
            name="Z''-Score (Hiệu chỉnh BĐS)",
            line=dict(color='#E74C3C', width=5),
            marker=dict(size=12, symbol='diamond'),
            hovertemplate='Z-Score: %{y:.2f}'
        ),
        secondary_y=False
    )

    # 3. Thanh khoản ròng (Line - Primary Axis)
    fig.add_trace(
        go.Scatter(
            x=merged_df['Year'], y=merged_df['wc_ta'],
            name="Thanh khoản ròng (WC_adj/TA)",
            line=dict(color='#2ECC71', width=3, dash='dash'),
            marker=dict(size=8),
            hovertemplate='WC_adj/TA: %{y:.3f}'
        ),
        secondary_y=False
    )

    # 4. ICR (Line - Primary Axis)
    if 'interest_coverage_cfo' in merged_df.columns:
        icr = merged_df['interest_coverage_cfo'].replace([np.inf, -np.inf], np.nan)
        fig.add_trace(
            go.Scatter(
                x=merged_df['Year'], y=icr,
                name="Khả năng trả lãi (ICR - TTM)",
                line=dict(color='#F1C40F', width=3),
                marker=dict(size=6),
                hovertemplate='ICR: %{y:.2f}'
            ),
            secondary_y=False
        )

    # 5. Inventory % (Line - Primary Axis)
    if 'inventory_to_assets' in merged_df.columns:
        inv_tts = merged_df['inventory_to_assets'] * 100
        fig.add_trace(
            go.Scatter(
                x=merged_df['Year'], y=inv_tts,
                name="Tỷ lệ Tồn kho / TTS (%)",
                line=dict(color='#7F8C8D', width=2, dash='dot'),
                marker=dict(size=6),
                hovertemplate='Inventory: %{y:.1f}%'
            ),
            secondary_y=False
        )

    # 6. Đòn bẩy (Line - Primary Axis)
    if 'leverage_equity_debt' in merged_df.columns:
        lev = merged_df['leverage_equity_debt'].replace(np.inf, 10).fillna(0)
        fig.add_trace(
            go.Scatter(
                x=merged_df['Year'], y=lev,
                name="Đòn bẩy (Equity/Total Debt)",
                line=dict(color='#9B59B6', width=2),
                visible='legendonly',
                hovertemplate='Leverage: %{y:.2f}'
            ),
            secondary_y=False
        )

    # Thêm các vùng ngưỡng cho Z-Score
    fig.add_hrect(y0=-5, y1=1.1, fillcolor="red", opacity=0.07, line_width=0, annotation_text="Danger Zone", secondary_y=False)
    fig.add_hrect(y0=1.1, y1=2.6, fillcolor="yellow", opacity=0.05, line_width=0, annotation_text="Watch Zone", secondary_y=False)
    fig.add_hline(y=2.6, line_dash="dash", line_color="#27AE60", opacity=0.8, annotation_text="Safe (2.6)", secondary_y=False)

    # Tinh chỉnh Layout
    fig.update_layout(
        height=600,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"),
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter")
    )

    # Cấu hình trục
    fig.update_xaxes(title_text="Năm Kế Toán", showgrid=False, tickmode='linear')
    fig.update_yaxes(title_text="<b>Chỉ số (Units/%)</b>", secondary_y=False, showgrid=True, gridcolor='rgba(0,0,0,0.05)')
    fig.update_yaxes(title_text="<b>Dòng tiền CFO (Tỷ VND)</b>", secondary_y=True, showgrid=False)

    st.plotly_chart(fig, use_container_width=True)





# =====================================================================
# SIDEBAR
# =====================================================================
def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ Cấu hình")

        base = os.path.join(os.path.dirname(__file__), '..')
        default_dir = os.path.join(base, "data", "companies")
        data_dir = st.text_input("📁 Thư mục dữ liệu", value=default_dir)

        industry = st.selectbox(
            "🏭 Ngành nghề",
            ['DEFAULT', 'RETAIL', 'REAL_ESTATE'],
            index=2, # Mặc định kích hoạt bộ rule cho ngành Bất động sản
            format_func=lambda x: {
                'DEFAULT': '📊 Tổng quát',
                'RETAIL': '🛒 Bán lẻ',
                'REAL_ESTATE': '🏗️ Bất động sản',
            }.get(x, x)
        )

        st.markdown("---")
        st.markdown("### 📖 Hướng dẫn")
        st.markdown("""
        1. Đặt file XLSX (BCTC) vào thư mục `data/companies/`
        2. Mỗi file = 1 doanh nghiệp (sheet: BS, IS, CF)
        3. Chọn ngành nghề phù hợp để kích hoạt luật đánh giá chuyên biệt
        """)

        st.markdown("---")
        st.markdown("### 🏗️ Kiến trúc")
        st.markdown("""
        ```
        ETL → Calculator → Features
              → ML Engine → Risk → Report
        ```
        """)

    return data_dir, industry


# =====================================================================
# DEMO DATA
# =====================================================================
def generate_demo_data():
    """Tạo dữ liệu demo cho 3 doanh nghiệp."""
    np.random.seed(42)
    years = list(range(2019, 2025))

    demo_companies = {
        'HVN': {  # Vietnam Airlines - high risk
            'z_base': 0.8, 'm_base': -1.5, 'pd_base': 55,
            'o_base': 2.5, 'zm_base': 1.2,
        },
        'VCB': {  # Vietcombank - low risk
            'z_base': 3.5, 'm_base': -3.2, 'pd_base': 5,
            'o_base': -2.0, 'zm_base': -3.5,
        },
        'FPT': {  # FPT Corp - medium risk
            'z_base': 2.2, 'm_base': -2.5, 'pd_base': 18,
            'o_base': 0.5, 'zm_base': -1.0,
        },
    }

    all_rows = []
    all_calc = {}

    for ticker, params in demo_companies.items():
        calc_res = {}
        rows_alt, rows_ben, rows_ohl, rows_zm, rows_sl = [], [], [], [], []
        rows_dscr, rows_rw = [], []

        for i, year in enumerate(years):
            noise = np.random.normal(0, 0.1)
            trend = i * 0.05  # slight trend

            z = params['z_base'] + noise + trend * (1 if params['z_base'] > 2 else -0.5)
            m = params['m_base'] + noise * 0.5
            pd_val = max(0, min(100, params['pd_base'] + noise * 10 - trend * 3))
            o = params['o_base'] + noise * 0.3
            zm_x = params['zm_base'] + noise * 0.5

            # Z-Score components
            wc_ta = 0.1 + noise * 0.3
            re_ta = 0.15 + noise * 0.2
            ebit_ta = 0.08 + noise * 0.15
            eq_tl = 0.8 + noise * 0.4

            rows_alt.append({
                'Year': year, 'WC_TA': wc_ta, 'RE_TA': re_ta,
                'EBIT_TA': ebit_ta, 'Equity_TL': eq_tl,
                'Z_Score': z,
                'Zone': 'An toàn' if z > 2.6 else ('Cảnh báo' if z > 1.1 else 'Nguy hiểm')
            })

            if i > 0:
                rows_ben.append({
                    'Year': year,
                    'DSRI': 1.0 + noise * 0.3, 'GMI': 1.0 + noise * 0.2,
                    'AQI': 1.0 + noise * 0.15, 'SGI': 1.05 + noise * 0.1,
                    'DEPI': 1.0, 'SGAI': 1.0 + noise * 0.1,
                    'TATA': noise * 0.05, 'LVGI': 1.0 + noise * 0.1,
                    'M_Score': m,
                    'Manipulation': 'Nghi ngờ' if m > -2.22 else 'Bình thường'
                })

                pd_ohl = 1 / (1 + np.exp(-o)) * 100
                rows_ohl.append({
                    'Year': year, 'O_Score': o,
                    'PD_Ohlson': pd_ohl,
                    'Risk': 'Cao' if pd_ohl > 50 else ('Trung bình' if pd_ohl > 30 else 'Thấp')
                })

                rows_sl.append({
                    'Year': year, 'Sloan_Pct': noise * 15,
                    'Quality': 'Cảnh báo' if abs(noise * 15) > 10 else 'Tốt'
                })

            pd_zm = 1 / (1 + np.exp(-zm_x)) * 100
            rows_zm.append({
                'Year': year, 'Zmijewski_X': zm_x,
                'PD_Zmijewski': pd_zm,
                'Risk': 'Cao' if pd_zm > 50 else ('Trung bình' if pd_zm > 30 else 'Thấp')
            })

            dscr = max(0.3, 1.5 + noise * 0.5 + (0.2 if params['pd_base'] < 20 else -0.3))
            rows_dscr.append({
                'Year': year, 'EBITDA': 1e9 * (1 + noise),
                'Debt_Service': 8e8 * (1 + noise * 0.5),
                'DSCR_Normal': dscr * 1.3, 'DSCR_Stressed': dscr,
                'Coverage': 'An toàn' if dscr > 1.5 else ('Vừa đủ' if dscr > 1.0 else 'Không đủ')
            })

            runway = max(3, 24 + noise * 12 + (12 if params['pd_base'] < 20 else -10))
            rows_rw.append({
                'Year': year, 'Cash': 5e8 * (1 + noise),
                'CFO_Annual': -2e8 * (1 + noise) if params['pd_base'] > 30 else 3e8,
                'Runway_Months': runway if params['pd_base'] > 30 else np.inf,
                'Status': 'Tốt' if runway > 24 else ('Cầm cự' if runway > 6 else 'Nguy hiểm')
            })

            # Feature row
            all_rows.append({
                'Year': year, 'Ticker': ticker,
                'PD_XGBoost': pd_val,
                'Z_Score': z, 'M_Score': m,
                'O_Score': o, 'PD_Ohlson': 1 / (1 + np.exp(-o)) * 100,
                'Zmijewski_X': zm_x, 'PD_Zmijewski': pd_zm,
                'DSCR_Stressed': dscr,
                'wc_ta': wc_ta, 're_ta': re_ta,
                'ebit_ta': ebit_ta, 'bv_eq_tl': eq_tl,
                'ni_ta': 0.05 + noise * 0.1,
                'ca_cl': 1.5 + noise * 0.5,
                'tl_ta': 0.5 + noise * 0.15,
                'cf_td': 0.1 + noise * 0.1,
                'revenue_growth': 0.05 + noise * 0.2,
                'asset_turnover': 0.7 + noise * 0.2,
            })

        calc_res['altman'] = pd.DataFrame(rows_alt)
        calc_res['beneish'] = pd.DataFrame(rows_ben)
        calc_res['ohlson'] = pd.DataFrame(rows_ohl)
        calc_res['zmijewski'] = pd.DataFrame(rows_zm)
        calc_res['sloan'] = pd.DataFrame(rows_sl)
        calc_res['dscr'] = pd.DataFrame(rows_dscr)
        calc_res['runway'] = pd.DataFrame(rows_rw)
        all_calc[ticker] = calc_res

    features_df = pd.DataFrame(all_rows)

    # Classify
    rc = RiskClassifier()
    classified_parts = []
    for ticker in features_df['Ticker'].unique():
        t_df = features_df[features_df['Ticker'] == ticker].copy()
        classified = rc.classify(t_df, all_calc[ticker])
        classified_parts.append(classified)

    classified_df = pd.concat(classified_parts, ignore_index=True)

    return classified_df, all_calc


# =====================================================================
# TAB 1: TỔNG QUAN RỦI RO
# =====================================================================
def render_tab1_overview(classified_df, calc_results):
    st.markdown("### 🗺️ Bản đồ Rủi ro Tổng thể")

    # Sanity check: Ensure PD_XGBoost exists to avoid KeyError
    if 'PD_XGBoost' not in classified_df.columns:
        st.warning("⚠️ Cảnh báo: Không tìm thấy dữ liệu dự báo PD (XGBoost). Vui lòng kiểm tra lại quá trình huấn luyện mô hình.")
        classified_df['PD_XGBoost'] = np.nan

    tickers = sorted(classified_df['Ticker'].unique())

    # Risk cards
    cols = st.columns(min(len(tickers), 4))
    for i, ticker in enumerate(tickers):
        t_data = classified_df[classified_df['Ticker'] == ticker].sort_values('Year')
        latest = t_data.iloc[-1]

        level = int(latest.get('Risk_Level', 0))
        bg = get_risk_bg(level)
        emoji = latest.get('Risk_Emoji', '')
        name = latest.get('Risk_VN', '')
        comp = latest.get('Composite_Score', 0)
        pd_val = latest.get('PD_XGBoost', 0)

        with cols[i % len(cols)]:
            st.markdown(f"""
            <div class="risk-card" style="background: {bg};">
                <div class="ticker">{emoji} {ticker}</div>
                <div class="score">{comp:.0f}</div>
                <div class="label">{name} | PD: {pd_val:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("")

    st.markdown("---")

    # PD Heatmap (DN × Năm)
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("#### 🔥 PD% Heatmap (Doanh nghiệp × Năm)")
        # Kiểm tra nếu tất cả là NaN
        if classified_df['PD_XGBoost'].isna().all():
            st.info("Dữ liệu PD đang trống.")
        else:
            pivot = classified_df.pivot_table(
                values='PD_XGBoost', index='Ticker', columns='Year', aggfunc='first'
            )
            if not pivot.empty:
                fig = px.imshow(
                    pivot.values,
                    x=[str(int(c)) for c in pivot.columns],
                    y=pivot.index.tolist(),
                    color_continuous_scale='RdYlGn_r',
                    aspect='auto',
                    labels=dict(color="PD%"),
                    text_auto='.1f',
                )
                fig.update_layout(
                    height=300, font=dict(family="Inter"),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=20, r=20, t=30, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### 📊 Composite Score Distribution")
        latest_data = classified_df.sort_values('Year').groupby('Ticker').last().reset_index()
        fig = px.bar(
            latest_data.sort_values('Composite_Score', ascending=True),
            x='Composite_Score', y='Ticker',
            orientation='h',
            color='Risk_Level',
            color_continuous_scale='RdYlGn_r',
            text='Composite_Score',
        )
        fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig.update_layout(
            height=300,
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=60, t=30, b=20),
            xaxis=dict(range=[0, 100]),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Trend chart
    st.markdown("#### 📈 Xu hướng PD% theo Thời gian")
    fig = px.line(
        classified_df, x='Year', y='PD_XGBoost',
        color='Ticker', markers=True,
        labels={'PD_XGBoost': 'PD (%)', 'Year': 'Năm'},
    )
    fig.add_hrect(y0=70, y1=100, fillcolor="red", opacity=0.08,
                  annotation_text="Critical", annotation_position="top left")
    fig.add_hrect(y0=40, y1=70, fillcolor="orange", opacity=0.06,
                  annotation_text="Danger")
    fig.add_hrect(y0=20, y1=40, fillcolor="yellow", opacity=0.04)
    fig.add_hrect(y0=0, y1=20, fillcolor="green", opacity=0.04)
    fig.update_layout(
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", y=-0.15),
    )
    st.plotly_chart(fig, use_container_width=True)


# =====================================================================
# TAB 2: MÔ HÌNH CỔ ĐIỂN
# =====================================================================
def render_tab2_classical(classified_df, calc_results, industry='DEFAULT'):
    tickers = sorted(classified_df['Ticker'].unique())
    selected = st.selectbox("🏢 Chọn doanh nghiệp", tickers, key="tab2_ticker")

    if selected not in calc_results:
        st.warning("Không có dữ liệu Calculator cho doanh nghiệp này.")
        return

    cr = calc_results[selected]

    # New: Display Composite Metric
    selected_data = classified_df[classified_df['Ticker'] == selected]
    render_composite_metric(selected_data)

    col1, col2 = st.columns(2)

    # Altman Z-Score
    with col1:
        st.markdown(f"#### 📐 Altman Z''-Score {'(Hiệu chỉnh BĐS)' if industry == 'REAL_ESTATE' else ''}")
        if industry == 'REAL_ESTATE':
            st.latex(r"Z'' = 3.25 + 6.56 \cdot \frac{CA - Inv - CL}{TA} + 3.26 \cdot \frac{RE}{TA} + 6.72 \cdot \frac{EBIT}{TA} + 1.05 \cdot \frac{BVE}{TL}")
            st.info("💡 **X1 (WC/TA)** đã được hiệu chỉnh loại bỏ Hàng tồn kho để phù hợp với đặc thù ngành Bất động sản.")
        else:
            st.latex(r"Z'' = 3.25 + 6.56 \cdot \frac{WC}{TA} + 3.26 \cdot \frac{RE}{TA} + 6.72 \cdot \frac{EBIT}{TA} + 1.05 \cdot \frac{BVE}{TL}")
        
        if 'altman' in cr and not cr['altman'].empty:
            alt = cr['altman']
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=alt['Year'], y=alt['Z_Score'],
                mode='lines+markers+text',
                name='Z-Score',
                text=[f"{z:.2f}" for z in alt['Z_Score']],
                textposition='top center',
                line=dict(color='#3498db', width=3),
                marker=dict(size=10),
            ))
            fig.add_hline(y=2.6, line_dash="dash", line_color="#2ecc71",
                         annotation_text="An toàn (2.6)")
            fig.add_hline(y=1.1, line_dash="dash", line_color="#e74c3c",
                         annotation_text="Nguy hiểm (1.1)")
            fig.add_hrect(y0=2.6, y1=max(alt['Z_Score'].max() + 0.5, 3.5),
                         fillcolor="green", opacity=0.05)
            fig.add_hrect(y0=-1, y1=1.1, fillcolor="red", opacity=0.05)
            fig.update_layout(
                height=350,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=30, b=20),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(alt, use_container_width=True, hide_index=True)
        else:
            st.info("Không có dữ liệu Altman.")

    # Beneish M-Score
    with col2:
        st.markdown("#### 🔎 Beneish M-Score")
        st.latex(r"M = -4.84 + 0.92 \cdot DSRI + 0.528 \cdot GMI + 0.404 \cdot AQI + 0.892 \cdot SGI + 0.115 \cdot DEPI - 0.172 \cdot SGAI + 4.679 \cdot TATA - 0.327 \cdot LVGI")
        if 'beneish' in cr and not cr['beneish'].empty:
            ben = cr['beneish']
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=ben['Year'], y=ben['M_Score'],
                mode='lines+markers+text',
                name='M-Score',
                text=[f"{m:.2f}" for m in ben['M_Score']],
                textposition='top center',
                line=dict(color='#e74c3c', width=3),
                marker=dict(size=10),
            ))
            fig.add_hline(y=-2.22, line_dash="dash", line_color="#f39c12",
                         annotation_text="Ngưỡng cảnh báo (-2.22)")
            fig.add_hrect(y0=-2.22, y1=max(ben['M_Score'].max() + 0.5, 0),
                         fillcolor="red", opacity=0.05)
            fig.update_layout(
                height=350,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=30, b=20),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(ben, use_container_width=True, hide_index=True)
        else:
            st.info("Không có dữ liệu Beneish.")

    st.markdown("---")

    col3, col4 = st.columns(2)

    # Ohlson O-Score
    with col3:
        st.markdown("#### 📉 Ohlson O-Score (PD%)")
        st.latex(r"O = -1.32 - 0.407 \cdot \ln(TA/10^6) + 6.03 \cdot \frac{TL}{TA} - 1.43 \cdot \frac{WC}{TA} + 0.0757 \cdot \frac{CL}{CA} - 1.72 \cdot OENEG - 2.37 \cdot \frac{NI}{TA} - 1.83 \cdot \frac{CFO}{TL} + 0.285 \cdot INTWO - 0.521 \cdot CHIN")
        if 'ohlson' in cr and not cr['ohlson'].empty:
            ohl = cr['ohlson']
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=ohl['Year'], y=ohl['PD_Ohlson'],
                name='PD (Ohlson)',
                marker_color=['#e74c3c' if p > 50 else '#f39c12' if p > 30 else '#2ecc71'
                              for p in ohl['PD_Ohlson']],
                text=[f"{p:.1f}%" for p in ohl['PD_Ohlson']],
                textposition='outside',
            ))
            fig.update_layout(
                height=300,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=30, b=20),
                yaxis=dict(range=[0, 100]),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không có dữ liệu Ohlson.")

    # Zmijewski
    with col4:
        st.markdown("#### 📊 Zmijewski Score (PD%)")
        st.latex(r"X = -4.336 - 4.513 \cdot \frac{NI}{TA} + 5.679 \cdot \frac{TL}{TA} - 0.004 \cdot \frac{CA}{CL}")
        if 'zmijewski' in cr and not cr['zmijewski'].empty:
            zm = cr['zmijewski']
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=zm['Year'], y=zm['PD_Zmijewski'],
                name='PD (Zmijewski)',
                marker_color=['#e74c3c' if p > 50 else '#f39c12' if p > 30 else '#2ecc71'
                              for p in zm['PD_Zmijewski']],
                text=[f"{p:.1f}%" for p in zm['PD_Zmijewski']],
                textposition='outside',
            ))
            fig.update_layout(
                height=300,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=30, b=20),
                yaxis=dict(range=[0, 100]),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Không có dữ liệu Zmijewski.")


# =====================================================================
# TAB 3: ML ENGINE
# =====================================================================
def render_tab3_ml(classified_df, calc_results):
    st.markdown("#### 🤖 Machine Learning — XGBoost Prediction")

    tickers = sorted(classified_df['Ticker'].unique())

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    latest_all = classified_df.sort_values('Year').groupby('Ticker').last()

    with col1:
        avg_pd = latest_all['PD_XGBoost'].mean() if 'PD_XGBoost' in latest_all else 0
        st.markdown(f"""
        <div class="metric-box">
            <div class="value">{avg_pd:.1f}%</div>
            <div class="label">Avg PD (Portfolio)</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        max_pd = latest_all['PD_XGBoost'].max() if 'PD_XGBoost' in latest_all else 0
        st.markdown(f"""
        <div class="metric-box">
            <div class="value">{max_pd:.1f}%</div>
            <div class="label">Max PD</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        critical_count = (latest_all['Risk_Level'] >= 4).sum() if 'Risk_Level' in latest_all else 0
        st.markdown(f"""
        <div class="metric-box">
            <div class="value">{critical_count}</div>
            <div class="label">DN Nguy hiểm</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        safe_count = (latest_all['Risk_Level'] <= 2).sum() if 'Risk_Level' in latest_all else 0
        st.markdown(f"""
        <div class="metric-box">
            <div class="value">{safe_count}</div>
            <div class="label">DN An toàn</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # PD distribution & SHAP
    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.markdown("##### 📊 PD% Distribution by Company")
        fig = go.Figure()
        for ticker in tickers:
            t_df = classified_df[classified_df['Ticker'] == ticker].sort_values('Year')
            fig.add_trace(go.Scatter(
                x=t_df['Year'], y=t_df['PD_XGBoost'],
                name=ticker, mode='lines+markers',
                line=dict(width=3), marker=dict(size=8),
            ))
        fig.add_hline(y=50, line_dash="dot", line_color="red",
                     annotation_text="High Risk")
        fig.update_layout(
            height=380,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", y=-0.15),
            yaxis_title="PD%",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("##### 🎯 SHAP Explanation (Individual)")
        
        # Load SHAP data
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
        shap_data = load_shap_data(output_dir)
        
        if shap_data.empty:
            st.info("Chưa có dữ liệu SHAP. Vui lòng chạy Pipeline trước.")
        else:
            # Select Ticker & Year for SHAP
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                s_ticker = st.selectbox("Chọn DN", tickers, key="shap_ticker")
            with s_col2:
                available_years = sorted(shap_data[shap_data['Ticker'] == s_ticker]['Year'].unique(), reverse=True)
                s_year = st.selectbox("Chọn Năm", available_years, key="shap_year")
            
            # Filter SHAP row
            row = shap_data[(shap_data['Ticker'] == s_ticker) & (shap_data['Year'] == s_year)]
            
            if not row.empty:
                row = row.iloc[0]
                features = [c for c in shap_data.columns if c not in ['Ticker', 'Year', 'Base_Value']]
                
                # Biểu đồ đóng góp (SHAP Waterfall style)
                values = [row[f] for f in features]
                
                # Sort by impact
                impact_df = pd.DataFrame({'Feature': features, 'Impact': values})
                impact_df['Abs_Impact'] = impact_df['Impact'].abs()
                impact_df = impact_df.sort_values('Abs_Impact', ascending=True)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    y=impact_df['Feature'],
                    x=impact_df['Impact'],
                    orientation='h',
                    marker_color=['#e74c3c' if x > 0 else '#2ecc71' for x in impact_df['Impact']],
                    text=[f"{x:+.2f}" for x in impact_df['Impact']],
                    textposition='outside',
                ))
                
                fig.update_layout(
                    height=350,
                    margin=dict(l=20, r=40, t=10, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis_title="Đóng góp vào rủi ro (Log-odds impact)",
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption("🔴 Tăng rủi ro | 🟢 Giảm rủi ro")
            else:
                st.warning("Không tìm thấy dữ liệu cho năm này.")

    # Detailed table
    st.markdown("##### 📋 Chi tiết PD% theo Năm")
    display_cols = ['Ticker', 'Year', 'PD_XGBoost', 'Composite_Score',
                    'Risk_Level', 'Risk_Emoji', 'Risk_VN']
    available = [c for c in display_cols if c in classified_df.columns]
    st.dataframe(
        classified_df[available].sort_values(['Ticker', 'Year']),
        use_container_width=True, hide_index=True,
        height=300
    )


# =====================================================================
# TAB 4: SO SÁNH ĐỐI CHIẾU
# =====================================================================
def render_tab4_comparison(classified_df, calc_results):
    st.markdown("#### ⚖️ Classical vs ML — Đối chiếu Phương pháp")

    tickers = sorted(classified_df['Ticker'].unique())
    selected = st.selectbox("🏢 Chọn doanh nghiệp", tickers, key="tab4_ticker")

    t_data = classified_df[classified_df['Ticker'] == selected].sort_values('Year')
    cr = calc_results.get(selected, {})

    # New: Display Composite Metric
    render_composite_metric(t_data)

    # Multi-model PD comparison
    st.markdown("##### 📉 So sánh PD% giữa các mô hình")

    fig = go.Figure()

    if 'PD_XGBoost' in t_data.columns:
        fig.add_trace(go.Scatter(
            x=t_data['Year'], y=t_data['PD_XGBoost'],
            name='XGBoost PD', mode='lines+markers',
            line=dict(color='#3498db', width=3),
        ))

    if 'PD_Ohlson' in t_data.columns:
        fig.add_trace(go.Scatter(
            x=t_data['Year'], y=t_data['PD_Ohlson'],
            name='Ohlson PD', mode='lines+markers',
            line=dict(color='#e74c3c', width=2, dash='dash'),
        ))

    if 'PD_Zmijewski' in t_data.columns:
        fig.add_trace(go.Scatter(
            x=t_data['Year'], y=t_data['PD_Zmijewski'],
            name='Zmijewski PD', mode='lines+markers',
            line=dict(color='#f39c12', width=2, dash='dot'),
        ))

    fig.update_layout(
        height=400,
        yaxis_title="PD (%)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", y=-0.12),
    )
    st.plotly_chart(fig, use_container_width=True)

    # New: Composite Score Trend
    st.markdown("##### 📈 Xu hướng Điểm tổng hợp (Composite Score History)")
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Scatter(
        x=t_data['Year'], y=t_data['Composite_Score'],
        name='Composite Score', mode='lines+markers+text',
        text=[f"{s:.1f}" for s in t_data['Composite_Score']],
        textposition='top center',
        line=dict(color='#9b59b6', width=4),
        marker=dict(size=10, symbol='diamond'),
    ))
    # Threshold lines for composite
    fig_comp.add_hrect(y0=75, y1=100, fillcolor="#2C3E50", opacity=0.1, annotation_text="Critical")
    fig_comp.add_hrect(y0=55, y1=75, fillcolor="#E74C3C", opacity=0.1, annotation_text="Danger")
    fig_comp.add_hrect(y0=35, y1=55, fillcolor="#E67E22", opacity=0.1, annotation_text="Stress")
    fig_comp.add_hrect(y0=15, y1=35, fillcolor="#F1C40F", opacity=0.1, annotation_text="Watch")
    fig_comp.add_hrect(y0=0, y1=15, fillcolor="#2ECC71", opacity=0.1, annotation_text="Safe")

    fig_comp.update_layout(
        height=350,
        yaxis=dict(range=[0, 100], title="Score"),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(fig_comp, use_container_width=True)

    # Radar chart (latest year)
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("##### 🕸️ Risk Profile Radar (năm mới nhất)")
        latest = t_data.iloc[-1]
        categories = ['Altman Risk', 'Beneish Risk', 'Ohlson PD',
                       'Zmijewski PD', 'ML PD', 'Composite']

        z_risk = max(0, min(100, (2.6 - latest.get('Z_Score', 2.6)) / 1.5 * 100))
        b_risk = max(0, min(100, (latest.get('M_Score', -3) + 2.22) / 0.44 * 100))
        values = [
            z_risk,
            b_risk,
            latest.get('PD_Ohlson', 0),
            latest.get('PD_Zmijewski', 0),
            latest.get('PD_XGBoost', 0),
            latest.get('Composite_Score', 0),
        ]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill='toself',
            fillcolor='rgba(231, 76, 60, 0.15)',
            line=dict(color='#e74c3c', width=2),
            marker=dict(size=8),
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            height=350,
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=40, r=40, t=30, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("##### 📊 Model Agreement Matrix")
        models_agree = pd.DataFrame()
        for _, row in t_data.iterrows():
            year = int(row['Year'])
            agree_row = {'Year': year}

            # Each model's verdict: High/Low risk
            agree_row['XGBoost'] = '🔴' if row.get('PD_XGBoost', 0) > 40 else '🟢'
            agree_row['Ohlson'] = '🔴' if row.get('PD_Ohlson', 0) > 50 else '🟢'
            agree_row['Zmijewski'] = '🔴' if row.get('PD_Zmijewski', 0) > 50 else '🟢'
            agree_row['Altman'] = '🔴' if row.get('Z_Score', 3) < 1.1 else '🟢'
            agree_row['Beneish'] = '🔴' if row.get('M_Score', -3) > -2.22 else '🟢'

            models_agree = pd.concat([models_agree, pd.DataFrame([agree_row])],
                                     ignore_index=True)

        st.dataframe(models_agree, use_container_width=True, hide_index=True)
        st.caption("🟢 = An toàn | 🔴 = Rủi ro cao")


# =====================================================================
# TAB 5: BÁO CÁO
# =====================================================================
def render_tab5_report(classified_df, calc_results, industry='DEFAULT'):
    st.markdown("#### 📝 Báo cáo Tự động")

    tickers = sorted(classified_df['Ticker'].unique())

    col1, col2 = st.columns([1, 3])

    with col1:
        selected = st.radio("🏢 Chọn DN", tickers, key="tab5_ticker")
        report_type = st.radio(
            "📄 Loại báo cáo",
            ["Chi tiết DN", "So sánh tổng hợp"]
        )

    with col2:
        rg = ReportGenerator()

        if report_type == "Chi tiết DN":
            cr = calc_results.get(selected, {})
            # Thêm biểu đồ Chỉ số sinh tử ngay trên báo cáo
            render_vital_signs_chart(
                classified_df[classified_df['Ticker'] == selected],
                cr
            )
            
            report_md = rg.generate_company_report(
                selected, classified_df, cr, industry=industry
            )
        else:
            report_md = rg.generate_comparison_report(classified_df)

        st.markdown(report_md)


        # Download button
        st.download_button(
            label="⬇️ Tải báo cáo (.md)",
            data=report_md,
            file_name=f"report_{selected}.md",
            mime="text/markdown",
        )


# =====================================================================
# TAB 6: PHÂN TÍCH BĐS
# =====================================================================
def render_tab6_bds(classified_df, calc_results):
    st.markdown("#### 🏗️ Phân tích Chuyên biệt Bất động sản")

    # Kiểm tra có dữ liệu BĐS không
    has_bds = any('bds_metrics' in cr and not cr.get('bds_metrics', pd.DataFrame()).empty
                  for cr in calc_results.values())
    if not has_bds:
        st.info("📝 Không có dữ liệu BĐS. Vui lòng chọn ngành 'Bất động sản' trong Sidebar để kích hoạt.")
        return

    tickers = sorted(classified_df['Ticker'].unique())
    selected = st.selectbox("🏢 Chọn doanh nghiệp", tickers, key="tab6_ticker")

    if selected not in calc_results or 'bds_metrics' not in calc_results[selected]:
        st.warning("Không có dữ liệu BĐS cho doanh nghiệp này.")
        return

    bds = calc_results[selected]['bds_metrics']
    if bds.empty:
        st.warning("Dữ liệu BĐS trống.")
        return

    periods = bds['Period'].astype(str).values

    col1, col2 = st.columns(2)

    # Chart 1: Cơ cấu Tài sản (Stacked Bar)
    with col1:
        st.markdown("##### 📦 Cơ cấu Tài sản (Khối u Kế toán)")
        inv_pct = (bds['inventory_to_assets'] * 100).values
        recv_pct = np.where(
            bds['Total_Assets'] > 0,
            bds['Receivables'] / bds['Total_Assets'] * 100,
            0
        )
        other_pct = 100 - inv_pct - recv_pct

        fig = go.Figure()
        fig.add_trace(go.Bar(x=periods, y=inv_pct, name='Tồn Kho (%)',
                             marker_color='#FF6B6B'))
        fig.add_trace(go.Bar(x=periods, y=recv_pct, name='Phải Thu (%)',
                             marker_color='#4ECDC4'))
        fig.add_trace(go.Bar(x=periods, y=other_pct, name='Tài sản Khác',
                             marker_color='#E0E0E0'))
        fig.update_layout(
            barmode='stack', height=350,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=30, b=20),
            yaxis_title="% Tổng tài sản",
            legend=dict(orientation="h", y=-0.15),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Chart 2: Lợi nhuận Kế toán vs Dòng tiền CFO
    with col2:
        st.markdown("##### 💰 Lợi nhuận Kế toán vs Dòng tiền TTM")
        # Lấy Lợi nhuận từ sloan nếu có
        cfo_ttm = bds['CFO_TTM'].values / 1e9

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=periods, y=cfo_ttm,
            name='CFO TTM (Tỷ VND)',
            marker_color=['#e74c3c' if v < 0 else '#2ecc71' for v in cfo_ttm],
        ))
        fig2.add_trace(go.Scatter(
            x=periods,
            y=bds['Interest_TTM'].values / 1e9,
            name='Chi phí lãi vay TTM',
            mode='lines+markers',
            line=dict(color='#e67e22', width=3),
        ))
        fig2.add_hline(y=0, line_dash="dash", line_color="black")
        fig2.update_layout(
            height=350,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=30, b=20),
            yaxis_title="Tỷ VND",
            legend=dict(orientation="h", y=-0.15),
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    col3, col4 = st.columns(2)

    # Chart 3: Interest Coverage CFO
    with col3:
        st.markdown("##### ⚠️ Khả năng Trả lãi (Interest Coverage CFO)")
        int_cov = bds['interest_coverage_cfo'].replace([np.inf, -np.inf], np.nan).values
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=periods, y=int_cov,
            mode='lines+markers',
            name='Interest Coverage',
            line=dict(color='#9b59b6', width=3),
            marker=dict(size=8),
        ))
        fig3.add_hline(y=1.0, line_dash="dash", line_color="red",
                       annotation_text="Ngưỡng nguy hiểm (1.0)")
        fig3.update_layout(
            height=300,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Chart 4: Runway Interest
    with col4:
        st.markdown("##### ⏱️ Runway Trả Lãi (Quý cầm cự)")
        runway = bds['runway_interest'].replace([np.inf, -np.inf], np.nan).values
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(
            x=periods, y=runway,
            name='Runway (Quý)',
            marker_color=['#e74c3c' if (r is not None and not np.isnan(r) and r < 1)
                          else '#f39c12' if (r is not None and not np.isnan(r) and r < 4)
                          else '#2ecc71'
                          for r in runway],
        ))
        fig4.add_hline(y=1.0, line_dash="dash", line_color="red",
                       annotation_text="Critical (< 1 Quý)")
        fig4.update_layout(
            height=300,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig4, use_container_width=True)

    # Chi tiết table
    st.markdown("##### 📋 Dữ liệu Chi tiết BĐS")
    display_cols = ['Period', 'inventory_to_assets', 'receivables_to_revenue',
                    'cfo_to_short_debt', 'interest_coverage_cfo', 'runway_interest',
                    'CFO_TTM', 'Interest_TTM', 'Cash']
    available = [c for c in display_cols if c in bds.columns]
    st.dataframe(bds[available], use_container_width=True, hide_index=True)


# =====================================================================
# TAB 7: ĐỊNH MỨC TÍN DỤNG
# =====================================================================
def render_tab7_credit(classified_df, calc_results, etl, industry='DEFAULT'):
    st.markdown("### 🏦 Định mức Tín dụng (Credit Sizing)")
    
    tickers = sorted(classified_df['Ticker'].unique())
    selected = st.selectbox("🏢 Chọn doanh nghiệp", tickers, key="tab7_ticker")
    
    # Extract data for selected ticker
    t_df = classified_df[classified_df['Ticker'] == selected].sort_values('Year')
    if t_df.empty:
        return
    latest = t_df.iloc[-1]
    year = int(latest['Year'])
    
    # AI variables
    pd_xgboost = latest.get('PD_XGBoost', 0.0)
    risk_level = latest.get('Risk_Level', 1)
    composite_score = latest.get('Composite_Score', 0.0)
    
    # -------------------------------------------------------------
    # CASH FLOW CREDIT SCORECARD INTEGRATION
    # -------------------------------------------------------------
    st.markdown("#### 💳 Điểm Tín dụng Dòng tiền (Cash Flow Scorecard - BCTC)")
    
    from cash_flow_scorer import BCTCCashFlowScorer
    cf_scorer = BCTCCashFlowScorer()
    
    cf_metrics = cf_scorer.calculate_metrics(selected, etl)
    cf_score, cf_details = cf_scorer.compute_score(cf_metrics)
    cf_grade, cf_decision, cf_color = cf_scorer.get_decision(cf_score)
    
    # 2-column layout: Score Card & Radar Chart
    score_col1, score_col2 = st.columns([1, 1])
    
    with score_col1:
        st.markdown(f"""
        <div style="background-color: #1e293b; padding: 25px; border-radius: 8px; border: 2px solid {cf_color}; height: 350px; display: flex; flex-direction: column; justify-content: center;">
            <div style="font-size: 0.9em; text-transform: uppercase; color: #94a3b8; font-weight: bold; letter-spacing: 0.05em;">Credit Score</div>
            <div style="font-size: 3em; font-weight: bold; color: {cf_color}; margin: 10px 0;">{cf_score} <span style="font-size: 0.45em; color: #94a3b8; font-weight: normal;">/ 1000</span></div>
            <div style="font-size: 1.5em; font-weight: bold; color: white; margin-bottom: 10px;">{cf_grade}</div>
            <div style="font-size: 0.95em; color: #cbd5e1; font-style: italic; line-height: 1.4;">🤖 <strong>Khuyến nghị của AI:</strong> {cf_decision}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with score_col2:
        # Normalized values (0-100) for Radar Plot
        norm_points = cf_scorer.get_normalized_points(cf_details)
        categories = [
            'Chất lượng doanh thu',
            'Khả năng trả nợ (DSCR)',
            'Đệm thanh khoản',
            'Độ ổn định doanh thu',
            'Cấu trúc đòn bẩy',
            'Xu hướng dòng tiền'
        ]
        
        # Close the loop for plotting
        norm_points_plot = norm_points + [norm_points[0]]
        categories_plot = categories + [categories[0]]
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=norm_points_plot,
            theta=categories_plot,
            fill='toself',
            name=selected,
            line_color=cf_color,
            fillcolor=cf_color,
            opacity=0.3
        ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    color='#475569',
                    gridcolor='#334155'
                ),
                angularaxis=dict(
                    color='#cbd5e1',
                    gridcolor='#334155'
                ),
                bgcolor='rgba(0,0,0,0)'
            ),
            showlegend=False,
            height=350,
            margin=dict(l=80, r=80, t=30, b=30),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_radar, use_container_width=True)
        
    with st.expander("🔍 Chi tiết bảng chấm điểm 6 chỉ tiêu dòng tiền", expanded=False):
        data_rows = []
        for key, vn_name in [
            ('cash_to_revenue', 'Chất lượng doanh thu (Cash-to-Revenue)'),
            ('dscr', 'Khả năng trả nợ (DSCR CFO-based)'),
            ('cash_buffer_days', 'Đệm thanh khoản (Cash Buffer Days)'),
            ('revenue_volatility', 'Độ ổn định doanh thu (Volatility CV)'),
            ('equity_to_debt', 'Cấu trúc đòn bẩy (Equity/Debt)'),
            ('cfo_growth_yoy', 'Xu hướng dòng tiền (CFO Growth YoY)')
        ]:
            detail = cf_details[key]
            val = detail['value']
            pts = detail['points']
            lbl = detail['label']
            
            if pd.isna(val):
                val_str = "N/A"
            elif key in ['cash_to_revenue', 'revenue_volatility', 'cfo_growth_yoy']:
                val_str = f"{val*100:.2f}%"
            elif key in ['dscr', 'equity_to_debt']:
                val_str = f"{val:.2f}x"
            else:
                val_str = f"{val:.1f} ngày"
                
            data_rows.append({
                'Chỉ tiêu': vn_name,
                'Giá trị thực tế': val_str,
                'Điểm thành phần': f"{pts:+.0f}",
                'Phân hạng đánh giá': lbl
            })
        st.dataframe(pd.DataFrame(data_rows), use_container_width=True, hide_index=True)
        
    # Circuit Breaker Logic
    is_blocked = (cf_grade == "Grade D")
    override = False
    if is_blocked:
        st.error(f"❌ **CẢNH BÁO HỆ THỐNG:** Doanh nghiệp có điểm tín dụng dòng tiền quá thấp ({cf_score} điểm - {cf_grade}). Khuyến nghị hệ thống: **TỪ CHỐI CẤP HẠN MỨC**.")
        override = st.checkbox("⚠️ Bỏ qua chốt chặn và tiếp tục thẩm định thủ công (Manual Override)", value=False, key="tab7_override")
        
    st.markdown("---")
    
    cr = calc_results.get(selected, {})
    
    # Get necessary inputs
    cfo_ttm = latest.get('CFO_TTM', np.nan)
    if 'bds_metrics' in cr and not cr['bds_metrics'].empty:
        bds = cr['bds_metrics']
        b_y = bds[bds['Year'] == year]
        if not b_y.empty:
            cfo_ttm = b_y.iloc[-1].get('CFO_TTM', cfo_ttm)
            icr = b_y.iloc[-1].get('interest_coverage_cfo', np.nan)
            inv_ta = b_y.iloc[-1].get('inventory_to_assets', np.nan)
        else:
            icr = np.nan
            inv_ta = np.nan
    else:
        icr = np.nan
        inv_ta = np.nan

    wc_ta = latest.get('wc_ta', np.nan)
    
    # Extract Equity and Total Debt from raw annual data
    annual = etl.get_annual_data(selected)
    bs = annual.get('BALANCE_SHEET', pd.DataFrame())
    bs_year = bs[bs['Year'] == year]
    if not bs_year.empty:
        def _col(df, pat):
            for c in df.columns:
                if pat.lower() in c.lower():
                    return pd.to_numeric(df[c], errors='coerce').fillna(0.0).iloc[0]
            return 0.0
        equity = _col(bs_year, 'VỐN CHỦ SỞ HỮU')
        total_debt = _col(bs_year, 'NỢ PHẢI TRẢ')
    else:
        equity = 0.0
        total_debt = 0.0
        
    equity_debt = equity / total_debt if total_debt > 0 else np.nan
    
    # Inputs on UI
    st.markdown("#### ⚙️ Giả định Vay vốn")
    col1, col2 = st.columns(2)
    with col1:
        rate = st.slider("Lãi suất cho vay (%/năm)", min_value=1.0, max_value=25.0, value=10.0, step=0.5) / 100
    with col2:
        tenor = st.slider("Kỳ hạn vay (Năm)", min_value=1, max_value=20, value=5, step=1)
        
    cu = CreditUnderwriter()
    res = cu.calculate_capacity(
        cfo_ttm=cfo_ttm, icr=icr, inventory_ta=inv_ta, equity_debt=equity_debt,
        wc_ta=wc_ta, equity=equity, total_debt=total_debt, rate=rate, tenor=tenor,
        pd_xgboost=pd_xgboost, risk_level=risk_level, composite_score=composite_score
    )
    
    # Apply Credit Score Circuit Breaker
    if is_blocked and not override:
        res['Status'] = "Từ chối"
        res['L_final'] = 0.0
        if "Từ chối cấp hạn mức tín dụng do Điểm tín dụng dòng tiền quá thấp (Grade D)" not in res['Warnings']:
            res['Warnings'].append("Từ chối cấp hạn mức tín dụng do Điểm tín dụng dòng tiền quá thấp (Grade D)")
    
    st.markdown("#### 📈 Kết quả Định mức")
    
    if res.get('AI_Impact', 'Không') != "Không":
        st.info(f"🤖 **Tác động của AI (XGBoost PD: {pd_xgboost:.1f}%):** {res['AI_Impact']}")
    
    # Metrics
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="value">{res['Target_DSCR']:.2f}x</div>
            <div class="label">Target DSCR</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-box">
            <div class="value">{res['PMT_max']/1e9:,.1f} Tỷ</div>
            <div class="label">Mức trả nợ tối đa/năm</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        color = "#2ecc71" if res['Status'] == "Khả thi" else ("#f39c12" if "Haircut" in res['Status'] else "#e74c3c")
        st.markdown(f"""
        <div class="metric-box" style="border: 2px solid {color};">
            <div class="value" style="color: {color}; -webkit-text-fill-color: {color};">{res['L_final']/1e9:,.1f} Tỷ</div>
            <div class="label">Hạn mức khả thi (L_max)</div>
        </div>
        """, unsafe_allow_html=True)
        
    if res['Warnings']:
        for w in res['Warnings']:
            st.warning(w)
            
    # Chart
    st.markdown("#### 📉 Độ nhạy Hạn mức theo biến thiên Lãi suất (±10%)")
    rates = np.linspace(max(0.01, rate - 0.1), rate + 0.1, 21)
    curve = cu.generate_sensitivity_curve({
        'cfo_ttm': cfo_ttm, 'icr': icr, 'inventory_ta': inv_ta, 
        'equity_debt': equity_debt, 'wc_ta': wc_ta, 'equity': equity, 
        'total_debt': total_debt, 'tenor': tenor,
        'pd_xgboost': pd_xgboost, 'risk_level': risk_level, 'composite_score': composite_score
    }, rates)
    
    curve_df = pd.DataFrame(curve)
    curve_df['Rate'] = curve_df['Rate'] * 100
    curve_df['L_final'] = curve_df['L_final'] / 1e9
    
    fig = px.line(curve_df, x='Rate', y='L_final', markers=True,
                  labels={'Rate': 'Lãi suất (%)', 'L_final': 'Hạn mức (Tỷ VND)'})
    fig.add_vline(x=rate*100, line_dash="dash", line_color="red", annotation_text="Lãi suất chọn")
    fig.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

    # Lập lịch trả nợ & Đề xuất AI
    st.markdown("---")
    st.markdown("#### 📅 Kế hoạch Trả nợ & Đề xuất AI")
    
    l_final = res.get('L_final', 0.0)
    
    # Lấy ý kiến khuyến nghị từ AI
    recomm = cu.recommend_repayment_method(
        risk_level=risk_level,
        dscr=res.get('Target_DSCR', 1.2),
        inventory_ta=inv_ta,
        industry=industry
    )
    
    # Tính toán lịch cho cả 2 phương án
    schedule_annuity = cu.generate_repayment_schedule(l_final, rate, tenor, "annuity")
    schedule_eq_principal = cu.generate_repayment_schedule(l_final, rate, tenor, "equal_principal")
    
    # Hiển thị đề xuất AI
    reasons_list = "".join([f"<li>{r}</li>" for r in recomm['Reasons']])
    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border-left: 5px solid #3498db; margin-bottom: 20px;">
        <h5 style="color: #3498db; margin: 0 0 10px 0;">🤖 Đề xuất Phương thức Trả nợ của AI</h5>
        <p style="margin: 0; font-size: 1.05em; color: white;">Phương án tối ưu: <strong>{recomm['Method_VN']}</strong></p>
        <ul style="margin: 10px 0 0 0; padding-left: 20px; font-size: 0.95em; color: #cbd5e1;">
            {reasons_list}
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    if l_final > 0:
        # Lựa chọn hiển thị
        method_opt = st.radio(
            "Chọn phương thức hiển thị lịch trả nợ:",
            ["Niên kim đều (Equal Annual Payment)", "Gốc đều, lãi giảm dần (Equal Principal Payment)"],
            index=0 if recomm['Method'] == "annuity" else 1
        )
        
        chosen_method = "annuity" if "Niên kim" in method_opt else "equal_principal"
        active_schedule = schedule_annuity if chosen_method == "annuity" else schedule_eq_principal
        
        # Hiển thị tóm tắt so sánh
        tot_annuity = sum([x['Interest_Paid'] for x in schedule_annuity])
        tot_eq = sum([x['Interest_Paid'] for x in schedule_eq_principal])
        saving = tot_annuity - tot_eq
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown(f"**Tổng lãi phải trả (Niên kim đều):** `{tot_annuity/1e9:,.3f}` Tỷ VND")
            st.markdown(f"**Tổng lãi phải trả (Gốc đều):** `{tot_eq/1e9:,.3f}` Tỷ VND")
        with col_c2:
            if saving > 0:
                st.success(f"💡 Phương án Gốc đều giúp tiết kiệm **{saving/1e9:,.3f} Tỷ VND** tiền lãi vay so với Niên kim!")
            elif saving < 0:
                st.success(f"💡 Phương án Niên kim giúp tiết kiệm **{-saving/1e9:,.3f} Tỷ VND** tiền lãi vay so với Gốc đều!")
            else:
                st.info("💡 Không có chênh lệch lãi vay.")
                
        # Biểu đồ Plotly
        sched_df = pd.DataFrame(active_schedule)
        fig_repay = go.Figure()
        fig_repay.add_trace(go.Bar(
            x=sched_df['Year'], y=sched_df['Principal_Paid']/1e9,
            name='Trả gốc (Tỷ VND)', marker_color='#2ecc71'
        ))
        fig_repay.add_trace(go.Bar(
            x=sched_df['Year'], y=sched_df['Interest_Paid']/1e9,
            name='Trả lãi (Tỷ VND)', marker_color='#e74c3c'
        ))
        fig_repay.update_layout(
            barmode='stack',
            height=350,
            title=f"Cơ cấu Trả gốc và Lãi qua các năm ({'Niên kim đều' if chosen_method == 'annuity' else 'Gốc đều'})",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title="Năm",
            yaxis_title="Tỷ VND",
            legend=dict(orientation="h", y=-0.15),
        )
        st.plotly_chart(fig_repay, use_container_width=True)
        
        # Bảng lịch trả nợ chi tiết
        st.markdown("##### 📋 Lịch trình trả nợ chi tiết")
        disp_df = sched_df.copy()
        disp_df['Beginning_Balance'] = disp_df['Beginning_Balance'] / 1e9
        disp_df['Payment'] = disp_df['Payment'] / 1e9
        disp_df['Principal_Paid'] = disp_df['Principal_Paid'] / 1e9
        disp_df['Interest_Paid'] = disp_df['Interest_Paid'] / 1e9
        disp_df['Ending_Balance'] = disp_df['Ending_Balance'] / 1e9
        
        disp_df.columns = ['Năm', 'Dư nợ đầu kỳ (Tỷ)', 'Tổng trả (Tỷ)', 'Trả gốc (Tỷ)', 'Trả lãi (Tỷ)', 'Dư nợ cuối kỳ (Tỷ)']
        st.dataframe(disp_df.round(3), use_container_width=True, hide_index=True)
        
        # Báo cáo tự động sinh
        st.markdown("---")
        st.markdown("#### 📝 Báo cáo Thẩm định Tín dụng & Phương án Trả nợ Tự động")
        
        from report_generator import ReportGenerator
        rg = ReportGenerator()
        
        report_md = rg.generate_credit_report(
            ticker=selected,
            latest_year_data=latest,
            credit_res=res,
            schedule_annuity=schedule_annuity,
            schedule_eq_principal=schedule_eq_principal,
            recommendation=recomm,
            rate=rate,
            tenor=tenor,
            industry=industry,
            score=cf_score,
            score_details=cf_details
        )
        
        with st.expander("🔍 Xem nội dung Báo cáo chi tiết", expanded=False):
            st.markdown(report_md)
            
        st.download_button(
            label="⬇️ Tải Báo cáo Thẩm định Tín dụng (.md)",
            data=report_md,
            file_name=f"credit_report_{selected}.md",
            mime="text/markdown",
            key=f"dl_credit_{selected}"
        )
    else:
        st.error("Doanh nghiệp bị từ chối cấp tín dụng. Không thể lập kế hoạch trả nợ.")


# =====================================================================
# MAIN
# =====================================================================
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📊 Hệ thống Kiểm soát & Dự báo Rủi ro Phá sản</h1>
        <p>Bankruptcy Risk Monitoring & Prediction System — Hybrid Classical + ML Engine</p>
    </div>
    """, unsafe_allow_html=True)

    data_dir, industry = render_sidebar()

    # Load data
    if not os.path.isdir(data_dir):
        st.error(f"Thư mục không tồn tại: {data_dir}")
        return

    try:
        etl, calc_results = load_pipeline_data(data_dir, industry=industry)
        features_df = build_features(etl, calc_results, industry=industry)

        if features_df.empty:
            st.warning("Không tìm thấy dữ liệu BCTC hợp lệ trong thư mục chỉ định.")
            return

        # ML predict
        model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        ml_engine, _ = load_ml_engine(model_dir)
        features_df = ml_engine.predict(features_df)

        # Classify
        rc = RiskClassifier(industry=industry)
        classified_parts = []
        for ticker in features_df['Ticker'].unique():
            t_df = features_df[features_df['Ticker'] == ticker].copy()
            cr = calc_results.get(ticker, {})
            classified = rc.classify(t_df, cr)
            classified_parts.append(classified)
        classified_df = pd.concat(classified_parts, ignore_index=True)

    except Exception as e:
        st.error(f"Lỗi xử lý dữ liệu: {e}")
        return

    # Tabs
    tabs = [
        "🗺️ Tổng quan Rủi ro",
        "📐 Mô hình Cổ điển",
        "🤖 ML Engine",
        "⚖️ So sánh Đối chiếu",
        "📝 Báo cáo",
    ]
    if industry == 'REAL_ESTATE':
        tabs.append("🏗️ Phân tích BĐS")
        
    tabs.append("🏦 Định mức Tín dụng")

    tab_objects = st.tabs(tabs)

    with tab_objects[0]:
        render_tab1_overview(classified_df, calc_results)
    with tab_objects[1]:
        render_tab2_classical(classified_df, calc_results, industry)
    with tab_objects[2]:
        render_tab3_ml(classified_df, calc_results)
    with tab_objects[3]:
        render_tab4_comparison(classified_df, calc_results)
    with tab_objects[4]:
        render_tab5_report(classified_df, calc_results, industry)

    if industry == 'REAL_ESTATE' and len(tab_objects) >= 6:
        with tab_objects[5]:
            render_tab6_bds(classified_df, calc_results)
        with tab_objects[6]:
            render_tab7_credit(classified_df, calc_results, etl, industry=industry)
    else:
        with tab_objects[5]:
            render_tab7_credit(classified_df, calc_results, etl, industry=industry)


if __name__ == "__main__":
    main()
