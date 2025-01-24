import pandas as pd

# Suponiendo que el archivo CSV ya está cargado como df
# Paso 1: Renombrar columnas para hacerlas más cortas
df.rename(columns={
    'funding_rate_fr_close_BTCUSDT_PERP.A': 'funding_rate',
    'long_short_ratio_longs_percentage_BTCUSDT_PERP.A': 'longs_percentage',
    'long_short_ratio_shorts_percentage_BTCUSDT_PERP.A': 'shorts_percentage',
    'long_short_ratio_timestamp_BTCUSDT_PERP.A': 'timestamp'
}, inplace=True)

# Paso 2: Calcular el funding rate mensual (multiplicar por 90)
df['funding_rate_monthly'] = df['funding_rate'] * 90

# Paso 3: Calcular el desequilibrio
df['desequilibrio'] = df['longs_percentage'] - df['shorts_percentage']

# Paso 4: Calcular estadísticas descriptivas
stats = df[['funding_rate_monthly', 'desequilibrio']].describe()

# Paso 5: Calcular correlación entre funding rate mensual y desequilibrio
correlacion = df['funding_rate_monthly'].corr(df['desequilibrio'])

# Agregar correlación como fila adicional en las estadísticas
stats.loc['correlation'] = [correlacion, '']

# Paso 6: Exportar los datos y las estadísticas a Excel
output_file = 'funding_analysis.xlsx'

with pd.ExcelWriter(output_file) as writer:
    df.to_excel(writer, sheet_name='Datos Procesados', index=False)
    stats.to_excel(writer, sheet_name='Estadísticas')

print(f"Análisis exportado a {output_file}")
