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

# Configuración de la API de CoinEx
WEBSOCKET_URL = "wss://socket.coinex.com/"
API_KEY = "2A8AE2B7B0D0458CBF00F06620FA4E7C"
API_SECRET = "958D43B4E07D47E8B84E7DEEA58AAF321818AB5A0452FA80"
SYMBOL = "BTCUSDT"  # Par de mercado
TIMEFRAME = 900  # 15 minutos en segundos

# Configuración de los indicadores
RSI_FAST_PERIOD =8
RSI_SLOW_PERIOD = 14
HULL_PERIOD = 14

# Función para calcular el RSI
def calculate_rsi(data, period):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Función para calcular el Hull Moving Average (HullMA)
def calculate_hullma(data, period):
    wma_half = data.rolling(window=period // 2).mean()
    wma_full = data.rolling(window=period).mean()
    diff = 2 * wma_half - wma_full
    hullma = diff.rolling(window=int(np.sqrt(period))).mean()
    return hullma

# Función para procesar datos de velas y generar señales
def process_kline_data(df, kline_data):
    # Agregar nueva vela al DataFrame
    close_price = float(kline_data['close'])
    df = df.append({"timestamp": kline_data['time'], "close": close_price}, ignore_index=True)

    if len(df) >= max(RSI_SLOW_PERIOD, RSI_FAST_PERIOD, HULL_PERIOD):
        # Calcular RSI y HullMA
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

    return df

# Función para realizar la orden (pendiente de implementar con API privada de CoinEx)
def place_order(order_type):
    logging.info(f"Orden de {order_type} (pendiente de implementar)")

# Función para suscribirse a velas
def subscribe_kline(ws):
    payload = {
        "method": "kline.subscribe",
        "params": [SYMBOL, 60],  # Intervalo en segundos
        "id": 1
    }
    ws.send(json.dumps(payload))
    logging.info(f"Suscripción a velas para {SYMBOL} enviada.")

# Función cuando se abre la conexión
def on_open(ws):
    subscribe_kline(ws)

# Función cuando se recibe un mensaje
def on_message(ws, message):
    global df
    data = json.loads(message)
    if "params" in data and "method" in data and data["method"] == "kline.update":
        kline_data = data['params'][0]
        df = process_kline_data(df, kline_data)

# Función cuando hay un error en WebSocket
def on_error(ws, error):
    logging.error(f"Error en WebSocket: {error}")

# Función cuando se cierra la conexión
def on_close(ws, close_status_code, close_msg):
    logging.info(f"WebSocket cerrado: {close_status_code} - {close_msg}")

# Función principal
def main():
    global df
    df = pd.DataFrame(columns=["timestamp", "close"])  # DataFrame para almacenar las velas

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
