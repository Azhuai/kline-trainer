# K线训练系统 📈

基于A股真实K线数据的专业训练系统，支持技术指标分析、盲测模式、排行榜等功能。

## ✨ 功能特点

- 🎯 **训练模式** - 预测K线涨跌方向（买入/卖出/持有）
- 🔍 **盲测模式** - 隐藏股票信息，考验真实盘感
- 📊 **技术指标** - MA(5/10/20/30)、MACD、KDJ、DMA
- 🏆 **排行榜** - 日/周/月/总/盲测多维度排名
- 📱 **响应式** - PC端和手机端自适应显示
- 🎨 **专业配色** - A股红涨绿跌标准配色

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
- macOS / Linux / Windows

### 2. 安装依赖

```bash
pip install flask baostock pandas numpy
```

### 3. 获取数据

#### 方式一：使用Qlib离线数据（推荐）

如果你已经有Qlib数据，直接配置路径：

```bash
# Qlib数据位置（默认）
~/.qlib/qlib_data/cn_data/stock/
├── sh/           # 上证股票
│   ├── 600519/   # 贵州茅台
│   │   └── 600519.csv
│   └── ...
├── sz/           # 深证股票
│   ├── 000858/   # 五粮液
│   │   └── 000858.csv
│   └── ...
└── bj/           # 北交所
    └── ...
```

#### 方式二：下载数据

```bash
# 下载A股日线数据
python download_5min.py
```

### 4. 启动服务

```bash
python server.py
```

访问 http://localhost:8889

## 📁 项目结构

```
kline-trainer/
├── server.py           # 后端服务
├── static/
│   └── index.html      # 前端页面
├── data/
│   └── leaderboard.json # 排行榜数据
├── download_5min.py    # 数据下载脚本
└── README.md
```

## 📊 数据格式

### Qlib CSV格式

```csv
date,open,high,low,close,volume,amount,adjustflag,factor
2024-01-02,1800.01,1810.50,1795.00,1805.30,12345678,22345678901,3,1.0
```

### 字段说明

| 字段 | 说明 |
|------|------|
| date | 日期 |
| open | 开盘价 |
| high | 最高价 |
| low | 最低价 |
| close | 收盘价 |
| volume | 成交量 |
| amount | 成交额 |
| adjustflag | 复权标志(1:后复权 2:前复权 3:不复权) |
| factor | 复权因子 |

## 🔧 配置说明

### 修改数据路径

编辑 `server.py` 中的 `QLIB_DATA_DIR`：

```python
# 默认路径
QLIB_DATA_DIR = os.path.expanduser("~/.qlib/qlib_data/cn_data/stock")

# 自定义路径
QLIB_DATA_DIR = "/path/to/your/qlib_data/stock"
```

### 修改端口

编辑 `server.py` 最后一行：

```python
httpd = HTTPServer(("", 8889), Handler)  # 修改8889为其他端口
```

## 📱 使用说明

### 训练模式

1. 选择K线数量（30/60/90/120根）
2. 设置每日目标（10/20/50题）
3. 可选输入股票代码（如 sh.600519）
4. 根据K线和技术指标判断走势
5. 点击买入/卖出/持有

### 盲测模式

- 隐藏股票名称和代码
- 训练结束后揭晓答案
- 考验真实盘感

### 排行榜

支持多维度排名：
- 📅 日榜
- 📆 周榜
- 🗓️ 月榜
- 📋 总榜
- 🔍 盲测榜

## 🔄 数据更新

### Qlib数据更新

```bash
# 使用Qlib官方工具更新
python -m qlib.run.get_data qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn
```

### 手动更新

直接替换CSV文件即可，保持格式一致：

```
~/.qlib/qlib_data/cn_data/stock/
└── sh/
    └── 600519/
        └── 600519.csv  # 替换此文件
```

## 🌐 局域网访问

启动后可在同一网络下访问：

- PC端：http://localhost:8889
- 手机端：http://你的IP:8889

查看本机IP：
```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# Linux
ip addr show | grep "inet " | grep -v 127.0.0.1
```

## 📦 依赖说明

| 包 | 版本 | 用途 |
|---|---|---|
| flask | ≥2.0 | Web服务器 |
| baostock | ≥0.8 | 数据下载 |
| pandas | ≥1.3 | 数据处理 |
| numpy | ≥1.21 | 数值计算 |

## 🤝 贡献

欢迎提交Issue和PR！

## 📄 许可证

MIT License

---

**作者**: 拽哥 & 牛牛 🐮
**创建时间**: 2026-05-06
