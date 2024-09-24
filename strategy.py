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
    # Break and retest of resistance as support
    break_above_resistance = last_price > resistance_5m and data_1m['close'].iloc[-2] <= resistance_5m
    retest_support = data_1m['low'].iloc[-1] <= resistance_5m and last_price > resistance_5m
    # Break and retest of support as resistance
    break_below_support = last_price < support_5m and data_1m['close'].iloc[-2] >= support_5m
    retest_resistance = data_1m['high'].iloc[-1] >= support_5m and last_price < support_5m



    # EMAs
    ema_9 = data_5m['ema_9'].iloc[-1]
    ema_21 = data_5m['ema_21'].iloc[-1]
    ema_50 = data_5m['ema_50'].iloc[-1]
    ema_120 = data_5m['ema_120'].iloc[-1]
    ema_200 = data_5m['ema_200'].iloc[-1]
    ema_50_1h = data_1h['ema_50'].iloc[-1]
    ema_200_1h = data_1h['ema_200'].iloc[-1]
    ema_crossover_9 = ema_9 > ema_21 and data_5m['ema_9'].iloc[-2] <= data_5m['ema_21'].iloc[-2]
    price_cross_above_ema200 = (last_price > ema_200) and (data_5m['close'].iloc[-2] <= ema_200)
    price_cross_below_ema200 = (last_price < ema_200) and (data_5m['close'].iloc[-2] >= ema_200)
    
    # Trend
    uptrend = ema_9 > ema_21 > ema_50  # Stronger uptrend confirmation
    downtrend = ema_9 < ema_21 < ema_50  # Stronger downtrend confirmation
    # Trend on 1-hour timeframe
    uptrend_1h = ema_50_1h > ema_200_1h
    downtrend_1h = ema_50_1h < ema_200_1h
    # Golden Cross
    golden_cross = ema_50 > ema_200 and data_5m['ema_50'].iloc[-2] <= data_5m['ema_200'].iloc[-2]
    # Death Cross
    death_cross = ema_50 < ema_200 and data_5m['ema_50'].iloc[-2] >= data_5m['ema_200'].iloc[-2]
    
    # Price bouncing off EMA 50 in an uptrend
    bounce_off_ema200 = (data_5m['low'].iloc[-1] <= ema_200) and (last_price > ema_200) and uptrend
    # Price rejecting at EMA 50 in a downtrend
    reject_at_ema200 = (data_5m['high'].iloc[-1] >= ema_200) and (last_price < ema_200) and downtrend


    # RSI Signal (Healthy RSI range: 40-70)
    rsi = data_5m['rsi'].iloc[-1]
    healthy_rsi = 40 <= rsi <= 65
    # Bullish RSI divergence
    price_lower_low = data_5m['low'].iloc[-1] < data_5m['low'].iloc[-2]
    rsi_higher_low = data_5m['rsi'].iloc[-1] > data_5m['rsi'].iloc[-2]
    bullish_divergence = price_lower_low and rsi_higher_low
    # Bearish RSI divergence
    price_higher_high = data_5m['high'].iloc[-1] > data_5m['high'].iloc[-2]
    rsi_lower_high = data_5m['rsi'].iloc[-1] < data_5m['rsi'].iloc[-2]
    bearish_divergence = price_higher_high and rsi_lower_high


    # MACD (Bearish to Bullish Crossover)
    macd = data_5m['macd'].iloc[-1]
    macd_signal = data_5m['macd_signal'].iloc[-1]
    macd_bullish = macd > macd_signal
    macd_bearish = macd < macd_signal
    macd_cross_bullish = macd > macd_signal and data_5m['macd'].iloc[-2] <= data_5m['macd_signal'].iloc[-2]
    macd_cross_bearish = macd < macd_signal and data_5m['macd'].iloc[-2] >= data_5m['macd_signal'].iloc[-2]

    # Volume Spike
    volume_spike = data_5m['volume'].iloc[-1] > data_5m['volume_ma'].iloc[-1] * config.VOLUME_SPIKE_BUFFER


    logging.info(f"Last Price: {last_price}\nSupport 5m: {support_5m}\nResistance 5m: {resistance_5m}")
    logging.info(f"Support 1h: {support_1h}\nResistance 1h: {resistance_1h}\nEMA 9: {ema_9}\nEMA 21: {ema_21}\nRSI: {rsi}")

    ############ Bullish Flags
    if break_above_resistance and retest_support and uptrend:
        signal = 'BUY'
        logging.info("Buy signal: Breakout above resistance followed by successful retest as support.")

    # Volume surge near support (within a tight buffer range, price bouncing off support)
    elif support_5m < last_price <= support_5m * (1 + config.S_R_BUFFER) and volume_spike and uptrend:
        signal = 'BUY'
        logging.info("Buy signal: Volume surge near 5-minute support, with price close above support.")
    elif support_1h < last_price <= support_1h * (1 + config.S_R_BUFFER) and volume_spike and uptrend:
        signal = 'BUY'
        logging.info("Buy signal: Volume surge near 1-hour support, with price close above support.")

    elif bounce_off_ema200 and uptrend and macd_cross_bullish:
        signal = 'BUY'
        logging.info("Buy signal: Price bounced off EMA 200 in an uptrend with MACD bullish crossover.")

    # Bouncing off support with MACD turning bullish (price near support and MACD is turning)
    elif (support_5m < last_price <= support_5m * (1 + config.S_R_BUFFER) and macd_cross_bullish) or \
         (support_1h < last_price <= support_1h * (1 + config.S_R_BUFFER) and macd_cross_bullish):
        signal = 'BUY'
        logging.info("Buy signal: Price bounced off support with MACD turning bullish.")

    # Breaking through 5 min resistance
    elif (resistance_5m < last_price <= resistance_5m * (1 + config.S_R_BUFFER)) and healthy_rsi and uptrend:
        signal = 'BUY'
        logging.info("Buy signal: Price broke through 5 min resistance with healthy RSI.")

    # Breaking through 1 hr resistance
    elif (resistance_1h < last_price <= resistance_1h * (1 + config.S_R_BUFFER)) and healthy_rsi and uptrend:
        signal = 'BUY'
        logging.info("Buy signal: Price broke through 1 hr resistance with healthy RSI.")

    elif bullish_divergence and (abs(last_price - support_5m) <= config.S_R_BUFFER * last_price):
        signal = 'BUY'
        logging.info("Buy signal: Bullish RSI divergence near support.")
    
    elif uptrend and uptrend_1h and macd_cross_bullish and healthy_rsi:
        signal = 'BUY'
        logging.info("Buy signal: Uptrend confirmed on both 5-minute and 1-hour charts.")
    elif golden_cross and uptrend:
        signal = 'BUY'
        logging.info("Buy signal: Golden cross detected in an uptrend.")
    elif price_cross_above_ema200 and uptrend and macd_cross_bullish:
        signal = 'BUY'
        logging.info("Buy signal: Price crossed above EMA 200 with bullish confirmation.")



    ############ Bearish Flags
    elif death_cross and downtrend:
        signal = 'SELL'
        logging.info("Sell signal: Death cross detected in a downtrend.")
    elif break_below_support and retest_resistance and downtrend:
        signal = 'SELL'
        logging.info("Sell signal: Breakdown below support followed by successful retest as resistance.")
    elif bearish_divergence and (abs(last_price - resistance_5m) <= config.S_R_BUFFER * last_price):
        signal = 'SELL'
        logging.info("Sell signal: Bearish RSI divergence near resistance.")

    elif downtrend and downtrend_1h and macd_cross_bearish and rsi < 40:
        signal = 'SELL'
        logging.info("Sell signal: Downtrend confirmed on both 5-minute and 1-hour charts.")

    # Bearish MACD crossover combined with a breakdown of support
    elif (macd_cross_bearish and last_price < support_5m) or (macd_cross_bearish and last_price < support_1h):
        signal = 'SELL'
        logging.info("Sell signal: MACD bearish crossover with price breaking support.")

    # Overbought RSI and price near resistance
    elif rsi > 70 and (last_price >= resistance_5m * (1 - config.S_R_BUFFER) or last_price >= resistance_1h * (1 - config.S_R_BUFFER)):
        signal = 'SELL'
        logging.info("Sell signal: Overbought RSI and price near resistance.")
    elif reject_at_ema200 and downtrend and macd_cross_bearish:
        signal = 'SELL'
        logging.info("Sell signal: Price rejected at EMA 200 in a downtrend with MACD bearish crossover.")
    # Sell signal when price breaks support
    elif last_price < support_5m and data_1m['close'].iloc[-2] >= support_5m and downtrend:
        signal = 'SELL'
        logging.info("Sell signal: Price broke 5-minute support.")
    elif last_price < support_1h and data_1m['close'].iloc[-2] >= support_1h and downtrend:
        signal = 'SELL'
        logging.info("Sell signal: Price broke 1-hour support.")
        
    elif price_cross_below_ema200 and downtrend and macd_cross_bearish:
        signal = 'SELL'
        logging.info("Sell signal: Price crossed below EMA 200 with bearish confirmation.")    
        
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
    balance_info = client.query_private('Balance')
    if balance_info is None:
        return 0
    balance = float(balance_info['ZUSD'])

    ################## JUST FOR TESTING PURPOSES -- ** PLEASE REMOVE
    balance = 500
    ################## JUST FOR TESTING PURPOSES -- ** PLEASE REMOVE


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
