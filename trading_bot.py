# trading_bot.py

import schedule
import time
import math
import utils
import config
import indicators
import strategy
import logging
import pandas as pd
import threading

client = utils.get_client()

# Global variables to track position
position = None
entry_price = 0
stop_loss_price = 0
take_profit_price = 0

# Global variables to store real-time data
data_frame = pd.DataFrame()
data_lock = threading.Lock()

def handle_socket_message(msg):
    global data_frame
    # Process the message and update the data_frame
    with data_lock:
        # Parse message and update data_frame
        event_time = pd.to_datetime(msg['E'], unit='ms')
        price = float(msg['c'])
        volume = float(msg['v'])
        
        new_row = {
            'timestamp': event_time,
            'close': price,
            'volume': volume,
            # Add other fields as necessary
        }
        data_frame = data_frame.append(new_row, ignore_index=True)
        # Keep only the required number of recent data points
        data_frame = data_frame.tail(500)


def run_bot(client):
    global position, entry_price, stop_loss_price, take_profit_price, data_frame
    while True:
        try:
            # Ensure there is enough data to perform calculations
            with data_lock:
                if len(data_frame) < config.REQUIRED_DATA_LENGTH:
                    continue  # Wait until enough data has been collected
                data = data_frame.copy()
            
            if len(data_frame) > 1000:
                data_frame = data_frame.tail(500)  # Keep a limited history of 500 rows

            # Apply indicators and generate signals using S/R
            data = indicators.apply_technical_indicators(data)
            signal, last_price = strategy.generate_signals_with_support_resistance(data, data, data)
        
            if position is None:
                if signal == 'BUY':
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
            elif position == 'LONG':
                current_price = last_price
                # Check for exit conditions using S/R
                if current_price <= stop_loss_price or current_price >= take_profit_price or signal == 'SELL':
                    quantity_info = client.get_asset_balance(asset='BTC')
                    if quantity_info is not None:
                        quantity = float(quantity_info['free'])
                        if quantity > 0:
                            order = utils.place_order(client, config.SYMBOL, 'SELL', quantity)
                            if order:
                                position = None
                                logging.info(f"Sold {quantity} {config.SYMBOL} at {last_price}")
                else:
                    logging.info(f"Holding position. Current Price: {last_price}")
                    time.sleep(1)
        except Exception as e:
            logging.error(f"Error in run_bot: {e}")
            time.sleep(10)  # Wait before retrying
            continue  # Retry after waiting

def main():
    # Schedule the bot to run every minute
    schedule.every(1).minutes.do(run_bot)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main()
