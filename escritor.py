import os
import time
import json # Solo se usa para decodificar el informe simulado en este ejemplo
from datetime import datetime, timedelta


OUTPUT_DIR = "Analisis_trading"  # Debe coincidir con tu configuración
TIME_BETWEEN_CHECKS = 900  # 15 minutos en segundos
DATA_DIR = "Informes" 
REINTENTOS_MAXIMOS = 6
TIEMPO_ESPERA_REINTENTO = 10


# Diccionario global para almacenar las fechas de cierre de vela
fechas_cierre_vela = {
    "15m": None,
    "1h": None,
    "4h": None,
    "1d": None,
}

def leer_informe_json(timeframe):
    """Lee un informe JSON."""
    archivo = os.path.join(DATA_DIR, f"report_{timeframe}.json")
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            informe = json.load(f)
            if not all(key in informe for key in ("timeframe", "indicators")):
                raise ValueError(f"El informe en {archivo} no tiene el formato esperado.")
            return informe
    except FileNotFoundError:
        print(f"Error: No se encontró el informe para {timeframe}.")
        return None
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error con el archivo {archivo}: {e}")
        return None
    except OSError as e:
        print(f"Error al leer el archivo {archivo}: {e}")
        return None

def archivos_actualizados(timeframe, fecha_cierre):
    """Verifica si el archivo del timeframe especificado está actualizado."""
    archivo = os.path.join(DATA_DIR, f"report_{timeframe}.json")
    if not os.path.exists(archivo):
        return False

    modificacion_time = os.path.getmtime(archivo)
    modificacion_datetime = datetime.fromtimestamp(modificacion_time)
    return modificacion_datetime >= fecha_cierre



def generar_analisis_texto(informe):
    """Genera un análisis textual a partir del informe."""
    if informe is None:
        return "No hay informe disponible para generar el análisis."

    timeframe = informe["timeframe"]
    indicators = informe["indicators"]
    price_action = informe.get("price_action_analysis",{}) #Manejo de la clave price_action_analysis que podria no existir en informes antiguos

    analisis = f"**Análisis Técnico - {timeframe}**\n\n"

  # Análisis del RSI--------------------------------------------------------
    rsi = indicators["RSI"]
    analisis += f"*   **RSI:** {rsi['message']}\n"

    if rsi["signal"] == "Sobrecompra":
        analisis += "    *   El RSI indica sobrecompra, lo que sugiere *precaución*. El precio muestra una fuerte presión compradora, pero podría entrar en una fase de consolidación o corrección *si otros indicadores lo confirman*.\n"
    elif rsi["signal"] == "Sobreventa":
        analisis += "    *   El RSI indica sobreventa, lo que sugiere *precaución*. El precio muestra una fuerte presión vendedora, pero podría experimentar un rebote *si otros indicadores lo confirman*.\n"
    elif rsi["signal"] == "Fuerte Alcista":
        analisis += "    *   El RSI se encuentra en zona alcista fuerte, mostrando un *fuerte impulso positivo* en el precio. Es importante monitorear otros indicadores para confirmar la continuación de la tendencia.\n"
    elif rsi["signal"] == "Fuerte Bajista":
        analisis += "    *   El RSI se encuentra en zona bajista fuerte, indicando una *fuerte presión vendedora*. Se recomienda prudencia y esperar confirmación de otros indicadores.\n"
    elif "Divergencia" in rsi["signal"]:
        tipo_divergencia = rsi["signal"].split(" ")[1]
        if "Oculta" in rsi["signal"]:
            analisis += f"    *   Se ha detectado una divergencia {tipo_divergencia} oculta. Este tipo de divergencia suele anticipar la continuación de la tendencia actual.\n"
        else:
            analisis += f"    *   Se ha detectado una divergencia {tipo_divergencia}. Las divergencias suelen ser señales de posibles cambios de tendencia. Es importante buscar confirmación con otros indicadores.\n"
        if "Sobrecompra" in rsi["signal"]:
            analisis += "    *   La divergencia se produce en zona de sobrecompra, lo que *aumenta la probabilidad* de una corrección.\n" #cambio de refuerza a aumenta la probabilidad
        elif "Sobreventa" in rsi["signal"]:
             analisis += "    *   La divergencia se produce en zona de sobreventa, lo que *aumenta la probabilidad* de un rebote.\n"#cambio de refuerza a aumenta la probabilidad
    elif rsi["signal"] == "Neutral":
        analisis += "    *   El RSI se encuentra en zona neutral, sin indicar una clara dirección en el corto plazo. Se recomienda esperar una mayor definición del mercado.\n"
    # Análisis del VWAP-------------------------------------------------------------------
    if "VWAP" in indicators: #Comprobamos que exista la clave VWAP
        vwap = indicators["VWAP"]
        analisis += f"*   **VWAP (Precio Promedio Ponderado por Volumen):** {vwap['message']}\n"

        # Explicación del VWAP (solo la primera vez que se encuentra)
        
        if vwap["signal"] == "Alcista":
            analisis += "    *   El precio se mantiene por encima del VWAP, sugiriendo una posible continuación de la tendencia alcista intradía.\n"
        elif vwap["signal"] == "Bajista":
            analisis += "    *   El precio se mantiene por debajo del VWAP, sugiriendo una posible continuación de la tendencia bajista intradía.\n"
        elif vwap["signal"] == "En VWAP":
            analisis += "    * El precio se encuentra en el VWAP, lo que indica un equilibrio entre compradores y vendedores en este momento.\n"
        #Interpretacion de la distancia porcentual
        distancia = float(vwap["message"].split("Distancia al VWAP: ")[1].split("%")[0]) if "Distancia al VWAP:" in vwap["message"] else None
        if distancia is not None:
             if abs(distancia) >= 1.5:
                 analisis += f"    *   La distancia al VWAP es del {distancia:.2f}%, lo cual se considera una desviación significativa. Esto podría indicar un posible retroceso hacia el VWAP o una consolidación.\n"
             elif abs(distancia) >0 and abs(distancia) < 1.5:
                analisis += f"    * La distancia al VWAP es del {distancia:.2f}%, lo cual se considera una desviación normal. El precio se mueve dentro de rangos esperados con respecto al VWAP.\n"
    else:
        analisis += "*   **VWAP (Precio Promedio Ponderado por Volumen):** No hay datos disponibles para el VWAP en este informe.\n"
    # Análisis del ATR-----------------------------------------------------------------------------
    if "ATR" in indicators: #Comprobamos que exista la clave ATR
        atr = indicators["ATR"]
        analisis += f"*   **ATR (Rango Promedio Verdadero):** {atr['message']}\n"

        if "aumentando" in atr["message"]:
            analisis += "    *   La volatilidad está aumentando, lo que sugiere que los movimientos de precio serán más amplios. Esto podría generar oportunidades de trading a corto plazo, pero también implica mayor riesgo.\n"
        elif "disminuyendo" in atr["message"]:
            analisis += "    *   La volatilidad está disminuyendo, lo que sugiere que los movimientos de precio serán más contenidos. Esto podría indicar un periodo de consolidación o un menor interés del mercado.\n"
        elif "fluctuaciones" in atr["message"]:
            analisis += "    *   La volatilidad ha mostrado fluctuaciones, lo que indica inestabilidad en el precio. Se recomienda precaución y una gestión adecuada del riesgo.\n"
        #Interpretacion del porcentaje de fluctuacion
        porcentaje_fluctuacion = float(atr["message"].split("Con una fluctuación promedio de ")[1].split("%")[0]) if "Con una fluctuación promedio de " in atr["message"] else None
        if porcentaje_fluctuacion is not None:
             if porcentaje_fluctuacion >= 2:
                 analisis += f"    *   La fluctuación promedio del {porcentaje_fluctuacion:.2f}% por periodo se considera alta, lo que implica un riesgo elevado.\n"
             elif porcentaje_fluctuacion > 0 and porcentaje_fluctuacion < 2:
                analisis += f"    * La fluctuación promedio del {porcentaje_fluctuacion:.2f}% por periodo se considera moderada.\n"
    else:
        analisis += "*   **ATR (Rango Promedio Verdadero):** No hay datos disponibles para el ATR en este informe.\n"

    # Análisis de la HULLMA-------------------------------------------------------------------------------------------------------
    if "HULLMA" in indicators: #Comprobamos que exista la clave HULLMA
        hullma = indicators["HULLMA"]
        analisis += f"*   **HULLMA (Media Móvil de Hull):** {hullma['message']}\n"

        
        if "Cruce alcista" in hullma["message"]:
            analisis += "    *   Se ha producido un cruce alcista, lo que sugiere una posible entrada en largo (compra). Se recomienda considerar el último mínimo relevante para colocar un stop-loss por debajo de este.\n"
            if "aceleración alcista" in hullma["message"]:
                 analisis += "    *   Este cruce alcista se produce con una aceleración alcista de la HULLMA, lo que refuerza la señal de compra y sugiere un fuerte impulso alcista.\n"
        elif "Cruce bajista" in hullma["message"]:
            analisis += "    *   Se ha producido un cruce bajista, lo que sugiere una posible entrada en corto (venta). Se recomienda considerar el último máximo relevante para colocar un stop-loss por encima de este, o considerar una toma de beneficios parcial o total, ya que el precio podría comenzar a retroceder.\n"
            if "aceleración bajista" in hullma["message"]:
                 analisis += "    *   Este cruce bajista se produce con una aceleración bajista de la HULLMA, lo que refuerza la señal de venta y sugiere un fuerte impulso bajista.\n"
        elif "por encima" in hullma["message"]:
            analisis += "    *   El precio se encuentra por encima de la HULLMA, lo que sugiere una posible tendencia alcista en curso. Se recomienda buscar confirmación con otros indicadores.\n"
        elif "por debajo" in hullma["message"]:
            analisis += "    *   El precio se encuentra por debajo de la HULLMA, lo que sugiere una posible tendencia bajista en curso. Se recomienda buscar confirmación con otros indicadores.\n"
        if "aceleración alcista" in hullma["message"] and "Cruce alcista" not in hullma["message"]:
            analisis += "    * La HULLMA muestra aceleración alcista sin cruce, lo que sugiere que la tendencia alcista podria continuar.\n"
        elif "aceleración bajista" in hullma["message"] and "Cruce bajista" not in hullma["message"]:
            analisis += "    * La HULLMA muestra aceleración bajista sin cruce, lo que sugiere que la tendencia bajista podria continuar.\n"
    else:
        analisis += "*   **HULLMA (Media Móvil de Hull):** No hay datos disponibles para la HULLMA en este informe.\n"
    # Análisis de las Bandas de Bollinger----------------------------------------
    if "Bollinger" in indicators: #Comprobamos que exista la clave Bollinger
        bollinger = indicators["Bollinger"]
        analisis += f"*   **Bandas de Bollinger:** {bollinger['message']}\n"


        if "Precio en o por encima de la Banda Superior" in bollinger["message"]:
            analisis += "    *   El precio ha alcanzado o superado la Banda Superior. Esto sugiere que el activo está relativamente 'caro' y podría experimentar un retroceso, pero en mercados volátiles, podría indicar también un fuerte impulso alcista. Se recomienda buscar confirmación con otros indicadores.\n"
        elif "Precio en o por debajo de la Banda Inferior" in bollinger["message"]:
            analisis += "    *   El precio ha alcanzado o caído por debajo de la Banda Inferior. Esto sugiere que el activo está relativamente 'barato' y podría experimentar un rebote, pero en mercados volátiles, podría indicar también un fuerte impulso bajista. Se recomienda buscar confirmación con otros indicadores.\n"
        elif "Precio por encima de la Banda Media" in bollinger["message"]:
            analisis += "    *   El precio se encuentra por encima de la Banda Media. Esto sugiere una posible tendencia alcista en curso, pero se necesita confirmación con otros indicadores.\n"
        elif "Precio por debajo de la Banda Media" in bollinger["message"]:
            analisis += "    *   El precio se encuentra por debajo de la Banda Media. Esto sugiere una posible tendencia bajista en curso, pero se necesita confirmación con otros indicadores.\n"

        if "Posible Squeeze detectado" in bollinger["message"]:
            analisis += "    *   Se ha detectado un posible Squeeze de Bollinger. Este patrón de baja volatilidad a menudo precede a movimientos de precio significativos. Esté atento a posibles rupturas.\n"
        if "Volatilidad en aumento" in bollinger["message"]:
            analisis += "    * La volatilidad esta en aumento, lo que implica mayor rango de fluctuacion del precio.\n"
        if "Probando soporte" in bollinger["message"]:
            analisis += "    * El precio esta probando el soporte de la banda inferior.\n"
        if "Probando resistencia" in bollinger["message"]:
            analisis += "    * El precio esta probando la resistencia de la banda superior.\n"
        if "Ruptura confirmada al alza" in bollinger["message"]:
            analisis += "    * Se ha confirmado una ruptura al alza de la banda superior.\n"
        if "Ruptura confirmada a la baja" in bollinger["message"]:
            analisis += "    * Se ha confirmado una ruptura a la baja de la banda inferior.\n"
        if "Divergencia: precio sube, banda superior no se expande" in bollinger["message"]:
            analisis += "    * Se observa una divergencia: el precio está subiendo, pero la Banda Superior no se expande proporcionalmente. Esto podría indicar una debilidad en el impulso alcista.\n"
        if "Divergencia: precio baja, banda inferior no se contrae" in bollinger["message"]:
            analisis += "    * Se observa una divergencia: el precio está bajando, pero la Banda Inferior no se contrae proporcionalmente. Esto podría indicar una debilidad en el impulso bajista.\n"
    else:
        analisis += "*   **Bandas de Bollinger:** No hay datos disponibles para las Bandas de Bollinger en este informe.\n"
    # Análisis del MACD------------------------------------------------------------------------------------------------------------------
    if "MACD" in indicators: #Comprobamos que exista la clave MACD
        macd = indicators["MACD"]
        analisis += f"*   **MACD (Convergencia/Divergencia de Medias Móviles):** {macd['message']}\n"

       
        if "Cruce Alcista" in macd["message"]:
            analisis += "    *   Se ha producido un cruce alcista del MACD (la línea MACD cruza por encima de la línea de Señal), lo que sugiere una posible señal de compra. Es importante buscar confirmación con otros indicadores.\n"
            macd_value = float(macd["message"].split("MACD (")[1].split(")")[0])
            signal_value = float(macd["message"].split("señal (")[1].split(")")[0])
            analisis += f"    *   MACD: {macd_value:.2f}, Señal: {signal_value:.2f}\n"
        elif "Cruce Bajista" in macd["message"]:
            analisis += "    *   Se ha producido un cruce bajista del MACD (la línea MACD cruza por debajo de la línea de Señal), lo que sugiere una posible señal de venta. Es importante buscar confirmación con otros indicadores.\n"
            macd_value = float(macd["message"].split("MACD (")[1].split(")")[0])
            signal_value = float(macd["message"].split("señal (")[1].split(")")[0])
            analisis += f"    *   MACD: {macd_value:.2f}, Señal: {signal_value:.2f}\n"

        if "Histograma MACD positivo" in macd["message"]:
            analisis += "    *   El histograma del MACD es positivo, lo que indica una posible tendencia alcista. Cuanto mayor sea el valor del histograma, mayor será la fuerza del impulso alcista.\n"
            histogram_value = float(macd["message"].split("positivo (")[1].split(")")[0])
            analisis += f"    *   Histograma: {histogram_value:.2f}\n"
        elif "Histograma MACD negativo" in macd["message"]:
            analisis += "    *   El histograma del MACD es negativo, lo que indica una posible tendencia bajista. Cuanto mayor sea el valor absoluto del histograma, mayor será la fuerza del impulso bajista.\n"
            histogram_value = float(macd["message"].split("negativo (")[1].split(")")[0])
            analisis += f"    *   Histograma: {histogram_value:.2f}\n"
        elif "Histograma en cero" in macd["message"]:
            analisis += "    *   El histograma del MACD está en cero, lo que indica una falta de impulso claro y una posible consolidación.\n"
            histogram_value = float(macd["message"].split("cero (")[1].split(")")[0])
            analisis += f"    *   Histograma: {histogram_value:.2f}\n"
        elif "Se necesitan al menos dos periodos" in macd["message"]:
            analisis += "    * No hay datos suficientes para calcular el MACD.\n"
    else:
        analisis += "*   **MACD (Convergencia/Divergencia de Medias Móviles):** No hay datos disponibles para el MACD en este informe.\n"

    # Análisis de la Acción del Precio--------------------------------------------------------------------------------------------------------------------
    if "Price Action" in indicators:
        price_action = indicators["Price Action"]
        if price_action["mensaje"] == "Datos insuficientes.":
            analisis += "*   **Acción del Precio:** Datos insuficientes para realizar un análisis de Price Action.\n"
        else:
            analisis += "**Análisis de la Acción del Precio:**\n"


            if price_action["patrones"]:
                analisis += "    *   **Patrones Chartistas Detectados:**\n"
                for patron in price_action["patrones"]:
                    analisis += f"        *   {patron}\n"
                    #Añadir explicaciones de los patrones
                    if patron == "Tendencia alcista detectada.":
                        analisis += "            *   Se caracteriza por una serie de máximos y mínimos ascendentes.\n"
                    elif patron == "Tendencia bajista detectada.":
                        analisis += "            *   Se caracteriza por una serie de máximos y mínimos descendentes.\n"
                    elif patron == "Triángulo simétrico detectado.":
                        analisis += "            *   Se forma por dos líneas de tendencia convergentes. Indica un periodo de consolidación antes de una posible ruptura en cualquier dirección.\n"
                    elif patron == "Triángulo ascendente detectado.":
                        analisis += "            *   Se forma por una línea de tendencia superior horizontal (resistencia) y una línea de tendencia inferior ascendente. Suele ser una figura alcista.\n"
                    elif patron == "Triángulo descendente detectado.":
                        analisis += "            *   Se forma por una línea de tendencia superior descendente y una línea de tendencia inferior horizontal (soporte). Suele ser una figura bajista.\n"
                    elif patron == "Consolidación lateral detectada.":
                        analisis += "            *   El precio se mueve dentro de un rango horizontal definido por niveles de soporte y resistencia. Indica un equilibrio entre compradores y vendedores.\n"
                    elif patron == "Doble techo detectado.":
                        analisis += "            *   Se forma cuando el precio alcanza dos máximos aproximadamente al mismo nivel, indicando una posible reversión bajista.\n"
                    elif patron == "Doble suelo detectado.":
                        analisis += "            *   Se forma cuando el precio alcanza dos mínimos aproximadamente al mismo nivel, indicando una posible reversión alcista.\n"
            else:
                analisis += "    * No se han detectado patrones chartistas.\n"

            # Análisis de Máximos y Mínimos (Solo valores y enfoque en zonas de interés)
            if price_action["maximos"] and price_action["minimos"]:
                analisis += "    *   **Posibles Zonas de Interés (Máximos y Mínimos Relevantes):**\n"
                maximos = sorted(price_action["maximos"], key=lambda x: x["valor"], reverse=True) #Ordenamos los maximos de mayor a menor
                minimos = sorted(price_action["minimos"], key=lambda x: x["valor"]) #Ordenamos los minimos de menor a mayor

                analisis += "        *   **Máximos (Posibles Resistencias/Áreas de Venta):**\n"
                for maximo in maximos:
                    analisis += f"            *   {maximo['valor']}\n"

                analisis += "        *   **Mínimos (Posibles Soportes/Áreas de Compra):**\n"
                for minimo in minimos:
                    analisis += f"            *   {minimo['valor']}\n"
            elif price_action["maximos"]:
                analisis += "    *   **Posibles Zonas de Interés (Máximos Relevantes/Áreas de Venta):**\n"
                maximos = sorted(price_action["maximos"], key=lambda x: x["valor"], reverse=True) #Ordenamos los maximos de mayor a menor
                for maximo in maximos:
                    analisis += f"            *   {maximo['valor']}\n"
            elif price_action["minimos"]:
                analisis += "    *   **Posibles Zonas de Interés (Mínimos Relevantes/Áreas de Compra):**\n"
                minimos = sorted(price_action["minimos"], key=lambda x: x["valor"]) #Ordenamos los minimos de menor a mayor
                for minimo in minimos:
                    analisis += f"            *   {minimo['valor']}\n"
            else:
                analisis += "    * No se han detectado máximos ni mínimos relevantes.\n"
    else:
        analisis += "*   **Acción del Precio:** No hay datos disponibles para el análisis de Price Action en este informe.\n"
     #-----------------------------------------------------------------------------------------------
    analisis += "\n**Conclusión:**\n"
    # Lógica de conclusión (ejemplo básico)
  # Sección de Conclusiones
    conclusiones = []
    momento_conclusiones = []
    if "RSI" in indicators and "Bollinger" in indicators:
        rsi = indicators["RSI"]
        bollinger = indicators["Bollinger"]
        if "Sobrecompra" in rsi["signal"] and "Precio en o por encima de la Banda Superior" in bollinger["message"]:
            momento_conclusiones.append("Alta probabilidad de corrección bajista debido a RSI en sobrecompra y precio cerca de la Banda Superior de Bollinger.")
        elif "Sobrecompra" in rsi["signal"]:
            momento_conclusiones.append("RSI en sobrecompra sugiere posible presión vendedora.")
        elif "Precio en o por encima de la Banda Superior" in bollinger["message"]:
            momento_conclusiones.append("El precio cerca de la Banda Superior de Bollinger indica posible presión vendedora.")
        elif "Sobreventa" in rsi["signal"] and "Precio en o por debajo de la Banda Inferior" in bollinger["message"]:
            momento_conclusiones.append("Alta probabilidad de rebote alcista debido a RSI en sobreventa y precio cerca de la Banda Inferior de Bollinger.")
        elif "Sobreventa" in rsi["signal"]:
            momento_conclusiones.append("RSI en sobreventa sugiere posible presión compradora.")
        elif "Precio en o por debajo de la Banda Inferior" in bollinger["message"]:
            momento_conclusiones.append("El precio cerca de la Banda Inferior de Bollinger indica posible presión compradora.")
    if momento_conclusiones:
        conclusiones.append("**Análisis de Momento:** " + " ".join(momento_conclusiones) + "\n")

    # Análisis de Tendencia
    tendencia_conclusiones = []
    if "MACD" in indicators and "HULLMA" in indicators:
        macd = indicators["MACD"]
        hullma = indicators["HULLMA"]
        if "Cruce Alcista" in macd["message"] and "Cruce alcista" in hullma["message"]:
            tendencia_conclusiones.append("Confirmación de tendencia alcista por MACD y HULLMA. Considera oportunidades de compra.")
        elif "Cruce Alcista" in macd["message"]:
            tendencia_conclusiones.append("MACD sugiere un posible inicio de tendencia alcista.")
        elif "Cruce alcista" in hullma["message"]:
            tendencia_conclusiones.append("HULLMA indica un posible inicio de tendencia alcista.")
        elif "Cruce Bajista" in macd["message"] and "Cruce bajista" in hullma["message"]:
            tendencia_conclusiones.append("Confirmación de tendencia bajista por MACD y HULLMA. Considera cerrar posiciones largas o abrir cortas.")
        elif "Cruce Bajista" in macd["message"]:
            tendencia_conclusiones.append("MACD sugiere un posible inicio de tendencia bajista.")
        elif "Cruce bajista" in hullma["message"]:
            tendencia_conclusiones.append("HULLMA indica un posible inicio de tendencia bajista.")
    if tendencia_conclusiones:
        conclusiones.append("**Análisis de Tendencia:** " + " ".join(tendencia_conclusiones) + "\n")

    # Análisis de Volatilidad
    volatilidad_conclusiones = []
    if "ATR" in indicators and "Bollinger" in indicators:
        atr = indicators["ATR"]
        bollinger = indicators["Bollinger"]
        if "Posible Squeeze detectado" in bollinger["message"]:
            volatilidad_conclusiones.append("Se anticipa un aumento significativo de volatilidad debido a un posible Squeeze de Bollinger.")
        elif "Volatilidad en aumento" in bollinger["message"] or "aumentando" in atr["message"]:
            volatilidad_conclusiones.append("Aumento de volatilidad detectado. Prepárate para movimientos rápidos en ambas direcciones.")
        elif "disminuyendo" in atr["message"]:
            volatilidad_conclusiones.append("Volatilidad disminuyendo. Es probable que el mercado se mueva en un rango estrecho.")
    if volatilidad_conclusiones:
        conclusiones.append("**Análisis de Volatilidad:** " + " ".join(volatilidad_conclusiones) + "\n")

    # Análisis de Acción del Precio
    price_action_conclusiones = []
    if "Price Action" in indicators:
        price_action = indicators["Price Action"]
        if price_action["patrones"]:
            price_action_conclusiones.append("Patrones chartistas detectados. Evalúa la dirección para anticipar movimientos futuros.")
        if price_action["maximos"] and price_action["minimos"]:
            price_action_conclusiones.append("Se han identificado niveles clave de soporte y resistencia. Úsalos para planificar entradas y salidas.")
    if price_action_conclusiones:
        conclusiones.append("**Análisis de Acción del Precio:** " + " ".join(price_action_conclusiones) + "\n")

    if conclusiones:
        analisis += "\n**Conclusiones Generales:**\n" + "".join(conclusiones)
        analisis += "\nBasado en el análisis, ajusta tu estrategia, esperamos sea de ayuda."
    else:
        analisis += "\n**Conclusiones Generales:** Los indicadores no ofrecen señales claras en este momento. Mantén precaución y espera confirmaciones adicionales antes de operar."

    return analisis


def guardar_informe(timeframe, analisis_markdown):
    """Guarda el análisis directamente en formato Markdown."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    archivo = os.path.join(OUTPUT_DIR, f"report_{timeframe}.md") # Guarda con extensión .md
    with open(archivo, "w", encoding="utf-8") as f:
        f.write(analisis_markdown) # Escribe directamente el string Markdown

def analizar_temporalidad(timeframe):
    """Analiza una temporalidad y guarda el informe."""
    informe = leer_informe_json(timeframe)
    if informe:
        analisis_markdown = generar_analisis_texto(informe)
        guardar_informe(timeframe, analisis_markdown)


def calcular_fechas_cierre(ahora):
    fechas = {}
    # 15 minutos
    minutos_actuales = ahora.minute
    minutos_restantes_15m = 15 - (minutos_actuales % 15)
    fechas["15m"] = ahora + timedelta(minutes=minutos_restantes_15m)

    # 1 hora
    minutos_restantes_1h = 60 - minutos_actuales
    fechas["1h"] = ahora + timedelta(minutes=minutos_restantes_1h)

    # 4 horas
    hora_actual = ahora.hour
    horas_restantes_4h = 4 - (hora_actual % 4)
    fechas["4h"] = ahora + timedelta(hours=horas_restantes_4h)

    # 1 dia - Se calcula el cierre a las 00:00 del *siguiente* día
    fechas["1d"] = ahora.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return fechas

def main():
    fechas_cierre_vela = calcular_fechas_cierre(datetime.now()) # Inicialización al principio

    while True:
        tiempo_inicio_ciclo = datetime.now()

        if tiempo_inicio_ciclo.day != fechas_cierre_vela["1d"].day:
            fechas_cierre_vela = calcular_fechas_cierre(tiempo_inicio_ciclo)
            print("Nuevo dia detectado, recalculando fechas de cierre de vela")
        else:
            fechas_cierre_vela = calcular_fechas_cierre(tiempo_inicio_ciclo)
            print("Mismo dia, recalculando fechas de cierre de vela")

        print(f"Iniciando ciclo de análisis: {tiempo_inicio_ciclo}")

        # Lógica de espera y reintento *solo para 15 minutos*
        timeframe_15m = "15m"
        tiempo_maximo_esperado_15m = fechas_cierre_vela[timeframe_15m]
        print(f"Verificando {timeframe_15m}. Fecha de cierre de vela: {tiempo_maximo_esperado_15m}")

        reintentos_15m = 0
        while reintentos_15m < REINTENTOS_MAXIMOS:
            if archivos_actualizados(timeframe_15m, tiempo_maximo_esperado_15m):
                print(f"Archivo de {timeframe_15m} actualizado.")
                analizar_temporalidad(timeframe_15m)
                break
            else:
                reintentos_15m += 1
                print(f"Esperando actualización del informe de {timeframe_15m} (intento {reintentos_15m}/{REINTENTOS_MAXIMOS})...")
                time.sleep(TIEMPO_ESPERA_REINTENTO)

        else:
            print(f"Fallo al actualizar el informe de {timeframe_15m} después de {REINTENTOS_MAXIMOS} intentos. Omitiendo análisis de este ciclo.")
            continue

        # Verificación individual para las *demás* temporalidades (sin reintentos)
        for timeframe in ("1h", "4h", "1d"):
            tiempo_maximo_esperado = fechas_cierre_vela[timeframe]
            print(f"Verificando {timeframe}. Fecha de cierre de vela: {tiempo_maximo_esperado}")
            if archivos_actualizados(timeframe, tiempo_maximo_esperado):
                print(f"Archivo de {timeframe} actualizado.")
                analizar_temporalidad(timeframe)
            else:
                print(f"Archivo de {timeframe} no actualizado. Omitiendo análisis de {timeframe} en este ciclo.")

        tiempo_fin_ciclo = datetime.now()
        tiempo_transcurrido = tiempo_fin_ciclo - tiempo_inicio_ciclo

        # Espera *entre ciclos* (se mantiene)
        minutos_actuales = tiempo_inicio_ciclo.minute
        minutos_restantes_15m = 15 - (minutos_actuales % 15)
        tiempo_espera = (minutos_restantes_15m * 60) - tiempo_transcurrido.total_seconds()

        if tiempo_espera > 0:
            print(f"Esperando {tiempo_espera:.0f} segundos hasta el próximo ciclo...")
            time.sleep(tiempo_espera)
        else:
            print("El analisis tardo mas de 15 minutos. Iniciando ciclo inmediatamente...")

if __name__ == "__main__":
    main()
