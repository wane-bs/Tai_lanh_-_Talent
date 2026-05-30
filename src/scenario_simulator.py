import pandas as pd
import numpy as np

def generate_2026_status_quo(ticker: str, annual: dict, quarterly: dict) -> tuple:
    """
    Tạo dữ liệu báo cáo tài chính giả định năm 2026 từ dữ liệu 2025.
    Giả định: Không thay đổi tình trạng hoạt động (Status Quo), chỉ dựa vào nội suy 3 năm.
    """
    # 1. Dự báo xu hướng CFO 3 năm (2023, 2024, 2025)
    cf_data = annual['CASH_FLOW']
    cfo_col = [c for c in cf_data.columns if 'lưu chuyển tiền thuần từ các hoạt động sản xuất' in c.lower()][0]
    
    cfo_history = cf_data.set_index('Year')[cfo_col].to_dict()
    cfo_2023 = cfo_history.get(2023, -3182e9)
    cfo_2024 = cfo_history.get(2024, -5971e9)
    cfo_2025 = cfo_history.get(2025, -6145e9)
    
    # Nội suy mức tăng thâm hụt (weighted average)
    diff_1 = cfo_2024 - cfo_2023
    diff_2 = cfo_2025 - cfo_2024
    avg_diff = (diff_1 + diff_2) / 2
    cfo_2026_forecast = cfo_2025 + avg_diff
    
    print(f"CFO Trend Extrapolation NVL: 2023({cfo_2023/1e9:.0f}T) -> 2024({cfo_2024/1e9:.0f}T) -> 2025({cfo_2025/1e9:.0f}T)")
    print(f"--> Projected 2026 CFO: {cfo_2026_forecast/1e9:.0f}T")

    # 2. Xây dựng Row giả định cho BALANCE SHEET, INCOME STATEMENT, CASH FLOW
    bs_last = annual['BALANCE_SHEET'].iloc[-1].copy()
    is_last = annual['INCOME_STATEMENT'].iloc[-1].copy()
    cf_last = annual['CASH_FLOW'].iloc[-1].copy()
    
    bs_26 = bs_last.copy()
    is_26 = is_last.copy()
    cf_26 = cf_last.copy()
    
    bs_26['Year'], is_26['Year'], cf_26['Year'] = 2026, 2026, 2026
    if 'Period' in bs_26: bs_26['Period'] = 'Q4 2026'
    if 'Period' in is_26: is_26['Period'] = 'Q4 2026'
    if 'Period' in cf_26: cf_26['Period'] = 'Q4 2026'
    
    # 3. Kéo giá trị CF Mới
    cf_26[cfo_col] = cfo_2026_forecast
    # Tác động làm giảm tiền mặt
    dCash = cfo_2026_forecast
    
    # 4. Hiệu chỉnh BALANCE SHEET tự động cân bằng
    cash_col = [c for c in bs_26.index if 'tương đương tiền' in str(c).lower()][0]
    st_debt_col = [c for c in bs_26.index if ('vay ngắn hạn' in str(c).lower() or 'vay và nợ thuê tài chính ngắn hạn' in str(c).lower())
                   and not any(x in str(c).lower() for x in ['cho vay', 'phải thu'])][0]
    re_col = [c for c in bs_26.index if 'chưa phân phối' in str(c).lower()][0]
    total_assets_col = [c for c in bs_26.index if 'TỔNG CỘNG TÀI SẢN' in str(c) or 'TỔNG TÀI SẢN' in str(c)][0]
    total_liabilities_col = [c for c in bs_26.index if 'NỢ PHẢI TRẢ' in str(c)][0]
    total_capital_col = [c for c in bs_26.index if 'TỔNG CỘNG NGUỒN VỐN' in str(c)][0]
    equity_col = [c for c in bs_26.index if 'VỐN CHỦ SỞ HỮU' in str(c)][0]
    current_liab_col = [c for c in bs_26.index if 'Nợ ngắn hạn' in str(c)][0]
    
    current_cash = bs_26.get(cash_col, 0)
    new_cash = current_cash + dCash
    
    if new_cash < 0:
        shortfall = abs(new_cash)
        bs_26[cash_col] = 0
        bs_26[st_debt_col] = bs_26.get(st_debt_col, 0) + shortfall
        bs_26[total_liabilities_col] = bs_26.get(total_liabilities_col, 0) + shortfall
        bs_26[current_liab_col] = bs_26.get(current_liab_col, 0) + shortfall
        asset_change = -current_cash
    else:
        bs_26[cash_col] = new_cash
        asset_change = dCash
        
    net_income_col = [c for c in is_26.index if 'sau thuế' in str(c).lower() and 'thuần' in str(c).lower()][0]
    net_income = is_26.get(net_income_col, 0)
    
    bs_26[re_col] = bs_26.get(re_col, 0) + net_income
    bs_26[equity_col] = bs_26.get(equity_col, 0) + net_income
    
    bs_26[total_assets_col] = bs_26.get(total_assets_col, 0) + asset_change
    bs_26[total_capital_col] = bs_26.get(total_liabilities_col, 0) + bs_26.get(equity_col, 0)
    bs_26[total_capital_col] = bs_26[total_assets_col] # Force identical balance

    # Annual concats
    annual['BALANCE_SHEET'] = pd.concat([annual['BALANCE_SHEET'], pd.DataFrame([bs_26])], ignore_index=True)
    annual['INCOME_STATEMENT'] = pd.concat([annual['INCOME_STATEMENT'], pd.DataFrame([is_26])], ignore_index=True)
    annual['CASH_FLOW'] = pd.concat([annual['CASH_FLOW'], pd.DataFrame([cf_26])], ignore_index=True)
    
    # Quarterly updates
    if 'CASH_FLOW' in quarterly:
        q_cf = quarterly['CASH_FLOW'].iloc[-1].copy()
        q_cf['Year'] = 2026
        q_cf['Quarter'] = 4
        ttm_cfo_col = [c for c in q_cf.index if 'chuẩn' not in c and '_TTM' in c and 'lưu chuyển tiền thuần' in c.lower()][0]
        q_cf[ttm_cfo_col] = cfo_2026_forecast
        quarterly['CASH_FLOW'] = pd.concat([quarterly['CASH_FLOW'], pd.DataFrame([q_cf])], ignore_index=True)
        
    if 'INCOME_STATEMENT' in quarterly:
        q_is = quarterly['INCOME_STATEMENT'].iloc[-1].copy()
        q_is['Year'] = 2026
        q_is['Quarter'] = 4
        quarterly['INCOME_STATEMENT'] = pd.concat([quarterly['INCOME_STATEMENT'], pd.DataFrame([q_is])], ignore_index=True)
        
    if 'BALANCE_SHEET' in quarterly:
        q_bs = bs_26.copy()
        q_bs['Quarter'] = 4
        quarterly['BALANCE_SHEET'] = pd.concat([quarterly['BALANCE_SHEET'], pd.DataFrame([q_bs])], ignore_index=True)

    return annual, quarterly, cfo_2026_forecast
