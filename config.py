# config.py

API_KEY = '1UuZ1YVKzHE50gfQNHI3oRC03brwTiXPP0qpsgqo2VfdgvNjfdMWiM0zHdPmlBAW'
API_SECRET = 'EwYoUSUz5s3e3jyxXwB3xaYK1wwfuhKGLLXbNIAREfWTcscg32XvkZGxWIexp1Ts'

PAPER_TRADING = True  # Set to False to enable live trading

# Trading parameters
SYMBOL = 'BTCUSD'
TRADE_QUANTITY_PERCENTAGE = 10  # Percentage of capital to use per trade
RISK_PER_TRADE_PERCENTAGE = 1   # Percentage of capital to risk per trade
REQUIRED_DATA_LENGTH = 500 # This is for indicator requirements, making sure we have enough data frames

# Stop-loss and take-profit settings
RISK_REWARD_RATIO = 2  # Desired risk-reward ratio

# Timeframes
TIMEFRAME_SHORT = '1m'
TIMEFRAME_LONG = '5m'
TIMEFRAME_CONFIRM = '1h'

# Technical indicator settings
EMA_SHORT_WINDOW = 9
EMA_LONG_WINDOW = 21
EMA_TREND_WINDOW = 200
RSI_WINDOW = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
S_R_BUFFER = 0.01 # 1% buffer for S/R levels
VOLUME_SPIKE_BUFFER = 1.2 

# ATR settings
ATR_WINDOW = 7
ATR_MULTIPLIER = 1.5
