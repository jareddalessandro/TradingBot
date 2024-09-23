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
data_frame = pd.DataFrame()
data_lock = threading.Lock()

def subscribe_to_ohlc():
    """Subscribe to Kraken OHLC WebSocket data."""
    subscription_message = {
        "event": "subscribe",
        "pair": [config.SYMBOL],
        "subscription": {"name": "ohlc", "interval": config.TIMEFRAME_SHORT}
    }
    ws.send(json.dumps(subscription_message))

def handle_socket_message(message):
    """Process incoming WebSocket message from Kraken."""
    global data_frame
    try:
        msg = json.loads(message)
        if isinstance(msg, list):
            ohlc_data = msg[1]
            new_row = {
                'timestamp': pd.to_datetime(float(ohlc_data[0]), unit='s'),
                'open': float(ohlc_data[1]),
                'high': float(ohlc_data[2]),
                'low': float(ohlc_data[3]),
                'close': float(ohlc_data[4]),
                'volume': float(ohlc_data[6]),
            }
            with data_lock:
                data_frame = data_frame.append(new_row, ignore_index=True)
                data_frame = data_frame.tail(config.REQUIRED_DATA_LENGTH)
            run_bot()
    except Exception as e:
        logging.error(f"Error in handle_socket_message: {e}")

def run_bot():
    """Run the trading bot logic."""
    global position, entry_price, stop_loss_price, take_profit_price, data_frame
    try:
        with data_lock:
            if len(data_frame) < config.REQUIRED_DATA_LENGTH:
                return

        data = data_frame.copy()
        data = indicators.apply_technical_indicators(data)
        signal, last_price = strategy.generate_signals(data, data, data)

        if position is None and signal == 'BUY':
            atr_value = data['atr'].iloc[-1]
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

def main():
    global ws
    ws = utils.get_websocket_manager()
    print("Connection Opened")
    wst = threading.Thread(target=ws.run_forever)
    wst.start()
    
    time.sleep(3)  # Allow WebSocket connection to open
    subscribe_to_ohlc()

    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
