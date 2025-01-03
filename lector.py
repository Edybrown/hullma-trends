import time
import json
import os
import pandas as pd
import numpy as np
import ta
import traceback
import re

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

COLUMN_MAPPING = {
    "Close": "close",
    "CLOSE": "close",
    "cLOSE": "close"
}

def load_csv(file_path):
    try:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, index_col='time', parse_dates=True)

            # Normalización de nombres de columna (con manejo de excepciones)
            try:
                def normalize_column_name(name):
                    name = name.lower()
                    name = re.sub(r"[^a-zA-Z0-9]+", "_", name)  # Sustituye caracteres no alfanuméricos por _
                    name = re.sub(r"__+", "_", name)  # Sustituye múltiples _ por uno solo
                    name = name.strip("_")  # Elimina _ al principio y al final
                    return name
                df.columns = [normalize_column_name(col) for col in df.columns]
            except AttributeError as e:
                print(f"Error al normalizar nombres de columna: {e}. Asegúrate de que las columnas sean strings")
                return None
            except Exception as e:
                print(f"Error desconocido al normalizar nombres de columna: {e}")
                return None

            df = df.rename(columns=COLUMN_MAPPING)

            if not df.empty:
                return df
            else:
                print(f"El archivo {file_path} está vacío.")
                return None
        else:
            print(f"El archivo {file_path} no existe.")
            return None
    except FileNotFoundError:
        print(f"Error: Archivo no encontrado en la ruta {file_path}")
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
            return {"value": None, "signal": "Datos insuficientes", "message": "Faltan las columnas 'RSI' o 'close' en el DataFrame."}

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
    """
    Analiza el VWAP.

    Esta función asume que la columna 'VWAP' YA ESTÁ CALCULADA y presente en el DataFrame 'df',
    junto con la columna 'close' (Precio de Cierre).

    Args:
        df (pd.DataFrame): DataFrame con las columnas 'VWAP' y 'close'.

    Returns:
        dict: Un diccionario con el valor del VWAP ('value'), la señal ('signal') y un mensaje descriptivo ('message').
              Devuelve un mensaje de error si faltan las columnas necesarias.
    """
    try:
        if not all(col in df.columns for col in ['vwap', 'close']):
            return {"value": None, "signal": "Datos insuficientes", "message": "Faltan las columnas 'vwap' o 'close' en el DataFrame."}

        last_vwap = df['vwap'].iloc[-1]
        last_close = df['close'].iloc[-1]

        signal = "Neutral"
        message = f"vwap en {last_vwap:.2f}. Precio actual en {last_close:.2f}. "

        if last_close > last_vwap:
            signal = "Alcista"
            message += "El precio actual está por encima del VWAP."
        elif last_close < last_vwap:
            signal = "Bajista"
            message += "El precio actual está por debajo del VWAP."
        else:
            message += "El precio actual está en el VWAP."

        # Análisis adicional basado en la distancia del precio al VWAP (en porcentaje)
        distancia_porcentual = abs((last_close - last_vwap) / last_vwap) * 100
        message += f" Distancia al VWAP: {distancia_porcentual:.2f}%. "

        if distancia_porcentual > 1:  # Ejemplo: Distancia mayor al 1% se considera significativa (Ajustable)
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





def analyze_indicators(df, timeframe):
    """Analiza todos los indicadores relevantes, incluyendo price action."""
    rsi_analysis = analyze_rsi(df)
    vwap_analysis = analyze_vwap(df)
    atr_analysis = analyze_atr(df)
    hullma_analysis = analyze_hullma(df)
    bollinger_analysis = analyze_bollinger_bands(df)
    macd_analysis = analyze_macd(df)
    price_action_analysis = analyze_price_action(df) # Llamada a analyze_price_action

    return {
        "RSI": rsi_analysis,
        "VWAP": vwap_analysis,
        "ATR": atr_analysis,
        "HULLMA": hullma_analysis,
        "Bollinger": bollinger_analysis,
        "MACD": macd_analysis,
        "PriceAction": price_action_analysis # Se añade el análisis de Price Action al diccionario
    }

# Función para generar un informe
def generate_report(timeframe, analysis):
    """Genera un informe basado en el análisis."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    return {
        "timeframe": timeframe,
        "timestamp": timestamp,
        "analysis": analysis
    }

def export_to_json(report, timeframe):
    """Exporta a JSON, guardando solo el último informe."""
    output_file = os.path.join(OUTPUT_DIR, f"report_{timeframe}.json")
    with open(output_file, "w") as f:
        json.dump(report, f, indent=4)
    print(f"Informe para {timeframe} exportado a {output_file}")

def espera_cierre_vela(timeframe, margen_segundos=5):
    """Espera hasta el cierre de la próxima vela, con un margen."""
    ahora = time.time()
    intervalo = TIME_INTERVALS[timeframe]
    tiempo_para_siguiente_vela = intervalo - (ahora % intervalo)
    tiempo_para_siguiente_vela = max(0, tiempo_para_siguiente_vela - margen_segundos)
    print(f"Esperando {tiempo_para_siguiente_vela:.0f} segundos para el cierre de la vela de {timeframe}...")
    time.sleep(tiempo_para_siguiente_vela)


def main_loop():
    analisis_inicial_completo = False

    # Procesamiento inicial
    for timeframe, file_path in CSV_FILES.items():
        df = load_csv(file_path)
        if df is not None and not df.empty:
            try:
                #Calculamos los indicadores ANTES del analisis
                df['macd'], df['macd_signal'], df['macd_hist'] = ta.macd(df['close'], fast=12, slow=26, signal_period=9)
                df['rsi'] = ta.rsi(df['close'], window=14)
                df['bollinger_bands'] = ta.BBANDS(df['close'], window=20)
                df['hullma'] = ta.hull_moving_average(df['close'])
                df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], volume=df.get('volume'))
                df['atr'] = ta.ATR(df['high'], df['low'], df['close'], window=14)

                indicators = analyze_indicators(df, timeframe)
                report = generate_report(timeframe, indicators)
                export_to_json(report, timeframe)
                LAST_RUN[timeframe] = df.index[-1]
            except Exception as e:
                print(f"Error durante el análisis inicial de {timeframe}: {e}")
                traceback.print_exc()
        elif df is not None and df.empty:
            print(f"DataFrame vacío para {timeframe}. Revisar archivo: {file_path}")

    analisis_inicial_completo = True

    while True:
        espera_cierre_vela("15m")
        df_15m = load_csv(CSV_FILES["15m"])

        if df_15m is not None and not df_15m.empty:
            if not analisis_inicial_completo:
                print("Esperando a que se complete el análisis inicial...")
                continue

            if df_15m.index[-1] != LAST_RUN["15m"]:
                print("Nueva vela detectada para 15m. Verificando otras temporalidades...")
                LAST_RUN["15m"] = df_15m.index[-1]
                timeframes_a_procesar = ["15m"]

                for timeframe in ["1h", "4h", "1d"]:
                    df = load_csv(CSV_FILES[timeframe])
                    if df is not None and not df.empty and df.index[-1] != LAST_RUN[timeframe]:
                        print(f"Nueva vela detectada para {timeframe}. Incluyendo en el procesamiento.")
                        timeframes_a_procesar.append(timeframe)
                        LAST_RUN[timeframe] = df.index[-1]

                for timeframe in timeframes_a_procesar:
                    df = load_csv(CSV_FILES[timeframe])
                    if df is not None and not df.empty:
                        try:
                            #Calculamos los indicadores ANTES del analisis
                            df['macd'], df['macd_signal'], df['macd_hist'] = ta.macd(df['close'], fast=12, slow=26, signal_period=9)
                            df['rsi'] = ta.rsi(df['close'], window=14)
                            df['bollinger_bands'] = ta.BBANDS(df['close'], window=20)
                            df['hullma'] = ta.hull_moving_average(df['close'])
                            df['vwap'] = ta.vwap(df['high'], df['low'], df['close'], volume=df.get('volume'))
                            df['atr'] = ta.ATR(df['high'], df['low'], df['close'], window=14)

                            indicators = analyze_indicators(df, timeframe)
                            report = generate_report(timeframe, indicators)
                            export_to_json(report, timeframe)
                        except Exception as e:
                            print(f"Error durante el análisis de {timeframe}: {e}")
                            traceback.print_exc()
                    elif df is not None and df.empty:
                        print(f"DataFrame vacío para {timeframe}. Revisar archivo: {file_path}")

            else:
                print("No hay nueva vela para 15m. Esperando la siguiente vela...")
        elif df_15m is None:
            print("Error al cargar el dataframe de 15m, revisa el archivo")
        else:
            print("El dataframe de 15m esta vacio")

if __name__ == "__main__":
    main_loop()
