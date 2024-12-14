import websocket
import json
import time
import logging
import hmac
import hashlib
import numpy as np
import pandas as pd

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuración de la API
WEBSOCKET_URL = "wss://ws.phemex.com"
API_KEY = '13412340-2737-4953-879c-8ff573cafa7f'
API_SECRET = 'uvCVTlX4UrrG5-OlplsUqIG1uWnuxPmYuC5uuPjP4IBkYTU0MDFkZS0xNzk1LTRlNTMtYWMwYS1jOTJkYjZlYTc3MzU'
SYMBOL = "sBTCUSDT"
TIMEFRAME = 900  # 15 minutos en segundos

# Configuración de los indicadores
RSI_FAST_PERIOD = 5
RSI_SLOW_PERIOD = 14
HULL_PERIOD = 14

# Función para generar la firma
def generate_signature(api_secret, expires, method, request_path, body=""):
    message = f"{expires}{method}{request_path}{body}"
    signature = hmac.new(bytes(api_secret, 'utf-8'), bytes(message, 'utf-8'), hashlib.sha256).hexdigest()
    return signature

# Función de autenticación
def authenticate(ws):
    expires = int(time.time()) + 60  # Tiempo de expiración de la firma
    request_path = "/user.auth"  # Path del endpoint para autenticación
    signature = generate_signature(API_SECRET, expires, "POST", request_path)

    auth_payload = {
        "id": 1,
        "method": "user.auth",
        "params": [API_KEY, signature, expires]
    }
    ws.send(json.dumps(auth_payload))
    logging.info(f"Autenticado con la firma: {signature}")

# Función para calcular el RSI
def calculate_rsi(data, period):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Función para calcular el Hull Moving Average (HullMA)
def calculate_hullma(data, period):
    wma_half = data.rolling(window=period//2).mean()
    wma_full = data.rolling(window=period).mean()
    diff = 2 * wma_half - wma_full
    hullma = diff.rolling(window=int(np.sqrt(period))).mean()
    return hullma

# Función para procesar datos de velas y generar señales
def process_kline_data(ws, message, df):
    data = json.loads(message)
    if "kline" in data.get("type", ""):
        kline = data['kline']
        close_price = float(kline['close'])
        df = df.append({"timestamp": kline['timestamp'], "close": close_price}, ignore_index=True)

        if len(df) >= max(RSI_SLOW_PERIOD, RSI_FAST_PERIOD, HULL_PERIOD):
            # Calculando RSI y HullMA
            df['rsi_fast'] = calculate_rsi(df['close'], RSI_FAST_PERIOD)
            df['rsi_slow'] = calculate_rsi(df['close'], RSI_SLOW_PERIOD)
            df['hullma'] = calculate_hullma(df['close'], HULL_PERIOD)

            rsi_fast = df['rsi_fast'].iloc[-1]
            rsi_slow = df['rsi_slow'].iloc[-1]
            hullma = df['hullma'].iloc[-1]
            last_close = df['close'].iloc[-1]

            # Señales de compra y venta
            if rsi_fast > rsi_slow and last_close > hullma:
                logging.info("Señal de COMPRA generada")
                place_order("buy")
            elif rsi_fast < rsi_slow and last_close < hullma:
                logging.info("Señal de VENTA generada")
                place_order("sell")

# Función para realizar la orden
def place_order(order_type):
    # Aquí debes integrar el código para hacer la orden de compra/venta en la API de Phemex
    logging.info(f"Ejecutando orden de tipo: {order_type}")

# Función para suscribirse a las velas
def subscribe_kline(ws):
    ws.send(json.dumps({
        "id": 3,
        "method": "kline.subscribe",
        "params": [SYMBOL, TIMEFRAME]
    }))

# Función cuando se abre la conexión
def on_open(ws):
    authenticate(ws)
    subscribe_kline(ws)

# Función cuando se recibe un mensaje
def on_message(ws, message):
    df = pd.DataFrame(columns=["timestamp", "close"])  # DataFrame para almacenar las velas
    process_kline_data(ws, message, df)

# Función cuando hay un error en WebSocket
def on_error(ws, error):
    logging.error(f"Error en WebSocket: {error}")

# Función cuando se cierra la conexión
def on_close(ws, close_status_code, close_msg):
    logging.info(f"WebSocket cerrado: {close_status_code} - {close_msg}")

# Función principal
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
