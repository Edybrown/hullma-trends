import ccxt
import time
import pandas as pd
import numpy as np
from datetime import datetime

# Configurar la API de Phemex
exchange = ccxt.phemex({
    'apiKey': '13412340-2737-4953-879c-8ff573cafa7f',
    'secret': 'uvCVTlX4UrrG5-OlplsUqIG1uWnuxPmYuC5uuPjP4IBkYTU0MDFkZS0xNzk1LTRlNTMtYWMwYS1jOTJkYjZlYTc3MzU',
    'enableRateLimit': True,
})

# Configuración del símbolo y cantidad
symbol = 'BTC/USDT'  # Para mercado spot
capital_usdt = 100  # Ajusta el capital inicial aquí

# Funciones para la estrategia Hull Moving Average (HMA)
def wma(values, length):
    """Cálculo de la Media Móvil Ponderada (WMA)"""
    weights = np.arange(1, length + 1)
    # Asegurarse de que la longitud de los valores sea suficiente
    if len(values) < length:
        return np.array([])  # Devolver un arreglo vacío si no hay suficientes datos
    return np.convolve(values, weights/weights.sum(), mode='valid')

def hma(series, length):
    """Cálculo de la Media Móvil de Hull (HMA)"""
    half_length = int(length / 2)
    sqrt_length = int(np.sqrt(length))
    wmaf = wma(series, half_length)
    wmas = wma(series, length)
    
    # Asegurarse de que ambos WMA tengan la misma longitud antes de restarlos
    if len(wmaf) == 0 or len(wmas) == 0:
        return np.array([])  # Devolver un arreglo vacío si los cálculos no son posibles
    
    raw_hma = 2 * wmaf[-len(wmas):] - wmas  # Ajuste de longitud para la resta
    final_hma = wma(raw_hma, sqrt_length)

    return final_hma

def apply_hull_trend(data, period):
    """Aplicar la estrategia de Hull Moving Average al dataframe de datos"""
    hma_values = hma(data['close'].values, period)
    
    if len(hma_values) == 0:
        data['hma'] = np.nan
        data['hma_shifted'] = np.nan
        data['trend'] = np.nan
        return data

    data = data.iloc[-len(hma_values):]  # Recortar el dataframe al tamaño de los resultados de HMA
    data['hma'] = hma_values
    data['hma_shifted'] = data['hma'].shift(1)
    data['trend'] = np.where(data['hma'] > data['hma_shifted'], 'buy', 'sell')
    
    return data

# Función para obtener datos de mercado
def fetch_market_data(symbol, timeframe='15m', limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Función para ejecutar la estrategia de trading
def execute_trading_strategy():
    global capital_usdt
    
    # Obtener datos de mercado
    data = fetch_market_data(symbol)
    data = apply_hull_trend(data, 14)  # Aplicar HMA con un periodo de 14

    # Verificar si hay suficientes datos
    if data['trend'].isna().all():
        print("No hay suficientes datos para aplicar la estrategia. Esperando más datos...")
        return

    # Obtener la señal de compra/venta más reciente
    latest_signal = data.iloc[-1]['trend']

    # Ejecutar la operación según la señal
    if latest_signal == 'buy':
        print("Señal de compra detectada. Ejecutando compra...")
        amount_to_buy = capital_usdt / float(data.iloc[-1]['close'])
        order = exchange.create_market_buy_order(symbol, amount_to_buy)
        print(f"Orden de compra ejecutada: {order}")
        capital_usdt = 0  # Se ha invertido todo el capital
    elif latest_signal == 'sell':
        print("Señal de venta detectada. Ejecutando venta...")
        balance = exchange.fetch_balance()
        btc_balance = balance['total']['BTC']
        if btc_balance > 0:
            order = exchange.create_market_sell_order(symbol, btc_balance)
            print(f"Orden de venta ejecutada: {order}")
            capital_usdt = btc_balance * float(data.iloc[-1]['close'])
    else:
        print("No hay señal de operación en este momento.")

# Bucle principal para ejecutar el bot
while True:
    try:
        execute_trading_strategy()
        time.sleep(900)  # Esperar 15 minutos antes de la siguiente ejecución
    except Exception as e:
        print(f"Error en la ejecución del bot: {e}")
        time.sleep(60)  # Esperar un minuto antes de reintentar
