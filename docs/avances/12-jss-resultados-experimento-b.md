# Resultados del Experimento B (OE3 y OE4)

| | |
|---|---|
| **Documento** | 12 — Resultados del Experimento B (OE3 y OE4) |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.1 |
| **Fecha** | 2026-11-08 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-11-07 | Versión inicial. Resultados de la corrida formal del Experimento B (`experimento-b-formal`) sobre las once series de evaluación: las cuatro condiciones, D16, H2, la validez del juez automático y la etapa del fallo de C2 (OE4). | La corrida formal y su verificación quedaron completas (issue #294, épica #288) y ningún documento reportaba aún estos resultados. |
| 1.1 | 2026-11-08 | Precisa la comparación entre condiciones y documenta el desacuerdo observado en q015, corrida 2. Actualiza los enlaces a los resultados finales. | Alinear la interpretación con los ADR 0013 y 0014 y con la muestra de verificación del juez. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

> **Alcance.** Este documento reporta solo el Experimento B. El Experimento A se reporta en el
> [documento 11](11-jss-resultados-experimento-a.md). Las series son de **evaluación**: se
> muestran identificadores de pregunta y de serie, etiquetas y cifras agregadas, nunca texto de
> respuestas, de decisiones ni de transcripciones ([ADR 0005](../decisions/0005-adr-development-evaluation-split.md)).
> Cada cifra remite al [notebook 30](../../notebooks/30-jss-experimento-b.ipynb) (sección
> indicada entre paréntesis) o a los archivos versionados que ese notebook lee, en
> `reports/experiment-b/experimento-b-formal/`.

## En una página

- **La pregunta.** Cuando se le pide a un modelo de lenguaje local que conteste preguntas sobre
  reuniones, ¿importa qué le damos para leer? Se comparan cuatro formas: nada (C0), trozos del
  texto de la reunión (C1), una base de conocimiento construida automáticamente (C2) y esa misma
  base con las decisiones corregidas por personas (C3).
- **Resultado principal.** C1, que lee texto, acierta más que C2, la base automática: **0,72
  frente a 0,49** en el total. La base con decisiones humanas (C3) llega a **0,80**. Sin contexto
  (C0) el modelo acierta **0,16**.
- **D16.** La hipótesis de que la base automática supera al texto en las preguntas de evolución
  (E3) **no se respalda**. Más aún: la diferencia es −0,38 y su intervalo de 95 % (de −0,61 a
  −0,14) queda **por completo por debajo de 0**. La herramienta imprime «inconclusive» porque ese
  rótulo cubre cualquier caso que no sea «por encima de 0»; no distingue «sin evidencia» de
  «evidencia en contra».
- **H2.** La brecha entre C3 y C2 es mayor en E3 (0,54) que en E1 (0,29), pero la diferencia
  (0,25; intervalo de −0,04 a 0,54) incluye 0: **no concluyente**.
- **El juez automático.** Para la corrección de las respuestas se mantiene: acuerdo con las
  personas de kappa 0,807 (umbral 0,70). Para `evidence_supported` no es confiable (0,438) y
  **H4 no se puede evaluar** con este juez. Por condición, C0 queda por debajo del umbral (0,484).
- **Dónde falla C2.** De 43 respuestas incorrectas de C2 en E1, **la etapa más frecuente es la
  extracción** (21, 48,8 %): el dato no llegó a quedar en la base. Siguen la recuperación (11,
  25,6 %) y la síntesis (11, 25,6 %).
- **Alcance.** Una sola corrida formal (tres repeticiones por pregunta), un generador local pequeño
  (qwen3:8b), 99 preguntas. Las cifras describen
  ese caso. La extracción confunde dos causas (el diseño de OpenKOS y la capacidad del modelo
  local) que el experimento no separa.

## 1. Qué pregunta responde y por qué importa

El Experimento B responde los objetivos OE3 y OE4 ([documento 03](03-jss-objetivos.md)). La idea
es sencilla: una persona que no estuvo en una serie de reuniones hace preguntas como «¿qué se
decidió sobre el precio?» o «¿esa decisión cambió después?». Un sistema contesta leyendo
material de las reuniones. El experimento mide **cuánto mejora o empeora la respuesta según el
material que el sistema recibe**, y por qué falla cuando falla.

Importa porque el sistema que se estudia (OpenKOS, [ADR 0003](../decisions/0003-adr-openkos-as-instrument.md))
se apoya en una base de decisiones construida automáticamente. El Experimento A
([documento 11](11-jss-resultados-experimento-a.md)) mostró que esa construcción encuentra cerca
de 3 de cada 10 decisiones de la referencia humana. El Experimento B pregunta si, aun así, esa base
sirve para responder mejor que simplemente leer el texto, y qué pasaría si las decisiones fueran
correctas.

## 2. Qué se hizo

### 2.1 La corrida

| Elemento | Valor | Fuente |
|---|---|---|
| Corrida | `experimento-b-formal` | Notebook 30, §1 |
| Series | 11 series de evaluación: ES2002, ES2008, ES2014, ES2016, IS1003, IS1006, IS1008, IS1009, TS3003, TS3005, TS3011 | Notebook 30, §1 |
| Preguntas | 99 (25 en E1, 25 en E2, 24 en E3, 25 en E4) | Notebook 30, §1 y §2 |
| Condiciones y repeticiones | 4 condiciones (C0 a C3), 3 repeticiones por pregunta | Notebook 30, §1 |
| Registros | 1.188 esperados, 1.188 completos, 0 con error | Notebook 30, §1 |
| Modelo generador | `qwen3:8b`, temperatura 0,1, semilla 42 | Notebook 30, §1 |
| Modelo juez | `gpt-oss:20b`, temperatura 0,0 | Notebook 30, §1 |
| Sistema | OpenKOS 0.7.0, Ollama 0.32.9 | Notebook 30, §1 |
| Commit de la corrida | `c6ee4500b9c7`; árbol de trabajo limpio (`git_dirty = False`); entorno fijado cumplido | Notebook 30, §1 |
| Congelamiento | [ADR 0025](../decisions/0025-adr-relaciones-con-extremo-compuesto.md) | Notebook 30, §1 |
| Informe | Reportable; el archivo del análisis es `analisis.json` | Notebook 30, §1 |

**Sobre el nombre del informe.** El issue #294 menciona un `informe.json`; ese nombre es el del
Experimento A. El comando de análisis del Experimento B guarda su informe en `analisis.json`.

### 2.2 Qué recibe cada condición

Las cuatro condiciones usan el **mismo generador** y reciben la **misma pregunta**. Para interpretar
la comparación entre C1 y C2 hay que distinguir el material recuperado del procedimiento que lo usa
para responder.

| Condición | En palabras simples | Qué recibe |
|---|---|---|
| **C0** | Sin ayuda | Nada. El modelo contesta solo con lo que ya sabe. Sirve de punto de referencia. |
| **C1** | Leer el texto | Recupera hasta cinco fragmentos de la transcripción y responde en una llamada con el flujo del RAG convencional. |
| **C2** | La base automática | Recupera objetos de la base compilada y comprueba si el contexto alcanza antes de responder con OpenKOS. |
| **C3** | La base con decisiones de referencia | Usa la consulta de C2 y sustituye las decisiones y sus enlaces por los de la referencia de OE1. |

**Un ejemplo con la serie ES2002, repetición 0** (Notebook 30, §1; son archivos locales no
versionados, por lo que la cifra proviene de la salida guardada del notebook):

- **C1** lee la transcripción cruda de la reunión (`data/interim/transcripts/ES2002a.md`),
  cortada en trozos.
- **C2** lee la base construida automáticamente (`data/interim/openkos/experimento-a-formal/ES2002/run-0/bundle/`).
  Esa base tiene 54 decisiones, 19 conceptos, 2 eventos, 1 proyecto y 4 fuentes.
- **C3** lee una copia de esa base con las decisiones y los enlaces de la referencia humana
  (`.../openkos-c3/experimento-a-formal/ES2002/run-0/bundle/`). Quedan 29
  decisiones (la referencia tiene 31; 2 se descartaron por no tener evidencia). Los conceptos,
  eventos, proyectos y fuentes son los mismos de C2. La trazabilidad queda en su `c3-manifest.json`.

La diferencia C2 − C1 corresponde a los dos sistemas completos. Incluye el efecto de la
representación y el del procedimiento de respuesta, incluida la comprobación de suficiencia de
OpenKOS ([ADR 0014](../decisions/0014-adr-c1-como-rag-convencional.md)). C2 y C3 sí comparten la
consulta, por lo que su contraste muestra el efecto conjunto de sustituir las decisiones y sus
enlaces ([ADR 0013](../decisions/0013-adr-composicion-de-la-base-c3.md)).

### 2.3 Tipos de pregunta (estratos)

| Estrato | Tipo de pregunta | Preguntas |
|---|---|---|
| E1 | Un hecho puntual de una decisión | 25 |
| E2 | Cuál es el estado vigente | 25 |
| E3 | Cómo evolucionó (relación entre decisiones) | 24 |
| E4 | No hay respuesta en el corpus | 25 |

En E4 lo correcto es abstenerse. Las respuestas de las tres repeticiones se promedian por
pregunta, y los intervalos remuestrean preguntas, no respuestas, porque las repeticiones de una
misma pregunta no son independientes.

### 2.4 Glosario

| Término | Qué significa, en simple |
|---|---|
| **Corrección** (`correct`) | Si el juez decide que la respuesta dice lo mismo que la respuesta de referencia. |
| **Juez** | Un segundo modelo de lenguaje que compara cada respuesta con la de referencia. |
| **Intervalo de 95 %** | Rango calculado por remuestreo de preguntas: indica cuánto podría variar la cifra con otras preguntas. |
| **Diferencia pareada** | Diferencia de corrección entre dos condiciones, pregunta por pregunta. |
| **Kappa** | Acuerdo entre dos evaluadores descontando el azar: 0 es como el azar, 1 es perfecto. El umbral es 0,70. |
| **Abstención** | La condición responde que no encuentra la respuesta en su contexto. |
| **D16, H2, H4** | Hipótesis preregistradas ([ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md), [0017](../decisions/0017-adr-medicion-de-h4.md), [0018](../decisions/0018-adr-medicion-de-h2-y-h3.md)). |

## 3. Resultados principales

### 3.1 Corrección por condición y estrato

Corrección (fracción de respuestas correctas) con su intervalo de 95 %. Fuente: Notebook 30, §2.

| Condición | E1 | E2 | E3 | E4 | Total |
|---|---|---|---|---|---|
| **C0** | 0,17 [0,04; 0,33] | 0,04 [0,00; 0,12] | 0,01 [0,00; 0,04] | 0,40 [0,21; 0,59] | 0,16 [0,09; 0,23] |
| **C1** | 0,72 [0,55; 0,88] | 0,64 [0,44; 0,84] | 0,54 [0,36; 0,72] | 0,96 [0,88; 1,00] | 0,72 [0,63; 0,80] |
| **C2** | 0,43 [0,25; 0,60] | 0,35 [0,19; 0,52] | 0,17 [0,04; 0,32] | 1,00 [1,00; 1,00] | 0,49 [0,39; 0,58] |
| **C3** | 0,72 [0,56; 0,88] | 0,76 [0,60; 0,91] | 0,71 [0,54; 0,86] | 1,00 [1,00; 1,00] | 0,80 [0,72; 0,87] |

El análisis no registró fallos del juez, registros con error ni advertencias, y ninguna celda
quedó por debajo del mínimo preregistrado de preguntas.

**Interpretación.**

- **C1 acierta más que C2 en E1, E2 y E3**, y la diferencia crece con la complejidad de la
  pregunta: en E3 C2 acierta 0,17 frente a 0,54 de C1.
- **C3 recupera casi todo lo que C2 pierde**: queda igual que C1 en E1 (0,72 las dos) y con
  valores más altos en E2 y E3 (0,76 y 0,71 frente a 0,64 y 0,54), sin que el análisis contraste
  esa diferencia (sección 8). La lectura de esta comparación está en la sección 7.
- **En E4 C2 y C3 puntúan 1,00 porque se abstienen siempre** (sección 6.1); abstenerse es lo
  correcto en E4. Ese valor no mide capacidad de responder.

### 3.2 D16: ¿la base automática supera al texto en E3?

D16 es la hipótesis principal. Se respalda si el intervalo de 95 % de la diferencia pareada
C2 − C1 en E3 queda **por encima de 0** ([ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md)).
Fuente: Notebook 30, §2.

| Indicador | Valor |
|---|---|
| Diferencia C2 − C1 en E3 | −0,38 |
| Intervalo de 95 % | de −0,61 a −0,14 |
| Preguntas pareadas | 24 (muestra suficiente) |
| Intervalo de C2 | de 0,04 a 0,32 |
| Intervalo de C1 | de 0,36 a 0,72 |
| Rótulo que imprime la herramienta | «inconclusive» |

**Interpretación.** El intervalo queda **por completo por debajo de 0**: D16 **no se respalda**, y
la dirección observada es la contraria (C1 supera a C2). El rótulo «inconclusive» no contradice
esto: la herramienta lo usa para todo resultado que no sea «por encima de 0», sin distinguir entre
«sin evidencia» y «evidencia en contra». Hay que leer el intervalo y no el rótulo. Los intervalos
independientes de C2 y C1 tampoco se superponen, y la redacción original del criterio (por no
superposición) da el mismo rótulo.

Las demás diferencias pareadas sobre la corrección apuntan en el mismo sentido en E1, E2, E3 y en
el total; en E4 no hay diferencia clara (diferencia con intervalo de 95 %):

| Comparación | E1 | E2 | E3 | E4 | Total |
|---|---|---|---|---|---|
| C2 − C1 | −0,29 [−0,49; −0,08] | −0,29 [−0,51; −0,08] | −0,38 [−0,61; −0,14] | 0,04 [0,00; 0,12] | −0,23 [−0,33; −0,13] |
| C2 − C3 | −0,29 [−0,51; −0,07] | −0,41 [−0,60; −0,24] | −0,54 [−0,72; −0,36] | 0,00 [0,00; 0,00] | −0,31 [−0,40; −0,22] |

(En «C2 − C3» una diferencia negativa significa que C3 acierta más. Solo la de E3 en «C2 − C1» es la
comparación primaria de D16; las demás son secundarias.)

### 3.3 H2: ¿la brecha entre C3 y C2 es mayor en relaciones que en decisiones?

H2 compara la brecha de corrección C3 − C2 en E3 (preguntas de relación) con la misma brecha en E1
(preguntas de decisión) ([ADR 0018](../decisions/0018-adr-medicion-de-h2-y-h3.md)). Fuente:
Notebook 30, §2.

| Indicador | Valor |
|---|---|
| Brecha C3 − C2 en E3 | 0,54 (24 preguntas) |
| Brecha C3 − C2 en E1 | 0,29 (25 preguntas) |
| Diferencia de brechas | 0,25 |
| Intervalo de 95 % | de −0,04 a 0,54 |
| Veredicto | no concluyente (`inconclusive`) |

**Interpretación.** La brecha es mayor en E3, en la dirección que H2 espera, pero el intervalo
incluye 0. No se puede afirmar que la brecha sea mayor en relaciones que en decisiones.

### 3.4 C0 como punto de referencia

Sin ningún contexto, C0 acierta 0,16 [0,09; 0,23] en el total (Notebook 30, §2). Frente a esa
referencia (diferencias descriptivas, que no deciden D16 ni las hipótesis):

| Comparación | E1 | E2 | E3 | E4 | Total |
|---|---|---|---|---|---|
| C1 − C0 | 0,55 [0,36; 0,73] | 0,60 [0,40; 0,80] | 0,53 [0,36; 0,69] | 0,56 [0,37; 0,75] | 0,56 [0,46; 0,65] |
| C2 − C0 | 0,25 [0,08; 0,44] | 0,31 [0,16; 0,48] | 0,15 [0,04; 0,31] | 0,60 [0,41; 0,79] | 0,33 [0,24; 0,42] |

Recuperar texto (C1) aporta 0,56 puntos sobre no recuperar nada y la base automática (C2) aporta 0,33.
Una respuesta acertada de C0 no prueba conocimiento previo del corpus ni lo descarta. C0 no cita ni
aporta evidencia, así que sus métricas de evidencia y de citación no aplican. La sección 4.3
muestra por qué estas dos diferencias podrían estar algo infladas.

## 4. Validez del juez automático

Germán verificó a ciegas 240 respuestas, 60 por condición. La hoja de anotación ocultaba la
condición y el veredicto del juez. El Notebook 30 (§3) cruza esa hoja con su clave y comprueba
el acuerdo registrado en `juez-humano.json`.

### 4.1 Acuerdo global

| Etiqueta | Ítems | Acuerdo observado | «Sí» del juez | «Sí» de las personas | Kappa | ¿Cumple 0,70? |
|---|---|---|---|---|---|---|
| `correct` | 240 | 0,904 | 52,9 % | 56,7 % | **0,807** | **Sí** |
| `evidence_supported` | 240 | 0,754 | 60,4 % | 80,0 % | 0,438 | **No** |
| `outdated` | 42 | 1,000 | 0,0 % | 0,0 % | indefinido | **No** |

**Interpretación.**

- **`correct` cumple.** Se mantiene el juicio automático de la corrección: los resultados de la
  sección 3 pueden leerse con él.
- **`evidence_supported` no cumple.** El juez marca «sí» en menos casos que las personas (60,4 %
  frente a 80,0 %): es más estricto. Esa métrica no es confiable y solo debe leerse como descriptiva
  o con evaluación humana. No se usa para ninguna conclusión de este documento.
- **`outdated` y H4.** En los 42 ítems que el juez evaluó, ni el juez ni las personas marcaron «sí»
  (0,0 % en ambos). Con una sola clase el kappa no se puede calcular y cuenta como «no cumple».
  Aunque el acuerdo observado sea 100 %, **H4 (respuestas desactualizadas) no es evaluable con este
  juez**: sin ninguna marca positiva no hay una tasa que comparar ([ADR 0017](../decisions/0017-adr-medicion-de-h4.md)).

### 4.2 Acuerdo por condición (exploratorio)

Kappa de `correct`, calculado por separado con los 60 ítems de cada condición (Notebook 30, §3):

| Condición | Ítems | Acuerdo observado | «Sí» del juez | «Sí» de las personas | Kappa | ¿Cumple 0,70? |
|---|---|---|---|---|---|---|
| C0 | 60 | 0,817 | 16,7 % | 28,3 % | 0,484 | **No** |
| C1 | 60 | 0,883 | 70,0 % | 71,7 % | 0,718 | Sí |
| C2 | 60 | 0,950 | 45,0 % | 46,7 % | 0,899 | Sí |
| C3 | 60 | 0,967 | 80,0 % | 80,0 % | 0,896 | Sí |

El umbral preregistrado se aplica a la muestra completa, no a cada condición, y 60 ítems por
condición dan estimaciones inestables: esta tabla describe, no contrasta.

### 4.3 Consecuencias de que C0 quede bajo el umbral

En C0 el juez marca «sí» en 16,7 % de la muestra y las personas en 28,3 %: **el juez es más
estricto con C0**. De ahí se desprende lo siguiente:

- La corrección de C0 (0,16) **probablemente está subestimada**.
- Las diferencias **C1 − C0 y C2 − C0 probablemente están sobreestimadas**; el tamaño del sesgo no
  está medido.
- **D16 y H2 usan otras condiciones.** D16 compara C2 con C1, y H2 compara C3 con C2. El menor
  acuerdo observado en C0 afecta la lectura de las comparaciones que incluyen esa condición.
  El acuerdo por condición es exploratorio y el umbral se aplica a la muestra completa.

### 4.4 Un desacuerdo comprobado y cuatro casos fuera de la muestra

En **q015, corrida 2**, el juez marcó la respuesta como incorrecta y Germán como correcta. El
Notebook 30 (§3) muestra el desacuerdo al unir la hoja de verificación y su clave por `id`.

| Pregunta | Corridas que el juez marcó incorrectas | Etapa OE4 | Verificación de la corrección |
|---|---|---|---|
| q015 | 0 y 2 | Síntesis | Germán marcó la 2 como correcta. La 0 quedó fuera de la muestra. |
| q019 | 0, 1 y 2 | Extracción | Las tres quedaron fuera de la muestra. |

El desacuerdo de q015 ilustra un error individual respecto de la etiqueta humana de verificación.
Los cuatro casos restantes se mantienen como observaciones. El conteo formal usa el veredicto del
juez bajo el criterio de acuerdo global fijado para la corrida.

## 5. OE4: en qué etapa falla C2

OE4 pregunta, cuando C2 responde mal en E1, **dónde se perdió el dato**: al *extraer* (la base
nunca lo guardó), al *recuperar* (la base lo tiene pero no se entregó a C2) o al *sintetizar*
(C2 lo recibió y no lo usó bien). Fuente: Notebook 30, §4 (`oe4-etapa-e1.csv`, `oe4-resumen.json` y
los registros `respuestas.jsonl`).

### 5.1 Cifra principal: las 43 respuestas incorrectas

Los registros contienen **43** respuestas incorrectas de C2 en E1 (en las 3 repeticiones). De ellas,
40 las etiquetó una persona a mano y 3 las atribuye la regla automática a la síntesis (la hoja de
etiquetado las deja fuera por diseño).

| Etapa | Casos | Proporción |
|---|---|---|
| **Extracción** | 21 | **48,8 %** |
| Recuperación | 11 | 25,6 % |
| Síntesis | 11 (8 etiquetadas + 3 por la regla) | 25,6 % |

**La etapa más frecuente es la extracción**: en esos casos el dato no llegó a quedar en el objeto
que la base ofrecía a C2.

**Los 3 casos de la regla.** Son la pregunta q025 en las 3 repeticiones. La regla cuenta una falla
como de síntesis cuando algún bloque del contexto entregado a C2 contiene todos los términos de
contenido de la respuesta de referencia. En esos tres casos C2 se abstuvo (`no_answer_in_context`)
teniendo el 100 % de esos términos a la vista en un bloque de tipo «sources», que es la
transcripción cruda importada a la base. La regla compara palabras y no significados, de modo que
es una pista y no una prueba.

### 5.2 Detalle de las 40 filas etiquetadas a mano

El anotador `gm` etiquetó a mano las 40 filas de `oe4-etapa-e1.csv`. Esta subsección es solo ese
subconjunto, por lo que sus proporciones (sobre 40) difieren de las de la cifra principal (sobre
43). Coinciden con `oe4-resumen.json`:

| Etapa | Casos | Proporción (sobre 40) |
|---|---|---|
| Extracción | 21 | 52,5 % |
| Recuperación | 11 | 27,5 % |
| Síntesis | 8 | 20,0 % |

- **Acuerdo con la regla.** La pista automática de la hoja solo sugiere etapa en 6 de las 40 filas y
  en las 6 coincide con la persona (6 de 6). Las otras 34 dependen del juicio humano.
- **Ajuste de q019.** La pregunta q019 (3 filas) quedó primero como síntesis, porque el objeto
  recuperado describía el mecanismo y C2 lo reprodujo. `jss` la reetiquetó como **extracción**: el
  detalle de la referencia sí está en la transcripción de la serie y falta en el objeto recuperado,
  es decir, C2 reprodujo fielmente lo que recuperó y el dato se perdió al extraer. La nota de esas
  filas en la hoja registra el cambio y el resumen se rehízo después.

## 6. Citas y abstención

Fuente: Notebook 30, §5 (`analisis.json` y `respuestas.jsonl`).

### 6.1 Abstención

Abstenciones sobre el total de registros de cada celda (3 repeticiones por pregunta):

| Condición | E1 | E2 | E3 | E4 |
|---|---|---|---|---|
| C0 | 0/75 (0 %) | 0/75 (0 %) | 0/72 (0 %) | 0/75 (0 %) |
| C1 | 0/75 (0 %) | 3/75 (4 %) | 0/72 (0 %) | 48/75 (64 %) |
| C2 | 27/75 (36 %) | 38/75 (51 %) | 51/72 (71 %) | 75/75 (100 %) |
| C3 | 3/75 (4 %) | 13/75 (17 %) | 17/72 (24 %) | 75/75 (100 %) |

C0 nunca se abstiene. En E4, donde abstenerse es lo esperado, C2 y C3 lo hacen siempre y C1 en el
64 %. C2 se abstiene mucho más que las demás en las preguntas que sí tienen respuesta (36 %, 51 % y
71 % en E1, E2 y E3), lo que es coherente con una base a la que le falta el dato.

### 6.2 Citas

C0 no cita. Para las otras tres condiciones, en el total:

| Condición | Cita correcta | Precisión de la cita | Respuestas con cita evaluable | Citas a la transcripción completa |
|---|---|---|---|---|
| C1 | 0,70 [0,59; 0,81] | 0,59 [0,50; 0,69] | 219 | 0 |
| C2 | 0,45 [0,31; 0,60] | 0,39 [0,26; 0,53] | 106 | 95 |
| C3 | 0,71 [0,60; 0,81] | 0,59 [0,49; 0,69] | 189 | 79 |

(Las «citas a la transcripción completa» apuntan a la reunión entera y no cuentan como evidencia.)

**Interpretación.** C2 cita correctamente menos que C1 y C3, que se parecen entre sí; además tiene
menos respuestas con cita evaluable y buena parte de sus citas apunta a la transcripción completa.
La precisión y la cobertura de actos dependen de cuán ancha es la cita (mediana de actos citados:
53 en C1, 7 en C2 y 5 en C3; cobertura media de actos: 0,34, 0,18 y 0,24): una cita correcta no
equivale a una cita precisa.

## 7. Lectura de conjunto

- **La extracción es la etapa más frecuente en E1.** Representa 21 de los 43 fallos de C2 (48,8 %).
  Recuperación y síntesis representan 11 cada una. En un contraste distinto, C3 conserva la consulta
  de C2 y reemplaza las decisiones y sus enlaces. La corrección en E3 pasa de 0,17 a 0,71, una
  diferencia de 0,54 en esta corrida.
- **C2 no supera a C1** (D16 no se respalda, con dirección contraria) y H2 queda no concluyente.
- **El juez es utilizable para la corrección,** no para la evidencia, y no permite evaluar H4.
- **Cómo interpretar C3.** Las decisiones y enlaces de referencia también sirvieron para redactar
  el banco de preguntas. Por eso C3 mide un escenario de control con acceso a ese contenido. Los
  conceptos, eventos, proyectos y fuentes siguen siendo los de la extracción automática.

## 8. Límites

- **C3 frente a C1 no fue una hipótesis preregistrada.** El análisis no la calcula como comparación
  guardada. Comparar las tasas de C3 y C1 es una lectura descriptiva y no sostiene ninguna
  afirmación de significancia.
- **Dos causas confundidas en la extracción.** Que la extracción sea el punto débil mezcla el diseño
  de extracción de OpenKOS con la capacidad del modelo local (`qwen3:8b`). El diseño del
  experimento no las separa, de modo que el fallo no puede atribuirse a una sola.
- **`evidence_supported` no es confiable y H4 no es evaluable** con este juez (sección 4.1).
- **Kappa por condición.** Es exploratorio (60 ítems por condición); en C0 queda bajo el umbral y
  las diferencias frente a C0 podrían estar sobreestimadas (sección 4.3).
- **Desacuerdo en la muestra.** q015, corrida 2, recibió juicios distintos del juez y de Germán.
  La revisión humana de la corrección se limita a los ítems incluidos en la muestra (§4.4).
- **La regla de síntesis es léxica.** Los 3 casos que atribuye la regla (sección 5.1) se basan en
  coincidencia de palabras, no de significado.
- **Una sola corrida formal,** con un generador local pequeño, 25 preguntas por estrato (24 en E3) y
  3 repeticiones que se promedian por pregunta. Los intervalos son anchos y las cifras por estrato
  son descriptivas.

## 9. Qué sigue

Las [tablas finales](../../reports/tables/), el [Notebook 31](../../notebooks/31-jss-resultados-finales.ipynb)
y el [avance de conclusiones](13-jss-conclusiones.md) reúnen los resultados de ambos experimentos.
El [preinforme 02](informes/02-jss-pre-informe.md) integra las cifras y su interpretación para la
entrega de AFG2.

## 10. Referencias

| Contenido | Fuente |
|---|---|
| Análisis de la corrida (todas las cifras de este documento) | [`notebooks/30-jss-experimento-b.ipynb`](../../notebooks/30-jss-experimento-b.ipynb) |
| Procedencia de la corrida | [`manifest.json`](../../reports/experiment-b/experimento-b-formal/manifest.json) |
| Análisis y comparaciones | [`analisis.json`](../../reports/experiment-b/experimento-b-formal/analisis.json) |
| Validez del juez | [`juez-humano.json`](../../reports/experiment-b/experimento-b-formal/juez-humano.json), [`muestra-juez.csv`](../../reports/experiment-b/experimento-b-formal/muestra-juez.csv), [`muestra-juez.clave.csv`](../../reports/experiment-b/experimento-b-formal/muestra-juez.clave.csv) |
| OE4 | [`oe4-etapa-e1.csv`](../../reports/experiment-b/experimento-b-formal/oe4-etapa-e1.csv), [`oe4-resumen.json`](../../reports/experiment-b/experimento-b-formal/oe4-resumen.json) |
| Registros de la corrida | [`respuestas.jsonl`](../../reports/experiment-b/experimento-b-formal/respuestas.jsonl) |
| Resultados del Experimento A | [documento 11](11-jss-resultados-experimento-a.md) |
| Separación desarrollo/evaluación | [ADR 0005](../decisions/0005-adr-development-evaluation-split.md) |
| Regla de citación | [ADR 0009](../decisions/0009-adr-regla-de-citacion-correcta.md) |
| Decisiones del análisis (D16) | [ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md) |
| C1 como RAG convencional | [ADR 0014](../decisions/0014-adr-c1-como-rag-convencional.md) |
| Medición de H4 | [ADR 0017](../decisions/0017-adr-medicion-de-h4.md) |
| Medición de H2 y H3 | [ADR 0018](../decisions/0018-adr-medicion-de-h2-y-h3.md) |
| C0 en la corrida formal | [ADR 0019](../decisions/0019-adr-c0-en-la-corrida-formal-del-experimento-b.md) |
| Hoja OE4 y congelamiento | [ADR 0024](../decisions/0024-adr-hoja-oe4-autocontenida.md), [ADR 0025](../decisions/0025-adr-relaciones-con-extremo-compuesto.md) |
| Objetivos, hipótesis y métricas | [documento 03](03-jss-objetivos.md), [documento 08](08-jss-metricas-y-criterio-de-exito.md) |
| Épica y tareas | Épica #288; issue #294 |
