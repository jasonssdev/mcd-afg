# Extracción con modelos de Google

| | |
|---|---|
| **Documento** | 15 — Extracción con modelos de Google |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.0 |
| **Fecha** | 2026-11-27 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-11-27 | Versión inicial. Resultado de las corridas de los dos modelos de Google (`gemini-3.8-flash` y `gemini-4-argon`) como extractor de C2, frente a la corrida formal y a la línea base de OpenKOS 0.7.3. | Las corridas completas de Google terminaron y ningún documento registraba su resultado. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

> **Alcance.** Este documento reporta solo la parte de Google de la extensión del Experimento A
> con modelos de pago ([ADR 0026](../decisions/0026-adr-extension-extractor-con-modelos-hosted.md)).
> Los resultados de OpenAI y de Anthropic tendrán su propio documento, y uno general cerrará la
> extensión. No presenta cifras del Experimento B. Las series son de **evaluación**: se muestran
> identificadores y cifras agregadas, nunca frases de decisión ni contenido de transcripciones
> ([ADR 0005](../decisions/0005-adr-development-evaluation-split.md)). Cada cifra remite al
> [notebook 35](../../notebooks/35-jss-extraccion-google.ipynb), que es el análisis que la
> respalda. Es un resultado **descriptivo**: las series de evaluación ya se usaron en la corrida
> formal, de modo que nada de lo que sigue confirma una hipótesis de la tesis.

## En una página

- **Qué se hizo.** Se reemplazó el modelo pequeño que extrae las decisiones (`qwen3:8b`, que corre
  en el computador del proyecto) por dos modelos de pago de Google, y se repitió la extracción
  sobre las mismas 11 series de evaluación, 3 veces cada una. El modelo pequeño de Google es
  `gemini-3.8-flash` y el grande, `gemini-4-argon`.
- **Resultado del modelo grande.** Encuentra el **70,5 %** de las decisiones de la referencia, frente
  al 30,8 % de la corrida formal (recall 0,705 frente a 0,308). A cambio extrae más decisiones de las
  que hay en la referencia: solo el 30 % de lo que extrae coincide con ella (precisión 0,298). Por
  la regla fijada de antemano, **mejora** la extracción.
- **Resultado del modelo pequeño.** Es más selectivo: de lo que extrae, el 44 % coincide con la
  referencia (precisión 0,438, frente a 0,149). Pero encuentra casi las mismas decisiones que el
  modelo local (recall 0,375 frente a 0,308), y esa diferencia no se distingue del azar. Por la
  regla, el veredicto es **sin diferencia demostrada**.
- **Costo y tiempo.** El modelo pequeño costó **USD 6,28** y tardó 2 h 31 min en las 33 corridas; el
  grande costó **USD 21,22** y tardó 7 h 33 min. La corrida formal, local, tardó 11 h 48 min y no
  tiene costo de uso.
- **Qué significa para la tesis.** Un extractor más fuerte **sí encuentra muchas más decisiones**,
  lo que apunta a que el extractor era el eslabón débil. Pero este documento mide solo la
  extracción, no si las respuestas de C2 mejoran con ella: eso se mide aparte.

## 1. Qué pregunta responde y por qué importa

En C2, el sistema responde a partir de las decisiones que una etapa previa extrae de las reuniones.
Esa etapa es el **eslabón más débil**: con el modelo local pequeño de la corrida formal, encuentra
menos de un tercio de las decisiones que el equipo anotó a mano. Si el extractor se pierde la
mayoría de las decisiones, ninguna etapa posterior puede recuperarlas.

La extensión del Experimento A (ADR 0026) pregunta: **¿un extractor más capaz arregla ese
eslabón?** Para responderlo se prueban seis modelos de pago, dos de cada uno de tres laboratorios
(OpenAI, Anthropic y Google). Este documento cubre los dos de Google, el primer laboratorio en
terminar.

## 2. Cómo se mide

- **Qué se compara.** Cada modelo de Google se compara con la corrida formal (la comparación
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
extracciones completas en cada uno y ninguna reunión sin objetos extraídos. Antes se hizo un piloto
de una serie con cada modelo (USD 0,24 el pequeño y USD 0,81 el grande), que salió bien y sirvió para
estimar el costo.

### 3.2 Calidad de la extracción

Con el criterio principal (umbral 0,70), cada cifra y su diferencia con la corrida formal:

| Medida | Corrida formal | Gemini 3.8 Flash | Diferencia (Flash) | Gemini 4 Argon | Diferencia (Argon) |
|---|---|---|---|---|---|
| Precisión | 0,149 | 0,438 | +0,290 (de +0,206 a +0,381) | 0,298 | +0,149 (de +0,100 a +0,205) |
| Recall | 0,308 | 0,375 | +0,067 (de −0,039 a +0,185) | 0,705 | +0,397 (de +0,285 a +0,505) |
| F1 | 0,201 | 0,404 | +0,204 (de +0,128 a +0,288) | 0,419 | +0,218 (de +0,151 a +0,289) |
| Veredicto | | | **sin diferencia demostrada** | | **mejora** |

- **Gemini 4 Argon.** Su recall sube 0,397 con un intervalo entero por encima de cero, y su
  precisión también sube, de modo que cumple las dos condiciones. El veredicto es **mejora** con los
  tres umbrales (0,70, 0,75 y 0,80).
- **Gemini 3.8 Flash.** Su precisión y su F1 suben con claridad, pero el intervalo del recall
  (de −0,039 a +0,185) incluye el cero: no se puede decir que encuentre más decisiones que
  `qwen3:8b`. Por la regla, **no es una mejora demostrada**. Con umbrales más exigentes el
  resultado se mueve: con 0,80 contra la corrida formal el veredicto pasa a «mejora», y con 0,75 y
  0,80 contra la línea base de la misma versión también. Se informa tal cual, como sensibilidad y
  no como criterio.
- **Lo mismo contra la línea base de la misma versión.** Las diferencias y los veredictos son casi
  iguales a los de la corrida formal (por ejemplo, el recall de Argon sube +0,399).

### 3.3 Cuántas decisiones extrae cada modelo

En promedio, la referencia tiene **6,3** decisiones por reunión. `qwen3:8b` extrae 13,1; Flash,
**5,4**; Argon, **15,0**. Esto explica el patrón: Flash extrae poco y casi todo lo que extrae es
válido (precisión alta, recall modesto); Argon extrae más de lo que hay en la referencia, encuentra
mucho más de ella, y por eso su precisión es menor. Parte de lo que Argon extrae de más puede ser
válido aunque nadie lo anotó, algo que esta medición no distingue.

### 3.4 Tiempo y costo

| | Mediana por reunión | Tiempo total de la corrida | Costo de la corrida | Costo mediano por reunión |
|---|---|---|---|---|
| `qwen3:8b` (corrida formal, local) | 307 s | 11 h 48 min | sin costo de uso | — |
| Gemini 3.8 Flash | 67 s | 2 h 31 min | USD 6,28 | USD 0,047 |
| Gemini 4 Argon | 195 s | 7 h 33 min | USD 21,22 | USD 0,159 |

Los dos modelos son más rápidos que el local con intervalos claros (Flash tarda alrededor de una
quinta parte; Argon, dos tercios). Los costos son **exactos**: todas las llamadas (2 218 y 2 220)
informaron cuántos tokens usaron, y los tokens son las unidades en que el proveedor cobra. Dos
advertencias: los precios usados son promocionales y vencen (Flash, el 31 de diciembre de 2026;
Argon, el 30 de noviembre de 2026, tres días después de la corrida), de modo que repetir la corrida
después de esas fechas costaría el doble; y el tiempo no es una comparación limpia, porque el
modelo local corre en un computador del proyecto y los de pago en los servidores del proveedor.

## 4. Qué significa para la tesis

La pregunta de la tesis es si **un extractor más fuerte arregla el eslabón más débil**.

- **Lo que sí muestra esta medición.** Un modelo más capaz **encuentra mucho más** de la
  referencia: Argon pasa de encontrar 3 de cada 10 decisiones a encontrar 7 de cada 10, con
  evidencia estadística. El extractor no era un techo fijo del sistema.
- **El equilibrio.** No hay un modelo mejor en todo. Flash es barato, rápido y selectivo, pero no
  encuentra más; Argon encuentra mucho más, pero con más ruido, más tiempo y unas tres veces el
  costo de Flash.
- **Lo que no se puede decir todavía.** Que las **respuestas** de C2 mejoren. Encontrar más
  decisiones es una condición necesaria, no suficiente: la medición de si C2 responde mejor con
  cada extractor, frente a C1, se hace aparte con el Experimento B de C2 (ADR 0026, tercera
  enmienda).
- **Límites.** Dos modelos de un solo laboratorio, 11 series, una configuración de razonamiento
  fija en `low` para todos y modelos que el proveedor puede cambiar sin aviso detrás del mismo
  nombre. Las series de evaluación ya se usaron en la corrida formal, por lo que estas cifras
  describen, no confirman una hipótesis.
- **Lo que sigue.** Las corridas de OpenAI y de Anthropic, cada una con su documento, y un documento
  general que compare los seis modelos.
