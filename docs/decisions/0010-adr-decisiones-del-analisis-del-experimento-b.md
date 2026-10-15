# 0010. El criterio D16 pasa a la diferencia pareada, y el juez se verifica por etiqueta con una corrida por pregunta

## Estado

Aceptada (2026-10-15). Enmienda el criterio D16 de la metodología (versión 2.0, 2026-10-13).

## Contexto

El código de análisis del Experimento B (`afg.experiments.analysis`, `afg.evaluation.judge_human_check` y los comandos `afg experiment b-report`, `b-sample` y `b-human-check`) dejó cuatro decisiones metodológicas con un valor provisional ([issue #101](https://github.com/jasonssdev/mcd-afg/issues/101)). Las cuatro se deciden **antes de correr cualquier evaluación**: a esta fecha no existe ninguna corrida de evaluación ni ningún dato de las series de evaluación, solo la corrida de humo con C1 sobre ES2015, que es una serie de desarrollo (ADR 0005). Ningún resultado pudo influir en estas decisiones.

Una de ellas toca algo prerregistrado. El criterio de éxito del proyecto (D16) se fijó el 2026-10-13 con esta redacción:

> «La hipótesis del proyecto se considera respaldada si el intervalo bootstrap del 95 % de C2 queda por encima del de C1 sin solaparse; si los intervalos se solapan, el resultado se reporta como no concluyente y nunca como éxito.»

La frase no dice si los intervalos son independientes por condición o pareados, ni cómo se combinan las tres corridas por pregunta. La implementación provisional usó la lectura literal: un intervalo por condición, promedio de corridas por pregunta y remuestreo de preguntas. Eso es lo que se decide ahora, porque la lectura literal tiene una consecuencia que la redacción no anticipaba.

## Decisión

1. **Juez, decisión por etiqueta.** La corrección de respuesta (`correct`) decide si el juicio automático de la métrica principal se mantiene: si su kappa con las personas no alcanza 0,70, esa métrica se reporta solo con evaluación humana. El soporte de evidencia (`evidence_supported`) tiene su propia marca de confiable o no confiable con el mismo umbral; si no lo alcanza, esa métrica se reporta solo con evaluación humana o marcada como no confiable. No decide sobre la métrica principal.
2. **Kappa indefinido.** Un kappa que no puede calcularse (juez y personas usan una sola clase) **sigue contando como «no cumple»**. Siempre se informan, junto al kappa, el **acuerdo observado** y la **prevalencia** (la fracción de «sí» del juez y de las personas).
3. **Criterio D16 (enmienda).** El criterio principal es que el intervalo bootstrap del 95 % de la **diferencia pareada C2 − C1** en la corrección de respuesta de E3 quede **por encima de 0**. La diferencia se calcula pregunta por pregunta, tras promediar las corridas de cada pregunta, y el bootstrap remuestrea preguntas. La **no superposición** de los intervalos independientes de C2 y C1 (la redacción anterior) se conserva como cifra de **robustez**: se informa al lado del veredicto principal y no lo reemplaza. Si el intervalo incluye 0, el resultado sigue siendo no concluyente y nunca un éxito.
4. **Muestra humana.** Se toma **una corrida sorteada por cada pregunta y condición**. Su tamaño por condición y estrato es el 20 % de las respuestas juzgadas (redondeado hacia arriba), con tope en los pares pregunta-condición disponibles. Sigue estratificada por condición y estrato, con semilla fija.

## Evidencia

### D16: simulación de potencia (notebook 10)

La decisión 3 se apoya en una simulación con datos sintéticos, versionada en `afg.experiments.power`, con pruebas, y explicada en [`notebooks/10-jss-potencia-criterio-d16.ipynb`](../../notebooks/10-jss-potencia-criterio-d16.ipynb). No se corrió ningún experimento ni ningún modelo. Cada escenario simula 1.000 experimentos de `n` preguntas respondidas 3 veces por C1 y por C2, con una dificultad por pregunta compartida entre las dos condiciones, y aplica los dos criterios con la misma función de intervalos que usa el informe (`bootstrap_mean_interval`). La rejilla son 135 escenarios: n de 25, 40 y 50; exactitud base de C1 de 0,4, 0,5 y 0,6; diferencias verdaderas de 0, 0,10, 0,15, 0,20 y 0,30; tres dispersiones de la dificultad compartida (ninguna, moderada, marcada).

Cifras con el mínimo de E3 (n = 25), exactitud base de C1 = 0,5 y dificultad compartida moderada. Es el porcentaje de experimentos simulados en que cada criterio declara respaldada la hipótesis:

| Diferencia verdadera | No solapamiento (anterior) | Diferencia pareada (nuevo) |
|---|---|---|
| 0 (falso positivo) | 0,0 % | 3,3 % |
| +0,15 | 10,4 % | 57,5 % |
| +0,20 | 27,8 % | 79,5 % |
| +0,30 | 79,5 % | 98,3 % |

- **Falsos positivos.** En los 27 escenarios sin diferencia, el de no solapamiento queda entre 0 % y 0,8 % y el pareado entre 2,5 % y 4,5 %; ambos por debajo del 5 %.
- **Potencia.** El pareado supera al de no solapamiento en todos los escenarios con diferencia, en las tres exactitudes base, los tres tamaños y las tres dispersiones. Sin dificultad compartida (el caso menos favorable al pareado) sigue ganando: 50,3 % frente a 21,5 % con +0,15 y 75,4 % frente a 41,7 % con +0,20. Con dificultad marcada, 71,1 % frente a 2,5 % y 88,7 % frente a 12,6 %.
- **Por qué.** El de no solapamiento equivale a una prueba mucho más exigente que el 5 % (su falso positivo es casi 0), y arrastra en cada intervalo la variación por la dificultad de las preguntas, que C1 y C2 comparten.
- **Tamaño.** Con 25 preguntas ningún criterio llega al 80 % de potencia ante una mejora de 15 puntos. Con 40 preguntas el pareado llega a 75,7 % y 93,8 % (+0,15 y +0,20), y con 50 a 83,5 % y 97,2 %.

Límites: es un modelo (respuestas independientes dadas la dificultad de la pregunta); la dispersión de la dificultad no puede estimarse sin datos de evaluación, por eso se prueba un rango; la simulación usa 300 remuestreos por intervalo (el análisis real, 10.000) y cada cifra tiene un error de a lo más unos 1,6 puntos porcentuales.

### Decisiones 1, 2 y 4: razones de principio

No hay una simulación equivalente para estas tres; se apoyan en el diseño.

- **Etiqueta por etiqueta (1).** El criterio principal (D16) descansa en `correct`. Exigir el umbral en las dos etiquetas anularía la métrica principal por un desacuerdo en una métrica secundaria. La calibración del juez ya mostró que son etiquetas de dificultad distinta (kappa 1,00 en `correct` y 0,87 en `evidence_supported`, [notebook 05](../../notebooks/05-jss-seleccion-juez.ipynb)), de modo que tratarlas por separado refleja lo que se sabe. La marca de no confiable evita que `evidence_supported` se reporte como si estuviera validado cuando no lo está.
- **Kappa indefinido como «no cumple» (2).** Dar por válido un juez porque la muestra tiene una sola clase sería afirmar una confiabilidad que no se midió. La alternativa de tratarlo como acuerdo premiaría una muestra poco informativa. En cambio, informar siempre el acuerdo observado y la prevalencia deja ver los dos hechos que el kappa oculta en ese caso: que coincidieron en todo y que casi todo era de una misma clase.
- **Una corrida por pregunta y condición (4).** Las corridas de una pregunta son mediciones repetidas de un mismo ítem, y el análisis ya cuenta preguntas, no respuestas (`analysis.py`). Muestrear respuestas sueltas pondría varias veces la misma pregunta y dejaría preguntas sin ninguna, de modo que el acuerdo medido pesaría más en unas preguntas que en otras. Se conserva el 20 % de las respuestas juzgadas como tamaño para no reducir el volumen prerregistrado.

## Alternativas descartadas

- **Mantener la redacción literal de D16.** Casi nunca permite concluir con las 25 preguntas mínimas de E3 aunque la mejora sea real, según la simulación. Un criterio que no puede cumplirse con el diseño previsto no mide el éxito del proyecto.
- **Elegir el criterio después de ver los datos.** Es justamente lo que el prerregistro impide; por eso la enmienda se hace ahora, antes de cualquier evaluación.
- **Reemplazar el criterio sin conservar el anterior.** Se conserva la no superposición como robustez para que el informe muestre si las dos lecturas coinciden y para que el cambio no se pueda leer como una forma de obtener un resultado favorable.
- **Exigir el umbral en las dos etiquetas del juez, o tratar el kappa indefinido como acuerdo.** Véanse las razones de principio arriba.

## Consecuencias

- **D16 queda enmendado, no borrado.** La metodología pasa a la versión 3.4 con una fila de historial y deja visible la redacción superada; el [registro de decisiones](README.md) añade la fila D17 sin editar la D16. El criterio original sigue en el informe como `nonoverlap_criterion`.
- **El informe lleva los dos veredictos.** `criterion` es el veredicto principal (diferencia pareada); `nonoverlap_criterion` es la robustez. Si difieren, se reportan ambos. El primer resultado de la tesis se lee con el criterio pareado, y la robustez dice si la lectura estricta lo confirmaría.
- **Con 25 preguntas el diseño es justo.** Incluso el criterio pareado queda por debajo del 80 % de potencia ante una mejora verdadera de 15 puntos. Si el banco de E3 permite más preguntas, conviene usarlas. Un resultado no concluyente con 25 preguntas no demuestra que no haya mejora.
- **Código.** `analysis.py` calcula el veredicto principal con la diferencia pareada y conserva la no superposición; `judge_human_check.py` entrega un veredicto por etiqueta, la marca `evidence_supported_reliable`, el acuerdo observado y la prevalencia, y la muestra de una corrida por pregunta y condición; `power.py` y el notebook 10 reproducen la evidencia desde `config/experiments.toml` (sección `[power_simulation]`). Los comandos `b-report`, `b-sample` y `b-human-check` muestran el texto correspondiente.
- **Ninguna otra métrica cambia.** Los umbrales, las demás métricas secundarias y la regla de citación (ADR 0009) quedan como estaban.
