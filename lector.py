import time
import json
import os
import pandas as pd
import numpy as np
import ta
import traceback
import re
import datetime

# --- CONFIGURACIÓN DE ARCHIVOS Y CARPETAS ---
DATA_DIR = "datos_BTC"
OUTPUT_DIR = "Informes"
PIVOTES_FILE = "pivotes_historicos.json"

# Verificar la existencia de directorios
for path in [DATA_DIR, OUTPUT_DIR]:
    if not os.path.exists(path):
        os.makedirs(path)
    elif not os.path.isdir(path):
        print(f"Error: '{path}' existe pero no es un directorio.")
        exit()

LAST_PROCESSED = {  # Diccionario para almacenar la última hora procesada
    "15m": None,
    "1h": None,
    "4h": None,
    "1d": None,
}

CURRENT_OPEN = {  # Nuevo diccionario para la hora de apertura actual
    "15m": None,
    "1h": None,
    "4h": None,
    "1d": None,
}

CSV_FILES = {
    "15m": os.path.join(DATA_DIR, "XBTUSDT_15m.csv"),
    "1h": os.path.join(DATA_DIR, "XBTUSDT_1h.csv"),
    "4h": os.path.join(DATA_DIR, "XBTUSDT_4h.csv"),
    "1d": os.path.join(DATA_DIR, "XBTUSDT_1d.csv"),
}

TIME_INTERVALS = {
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400
}

LAST_RUN = {key: None for key in CSV_FILES.keys()}

# Unificar mapeos de nombres de columnas
COLUMN_MAPPING = {
    "close": "close",
    "volume": "volume",
    "time": "time",
    "open": "open",
    "high": "high",
    "low": "low",
    "cierre": "close",
    "volumen": "volume",
    "Close": "close",
    "CLOSE": "close",
    "cLOSE": "close" ,
    "RSI": "rsi" ,
    "HULLMA":"hullma" ,
    "ATR": "atr" ,

}

# --- FUNCIONES ---
def normalize_column_name(name):
    """
    Normaliza los nombres de las columnas: convierte a minúsculas,
    reemplaza caracteres no alfanuméricos por guiones bajos y elimina guiones bajos redundantes.
    """
    name = name.lower()  # Convertir a minúsculas
    name = re.sub(r"[^a-z0-9]+", "_", name)  # Reemplazar caracteres no alfanuméricos
    name = re.sub(r"__+", "_", name)  # Reemplazar múltiples guiones bajos por uno solo
    name = name.strip("_")  # Eliminar guiones bajos al inicio o final
    return name

def load_csv(file_path):
    try:
        # Verificar si el archivo existe
        if not os.path.exists(file_path):
            print(f"El archivo {file_path} no existe.")
            return None
        
        # Verificar si el archivo está vacío
        if os.path.getsize(file_path) == 0:
            print(f"El archivo {file_path} está vacío.")
            return None
        
        # Intentar cargar el archivo CSV
        df = pd.read_csv(file_path, index_col='time', parse_dates=True)

        # Convertir todos los nombres de columnas a minúsculas
        df.columns = df.columns.str.lower()

        # Normalización de nombres de columnas
        def normalize_column_name(name):
            name = re.sub(r"[^a-zA-Z0-9]+", "_", name)
            name = re.sub(r"__+", "_", name)
            name = name.strip("_")
            return name

        df.columns = [normalize_column_name(col) for col in df.columns]

        # Mapeo de columnas
        df = df.rename(columns=COLUMN_MAPPING)

        # Verificar si el DataFrame está vacío después de la carga
        if df.empty:
            print(f"El archivo {file_path} no contiene datos después de la carga.")
            return None
        if df is not None:
        try:
            df.index = pd.to_datetime(df.index)
        except ValueError as e:
            print(f"Error al convertir el índice a datetime: {e}")
            return None
        
        return df

    except FileNotFoundError:
        print(f"Error: Archivo no encontrado en la ruta {file_path}")
        return None
    except pd.errors.EmptyDataError:
        print(f"Error: No se encontraron columnas para analizar en el archivo {file_path}.")
        return None
    except pd.errors.ParserError:
        print(f"Error: No se pudo analizar el archivo CSV en {file_path}. Asegúrate de que el formato sea correcto.")
        return None
    except Exception as e:
        print(f"Error desconocido al cargar el archivo {file_path}: {e}")
        return None

def analyze_rsi(df):
    """Analiza el RSI PRECALCULADO en el DataFrame, incluyendo divergencias ocultas."""
    try:
        if 'rsi' not in df.columns or 'close' not in df.columns:
            return {"value": None, "signal": "Datos insuficientes", "message": "Faltan las columnas 'rsi' o 'close' en el DataFrame."}

        last_rsi = df['rsi'].iloc[-1]
        signal = "Neutral"
        message = f"RSI en {last_rsi:.2f}. "

        # Rangos de fuerza (sin cambios)
        if last_rsi > 70:
            signal = "Sobrecompra"
            message += "Entrando en zona de sobrecompra."
        elif last_rsi < 30:
            signal = "Sobreventa"
            message += "Entrando en zona de sobreventa."
        elif 60 < last_rsi <= 70:
            signal = "Fuerte Alcista"
            message += "En zona alcista fuerte."
        elif 30 <= last_rsi < 40:
            signal = "Fuerte Bajista"
            message += "En zona bajista fuerte."
        else:
            message += "En zona neutral."

        # Detección de divergencias (incluyendo ocultas)
        if len(df) >= 3:
            # Divergencias regulares (sin cambios)
            if df['close'].iloc[-1] > df['close'].iloc[-2] and df['rsi'].iloc[-1] < df['rsi'].iloc[-2]:
                message += " Posible divergencia bajista."
                if signal == "Sobrecompra":
                    signal = "Divergencia Bajista en Sobrecompra"
                else:
                    signal = "Divergencia Bajista"
            elif df['close'].iloc[-1] < df['close'].iloc[-2] and df['rsi'].iloc[-1] > df['rsi'].iloc[-2]:
                message += " Posible divergencia alcista."
                if signal == "Sobreventa":
                    signal = "Divergencia Alcista en Sobreventa"
                else:
                    signal = "Divergencia Alcista"

            # Divergencias ocultas (AÑADIDO)
            # Divergencia oculta alcista (precio hace un mínimo más alto, RSI hace un mínimo más bajo)
            if df['close'].iloc[-1] > df['close'].iloc[-2] and df['rsi'].iloc[-1] < df['rsi'].iloc[-2] and df['close'].iloc[-2] > df['close'].iloc[-3] and df['rsi'].iloc[-2] > df['rsi'].iloc[-3]:
                message += " Posible divergencia oculta alcista."
                signal = "Divergencia Oculta Alcista"

            # Divergencia oculta bajista (precio hace un máximo más bajo, RSI hace un máximo más alto)
            elif df['close'].iloc[-1] < df['close'].iloc[-2] and df['rsi'].iloc[-1] > df['rsi'].iloc[-2] and df['close'].iloc[-2] < df['close'].iloc[-3] and df['rsi'].iloc[-2] < df['rsi'].iloc[-3]:
                message += " Posible divergencia oculta bajista."
                signal = "Divergencia Oculta Bajista"
        return {"value": last_rsi, "signal": signal, "message": message}

    except IndexError:
        return {"value": None, "signal": "Error", "message": "Error al analizar el RSI. DataFrame vacío o datos insuficientes."}

def analyze_vwap(df):
    try:
        if not all(col in df.columns for col in ['vwap', 'close']):
            return {"value": None, "signal": "Datos insuficientes", "message": "Faltan las columnas 'vwap' o 'close' en el DataFrame."}

        last_vwap = round(df['vwap'].iloc[-1], 2)
        last_close = round(df['close'].iloc[-1], 2)

        signal = "Neutral"
        message = f"VWAP en {last_vwap:.2f}. Precio actual en {last_close:.2f}. "

        if last_close > last_vwap:
            signal = "Alcista"
            message += "El precio actual está por encima del VWAP."
        elif last_close < last_vwap:
            signal = "Bajista"
            message += "El precio actual está por debajo del VWAP."
        else:
            message += "El precio actual está en el VWAP."

        distancia_porcentual = abs((last_close - last_vwap) / last_vwap) * 100
        distancia_porcentual = round(distancia_porcentual, 2)
        message += f" Distancia al VWAP: {distancia_porcentual:.2f}%. "

        if distancia_porcentual > 1:
            if last_close > last_vwap:
                message += "El precio se ha alejado significativamente del VWAP al alza."
            else:
                message += "El precio se ha alejado significativamente del VWAP a la baja."

        return {"value": last_vwap, "signal": signal, "message": message}

    except IndexError:
        return {"value": None, "signal": "Error", "message": "Error al analizar el VWAP. DataFrame vacío o datos insuficientes."}

# Función para analizar ATR

def analyze_atr(df, lookback=5):
    """
    Analiza el ATR.

    Esta función asume que la columna 'ATR' YA ESTÁ CALCULADA y presente en el DataFrame 'df'.

    Args:
        df (pd.DataFrame): DataFrame con la columna 'ATR'.
        lookback (int, optional): Número de periodos para analizar el comportamiento reciente del ATR. Defaults to 5.

    Returns:
        dict: Un diccionario con el valor del ATR ('value'), la señal ('signal') y un mensaje descriptivo ('message').
              Devuelve un mensaje de error si faltan las columnas necesarias o si no hay suficientes datos.
    """
    try:
        if 'atr' not in df.columns:
            return {"value": None, "signal": "Datos insuficientes", "message": "Falta la columna 'ATR' en el DataFrame."}

        if len(df) < lookback + 1:
            return {"value": None, "signal": "Datos insuficientes", "message": f"No hay suficientes datos para analizar el comportamiento del ATR en los últimos {lookback} periodos."}

        last_atr = df['atr'].iloc[-1]
        message = f"ATR en {last_atr:.2f}. "

        atr_lookback = df['atr'].iloc[-lookback:]
        atr_change = np.diff(atr_lookback)

        # Calcula el cambio porcentual para mejor entendimiento
        atr_percent_change = (atr_change / atr_lookback[:-1]) * 100

        if all(change > 0 for change in atr_change):
            message += f"La volatilidad ha estado aumentando en los últimos {lookback} periodos. "
            avg_percent_change = np.mean(atr_percent_change)
            message += f"Aumentando en promedio un {avg_percent_change:.2f}% por periodo."
        elif all(change < 0 for change in atr_change):
            message += f"La volatilidad ha estado disminuyendo en los últimos {lookback} periodos. "
            avg_percent_change = np.mean(atr_percent_change)
            message += f"Disminuyendo en promedio un {abs(avg_percent_change):.2f}% por periodo."
        else:
            message += f"La volatilidad ha mostrado fluctuaciones en los últimos {lookback} periodos."
            avg_percent_change = np.mean(np.abs(atr_percent_change))
            message += f"Con una fluctuación promedio de {avg_percent_change:.2f}% por periodo."

        return {"value": last_atr, "signal": "Valor analizado", "message": message} #Se cambia "calculado" por "analizado"

    except IndexError:
        return {"value": None, "signal": "Error", "message": "Error al analizar el ATR. DataFrame vacío o datos insuficientes."}

def analyze_hullma(df):
    """
    Analiza la HULLMA.

    Esta función asume que la columna 'HULLMA' YA ESTÁ CALCULADA y presente en el DataFrame 'df',
    junto con la columna 'close' (Precio de Cierre).

    Args:
        df (pd.DataFrame): DataFrame con las columnas 'HULLMA' y 'close'.

    Returns:
        dict: Un diccionario con el valor de la HULLMA ('value'), la señal ('signal') y un mensaje descriptivo ('message').
              Devuelve un mensaje de error si faltan las columnas necesarias o si no hay suficientes datos.
    """
    try:
        if not all(col in df.columns for col in ['hullma', 'close']):
            return {"value": None, "signal": "Datos insuficientes", "message": "Faltan las columnas 'HULLMA' o 'close' en el DataFrame."}

        if len(df) < 3:  # Necesitamos al menos tres datos para comparar aceleración
            return {"value": None, "signal": "Datos insuficientes", "message": "No hay suficientes datos para analizar la HULLMA y detectar impulsos."}

        last_hullma = df['hullma'].iloc[-1]
        previous_hullma = df['hullma'].iloc[-2]
        previous_previous_hullma = df['hullma'].iloc[-3]
        last_close = df['close'].iloc[-1]
        previous_close = df['close'].iloc[-2]

        signal = "Neutral"
        message = f"HULLMA en {last_hullma:.2f}. Precio actual en {last_close:.2f}. "

        # Detección de cruces e impulsos
        if previous_close < previous_hullma and last_close > last_hullma:
            signal = "Compra - Impulso Alcista"
            if last_hullma > previous_hullma and previous_hullma > previous_previous_hullma:
                message += "Cruce alcista con HULLMA en aceleración alcista. Fuerte señal de compra."
            else:
                message += "Cruce alcista. Señal de compra."
        elif previous_close > previous_hullma and last_close < last_hullma:
            signal = "Venta - Impulso Bajista"
            if last_hullma < previous_hullma and previous_hullma < previous_previous_hullma:
                message += "Cruce bajista con HULLMA en aceleración bajista. Fuerte señal de venta."
            else:
                message += "Cruce bajista. Señal de venta."
        elif last_close > last_hullma:
            signal = "Alcista"
            message += "El precio está por encima de la HULLMA."
        elif last_close < last_hullma:
            signal = "Bajista"
            message += "El precio está por debajo de la HULLMA."

        # Análisis de la aceleración de la HULLMA
        if last_hullma > previous_hullma and previous_hullma > previous_previous_hullma:
            message += " La HULLMA muestra aceleración alcista."
        elif last_hullma < previous_hullma and previous_hullma < previous_previous_hullma:
            message += " La HULLMA muestra aceleración bajista."

        return {"value": last_hullma, "signal": signal, "message": message}

    except IndexError:
        return {"value": None, "signal": "Error", "message": "Error al analizar la HULLMA. DataFrame vacío o datos insuficientes."}



def analyze_bollinger_bands(df):
    """Analiza Bandas de Bollinger precalculadas en el DataFrame."""
    try:
        df.columns = df.columns.str.lower() #Convertimos a minusculas
        if not all(col in df.columns for col in ['bb_upper', 'bb_middle', 'bb_lower', 'close']):
            return {"signal": "Datos insuficientes", "message": "Faltan columnas de Bandas de Bollinger (bb_upper, bb_middle, bb_lower, close)."}

        last_bb_m = df['bb_middle'].iloc[-1]
        last_bb_h = df['bb_upper'].iloc[-1]
        last_bb_l = df['bb_lower'].iloc[-1]
        last_close = df['close'].iloc[-1]

        signal = "Neutral"
        message = f"BB: Media {last_bb_m:.2f}, Sup {last_bb_h:.2f}, Inf {last_bb_l:.2f}, Precio {last_close:.2f}. "

        if last_close > last_bb_h:
            signal = "Sobrecompra"
            message += "Precio en o por encima de la Banda Superior."
        elif last_close < last_bb_l:
            signal = "Sobreventa"
            message += "Precio en o por debajo de la Banda Inferior."
        elif last_close > last_bb_m:
            signal = "Alcista"
            message += "Precio por encima de la Banda Media."
        elif last_close < last_bb_m:
            signal = "Bajista"
            message += "Precio por debajo de la Banda Media."

        if len(df) >= 2:
            current_band_width = last_bb_h - last_bb_l
            previous_band_width = df['bb_upper'].iloc[-2] - df['bb_lower'].iloc[-2]
            band_width_change = (current_band_width - previous_band_width) / previous_band_width * 100

            if current_band_width < previous_band_width and band_width_change < -5:
                message += " Posible Squeeze detectado."
            elif current_band_width > previous_band_width and band_width_change > 5:
                message += " Volatilidad en aumento."

        if last_close < last_bb_l:
            message += " Probando soporte."
        elif last_close > last_bb_h:
            message += " Probando resistencia."

        if last_close > last_bb_h and df['close'].iloc[-2] <= df['bb_upper'].iloc[-2]:
            message += " Ruptura confirmada al alza."
        elif last_close < last_bb_l and df['close'].iloc[-2] >= df['bb_lower'].iloc[-2]:
            message += " Ruptura confirmada a la baja."

        if last_close > last_bb_h and (df['bb_upper'].iloc[-2] - df['bb_upper'].iloc[-3]) < 0:
            message += " Divergencia: precio sube, banda superior no se expande."
        elif last_close < last_bb_l and (df['bb_lower'].iloc[-2] - df['bb_lower'].iloc[-3]) > 0:
            message += " Divergencia: precio baja, banda inferior no se contrae."

        return {"signal": signal, "message": message}

    except IndexError:
        return {"signal": "Error", "message": "Error al analizar las Bandas de Bollinger."}
    except Exception as e:
        print(f"Error en analyze_bollinger_bands: {e}")
        return {"signal": "Error", "message": f"Error al analizar las Bandas de Bollinger: {e}"}

def analyze_macd(df):
    print(f"Columnas disponibles en MACD: {df.columns.tolist()}")
    required_columns = ['macd', 'macd_signal', 'macd_hist', 'close']
    if not all(col in df.columns for col in required_columns):
        missing_columns = [col for col in required_columns if col not in df.columns]
        return {"signal": "Datos insuficientes", "message": f"Faltan las columnas: {missing_columns}. Columnas presentes: {df.columns.tolist()}"}
    try:
        if df.empty:
            return {"signal": "Datos insuficientes", "message": "DataFrame vacío."}
        
        last_macd = df['macd'].iloc[-1]
        last_signal = df['macd_signal'].iloc[-1]
        last_histogram = df['macd_hist'].iloc[-1]
        last_close = df['close'].iloc[-1]
        
        if pd.isna(last_macd) or pd.isna(last_signal) or pd.isna(last_histogram) or pd.isna(last_close):
            return {"signal": "Datos insuficientes", "message": "Valores MACD, Señal, Histograma o Close faltantes (NaN)."}

        if len(df) >= 2:
            prev_macd = df['macd'].iloc[-2]
            prev_signal = df['macd_signal'].iloc[-2]
            if last_macd > last_signal and prev_macd <= prev_signal:
                signal = "Cruce Alcista"
                message = f"Cruce alcista del MACD. MACD ({last_macd:.2f}) cruza por encima de la señal ({last_signal:.2f})."
            elif last_macd < last_signal and prev_macd >= prev_signal:
                signal = "Cruce Bajista"
                message = f"Cruce bajista del MACD. MACD ({last_macd:.2f}) cruza por debajo de la señal ({last_signal:.2f})."
            elif last_histogram > 0:
                signal = "Tendencia Alcista"
                message = f"Histograma MACD positivo ({last_histogram:.2f}). Tendencia alcista."
            elif last_histogram < 0:
                signal = "Tendencia Bajista"
                message = f"Histograma MACD negativo ({last_histogram:.2f}). Tendencia bajista."
            else:
                 signal = "Sin señal clara"
                 message = f"Sin señal clara del MACD. Histograma en cero ({last_histogram:.2f})"
        else:
            signal = "Datos insuficientes"
            message = "Se necesitan al menos dos periodos para analizar cruces del MACD."
        return {"signal": signal, "message": message}

    except IndexError:
        return {"signal": "Error", "message": "Error de índice al analizar MACD. Datos insuficientes."}
    except Exception as e:
        return {"signal": "Error", "message": f"Error inesperado al analizar MACD: {e}"}


def analyze_chart_patterns(maximos, minimos):
    """Subfunción interna para analizar patrones chartistas."""
    patrones = []

    # Revisar el número de elementos disponibles
    for n in [5, 3, 2]:  # Probar con 5, 3 y 2 puntos
        if len(maximos) >= n and len(minimos) >= n:
            max_vals = [m["valor"] for m in maximos[-n:]]  # Usar solo los últimos n puntos
            min_vals = [m["valor"] for m in minimos[-n:]]  # Usar solo los últimos n puntos

            # Análisis de tendencias y patrones
            if all(x < y for x, y in zip(max_vals[:-1], max_vals[1:])) and all(x < y for x, y in zip(min_vals[:-1], min_vals[1:])):
                patrones.append(f"Tendencia alcista detectada con {n} puntos.")
                break
            elif all(x > y for x, y in zip(max_vals[:-1], max_vals[1:])) and all(x > y for x, y in zip(min_vals[:-1], min_vals[1:])):
                patrones.append(f"Tendencia bajista detectada con {n} puntos.")
                break
            elif all(x > y for x, y in zip(max_vals[:-1], max_vals[1:])) and all(x < y for x, y in zip(min_vals[:-1], min_vals[1:])):
                patrones.append(f"Triángulo simétrico detectado con {n} puntos.")
                break
            elif all(x == max_vals[0] for x in max_vals) and all(x < y for x, y in zip(min_vals[:-1], min_vals[1:])):
                patrones.append(f"Triángulo ascendente detectado con {n} puntos.")
                break
            elif all(x < y for x, y in zip(max_vals[:-1], max_vals[1:])) and all(x == min_vals[0] for x in min_vals):
                patrones.append(f"Triángulo descendente detectado con {n} puntos.")
                break
            elif max(abs(max_vals[i] - max_vals[i + 1]) for i in range(len(max_vals) - 1)) < 0.01 and \
                    max(abs(min_vals[i] - min_vals[i + 1]) for i in range(len(min_vals) - 1)) < 0.01:
                patrones.append(f"Consolidación lateral detectada con {n} puntos.")
                break
            elif abs(max_vals[-1] - max_vals[-2]) < 0.01 and min_vals[-1] < min_vals[-2]:
                patrones.append(f"Doble techo detectado con {n} puntos.")
                break
            elif abs(min_vals[-1] - min_vals[-2]) < 0.01 and max_vals[-1] > max_vals[-2]:
                patrones.append(f"Doble suelo detectado con {n} puntos.")
                break

    return patrones

def analyze_price_action(df, velas_maximas=200, min_velas=5, min_movimiento=0.011):
    """
    Analiza la acción del precio, incluyendo cruces, máximos/mínimos relativos y patrones chartistas.
    Prioriza la separación mínima de 5 velas, pero permite señales con menos separación
    si el movimiento porcentual entre ellas es mayor al 1.1%.
    """
    if df.empty or len(df) < 7:
        return {"maximos": [], "minimos": [], "patrones": [], "mensaje": "Datos insuficientes."}

    close = df['close']
    high = df['high']
    low = df['low']
    hullma = df['hullma'] if 'hullma' in df.columns else None

    maximos = []
    minimos = []
    mensaje = ""
    ultima_senal = None  # Para rastrear la última señal procesada

    if hullma is not None and len(df) >= 7:
        for i in range(7, len(df)):
            # Validar cruce al alza
            if close.iloc[i - 1] < hullma.iloc[i - 1] and close.iloc[i] > hullma.iloc[i]:
                min_valor = min(low.iloc[i - 5:i])
                min_indice = low.iloc[i - 5:i].idxmin()

                if ultima_senal is None or (i - ultima_senal['indice']) >= min_velas:
                    # Si cumple con la separación de 5 velas, aceptar directamente
                    minimos.append({"indice": min_indice.isoformat(), "valor": min_valor})
                    ultima_senal = {"indice": i, "valor": min_valor}
                else:
                    # Evaluar si el porcentaje de movimiento es suficiente
                    if abs(min_valor - ultima_senal['valor']) / ultima_senal['valor'] >= min_movimiento:
                        minimos.append({"indice": min_indice.isoformat(), "valor": min_valor})
                        ultima_senal = {"indice": i, "valor": min_valor}

            # Validar cruce a la baja
            elif close.iloc[i - 1] > hullma.iloc[i - 1] and close.iloc[i] < hullma.iloc[i]:
                max_valor = max(high.iloc[i - 5:i])
                max_indice = high.iloc[i - 5:i].idxmax()

                if ultima_senal is None or (i - ultima_senal['indice']) >= min_velas:
                    # Si cumple con la separación de 5 velas, aceptar directamente
                    maximos.append({"indice": max_indice.isoformat(), "valor": max_valor})
                    ultima_senal = {"indice": i, "valor": max_valor}
                else:
                    # Evaluar si el porcentaje de movimiento es suficiente
                    if abs(max_valor - ultima_senal['valor']) / ultima_senal['valor'] >= min_movimiento:
                        maximos.append({"indice": max_indice.isoformat(), "valor": max_valor})
                        ultima_senal = {"indice": i, "valor": max_valor}

    chart_patterns = analyze_chart_patterns(maximos[-5:], minimos[-5:])

    return {
        "maximos": maximos[-5:],
        "minimos": minimos[-5:],
        "patrones": chart_patterns,
        "mensaje": mensaje
    }

def analyze_indicators(df, timeframe):
    """Analiza todos los indicadores relevantes."""
    rsi_analysis = analyze_rsi(df)
    vwap_analysis = analyze_vwap(df)
    atr_analysis = analyze_atr(df)
    hullma_analysis = analyze_hullma(df)
    bollinger_analysis = analyze_bollinger_bands(df)
    macd_analysis = analyze_macd(df)
    price_action_analysis = analyze_price_action(df.tail(100))
    return {
        "RSI": rsi_analysis,
        "VWAP": vwap_analysis,
        "ATR": atr_analysis,
        "HULLMA": hullma_analysis,
        "Bollinger": bollinger_analysis,
        "MACD": macd_analysis,
        "Price Action": price_action_analysis,  # Resultado de la nueva función
    }

# Función para generar un informe
def generate_report(timeframe, indicators, price_action_analysis):
    # Código de generación de reporte con indicadores y análisis de acción del precio
    report = {
        "timeframe": timeframe,
        "indicators": indicators,
        "price_action_analysis": price_action_analysis,
        # Agrega otros campos según sea necesario
    }
    return report
    
def datetime_to_iso(o):
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

def export_to_json(report, timeframe):
    """Exporta a JSON, manejando objetos Timestamp."""
    output_file = os.path.join(OUTPUT_DIR, f"report_{timeframe}.json")
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False, default=datetime_to_iso)
        print(f"Informe para {timeframe} exportado a {output_file}")
    except Exception as e:
        print(f"Error al exportar a JSON: {e}")
        traceback.print_exc()
        

def obtener_ultima_vela_valida(file_path, timeframe):
    try:
        df = pd.read_csv(file_path, index_col="time", parse_dates=True)
        df.index = df.index.tz_localize('UTC')

        if timeframe == "1d":
            df.index = df.index.normalize()

        return df
    except FileNotFoundError:
        print(f"Archivo no encontrado: {file_path}")
        return None
    except Exception as e:
        print(f"Error al leer el archivo de {timeframe}: {e}")
        traceback.print_exc()
        return None

def main_loop():
    timeframes_ordenadas = ["15m", "1h", "4h", "1d"]

    while True:
        ahora = pd.Timestamp.now(tz='UTC')

        # 1. Obtener la hora de apertura de la vela actual para cada temporalidad
        for timeframe in timeframes_ordenadas:
            if timeframe == "15m":
                CURRENT_OPEN[timeframe] = ahora.floor('15min')
            elif timeframe == "1h":
                CURRENT_OPEN[timeframe] = ahora.floor('1h')
            elif timeframe == "4h":
                CURRENT_OPEN[timeframe] = ahora.floor('4h')
            elif timeframe == "1d":
                CURRENT_OPEN[timeframe] = ahora.floor('1D')

        # 2. Calcular el tiempo de espera para el cierre de la vela de 15m (ESTO DEFINE EL INICIO DEL SIGUIENTE CICLO)
        cierre_15m = CURRENT_OPEN["15m"] + pd.Timedelta(minutes=15)
        tiempo_espera_15m = (cierre_15m - ahora).total_seconds()
        tiempo_espera_15m = max(0, tiempo_espera_15m)

        print(f"Esperando {tiempo_espera_15m:.0f} segundos para el cierre de la siguiente vela de 15m")
        time.sleep(tiempo_espera_15m)

        ahora = pd.Timestamp.now(tz='UTC') #Actualizar 'ahora' despues de la espera

        # 3. Verificar y procesar cada temporalidad (LÓGICA CORREGIDA PARA 15M)
        for timeframe in timeframes_ordenadas:
            file_path = CSV_FILES[timeframe]
            print(f"Verificando {timeframe}...")
            df = obtener_ultima_vela_valida(file_path, timeframe)

            if df is not None and not df.empty:
                ultima_fecha_csv = df.index[-1]

                current_open_utc = CURRENT_OPEN[timeframe].tz_convert('UTC')
                ultima_fecha_csv_utc = ultima_fecha_csv.tz_convert('UTC')

                if timeframe == "1d":
                    current_open_utc = current_open_utc.normalize()
                    ultima_fecha_csv_utc = ultima_fecha_csv_utc.normalize()

                if ultima_fecha_csv_utc == current_open_utc:
                    if LAST_PROCESSED[timeframe] != current_open_utc:
                        try:
                            indicators = analyze_indicators(df, timeframe)
                            price_action_analysis = analyze_price_action(df.tail(100))
                            report = generate_report(timeframe, indicators, price_action_analysis)
                            export_to_json(report, timeframe)
                            LAST_PROCESSED[timeframe] = current_open_utc
                            print(f"Procesada vela de {timeframe} con apertura {current_open_utc}")
                        except Exception as e:
                            print(f"Error durante el análisis de {timeframe}: {e}")
                            traceback.print_exc()
                    else:
                        print(f"Vela de {timeframe} con apertura {current_open_utc} ya procesada. Saltando...")
                elif ultima_fecha_csv_utc < current_open_utc:
                    if timeframe == "15m": #Espera adicional solo para 15m
                        print(f"Esperando actualización de datos para {timeframe}...")
                        tiempo_espera_temporalidad = 0
                        while tiempo_espera_temporalidad < 90:  # Espera hasta 90 segundos para 15m
                            time.sleep(10)
                            tiempo_espera_temporalidad += 10
                            print(f"Revisando actualizacion para {timeframe}, Tiempo transcurrido: {tiempo_espera_temporalidad} segundos")
                            df_actualizado = obtener_ultima_vela_valida(file_path, timeframe)
                            if df_actualizado is not None and not df_actualizado.empty:
                                ultima_fecha_csv_actualizado = df_actualizado.index[-1]
                                ultima_fecha_csv_actualizado_utc = ultima_fecha_csv_actualizado.tz_convert('UTC')
                                if ultima_fecha_csv_actualizado_utc == current_open_utc:
                                    try:
                                        indicators = analyze_indicators(df_actualizado, timeframe)
                                        price_action_analysis = analyze_price_action(df_actualizado.tail(100))
                                        report = generate_report(timeframe, indicators, price_action_analysis)
                                        export_to_json(report, timeframe)
                                        LAST_PROCESSED[timeframe] = current_open_utc
                                        print(f"Datos actualizados. Procesada vela de {timeframe} con apertura {current_open_utc}")
                                        break
                                    except Exception as e:
                                        print(f"Error durante el análisis de {timeframe}: {e}")
                                        traceback.print_exc()
                            else:
                                print(f"No se pudo obtener la vela actualizada para {timeframe}. Revisar el archivo o la conexión.")
                                break
                    else:
                        print(f"La temporalidad {timeframe} no está actualizada. Se verificará en el próximo ciclo.")
            elif df is None:
                print(f"No se pudo obtener la vela para {timeframe}. Revisar el archivo o la conexión.")

if __name__ == "__main__":
    main_loop()
