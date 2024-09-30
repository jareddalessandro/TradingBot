# config.py

API_KEY = 'RtV71+yx04HpsM45HWmd6HTW8qBu0LdtA4ICnTRUZb8AegOVR/2cgOSz'
API_SECRET = 'UNqbf/ulr50iVOupdcAz5zu6Sedap3++W9EuOURtobqk7cfkeqP7cRds516WyzdBl7ILD2Gn+uL5F0WCnQCgeA=='

PAPER_TRADING = True  # Set to False to enable live trading

# Trading parameters
SYMBOL = 'XBT/USD'  # Use Kraken's trading pair notation for Bitcoin/USD
REST_SYMBOL = 'XXBTZUSD'
TRADE_QUANTITY_PERCENTAGE = 10  # Percentage of capital to use per trade
RISK_PER_TRADE_PERCENTAGE = 1   # Percentage of capital to risk per trade
REQUIRED_DATA_LENGTH = 500 # This is for indicator requirements, making sure we have enough data frames

# Stop-loss and take-profit settings
RISK_REWARD_RATIO = 2  # Desired risk-reward ratio

# Timeframes
TIMEFRAME_SHORT = 1
TIMEFRAME_LONG = 5
TIMEFRAME_CONFIRM = 60

# Technical indicator settings
EMA_9_WINDOW = 9
EMA_21_WINDOW = 21
EMA_50_WINDOW = 50
EMA_120_WINDOW = 120
EMA_200_WINDOW = 200
RSI_WINDOW = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
S_R_BUFFER = 0.0011 # 0.011% buffer for S/R levels
VOLUME_SPIKE_BUFFER = 1.2 

# ATR settings
ATR_WINDOW = 7
ATR_MULTIPLIER = 1.5
