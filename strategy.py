import config
import utils
import math
import logging

def generate_signals(data_1m, data_5m, data_1h):
    """Generate buy or sell signals based on technical indicators and support/resistance."""
    signal = None
    last_price = data_1m['close'].iloc[-1]  # Using 1-minute data for last price

    # Calculate support and resistance
    data_1m = calculate_support_resistance(data_1m)
    data_5m = calculate_support_resistance(data_5m)
    data_1h = calculate_support_resistance(data_1h)

    # Support and Resistance from both 5-minute and 1-hour data
    support_5m = data_5m['support'].iloc[-1]
    resistance_5m = data_5m['resistance'].iloc[-1]
    support_1h = data_1h['support'].iloc[-1]
    resistance_1h = data_1h['resistance'].iloc[-1]

    # EMA Crossover (9 over 21)
    ema_9 = data_5m['ema_9'].iloc[-1]
    ema_21 = data_5m['ema_21'].iloc[-1]
    ema_50 = data_5m['ema_50'].iloc[-1]
    ema_120 = data_5m['ema_120'].iloc[-1]
    ema_200 = data_5m['ema_120'].iloc[-1]
    ema_crossover_9 = ema_9 > ema_21 and data_5m['ema_9'].iloc[-2] <= data_5m['ema_21'].iloc[-2]

    # RSI Signal (Healthy RSI range: 40-70)
    rsi = data_5m['rsi'].iloc[-1]
    healthy_rsi = 40 <= rsi <= 65

    # MACD (Bearish to Bullish Crossover)
    macd = data_5m['macd'].iloc[-1]
    macd_signal = data_5m['macd_signal'].iloc[-1]
    macd_cross_bullish = macd > macd_signal and data_5m['macd'].iloc[-2] <= data_5m['macd_signal'].iloc[-2]
    macd_cross_bearish = macd < macd_signal and data_5m['macd'].iloc[-2] >= data_5m['macd_signal'].iloc[-2]

    # Volume Spike
    volume_spike = data_5m['volume'].iloc[-1] > data_5m['volume_ma'].iloc[-1] * config.VOLUME_SPIKE_BUFFER

    # Trend
    uptrend = ema_9 > ema_21

    logging.info(f"Last Price: {last_price}\nSupport 5m: {support_5m}\nResistance 5m: {resistance_5m}")
    logging.info(f"Support 1h: {support_1h}\nResistance 1h: {resistance_1h}\nEMA 9: {ema_9}\nEMA 21: {ema_21}\nRSI: {rsi}")

    ############ Bullish Flags

    # Volume surge near support (within a tight buffer range, price bouncing off support)
    if support_5m < last_price <= support_5m * (1 + config.S_R_BUFFER) and volume_spike and uptrend:
        signal = 'BUY'
        logging.info("Buy signal: Volume surge near 5-minute support, with price close above support.")
    elif support_1h < last_price <= support_1h * (1 + config.S_R_BUFFER) and volume_spike and uptrend:
        signal = 'BUY'
        logging.info("Buy signal: Volume surge near 1-hour support, with price close above support.")

    # Bouncing off support with MACD turning bullish (price near support and MACD is turning)
    elif (support_5m < last_price <= support_5m * (1 + config.S_R_BUFFER) and macd_cross_bullish) or \
         (support_1h < last_price <= support_1h * (1 + config.S_R_BUFFER) and macd_cross_bullish):
        signal = 'BUY'
        logging.info("Buy signal: Price bounced off support with MACD turning bullish.")

    # EMA Crossover with a healthy RSI (EMA 9 crossover EMA 21 and RSI is healthy)
    elif ema_crossover_9 and healthy_rsi and (last_price > support_5m):
        signal = 'BUY'
        logging.info("Buy signal: EMA 9 crossed above EMA 21 with a healthy RSI.")

    # Breaking through 5 min resistance
    elif (resistance_5m < last_price <= resistance_5m * (1 + config.S_R_BUFFER)) and healthy_rsi:
        signal = 'BUY'
        logging.info("Buy signal: Price broke through 5 min resistance with healthy RSI.")

    # Breaking through 1 hr resistance
    elif (resistance_1h < last_price <= resistance_1h * (1 + config.S_R_BUFFER)) and healthy_rsi:
        signal = 'BUY'
        logging.info("Buy signal: Price broke through 1 hr resistance with healthy RSI.")
    
    # Positive trend
    elif macd_signal and healthy_rsi and uptrend:
        signal = 'BUY'
        logging.info("Buy signal: Price broke through 1 hr resistance with healthy RSI.")

    ############ Bearish Flags

    # Bearish MACD crossover combined with a breakdown of support
    elif (macd_cross_bearish and last_price < support_5m) or (macd_cross_bearish and last_price < support_1h):
        signal = 'SELL'
        logging.info("Sell signal: MACD bearish crossover with price breaking support.")

    # Overbought RSI and price near resistance
    elif rsi > 70 and (last_price >= resistance_5m * (1 - config.S_R_BUFFER) or last_price >= resistance_1h * (1 - config.S_R_BUFFER)):
        signal = 'SELL'
        logging.info("Sell signal: Overbought RSI and price near resistance.")
    
    # Sell signal when price breaks support
    elif last_price < support_5m and data_1m['close'].iloc[-2] >= support_5m and not uptrend:
        signal = 'SELL'
        logging.info("Sell signal: Price broke 5-minute support.")
    elif last_price < support_1h and data_1m['close'].iloc[-2] >= support_1h and not uptrend:
        signal = 'SELL'
        logging.info("Sell signal: Price broke 1-hour support.")
    else:
        logging.info("Hold: No action determined")
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

def calculate_support_resistance(data, window=50):
    """
    Calculate dynamic support and resistance based on recent highs and lows.
    """
    data['support'] = data['low'].rolling(window=window, min_periods=1).min()
    data['resistance'] = data['high'].rolling(window=window, min_periods=1).max()
    return data

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
