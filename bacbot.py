import requests
import pandas as pd
import talib
import os
import logging
import csv
import datetime
import pytz
import numpy as np
import json

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def obtener_tiempo_local():
    dt_utc = datetime.datetime.now(tz=pytz.utc)
    return dt_utc

def obtener_datos_coinex(simbolo, intervalo, limit=1000):
    intervalos_coinex = {
        "1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min",
        "30m": "30min", "1h": "1hour", "2h": "2hour", "4h": "4hour",
        "6h": "6hour", "12h": "12hour", "1d": "1day", "3d": "3day",
        "1w": "1week"
    }

    if intervalo not in intervalos_coinex:
        logging.error(f"Intervalo no válido: {intervalo}. Intervalos válidos: {list(intervalos_coinex.keys())}")
        return None

    intervalo_coinex = intervalos_coinex[intervalo]
    market = simbolo.replace("/", "")
    url = f"https://api.coinex.com/v2/spot/kline?market={market}&type={intervalo_coinex}&limit={limit}" # Endpoint corregido

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data.get('code') == 0 and 'data' in data and data['data']: #Comprobar que data no este vacio
            klines = data['data']
            # Convertir klines a lista de diccionarios si es necesario
            if isinstance(klines, list):
                if isinstance(klines[0],list): #Si viene como lista de listas
                    df = pd.DataFrame(klines, columns=['time', 'open', 'close', 'high', 'low', 'volume'])
                elif isinstance(klines[0], dict): #Si viene como lista de diccionarios, aunque la doc dice que no
                    df = pd.DataFrame(klines)
                else:
                    logging.error(f"Formato de datos kline inesperado: {type(klines[0])}")
                    print(json.dumps(data, indent=4))
                    return None
            elif isinstance(klines, dict): #Si viene como diccionario
                df = pd.DataFrame.from_dict(klines, orient='index', columns=['open', 'close', 'high', 'low', 'volume'])
                df['time'] = df.index
            else:
                logging.error(f"Formato de datos kline inesperado: {type(klines)}")
                print(json.dumps(data, indent=4))
                return None
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df = df.apply(pd.to_numeric, errors='coerce')
            df.rename(columns={'open':'Open', 'close':'Close', 'high':'High', 'low':'Low', 'volume':'Volume'}, inplace=True)
            return df
        else:
            mensaje_error = data.get('message', f"Código de error desconocido: {data.get('code', 'sin codigo')}")
            logging.error(f"Error en la respuesta de la API: {mensaje_error}")
            print(json.dumps(data, indent=4)) #Imprime el json para debug
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al obtener datos de CoinEx: {e}")
        return None
    except (KeyError, IndexError, TypeError, ValueError) as e:
        logging.error(f"Error al procesar datos de CoinEx, posible cambio en formato de API: {e}")
        print(json.dumps(data, indent=4)) #Imprime el json para debug
        return None
def calcular_hma(data, period):
    """Calcula la Hull Moving Average."""
    wma1 = talib.WMA(data, period // 2)
    wma2 = talib.WMA(data, period)
    delta_wma = 2 * wma1 - wma2
    hma = talib.WMA(delta_wma, int(np.sqrt(period)))
    return hma

def aplicar_estrategia(df, rsi_period_1=2, rsi_period_2=14, hma_period=20):
    """Aplica la estrategia de trading basada en Doble RSI y HMA."""

    if 'Close' not in df.columns:
        logging.error("La columna 'Close' no está presente en el DataFrame.")
        return df, []
    
    operaciones = []
    
    try:
        df['RSI_1'] = talib.RSI(df['Close'], timeperiod=rsi_period_1)
        df['RSI_2'] = talib.RSI(df['Close'], timeperiod=rsi_period_2)
        df['HMA'] = calcular_hma(df['Close'], hma_period)

        for i in range(1, len(df)):
            precio_actual = df['Close'][i]
            hma_actual = df['HMA'][i]
            rsi_1_actual = df['RSI_1'][i]
            rsi_2_actual = df['RSI_2'][i]
            rsi_1_anterior = df['RSI_1'][i-1]

            # Señal de Compra:
            # 1. RSI de corto plazo cruza por encima de 30.
            # 2. RSI de largo plazo está por encima de 50.
            # 3. El precio cruza por encima de la HMA.
            if rsi_1_actual > 30 and rsi_1_anterior <= 30 and rsi_2_actual > 50 and precio_actual > hma_actual:
                operaciones.append([df.index[i], "COMPRA", precio_actual])
                logging.info(f"Señal de COMPRA en {df.index[i]}: Precio {precio_actual}, HMA {hma_actual}, RSI1 {rsi_1_actual}, RSI2 {rsi_2_actual}")
                
            # Señal de Venta:
            # 1. RSI de corto plazo cruza por debajo de 70.
            # 2. RSI de largo plazo está por debajo de 50.
            # 3. El precio cruza por debajo de la HMA.
            elif rsi_1_actual < 70 and rsi_1_anterior >= 70 and rsi_2_actual < 50 and precio_actual < hma_actual:
                operaciones.append([df.index[i], "VENTA", precio_actual])
                logging.info(f"Señal de VENTA en {df.index[i]}: Precio {precio_actual}, HMA {hma_actual}, RSI1 {rsi_1_actual}, RSI2 {rsi_2_actual}")

        return df, operaciones
    except Exception as e:
        logging.error(f"Error al aplicar la estrategia: {e}")
        return df, []
def registrar_operaciones(simbolo, intervalo, operaciones):
    nombre_archivo = f"registros/{simbolo}_{intervalo}.csv"
    os.makedirs("registros", exist_ok=True) # Crea el directorio si no existe.
    try:
        with open(nombre_archivo, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Fecha", "Tipo", "Precio"]) # Encabezado del CSV
            for operacion in operaciones:
                writer.writerow(operacion)
    except Exception as e:
        logging.error(f"Error al registrar operaciones: {e}")

if __name__ == "__main__":
    simbolos = ["BTC/USDT", "ETH/USDT"]  # <-- Definición de simbolos
    intervalos = ["1m", "5m", "1h"]  # <-- Definición de intervalos

    tiempo_inicio = obtener_tiempo_local()
    logging.info(f"Inicio del backtesting (UTC): {tiempo_inicio}")

    for simbolo in simbolos:
        for intervalo in intervalos:
            logging.info(f"Descargando datos de {simbolo} en {intervalo}...")
            df = obtener_datos_coinex(simbolo, intervalo, limit=1000)
            if df is not None:
                logging.info(f"Datos descargados correctamente para {simbolo} en {intervalo}")
                df = calcular_indicadores(df)
                if df is not None:
                    logging.info("Aplicando estrategia...")
                    df, operaciones = aplicar_estrategia(df)
                    if operaciones:
                        logging.info(f"Registrando operaciones para {simbolo} en {intervalo}...")
                        registrar_operaciones(simbolo.replace("/", ""), intervalo, operaciones)
                        logging.info(f"Operaciones registradas en registros/{simbolo.replace('/', '')}_{intervalo}.csv")
                    else:
                        logging.info(f"No hubo operaciones para {simbolo} en {intervalo}") #Añadido mensaje informativo
                else:
                    logging.warning(f"No se pudieron calcular los indicadores para {simbolo} en {intervalo}")
            else:
                logging.error(f"Error al obtener datos para {simbolo} en {intervalo}")

    tiempo_fin = obtener_tiempo_local()
    logging.info(f"Fin del backtesting (UTC): {tiempo_fin}")
