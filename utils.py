# utils.py

import krakenex
import logging
import websocket
import json
import time
import threading
import config

# Configure logging
logging.basicConfig(
    filename='trading_bot.log',
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(message)s'
)


MAX_RETRIES = 6  # Maximum number of retries before giving up
RETRY_DELAY = 10  # Delay between retries (in seconds)
retry_count = 0

kraken = krakenex.API()

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
    print(f"Message received: {message}")  # Print the message to the console
    try:
        msg = json.loads(message)
        # Check if the message contains data and log it
        if 'event' not in msg:
            logging.info(f"Message received: {msg}")
            # Additional logic to process the message can be added here
        else:
            logging.info(f"Event message received: {msg}")
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        print(f"Error: {e}")


def on_error(ws, error):
    """Handle WebSocket errors and try to reconnect."""
    global retry_count
    logging.error(f"WebSocket error: {error}")

    if retry_count < MAX_RETRIES:
        retry_count += 1
        logging.info(f"Retrying WebSocket connection ({retry_count}/{MAX_RETRIES})...")
        time.sleep(RETRY_DELAY * retry_count)  # Exponential backoff
        reconnect_websocket()
    else:
        logging.error("Max retries reached. Could not reconnect WebSocket.")

def on_close(ws):
    """Handle WebSocket closing and attempt to reconnect."""
    global retry_count
    logging.warning("WebSocket connection closed.")
    
    if retry_count < MAX_RETRIES:
        retry_count += 1
        logging.info(f"Retrying WebSocket connection ({retry_count}/{MAX_RETRIES})...")
        time.sleep(RETRY_DELAY * retry_count)
        reconnect_websocket()
    else:
        logging.error("Max retries reached. Could not reconnect WebSocket.")

def on_open(ws):
    """Reset retry count when WebSocket successfully connects."""
    global retry_count
    logging.info("WebSocket connection opened.")
    retry_count = 0  # Reset retry counter on successful connection

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