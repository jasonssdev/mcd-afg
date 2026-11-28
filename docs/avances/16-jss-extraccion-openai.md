# Extracción con modelos de OpenAI

| | |
|---|---|
| **Documento** | 16 — Extracción con modelos de OpenAI |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.0 |
| **Fecha** | 2026-11-28 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-11-28 | Versión inicial. Resultado de las corridas de los dos modelos de OpenAI (`gpt-5-mini` y `gpt-6-luna`) como extractor de C2, frente a la corrida formal y a la línea base de OpenKOS 0.7.3. | Las corridas completas de OpenAI terminaron y ningún documento registraba su resultado. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

> **Alcance.** Este documento reporta solo la parte de OpenAI de la extensión del Experimento A
> con modelos de pago ([ADR 0026](../decisions/0026-adr-extension-extractor-con-modelos-hosted.md)).
> Los resultados de los otros laboratorios tienen su propio documento, y uno general cierra la
> extensión. No presenta cifras del Experimento B. Las series son de **evaluación**: se muestran
> identificadores y cifras agregadas, nunca frases de decisión ni contenido de transcripciones
> ([ADR 0005](../decisions/0005-adr-development-evaluation-split.md)). Cada cifra remite al
> [notebook 36](../../notebooks/36-jss-extraccion-openai.ipynb), que es el análisis que la
> respalda. Es un resultado **descriptivo**: las series de evaluación ya se usaron en la corrida
> formal, de modo que nada de lo que sigue confirma una hipótesis de la tesis.

## En una página

- **Qué se hizo.** Se reemplazó el modelo pequeño que extrae las decisiones (`qwen3:8b`, que corre
  en el computador del proyecto) por dos modelos de pago de OpenAI, y se repitió la extracción
  sobre las mismas 11 series de evaluación, 3 veces cada una. El modelo pequeño de OpenAI es
  `gpt-5-mini` y el grande, `gpt-6-luna`.
- **Resultado del modelo grande.** Encuentra el **60,8 %** de las decisiones de la referencia, frente
  al 30,8 % de la corrida formal (recall 0,608 frente a 0,308), y además es más preciso: el 24,5 % de
  lo que extrae coincide con la referencia (precisión 0,245, frente a 0,149). Por la regla fijada de
  antemano, **mejora** la extracción.
- **Resultado del modelo pequeño.** Encuentra el 49,2 % de las decisiones de la referencia (recall
  0,492, frente a 0,308), pero su precisión no mejora (0,134, frente a 0,149) y no se puede descartar
  que baje más de lo que la regla tolera. Por la regla, el veredicto es **sin diferencia
  demostrada**.
- **Costo y tiempo.** El modelo pequeño costó **USD 4,84** y tardó 5 h 13 min en las 33 corridas; el
  grande costó **USD 1,07** y tardó 2 h 31 min. La corrida formal, local, tardó 11 h 48 min y no
  tiene costo de uso. En este laboratorio el modelo grande resultó más barato y más rápido que el
  pequeño.
- **Qué significa para la tesis.** Un extractor más fuerte de OpenAI **sí encuentra muchas más
  decisiones**, lo que refuerza que el extractor era el eslabón débil. Pero este documento mide solo
  la extracción, no si las respuestas de C2 mejoran con ella: eso se mide aparte.

## 1. Qué pregunta responde y por qué importa

En C2, el sistema responde a partir de las decisiones que una etapa previa extrae de las reuniones.
Esa etapa es el **eslabón más débil**: con el modelo local pequeño de la corrida formal, encuentra
menos de un tercio de las decisiones que el equipo anotó a mano. Si el extractor se pierde la
mayoría de las decisiones, ninguna etapa posterior puede recuperarlas.

La extensión del Experimento A (ADR 0026) pregunta: **¿un extractor más capaz arregla ese
eslabón?** Para responderlo se prueban seis modelos de pago, dos de cada uno de tres laboratorios
(OpenAI, Anthropic y Google). Este documento cubre los dos de OpenAI, el segundo laboratorio en
terminar.

## 2. Cómo se mide

- **Qué se compara.** Cada modelo de OpenAI se compara con la corrida formal (la comparación
  principal) y con `qwen3:8b` ejecutado sobre la misma versión del programa que usan los modelos de
  pago, para que la versión no explique las diferencias ([documento 14](14-jss-linea-base-openkos-0-7-3.md)).
  Los dos resultados coinciden en los veredictos.
- **Precisión, recall y F1.** La **precisión** es la parte de lo extraído que está en la
  referencia: responde a «¿cuánto de lo que dice el sistema es una decisión real?». El **recall** es
  la parte de la referencia que el sistema encontró: responde a «¿cuántas decisiones reales se
  perdieron?». El **F1** resume las dos en un número. Una decisión extraída cuenta como encontrada
  cuando su similitud con la de la referencia supera un umbral (0,70 es el criterio; 0,75 y 0,80 son
  pruebas de sensibilidad).
- **La regla, fijada antes de ver datos.** Un modelo **mejora** la extracción solo si se cumplen
  dos condiciones a la vez: (1) su recall es mayor que el de la línea base **con certeza
  estadística**, es decir, el intervalo de la diferencia queda entero por encima de cero, y (2) su
  precisión no cae más de 0,05 respecto de la línea base. Si el intervalo del recall incluye el
  cero, el veredicto es «sin diferencia demostrada», aunque otras cifras suban. Por eso la regla
  pide una ganancia **demostrada de recall**: lo que busca la extensión es encontrar decisiones que
  antes se perdían.
- **Cómo se decide la certeza.** Para cada reunión se compara cuántas decisiones encuentra cada
  sistema y se remuestrea 10 000 veces para ver cuánto puede variar la diferencia por azar. Como se
  prueban seis modelos, los intervalos son más exigentes que el 95 % habitual (99,17 %).

## 3. Resultados

### 3.1 Las corridas terminaron completas

Los dos modelos terminaron las 33 repeticiones (11 series por 3), sobre 44 reuniones: 132 de 132
extracciones completas en cada uno y ninguna reunión con marca de fallo de la extracción. Antes se
hizo un piloto de una serie con cada modelo (USD 0,17 el pequeño y USD 0,04 el grande), que salió
bien y sirvió para estimar el costo.

### 3.2 Calidad de la extracción

Con el criterio principal (umbral 0,70), cada cifra y su diferencia con la corrida formal:

| Medida | Corrida formal | GPT-5 mini | Diferencia (mini) | GPT-6 Luna | Diferencia (Luna) |
|---|---|---|---|---|---|
| Precisión | 0,149 | 0,134 | −0,014 (de −0,064 a +0,034) | 0,245 | +0,096 (de +0,053 a +0,143) |
| Recall | 0,308 | 0,492 | +0,183 (de +0,047 a +0,341) | 0,608 | +0,300 (de +0,192 a +0,419) |
| F1 | 0,201 | 0,211 | +0,010 (de −0,057 a +0,084) | 0,349 | +0,148 (de +0,089 a +0,216) |
| Veredicto | | | **sin diferencia demostrada** | | **mejora** |

- **GPT-6 Luna.** Su recall sube 0,300 con un intervalo entero por encima de cero, y su precisión
  también sube con un intervalo entero por encima de cero, de modo que cumple las dos condiciones. El
  veredicto es **mejora** con los tres umbrales (0,70, 0,75 y 0,80).
- **GPT-5 mini.** Es un caso límite que conviene explicar con cuidado. Su recall sube 0,183 y el
  intervalo queda entero por encima de cero: encuentra más decisiones de la referencia que
  `qwen3:8b`. Pero la regla pide además que la precisión no caiga más de 0,05, y el extremo inferior
  de su intervalo de precisión (−0,064) pasa ese margen. Es decir, encuentra más de la referencia,
  pero con una posible pérdida de precisión mayor que la tolerada. La regla no se cumple y el
  veredicto es **sin diferencia demostrada**; se informa tal cual. Con los umbrales más exigentes
  (0,75 y 0,80) contra la corrida formal el veredicto sigue igual, y contra la línea base de la
  misma versión pasa a «mejora» con 0,75 y 0,80, como sensibilidad y no como criterio.
- **Lo mismo contra la línea base de la misma versión.** Con el criterio principal los veredictos de
  los dos modelos coinciden con los de la corrida formal, y las diferencias son casi iguales (por
  ejemplo, el recall de Luna sube +0,302).

### 3.3 Cuántas decisiones extrae cada modelo

En promedio, la referencia tiene **6,3** decisiones por reunión. `qwen3:8b` extrae 13,1; GPT-5 mini,
**23,1**; GPT-6 Luna, **15,7**. Esto explica el patrón: mini extrae casi cuatro veces las decisiones de
la referencia, encuentra bastante más de ella, pero gran parte de lo que extrae no está en la
referencia, por lo que su precisión no mejora. Luna extrae menos que mini y acierta más: encuentra
mucho más de la referencia y su precisión sube. Parte de lo que los dos extraen de más puede ser
válido aunque nadie lo anotó, algo que esta medición no distingue.

### 3.4 Tiempo y costo

| | Mediana por reunión | Tiempo total de la corrida | Costo de la corrida | Costo mediano por reunión |
|---|---|---|---|---|
| `qwen3:8b` (corrida formal, local) | 307 s | 11 h 48 min | sin costo de uso | — |
| GPT-5 mini | 143 s | 5 h 13 min | USD 4,84 | USD 0,038 |
| GPT-6 Luna | 70 s | 2 h 31 min | USD 1,07 | USD 0,008 |

Los dos modelos son más rápidos que el local con intervalos claros (mini tarda algo menos de la mitad;
Luna, alrededor de una quinta parte). Los costos son **exactos**: todas las llamadas (2 215 y 2 220)
informaron cuántos tokens usaron, y los tokens son las unidades en que el proveedor cobra. Se usaron
los precios de lista leídos el 26 de noviembre de 2026 (USD 0,25 de entrada y 2,00 de salida por
millón de tokens para mini; USD 0,10 y 0,50 para Luna), sin promociones con fecha de término. El
modelo grande resultó más barato porque su precio por token es menor y usó menos tokens (6,80
millones frente a 7,52 millones). Una advertencia: el tiempo no es una comparación limpia, porque el
modelo local corre en un computador del proyecto y los de pago en los servidores del proveedor.

## 4. Qué significa para la tesis

La pregunta de la tesis es si **un extractor más fuerte arregla el eslabón más débil**.

- **Lo que sí muestra esta medición.** Un modelo más capaz **encuentra mucho más** de la
  referencia: Luna pasa de encontrar 3 de cada 10 decisiones a encontrar 6 de cada 10, con evidencia
  estadística, y a la vez sube su precisión. El extractor no era un techo fijo del sistema.
- **El equilibrio.** En este laboratorio no hay que elegir entre calidad, tiempo y costo: Luna es el
  único modelo de OpenAI con mejora demostrada, y también es el más rápido y el más barato. Mini
  encuentra más decisiones que el modelo local, pero con más ruido, más tiempo y más de cuatro veces el
  costo de Luna, sin cumplir la regla.
- **Lo que no se puede decir todavía.** Que las **respuestas** de C2 mejoren. Encontrar más
  decisiones es una condición necesaria, no suficiente: la medición de si C2 responde mejor con
  cada extractor, frente a C1, se hace aparte con el Experimento B de C2 (ADR 0026, tercera
  enmienda).
- **Límites.** Dos modelos de un solo laboratorio, 11 series, una configuración de razonamiento
  fija en `low` para todos y modelos que el proveedor puede cambiar sin aviso detrás del mismo
  nombre. Las series de evaluación ya se usaron en la corrida formal, por lo que estas cifras
  describen, no confirman una hipótesis.
- **Lo que sigue.** Las corridas de Anthropic, con su propio documento, y un documento general que
  compare los seis modelos. Como referencia, los dos modelos de Google (documento 15) dieron un
  resultado de mejora solo para el grande.
