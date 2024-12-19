import yfinance as yf
import pandas as pd
import talib
import os
import logging
import datetime

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def obtener_datos(simbolo, periodo, intervalo):
    nombre_archivo = f"data/{simbolo}_{periodo}_{intervalo}.csv" # Guarda los datos en una carpeta "data"
    os.makedirs("data", exist_ok=True) # Crea la carpeta si no existe

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
    df['Retorno'] = 0.0
    posicion = False
    precio_compra = 0
    for i in range(1, len(df)):
        if (df['RSI_7'][i] > df['RSI_14'][i] and df['RSI_7'][i-1] <= df['RSI_14'][i-1] and df['Close'][i] > df['HMA_9'][i]):
            if not posicion:
                df['Signal'][i] = 1  # Señal de compra
                posicion = True
                precio_compra = df['Close'][i]
                logging.info(f"{df.index[i]} - Compra {simbolo} en {intervalo} a {precio_compra}")

        elif posicion:
            if (df['Close'][i] < precio_compra * (1 - stop_loss_percent)):  # Stop loss
                df['Retorno'][i] = (df['Close'][i] - precio_compra) / precio_compra
                posicion = False
                logging.info(f"{df.index[i]} - Venta por Stop Loss {simbolo} en {intervalo} a {df['Close'][i]}, Pérdida: {df['Retorno'][i]:.2%}")
            elif (df['RSI_7'][i] < df['RSI_14'][i] and df['RSI_7'][i-1] >= df['RSI_14'][i-1]):
                df['Retorno'][i] = (df['Close'][i] - precio_compra) / precio_compra
                posicion = False
                logging.info(f"{df.index[i]} - Venta por señal {simbolo} en {intervalo} a {df['Close'][i]}, Ganancia/Pérdida: {df['Retorno'][i]:.2%}")
    return df

def analizar_resultados(df, simbolo, intervalo):
    ganancias = df[df['Retorno'] > 0]['Retorno'].sum()
    perdidas = df[df['Retorno'] < 0]['Retorno'].sum()
    total_operaciones = df[df['Retorno'] != 0].shape[0]
    operaciones_ganadoras = df[df['Retorno'] > 0].shape[0]
    operaciones_perdedoras = df[df['Retorno'] < 0].shape[0]
    if total_operaciones > 0 :
        ratio_ganancia_perdida = abs(ganancias) / abs(perdidas) if perdidas != 0 else float('inf')
        porcentaje_ganadoras = (operaciones_ganadoras / total_operaciones) * 100
    else:
        ratio_ganancia_perdida = 0
        porcentaje_ganadoras = 0
    logging.info(f"Resumen de {simbolo} en {intervalo}:")
    logging.info(f"Ganancias totales: {ganancias:.2%}")
    logging.info(f"Pérdidas totales: {perdidas:.2%}")
    logging.info(f"Total de operaciones: {total_operaciones}")
    logging.info(f"Operaciones ganadoras: {operaciones_ganadoras}")
    logging.info(f"Operaciones perdedoras: {operaciones_perdedoras}")
    logging.info(f"Ratio Ganancia/Pérdida: {ratio_ganancia_perdida:.2f}")
    logging.info(f"Porcentaje de operaciones ganadoras: {porcentaje_ganadoras:.2f}%")

simbolos = ["AAPL", "MSFT", "GOOG"]  # Lista de símbolos
periodo = "1y"  # Periodo de tiempo
intervalos = ["5m", "15m", "30m", "1h"]  # Intervalos de tiempo

for simbolo in simbolos:
    for intervalo in intervalos:
        datos = obtener_datos(simbolo, periodo, intervalo)
        if datos is not None:
            datos = calcular_indicadores(datos)
            if datos is not None:
                datos = aplicar_estrategia(datos)
                analizar_resultados(datos, simbolo, intervalo)
                # Guarda los resultados con el simbolo y el intervalo
                datos.to_csv(f"resultados/{simbolo}_{periodo}_{intervalo}_resultados.csv")
