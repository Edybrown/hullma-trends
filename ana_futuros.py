import pandas as pd
import numpy as np
import os

# Configuración
carpeta_datos = "coinalyze_data"
nombre_archivo = "datos_4h.csv"
apalancamiento = 10  # Apalancamiento promedio (ajustar si es necesario)

# Cargar datos
ruta_archivo = os.path.join(carpeta_datos, nombre_archivo)
try:
    df = pd.read_csv(ruta_archivo)
except FileNotFoundError:
    print(f"Error: No se encontró el archivo {nombre_archivo} en la carpeta {carpeta_datos}")
    exit()

# Seleccionar columnas relevantes y renombrarlas para mayor claridad
try:
    df = df[["fecha_hora", "long_short_ratio_longs_percentage_", "long_short_ratio_shorts_percentage_", "funding_rate"]].copy()
    df.rename(columns={
        "long_short_ratio_longs_percentage_": "longs_percentage",
        "long_short_ratio_shorts_percentage_": "shorts_percentage",
        "funding_rate": "funding_rate_4h"
    }, inplace=True)
except KeyError as e:
    print(f"Error: Falta la columna {e} en el archivo CSV.")
    exit()


# Convertir la columna 'fecha_hora' a datetime
df['fecha_hora'] = pd.to_datetime(df['fecha_hora'])

# Calcular la diferencia Long/Short
df["diferencia_long_short"] = df["longs_percentage"] - df["shorts_percentage"]

# Calcular el Funding Rate mensual y ajustado
df["funding_rate_mensual"] = df["funding_rate_4h"] * 3 * 30  # 3 cobros al día, 30 días al mes
df["funding_rate_ajustado"] = df["funding_rate_mensual"] * apalancamiento

#Evitar la division por cero
df = df[df["funding_rate_ajustado"] != 0].copy()

# Calcular la proporción
df["proporcion"] = df["diferencia_long_short"] / df["funding_rate_ajustado"]

# Análisis de la Proporción
print("Análisis de la Proporción:")
print(f"Promedio de la proporción: {df['proporcion'].mean()}")
print(f"Rango de la proporción: {df['proporcion'].min()} - {df['proporcion'].max()}")
print(f"Desviación estándar de la proporción: {df['proporcion'].std()}")

#Visualizacion de datos
import matplotlib.pyplot as plt
plt.figure(figsize=(12, 6))
plt.plot(df['fecha_hora'], df['proporcion'])
plt.xlabel('Fecha y Hora')
plt.ylabel('Proporción (Diferencia L/S / Funding Rate Ajustado)')
plt.title('Evolución de la Proporción a lo largo del Tiempo')
plt.grid(True)
plt.show()

# Análisis de la relación con el precio (requiere datos de precio)
# Si tienes datos de precio en otro archivo, puedes cargarlos y unirlos al DataFrame df
# Ejemplo hipotético (necesitas adaptar esto a tus datos reales):

# Supongamos que tienes datos de precio en un DataFrame llamado df_precio con columnas 'fecha_hora' y 'precio'
# df = pd.merge(df, df_precio, on='fecha_hora', how='left')
# if 'precio' in df.columns:
#     plt.figure(figsize=(12, 6))
#     plt.plot(df['fecha_hora'], df['proporcion'], label='Proporción')
#     plt.plot(df['fecha_hora'], df['precio'], label='Precio', secondary_y=True) # Eje secundario para el precio
#     plt.xlabel('Fecha y Hora')
#     plt.ylabel('Proporción / Precio')
#     plt.title('Relación entre la Proporción y el Precio')
#     plt.legend()
#     plt.grid(True)
#     plt.show()
# else:
#     print("No se encontraron datos de precio para analizar la correlación.")

# Mostrar las primeras filas del DataFrame con los cálculos
print("\nPrimeras filas del DataFrame con los cálculos:")
print(df.head())
