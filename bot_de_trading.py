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
capital_usdt = 10  # Ajusta el capital inicial aquí

# Función para consultar el saldo
def check_balance():
    """Consulta y muestra el balance disponible."""
    try:
        print("Consultando el saldo de la cuenta...")
        balance = exchange.fetch_balance()
        total_balance = balance['total']  # Balance total (incluye todos los activos)
        free_balance = balance['free']  # Balance disponible para operar
        print("Balance total:", total_balance)
        print("Balance disponible:", free_balance)
        return balance
    except Exception as e:
        print(f"Error al consultar el saldo: {e}")
        return None

# Funciones para la estrategia Hull Moving Average (HMA)
def wma(values, length):
    """Cálculo de la Media Móvil Ponderada (WMA)"""
    weights = np.arange(1, length + 1)
    if len(values) < length:
        return np.array([])  # Devolver un arreglo vacío si no hay suficientes datos
    return np.convolve(values, weights/weights.sum(), mode='valid')

def hma(series, length):
    """Cálculo de la Media Móvil de Hull (HMA)"""
    half_length = int(length / 2)
    sqrt_length = int(np.sqrt(length))
    wmaf = wma(series, half_length)
    wmas = wma(series, length)
    
    if len(wmaf) == 0 or len(wmas) == 0:
        return np.array([])
    
    raw_hma = 2 * wmaf[-len(wmas):] - wmas
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
    try:
        print(f"Consultando datos de mercado para {symbol} en el marco temporal {timeframe}...")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Error al obtener datos de mercado: {e}")
        return pd.DataFrame()  # Devuelve un DataFrame vacío en caso de error

# Función para ejecutar la estrategia de trading
def execute_trading_strategy():
    global capital_usdt
    
    # Consultar saldo antes de operar
    balance = check_balance()
    if not balance:
        print("No se pudo obtener el saldo. Reintentando...")
        return

    # Obtener datos de mercado
    data = fetch_market_data(symbol)
    if data.empty:
        print("No se pudieron obtener datos de mercado. Reintentando...")
        return

    data = apply_hull_trend(data, 14)  # Aplicar HMA con un periodo de 14

    if data['trend'].isna().all():
        print("No hay suficientes datos para aplicar la estrategia. Esperando más datos...")
        return

    latest_signal = data.iloc[-1]['trend']

    if latest_signal == 'buy':
        print("Señal de compra detectada. Ejecutando compra...")
        amount_to_buy = capital_usdt / float(data.iloc[-1]['close'])
        try:
            order = exchange.create_market_buy_order(symbol, amount_to_buy)
            print(f"Orden de compra ejecutada: {order}")
            capital_usdt = 0
        except Exception as e:
            print(f"Error al ejecutar la compra: {e}")
    elif latest_signal == 'sell':
        print("Señal de venta detectada. Ejecutando venta...")
        btc_balance = balance['total'].get('BTC', 0)
        if btc_balance > 0:
            try:
                order = exchange.create_market_sell_order(symbol, btc_balance)
                print(f"Orden de venta ejecutada: {order}")
                capital_usdt = btc_balance * float(data.iloc[-1]['close'])
            except Exception as e:
                print(f"Error al ejecutar la venta: {e}")
        else:
            print("No hay saldo de BTC disponible para vender.")
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
        def execute_trading_strategy():
    # ... (tu código para obtener el saldo y los datos del mercado)

    if 'USDT' in balance['total']:
        usdt_balance = balance['total']['USDT']
        if usdt_balance > 0:
            # ... (tu lógica de compra/venta usando usdt_balance)
        else:
            print("No tienes suficiente saldo USDT para operar.")
    else:
        print("No se encontró saldo USDT en tu cuenta.")
