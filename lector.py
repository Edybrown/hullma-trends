import time
import json
import os


# Configuración de archivos y tiempos
CSV_FILES = {
    "15m": "XBTUSDT_15m.csv",
    "1h": "XBTUSDT_1h.csv",
    "4h": "XBTUSDT_4h.csv",  # Archivo para 4 horas
    "1d": "XBTUSDT_1d.csv""
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
def analyze_rsi(df):
    """Analiza el RSI para identificar señales."""
    # Placeholder: Implementar análisis detallado del RSI
    return {"RSI": "Análisis pendiente"}


# Función para analizar VWAP

def analyze_vwap(df):
    """Analiza el VWAP y su interacción con el precio."""
    # Placeholder: Implementar análisis detallado del VWAP
    return {"VWAP": "Análisis pendiente"}

# Función para analizar ATR
def analyze_atr(df):
    """Analiza el ATR para identificar volatilidad."""
    # Placeholder: Implementar análisis detallado del ATR
    return {"ATR": "Análisis pendiente"}
# Función para analizar el precio y patrones (chartismo)

def analyze_hullma(df, period=9): #periodo por defecto de 9
    try:
      df['HULLMA'] = ta.trend.HullMovingAverage(df['Close'], window=period).hull_moving_average()
      last_hullma = df['HULLMA'].iloc[-1]
      return {"HULLMA": last_hullma}
    except IndexError:
        print("Error: DataFrame vacío para HULLMA")
        return {"HULLMA": None}

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
# Función para exportar informes a JSON
def export_to_json(reports):
    """Exporta los informes generados a un archivo JSON."""
    timestamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    output_file = f"reports_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump(reports, f, indent=4)
    print(f"Informes exportados a {output_file}")

# Bucle principal
def main_loop():
    pivotes_historicos = {}  # Inicializar al principio
    try:
        with open("pivotes_historicos.json", "r") as f:
            pivotes_historicos = json.load(f)
    except FileNotFoundError:
        pass

    while True:
        current_time = time.time()
        all_reports = []

        for timeframe, file_path in CSV_FILES.items():
            # Verificar si es momento de procesar
            if current_time - LAST_RUN.get(timeframe,0) >= TIME_INTERVALS[timeframe]: #Se usa .get para evitar errores si no existe la clave
                print(f"Procesando {timeframe}...")
                df = load_csv(file_path)
                if df is not None and not df.empty: #Se añade la comprobacion de df.empty
                    # Análisis completo (ahora pasando pivotes_historicos)
                    indicators = analyze_indicators(df, timeframe, pivotes_historicos)

                    # Generar informe
                    report = generate_report(timeframe, indicators)
                    all_reports.append(report)

                    # Actualizar el tiempo de última ejecución
                    LAST_RUN[timeframe] = current_time

                    # Actualizar pivotes_historicos (CORREGIDO)
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

        # Exportar todos los informes
        if all_reports:
            export_to_json(all_reports)

        # Guardar pivotes_historicos (FUERA del bucle de timeframes)
        with open("pivotes_historicos.json", "w") as f:
            json.dump(pivotes_historicos, f, indent=4)

        # Pausa antes del siguiente ciclo
        time.sleep(1)
if __name__ == "__main__":
    main_loop() 
