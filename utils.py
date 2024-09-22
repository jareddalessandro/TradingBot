# utils.py

from binance.client import Client
import config
import logging
import os
from binance import ThreadedWebsocketManager

# Configure logging
logging.basicConfig(
    filename='trading_bot.log',
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

def get_client():
    """Initialize and return the Binance.US client."""
    client = Client(config.API_KEY, config.API_SECRET)
    client.API_URL = 'https://api.binance.us/api'
    return client

def get_websocket_manager():
    """Initialize and return the Binance.US WebSocket manager."""
    twm = ThreadedWebsocketManager(api_key=config.API_KEY, api_secret=config.API_SECRET)
    twm.API_URL = 'wss://stream.binance.us:9443/ws'  # Binance.US WebSocket endpoint
    return twm


def place_order(client, symbol, side, quantity):
    if config.PAPER_TRADING:
        logging.info(f"Simulated {side} order for {quantity} {symbol}")
        return {'status': 'simulated', 'side': side, 'quantity': quantity}
    else:
        # Place a real order
        try:
            order = client.create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            logging.info(f"Order placed: {order}")
            return order
        except Exception as e:
            logging.error(f"Error placing order: {e}")
            return None

def get_symbol_precision(client, symbol):
    """Get the precision required for quantity and price."""
    info = client.get_symbol_info(symbol)
    step_size = None
    tick_size = None
    for f in info['filters']:
        if f['filterType'] == 'LOT_SIZE':
            step_size = float(f['stepSize'])
        if f['filterType'] == 'PRICE_FILTER':
            tick_size = float(f['tickSize'])
    return step_size, tick_size
