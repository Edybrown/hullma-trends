import yfinance as yf
import pandas as pd
import talib
import os
import logging
import datetime
import numpy as np

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def obtener_datos(simbolo, periodo, intervalo):
    nombre_archivo = f"data/{simbolo}_{periodo}_{intervalo}.csv"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(nombre_archivo):
        logging.info(f"Cargando datos desde {nombre_archivo}")
        try:
            df = pd.read_csv(nombre_archivo, index_col="Date", parse_dates=True)
            return df
        except pd.errors.EmptyDataError:
            logging.warning(f"Archivo {nombre_archivo} vacío. Descargando datos...")

    logging.info(f"Descargando datos de {simbolo} en {intervalo}...")
    try:
        data = yf.download(simbolo, period=periodo, interval=intervalo)
        if data.empty:
            logging.warning(f"No se encontraron datos para {simbolo} en {intervalo}")
            return None
        data.to_csv(nombre_archivo)
        return data
    except Exception as e:
        logging.error(f"Error al descargar datos de {simbolo}: {e}")
        return None

def calcular_indicadores(df):
    try:
        df['RSI_14'] = talib.RSI(df['Close'], timeperiod=14)
        df['RSI_7'] = talib.RSI(df['Close'], timeperiod=7)
        df['HMA_9'] = talib.HMA(df['Close'], timeperiod=9)
        return df
    except Exception as e:
        logging.error(f"Error al calcular indicadores: {e}")
        return None

def aplicar_estrategia(df, stop_loss_percent=0.01):
    df['Signal'] = 0
    df['Posicion'] = 0 # 1 para comprado, -1 para vendido
    df['Retorno'] = 0.0
    capital = 1000  # Capital inicial
    capital_inicial = capital
    operaciones = []

    for i in range(1, len(df)):
        if (df['RSI_7'][i] > df['RSI_14'][i] and df['RSI_7'][i-1] <= df['RSI_14'][i-1] and df['Close'][i] > df['HMA_9'][i]):
            if df['Posicion'][i-1] == 0: # Solo si no hay una posición abierta
                df['Signal'][i] = 1  # Señal de compra
                df['Posicion'][i] = 1
                cantidad = capital / df['Close'][i]
                capital = capital - cantidad * df['Close'][i]
                operaciones.append({'Fecha': df.index[i], 'Tipo': 'Compra', 'Precio': df['Close'][i], 'Cantidad': cantidad, 'Capital': capital})
                logging.info(f"{df.index[i]} - Compra {simbolo} en {intervalo} a {df['Close'][i]}")

        elif df['Posicion'][i-1] == 1: # Si hay una posición comprada
            if (df['Close'][i] < df['Close'][i-1] * (1 - stop_loss_percent)):  # Stop loss (usando el cierre anterior)
                df['Signal'][i] = -1
                df['Posicion'][i] = 0
                retorno = (df['Close'][i] - df['Close'][i-1]) / df['Close'][i-1]
                capital += cantidad * df['Close'][i]
                operaciones.append({'Fecha': df.index[i], 'Tipo': 'Venta (Stop Loss)', 'Precio': df['Close'][i], 'Cantidad': cantidad, 'Capital': capital, 'Retorno': retorno})
                logging.info(f"{df.index[i]} - Venta por Stop Loss {simbolo} en {intervalo} a {df['Close'][i]}, Pérdida: {retorno:.2%}")
            elif (df['RSI_7'][i] < df['RSI_14'][i] and df['RSI_7'][i-1] >= df['RSI_14'][i-1]):
                df['Signal'][i] = -1
                df['Posicion'][i] = 0
                retorno = (df['Close'][i] - df['Close'][i-1]) / df['Close'][i-1]
                capital += cantidad * df['Close'][i]
                operaciones.append({'Fecha': df.index[i], 'Tipo': 'Venta (Señal)', 'Precio': df['Close'][i], 'Cantidad': cantidad, 'Capital': capital, 'Retorno': retorno})
                logging.info(f"{df.index[i]} - Venta por señal {simbolo} en {intervalo} a {df['Close'][i]}, Ganancia/Pérdida: {retorno:.2%}")
            else:
                df['Posicion'][i] = df['Posicion'][i-1] #Mantenemos la posicion anterior

    df['Retorno_Acumulado'] = (1 + df['Retorno']).cumprod() - 1
    df['Capital_Final'] = capital
    df['Capital_Inicial'] = capital_inicial
    return df, operaciones

def analizar_resultados(df, simbolo, intervalo, operaciones):
    ganancias = df[df['Retorno'] > 0]['Retorno'].sum()
    perdidas = df[df['Retorno'] < 0]['Retorno'].sum()
    total_operaciones = len(operaciones)
    operaciones_ganadoras = sum(1 for op in operaciones if op.get('Retorno', 0) > 0)
    operaciones_perdedoras = sum(1 for op in operaciones if op.get('Retorno', 0) < 0)

    if total_operaciones > 0:
        ratio_ganancia_perdida = abs(ganancias) / abs(perdidas) if perdidas != 0 else float('inf')
        porcentaje_ganadoras = (operaciones_ganadoras / total_operaciones) * 100
    else:
        ratio_ganancia_perdida = 0
        porcentaje_ganadoras = 0
    
    capital_final = df['Capital_Final'].iloc[-1]
    capital_inicial = df['Capital_Inicial'].iloc[-1]
    beneficio_neto = capital_final - capital_inicial
    retorno_total = (beneficio_neto / capital_inicial)

    logging.info(f"Resumen de {simbolo} en {intervalo}:")
    logging.info(f"Capital inicial: {capital_inicial:.2f}")
    logging.info(f"Capital final: {capital_final:.2f}")
    logging.info(f"Beneficio neto: {beneficio_neto:.2f}")
    logging.info(f"Retorno total: {retorno_total:.2%}")
    logging.info(f"Ganancias totales: {ganancias:.2%}")
    logging.info(f"Pérdidas totales: {perdidas:.2%}")
    logging.info(f"Total de operaciones: {total_operaciones}")
    logging.info(f"Operaciones ganadoras: {operaciones_ganadoras}")
    logging.info(f"Operaciones perdedoras: {operaciones_perdedoras}")
    logging.info(f"Ratio Ganancia/Pérdida: {ratio_ganancia_perdida:.2f}")
    logging.info(f"Porcentaje de operaciones ganadoras: {porcentaje_ganadoras:.2f}%")

simbolos = ["AAPL", "MSFT", "GOOG"]
periodo = "1y"
intervalos = ["5m", "15m", "30m", "1h"]

for simbolo in simbolos:
    for intervalo in intervalos:
        datos = obtener_datos(simbolo, periodo, intervalo)
        if datos is not None:
            datos = calcular_indicadores(datos)
            if datos is not None:
                datos
