import time
import json
import os
import pandas as pd
import numpy as np
import ta
import traceback  # Importar traceback una sola vez

# --- CONFIGURACIÓN DE ARCHIVOS Y CARPETAS ---
DATA_DIR = "datos_BTC"
OUTPUT_DIR = "Informes"  # Define el directorio de salida para informes
PIVOTES_FILE = "pivotes_historicos.json" #Archivo para guardar pivotes

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

LAST_RUN = {key: None for key in CSV_FILES.keys()} #Inicializar a None

# --- FUNCIÓN PARA CARGAR DATOS ---
def load_csv(file_path):
    try:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, index_col=0, parse_dates=True) #Parsea las fechas
            return df
        else:
            print(f"Archivo no encontrado: {file_path}")
            return None
    except pd.errors.ParserError as e: #Manejo de errores al parsear el csv
        print(f"Error al leer el archivo CSV {file_path}: {e}")
        return None




def analyze_rsi(df):
    """Analiza el RSI PRECALCULADO en el DataFrame, incluyendo divergencias ocultas."""
    try:
        if 'RSI' not in df.columns or 'close' not in df.columns:
            return {"value": None, "signal": "Datos insuficientes", "message": "Faltan las columnas 'RSI' o 'close' en el DataFrame."}

        last_rsi = df['RSI'].iloc[-1]
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
            if df['close'].iloc[-1] > df['close'].iloc[-2] and df['RSI'].iloc[-1] < df['RSI'].iloc[-2]:
                message += " Posible divergencia bajista."
                if signal == "Sobrecompra":
                    signal = "Divergencia Bajista en Sobrecompra"
                else:
                    signal = "Divergencia Bajista"
            elif df['close'].iloc[-1] < df['close'].iloc[-2] and df['RSI'].iloc[-1] > df['RSI'].iloc[-2]:
                message += " Posible divergencia alcista."
                if signal == "Sobreventa":
                    signal = "Divergencia Alcista en Sobreventa"
                else:
                    signal = "Divergencia Alcista"

            # Divergencias ocultas (AÑADIDO)
            # Divergencia oculta alcista (precio hace un mínimo más alto, RSI hace un mínimo más bajo)
            if df['close'].iloc[-1] > df['close'].iloc[-2] and df['RSI'].iloc[-1] < df['RSI'].iloc[-2] and df['close'].iloc[-2] > df['close'].iloc[-3] and df['RSI'].iloc[-2] > df['RSI'].iloc[-3]:
                message += " Posible divergencia oculta alcista."
                signal = "Divergencia Oculta Alcista"

            # Divergencia oculta bajista (precio hace un máximo más bajo, RSI hace un máximo más alto)
            elif df['close'].iloc[-1] < df['close'].iloc[-2] and df['RSI'].iloc[-1] > df['RSI'].iloc[-2] and df['close'].iloc[-2] < df['close'].iloc[-3] and df['RSI'].iloc[-2] < df['RSI'].iloc[-3]:
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
        if not all(col in df.columns for col in ['VWAP', 'close']):
            return {"value": None, "signal": "Datos insuficientes", "message": "Faltan las columnas 'VWAP' o 'close' en el DataFrame."}

        last_vwap = df['VWAP'].iloc[-1]
        last_close = df['close'].iloc[-1]

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
        if 'ATR' not in df.columns:
            return {"value": None, "signal": "Datos insuficientes", "message": "Falta la columna 'ATR' en el DataFrame."}

        if len(df) < lookback + 1:
            return {"value": None, "signal": "Datos insuficientes", "message": f"No hay suficientes datos para analizar el comportamiento del ATR en los últimos {lookback} periodos."}

        last_atr = df['ATR'].iloc[-1]
        message = f"ATR en {last_atr:.2f}. "

        atr_lookback = df['ATR'].iloc[-lookback:]
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
        if not all(col in df.columns for col in ['HULLMA', 'close']):
            return {"value": None, "signal": "Datos insuficientes", "message": "Faltan las columnas 'HULLMA' o 'close' en el DataFrame."}

        if len(df) < 3:  # Necesitamos al menos tres datos para comparar aceleración
            return {"value": None, "signal": "Datos insuficientes", "message": "No hay suficientes datos para analizar la HULLMA y detectar impulsos."}

        last_hullma = df['HULLMA'].iloc[-1]
        previous_hullma = df['HULLMA'].iloc[-2]
        previous_previous_hullma = df['HULLMA'].iloc[-3]
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
    """Analiza el indicador MACD precalculado en el DataFrame."""
    try:
        if df is None or df.empty:
            return {"signal": "Datos insuficientes", "message": "DataFrame vacío o None."}
        df = df.rename(columns={'Close': 'close', 'CLOSE':'close', 'cLOSE':'close'}) #Nos aseguramos que close este en minuscula
        # Verificar que las columnas necesarias estén en el DataFrame
        if not all(col in df.columns for col in ['MACD', 'MACD_Signal', 'MACD_Hist', 'close']):
            return {"signal": "Datos insuficientes", "message": "Faltan columnas de MACD (MACD, MACD_Signal, MACD_Hist, close)."}

        # Últimos valores de las columnas necesarias
        last_macd = df['MACD'].iloc[-1]
        last_signal = df['MACD_Signal'].iloc[-1]
        last_histogram = df['MACD_Hist'].iloc[-1]
        last_close = df['close'].iloc[-1]
        if len(df) >= 2:
            prev_close = df['close'].iloc[-2]

        signal = "Neutral"
        message = f"MACD: {last_macd:.2f}, Señal: {last_signal:.2f}, Histograma: {last_histogram:.2f}. "

        # Analizar cruces entre MACD y Signal
        if last_macd > last_signal and df['MACD'].iloc[-2] <= df['MACD_Signal'].iloc[-2]:
            signal = "Compra"
            message += "Cruce alcista detectado (MACD supera a la Señal)."
        elif last_macd < last_signal and df['MACD'].iloc[-2] >= df['MACD_Signal'].iloc[-2]:
            signal = "Venta"
            message += "Cruce bajista detectado (MACD cae por debajo de la Señal)."

        # Analizar la posición respecto a la línea cero
        if last_macd > 0:
            message += " MACD por encima de cero: Momentum alcista."
        elif last_macd < 0:
            message += " MACD por debajo de cero: Momentum bajista."

        # Análisis del Histograma
        if last_histogram > 0 and df['MACD_Hist'].iloc[-2] <= 0:
            message += " Incremento en momentum alcista."
        elif last_histogram < 0 and df['MACD_Hist'].iloc[-2] >= 0:
            message += " Incremento en momentum bajista."

        # Análisis de divergencias
        if len(df) >= 3:
            if last_macd < df['MACD'].iloc[-2] and last_close > prev_close:
                message += " Divergencia bajista: MACD baja mientras precio sube."
                signal = "Divergencia Bajista"
            elif last_macd > df['MACD'].iloc[-2] and last_close < prev_close:
                message += " Divergencia alcista: MACD sube mientras precio baja."
                signal = "Divergencia Alcista"

        return {"signal": signal, "message": message}

    except IndexError:
        return {"signal": "Error", "message": "Error al analizar el MACD. Datos insuficientes"}
    except Exception as e:
        print(f"Error en analyze_macd: {e}")
        return {"signal": "Error", "message": f"Error al analizar el MACD: {e}"}
        
def encontrar_pivotes(precios, max_pivotes=10):
    """Encuentra pivotes máximos y mínimos en una serie de precios."""
    pivotes = []
    for i in range(1, len(precios) - 1):
        if precios[i - 1] < precios[i] > precios[i + 1]:
            pivotes.append((i, precios[i], "maximo"))
        elif precios[i - 1] > precios[i] < precios[i + 1]:
            pivotes.append((i, precios[i], "minimo"))
    # Retornar solo los últimos pivotes relevantes
    return pivotes[-max_pivotes:]

def guardar_pivotes(pivotes_historicos): #Función guardar_pivotes
    """Guarda los pivotes históricos en un archivo JSON."""
    try:
        with open(PIVOTES_FILE, "w") as f:
            json.dump(pivotes_historicos, f, indent=4)
        print(f"Pivotes guardados en {PIVOTES_FILE}")
    except Exception as e:
        print(f"Error al guardar pivotes: {e}")


def analizar_patrones(pivotes, tolerance=0.02):
    """Analiza patrones chartistas basados en pivotes."""
    if len(pivotes) < 3:
        return {"Patrones": "No hay suficientes pivotes"}
    patrones = []
    for i in range(len(pivotes)):
        for j in range(i + 1, len(pivotes)):
            for k in range(j + 1, len(pivotes)):
                p1, p2, p3 = pivotes[i], pivotes[j], pivotes[k]
                # Mismo tipo de pivote (Canales)
                if p1[2] == p2[2] == p3[2]:
                    if p1[2] == "maximo" and p3[0] > p2[0] > p1[0] and p3[1] < p2[1] < p1[1]:
                        patrones.append({"Patron": "Canal Bajista", "pivotes": [p1, p2, p3]})
                    elif p1[2] == "minimo" and p3[0] > p2[0] > p1[0] and p3[1] > p2[1] > p1[1]:
                        patrones.append({"Patron": "Canal Alcista", "pivotes": [p1, p2, p3]})
                # Distinto tipo de pivote (Dobles Suelos/Techos y Triángulos)
                elif p1[2] != p2[2] and p2[2] != p3[2]:
                    if p1[2] == "maximo" and p2[2] == "minimo" and p3[2] == "maximo":
                        if abs(p1[1] - p3[1]) / max(p1[1], p3[1]) < tolerance:
                            patrones.append({"Patron": "Doble Techo", "pivotes": [p1, p2, p3]})
                        elif p1[1] > p3[1] and p2[1] > min(p1[1], p3[1]):
                            patrones.append({"Patron": "Triángulo Simétrico", "pivotes": [p1, p2, p3]})
                    elif p1[2] == "minimo" and p2[2] == "maximo" and p3[2] == "minimo":
                        if abs(p1[1] - p3[1]) / max(p1[1], p3[1]) < tolerance:
                            patrones.append({"Patron": "Doble Suelo", "pivotes": [p1, p2, p3]})
                        elif p1[1] < p3[1] and p2[1] < max(p1[1], p3[1]):
                            patrones.append({"Patron": "Triángulo Simétrico", "pivotes": [p1, p2, p3]})
    return {"Patrones": patrones}

def encontrar_zonas_pivotes(pivotes_actuales, pivotes_historicos, tolerancia=0.02):
    """Encuentra zonas de soporte y resistencia basadas en pivotes."""
    zonas = {}
    for pivote_actual in pivotes_actuales:
        nivel_actual = pivote_actual[1]
        encontrado = False
        for nivel_historico_str, datos_historicos in pivotes_historicos.items():
            nivel_historico = float(nivel_historico_str)
            if abs(nivel_actual - nivel_historico) / max(nivel_actual, nivel_historico) < tolerancia:
                encontrado = True
                if str(nivel_historico) not in zonas:
                    zonas[str(nivel_historico)] = {"conteo": datos_historicos["conteo"] + 1, "tipo": datos_historicos["tipo"]}
                else:
                    zonas[str(nivel_historico)]["conteo"] += datos_historicos["conteo"]
                break
        if not encontrado:
            zonas[str(nivel_actual)] = {"conteo": 1, "tipo": pivote_actual[2]}
    return zonas

def analyze_price_action(df, pivotes_historicos, max_velas=200, max_pivotes=10):
    """Analiza la acción del precio con un rango limitado de datos."""
    try:
        # Limita el rango de análisis
        df = df.tail(max_velas)
        precios = df['close'].values
        pivotes = encontrar_pivotes(precios, max_pivotes=max_pivotes)
        patrones = analizar_patrones(pivotes)
        zonas_sr = encontrar_zonas_pivotes(pivotes, pivotes_historicos)
        
        return {
            "Patrones": patrones["Patrones"],
            "ZonasSR": zonas_sr,
            "UltimosPivotes": pivotes,
        }
    except KeyError as e:
        print(f"Error KeyError: {e}")
        return {"Error": f"Columna faltante: {e}"}
    except Exception as e:
        print(f"Error en analyze_price_action: {e}")
        return {"Error": str(e)}


def analyze_indicators(df, timeframe, pivotes_historicos):
    """Analiza todos los indicadores relevantes."""
    rsi_analysis = analyze_rsi(df)
    vwap_analysis = analyze_vwap(df)
    atr_analysis = analyze_atr(df)
    hullma_analysis = analyze_hullma(df)
    bollinger_analysis = analyze_bollinger_bands(df)
    macd_analysis = analyze_macd(df)
    price_action_analysis = analyze_price_action(df, pivotes_historicos) #Se pasa pivotes_historicos
    return {
        "RSI": rsi_analysis,
        "VWAP": vwap_analysis,
        "ATR": atr_analysis,
        "HULLMA": hullma_analysis,
        "Bollinger": bollinger_analysis,
        "MACD": macd_analysis,
        "PriceAction": price_action_analysis
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

def espera_cierre_vela(timeframe):
    """Espera hasta el cierre de la próxima vela."""
    ahora = time.time()
    intervalo = TIME_INTERVALS[timeframe]
    tiempo_para_siguiente_vela = intervalo - (ahora % intervalo)
    print(f"Esperando {tiempo_para_siguiente_vela:.0f} segundos para el cierre de la vela de {timeframe}...")
    time.sleep(tiempo_para_siguiente_vela)

def main_loop():
    pivotes_historicos = {}
    try:
        with open(PIVOTES_FILE, "r") as f:
            pivotes_historicos = json.load(f)
        print(f"Pivotes historicos cargados desde {PIVOTES_FILE}")
    except FileNotFoundError:
        print(f"Archivo {PIVOTES_FILE} no encontrado. Se creará un nuevo archivo.")
    except json.JSONDecodeError:
        print(f"Error al decodificar json en {PIVOTES_FILE}. Se creará un nuevo archivo.")
        pivotes_historicos = {}

    # Procesamiento inicial (una vez al inicio)
    for timeframe, file_path in CSV_FILES.items():
        df = load_csv(file_path)
        if df is not None and not df.empty:
            print(f"Procesando {timeframe} por primera vez...")
            try:
                indicators = analyze_indicators(df, timeframe, pivotes_historicos)
                report = generate_report(timeframe, indicators)
                export_to_json(report, timeframe)
                LAST_RUN[timeframe] = df.index[-1]
                try:
                    nuevos_pivotes = indicators.get("PriceAction", {}).get("ZonasSR", {}) # Manejo seguro de claves anidadas
                    if nuevos_pivotes: #Verificar si hay zonas SR
                        for nivel, datos in nuevos_pivotes.items():
                            pivotes_historicos.setdefault(nivel, {"conteo": 0, "tipo": datos["tipo"]})
                            pivotes_historicos[nivel]["conteo"] += datos["conteo"]
                except Exception as e:
                    print(f"Error al actualizar pivotes históricos: {e}")
                    traceback.print_exc()
            except Exception as e:
                print(f"Error durante el análisis inicial de {timeframe}: {e}")
                traceback.print_exc()

    while True:
        for timeframe, file_path in CSV_FILES.items():
            espera_cierre_vela(timeframe)
            df = load_csv(file_path)

            if df is not None and not df.empty:
                try:
                    if df.index[-1] != LAST_RUN[timeframe]:
                        print(f"Nueva vela detectada para {timeframe}. Procesando...")
                        try:
                            indicators = analyze_indicators(df, timeframe, pivotes_historicos)
                            report = generate_report(timeframe, indicators)
                            export_to_json(report, timeframe)
                            LAST_RUN[timeframe] = df.index[-1]
                            try:
                                nuevos_pivotes = indicators.get("PriceAction", {}).get("ZonasSR", {}) # Manejo seguro de claves anidadas
                                if nuevos_pivotes: #Verificar si hay zonas SR
                                    for nivel, datos in nuevos_pivotes.items():
                                        pivotes_historicos.setdefault(nivel, {"conteo": 0, "tipo": datos["tipo"]})
                                        pivotes_historicos[nivel]["conteo"] += datos["conteo"]
                            except Exception as e:
                                print(f"Error al actualizar pivotes históricos: {e}")
                                traceback.print_exc()
                        except Exception as e:
                            print(f"Error durante el análisis de {timeframe}: {e}")
                            traceback.print_exc()
                    else:
                        print(f"No hay nueva vela para {timeframe}. Esperando 30 segundos adicionales...")
                        time.sleep(30)
                        df = load_csv(file_path)
                        if df is not None and not df.empty and df.index[-1] != LAST_RUN[timeframe]:
                            print(f"Nueva vela detectada despues de la espera para {timeframe}. Procesando...")
                            try:
                                indicators = analyze_indicators(df, timeframe, pivotes_historicos)
                                report = generate_report(timeframe, indicators)
                                export_to_json(report, timeframe)
                                LAST_RUN[timeframe] = df.index[-1]
                                try:
                                    nuevos_pivotes = indicators.get("PriceAction", {}).get("ZonasSR", {}) # Manejo seguro de claves anidadas
                                    if nuevos_pivotes: #Verificar si hay zonas SR
                                        for nivel, datos in nuevos_pivotes.items():
                                            pivotes_historicos.setdefault(nivel, {"conteo": 0, "tipo": datos["tipo"]})
                                            pivotes_historicos[nivel]["conteo"] += datos["conteo"]
                                except Exception as e:
                                    print(f"Error al actualizar pivotes históricos: {e}")
                                    traceback.print_exc()
                            except Exception as e:
                                print(f"Error durante el analisis despues de la espera de {timeframe}: {e}")
                                traceback.print_exc()
                        else:
                            print(f"Aun no hay nueva vela para {timeframe} despues de la espera.")
                except Exception as e:
                    print(f"Error en la verificacion de nueva vela {timeframe}: {e}")
                    traceback.print_exc()
            elif df is not None and df.empty:
                print(f"DataFrame vacío para {timeframe}. Revisar archivo: {file_path}")
        guardar_pivotes(pivotes_historicos) # Correctamente indentado

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("Script detenido por el usuario.")
    except Exception as e:
        print(f"Error inesperado en el script principal: {e}")
        traceback.print_exc()
    finally:
        print("Fin del script.")
