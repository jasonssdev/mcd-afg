# Conclusiones del proyecto

| | |
|---|---|
| **Documento** | 13 — Conclusiones del proyecto |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.1 |
| **Fecha** | 2026-11-09 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-11-07 | Versión inicial. Reúne en un solo lugar la respuesta a los cuatro objetivos específicos y a las hipótesis, el costo, lo que los resultados significan, sus límites y el trabajo futuro. | Los dos experimentos formales, las verificaciones humanas y el análisis final quedaron completos (issue #294, épica #288) y el [notebook 31](../../notebooks/31-jss-resultados-finales.ipynb) reúne las cifras; ningún documento contrastaba aún los resultados con los objetivos y las hipótesis. |
| 1.1 | 2026-11-09 | La sección 5 identifica la máquina en que se midieron los tiempos (MacBook Pro de 16 pulgadas de 2024, Apple M4 Pro, 48 GB de memoria unificada, macOS 27), registrada también en `config/experiments.toml` (`[execution_hardware]`). Sin cambios de cifras. | Los tiempos de pared no se pueden interpretar ni reproducir sin conocer el equipo; la revisión del pre-informe 02 para lectura externa detectó la omisión. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

> **Alcance.** Este documento no presenta resultados nuevos: contrasta los ya reportados con
> los objetivos y las hipótesis del [documento 03](03-jss-objetivos.md). Los detalles están en
> el [documento 10](10-jss-confiabilidad-de-la-referencia.md) (OE1), el
> [documento 11](11-jss-resultados-experimento-a.md) (OE2) y el
> [documento 12](12-jss-resultados-experimento-b.md) (OE3 y OE4). Las series son de
> **evaluación**: se muestran identificadores, etiquetas y cifras agregadas, nunca texto de
> respuestas, de decisiones ni de transcripciones ([ADR 0005](../decisions/0005-adr-development-evaluation-split.md)).
> Cada cifra remite al [notebook 31](../../notebooks/31-jss-resultados-finales.ipynb) (sección
> indicada entre paréntesis), que a su vez lee las salidas de los notebooks
> [28](../../notebooks/28-jss-experimento-a.ipynb), [29](../../notebooks/29-jss-anotacion-f3-referencia.ipynb)
> y [30](../../notebooks/30-jss-experimento-b.ipynb) y las tablas `reports/tables/final-*`.

## En una página

- **La pregunta.** Las reuniones quedan transcritas, pero las decisiones y sus cambios quedan
  enterrados en el texto. ¿Conviene que un sistema construya una base de decisiones a partir de
  las transcripciones, en lugar de buscar fragmentos del texto cada vez que alguien pregunta?
- **Respuesta corta.** Con el modelo local pequeño que se usó, **todavía no**: la base construida
  automáticamente responde peor que buscar en el texto (corrección de **0,49 frente a 0,72** en el
  total). Pero la misma base, con las decisiones corregidas por personas, llega a **0,80**. La
  idea de la base de decisiones **funciona cuando las decisiones son buenas**; lo que falla es
  obtenerlas automáticamente con un modelo pequeño.
- **Dónde se pierde el dato.** La máquina encuentra cerca de **3 de cada 10** decisiones de la
  referencia humana (recall 0,308). Cuando la base responde mal en preguntas de un hecho puntual,
  la causa más frecuente es la extracción (**21 de 43** respuestas incorrectas, 48,8 %), no la
  consulta.
- **Hipótesis.** El criterio principal (D16) **no se respalda**, y la dirección es la contraria
  a la esperada. Dos hipótesis quedan no concluyentes (H2 y H3) y una no se puede evaluar con el
  juez automático (H4).
- **Costo.** Cada consulta a la base tarda unas **2,7 veces** lo que una consulta de búsqueda
  de texto (15,3 s frente a 5,7 s), y construir la base cuesta horas. Por eso **no existe punto de
  equilibrio**: la base nunca se vuelve más barata por consulta.
- **Alcance.** Un solo modelo local pequeño (qwen3:8b), una corrida formal por experimento, once
  series de evaluación. Las cifras describen ese caso; no se generalizan a otros modelos.

## 1. Qué se preguntó

Hoy casi toda reunión se transcribe, pero una transcripción es texto conversacional: una decisión
no es un objeto que se pueda consultar, sino un pasaje repartido entre varios turnos. Y cuando la
decisión **cambia** (se toma en octubre, se matiza en noviembre, se revierte en diciembre), ninguna
reunión contiene el hecho más importante, que es la relación entre ellas.

El proyecto compara dos formas de contestar preguntas sobre las reuniones
([documento 03](03-jss-objetivos.md)):

| Condición | En palabras simples |
|---|---|
| **C0** | Sin ayuda: el modelo contesta solo con lo que ya sabe. Es el punto de referencia. |
| **C1** | Buscar en el texto: se recuperan los fragmentos más parecidos a la pregunta (la técnica usual llamada RAG). |
| **C2** | La base automática: una base de decisiones construida por un modelo local a partir de las transcripciones. |
| **C3** | La base con decisiones humanas: la misma base de C2, pero con las decisiones de la referencia hecha por personas. |

C2 y C3 comparten el código que consulta la base, así que **la única diferencia entre ambas son las
decisiones**. Por eso la distancia entre C3 y C2 mide cuánto cuestan los errores de la extracción
automática (notebook 31, sección 2.3).

## 2. Qué se encontró en cada objetivo

| Objetivo | Pregunta | Resultado principal | Fuente |
|---|---|---|---|
| **OE1** | ¿Se puede construir una referencia humana confiable? | Referencia de **14 series, 358 decisiones y 46 relaciones**. Dos personas coinciden bien en si hay una relación (kappa 0,783) y moderadamente en su tipo (0,554); la dirección no tiene kappa por falta de variación (acuerdo del 100 %). | Notebook 31, §2.1 |
| **OE2** | ¿Cuánto de la referencia encuentra la máquina? | Precisión **0,149**, recall **0,308**, F1 **0,201** (intervalo de 95 %: 0,161 a 0,240). De las relaciones, encuentra 11 de 111 de extremo a extremo y 11 de 24 cuando ya halló sus dos decisiones. | Notebook 31, §2.2 |
| **OE3** | ¿Responde mejor la base que el texto? | **No.** Corrección total: C0 0,16, C1 **0,72**, C2 **0,49**, C3 **0,80**. | Notebook 31, §2.3 |
| **OE4** | ¿Dónde falla C2? | De 43 respuestas incorrectas en hechos puntuales: extracción **21 (48,8 %)**, recuperación 11 (25,6 %), síntesis 11 (25,6 %). | Notebook 31, §2.4 |

### 2.1 OE1: la referencia es sólida donde se midió, y limitada donde no

La confiabilidad se midió en cuatro series de control (37 pares para existencia, 18 para tipo). Es
una buena señal, pero la mayor parte de la referencia de evaluación la produjo una sola persona:
**7 de las 11 series** (4 están adjudicadas tras doble anotación). Esa parte no tiene medida de
acuerdo (notebook 31, sección 2.1; [documento 10](10-jss-confiabilidad-de-la-referencia.md)).

### 2.2 OE2: la extracción automática es el eslabón débil

Con el criterio principal (τ = 0,70), de cada 100 decisiones que la máquina propone, unas 15
corresponden a una de la referencia, y de cada 100 de la referencia encuentra unas 31. Repetir la
extracción da prácticamente lo mismo (la desviación entre repeticiones es de unas milésimas): es una
propiedad de este modelo y esta configuración, no un azar. Una persona verificó a mano la regla que
decide cuándo dos decisiones son «la misma»: la concordancia fue de **0,825** y cumple el criterio
de 0,80 (notebook 31, sección 2.2; [documento 11](11-jss-resultados-experimento-a.md)).

### 2.3 OE3: el texto gana a la base automática; la base humana gana a ambos

| Condición | E1 (hecho puntual) | E2 (estado vigente) | E3 (evolución) | Total |
|---|---|---|---|---|
| C0 | 0,17 | 0,04 | 0,01 | 0,16 |
| C1 | 0,72 | 0,64 | 0,54 | 0,72 |
| C2 | 0,43 | 0,35 | 0,17 | 0,49 |
| C3 | 0,72 | 0,76 | 0,71 | 0,80 |

(Corrección, fracción de respuestas correctas; los intervalos de 95 % están en el
[documento 12](12-jss-resultados-experimento-b.md), sección 3.1. Fuente: notebook 31, sección 2.3.)
En E4 (preguntas sin respuesta en el corpus) C2 y C3 puntúan 1,00 porque se abstienen siempre; ese
valor no mide capacidad de responder.

### 2.4 OE4: el dato se pierde sobre todo al extraer

La cifra principal cubre **todas** las respuestas incorrectas de C2 en hechos puntuales: 43, de las
cuales 40 las etiquetó una persona a mano y 3 las atribuye una regla automática a la síntesis. El
detalle de las 40 etiquetadas a mano da 21 de extracción (52,5 %), 11 de recuperación (27,5 %) y 8 de
síntesis (20,0 %) (notebook 31, sección 2.4; [documento 12](12-jss-resultados-experimento-b.md),
sección 5).

## 3. Qué se encontró en cada hipótesis

| Hipótesis | Qué afirma | Resultado | Estado |
|---|---|---|---|
| **D16** (criterio principal) | La base automática (C2) supera al texto (C1) en preguntas de evolución (E3). | Diferencia C2 − C1 en E3 de −0,38; intervalo de 95 % de −0,61 a −0,14, por completo por debajo de 0. | **No respaldada**, con dirección contraria. |
| **H1** | C2 y C3 superan a C1 en E3, con diferencia pequeña o nula en E1. | Para C2, ver D16; en E1 también queda por debajo (−0,29). C3 frente a C1: 0,71 y 0,54 en E3, 0,72 y 0,72 en E1. | **No respaldada para C2.** C3 frente a C1 no tiene contraste preregistrado: es una lectura descriptiva. |
| **H2** | La brecha entre C3 y C2 es mayor en relaciones que en decisiones. | Brecha de 0,54 en E3 y de 0,29 en E1; diferencia de 0,25, intervalo de −0,04 a 0,54. | **No concluyente.** |
| **H3** | La dirección de las relaciones es un modo de falla dominante, sin mejora con el tamaño del modelo. | De 11 enlaces detectados, 0 con la dirección equivocada (cota superior 0,259) y 5 con el tipo equivocado. | **No concluyente.** Solo se midió una escala de modelo. |
| **H4** | C1 da más respuestas confiadas pero desactualizadas que C2 y C3. | Ni el juez ni las personas marcaron ninguna respuesta como desactualizada (42 ítems). | **No evaluable** con este juez. |

Fuente: notebook 31, sección 3.

**Cómo leer D16.** La herramienta imprime «inconclusive» para cualquier resultado que no quede por
encima de 0; ese rótulo no distingue «sin evidencia» de «evidencia en contra». Aquí hay que leer el
intervalo: queda por completo por debajo de 0, es decir, C1 supera a C2 (notebook 31, sección 3;
[documento 12](12-jss-resultados-experimento-b.md), sección 3.2).

**Qué dice el [documento 03](03-jss-objetivos.md) para este caso.** Declara que un resultado
negativo es igualmente publicable: «ninguna conclusión del proyecto depende de que el sistema
compilado gane; el aporte es la medición, no el sistema».

## 4. Qué significa

1. **La idea de la base de decisiones es viable cuando las decisiones son buenas.** C3 y C2 usan el
   mismo código de consulta; al reemplazar las decisiones automáticas por las de la referencia, la
   corrección en E3 pasa de 0,17 a 0,71 (una brecha de 0,54) y en el total de 0,49 a 0,80. El
   código de consulta no es lo que limita a C2 (notebook 31, sección 7).
2. **El cuello de botella es obtener esas decisiones automáticamente con un modelo local pequeño.**
   La extracción encuentra 0,308 de las decisiones (OE2) y es la etapa más frecuente del fallo de
   C2 (48,8 %, OE4). La causa no se puede atribuir a una sola cosa: el diseño de la extracción de
   OpenKOS y la capacidad del modelo local (qwen3:8b) están **confundidos** y el experimento no
   los separa.
3. **C3 es una referencia para las decisiones, no un techo.** Sus conceptos, eventos, proyectos y
   fuentes siguen siendo los de la extracción automática. Lo que C3 muestra es lo que se gana con
   buenas decisiones, no lo máximo que el sistema podría lograr.
4. **C3 frente a C1 es una lectura descriptiva.** La comparación no se preregistró, el análisis no
   la calcula y no sostiene ninguna afirmación de significancia. Los números (C3 0,80 y C1 0,72
   en el total) son un dato de contexto, no una conclusión.
5. **El resultado negativo de D16 es un resultado.** En este dominio y con este modelo, un RAG
   convencional supera a la base compilada automáticamente en todos los estratos con respuesta.

## 5. Costos

Tiempos de pared de una máquina concreta: un MacBook Pro de 16 pulgadas (2024) con chip Apple
M4 Pro, 48 GB de memoria unificada y macOS 27, con los modelos ejecutados localmente mediante
Ollama (`config/experiments.toml`, sección `[execution_hardware]`). Los tokens y la memoria no se
registraron. Fuente: notebook 31, sección 4, y las tablas `final-cost-latency` y
`final-break-even`.

| Concepto | Valor |
|---|---|
| Una consulta de C1 (búsqueda de texto) | 5,7 s |
| Una consulta de C2 (base automática) | 15,3 s (2,7 veces C1) |
| Una consulta de C3 | 14,5 s |
| Una consulta de C0 | 4,2 s |
| Juez automático, por respuesta | 6,3 s |
| Extracción de las once series, tres repeticiones | 11 h 48 min 42 s |
| Compilar la base de las once series, una repetición | 3 h 56 min 14 s |

**Punto de equilibrio.** La idea del diseño era que construir la base cuesta una vez y que cada
consulta posterior cuesta menos que una consulta RAG, de modo que en algún número de consultas se
recuperaría la inversión. En esta medición la segunda parte no se cumple: una consulta a la base es
**más lenta** que una consulta de texto, así que la inversión nunca se recupera y el punto de
equilibrio **no existe** (`no existe: C2 no es más barata por consulta que C1`). Esta conclusión se
refiere al tiempo de pared de este montaje; no considera el costo de la persona que consulta ni el
de los modelos en la nube.

## 6. Implicación práctica

Estos resultados **no** respaldan reemplazar la búsqueda de texto por una base construida
automáticamente con un modelo local pequeño. Sugieren, como **hipótesis para trabajo futuro y no
como resultado**, un diseño intermedio: que las personas confirmen o corrijan las decisiones al
momento de capturarlas (una persona en el circuito) y que la búsqueda de texto quede como respaldo
cuando la base no tenga el dato. La evidencia a favor es indirecta (C3 mejora mucho a C2 con
decisiones humanas y C2 se abstiene mucho cuando le falta el dato: 36 %, 51 % y 71 % en E1, E2 y E3; notebook 30, sección 5);
este proyecto no probó ese diseño ni midió el esfuerzo humano que exigiría.

## 7. Límites

- **Un solo modelo local pequeño** (qwen3:8b) para extraer y responder, y una sola corrida formal
  por experimento. Las cifras no se generalizan a otros modelos.
- **Diseño y modelo confundidos.** No se puede separar el diseño de la extracción de la capacidad
  del modelo (sección 4).
- **Juez automático.** Para la corrección se mantiene (kappa 0,807, umbral 0,70). Para la evidencia
  (`evidence_supported`) no es confiable (0,438) y H4 no se puede evaluar. Por condición, C0 queda
  bajo el umbral (0,484): el juez es más estricto con C0 que las personas, por lo que su corrección
  probablemente está subestimada y las diferencias frente a C0 podrían estar sobreestimadas. D16 y
  H2 no se ven afectadas, porque comparan condiciones que sí cumplen el umbral (notebook 31,
  sección 6).
- **Referencia de un solo anotador** en 7 de las 11 series de evaluación; la confiabilidad se midió
  solo en las cuatro series de control.
- **Muestra pequeña.** 99 preguntas (25 por estrato, 24 en E3), tres repeticiones promediadas por
  pregunta; los intervalos son anchos y las cifras por estrato son descriptivas. Las pocas relaciones
  (24 y 27 casos en la vista condicionada, 11 en tipo y dirección; notebook 28, sección 3.1) dejan H3 sin conclusión.
- **Dos posibles falsos negativos del juez** (preguntas q015 y q019) no verificados por una persona;
  no cambian ninguna cifra publicada.
- **La regla de síntesis de OE4 es léxica:** los 3 casos que atribuye comparan palabras, no
  significados.
- **Un corpus y un idioma.** Reuniones de un solo corpus (AMI) y una referencia comparada en inglés
  (traducción automática).

## 8. Trabajo futuro

1. **Correr el modelo grande.** El modelo de mayor escala está configurado
   (`generative_model_large`) pero no se corrió. Permitiría separar el diseño de la extracción de la
   capacidad del modelo y evaluar la cláusula de H3 sobre el tamaño.
2. **Una persona en el circuito.** Probar la captura de decisiones confirmadas por personas, con la
   búsqueda de texto como respaldo, y medir el esfuerzo que exige (sección 6).
3. **Un juez que pueda evaluar H4.** Con marcas positivas de respuestas desactualizadas (casos
   construidos a propósito o evaluación humana) para poder poner a prueba H4 y la evidencia.
4. **Ampliar la referencia.** Doble anotación de las series que hoy tienen un solo anotador y más
   relaciones de evolución, para sostener H2 y H3.
5. **Medir costo completo.** Tokens, memoria y el trabajo humano, además del tiempo de pared.
6. **Contraste preregistrado de C3 frente a C1,** si se quiere afirmar algo sobre el valor de la
   base con buenas decisiones frente al RAG.

## 9. Referencias

| Contenido | Fuente |
|---|---|
| Todas las cifras de este documento | [`notebooks/31-jss-resultados-finales.ipynb`](../../notebooks/31-jss-resultados-finales.ipynb) |
| Tablas y figuras finales | [`reports/tables/`](../../reports/tables/) (archivos `final-*`) |
| OE1: referencia y confiabilidad | [documento 10](10-jss-confiabilidad-de-la-referencia.md), [`notebooks/29-jss-anotacion-f3-referencia.ipynb`](../../notebooks/29-jss-anotacion-f3-referencia.ipynb) |
| OE2: Experimento A | [documento 11](11-jss-resultados-experimento-a.md), [`notebooks/28-jss-experimento-a.ipynb`](../../notebooks/28-jss-experimento-a.ipynb) |
| OE3 y OE4: Experimento B | [documento 12](12-jss-resultados-experimento-b.md), [`notebooks/30-jss-experimento-b.ipynb`](../../notebooks/30-jss-experimento-b.ipynb) |
| Objetivos e hipótesis | [documento 03](03-jss-objetivos.md), [documento 08](08-jss-metricas-y-criterio-de-exito.md) |
| Separación desarrollo/evaluación | [ADR 0005](../decisions/0005-adr-development-evaluation-split.md) |
| Decisiones del análisis (D16) | [ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md) |
| Medición de H4, H2 y H3 | [ADR 0017](../decisions/0017-adr-medicion-de-h4.md), [ADR 0018](../decisions/0018-adr-medicion-de-h2-y-h3.md) |
| Épica y tareas | Épica #288; issue #294 |
