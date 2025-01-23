import pandas as pd
import numpy as np
import os
import ta

def calcular_hma(serie, periodo=12):
    return ta.trend.hma(close=serie, window=periodo)

carpeta_csv = 'coinalyze_data'

for archivo in os.listdir(carpeta_csv):
    if archivo.endswith('.csv'):
        ruta_csv = os.path.join(carpeta_csv, archivo)

        try:
            df = pd.read_csv(ruta_csv, parse_dates=['fecha_hora'])
        except FileNotFoundError:
            print(f"No se encontró el archivo: {archivo}")
            continue
        except pd.errors.ParserError:
            print(f"Error al parsear el archivo {archivo}. Verifique el formato.")
            continue

        columnas_necesarias = [
            'ohlcv_close_BTCUSDT_PERP.A',
            'fecha_hora',
            'desequilibrio_OI'
        ]

        if all(col in df.columns for col in columnas_necesarias):
            df = df.set_index('fecha_hora')
            temporalidades = ['1H', '4H', '1D']

            for temporalidad in temporalidades:
                df_resampled = df.resample(temporalidad).last()
                if df_resampled.empty:
                    print(f"No hay datos para la temporalidad {temporalidad} en el archivo {archivo}")
                    continue

                # Import statement for ta library
                import ta  # Make sure this line is at the beginning

                df_resampled['hma_12'] = calcular_hma(df_resampled['ohlcv_close_BTCUSDT_PERP.A'])

                df_resampled['cruce'] = np.where(df_resampled['hma_12'] > df_resampled['hma_12'].shift(1), 1, np.where(df_resampled['hma_12'] < df_resampled['hma_12'].shift(1), -1, 0))

                for tipo_cruce in [1, -1]:
                    desequilibrios_antes = []
                    desequilibrios_despues = []
                    for i in range(1, len(df_resampled)):
                        if df_resampled['cruce'].iloc[i] == tipo_cruce:
                            desequilibrio_antes = df_resampled['desequilibrio_OI'].iloc[i - 1]
                            desequilibrio_despues = df_resampled['desequilibrio_OI'].iloc[i]
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
                        print(f"No hay cruces {tipo_cruce_str} en {archivo} para
