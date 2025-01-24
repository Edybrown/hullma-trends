import pandas as pd
import matplotlib.pyplot as plt

# Cargar datos
df = pd.read_csv("coinalyze_data/datos_combined.csv")

# Convertir timestamp a datetime
df['fecha_hora'] = pd.to_datetime(df['fecha_hora'])

# Calcular el desequilibrio porcentual (longs - shorts)
df['desequilibrio'] = df['long_short_ratio_long_percentage_BTCUSDT_PERP.A'] - df['long_short_ratio_short_percentage_BTCUSDT_PERP.A']

# Funding rate mensualizado
# Número de períodos mensuales, considerando un funding rate cada 8 horas
periodos_mensuales = 24 * 30 / 8
df['funding_rate_mensual'] = df['funding_rate_fr_close_BTCUSDT_PERP.A'] * periodos_mensuales

# Comparar el desequilibrio porcentual con el funding rate mensualizado
df['diferencia_porcentual'] = (df['desequilibrio'] - df['funding_rate_mensual']) / df['funding_rate_mensual'] * 100

# Visualización: Desequilibrio vs Funding Rate
plt.figure(figsize=(12, 6))
plt.plot(df['fecha_hora'], df['desequilibrio'], label="Desequilibrio (%)")
plt.plot(df['fecha_hora'], df['funding_rate_mensual'], label="Funding Rate Mensualizado (%)")
plt.legend()
plt.title("Comparación entre Desequilibrio y Funding Rate Mensualizado")
plt.xlabel("Fecha")
plt.ylabel("Porcentaje")
plt.grid()
plt.show()

# Visualización: Diferencia porcentual
plt.figure(figsize=(12, 6))
plt.plot(df['fecha_hora'], df['diferencia_porcentual'], label="Diferencia Porcentual (%)", color="red")
plt.legend()
plt.title("Diferencia Porcentual entre Desequilibrio y Funding Rate")
plt.xlabel("Fecha")
plt.ylabel("Diferencia Porcentual (%)")
plt.grid()
plt.show()

# Correlación entre desequilibrio y funding rate mensualizado
correlation = df[['desequilibrio', 'funding_rate_mensual']].corr()
print("Correlación entre Desequilibrio y Funding Rate Mensualizado:")
print(correlation)
