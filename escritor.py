import json
import os
from datetime import datetime

OUTPUT_DIR = "Informes"  # Debe coincidir con tu configuración

def leer_informe_json(timeframe):
    """Lee un informe JSON."""
    archivo = os.path.join(OUTPUT_DIR, f"report_{timeframe}.json")
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró el informe para {timeframe}.")
        return None
    except json.JSONDecodeError:
        print(f"Error: El archivo {archivo} no es un JSON válido.")
        return None

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
        if "explicacion_vwap" not in analisis: # usamos una variable temporal para que solo se imprima una vez la explicacion
            analisis += "    *   El VWAP representa el precio promedio al que se ha negociado un activo durante un período de tiempo, ponderado por el volumen. Se utiliza principalmente para identificar la dirección de la tendencia intradía y como nivel de soporte/resistencia dinámico.\n"
            analisis += "    *   Un precio por encima del VWAP sugiere una tendencia alcista intradía, mientras que un precio por debajo del VWAP sugiere una tendencia bajista intradía.\n"
            analisis += "    *   La *distancia porcentual al VWAP* indica cuánto se ha alejado el precio del promedio. Desviaciones significativas pueden indicar posibles reversiones o consolidaciones.\n"
            analisis += "    *   En el mercado de criptomonedas, el VWAP puede ser útil para traders intradía, pero su relevancia disminuye en timeframes mayores debido a la volatilidad y las tendencias más prolongadas.\n"
            analisis += "explicacion_vwap" # agregamos la variable para que no se vuelva a imprimir la explicacion

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

        # Explicación del ATR (solo la primera vez)
        if "explicacion_atr" not in analisis:
            analisis += "    *   El ATR mide la volatilidad del precio de un activo. Un ATR alto indica mayor volatilidad (mayores fluctuaciones de precio), mientras que un ATR bajo indica menor volatilidad (fluctuaciones de precio más pequeñas).\n"
            analisis += "    *   El ATR no predice la dirección del precio, solo la magnitud de los movimientos. Es útil para establecer stops de pérdida, dimensionar posiciones y anticipar posibles rupturas.\n"
            analisis += "explicacion_atr"

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

        # Explicación de la HULLMA (solo la primera vez)
        if "explicacion_hullma" not in analisis:
            analisis += "    *   La HULLMA es una media móvil diseñada para reducir el retraso (lag) que presentan otras medias móviles, ofreciendo señales más rápidas y precisas.\n"
            analisis += "    *   Un cruce del precio por encima de la HULLMA se interpreta como una señal alcista, mientras que un cruce por debajo se interpreta como una señal bajista.\n"
            analisis += "    *   La 'aceleración' de la HULLMA indica la fuerza del movimiento. Una aceleración alcista sugiere un fuerte impulso comprador, y una aceleración bajista sugiere un fuerte impulso vendedor.\n"
            analisis += "explicacion_hullma"

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

        # Explicación de las Bandas de Bollinger (solo la primera vez)
        if "explicacion_bollinger" not in analisis:
            analisis += "    *   Las Bandas de Bollinger consisten en una media móvil central, una banda superior (desviación estándar positiva) y una banda inferior (desviación estándar negativa).\n"
            analisis += "    *   Se utilizan para medir la volatilidad del mercado y para identificar posibles zonas de sobrecompra/sobreventa, aunque en mercados volátiles como las criptomonedas, estas señales deben interpretarse con cautela.\n"
            analisis += "    *   Cuando el precio toca o supera la Banda Superior, se considera que el activo está relativamente 'caro' (pero no necesariamente sobrecomprado). Cuando el precio toca o cae por debajo de la Banda Inferior, se considera que el activo está relativamente 'barato' (pero no necesariamente sobrevendido).\n"
            analisis += "    *   El 'Squeeze' de Bollinger ocurre cuando las bandas se estrechan, lo que indica un período de baja volatilidad que a menudo precede a un aumento de la volatilidad y un posible movimiento de precio significativo.\n"
            analisis += "explicacion_bollinger"

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

        # Explicación del MACD (solo la primera vez)
        if "explicacion_macd" not in analisis:
            analisis += "    *   El MACD se compone de:\n"
            analisis += "        *   **Línea MACD:** Diferencia entre dos medias móviles exponenciales (generalmente de 12 y 26 períodos).\n"
            analisis += "        *   **Línea de Señal:** Media móvil exponencial de la línea MACD (generalmente de 9 períodos).\n"
            analisis += "        *   **Histograma:** Diferencia entre la línea MACD y la línea de Señal.\n"
            analisis += "    *   Los cruces de la línea MACD por encima de la línea de Señal se interpretan como señales alcistas, y los cruces por debajo como señales bajistas.\n"
            analisis += "    *   El histograma indica la fuerza del impulso. Un histograma creciente (en valor absoluto) indica un fortalecimiento de la tendencia, mientras que un histograma decreciente indica un debilitamiento.\n"
            analisis += "explicacion_macd"

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

            # Explicación general de Price Action (solo la primera vez)
            if "explicacion_price_action" not in analisis:
                analisis += "    *   El análisis de la Acción del Precio se centra en el estudio de los movimientos del precio en un gráfico, buscando patrones y formaciones que puedan predecir futuros movimientos.\n"
                analisis += "    *   Se basa en la premisa de que toda la información relevante está reflejada en el precio y que el estudio de este puede proporcionar señales de trading.\n"
                analisis += "explicacion_price_action"

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

    # 1. Momento (Sobrecompra/Sobreventa)
    momento_conclusiones = []
    if "RSI" in indicators and "Bollinger" in indicators:
        rsi = indicators["RSI"]
        bollinger = indicators["Bollinger"]
        if "Sobrecompra" in rsi["signal"] and "Precio en o por encima de la Banda Superior" in bollinger["message"]:
            momento_conclusiones.append("Fuerte presión vendedora detectada por RSI y Bandas de Bollinger.")
        elif "Sobrecompra" in rsi["signal"]:
            momento_conclusiones.append("Presión vendedora detectada por RSI.")
        elif "Precio en o por encima de la Banda Superior" in bollinger["message"]:
            momento_conclusiones.append("Posible presión vendedora al alcanzar la Banda Superior de Bollinger.")
        if "Sobreventa" in rsi["signal"] and "Precio en o por debajo de la Banda Inferior" in bollinger["message"]:
            momento_conclusiones.append("Fuerte presión compradora detectada por RSI y Bandas de Bollinger.")
        elif "Sobreventa" in rsi["signal"]:
            momento_conclusiones.append("Presión compradora detectada por RSI.")
        elif "Precio en o por debajo de la Banda Inferior" in bollinger["message"]:
            momento_conclusiones.append("Posible presión compradora al alcanzar la Banda Inferior de Bollinger.")
    if momento_conclusiones:
        conclusiones.append("**Análisis de Momento:** " + " ".join(momento_conclusiones) + "\n")

    # 2. Tendencia
    tendencia_conclusiones = []
    if "MACD" in indicators and "HULLMA" in indicators:
        macd = indicators["MACD"]
        hullma = indicators["HULLMA"]
        if "Cruce Alcista" in macd["message"] and "Cruce alcista" in hullma["message"]:
            tendencia_conclusiones.append("Fuerte señal de tendencia alcista confirmada por MACD y HULLMA.")
        elif "Cruce Alcista" in macd["message"]:
            tendencia_conclusiones.append("Posible inicio de tendencia alcista según el MACD.")
        elif "Cruce alcista" in hullma["message"]:
            tendencia_conclusiones.append("Posible inicio de tendencia alcista según la HULLMA.")
        if "Cruce Bajista" in macd["message"] and "Cruce bajista" in hullma["message"]:
            tendencia_conclusiones.append("Fuerte señal de tendencia bajista confirmada por MACD y HULLMA.")
        elif "Cruce Bajista" in macd["message"]:
            tendencia_conclusiones.append("Posible inicio de tendencia bajista según el MACD.")
        elif "Cruce bajista" in hullma["message"]:
            tendencia_conclusiones.append("Posible inicio de tendencia bajista según la HULLMA.")

    if tendencia_conclusiones:
        conclusiones.append("**Análisis de Tendencia:** " + " ".join(tendencia_conclusiones) + "\n")

    # 3. Volatilidad
    volatilidad_conclusiones = []
    if "ATR" in indicators and "Bollinger" in indicators:
        atr = indicators["ATR"]
        bollinger = indicators["Bollinger"]
        if "Posible Squeeze detectado" in bollinger["message"]:
            volatilidad_conclusiones.append("Se ha detectado un posible Squeeze de Bollinger, lo que anticipa un aumento de la volatilidad.")
        if "Volatilidad en aumento" in bollinger["message"]:
            volatilidad_conclusiones.append("La volatilidad está en aumento según las Bandas de Bollinger.")
        if "aumentando" in atr["message"]:
            volatilidad_conclusiones.append("La volatilidad está aumentando según el ATR.")
        elif "disminuyendo" in atr["message"]:
            volatilidad_conclusiones.append("La volatilidad está disminuyendo según el ATR.")
        if volatilidad_conclusiones:
            conclusiones.append("**Análisis de Volatilidad:** " + " ".join(volatilidad_conclusiones) + "\n")
    # 4. Accion del precio
    price_action_conclusiones = []
    if "Price Action" in indicators:
        price_action = indicators["Price Action"]
        if price_action["patrones"]:
            price_action_conclusiones.append("Se han detectado patrones chartistas que pueden indicar posibles cambios en la tendencia o continuación de la misma.")
        if price_action["maximos"] and price_action["minimos"]:
            price_action_conclusiones.append("Se han identificado niveles de precios relevantes que podrían actuar como soporte o resistencia.")
    if price_action_conclusiones:
        conclusiones.append("**Análisis de Acción del Precio:** " + " ".join(price_action_conclusiones) + "\n")

    if conclusiones:
        analisis += "\n**Conclusiones Generales:**\n" + "".join(conclusiones)
    else:
        analisis += "\n**Conclusiones Generales:** Los indicadores no ofrecen una señal clara en este momento.\n"

    return analisis

def main():
    timeframes = ["15m", "1h", "4h", "1d"]
    for timeframe in timeframes:
        informe = leer_informe_json(timeframe)
        if informe:
            analisis = generar_analisis_texto(informe)
            print(analisis)
            print("-" * 50)  # Separador entre análisis

if __name__ == "__main__":
    main()
