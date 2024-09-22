# strategy.py

import config
import utils
import math

def generate_signals(data_short, data_long, data_confirm):
    """Generate buy or sell signals based on technical indicators and support/resistance."""
    signal = None
    last_price = data_short['close'].iloc[-1]
    
    # Trend Confirmation (higher timeframe)
    is_uptrend = data_confirm['close'].iloc[-1] > data_confirm['ema_trend'].iloc[-1]
    
    # EMA Crossover (lower timeframe)
    ema_crossover = data_long['ema_short'].iloc[-1] > data_long['ema_long'].iloc[-1] and \
                    data_long['ema_short'].iloc[-2] <= data_long['ema_long'].iloc[-2]
    
    # RSI Signal
    rsi_signal = data_long['rsi'].iloc[-1] > 30 and data_long['rsi'].iloc[-2] <= 30
    
    # MACD Signal
    macd_signal = data_long['macd'].iloc[-1] > data_long['macd_signal'].iloc[-1] and \
                  data_long['macd'].iloc[-2] <= data_long['macd_signal'].iloc[-2]
    
    # Volume Spike
    volume_spike = data_long['volume'].iloc[-1] > data_long['volume_ma'].iloc[-1] * config.VOLUME_SPIKE_BUFFER  # 20% above average volume
    
    # Candlestick Pattern Placeholder (implement if desired)
    candlestick_pattern = True  # Placeholder

    # --- NEW: Calculate Pivot Points and Swing High/Low Support/Resistance ---
    pivot, resistance_1, support_1, resistance_2, support_2 = calculate_pivot_points(data_long)
    dynamic_support, dynamic_resistance = calculate_swing_highs_lows(data_long)
    
    # --- NEW: Support/Resistance Filtering ---
    # Buy Signal when close to Support
    if is_uptrend and ema_crossover and (rsi_signal or macd_signal) and volume_spike:
        if last_price <= support_1 * (1 + config.S_R_BUFFER) or last_price <= dynamic_support * (1 + config.S_R_BUFFER):
            signal = 'BUY'
    
    # Sell Signal when close to Resistance
    elif last_price >= resistance_1 * (1 - config.S_R_BUFFER) or last_price >= dynamic_resistance * (1 - config.S_R_BUFFER):
        signal = 'SELL'
    else:
        # Additional filtering for existing sell signals
        ema_cross_down = data_long['ema_short'].iloc[-1] < data_long['ema_long'].iloc[-1] and \
                         data_long['ema_short'].iloc[-2] >= data_long['ema_long'].iloc[-2]
        rsi_overbought = data_long['rsi'].iloc[-1] < 70 and data_long['rsi'].iloc[-2] >= 73
        macd_cross_down = data_long['macd'].iloc[-1] < data_long['macd_signal'].iloc[-1] and \
                          data_long['macd'].iloc[-2] >= data_long['macd_signal'].iloc[-2]
        
        # If existing sell conditions are met and close to resistance
        if ema_cross_down or rsi_overbought or macd_cross_down:
            if last_price >= resistance_1 * (1 - config.S_R_BUFFER) or last_price >= dynamic_resistance * (1 - config.S_R_BUFFER):
                signal = 'SELL'
    
    return signal, last_price

def calculate_stop_loss(entry_price, atr_value):
    """Calculate stop-loss price based on ATR."""
    stop_loss_price = entry_price - (config.ATR_MULTIPLIER * atr_value)
    return stop_loss_price

def calculate_take_profit(entry_price, stop_loss_price):
    """Calculate take-profit price based on risk-reward ratio."""
    risk_per_unit = entry_price - stop_loss_price
    take_profit_price = entry_price + (config.RISK_REWARD_RATIO * risk_per_unit)
    return take_profit_price

def calculate_pivot_points(data):
    """Calculate pivot points and S/R levels."""
    pivot_point = (data['high'].iloc[-1] + data['low'].iloc[-1] + data['close'].iloc[-1]) / 3
    
    resistance_1 = (2 * pivot_point) - data['low'].iloc[-1]
    support_1 = (2 * pivot_point) - data['high'].iloc[-1]
    
    # Optional: Add more levels (Resistance 2, Support 2)
    resistance_2 = pivot_point + (data['high'].iloc[-1] - data['low'].iloc[-1])
    support_2 = pivot_point - (data['high'].iloc[-1] - data['low'].iloc[-1])
    
    return pivot_point, resistance_1, support_1, resistance_2, support_2

def calculate_swing_highs_lows(data, window=20):
    """Identify recent swing highs and lows over a given window."""
    recent_high = data['high'].rolling(window=window).max().iloc[-1]
    recent_low = data['low'].rolling(window=window).min().iloc[-1]
    return recent_low, recent_high

def calculate_quantity(client, entry_price, stop_loss_price):
    """Calculate the quantity to buy based on risk per trade."""
    balance_info = client.get_asset_balance(asset='USDT')
    if balance_info is None:
        return 0
    balance = float(balance_info['free'])
    risk_amount = balance * (config.RISK_PER_TRADE_PERCENTAGE / 100)
    risk_per_unit = entry_price - stop_loss_price
    if risk_per_unit <= 0:
        return 0
    
    quantity = risk_amount / risk_per_unit
    # Adjust quantity based on symbol precision
    step_size, _ = utils.get_symbol_precision(client, config.SYMBOL)
    precision = int(round(-math.log(step_size, 10), 0))
    quantity = round(quantity, precision)
    min_quantity = 0.001  # Define a minimum trade size based on exchange rules
    if quantity < min_quantity:
        return 0
    
    return quantity
