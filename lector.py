import time
import json
import os


# Configuración de archivos y tiempos
CSV_FILES = {
    "15m": "XBTUSDT_15m.csv",
    "1h": "XBTUSDT_1h.csv",
    "4h": "XBTUSDT_4h.csv",  # Archivo para 4 horas
    "1d": "XBTUSDT_1d.csv"",
}

TIME_INTERVALS = {
   "15m": 900,      # 15 minutos
    "1h": 3600,      # 1 hora
    "4h": 14400,     # 4 horas (60 * 60 * 4)
    "1d": 86400      # 1 día
}
LAST_RUN = {key: 0 for key in CSV_FILES.keys()}
# Función para cargar datos de un archivo CSV
def load_csv(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        print(f"Archivo no encontrado: {file_path}")
        return None
# Función para analizar RSI
import ta
import pandas as pd

def analyze_rsi(df, period=14):
    """Analiza el RSI, incluyendo divergencias y rangos de fuerza."""
    try:
        if len(df) < period:
            return {"value": None, "signal": "Datos insuficientes", "message": "No hay suficientes datos para calcular el RSI."}

        df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=period).rsi()
        last_rsi = df['RSI'].iloc[-1]

        signal = "Neutral"
        message = f"RSI en {last_rsi:.2f}. "

        # Rangos de fuerza
        if last_rsi > 70:
            signal = "Sobrecompra"
            message += "Entrando en zona de sobrecompra. Posible señal de venta."
        elif last_rsi < 30:
            signal = "Sobreventa"
            message += "Entrando en zona de sobreventa. Posible señal de compra."
        elif 60 < last_rsi <= 70:
            signal = "Fuerte Alcista"
            message += "En zona alcista fuerte. Posible continuación de la tendencia alcista."
        elif 30 <= last_rsi < 40:
            signal = "Fuerte Bajista"
            message += "En zona bajista fuerte. Posible continuación de la tendencia bajista."
        else:
            message += "En zona neutral."

        # Detección de divergencias (ejemplo básico - se puede mejorar)
        if len(df) >= 3:
            # Divergencia bajista (precio sube, RSI baja)
            if df['Close'].iloc[-1] > df['Close'].iloc[-2] and df['RSI'].iloc[-1] < df['RSI'].iloc[-2]:
                message += " Posible divergencia bajista."
                if signal == "Sobrecompra":
                  signal = "Divergencia Bajista en Sobrecompra" #Prioridad a la divergencia en zona de sobrecompra
                else:
                  signal = "Divergencia Bajista"
            # Divergencia alcista (precio baja, RSI sube)
            elif df['Close'].iloc[-1] < df['Close'].iloc[-2] and df['RSI'].iloc[-1] > df['RSI'].iloc[-2]:
                message += " Posible divergencia alcista."
                if signal == "Sobreventa":
                  signal = "Divergencia Alcista en Sobreventa" #Prioridad a la divergencia en zona de sobreventa
                else:
                  signal = "Divergencia Alcista"

        return {"value": last_rsi, "signal": signal, "message": message}
    except IndexError:
        return {"value": None, "signal": "Error", "message": "Error al calcular el RSI. DataFrame vacío."}

# Función para analizar VWAP

def analyze_vwap(df):
    """Analiza el VWAP y proporciona señales basadas en su relación con el precio."""
    try:
        if len(df) < 1:
            return {"value": None, "signal": "Datos insuficientes", "message": "No hay suficientes datos para calcular el VWAP."}

        df['VWAP'] = ta.volume.VolumeWeightedAveragePrice(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume']).vwap()
        last_vwap = df['VWAP'].iloc[-1]
        last_close = df['Close'].iloc[-1]

        signal = "Neutral"
        message = f"VWAP en {last_vwap:.2f}. Precio actual en {last_close:.2f}. "

        if last_close > last_vwap:
            signal = "Alcista"
            message += "El precio actual está por encima del VWAP, lo que sugiere una posible tendencia alcista o presión de compra."
        elif last_close < last_vwap:
            signal = "Bajista"
            message += "El precio actual está por debajo del VWAP, lo que sugiere una posible tendencia bajista o presión de venta."
        else:
            message += "El precio actual está en el VWAP. Posible zona de consolidación."

        #Análisis adicional basado en la distancia del precio al VWAP (en porcentaje)
        distancia_porcentual = abs((last_close - last_vwap) / last_vwap) * 100
        message += f" Distancia al VWAP: {distancia_porcentual:.2f}%. "

        if distancia_porcentual > 1: #Ejemplo: Distancia mayor al 1% se considera significativa
          if last_close > last_vwap:
            message += "El precio se ha alejado significativamente del VWAP al alza."
          else:
            message += "El precio se ha alejado significativamente del VWAP a la baja."

        return {"value": last_vwap, "signal": signal, "message": message}

    except IndexError:
        return {"value": None, "signal": "Error", "message": "Error al calcular el VWAP. DataFrame vacío."}
        
# Función para analizar ATR
def analyze_atr(df, period=14, lookback=5): # Se añade el parámetro lookback
    """Analiza el ATR y proporciona información sobre la volatilidad y su comportamiento reciente."""
    try:
        if len(df) < period:
            return {"value": None, "signal": "Datos insuficientes", "message": "No hay suficientes datos para calcular el ATR."}

        df['ATR'] = ta.volatility.AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=period).average_true_range()
        last_atr = df['ATR'].iloc[-1]

        message = f"ATR({period}) en {last_atr:.2f}. "

        # Análisis del comportamiento reciente del ATR
        if len(df) >= lookback + period: #Se asegura que haya suficientes datos para el lookback
            atr_lookback = df['ATR'].iloc[-lookback:] # Obtiene los últimos valores de ATR según lookback
            atr_change = np.diff(atr_lookback) # Calcula las diferencias entre valores consecutivos
            
            #Calcula el cambio porcentual para mejor entendimiento
            atr_percent_change = (atr_change / atr_lookback[:-1]) * 100

            if all(change > 0 for change in atr_change): # Verifica si todos los cambios son positivos
                message += f"La volatilidad ha estado aumentando en los últimos {lookback} periodos. "
                avg_percent_change = np.mean(atr_percent_change)
                message += f"Aumentando en promedio un {avg_percent_change:.2f}% por periodo."
            elif all(change < 0 for change in atr_change): # Verifica si todos los cambios son negativos
                message += f"La volatilidad ha estado disminuyendo en los últimos {lookback} periodos. "
                avg_percent_change = np.mean(atr_percent_change)
                message += f"Disminuyendo en promedio un {abs(avg_percent_change):.2f}% por periodo."
            else:
                message += f"La volatilidad ha mostrado fluctuaciones en los últimos {lookback} periodos."
                avg_percent_change = np.mean(np.abs(atr_percent_change))
                message += f"Con una fluctuacion promedio de {avg_percent_change:.2f}% por periodo."

        return {"value": last_atr, "signal": "Valor calculado", "message": message}

    except IndexError:
        return {"value": None, "signal": "Error", "message": "Error al calcular el ATR. DataFrame vacío."}
# Función para analizar el precio y patrones (chartismo)

def analyze_hullma(df, period=9):
    """Analiza la HULLMA, detecta cruces y proporciona información sobre impulsos."""
    try:
        if len(df) < period + 2:  # Necesitamos al menos dos datos más para comparar aceleración
            return {"value": None, "signal": "Datos insuficientes", "message": "No hay suficientes datos para calcular la HULLMA y detectar impulsos."}

        df['HULLMA'] = ta.trend.HullMovingAverage(df['Close'], window=period).hull_moving_average()
        last_hullma = df['HULLMA'].iloc[-1]
        previous_hullma = df['HULLMA'].iloc[-2]
        previous_previous_hullma = df['HULLMA'].iloc[-3]
        last_close = df['Close'].iloc[-1]
        previous_close = df['Close'].iloc[-2]

        signal = "Neutral"
        message = f"HULLMA({period}) en {last_hullma:.2f}. Precio actual en {last_close:.2f}. "

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
        
        #Analisis de la aceleracion de la HULLMA
        if last_hullma > previous_hullma and previous_hullma > previous_previous_hullma:
            message += " La HULLMA muestra aceleración alcista."
        elif last_hullma < previous_hullma and previous_hullma < previous_previous_hullma:
            message += " La HULLMA muestra aceleración bajista."

        return {"value": last_hullma, "signal": signal, "message": message}

    except IndexError:
        return {"value": None, "signal": "Error", "message": "Error al calcular la HULLMA. DataFrame vacío o datos insuficientes."}

def analyze_bollinger(df, period=20, std=2):
    try:
        indicator_bb = ta.volatility.BollingerBands(close=df["Close"], window=period, window_dev=std)
        df['bb_high'] = indicator_bb.bollinger_hband()
        df['bb_mid'] = indicator_bb.bollinger_mavg()
        df['bb_low'] = indicator_bb.bollinger_lband()
        last_bb_high = df['bb_high'].iloc[-1]
        last_bb_mid = df['bb_mid'].iloc[-1]
        last_bb_low = df['bb_low'].iloc[-1]
        return {"bb_high": last_bb_high, "bb_mid": last_bb_mid, "bb_low": last_bb_low}
    except IndexError:
        print("Error: DataFrame vacío para Bollinger")
        return {"bb_high": None, "bb_mid": None, "bb_low": None}

def analyze_macd(df, fast=12, slow=26, signal=9):
    try:
        macd = ta.trend.MACD(close=df["Close"], window_fast=fast, window_slow=slow, window_sign=signal)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        last_macd = df['macd'].iloc[-1]
        last_macd_signal = df['macd_signal'].iloc[-1]
        last_macd_diff = df['macd_diff'].iloc[-1]
        return {"macd": last_macd, "macd_signal": last_macd_signal, "macd_diff": last_macd_diff}
    except IndexError:
        print("Error: DataFrame vacío para MACD")
        return {"macd": None, "macd_signal": None, "macd_diff": None}

def analizar_patrones(pivotes, tolerance=0.02):
    """Analiza patrones chartistas basados en pivotes."""
    if len(pivotes) < 3:
        return {"Patrones": "No hay suficientes pivotes"}
    patrones = []
    for i in range(len(pivotes)):
        for j in range(i + 1, len(pivotes)):
            for k in range(j + 1, len(pivotes)):
                p1 = pivotes[i]
                p2 = pivotes[j]
                p3 = pivotes[k]
                if p1[2] == p2[2] == p3[2]:  # Mismo tipo de pivote (Canales)
                    if p1[2] == "maximo":  # Canal bajista
                        if p3[0] > p2[0] > p1[0] and p3[1] < p2[1] < p1[1]:
                            patrones.append({"Patron": "Canal Bajista", "pivotes": [p1, p2, p3]})
                    elif p1[2] == "minimo":  # Canal alcista
                        if p3[0] > p2[0] > p1[0] and p3[1] > p2[1] > p1[1]:
                            patrones.append({"Patron": "Canal Alcista", "pivotes": [p1, p2, p3]})
                elif p1[2] != p2[2] and p2[2] != p3[2]:  # Distinto tipo de pivote (Dobles Suelos/Techos y Triángulos)
                    if p1[2] == "maximo" and p2[2] == "minimo" and p3[2] == "maximo":
                        if abs(p1[1] - p3[1]) / max(p1[1], p3[1]) < tolerance:
                            patrones.append({"Patron": "Doble Techo", "pivotes": [p1, p2, p3]})
                        elif p1[1] > p3[1] and p2[1] > min(p1[1],p3[1]):
                            patrones.append({"Patron": "Triangulo Simetrico", "pivotes": [p1, p2, p3]})
                        else:
                            patrones.append({"Patron": "Triangulo Ascendente", "pivotes": [p1, p2, p3]})
                    elif p1[2] == "minimo" and p2[2] == "maximo" and p3[2] == "minimo":
                        if abs(p1[1] - p3[1]) / max(p1[1], p3[1]) < tolerance:
                            patrones.append({"Patron": "Doble Suelo", "pivotes": [p1, p2, p3]})
                        elif p1[1] < p3[1] and p2[1] < max(p1[1],p3[1]):
                            patrones.append({"Patron": "Triangulo Simetrico", "pivotes": [p1, p2, p3]})
                        else:
                            patrones.append({"Patron": "Triangulo Descendente", "pivotes": [p1, p2, p3]})
    return {"Patrones": patrones}

def encontrar_zonas_pivotes(pivotes_actuales, pivotes_historicos, tolerancia=0.02):
    zonas = {}
    for pivote_actual in pivotes_actuales:
        nivel_actual = pivote_actual[1]
        encontrado = False  # Variable para controlar si se encontró una zona cercana
        for nivel_historico_str, datos_historicos in pivotes_historicos.items(): #Iteramos sobre los items para obtener clave y valor
            nivel_historico = float(nivel_historico_str) #Convertimos la clave a float para la comparacion
            if abs(nivel_actual - nivel_historico) / max(nivel_actual, nivel_historico) < tolerancia:
                encontrado = True
                if str(nivel_historico) not in zonas:
                    zonas[str(nivel_historico)] = {"conteo": datos_historicos["conteo"] + 1, "tipo": datos_historicos["tipo"]} #Usamos el tipo de pivote historico
                else:
                    zonas[str(nivel_historico)]["conteo"] += datos_historicos["conteo"]
                break  # Importante: salir del bucle interno una vez encontrada la zona
        if not encontrado:  # Si no se encontró ninguna zona cercana, se crea una nueva
            zonas[str(nivel_actual)] = {"conteo": 1, "tipo": pivote_actual[2]}
    return zonas
def analyze_price_action(df, pivotes_historicos):
    """Función principal para analizar la acción del precio, incluyendo zonas SR."""
    try:
        precios = df['Close'].values
        pivotes = encontrar_pivotes(precios)
        patrones = analizar_patrones(pivotes)
        zonas_sr = encontrar_zonas_pivotes(pivotes, pivotes_historicos)

        resultados = {"Patrones": patrones["Patrones"], "ZonasSR": zonas_sr}  # Combina los resultados
        return resultados
    except IndexError:
        return {"Patron": "No hay suficientes datos"}

def analyze_indicators(df, timeframe):
    """Analiza todos los indicadores relevantes."""
    rsi_analysis = analyze_rsi(df)
    vwap_analysis = analyze_vwap(df)
    atr_analysis = analyze_atr(df)
    hullma_analysis = analyze_hullma(df)
    bollinger_analysis = analyze_bollinger(df)
    macd_analysis = analyze_macd(df)
    price_action_analysis = analyze_price_action(df)
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


def export_to_json(report, timeframe, max_reports=10):
    """Exporta/acumula el informe a un archivo JSON con el nombre de la temporalidad,
    manteniendo los últimos max_reports registros."""

    output_file = f"report_{timeframe}.json"

    try:
        with open(output_file, "r") as f:
            existing_reports = json.load(f)
    except FileNotFoundError:
        existing_reports = []

    existing_reports.append(report)

    if len(existing_reports) > max_reports:
        existing_reports = existing_reports[-max_reports:]

    with open(output_file, "w") as f:
        json.dump(existing_reports, f, indent=4)
    print(f"Informe para {timeframe} (acumulado, últimos {max_reports} registros) exportado a {output_file}")

def main_loop():
    pivotes_historicos = {}
    try:
        with open("pivotes_historicos.json", "r") as f:
            pivotes_historicos = json.load(f)
    except FileNotFoundError:
        pass

    while True:
        current_time = time.time()

        for timeframe, file_path in CSV_FILES.items():
            if current_time - LAST_RUN.get(timeframe, 0) >= TIME_INTERVALS[timeframe]:
                print(f"Procesando {timeframe}...")
                df = load_csv(file_path)

                if df is not None and not df.empty:
                    indicators = analyze_indicators(df, timeframe, pivotes_historicos)
                    report = generate_report(timeframe, indicators)
                    export_to_json(report, timeframe) #Llamada a export_to_json
                    LAST_RUN[timeframe] = current_time

                    try:
                        nuevos_pivotes = indicators["PriceAction"]["ZonasSR"]
                        for nivel, datos in nuevos_pivotes.items():
                            if nivel in pivotes_historicos:
                                pivotes_historicos[nivel]["conteo"] += datos["conteo"]
                            else:
                                pivotes_historicos[nivel] = datos
                    except KeyError as e:
                        print(f"Error al acceder a la clave: {e}. Probablemente no hay zonas SR.")
                        print(indicators["PriceAction"])

                elif df is not None and df.empty:
                    print(f"DataFrame vacío para {timeframe}. Revisar archivo: {file_path}")

        with open("pivotes_historicos.json", "w") as f:
            json.dump(pivotes_historicos, f, indent=4)

        time.sleep(1)
