import websocket
import json
import pandas as pd
import numpy as np
import time
import logging

# Configuración de logs
logging.basicConfig(
    filename="trading_bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Configuración general
SYMBOL = "BTCUSDT"  # Sin el prefijo 's'
TIMEFRAME = 86400  # 1 día (86400 segundos)

# Configuración del WebSocket
WEBSOCKET_URL = "wss://ws.phemex.com/ws"

# Variables globales para almacenar los datos de las velas
candles_data = []

# Función para procesar los datos de las velas recibidos
def process_kline_data(ws, message):
    global candles_data
    try:
        # Analizar el mensaje JSON
        data = json.loads(message)
        
        # Verificar si es un mensaje de kline
        if "method" in data and data["method"] == "kline.update":
            kline = data["params"][0]
            timestamp = kline["t"]
            open_price = float(kline["o"])
            high_price = float(kline["h"])
            low_price = float(kline["l"])
            close_price = float(kline["c"])
            volume = float(kline["v"])
            
            # Almacenar los datos de la vela
            candles_data.append({
                "timestamp": timestamp,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume
            })
            
            # Mantener solo los últimos 1000 datos
            if len(candles_data) > 1000:
                candles_data = candles_data[-1000:]
            
            # Mostrar los últimos datos
            logging.info(f"Nueva vela: {candles_data[-1]}")
            
            # Si tenemos suficientes datos, podemos comenzar a analizar
            if len(candles_data) > 1:
                df = pd.DataFrame(candles_data)
                # Procesar análisis aquí (RSI, HullMA, señales, etc.)
                analyze_data(df)
    
    except Exception as e:
        logging.error(f"Error al procesar los datos del kline: {e}")

# Función de análisis de los datos de las velas
def analyze_data(df):
    try:
        # Calcular el RSI
        rsi_fast = calculate_rsi(df['close'], 14)
        rsi_slow = calculate_rsi(df['close'], 28)
        
        # Calcular HullMA
        hullma = hull_moving_average(df['close'], 14)
        
        # Lógica de trading basada en RSI y HullMA
        latest = df.iloc[-1]
        
        if rsi_fast.iloc[-1] > rsi_slow.iloc[-1] and latest['close'] > hullma.iloc[-1]:
            logging.info("Señal de compra detectada.")
            # Coloca tu código de compra aquí
        elif rsi_fast.iloc[-1] < rsi_slow.iloc[-1] and latest['close'] < hullma.iloc[-1]:
            logging.info("Señal de venta detectada.")
            # Coloca tu código de venta aquí
    
    except Exception as e:
        logging.error(f"Error al analizar los datos: {e}")

# Función para calcular el RSI
def calculate_rsi(data, period):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Función para calcular Hull Moving Average
def hull_moving_average(data, period):
    wma_half = data.rolling(window=period//2).mean()
    wma_full = data.rolling(window=period).mean()
    return (2 * wma_half - wma_full).rolling(window=int(np.sqrt(period))).mean()

# Función para suscribirse al WebSocket
def subscribe_kline():
    def on_error(ws, error):
        logging.error(f"Error en WebSocket: {error}")

    def on_close(ws):
        logging.info("WebSocket cerrado")
    
    ws = websocket.WebSocketApp(
        WEBSOCKET_URL,
        on_message=process_kline_data,
        on_error=on_error,
        on_close=on_close,
    )
    
    # Suscripción al flujo de velas para el símbolo y timeframe deseados
    subscription_message = {
        "id": 0,
        "method": "kline.subscribe",
        "params": [
            SYMBOL,
            TIMEFRAME
        ]
    }
    
    ws.on_open = lambda ws: ws.send(json.dumps(subscription_message))
    
    # Mantener el WebSocket en ejecución
    ws.run_forever()

# Función principal
if __name__ == "__main__":
    logging.info("Iniciando bot y suscripción al WebSocket...")
    subscribe_kline()
