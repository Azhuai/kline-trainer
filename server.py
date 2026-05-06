#!/usr/bin/env python3
"""
K线训练系统 - 使用Qlib离线数据
修复版：所有数值保留2位小数
"""
import os
import json
import random
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse as urlparse
import pandas as pd
import numpy as np

QLIB_DIR = os.path.expanduser("~/.qlib/qlib_data/cn_data/stock")
LEADERBOARD_FILE = os.path.join(os.path.dirname(__file__), "data", "leaderboard.json")

def r2(x):
    """保留2位小数"""
    if pd.isna(x) or x is None:
        return 0.0
    return round(float(x), 2)

def calc_ma(series, window):
    """移动平均线"""
    return series.rolling(window=window, min_periods=1).mean().apply(r2)

def calc_ema(series, span):
    """指数移动平均"""
    return series.ewm(span=span, adjust=False).mean().apply(r2)

def calc_macd(close, fast=12, slow=26, signal=9):
    """MACD"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = (ema_fast - ema_slow).apply(r2)
    dea = dif.ewm(span=signal, adjust=False).mean().apply(r2)
    macd = ((dif - dea) * 2).apply(r2)
    return dif, dea, macd

def calc_kdj(high, low, close, n=9, m1=3, m2=3):
    """KDJ"""
    lowest_low = low.rolling(window=n, min_periods=1).min()
    highest_high = high.rolling(window=n, min_periods=1).max()
    rsv = ((close - lowest_low) / (highest_high - lowest_low) * 100).fillna(50)
    
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = (3 * k - 2 * d)
    
    return k.apply(r2), d.apply(r2), j.apply(r2)

def calc_dma(close, short=10, long=50, m=10):
    """DMA"""
    dma = (calc_ma(close, short) - calc_ma(close, long)).apply(r2)
    ama = calc_ma(dma, m).apply(r2)
    return dma, ama

def get_stock_list():
    """获取所有可用股票"""
    stocks = []
    for market in ['sh', 'sz']:
        market_dir = os.path.join(QLIB_DIR, market)
        if os.path.exists(market_dir):
            for code in os.listdir(market_dir):
                csv_path = os.path.join(market_dir, code, f"{code}.csv")
                if os.path.exists(csv_path):
                    stocks.append({"code": f"{market}.{code}", "market": market, "name": code})
    return stocks

    # 加载股票**日 K 线**数据
def load_stock_data(code):
    """加载股票日线数据"""
    parts = code.split('.')
    if len(parts) != 2:
        return None
    market, stock_code = parts
    csv_path = os.path.join(QLIB_DIR, market, stock_code, f"{stock_code}.csv")
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['close'])
    df = df[df['volume'] > 0]
    df = df.sort_values('date').reset_index(drop=True)
    return df

def get_training_data(code, start_idx, length):
    """获取训练数据（带技术指标）"""
    df = load_stock_data(code)
    if df is None or len(df) < start_idx + length + 1:
        return None
    
    # 截取数据段（多取60根用于计算指标）
    seg_start = max(0, start_idx - 60)
    segment = df.iloc[seg_start:start_idx+length].copy().reset_index(drop=True)
    
    close = segment['close']
    high = segment['high']
    low = segment['low']
    
    # 计算指标
    segment['ma5'] = calc_ma(close, 5)
    segment['ma10'] = calc_ma(close, 10)
    segment['ma20'] = calc_ma(close, 20)
    segment['ma30'] = calc_ma(close, 30)
    
    dif, dea, macd = calc_macd(close)
    segment['macd_dif'] = dif
    segment['macd_dea'] = dea
    segment['macd_bar'] = macd
    
    k, d, j = calc_kdj(high, low, close)
    segment['kdj_k'] = k
    segment['kdj_d'] = d
    segment['kdj_j'] = j
    
    dma, ama = calc_dma(close)
    segment['dma'] = dma
    segment['dma_ama'] = ama
    
    # 只返回后半部分
    result = segment.iloc[60:].copy().reset_index(drop=True)
    result = result.fillna(0)
    
    # 确保所有数值2位小数
    num_cols = ['open', 'high', 'low', 'close', 'ma5', 'ma10', 'ma20', 'ma30',
                'macd_dif', 'macd_dea', 'macd_bar', 'kdj_k', 'kdj_d', 'kdj_j', 'dma', 'dma_ama']
    for col in num_cols:
        if col in result.columns:
            result[col] = result[col].apply(r2)
    
    records = []
    for _, row in result.iterrows():
        records.append({
            "date": str(row['date']),
            "open": r2(row['open']),
            "high": r2(row['high']),
            "low": r2(row['low']),
            "close": r2(row['close']),
            "volume": int(row['volume']) if not pd.isna(row['volume']) else 0,
            "ma5": r2(row['ma5']),
            "ma10": r2(row['ma10']),
            "ma20": r2(row['ma20']),
            "ma30": r2(row['ma30']),
            "macd_dif": r2(row['macd_dif']),
            "macd_dea": r2(row['macd_dea']),
            "macd_bar": r2(row['macd_bar']),
            "kdj_k": r2(row['kdj_k']),
            "kdj_d": r2(row['kdj_d']),
            "kdj_j": r2(row['kdj_j']),
            "dma": r2(row['dma']),
            "dma_ama": r2(row['dma_ama'])
        })
    return records

def get_random_training(length, stock_code=None):
    """获取随机训练数据"""
    stocks = get_stock_list()
    if not stocks:
        return None
    
    if stock_code:
        stock = next((s for s in stocks if s['code'] == stock_code), None)
        if not stock:
            stock = random.choice(stocks)
    else:
        stock = random.choice(stocks)
    
    df = load_stock_data(stock['code'])
    if df is None or len(df) < length + 100:
        return None
    
    max_start = len(df) - length - 1
    start_idx = random.randint(100, max(100, max_start))
    
    klines = get_training_data(stock['code'], start_idx, length)
    if not klines:
        return None
    
    # 答案（下一根K线）
    answer_idx = start_idx + length
    answer = None
    if answer_idx < len(df):
        row = df.iloc[answer_idx]
        prev_close = klines[-1]['close']
        answer = {
            "date": str(row['date']),
            "open": r2(float(row['open'])),
            "close": r2(float(row['close'])),
            "high": r2(float(row['high'])),
            "low": r2(float(row['low'])),
            "direction": "up" if row['close'] >= prev_close else "down",
            "change_pct": r2(abs(row['close'] - prev_close) / prev_close * 100)
        }
    
    return {
        "code": stock['code'],
        "klines": klines,
        "answer": answer,
        "start_idx": start_idx,
        "total_len": len(df),
        "buy_hold_return": r2((klines[-1]['close'] - klines[0]['close']) / klines[0]['close'] * 100) if klines else 0
    }

def get_stock_next_training(stock_code, start_idx, length):
    """获取个股连续训练数据"""
    df = load_stock_data(stock_code)
    if df is None or len(df) < start_idx + length + 1:
        return None
    
    # 确保起始索引有效
    if start_idx < 100:
        start_idx = 100
    
    # 检查是否超出数据范围
    if start_idx + length >= len(df):
        return None
    
    klines = get_training_data(stock_code, start_idx, length)
    if not klines:
        return None
    
    # 答案（下一根K线）
    answer_idx = start_idx + length
    answer = None
    if answer_idx < len(df):
        row = df.iloc[answer_idx]
        prev_close = klines[-1]['close']
        answer = {
            "date": str(row['date']),
            "open": r2(float(row['open'])),
            "close": r2(float(row['close'])),
            "high": r2(float(row['high'])),
            "low": r2(float(row['low'])),
            "direction": "up" if row['close'] >= prev_close else "down",
            "change_pct": r2(abs(row['close'] - prev_close) / prev_close * 100)
        }
    
    return {
        "code": stock_code,
        "klines": klines,
        "answer": answer,
        "start_idx": start_idx,
        "next_idx": start_idx + 1,
        "total_len": len(df),
        "buy_hold_return": r2((klines[-1]['close'] - klines[0]['close']) / klines[0]['close'] * 100) if klines else 0
    }

def get_stock_full_data(stock_code, length):
    """获取个股全部数据用于模拟交易"""
    df = load_stock_data(stock_code)
    if df is None or len(df) < length + 100:
        return None
    
    # 使用全部数据，从第100根开始（确保指标计算准确）
    # 留出一些空间用于指标计算
    start_idx = 100
    max_length = len(df) - start_idx - 60  # 减去指标计算需要的前置数据
    if max_length < length:
        length = max_length
    
    klines = get_training_data(stock_code, start_idx, length)
    if not klines:
        return None
    
    return {
        "code": stock_code,
        "klines": klines,
        "total": len(klines)
    }

def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, 'r') as f:
            return json.load(f)
    return {"daily": [], "weekly": [], "monthly": [], "all_time": [], "blind_test": []}

def save_leaderboard(data):
    os.makedirs(os.path.dirname(LEADERBOARD_FILE), exist_ok=True)
    with open(LEADERBOARD_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def add_score(name, score, mode, kl=60, details=None):
    board = load_leaderboard()
    entry = {"name": name, "score": score, "time": datetime.now().isoformat(), "details": details or {}}
    
    # 生成分类键：mode_kl (如 train_60, stock_30, stockblind_0)
    key = f"{mode}_{kl}"
    if key not in board:
        board[key] = []
    existing = next((e for e in board[key] if e['name'] == name), None)
    if existing:
        if score > existing['score']:
            existing['score'] = score
            existing['time'] = entry['time']
            existing['details'] = details
    else:
        board[key].append(entry.copy())
    board[key].sort(key=lambda x: x['score'], reverse=True)
    board[key] = board[key][:100]
    
    save_leaderboard(board)
    return board

class KlineHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse.urlparse(self.path)
        path = parsed.path
        params = urlparse.parse_qs(parsed.query)
        
        if path == '/api/stocks':
            stocks = get_stock_list()
            self.send_json(stocks[:200])
        elif path == '/api/random':
            length = int(params.get('length', ['60'])[0])
            stock_code = params.get('code', [None])[0]
            blind = params.get('blind', ['false'])[0] == 'true'
            data = get_random_training(length, stock_code)
            if data and blind:
                data['blind_code'] = data['code']
                data['code'] = '??????'
            self.send_json(data)
        elif path == '/api/stock_next':
            stock_code = params.get('code', [None])[0]
            length = int(params.get('length', ['60'])[0])
            index = int(params.get('index', ['0'])[0])
            blind = params.get('blind', ['false'])[0] == 'true'
            # 如果没有指定股票，随机选一个
            if not stock_code:
                stocks = get_stock_list()
                if stocks:
                    stock = random.choice(stocks)
                    stock_code = stock['code']
                else:
                    self.send_json({'error': 'No stocks available'})
                    return
            data = get_stock_next_training(stock_code, index, length)
            if data and blind:
                data['blind_code'] = data['code']
                data['code'] = '??????'
            self.send_json(data)
        elif path == '/api/stock_train':
            stock_code = params.get('code', [None])[0]
            length = int(params.get('length', ['60'])[0])
            if not stock_code:
                stocks = get_stock_list()
                if stocks:
                    stock = random.choice(stocks)
                    stock_code = stock['code']
                else:
                    self.send_json({'error': 'No stocks available'})
                    return
            data = get_stock_full_data(stock_code, length)
            self.send_json(data)
        elif path == '/api/leaderboard':
            self.send_json(load_leaderboard())
        elif path == '/' or path == '/index.html':
            self.path = '/static/index.html'
            super().do_GET()
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path == '/api/submit_score':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            name = data.get('name', 'Anonymous')
            score = data.get('score', 0)
            mode = data.get('mode', 'train')
            kl = int(data.get('kl', 60))
            blind = str(data.get('blind', 'false')).lower() == 'true'
            
            details = {
                "mode": mode, "blind": blind, "kl": kl,
                "total": data.get('total', 0),
                "correct": data.get('correct', 0),
                "stock": data.get('stock', '')
            }
            
            board = add_score(name, score, mode, kl, details)
            self.send_json({"success": True, "leaderboard": board})
        else:
            self.send_error(404)
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

def run_server(port=8889):
    server = HTTPServer(('0.0.0.0', port), KlineHandler)
    print(f"K线训练服务器启动: http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
