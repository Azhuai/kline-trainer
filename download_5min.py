#!/usr/bin/env python3
"""
下载A股5分钟K线数据用于日内训练
使用baostock获取数据
"""
import os
import sys
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "5min")
META_FILE = os.path.join(os.path.dirname(__file__), "data", "meta.json")

# 常用股票列表（蓝筹+热门）
DEFAULT_STOCKS = [
    "sh.600000", "sh.600016", "sh.600028", "sh.600030", "sh.600036",
    "sh.600048", "sh.600050", "sh.600104", "sh.600276", "sh.600309",
    "sh.600519", "sh.600585", "sh.600690", "sh.600887", "sh.601012",
    "sh.601088", "sh.601166", "sh.601288", "sh.601318", "sh.601398",
    "sh.601601", "sh.601628", "sh.601668", "sh.601857", "sh.601899",
    "sh.601919", "sh.601985", "sh.601988", "sh.601989", "sh.601998",
    "sz.000001", "sz.000002", "sz.000063", "sz.000100", "sz.000157",
    "sz.000333", "sz.000338", "sz.000425", "sz.000538", "sz.000568",
    "sz.000651", "sz.000725", "sz.000776", "sz.000858", "sz.000895",
    "sz.002027", "sz.002049", "sz.002142", "sz.002230", "sz.002271",
    "sz.002304", "sz.002352", "sz.002415", "sz.002460", "sz.002475",
    "sz.002594", "sz.002607", "sz.002714", "sz.002736", "sz.003816",
    "sz.300059", "sz.300122", "sz.300124", "sz.300750", "sz.300760"
]

def download_5min_data(stock_code, start_from="2026-01-01"):
    """下载单只股票的5分钟K线数据"""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = start_from
    
    rs = bs.query_history_k_data_plus(
        stock_code,
        "date,time,code,open,high,low,close,volume,amount",
        start_date=start_date,
        end_date=end_date,
        frequency="5",
        adjustflag="2"
    )
    
    if rs.error_code != '0':
        print(f"  ❌ {stock_code}: {rs.error_msg}")
        return None
    
    data = []
    while rs.next():
        data.append(rs.get_row_data())
    
    if not data:
        print(f"  ⚠️ {stock_code}: 无数据")
        return None
    
    df = pd.DataFrame(data, columns=rs.fields)
    
    # 保存为CSV
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, f"{stock_code.replace('.', '_')}.csv")
    df.to_csv(filepath, index=False)
    
    print(f"  ✅ {stock_code}: {len(df)} 条记录")
    return len(df)

def download_daily_data(stock_code, years=3):
    """下载日线数据用于趋势训练"""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=years*365)).strftime("%Y-%m-%d")
    
    rs = bs.query_history_k_data_plus(
        stock_code,
        "date,code,open,high,low,close,volume,amount,turn,pctChg",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="2"
    )
    
    if rs.error_code != '0':
        return None
    
    data = []
    while rs.next():
        data.append(rs.get_row_data())
    
    if not data:
        return None
    
    df = pd.DataFrame(data, columns=rs.fields)
    
    # 保存
    daily_dir = os.path.join(os.path.dirname(__file__), "data", "daily")
    os.makedirs(daily_dir, exist_ok=True)
    filepath = os.path.join(daily_dir, f"{stock_code.replace('.', '_')}.csv")
    df.to_csv(filepath, index=False)
    
    return len(df)

def get_stock_name(stock_code):
    """获取股票名称"""
    rs = bs.query_stock_basic(code=stock_code)
    while rs.next():
        row = rs.get_row_data()
        return row[1]  # 股票名称
    return stock_code

def main():
    print("=" * 60)
    print("K线训练数据下载")
    print("=" * 60)
    
    lg = bs.login()
    if lg.error_code != '0':
        print(f"登录失败: {lg.error_msg}")
        sys.exit(1)
    
    stocks = DEFAULT_STOCKS
    print(f"\n准备下载 {len(stocks)} 只股票的数据\n")
    
    # 下载5分钟数据
    print("【1/2】下载5分钟K线数据（从2026-01-01开始）...")
    min5_count = 0
    for i, code in enumerate(stocks):
        print(f"[{i+1}/{len(stocks)}] {code}")
        result = download_5min_data(code, start_from="2026-01-01")
        if result:
            min5_count += 1
    
    # 下载日线数据
    print(f"\n【2/2】下载日线数据（最近3年）...")
    daily_count = 0
    for i, code in enumerate(stocks):
        print(f"[{i+1}/{len(stocks)}] {code}")
        result = download_daily_data(code, years=3)
        if result:
            daily_count += 1
    
    # 保存元数据
    meta = {
        "update_time": datetime.now().isoformat(),
        "stocks_5min": min5_count,
        "stocks_daily": daily_count,
        "stock_list": stocks
    }
    with open(META_FILE, 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    
    bs.logout()
    
    print("\n" + "=" * 60)
    print(f"下载完成！")
    print(f"  5分钟数据: {min5_count} 只股票")
    print(f"  日线数据: {daily_count} 只股票")
    print(f"  数据目录: {os.path.dirname(__file__)}/data/")
    print("=" * 60)

if __name__ == "__main__":
    main()
