# Línea base de OpenKOS 0.7.3

| | |
|---|---|
| **Documento** | 14 — Línea base de OpenKOS 0.7.3 |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.0 |
| **Fecha** | 2026-11-27 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-11-27 | Versión inicial. Resultado de la corrida `experimento-a-base-0-7-3`: `qwen3:8b` con OpenKOS 0.7.3 frente a la corrida formal (OpenKOS 0.7.0). | La corrida terminó (issue #331) y ningún documento registraba su resultado. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

> **Alcance.** Este documento reporta solo una comprobación previa de la extensión del
> Experimento A con modelos de pago ([ADR 0026](../decisions/0026-adr-extension-extractor-con-modelos-hosted.md)).
> No presenta resultados de modelos de pago ni del Experimento B. Las series son de
> **evaluación**: se muestran identificadores y cifras agregadas, nunca frases de decisión ni
> contenido de transcripciones ([ADR 0005](../decisions/0005-adr-development-evaluation-split.md)).
> Cada cifra remite al [notebook 34](../../notebooks/34-jss-linea-base-openkos-0-7-3.ipynb), que
> es el análisis que la respalda.

## En una página

- **Por qué se hizo.** La versión 0.7.3 de OpenKOS no se creó para extraer mejor: agrega las
  piezas para que el sistema funcione con modelos de pago a través de sus servicios en línea.
  La corrida formal del Experimento A usó la versión 0.7.0. Antes de comparar modelos de pago,
  había que comprobar que cambiar de versión, por sí solo, **no altera** lo que se extrae.
- **Qué se hizo.** Se repitió la extracción con el mismo modelo local de la corrida formal
  (`qwen3:8b`), pero con la versión 0.7.3, sobre las 11 series de evaluación, 3 veces cada una,
  con los mismos ajustes (semilla 42 y temperatura 0,1).
- **Resultado.** La corrida terminó completa (33 de 33 repeticiones, 44 reuniones, 12 h 56 min).
  Con el criterio principal, las cifras son prácticamente iguales a las de la corrida formal:
  precisión 0,147 frente a 0,149, recall 0,306 frente a 0,308 y F1 0,198 frente a 0,201. Las
  diferencias son de 0,002 y están dentro del margen de azar: **no se demuestra ninguna
  diferencia**.
- **Qué significa.** Los modelos de pago se pueden comparar con la corrida formal sin que el
  cambio de versión explique las diferencias. Si un modelo de pago extrae distinto, la causa será
  el modelo.
- **Lo que sigue.** Pilotos y corridas completas con los seis modelos de pago, comparados con
  esta corrida y con la formal.

## 1. Qué pregunta responde y por qué importa

La extensión del Experimento A repite la extracción de decisiones con seis modelos de pago para
saber si un modelo más capaz encuentra más decisiones de la referencia que el modelo local
pequeño. Esos modelos funcionan con la versión 0.7.3 de OpenKOS, mientras que la corrida formal
(el punto de comparación) usó la 0.7.0.

Si las dos versiones extrajeran distinto, cualquier diferencia entre un modelo de pago y la
corrida formal mezclaría dos causas: el modelo y la versión. La comprobación consiste en mantener
el modelo igual y cambiar solo la versión. Si el resultado es el mismo, la versión no es una
explicación posible.

## 2. Qué se hizo

- **Mismo modelo y mismos ajustes.** `qwen3:8b`, semilla 42, temperatura 0,1, el mismo modelo de
  búsqueda por similitud (`bge-m3`) y las mismas 11 series de evaluación con 3 repeticiones.
- **Medición idéntica a la formal.** Se midió con el mismo umbral de similitud (0,70), la misma
  referencia y el mismo método de intervalos: para cada reunión se compara cuántas decisiones
  encuentra cada corrida, y se remuestrea 10 000 veces para ver cuánto puede variar la diferencia
  por azar. El nivel de los intervalos (99,17 %) es el que se usará con los seis modelos de pago,
  de modo que esta comprobación se lee con la misma exigencia.
- **Qué mide de más.** La corrida se hizo con una versión más nueva del servidor local de modelos
  (Ollama 0.40.16) que la de la corrida formal. La diferencia que se observa incluye ese cambio,
  no solo el de OpenKOS (cuarta enmienda del ADR 0026). Como la diferencia resultó nula, no cambia
  la conclusión.

## 3. Resultados

### 3.1 La corrida terminó completa

Se completaron las 33 repeticiones (11 series por 3), sin fallos, sobre 44 reuniones. Todas las
decisiones extraídas se pudieron asociar a su reunión y todas las citas de apoyo se encontraron en
las transcripciones (1 738 de 1 738). El proceso tardó 12 h 56 min.

### 3.2 Calidad de la extracción

Con el criterio principal (umbral 0,70), cada cifra y su diferencia con la corrida formal:

| Medida | Corrida formal (0.7.0) | Esta corrida (0.7.3) | Diferencia (0.7.3 menos 0.7.0) |
|---|---|---|---|
| Precisión | 0,149 | 0,147 | −0,002 (de −0,015 a +0,010) |
| Recall | 0,308 | 0,306 | −0,002 (de −0,031 a +0,022) |
| F1 | 0,201 | 0,198 | −0,002 (de −0,020 a +0,013) |

La **precisión** es la parte de lo extraído que está en la referencia; el **recall**, la parte de
la referencia que se encontró; el **F1** las resume en un solo número. En las tres, la diferencia
es de dos milésimas y el intervalo incluye el cero: con 44 reuniones no se distingue de cero. El
veredicto es «sin diferencia demostrada». Esto no prueba que las versiones sean idénticas, solo que
esta medición no encuentra una diferencia.

Con umbrales más estrictos (0,75 y 0,80), que son análisis de sensibilidad y no el criterio, las
diferencias siguen siendo de uno o dos puntos porcentuales como máximo; con 0,75 tampoco se
demuestra diferencia, y con 0,80 los intervalos quedan algo por debajo de cero (veredicto
«empeora»). Se informa tal cual: es un cambio de alrededor de un punto porcentual en un umbral más
exigente que el prerregistrado, y no altera la conclusión con el criterio principal.

### 3.3 Tiempo por reunión

La mediana de tiempo por reunión fue de 327,5 s con la 0.7.3 y de 307,1 s en la corrida formal.
El cociente es 1,09 (intervalo de 1,00 a 1,19) y el veredicto también es «sin diferencia
demostrada». El tiempo depende además de la carga del equipo y de la versión de Ollama, por lo que
es solo una referencia.

### 3.4 El puente de la versión 0.7.2

Antes de esta corrida se hizo un ensayo corto con la versión 0.7.2 (una serie, una repetición). Su
precisión y su F1 quedaron algo por encima del rango de las tres repeticiones formales de esa serie.
Esto ya se conocía: una sola repetición no permite separar el efecto de la versión del azar, y la
primera enmienda del ADR 0026 dejó establecido que decide la corrida de la misma versión sobre
todas las series, que es esta.

## 4. Qué significa para la extensión con modelos de pago

- Las diferencias que aparezcan entre un modelo de pago y la corrida formal no se pueden explicar
  por el cambio de versión de OpenKOS: se leerán como efecto del modelo.
- Esta corrida sirve como segunda línea base, con la misma versión que usarán los modelos de pago.
  La corrida formal sigue siendo la principal.
- **Límites.** Un solo modelo, 11 series, una sola máquina. Las series de evaluación ya se usaron
  en la corrida formal, por lo que estas cifras describen, no confirman una hipótesis de la tesis.
- **Lo que sigue.** Pilotos y corridas completas de los seis modelos de pago (issues #332 y #333),
  comparados con esta línea base y con la corrida formal en el [notebook 33](../../notebooks/33-jss-extraccion-con-modelos-de-pago.ipynb).
