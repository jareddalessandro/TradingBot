# indicators.py

import pandas as pd
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
import config

def apply_technical_indicators(data):
    """Calculate technical indicators and add them to the DataFrame."""
    # EMAs
    data['ema9'] = EMAIndicator(
        close=data['close'], window=config.EMA_9_WINDOW).ema_indicator()
    data['ema21'] = EMAIndicator(
        close=data['close'], window=config.EMA_21_WINDOW).ema_indicator()
    data['ema50'] = EMAIndicator(
        close=data['close'], window=config.EMA_50_WINDOW).ema_indicator()
    data['ema200'] = EMAIndicator(
        close=data['close'], window=config.EMA_200_WINDOW).ema_indicator()
    
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
