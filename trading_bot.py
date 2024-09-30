import time
import indicators
import strategy
import logging
import pandas as pd
import threading
import json
import krakenex
import logging
import websocket
import config


## TODO:
# 1. confirm that candle closed IS UNDERSTOOD and written correctly
# 2. 

# Configure logging
logging.basicConfig(
    filename='trading_bot.log',
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

MAX_RETRIES = 6  # Maximum number of retries before giving up
RETRY_DELAY = 10  # Delay between retries (in seconds)
RETRY_COUNT = 0

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

################ WEB SOCKET RELATED FUNCTIONS ##########################

def get_client():
    """Initialize and return the Kraken client."""
    kraken.key = config.API_KEY
    kraken.secret = config.API_SECRET
    return kraken

def place_order(client, pair, side, volume):
    """Place an order on Kraken."""
    if config.PAPER_TRADING:
        logging.info(f"Simulated {side} order for {volume} {pair}")
        return {'status': 'simulated', 'side': side, 'volume': volume}
    else:
        try:
            order = client.query_private('AddOrder', {
                'pair': pair,
                'type': side.lower(),
                'ordertype': 'market',
                'volume': volume
            })
            logging.info(f"Order placed: {order}")
            return order
        except Exception as e:
            logging.error(f"Error placing order: {e}")
            return None

def get_websocket_manager():
    """Start the Kraken WebSocket connection with retry logic."""
    ws = websocket.WebSocketApp(
        "wss://ws.kraken.com/",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.on_open = on_open
    return ws

def on_message(ws, message):    
    """Handle incoming WebSocket messages."""
    handle_socket_message(message)


def on_error(ws, error):
    """Handle WebSocket errors and try to reconnect."""
    global RETRY_COUNT
    logging.error(f"WebSocket error: {error}")

    if RETRY_COUNT < MAX_RETRIES:
        RETRY_COUNT += 1
        logging.info(f"Retrying WebSocket connection ({RETRY_COUNT}/{MAX_RETRIES})...")
        time.sleep(RETRY_DELAY * RETRY_COUNT)  # Exponential backoff
        reconnect_websocket()
    else:
        logging.error("Max retries reached. Could not reconnect WebSocket.")

def on_close(ws):
    """Handle WebSocket closing and attempt to reconnect."""
    global RETRY_COUNT
    logging.warning("WebSocket connection closed.")
    
    if RETRY_COUNT < MAX_RETRIES:
        RETRY_COUNT += 1
        logging.info(f"Retrying WebSocket connection ({RETRY_COUNT}/{MAX_RETRIES})...")
        time.sleep(RETRY_DELAY * RETRY_COUNT)
        reconnect_websocket()
    else:
        logging.error("Max retries reached. Could not reconnect WebSocket.")

def on_open(ws):
    """Reset retry count when WebSocket successfully connects."""
    global RETRY_COUNT
    logging.info("WebSocket connection opened.")
    RETRY_COUNT = 0  # Reset retry counter on successful connection

def reconnect_websocket():
    """Attempt to reconnect the WebSocket."""
    global ws
    try:
        ws = get_websocket_manager()
        wst = threading.Thread(target=ws.run_forever)
        wst.start()
        logging.info("WebSocket reconnection successful.")
    except Exception as e:
        logging.error(f"Error reconnecting WebSocket: {e}")


def subscribe_to_ohlc():
    global data_frame_1m, data_frame_5m, data_frame_1h
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

        if isinstance(msg, list):
            ohlc_data = msg[1]
            subscription = msg[2]

            # Check if the candle is closed by comparing last update time to interval end time
            is_candle_closed = ohlc_data[0] == ohlc_data[1]  # ohlc_data[0] is last update time, ohlc_data[1] is interval end time

            # Create a new DataFrame row (for the latest OHLC data)
            new_row = pd.DataFrame([{
                'timestamp': pd.to_datetime(float(ohlc_data[1]), unit='s'),  # Candle end time
                'open': float(ohlc_data[2]),  # Open price
                'high': float(ohlc_data[3]),  # High price
                'low': float(ohlc_data[4]),   # Low price
                'close': float(ohlc_data[5]), # Close price
                'vwap': float(ohlc_data[6]),  # VWAP
                'volume': float(ohlc_data[7]),# Volume
                'count': float(ohlc_data[8]), # Number of trades
            }])
            print("OHCL [0]", pd.to_datetime(float(ohlc_data[0]), unit='s'))
            with data_lock:
                if is_candle_closed:  # Append new row when the candle is closed
                    print("Candle is closed...Concatenating")
                    if 'ohlc-1' in subscription:
                        print("Updating 1 min")
                        data_frame_1m = pd.concat([data_frame_1m, new_row])
                        data_frame_1m = data_frame_1m.tail(config.REQUIRED_DATA_LENGTH)

                    elif 'ohlc-5' in subscription:
                        print("Updating 5 min")
                        data_frame_5m = pd.concat([data_frame_5m, new_row])
                        data_frame_5m = data_frame_5m.tail(config.REQUIRED_DATA_LENGTH)

                    elif 'ohlc-60' in subscription:
                        print("Updating 1 hour")
                        data_frame_1h = pd.concat([data_frame_1h, new_row])
                        data_frame_1h = data_frame_1h.tail(config.REQUIRED_DATA_LENGTH)
                else:
                    print("Candle NOT closed...replacing last entry")
                    # Overwrite the last row if the candle is still open (not yet closed)
                    if 'ohlc-1' in subscription:
                        print("Updating 1 min")
                        print(new_row.iloc[0])
                        data_frame_1m.iloc[-1] = new_row.iloc[0]
                    elif 'ohlc-5' in subscription:
                        print("Updating 5 min")
                        print(new_row.iloc[0])
                        data_frame_5m.iloc[-1] = new_row.iloc[0]  
                    elif 'ohlc-60' in subscription:
                        print("Updating 1 hr")
                        print(new_row.iloc[0])
                        data_frame_1h.iloc[-1] = new_row.iloc[0]

            # Run the bot after adding/updating data
            run_bot()

    except Exception as e:
        logging.error(f"Error in handle_socket_message: {e}")


################ WEB SOCKET RELATED FUNCTIONS ENDING ##########################


def fetch_historical_data():
    """Fetch historical OHLC data for 1m, 5m, and 1h intervals."""
    global data_frame_1m, data_frame_5m, data_frame_1h


    # Current UNIX timestamp (in seconds)
    current_timestamp = int(time.time())

    # Calculate since timestamps for 500 periods
    since_1m = current_timestamp - (500 * 60)  # 1-minute chart
    since_5m = current_timestamp - (500 * 5 * 60)  # 5-minute chart
    since_1h = current_timestamp - (500 * 60 * 60 * 1)  # 1-hour chart`
    # Fetch historical data for 1-minute, 5-minute, and 1-hour intervals
    data_frame_1m = get_historical_ohlc(config.REST_SYMBOL, config.TIMEFRAME_SHORT, since_1m)
    data_frame_5m = get_historical_ohlc(config.REST_SYMBOL, config.TIMEFRAME_LONG, since_5m)
    data_frame_1h = get_historical_ohlc(config.REST_SYMBOL, config.TIMEFRAME_CONFIRM, since_1h)

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



def run_bot():
    """Run the trading bot logic."""
    global position, entry_price, stop_loss_price, take_profit_price, data_frame_1m, data_frame_5m, data_frame_1h
    try:
        with data_lock:
            # Use the 1-minute data for decision making, confirm trend using 5-minute and 1-hour data
            data_1m = data_frame_1m.copy()
            data_5m = data_frame_5m.copy()
            data_1h = data_frame_1h.copy()            
            data_1m = indicators.apply_technical_indicators(data_1m)
            data_5m = indicators.apply_technical_indicators(data_5m)
            data_1h = indicators.apply_technical_indicators(data_1h)

            logging.info("1-minute data (last 5 rows):\n%s", data_1m.tail(10).to_string())
            logging.info("5-minute data (last 5 rows):\n%s", data_5m.tail(10).to_string())
            logging.info("1-hour data (last 5 rows):\n%s", data_1h.tail(10).to_string())
            signal, last_price = strategy.generate_signals(data_1m, data_5m, data_1h)
            
        

            if position is None and signal == 'BUY':
                atr_value = data_1m['atr'].iloc[-1]
                stop_loss_price = strategy.calculate_stop_loss(last_price, atr_value)
                take_profit_price = strategy.calculate_take_profit(last_price, stop_loss_price)
                quantity = strategy.calculate_quantity(client, last_price, stop_loss_price)
                if quantity > 0:
                    order = place_order(client, config.SYMBOL, 'BUY', quantity)
                    if order:
                        position = 'LONG'
                        entry_price = last_price
                        logging.info(f"Bought {quantity} {config.SYMBOL} at {last_price}")
            elif position == 'LONG' and (signal == 'SELL' or last_price <= stop_loss_price or last_price >= take_profit_price):
                order = place_order(client, config.SYMBOL, 'SELL', position)
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


## IMPORTANT VARIABLES 
kraken = krakenex.API()
client = get_client()

def main():
    global ws, data_frame_1m, data_frame_5m, data_frame_1h

    # Step 1: Fetch historical data
    if not fetch_historical_data():
        logging.error("Failed to fetch historical data. Exiting.")
        return
    
    # Step 2: Set up WebSocket connection for real-time updates
    ws = get_websocket_manager()
    wst = threading.Thread(target=ws.run_forever)
    wst.start()

    time.sleep(3)  # Allow WebSocket connection to open
    subscribe_to_ohlc()

    # Step 3: Main loop to keep the WebSocket connection alive
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
