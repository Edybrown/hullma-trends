# Función para calcular el Indicador de Presión Direccional Modificado con Funding Rate anualizado
def calcular_indicador_anualizado(funding_rate, temporalidad, long_short_ratio, oi_total, longs_percentage):
    # Definir el número de periodos por año según la temporalidad
    if temporalidad == '1hour':
        periods_per_year = 365 * 24  # 24 periodos de 1 hora en un día, 365 días
    elif temporalidad == '8hours':
        periods_per_year = 365 * 3  # 3 periodos de 8 horas en un día, 365 días
    elif temporalidad == '1day':
        periods_per_year = 365  # 1 periodo por día, 365 días
    else:
        periods_per_year = 365  # Valor por defecto si la temporalidad no es reconocida

    # Anualizar el funding rate
    funding_rate_annualized = funding_rate * periods_per_year

    # Evitar valores cero en OI
    oi_total = max(oi_total, 1)  # Prevenir que OI sea 0, establecer en 1 si es muy bajo

    # Asegurémonos de que el funding_rate esté bien procesado, usaremos valor absoluto
    funding_rate_abs = abs(funding_rate_annualized)

    # Evitar valores extremos con un logaritmo de OI más seguro
    try:
        log_oi = math.log(oi_total)  # Logaritmo de OI
    except ValueError:
        log_oi = 0  # En caso de un valor no válido en OI

    # Termino de la fórmula
    term1 = (funding_rate_abs * 100) / (long_short_ratio + 0.0001)
    term2 = log_oi
    term3 = abs(longs_percentage - 50) / 50

    # Asegurarse de que no tengamos división por 0
    if term1 == 0 or term2 == 0:
        return 0
    
    # Indicador de Presión Direccional
    indicador = term1 * term2 * term3
    return indicador
