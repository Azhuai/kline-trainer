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
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

def r2(x):
    """保留2位小数"""
    if pd.isna(x) or x is None:
        return 0.0
    return round(float(x), 2)

def r4(x):
    """保留4位小数（用于中间计算）"""
    if pd.isna(x) or x is None:
        return 0.0
    return round(float(x), 4)

def calc_ma(series, window):
    """移动平均线"""
    return series.rolling(window=window, min_periods=1).mean().apply(r4)

def calc_ema(series, span):
    """指数移动平均"""
    return series.ewm(span=span, adjust=False).mean().apply(r4)

def calc_macd(close, fast=12, slow=26, signal=9):
    """MACD"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd = (dif - dea) * 2
    return dif.apply(r4), dea.apply(r4), macd.apply(r4)

def calc_kdj(high, low, close, n=9, m1=3, m2=3):
    """KDJ"""
    lowest_low = low.rolling(window=n, min_periods=1).min()
    highest_high = high.rolling(window=n, min_periods=1).max()
    rsv = ((close - lowest_low) / (highest_high - lowest_low) * 100).fillna(50)
    
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = (3 * k - 2 * d)
    
    return k.apply(r4), d.apply(r4), j.apply(r4)

def calc_dma(close, short=10, long=50, m=10):
    """DMA"""
    dma = (calc_ma(close, short) - calc_ma(close, long)).apply(r4)
    ama = calc_ma(dma, m).apply(r4)
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
    """加载股票日线数据，支持 sh.600000 和 600000.SH 两种格式"""
    parts = code.split('.')
    if len(parts) != 2:
        return None
    # 自动识别格式：sh.600000 或 600000.SH
    if parts[0].lower() in ('sh', 'sz'):
        market, stock_code = parts[0].lower(), parts[1]
    else:
        stock_code, market = parts[0], parts[1].lower()
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
    if df is None or len(df) < 170:
        return None
    
    # 自适应：如果数据不够，调整 length
    if start_idx + length >= len(df):
        length = len(df) - start_idx - 1
    if length < 10:
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
    
    # 不提前四舍五入，保持高精度计算指标
    # 最终输出时才四舍五入
    
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
    """获取随机训练数据（自动重试）"""
    stocks = get_stock_list()
    if not stocks:
        return None
    
    # 最多重试10次找到数据足够的股票
    for _ in range(10):
        if stock_code:
            stock = next((s for s in stocks if s['code'] == stock_code), None)
            if not stock:
                stock = random.choice(stocks)
        else:
            stock = random.choice(stocks)
        
        df = load_stock_data(stock['code'])
        if df is None or len(df) < 170:
            stock_code = None  # 重试换一个
            continue
        
        # 自适应长度
        available = len(df) - 160
        if available <= 0:
            stock_code = None
            continue
        actual_length = min(length, available)
        
        max_start = len(df) - actual_length - 1
        start_idx = random.randint(100, max(100, max_start))
        
        klines = get_training_data(stock['code'], start_idx, actual_length)
        if not klines:
            stock_code = None
            continue
        
        # 答案（下一根K线）
        answer_idx = start_idx + actual_length
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
        
        initial_close = klines[0]['close'] if klines else 0
        if initial_close == 0 or (isinstance(initial_close, float) and np.isnan(initial_close)):
            buy_hold_return = 0.0
        else:
            buy_hold_return = r2((klines[-1]['close'] - initial_close) / initial_close * 100)
        
        return {
            "code": stock['code'],
            "klines": klines,
            "answer": answer,
            "start_idx": start_idx,
            "total_len": len(df),
            "buy_hold_return": buy_hold_return
        }
    
    return None

def get_stock_next_training(stock_code, start_idx, length):
    """获取个股连续训练数据"""
    df = load_stock_data(stock_code)
    if df is None or len(df) < 170:
        return None
    
    # 确保起始索引有效
    if start_idx < 100:
        start_idx = 100
    
    # 自适应：如果超出范围，调整 start_idx
    if start_idx + length >= len(df):
        start_idx = max(100, len(df) - length - 1)
    if start_idx + length >= len(df):
        # 还是不够，缩短 length
        length = len(df) - start_idx - 1
    if length < 10:
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
    
    initial_close = klines[0]['close'] if klines else 0
    if initial_close == 0 or (isinstance(initial_close, float) and np.isnan(initial_close)):
        buy_hold_return = 0.0
    else:
        buy_hold_return = r2((klines[-1]['close'] - initial_close) / initial_close * 100)

    return {
        "code": stock_code,
        "klines": klines,
        "answer": answer,
        "start_idx": start_idx,
        "next_idx": start_idx + 1,
        "total_len": len(df),
        "buy_hold_return": buy_hold_return
    }

def get_stock_full_data(stock_code, length):
    """获取个股全部数据用于模拟交易"""
    df = load_stock_data(stock_code)
    if df is None or len(df) < 170:  # 至少需要100前置+70可见
        return None
    
    # 自适应：根据实际数据量调整 start_idx
    # 确保至少有 length 条可用数据
    needed = length + 60  # 需要额外60条用于指标计算
    start_idx = max(60, len(df) - needed)  # 最小start_idx=60（保证指标计算）
    available = len(df) - start_idx - 1
    if available < 10:
        return None
    actual_length = min(length, available)
    
    klines = get_training_data(stock_code, start_idx, actual_length)
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
                    # 尝试多次找一个有足够数据的股票
                    for _ in range(20):
                        stock = random.choice(stocks)
                        data = get_stock_full_data(stock['code'], length)
                        if data and len(data['klines']) >= length * 0.8:
                            self.send_json(data)
                            return
                    # 最后一次不管够不够都返回
                    if data:
                        self.send_json(data)
                    else:
                        self.send_json({'error': 'No stocks with enough data'})
                else:
                    self.send_json({'error': 'No stocks available'})
                return
            data = get_stock_full_data(stock_code, length)
            self.send_json(data)
        elif path == '/api/leaderboard':
            self.send_json(load_leaderboard())
        elif path == '/' or path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            with open(os.path.join(STATIC_DIR, 'index.html'), 'rb') as f:
                self.wfile.write(f.read())
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
