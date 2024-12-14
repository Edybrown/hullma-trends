import websocket
import json
import pandas as pd
import numpy as np
import logging
import time
import hmac
import hashlib
import base64

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuración de la API
WEBSOCKET_URL = "wss://phemex.com/ws"
API_KEY = "13412340-2737-4953-879c-8ff573cafa7f"
API_SECRET = "uvCVTlX4UrrG5-OlplsUqIG1uWnuxPmYuC5uuPjP4IBkYTU0MDFkZS0xNzk1LTRlNTMtYWMwYS1jOTJkYjZlYTc3MzU"
SYMBOL = "sBTCUSDT"
TIMEFRAME = 900  # 15 minutos en segundos

# Variables globales
candles_data = []  # Lista para almacenar datos de velas

def weighted_moving_average(data, period):
    weights = np.arange(1, period + 1)
    return data.rolling(period).apply(lambda prices: np.dot(prices, weights) / weights.sum(), raw=True)

def hull_moving_average(data, period):
    wma_half = weighted_moving_average(data, period // 2)
    wma_full = weighted_moving_average(data, period)
    hull_ma = (2 * wma_half - wma_full).rolling(int(np.sqrt(period))).mean()
    return hull_ma

def calculate_rsi(data, period):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def generate_signature(api_secret, expires):
    message = f"{expires}"
    signature = hmac.new(bytes(api_secret, 'utf-8'), bytes(message, 'utf-8'), hashlib.sha256).hexdigest()
    return signature

def authenticate(ws):
    expires = int(time.time()) + 60  # Tiempo de expiración de la firma
    signature = generate_signature(API_SECRET, expires)

    auth_payload = {
        "id": 1,
        "method": "user.auth",
        "params": ["API", API_KEY, signature, expires]
    }
    ws.send(json.dumps(auth_payload))

def process_kline_data(ws, message):
    global candles_data

    # Parsear el mensaje recibido
    data = json.loads(message)

    if "kline" in data.get("type", ""):
        kline = data['kline']

        # Extraer datos de la vela
        new_candle = {
            "timestamp": kline[0],
            "open": float(kline[1]),
            "high": float(kline[2]),
            "low": float(kline[3]),
            "close": float(kline[4]),
            "volume": float(kline[5])
        }

        candles_data.append(new_candle)

        # Asegurar que solo mantenemos los datos necesarios
        if len(candles_data) > 500:
            candles_data.pop(0)

        analyze_market(ws)

def analyze_market(ws):
    global candles_data

    # Convertir datos a DataFrame
    df = pd.DataFrame(candles_data)
    df['close'] = pd.to_numeric(df['close'])

    # Validar datos
    if df.empty or len(df) < 30:
        logging.warning("No hay suficientes datos para el análisis.")
        return

    # Calcular Hull Moving Average y RSI
    df['HullMA'] = hull_moving_average(df['close'], 14)
    df['RSI_fast'] = calculate_rsi(df['close'], 8)
    df['RSI_slow'] = calculate_rsi(df['close'], 14)

    # Eliminar filas con valores NaN
    df = df.dropna()

    # Lógica de señales
    last_row = df.iloc[-1]

    if last_row['RSI_fast'] > 70 and last_row['RSI_slow'] > 70 and last_row['close'] > last_row['HullMA']:
        logging.info(f"Señal de venta detectada: RSI_fast={last_row['RSI_fast']}, RSI_slow={last_row['RSI_slow']}, Precio={last_row['close']}")
        send_alert("Señal de venta detectada")
        place_order(ws, "Sell", 1)
    elif last_row['RSI_fast'] < 30 and last_row['RSI_slow'] < 30 and last_row['close'] < last_row['HullMA']:
        logging.info(f"Señal de compra detectada: RSI_fast={last_row['RSI_fast']}, RSI_slow={last_row['RSI_slow']}, Precio={last_row['close']}")
        send_alert("Señal de compra detectada")
        place_order(ws, "Buy", 1)

def place_order(ws, side, quantity):
    order_payload = {
        "id": 2,
        "method": "order.create",
        "params": {
            "symbol": SYMBOL,
            "side": side,
            "quantity": quantity,
            "price": 0,  # Precio de mercado
            "ordType": "Market"
        }
    }
    ws.send(json.dumps(order_payload))
    logging.info(f"Orden enviada: {side} {quantity} {SYMBOL}")

def send_alert(message):
    # Puedes integrar aquí Telegram, correo electrónico, etc.
    logging.info(f"Alerta enviada: {message}")

def subscribe_kline(ws):
    ws.send(json.dumps({
        "id": 3,
        "method": "kline.subscribe",
        "params": [SYMBOL, TIMEFRAME]
    }))

def on_message(ws, message):
    process_kline_data(ws, message)

def on_open(ws):
    authenticate(ws)
    subscribe_kline(ws)

def on_error(ws, error):
    logging.error(f"Error en WebSocket: {error}")

def on_close(ws):
    logging.info("WebSocket cerrado")

def main():
    while True:
        try:
            ws = websocket.WebSocketApp(
                WEBSOCKET_URL,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            ws.on_open = on_open
            ws.run_forever()
        except Exception as e:
            logging.error(f"Error en WebSocket, intentando reconectar: {e}")
            time.sleep(5)  # Esperar antes de intentar reconectar

if __name__ == "__main__":
    main()
