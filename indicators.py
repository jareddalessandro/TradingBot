# indicators.py

import pandas as pd
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
import utils
import config

client = utils.get_client()

def get_historical_ohlc(pair, interval, since):
    """Fetch historical OHLC data from Kraken."""
    try:
        ohlc_data = client.query_public('OHLC', {'pair': pair, 'interval': interval, 'since': since})
        data = pd.DataFrame(ohlc_data['result'][pair], columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume'
        ])
        data['timestamp'] = pd.to_datetime(data['timestamp'], unit='s')
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric)
        return data
    except Exception as e:
        return None

def apply_technical_indicators(data):
    """Calculate technical indicators and add them to the DataFrame."""
    # EMAs
    data['ema_short'] = EMAIndicator(
        close=data['close'], window=config.EMA_SHORT_WINDOW).ema_indicator()
    data['ema_long'] = EMAIndicator(
        close=data['close'], window=config.EMA_LONG_WINDOW).ema_indicator()
    data['ema_trend'] = EMAIndicator(
        close=data['close'], window=config.EMA_TREND_WINDOW).ema_indicator()
    
    # RSI
    data['rsi'] = RSIIndicator(
        close=data['close'], window=config.RSI_WINDOW).rsi()
    
    # MACD
    macd_indicator = MACD(
        close=data['close'],
        window_slow=config.MACD_SLOW,
        window_fast=config.MACD_FAST,
        window_sign=config.MACD_SIGNAL
    )
    data['macd'] = macd_indicator.macd()
    data['macd_signal'] = macd_indicator.macd_signal()
    
    # ATR
    atr_indicator = AverageTrueRange(
        high=data['high'],
        low=data['low'],
        close=data['close'],
        window=config.ATR_WINDOW
    )
    data['atr'] = atr_indicator.average_true_range()
    
    # Volume Moving Average
    data['volume_ma'] = data['volume'].rolling(window=20).mean()
    
    return data
