import pandas as pd

# Función para calcular la HMA
def calcular_hma(datos, periodo):
    wma1 = datos['close'].rolling(window=periodo // 2).mean()
    wma2 = datos['close'].rolling(window=periodo).mean()
    hma = (2 * wma1 - wma2).rolling(window=int(periodo ** 0.5)).mean()
    return hma

# Procesar archivo y temporalidad
def procesar_archivo(archivo, temporalidad):
    print(f"Procesando archivo: {archivo}")
    try:
        datos = pd.read_csv(archivo)
        datos['hma'] = calcular_hma(datos, 14)
        
        if datos['hma'].isna().all():
            print(f"Sin datos válidos después de calcular la HMA para {temporalidad} en {archivo}.")
            return

        resultados = {
            'cruce_alcista': {'positivos': [], 'negativos': []},
            'cruce_bajista': {'positivos': [], 'negativos': []},
        }

        for i in range(1, len(datos) - 1):
            if pd.notna(datos['hma'].iloc[i - 1]) and pd.notna(datos['hma'].iloc[i]):
                # Detectar cruces
                if datos['hma'].iloc[i - 1] < datos['close'].iloc[i - 1] and datos['hma'].iloc[i] >= datos['close'].iloc[i]:
                    tipo_cruce = 'cruce_alcista'
                elif datos['hma'].iloc[i - 1] > datos['close'].iloc[i - 1] and datos['hma'].iloc[i] <= datos['close'].iloc[i]:
                    tipo_cruce = 'cruce_bajista'
                else:
                    continue

                # Desequilibrio en la vela anterior y posterior al cruce
                desequilibrio_anterior = ((datos['high'].iloc[i - 1] - datos['low'].iloc[i - 1]) / datos['low'].iloc[i - 1]) * 100
                desequilibrio_posterior = ((datos['high'].iloc[i + 1] - datos['low'].iloc[i + 1]) / datos['low'].iloc[i + 1]) * 100

                # Clasificar desequilibrios
                if desequilibrio_anterior >= 0:
                    resultados[tipo_cruce]['positivos'].append(desequilibrio_anterior)
                else:
                    resultados[tipo_cruce]['negativos'].append(desequilibrio_anterior)

                if desequilibrio_posterior >= 0:
                    resultados[tipo_cruce]['positivos'].append(desequilibrio_posterior)
                else:
                    resultados[tipo_cruce]['negativos'].append(desequilibrio_posterior)

        for tipo_cruce, datos_cruce in resultados.items():
            positivos = datos_cruce['positivos']
            negativos = datos_cruce['negativos']

            print(f"{archivo} ({temporalidad}): {tipo_cruce.capitalize()}")
            print(f"  Positivos - Cantidad: {len(positivos)}, Promedio: {sum(positivos) / len(positivos) if positivos else 0:.2f}%")
            print(f"  Negativos - Cantidad: {len(negativos)}, Promedio: {sum(negativos) / len(negativos) if negativos else 0:.2f}%")

    except Exception as e:
        print(f"Error procesando el archivo {archivo}: {e}")

# Lista de archivos y temporalidades
archivos_temporalidades = [
    ('datos_daily.csv', '1d'),
    ('datos_4hour.csv', '4h'),
    ('datos_1hour.csv', '1h'),
]

for archivo, temporalidad in archivos_temporalidades:
    procesar_archivo(archivo, temporalidad)
