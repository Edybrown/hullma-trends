import websocket
import json
import time
import hashlib
import hmac
import logging
import requests
import numpy as np
import pandas as pd

# Configuración de logging
logging.basicConfig(level=logging.INFO)

# Variables de configuración
API_KEY = '13412340-2737-4953-879c-8ff573cafa7f'
API_SECRET = 'uvCVTlX4UrrG5-OlplsUqIG1uWnuxPmYuC5uuPjP4IBkYTU0MDFkZS0xNzk1LTRlNTMtYWMwYS1jOTJkYjZlYTc3MzU'
WEBSOCKET_URL = 'wss://ws.phemex.com'
REST_API_URL = 'https://api.phemex.com'

# Función para generar la firma para autenticación
def generate_signature(secret_key, expires):
    message = f'{API_KEY}{expires}'
    signature = hmac.new(bytes(secret_key, 'utf-8'), msg=bytes(message, 'utf-8'), digestmod=hashlib.sha256).hexdigest()
    return signature

# Función para autenticar en el WebSocket
def authenticate(ws):
    expires = int(time.time()) + 60  # Expiración de la firma
    signature = generate_signature(API_SECRET, expires)

    auth_payload = {
        "id": 1,
        "method": "user.auth",
        "params": [API_KEY, signature, expires]
    }
    ws.send(json.dumps(auth_payload))
    logging.info(f"Autenticación enviada: {auth_payload}")

# Función para suscribirse al canal de velas
def subscribe_kline(ws, symbol='BTCUSD', interval='15m'):
    payload = {
        "id": 2,
        "method": "trade.subscribe",
        "params": [symbol, interval]
    }
    ws.send(json.dumps(payload))
    logging.info(f"Suscripción a Kline enviada: {payload}")

# Función para procesar los datos de Kline recibidos
def process_kline_data(ws, message):
    try:
        data = json.loads(message)
        if 'params' in data and 'data' in data['params']:
            kline_data = data['params']['data']
            logging.info(f"Datos de Kline recibidos: {kline_data}")
            # Aquí se realiza el análisis de los datos y la toma de decisiones
            analyze_market(kline_data)
    except Exception as e:
        logging.error(f"Error al procesar el mensaje de Kline: {e}")

# Función para calcular el Hull Moving Average (Hull MA)
def hull_moving_average(data, period):
    weights = np.array([2 * np.arange(1, period // 2 + 1), np.arange(1, period // 2 + 1)])
    wma_half = pd.Series(data['close']).rolling(window=period // 2).mean()
    wma_full = pd.Series(data['close']).rolling(window=period).mean()

    hull = np.sqrt(wma_half - wma_full)
    return hull

# Función para calcular el RSI (Relative Strength Index) doble
def double_rsi(data, fast_period=7, slow_period=14):
    delta = pd.Series(data['close']).diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # RSI rápido
    avg_gain_fast = gain.rolling(window=fast_period).mean()
    avg_loss_fast = loss.rolling(window=fast_period).mean()
    rs_fast = avg_gain_fast / avg_loss_fast
    rsi_fast = 100 - (100 / (1 + rs_fast))

    # RSI lento
    avg_gain_slow = gain.rolling(window=slow_period).mean()
    avg_loss_slow = loss.rolling(window=slow_period).mean()
    rs_slow = avg_gain_slow / avg_loss_slow
    rsi_slow = 100 - (100 / (1 + rs_slow))

    return rsi_fast, rsi_slow

# Función para analizar el mercado con Hull MA y RSI
def analyze_market(kline_data):
    df = pd.DataFrame(kline_data)
    df['close'] = df['close'].astype(float)  # Asegurar que los datos de cierre sean flotantes

    # Cálculo de Hull MA y RSI doble
    hull = hull_moving_average(df, period=14)
    rsi_fast, rsi_slow = double_rsi(df)

    # Estrategia de señales: ambas señales deben coincidir
    if hull[-1] > hull[-2] and rsi_fast[-1] < 30 and rsi_slow[-1] < 30:
        logging.info("Señal de compra detectada: Hull MA y RSI coinciden")
        place_order('buy', 1)
    elif hull[-1] < hull[-2] and rsi_fast[-1] > 70 and rsi_slow[-1] > 70:
        logging.info("Señal de venta detectada: Hull MA y RSI coinciden")
        place_order('sell', 1)

# Función para colocar una orden
def place_order(order_type, quantity):
    order_payload = {
        "method": "order.place",
        "params": {
            "symbol": "BTCUSD",
            "side": order_type,  # 'buy' o 'sell'
            "size": quantity,
            "price": 0,  # Asegúrate de definir la lógica para el precio
        }
    }
    response = requests.post(f'{REST_API_URL}/order', json=order_payload, headers={
        'x-phemex-api-key': API_KEY,
        'x-phemex-api-secret': API_SECRET
    })
    logging.info(f"Orden {order_type} enviada: {response.json()}")

# Función para enviar un heartbeat
def send_heartbeat(ws):
    heartbeat_payload = {
        "id": 3,
        "method": "server.ping",
        "params": []
    }
    ws.send(json.dumps(heartbeat_payload))
    logging.info("Heartbeat enviado")

# Función para manejar errores
def on_error(ws, error):
    logging.error(f"Error en WebSocket: {error}")

# Función para manejar cierre de conexión
def on_close(ws, close_status_code, close_msg):
    logging.info(f"WebSocket cerrado: {close_status_code} - {close_msg}")

# Función para manejar apertura de conexión
def on_open(ws):
    authenticate(ws)
    subscribe_kline(ws)
    send_heartbeat(ws)  # Enviar primer heartbeat

# Función para manejar mensajes
def on_message(ws, message):
    process_kline_data(ws, message)
    time.sleep(30)  # Espera antes de enviar el siguiente heartbeat
    send_heartbeat(ws)

# Función principal que inicia el WebSocket
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
            time.sleep(10)  # Espera antes de intentar reconectar

if __name__ == "__main__":
    main()
