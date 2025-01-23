import pandas as pd
import numpy as np
import os
import ta

def calcular_hma(serie, periodo=12):
    try:
        return ta.trend.hma(close=serie, window=periodo)
    except Exception as e:
        print(f"Error al calcular la HMA: {e}")
        return pd.Series(index=serie.index, dtype='float64') #Retorna una serie vacia en caso de error

carpeta_csv = 'coinalyze_data'

if not os.path.exists(carpeta_csv):
    os.makedirs(carpeta_csv)
    print(f"Se ha creado la carpeta: {carpeta_csv}")

for archivo in os.listdir(carpeta_csv):
    if archivo.endswith('.csv'):
        ruta_csv = os.path.join(carpeta_csv, archivo)
        print(f"Procesando archivo: {archivo}") #mensaje para saber que archivo se esta procesando
        try:
            df = pd.read_csv(ruta_csv, parse_dates=['fecha_hora'])
        except FileNotFoundError:
            print(f"No se encontró el archivo: {archivo}")
            continue
        except pd.errors.ParserError:
            print(f"Error al parsear el archivo {archivo}. Verifique el formato.")
            continue
        except Exception as e:
            print(f"Error desconocido al leer el archivo {archivo}: {e}")
            continue

        columnas_necesarias = [
            'ohlcv_close_BTCUSDT_PERP.A',
            'fecha_hora',
            'desequilibrio_OI'
        ]

        if all(col in df.columns for col in columnas_necesarias):
            try:
                df = df.set_index('fecha_hora')
                temporalidades = ['1H', '4H', '1D']

                for temporalidad in temporalidades:
                    df_resampled = df.resample(temporalidad).last()
                    if df_resampled.empty:
                        print(f"No hay datos para la temporalidad {temporalidad} en el archivo {archivo}")
                        continue

                    df_resampled['hma_12'] = calcular_hma(df_resampled['ohlcv_close_BTCUSDT_PERP.A'])

                    # Eliminar filas con NaN después del cálculo de la HMA
                    df_resampled.dropna(inplace=True)

                    if df_resampled.empty: #Comprobar si despues de eliminar los NaN quedo vacio el dataframe
                        print(f"No hay datos suficientes para calcular la HMA en la temporalidad {temporalidad} en el archivo {archivo}")
                        continue

                    df_resampled['cruce'] = np.where(df_resampled['hma_12'] > df_resampled['hma_12'].shift(1), 1, np.where(df_resampled['hma_12'] < df_resampled['hma_12'].shift(1), -1, 0))

                    for tipo_cruce in [1, -1]:
                        desequilibrios_antes = []
                        desequilibrios_despues = []
                        for i in range(1, len(df_resampled)):
                            if df_resampled['cruce'].iloc[i] == tipo_cruce:
                                if i > 0 and i < len(df_resampled) -1: #Comprobar que no se salga del rango del dataframe
                                    desequilibrio_antes = df_resampled['desequilibrio_OI'].iloc[i - 1]
                                    desequilibrio_despues = df_resampled['desequilibrio_OI'].iloc[i + 1] #Toma el valor DESPUES del cruce
                                    desequilibrios_antes.append(desequilibrio_antes)
                                    desequilibrios_despues.append(desequilibrio_despues)

                        if desequilibrios_antes:
                            promedio_antes = np.mean(desequilibrios_antes)
                            promedio_despues = np.mean(desequilibrios_despues)
                            tipo_cruce_str = "Alcista" if tipo_cruce == 1 else "Bajista"
                            print(f"Promedio del desequilibrio_OI en {archivo} (Temporalidad: {temporalidad}, Cruce {tipo_cruce_str}):")
                            print(f"Antes del cruce: {promedio_antes:.2f}%")
                            print(f"Después del cruce: {promedio_despues:.2f}%\n")
                        else:
                            tipo_cruce_str = "Alcista" if tipo_cruce == 1 else "Bajista"
                            print(f"No hay cruces {tipo_cruce_str} en {archivo} para la temporalidad {temporalidad}\n")

            except Exception as e:
                print(f"Error durante el procesamiento del archivo {archivo}: {e}")
                continue

        else:
            print(f"Faltan algunas columnas necesarias en el archivo: {archivo}")

print("Proceso completado.")
