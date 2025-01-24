import pandas as pd
import matplotlib.pyplot as plt

# Cargar el archivo CSV (asegúrate de reemplazar 'tu_archivo.csv' con la ruta de tu archivo)
carpeta = 'coinalyze_data'
archivo = 'datos_4hour.csv'
ruta_archivo = os.path.join(carpeta, archivo)

# Cargar el archivo CSV
df = pd.read_csv(ruta_archivo)

# Verificar si las columnas necesarias existen
required_columns = [
    'funding_rate_fr_close_BTCUSDT_PERP.A',
    'long_short_ratio_longs_percentage_BTCUSDT_PERP.A',
    'long_short_ratio_shorts_percentage_BTCUSDT_PERP.A',
    'long_short_ratio_timestamp_BTCUSDT_PERP.A'
]

if all(col in df.columns for col in required_columns):
    # Calcular el desequilibrio (diferencia entre largos y cortos)
    df['desequilibrio'] = df['long_short_ratio_longs_percentage_BTCUSDT_PERP.A'] - df['long_short_ratio_shorts_percentage_BTCUSDT_PERP.A']
    
    # Relación del desequilibrio con el funding rate (porcentaje relativo)
    df['relacion_funding_desequilibrio'] = (df['desequilibrio'] / df['funding_rate_fr_close_BTCUSDT_PERP.A']).fillna(0)
    
    # Imprimir resultados iniciales
    print("Análisis de funding rate y desequilibrio completado:")
    print(df[['funding_rate_fr_close_BTCUSDT_PERP.A', 'desequilibrio', 'relacion_funding_desequilibrio']].head())
    
    # Graficar los datos
    plt.figure(figsize=(12, 6))
    
    # Funding rate
    plt.subplot(2, 1, 1)
    plt.plot(df['funding_rate_fr_close_BTCUSDT_PERP.A'], label='Funding Rate (Cierre)', color='blue')
    plt.title('Funding Rate (Cierre)')
    plt.legend()
    plt.grid()

    # Desequilibrio
    plt.subplot(2, 1, 2)
    plt.plot(df['desequilibrio'], label='Desequilibrio (Largos - Cortos)', color='green')
    plt.title('Desequilibrio: Largos vs Cortos')
    plt.legend()
    plt.grid()

    plt.tight_layout()
    plt.show()
    
    # Calcular correlación
    correlacion = df['funding_rate_fr_close_BTCUSDT_PERP.A'].corr(df['desequilibrio'])
    print(f"Correlación entre el funding rate y el desequilibrio: {correlacion}")

    # Procesar fechas y agrupar por mes
    df['fecha'] = pd.to_datetime(df['long_short_ratio_timestamp_BTCUSDT_PERP.A'])
    df.set_index('fecha', inplace=True)

    # Agrupar por mes y mostrar el resumen
    resumen_mensual = df.resample('M').mean()
    print(resumen_mensual[['funding_rate_fr_close_BTCUSDT_PERP.A', 'desequilibrio']])
else:
    print("Una o más columnas necesarias no están presentes en el DataFrame.")
    print("Columnas disponibles:", df.columns)
