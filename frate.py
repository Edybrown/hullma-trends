import pandas as pd

# Cargar los datos desde el archivo CSV
file_path = "coinalyze_data/datos_4hour.csv"
df = pd.read_csv(file_path)

# Verificar si las columnas necesarias existen
required_columns = [
    'funding_rate_fr_close_BTCUSDT_PERP.A',
    'long_short_ratio_longs_percentage_BTCUSDT_PERP.A',
    'long_short_ratio_shorts_percentage_BTCUSDT_PERP.A'
]

if all(col in df.columns for col in required_columns):
    # Calcular el funding rate mensual
    df['funding_rate_monthly'] = df['funding_rate_fr_close_BTCUSDT_PERP.A'] * 90
    
    # Calcular el desequilibrio
    df['desequilibrio'] = df['long_short_ratio_longs_percentage_BTCUSDT_PERP.A'] - df['long_short_ratio_shorts_percentage_BTCUSDT_PERP.A']
    
    # Calcular estadísticas descriptivas
    estadisticas = df[['funding_rate_monthly', 'desequilibrio']].describe()
    
    # Calcular la correlación
    correlacion = df['funding_rate_monthly'].corr(df['desequilibrio'])
    estadisticas.loc['correlacion'] = [correlacion, "N/A"]

    # Exportar a Excel
    output_path = "funding_analysis.xlsx"
    with pd.ExcelWriter(output_path) as writer:
        df.to_excel(writer, sheet_name="Datos Procesados", index=False)
        estadisticas.to_excel(writer, sheet_name="Estadísticas")

    print(f"Análisis completado. Datos guardados en {output_path}")
else:
    print("Faltan columnas necesarias en el archivo CSV.")
    print("Columnas disponibles:", df.columns)
