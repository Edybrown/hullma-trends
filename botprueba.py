import websocket
import json
import time
import hmac
import hashlib
import requests

def on_open(ws):
    subscription_message = {
        "method": "state.subscribe",
        "params": {"market_list": ["BTCUSDT", "ETHUSDT", "BNBUSDT"]},
        "id": 1
    }
    ws.send(json.dumps(subscription_message))

def on_message(ws, message):
    print(message)

ws = websocket.WebSocketApp("wss://api.coinex.com/ws/v1/", on_open=on_open, on_message=on_message)
ws.run_forever()
