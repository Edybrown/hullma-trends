import time
import hmac
import hashlib
import requests
import websocket
import json
import logging
import numpy as np

# Configuración de logging
logging.basicConfig(level=logging.INFO)

# Credenciales de acceso
ACCESS_ID = "2A8AE2B7B0D0458CBF00F06620FA4E7C"
SECRET_KEY = "958D43B4E07D47E8B84E7DEEA58AAF321818AB5A0452FA80"

# URL base de la API
BASE_URL = "https://api.coinex.com"

# Función para generar la firma HMAC-SHA256
def generate_signature(secret_key, message):
    return hmac.new(bytes(secret_key, 'latin-1'),
                    msg=bytes(message, 'latin-1'),
                    digestmod=hashlib.sha256).hexdigest().lower()

# Función para obtener el saldo
def check_balance():
    url = f'{BASE_URL}/v1/balance'
    timestamp = str(int(time.time() * 1000))
    signature = generate_signature(SECRET_KEY, f"GET/v1/balance{timestamp}")
    
    headers = {
        "X-COINEX-KEY": ACCESS_ID,
        "X-COINEX-SIGN": signature,
        "X-COINEX-TIMESTAMP": timestamp
    }

    response = requests.get(url, headers=headers)
    data = response.json()
    
    if data['code'] == 0:
        balance = data['data']['BTC']['available']
        logging.info(f"Saldo disponible: {balance} BTC")
        return balance
    else:
        logging.error(f"Error al obtener saldo: {data['message']}")
        return 0

# Función para calcular el RSI
def calculate_rsi(data, period):
    delta = np.diff(data)
    gain = delta[delta > 0].mean() if len(delta[delta > 0]) > 0 else 0
    loss = -delta[delta < 0].mean() if len(delta[delta < 0]) > 0 else 0
    
    rs = gain / loss if loss != 0 else gain  # Evitar división por cero
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

# Función para calcular el Hull Moving Average (HMA)
def calculate_hma(data, period):
    wma1 = np.convolve(data, np.ones(period), mode='valid') / period  # Media ponderada simple
    wma2 = np.convolve(data, np.ones(period//2), mode='valid') / (period//2)
    diff = wma1 - wma2
    hma = np.convolve(diff, np.ones(int(np.sqrt(period))), mode='valid') / int(np.sqrt(period))
    
    return hma[-1] if len(hma) > 0 else None

# Función para colocar una orden de mercado
def place_market_order(order_type, quantity):
    order_payload = {
        "method": "order.place",
        "params": {
            "market": "BTCUSDT",
            "price": 0,  # Órdenes de mercado no necesitan precio
            "amount": quantity,
            "side": order_type,
            "type": "market"
        },
        "id": 2
    }
    ws.send(json.dumps(order_payload))
    logging.info(f"Orden de {order_type} a mercado de {quantity} BTC enviada.")

# Función para gestionar reconexión del WebSocket
def on_open(ws):
    logging.info("Conexión WebSocket abierta")
    subscription_message = {
        "method": "state.subscribe",
        "params": {"market_list": ["BTCUSDT", "ETHUSDT", "BNBUSDT"]},
        "id": 1
    }
    ws.send(json.dumps(subscription_message))

def on_message(ws, message):
    logging.info(f"Mensaje recibido: {message}")

def on_error(ws, error):
    logging.error(f"Error en WebSocket: {error}")
    reconnect_ws(ws)

def on_close(ws, close_status_code, close_msg):
    logging.info(f"Conexión WebSocket cerrada: {close_msg}")
    reconnect_ws(ws)

def reconnect_ws(ws):
    logging.info("Reintentando conexión...")
    ws.run_forever()

# Función principal para ejecutar el bot
def main():
    # WebSocket para recibir actualizaciones del mercado
    ws = websocket.WebSocketApp("wss://api.coinex.com/ws/v1/", 
                                on_open=on_open, 
                                on_message=on_message, 
                                on_error=on_error, 
                                on_close=on_close)
    
    # Reintentar conexión en caso de cierre inesperado
    ws.run_forever()

    # Obtener datos del mercado (previamente recopilados)
    market_data = [35000, 35500, 35300, 35900, 36000, 35800, 35600]  # Simulamos precios
    
    # Calcular RSI de 8 y 14 periodos
    rsi_8 = calculate_rsi(market_data, 8)
    rsi_14 = calculate_rsi(market_data, 14)
    logging.info(f"RSI de 8 periodos: {rsi_8}, RSI de 14 periodos: {rsi_14}")
    
    # Calcular Hull Trend (HMA)
    hma_14 = calculate_hma(market_data, 14)
    logging.info(f"HMA de 14 periodos: {hma_14}")
    
    # Lógica de compra/venta según RSI y Hull Trend
    if rsi_14 < 30 and rsi_8 < 30 and hma_14 > market_data[-1]:  # Condición para comprar
        logging.info("Condiciones para compra detectadas.")
        available_balance = check_balance()
        if available_balance >= 0.001:
            place_market_order("buy", 0.001)  # Ejemplo de compra de 0.001 BTC
            time.sleep(5)  # Esperar a que se complete la orden
    elif rsi_14 > 70 and rsi_8 > 70 and hma_14 < market_data[-1]:  # Condición para vender
        logging.info("Condiciones para venta detectadas.")
        available_balance = check_balance()
        if available_balance >= 0.001:
            place_market_order("sell", 0.001)  # Ejemplo de venta de 0.001 BTC
            time.sleep(5)  # Esperar a que se complete la orden

# Ejecutar el bot
if __name__ == "__main__":
    main()
