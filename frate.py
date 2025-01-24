import pandas as pd

# Cargar los datos desde el archivo CSV
file_path = "coinalyze_data/datos_4hour.csv"
df = pd.read_csv(file_path)

# Renombrar columnas para simplificar
df.rename(columns={
    'funding_rate_fr_close_BTCUSDT_PERP.A': 'funding_rate',
    'long_short_ratio_longs_percentage_BTCUSDT_PERP.A': 'longs_pct',
    'long_short_ratio_shorts_percentage_BTCUSDT_PERP.A': 'shorts_pct',
    'long_short_ratio_timestamp_BTCUSDT_PERP.A': 'timestamp'
}, inplace=True)

# Convertir el timestamp a formato datetime y establecerlo como índice
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp', inplace=True)

# Calcular el desequilibrio (diferencia entre largos y cortos)
df['desequilibrio'] = df['longs_pct'] - df['shorts_pct']

# Calcular el funding rate mensual acumulado
df['monthly_funding_rate'] = df['funding_rate'] * 90

# Agrupar por mes y calcular estadísticas
monthly_stats = df.resample('M').agg({
    'monthly_funding_rate': ['mean', 'std', 'min', 'max', 'sum'],
    'desequilibrio': ['mean', 'std', 'min', 'max'],
    'funding_rate': ['mean', 'std'],
})

# Aplanar columnas para facilitar el análisis
monthly_stats.columns = ['_'.join(col).strip() for col in monthly_stats.columns]

# Calcular correlaciones mensuales
correlation = df.resample('M').apply(
    lambda x: x['funding_rate'].corr(x['desequilibrio'])
)
monthly_stats['correlation_funding_desequilibrio'] = correlation

# Guardar los datos procesados en un archivo Excel
output_file = "monthly_funding_analysis.xlsx"
with pd.ExcelWriter(output_file) as writer:
    df.to_excel(writer, sheet_name="Raw_Data")  # Datos originales procesados
    monthly_stats.to_excel(writer, sheet_name="Monthly_Stats")  # Estadísticas mensuales

print(f"Análisis completo guardado en {output_file}.")
