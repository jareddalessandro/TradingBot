# trading_bot.py

import time
import utils
import config
import indicators
import strategy
import logging
import pandas as pd
import threading
import json

client = utils.get_client()

# Global variables for the bot
position = None
entry_price = 0
stop_loss_price = 0
take_profit_price = 0

# Separate DataFrames for 1m, 5m, and 1h data
data_frame_1m = pd.DataFrame()
data_frame_5m = pd.DataFrame()
data_frame_1h = pd.DataFrame()
data_lock = threading.Lock()

def fetch_historical_data():
    """Fetch historical OHLC data for 1m, 5m, and 1h intervals."""
    global data_frame_1m, data_frame_5m, data_frame_1h

    # Fetch historical data for 1-minute, 5-minute, and 1-hour intervals
    data_frame_1m = get_historical_ohlc(config.REST_SYMBOL, config.TIMEFRAME_SHORT, 0)
    data_frame_5m = get_historical_ohlc(config.REST_SYMBOL, config.TIMEFRAME_LONG, 0)
    data_frame_1h = get_historical_ohlc(config.REST_SYMBOL, config.TIMEFRAME_CONFIRM, 0)

    # Ensure we have enough data before starting
    if data_frame_1m is None or len(data_frame_1m) < config.REQUIRED_DATA_LENGTH:
        logging.error("Not enough 1-minute historical data.")
        return False
    if data_frame_5m is None or len(data_frame_5m) < config.REQUIRED_DATA_LENGTH:
        logging.error("Not enough 5-minute historical data.")
        return False
    if data_frame_1h is None or len(data_frame_1h) < config.REQUIRED_DATA_LENGTH:
        logging.error("Not enough 1-hour historical data.")
        return False
    logging.info("*** Historical Data Successfully Loaded ***")
    return True

def subscribe_to_ohlc():
    """Subscribe to Kraken OHLC WebSocket data for 1m, 5m, and 1h intervals."""
    # Subscribe to the 1-minute OHLC
    ws.send(json.dumps({
        "event": "subscribe",
        "pair": [config.SYMBOL],
        "subscription": {"name": "ohlc", "interval": config.TIMEFRAME_SHORT}
    }))

    # Subscribe to the 5-minute OHLC
    ws.send(json.dumps({
        "event": "subscribe",
        "pair": [config.SYMBOL],
        "subscription": {"name": "ohlc", "interval": config.TIMEFRAME_LONG}
    }))

    # Subscribe to the 1-hour OHLC
    ws.send(json.dumps({
        "event": "subscribe",
        "pair": [config.SYMBOL],
        "subscription": {"name": "ohlc", "interval": config.TIMEFRAME_CONFIRM}
    }))

def handle_socket_message(message):
    global data_frame_1m, data_frame_5m, data_frame_1h
    try:
        msg = json.loads(message)
        #logging.info(f"WebSocket message received: {msg}")
        
        if isinstance(msg, list):
            ohlc_data = msg[1]
            subscription = msg[2]
            
            # Log which timeframe is being updated
            #logging.info(f"Processing data for: {subscription}")

             # Create a new DataFrame row
            new_row = pd.DataFrame([{
                'timestamp': pd.to_datetime(float(ohlc_data[0]), unit='s'),
                'open': float(ohlc_data[1]),
                'high': float(ohlc_data[2]),
                'low': float(ohlc_data[3]),
                'close': float(ohlc_data[4]),
                'volume': float(ohlc_data[6]),
            }])

            with data_lock:
                if 'ohlc-1' in subscription:
                    data_frame_1m = pd.concat([data_frame_1m, new_row], ignore_index=True)
                    data_frame_1m = data_frame_1m.tail(config.REQUIRED_DATA_LENGTH)
                    #logging.info(f"Updated 1-minute data: {data_frame_1m.tail(1)}")
                elif 'ohlc-5' in subscription:
                    data_frame_5m = pd.concat([data_frame_5m, new_row], ignore_index=True)
                    data_frame_5m = data_frame_5m.tail(config.REQUIRED_DATA_LENGTH)
                    #logging.info(f"Updated 5-minute data: {data_frame_5m.tail(1)}")
                elif 'ohlc-60' in subscription:
                    data_frame_1h = pd.concat([data_frame_1h, new_row], ignore_index=True)
                    data_frame_1h = data_frame_1h.tail(config.REQUIRED_DATA_LENGTH)
                    #logging.info(f"Updated 1-hour data: {data_frame_1h.tail(1)}")

            run_bot()

    except Exception as e:
        logging.error(f"Error in handle_socket_message: {e}")

    except Exception as e:
        logging.error(f"Error in handle_socket_message: {e}")

def run_bot():
    """Run the trading bot logic."""
    global position, entry_price, stop_loss_price, take_profit_price, data_frame_1m, data_frame_5m, data_frame_1h
    try:
        # Use the 1-minute data for decision making, confirm trend using 5-minute and 1-hour data
        data_1m = data_frame_1m.copy()
        data_5m = data_frame_5m.copy()
        data_1h = data_frame_1h.copy()            
        data_1m = indicators.apply_technical_indicators(data_1m)
        data_5m = indicators.apply_technical_indicators(data_5m)
        data_1h = indicators.apply_technical_indicators(data_1h)

        signal, last_price = strategy.generate_signals(data_1m, data_5m, data_frame_1h)

        if position is None and signal == 'BUY':
            atr_value = data_1m['atr'].iloc[-1]
            stop_loss_price = strategy.calculate_stop_loss(last_price, atr_value)
            take_profit_price = strategy.calculate_take_profit(last_price, stop_loss_price)
            quantity = strategy.calculate_quantity(client, last_price, stop_loss_price)
            if quantity > 0:
                order = utils.place_order(client, config.SYMBOL, 'BUY', quantity)
                if order:
                    position = 'LONG'
                    entry_price = last_price
                    logging.info(f"Bought {quantity} {config.SYMBOL} at {last_price}")
        elif position == 'LONG' and (signal == 'SELL' or last_price <= stop_loss_price or last_price >= take_profit_price):
            order = utils.place_order(client, config.SYMBOL, 'SELL', position)
            if order:
                position = None
                logging.info(f"Sold position at {last_price}")
    except Exception as e:
        logging.error(f"Error in run_bot: {e}")


def get_historical_ohlc(pair, interval, since):
    """Fetch historical OHLC data from Kraken."""
    try:
        ohlc_data = client.query_public('OHLC', {'pair': pair, 'interval': interval, 'since': since})

        # Check if the pair data exists in the response
        if 'result' in ohlc_data and pair in ohlc_data['result']:
            # Kraken returns 8 columns in the OHLC data: timestamp, open, high, low, close, vwap, volume, count
            data = pd.DataFrame(ohlc_data['result'][pair], columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'
            ])
            data['timestamp'] = pd.to_datetime(data['timestamp'], unit='s')

            # Convert numeric columns to appropriate types
            numeric_columns = ['open', 'high', 'low', 'close', 'vwap', 'volume', 'count']
            data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric)

            return data
        else:
            logging.error(f"No data found for pair {pair} or API error: {ohlc_data}")
            return None

    except Exception as e:
        logging.error(f"Error fetching historical data for {pair} on {interval} interval: {e}")
        return None


def main():
    global ws

    # Step 1: Fetch historical data
    if not fetch_historical_data():
        logging.error("Failed to fetch historical data. Exiting.")
        return

    # Step 2: Set up WebSocket connection for real-time updates
    ws = utils.get_websocket_manager()
    wst = threading.Thread(target=ws.run_forever)
    wst.start()

    time.sleep(3)  # Allow WebSocket connection to open
    subscribe_to_ohlc()

    # Step 3: Main loop to keep the WebSocket connection alive
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
