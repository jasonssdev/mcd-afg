# Métricas y criterio de éxito

| | |
|---|---|
| **Documento** | 08 — Métricas y criterio de éxito |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.0 |
| **Fecha** | 2026-10-15 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-10-15 | Versión inicial. Reúne en un solo lugar qué se mide, sobre qué objeto, cómo se calcula, qué umbral o intervalo aplica y cómo se sabrá si el experimento tuvo éxito; declara las decisiones que siguen abiertas. No fija ninguna cifra ni regla nueva: cada dato remite al documento, ADR, configuración o notebook donde ya está definido. | Retroalimentación del profesor: faltaba tener claras las métricas del proyecto. El material del curso pide métricas aunque sean preliminares, como línea base (pre-informe del curso, p. 12, pregunta frecuente 5). |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## Por qué existe este documento

Las métricas del proyecto están repartidas en cuatro lugares: la propuesta, los objetivos
(documento 03), la metodología (documento 06) y los registros de decisión (`docs/decisions/`).
Cada lugar explica la parte que le toca, y quien quiera responder "¿qué se mide, y cómo
sabremos si funcionó?" tiene que recorrerlos todos. Este documento junta esa respuesta en un
solo sitio y la cuenta en lenguaje llano.

Una advertencia de honestidad sobre el estado del proyecto: **todavía no existe ningún
resultado de evaluación**. Las cifras que aparecen aquí son de tres tipos: umbrales y reglas
fijadas de antemano, mediciones sobre series de desarrollo (que sirven para calibrar, nunca
para reportar) y simulaciones con datos sintéticos. Cada una está marcada como tal.

## Términos que se usan

- **OE1 a OE4.** Los cuatro objetivos específicos ([documento 03](03-jss-objetivos.md)). OE1
  construye el conjunto de referencia, anotado por personas. OE2 mide qué tan bien extrae
  decisiones la máquina (Experimento A). OE3 compara la utilidad de tres condiciones al
  responder preguntas (Experimento B). OE4 atribuye cada error a su etapa.
- **C1, C2 y C3.** Las tres condiciones que se comparan. C1 busca fragmentos de texto y
  redacta con ellos (RAG); C2 consulta una base de decisiones construida por la máquina; C3
  consulta la misma base construida por personas ([documento 09](09-jss-modelos-y-justificacion.md), §3).
- **Estrato.** Grupo de preguntas del mismo tipo: E1 (hecho puntual), E2 (estado vigente), E3
  (evolución de una decisión, el que prueba la tesis) y E4 (sin respuesta en el material).
- **τ (tau).** Umbral de similitud a partir del cual una decisión extraída por la máquina y una
  de la referencia se consideran candidatas a ser la misma (§4.3).
- **OpenKOS.** Motor de código abierto con el que se construye y consulta la base de decisiones
  de C2 y C3 ([documento 09](09-jss-modelos-y-justificacion.md), §3.2).

## 1. Un caso concreto: qué es "una respuesta correcta"

En una de las series del corpus AMI (IS1004), el resumen oficial de la cuarta reunión afirma
que el equipo eliminó el botón "turbo" del control remoto. Al leer la transcripción completa,
el botón se mantuvo: la eliminación nunca ocurrió (documento 06, §7–8; manual de anotación,
§3 y §4). Es el caso que motiva el proyecto.

Supóngase que se le hace al sistema esta pregunta, que pertenece al tipo "evolución" (E3):

> ¿Se mantuvo el botón turbo?

- **Respuesta de referencia**, derivada de la evidencia que las personas marcaron en la
  transcripción: *"Sí. Se decidió conservarlo en la reunión c y nada posterior lo revirtió."*
- **Una respuesta correcta** coincide con la referencia en lo esencial: dice que se mantuvo.
- **Una respuesta incorrecta pero confiada** dice "no, se eliminó en la reunión d". Es lo que
  contesta un sistema que se fía del resumen oficial.
- **Una respuesta correcta con mala cita** dice "sí, se mantuvo", pero la fuente que cita es
  un pasaje que no habla del botón. La respuesta acierta; la cita no la respalda.
- **Una abstención** ("no hay información") es correcta solo en las preguntas que el material
  no puede responder (estrato E4). Aquí sería un error.

Cada métrica de este documento mide una de esas facetas: si la respuesta acierta (corrección),
si lo que dice tiene respaldo en la transcripción (soporte de evidencia), si la cita apunta al
lugar correcto (citación correcta) y si el sistema sabe callar cuando corresponde (corrección
del rechazo).

## 2. Cómo leer este documento: seis ideas

### 2.1 Umbrales de validez y criterio de éxito son cosas distintas

El proyecto usa dos clases de regla que conviene no mezclar.

- Un **umbral de validez** responde: *¿se puede confiar en la medición?* Por ejemplo, si el
  juez automático (un segundo modelo que califica las respuestas) coincide poco con las
  personas, sus calificaciones no sirven. Cumplir un umbral de validez **no** significa que el
  proyecto haya tenido éxito; incumplirlo significa que cierta medición no se puede usar tal
  cual.
- El **criterio de éxito** responde: *¿funcionó la propuesta?* Es una sola regla, fijada antes
  de correr el experimento para que no se pueda ajustar a los resultados (decisión D16,
  enmendada por D17).

El registro de decisiones lo dice así: los umbrales operativos del documento 06 "son umbrales
de validez de la medición, no criterios de éxito" (`docs/decisions/README.md`, D16).

### 2.2 Intervalo de confianza

Una cifra obtenida con pocos casos puede cambiar mucho con otros casos parecidos. El
**intervalo de confianza (IC) del 95 %** es el rango de valores compatibles con lo observado;
un intervalo ancho avisa que se ha visto poco. El proyecto usa dos métodos (documento 06,
§7–8):

- **Intervalo de Wilson**, para una proporción con pocos casos (por ejemplo, 5 de 11). No produce límites
  fuera de 0 y 1.
- **Bootstrap percentil**, para todo resultado experimental: se remuestrean las preguntas con
  reemplazo 10.000 veces, se recalcula la métrica en cada remuestreo y se toman los
  percentiles 2,5 % y 97,5 % (`config/experiments.toml`, `bootstrap_resamples`,
  `bootstrap_confidence_level`; `afg.evaluation.metrics.bootstrap_ci`).

### 2.3 Diferencia pareada

C1 y C2 responden **las mismas preguntas**. En lugar de comparar el promedio de aciertos de
cada una por separado, se calcula pregunta por pregunta cuánto mejor o peor le fue a C2 que a
C1 y se promedian esas diferencias. Ejemplo ilustrativo con cuatro preguntas (los números son
inventados, solo para mostrar el mecanismo):

| Pregunta | C1 | C2 | Diferencia C2 − C1 |
|---|---|---|---|
| P1 | incorrecta (0) | correcta (1) | +1 |
| P2 | incorrecta (0) | incorrecta (0) | 0 |
| P3 | correcta (1) | correcta (1) | 0 |
| P4 | incorrecta (0) | correcta (1) | +1 |

La diferencia promedio es +0,5. La ventaja de este enfoque: una pregunta difícil lo es para
las dos condiciones, y esa dificultad común se cancela en la diferencia. Por eso detecta
mejoras reales con menos preguntas que comparar dos intervalos independientes (§5).

### 2.4 Precisión, cobertura y F1

Miden la extracción de decisiones (OE2). Ejemplo ilustrativo: la referencia tiene 16 decisiones
reales y la máquina extrae 10, de las cuales 8 son reales y 2 son sobras.

- **Precisión**: de lo extraído, qué parte era correcta. 8 de 10 = 0,80.
- **Cobertura** (*recall*): de lo que existe, qué parte se encontró. 8 de 16 = 0,50.
- **F1**: un solo número que combina ambas y baja si cualquiera es baja:
  2 × 0,80 × 0,50 / (0,80 + 0,50) ≈ 0,62.

Una máquina que extrae poco y acierta siempre tiene precisión alta y cobertura baja; el F1
impide quedarse con una sola de las dos caras.

### 2.5 Kappa de Cohen

Mide cuánto coinciden dos personas **descontando el azar**. Vale 1 si coinciden del todo, 0 si
coinciden lo mismo que el azar y es negativo si coinciden menos. Ejemplo del manual de anotación
(§6): en diez pares, dos personas coinciden en el 80 %; pero como cada una vio enlace en 8 de 10
pares, el azar por sí solo explicaría un 68 %. El kappa es (0,80 − 0,68) / (1 − 0,68) =
**0,375**: un 80 % de coincidencia "suena alto", pero con una categoría dominante el azar
explica casi todo. El kappa puede quedar **indefinido** si las dos personas usan siempre la
misma categoría única; no se reemplaza por 1 ni por 0 (manual de anotación, §6).

### 2.6 Estado de cada métrica

En las tablas se usan tres estados: **implementada** (existe la función y su prueba en
`src/afg/`, pero no hay resultado real), **medida** (existe una cifra, con su fuente) y
**pendiente** (falta trabajo humano o una corrida para obtenerla). Una métrica puede estar
implementada y además tener una cifra preliminar sobre desarrollo.

## 3. Tabla resumen

| Métrica | Qué mide (en simple) | Se aplica a | Cómo se calcula | Umbral / intervalo / regla de lectura | Dónde está definida | Estado |
|---|---|---|---|---|---|---|
| **Kappa de anotación** (existencia, tipo, dirección) | Cuánto coinciden dos personas al marcar si dos decisiones se relacionan, cómo y en qué sentido | Series de control con doble anotación (4 de las 11 series de evaluación, 36,4 %; más 2 series de calibración de desarrollo) | Kappa de Cohen, un valor por cada uno de los tres ejes, nunca combinados | **Sin umbral de aceptación, por diseño.** Se reporta tal como salga; un kappa bajo es un hallazgo | Doc. 06 §1 y §5–6; manual de anotación §6; `annotation/agreement.py` | Implementada. Medida solo como diagnóstico en la calibración (kappa de estado 0,094 en ES2015); series de control pendientes |
| **Recall del filtro léxico** | Qué parte de las relaciones reales deja pasar el filtro que decide qué pares se anotan | 200 pares rechazados (50 por serie × IS1004, ES2016, IS1003, TS3005) | Relaciones reales halladas entre los rechazados, sobre el total muestreado; por sitio y en conjunto, con IC bootstrap | **Sin umbral.** Se reporta la cifra y su intervalo | Doc. 06 §2; manual de anotación §5; `annotation/blocking.py`; `config/annotation.toml` `[annotation.recall_sample]` | Muestra generada, sin anotar. Pendiente |
| **Precisión, cobertura y F1** (OE2) | Qué tan bien la máquina encuentra las decisiones de la referencia | Decisiones extraídas por la máquina frente a las 343 de la referencia | Conteos de aciertos, sobras y faltantes tras el alineamiento (§4.3); F1 como **curva sobre τ** | Sin umbral ni criterio de éxito; curva con τ de 0,50 a 0,90 en pasos de 0,05 | Propuesta §5.4 y §5.6; [`docs/protocols/alignment.md`](../protocols/alignment.md); [`config/experiments.toml`](../../config/experiments.toml) `[alignment]` | Implementada. Pendiente de medir (no hay extracción real de evaluación) |
| **Exactitud de tipo y de dirección** (OE2) | Si la máquina acierta qué relación hay entre dos decisiones y cuál revisa a cuál | Relaciones entre decisiones | Fracción de relaciones con etiqueta (o sentido) igual a la referencia; se reportan por separado | Sin umbral | Propuesta §5.6; `evaluation/metrics.py` | Implementada. Pendiente |
| **Concordancia del alineamiento** | Si la regla automática que empareja decisiones coincide con el emparejamiento manual | Muestra de al menos 100 pares | Pares coincidentes entre ambos emparejamientos sobre la unión de pares emparejados | **≥ 0,80**; si no, se revisa la grilla de τ y se repite | Doc. 06 §1; [`docs/protocols/alignment.md`](../protocols/alignment.md); `evaluation/alignment.py` (`concordance`) | Implementada. Pendiente de medir |
| **Corrección de respuesta** (OE3) | Si la respuesta acierta frente a la referencia | Preguntas del banco; **métrica principal en el estrato E3** | Promedio por pregunta de las corridas calificadas por el juez; IC bootstrap | Ver criterio D16 (§6): IC de la diferencia pareada C2 − C1 por encima de 0 | Doc. 06 §1; D16 y D17 (`docs/decisions/README.md`); [ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md); `experiments/analysis.py` | Implementada. Pendiente de medir |
| **Soporte de evidencia** (OE3) | Si cada afirmación de la respuesta tiene respaldo en la transcripción | Preguntas del banco | Marca del juez por respuesta; promedio por pregunta | Secundaria y descriptiva. Verificación humana con su propia marca de confiable o no confiable (kappa ≥ 0,70) | Propuesta §5.6; [ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md) | Implementada. Pendiente |
| **Citación correcta** y **precisión de la citación** (OE3) | Si la fuente citada contiene la evidencia de la pregunta; qué fracción de lo citado es pertinente | Respuestas a preguntas con respuesta (no E4) | Correcta si **al menos un** pasaje citado toca la evidencia; sin cita cuenta como falla. Precisión = pasajes que aciertan / pasajes citados | Secundaria y descriptiva. Riesgo declarado: podría favorecer a C1, que cita fragmentos grandes | [ADR 0009](../decisions/0009-adr-regla-de-citacion-correcta.md); doc. 06 §1; `evaluation/citation.py` | Implementada. Pendiente |
| **Corrección del rechazo** (OE3) | Si el sistema sabe decir "no hay información" cuando no la hay | Estrato E4 (preguntas sin respuesta) | Fracción de preguntas E4 en que el sistema se abstiene | Secundaria y descriptiva | Propuesta §5.6; `experiments/analysis.py` | Implementada. Pendiente |
| **Costo amortizado** (OE3) | Desde cuántas consultas compensa haber construido la base | C2 (y C3) frente a C1 | Menor *n* tal que `costo_compilación + n · costo_consulta_estructurada < n · costo_consulta_RAG` | Si la consulta estructurada no es más barata que la RAG, no hay punto de equilibrio y eso es un resultado | Propuesta §5.6; doc. 06 §7–8; `evaluation/amortization.py` | Implementada. Pendiente |
| **Recall@K de recuperación** | Si entre los K fragmentos recuperados está la evidencia | Solo la etapa de recuperación de C1 y C2 | Fracción de la evidencia de referencia que aparece entre los K recuperados | Sin umbral; se usa para ajustar C1 sobre ES2015 con una regla fijada antes de correr | Propuesta §5.4; [ADR 0007](../decisions/0007-adr-ajuste-c1-y-presupuesto-de-contexto.md); `config/experiments.toml` `[retrieval.tuning]` | Implementada y usada en desarrollo ([notebook 06](../../notebooks/06-jss-ajuste-c1.ipynb)) |
| **Atribución del error** (OE4) | En qué etapa nació cada respuesta fallida de C2 | Respuestas fallidas de C2 | Reglas fijas en orden: extracción, luego recuperación, luego síntesis | Cada error cae en una y solo una categoría; la proporción atribuible a extracción es la cifra principal | Doc. 03 (OE4); doc. 06 §7–8; `evaluation/attribution.py` | Implementada. Pendiente |
| **Concordancia juez–humano** | Si el juez automático coincide con las personas | 20 % de las respuestas juzgadas (una corrida sorteada por pregunta y condición), por etiqueta | Kappa de Cohen; siempre se informan también el acuerdo observado y la prevalencia | **Kappa ≥ 0,70** por etiqueta; kappa indefinido cuenta como «no cumple» | Doc. 06 §1 y §5–6; [ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md); `evaluation/judge_human_check.py` | Implementada. Pendiente sobre el Experimento B |
| **Calibración del juez** | Si un modelo candidato sirve de juez | 42 respuestas etiquetadas a mano sobre ES2015 | Kappa y otras cinco comprobaciones ([documento 09](09-jss-modelos-y-justificacion.md), §4) | Seis requisitos fijados antes de correr ([`config/experiments.toml`](../../config/experiments.toml) `[judge.calibration]`) | Doc. 06 §5–6; [notebook 05](../../notebooks/05-jss-seleccion-juez.ipynb) | **Medida**: `gpt-oss:20b` cumple todos; kappa 0,951 |
| **Viabilidad de E3** | Si habrá suficientes relaciones reales para sostener el estrato que prueba la tesis | 11 pares candidatos adjudicados de desarrollo | Proporción de relaciones reales; IC de Wilson; proyección a evaluación | E3 exige ≥ 25 preguntas. Provisional | Doc. 06 §7–8; D12; [notebook 01](../../notebooks/01-jss-viabilidad-e3.ipynb) | **Medida**: 45,5 % (5/11), IC [21,3 – 72,0 %]; proyección ≈ 37 relaciones, IC [17 – 58] |
| **Potencia del criterio D16** | Con 25 preguntas, qué tan seguido el criterio detecta una mejora real | Simulación con datos sintéticos | 1.000 experimentos simulados por escenario | Informativa; no es un umbral | D17; [ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md); [notebook 10](../../notebooks/10-jss-potencia-criterio-d16.ipynb); `experiments/power.py` | **Medida** (sintética): 57,5 % para +0,15 y 79,5 % para +0,20 (n = 25, base 0,5) |

## 4. Las métricas, objetivo por objetivo

### 4.1 OE1: el conjunto de referencia y su confiabilidad

**Qué se mide.** Antes de medir a la máquina hay que medir a las personas. OE1 construye el
conjunto de referencia (14 series, 56 reuniones, 343 decisiones) y debe demostrar que dos
personas lo anotan de forma consistente. El documento 01 muestra que dos equipos expertos
obtuvieron un kappa negativo anotando decisiones sobre este mismo corpus; por eso el
proyecto **mide** la confiabilidad y no la supone.

**Cómo se mide.** Cuatro series de control (ES2016, IS1003, TS3005 y ES2008), que son 4 de las
11 series de evaluación (36,4 %; el mínimo exigido es 25 %), se anotan por separado por dos
personas y se calcula un kappa **por eje**: existencia (¿hay relación?), tipo (¿cuál?) y
dirección (¿cuál revisa a cuál?). Dos series de desarrollo (ES2015 y TS3009) se usan solo para
calibrar a las personas que anotan. Los tres kappa no se combinan, porque es más fácil coincidir
en que existe una relación que en su tipo exacto, y una sola cifra ocultaría dónde está el
desacuerdo. Todo desacuerdo lo resuelve una tercera persona
(adjudicación) que deja escrita la razón.

**Cómo leer el resultado.** No hay umbral de aceptación: los anotadores no deben sentirse
obligados a coincidir, porque entonces se mediría el esfuerzo de ponerse de acuerdo y no el
acuerdo real. Las bandas de Landis y Koch (0,41–0,60 moderado, 0,61–0,80 sustancial, etc.)
son solo una ayuda de lectura. Un kappa bajo se reporta como hallazgo, junto con los
desacuerdos que lo explican.

**Lo medido hasta ahora** es solo diagnóstico: la calibración sobre ES2015 dio un kappa de
estado de 0,094 (13 de 29 filas en acuerdo), porque la guía no tenía un criterio de umbral;
se corrigió la guía y se recalibra sobre TS3009 antes de tocar una serie de control (notebook
04; documento 06, §5–6). Esa cifra no se reporta como resultado.

### 4.2 El filtro léxico y su recall

**Qué se mide.** Leer los 3.071 pares posibles de decisiones entre reuniones no es viable, así
que un filtro léxico selecciona 92 pares candidatos (la regla y su justificación están en el
[documento 07](07-jss-analisis-exploratorio.md), §7). La pregunta es **qué relaciones reales
dejó fuera**. Mientras no se mida, 92 es una cota superior de lo que la anotación puede
encontrar.

**Cómo se mide (Tarea C).** Se anotan 50 pares rechazados por el filtro en cada una de cuatro
series (IS1004, ES2016, IS1003, TS3005; documento 07, §7.5); toda relación real entre ellos es
un falso negativo. El **recall** es la proporción de relaciones reales que el filtro deja
pasar. Se reporta por sitio de grabación y en conjunto, con intervalo bootstrap, en la forma "el
filtro recuperó N de M relaciones en una muestra aleatoria de pares rechazados" (manual de
anotación, §5).

**Cómo leer el resultado.** No hay umbral. La cifra dice cuánto se perdió y si la pérdida es
pareja entre sitios; una pérdida alta no invalida el conjunto de referencia, pero obliga a
declararlo como limitación.

**Estado.** La muestra está generada y **sin anotar**; no hay cifra. En el código existe el
muestreo, y el cálculo del recall se hará con el intervalo bootstrap general.

### 4.3 OE2: la extracción automática

**Qué se mide.** Qué tan bien la máquina reencuentra las decisiones de la referencia
(precisión, cobertura y F1) y, sobre las relaciones, qué tan bien acierta su tipo y su
dirección.

**Cómo se mide.** Para decidir si una decisión extraída es "la misma" que una de la
referencia hace falta una regla fija (`docs/protocols/alignment.md`): se consideran
candidatas las parejas cuya similitud supera un umbral τ; se empareja una a una de la mejor
manera global posible (algoritmo húngaro, no vecino más cercano); y la regla automática se
contrasta con un emparejamiento manual de al menos 100 pares (concordancia ≥ 0,80). Como
elegir un único τ permitiría escoger el más favorable, **el F1 se reporta como curva** sobre
la grilla 0,50 a 0,90. Dos reglas provisionales de puntuación (ámbito de la alineación y rol
del hablante) se confirmarán con la primera extracción real (documento 06, §1).

**Cómo leer el resultado.** Se leen la curva completa y si el orden entre condiciones cambia a
lo largo de τ; si cambia, se declara. Cada corrida se repite al menos tres veces y se reporta
media y dispersión, porque la extracción con un modelo de lenguaje no es determinista. **No
existe un criterio de éxito ni una regla para elegir τ** (ver decisión abierta A).

Un riesgo ya observado: en una prueba sobre ES2015 con OpenKOS 0.5.2, la máquina extrajo 4
objetos Decision frente a 29 en la anotación adjudicada. Es una serie y una corrida con una
versión que se está corrigiendo (documento 06, §7–8), pero anticipa una cobertura baja.

### 4.4 OE3: la utilidad funcional (Experimento B)

**Qué se mide.** Las tres condiciones responden el mismo banco de preguntas, en cuatro
estratos: E1 (hecho puntual, donde se espera paridad), E2 (estado vigente), E3 (evolución de
una decisión: el estrato que prueba la tesis) y E4 (sin respuesta en el material). El mínimo
es de 25 preguntas por estrato; E3 admite hasta 40.

**Cómo se mide.** Las respuestas (al menos unas 900: 100 preguntas como mínimo × 3
condiciones × 3 corridas; hasta 115 preguntas si E3 llega a 40) las califica un juez
automático, `gpt-oss:20b`. Se eligió con una prueba propia sobre 42 respuestas de ES2015
etiquetadas a mano, con seis requisitos fijados antes de correr (acuerdo con las personas,
estabilidad ante cambios de orden y de semilla, exactitud en E4, formato válido y no premiar la
verbosidad); cumplió todos (kappa 0,951). El detalle de la elección está en el
[documento 09](09-jss-modelos-y-justificacion.md), §4. Como protección adicional, una persona
vuelve a juzgar el 20 % de las respuestas del experimento y la concordancia debe alcanzar
kappa ≥ 0,70 **por etiqueta**:

- Si falla la **corrección de respuesta**, se descarta el juicio automático de la métrica
  principal y se reporta solo la evaluación humana.
- Si falla el **soporte de evidencia**, esa métrica se reporta solo con evaluación humana o
  marcada como no confiable; no afecta a la métrica principal.

Las métricas secundarias se leen así:

- **Soporte de evidencia**: ¿cada afirmación está respaldada por la transcripción?
- **Citación correcta**: ¿al menos una fuente citada contiene la evidencia marcada por las
  personas? Se informa además la precisión de la citación, que deja a la vista a quien cita
  de más (ADR 0009).
- **Corrección del rechazo (E4)**: ¿se abstiene el sistema donde no hay respuesta?
- **Costo amortizado**: ¿a partir de cuántas consultas se recupera la inversión de construir
  la base?

**Cómo leer el resultado.** Todo resultado lleva su intervalo bootstrap del 95 %, y ninguna
conclusión se apoya en diferencias que caigan dentro de él (propuesta §5.0). Todas las
métricas secundarias son descriptivas: ninguna decide el éxito.

La limitación de la calibración del juez (el identificador de cada respuesta dejaba ver cómo
se había generado, así que el acuerdo podría estar algo inflado) se declara en el
[documento 09](09-jss-modelos-y-justificacion.md), §4; la verificación humana del 20 % es la
salvaguarda.

### 4.5 OE4: la atribución del error

**Qué se mide.** Cuando C2 responde mal, en qué etapa nació el error: **extracción** (el hecho
quedó mal escrito en la base o no quedó), **recuperación** (existía y no se encontró) o
**síntesis** (se encontró y la respuesta lo contradice). Las reglas son fijas y se aplican en
ese orden, de modo que cada error cae en una sola categoría.

**Cómo leer el resultado.** La cifra principal es la proporción de errores atribuible a
extracción. Es un resultado descriptivo: dice dónde conviene invertir, no si el proyecto
funcionó. Para que sirva, la comparación con C3 (base construida por personas, sin errores de
extracción) separa el costo de los errores de la máquina del valor de la idea.

## 5. Por qué la diferencia pareada y no la superposición de intervalos

La redacción original de D16 (13 de octubre) pedía que el intervalo de C2 quedara por encima
del de C1 sin solaparse. Se enmendó el 15 de octubre (D17, ADR 0010), antes de que existiera
cualquier corrida de evaluación, porque con las 25 preguntas mínimas de E3 esa lectura casi
nunca concluye aunque la mejora sea real. Una simulación con datos sintéticos (notebook 10;
1.000 experimentos por escenario) dio, con n = 25, exactitud base de C1 de 0,5 y dificultad
compartida moderada:

| Mejora verdadera de C2 sobre C1 | Criterio pareado (vigente) | No solapamiento (robustez) |
|---|---|---|
| +0,15 | 57,5 % | 10,4 % |
| +0,20 | 79,5 % | 27,8 % |

Con 40 preguntas, el criterio pareado sube a 75,7 % (+0,15) y 93,8 % (+0,20). Los falsos
positivos (cuando no hay mejora real) son de a lo más 4,5 % para el criterio pareado y 0,8 %
para el de no solapamiento. Es una simulación: dice cuánta potencia tiene el criterio, no
cuánto mejorará C2.

## 6. Cómo sabremos si el experimento tuvo éxito

**El criterio (D16 enmendada por D17), en palabras llanas.** Se mira una sola métrica, en un
solo estrato, para una sola comparación: la **corrección de respuesta** en las preguntas de
**evolución (E3)**, de **C2 frente a C1**. Para cada pregunta se calcula cuánto mejor o peor
le fue a C2 que a C1 (promediando las corridas de cada pregunta). Con esas diferencias se
construye un intervalo bootstrap del 95 % de la diferencia promedio.

Hay tres desenlaces posibles:

| Desenlace | Condición | Qué significa | Qué no significa |
|---|---|---|---|
| **Hipótesis respaldada** | El intervalo está **completamente por encima de 0** | Con los datos disponibles, C2 responde mejor que C1 las preguntas de evolución | No dice cuánto mejor, ni que valga en otros dominios o idiomas (fuera de alcance, propuesta §7) |
| **No concluyente** | El intervalo **incluye el 0** | Los datos no permiten afirmar diferencia; puede ser que no la haya o que falte potencia | **Nunca se reporta como éxito**, ni tampoco como prueba de que C2 no sirve |
| **Contraria** | El intervalo está **completamente por debajo de 0** | Con los datos disponibles, C2 responde peor que C1 | Se reporta tal cual y se explica con la atribución de error (OE4) |

Dos precisiones sobre cómo está escrito el criterio en el código: el veredicto
`supported` se emite solo si el límite inferior del intervalo es mayor que 0, y cualquier otro
caso se marca `inconclusive` (`experiments/analysis.py`, `_paired`; la cifra de robustez la
calcula `intervals_disjoint_above`); la distinción entre
"no concluyente" y "contraria" la hace quien lea el intervalo, porque el código no emite una
etiqueta específica para el segundo caso.

**Cifra de robustez.** Además se informa si los intervalos independientes de C2 y de C1 se
solapan. Acompaña al veredicto y no lo reemplaza: si el criterio pareado respalda la
hipótesis y los intervalos independientes no se solapan, la conclusión es más sólida; si solo
la respalda el pareado, es la lectura prevista con 25 preguntas.

**Qué no entra al criterio.** Precisión, cobertura y F1; exactitud de tipo y de dirección;
soporte de evidencia; citación; corrección del rechazo; costo amortizado; los estratos E1, E2
y E4; y la comparación de C2 con C3 son secundarios y descriptivos (D16). Un buen F1 de OE2 no
compensa un resultado no concluyente en E3, ni al revés.

**Condiciones previas para que el veredicto cuente.** Que el kappa de corrección de respuesta
entre juez y personas alcance 0,70 (si no, ese veredicto se reporta solo con evaluación
humana); que E3 alcance el tamaño mínimo (ver decisión abierta C); y que se fije una versión
publicada de OpenKOS antes de tocar una serie de evaluación (documento 06, §7–8).

## 7. Decisiones abiertas

Lo que sigue **se declara, no se decide**: son puntos que el equipo debe resolver. Para cada
uno se indica dónde se manifiesta, las opciones con su contrapartida y qué bloquea.

### A. No hay criterio de éxito para OE1 y OE2, ni regla para elegir τ

- **Dónde se ve.** D16 define el éxito solo para OE3/E3. En OE1 el kappa se reporta "sin
  umbral por diseño" (documento 06, §1); en OE2 el F1 es una curva sobre τ sin regla de
  lectura ni de selección (propuesta §5.4; documento 03, criterio de cumplimiento de OE2:
  "reportados como curva sobre τ").
- **Opciones.**
  1. *Dejarlo descriptivo* (estado actual). Evita fijar umbrales sin datos, pero el lector
     no sabe qué F1 o kappa se consideraría "bueno".
  2. *Fijar rangos de lectura antes de ver resultados* (por ejemplo, bandas de F1 o el
     criterio de Landis y Koch). Da una referencia, a costa de introducir cortes arbitrarios.
  3. *Fijar una regla de selección de τ* (por ejemplo, reportar el τ de máximo F1 y declararlo
     optimista, o el τ que maximiza la concordancia con el emparejamiento manual). Da un número
     único comparable, pero es la elección que la curva buscaba evitar.
- **Qué bloquea.** No bloquea correr nada. Afecta cómo se resume OE2 en el informe y qué se
  responde si se pregunta "¿la extracción fue buena?".

### B. C3 frente a C2 y C1 es solo descriptivo

- **Dónde se ve.** D16 lista "C2 frente a C3" entre las métricas secundarias; el código
  calcula las comparaciones C2–C1 y C2–C3 con la misma maquinaria (`SECONDARY_PAIRS`), pero
  solo la primera tiene criterio. No hay regla para leer C3 frente a C1.
- **Opciones.**
  1. *Mantenerlo descriptivo.* Simple y coherente con D16, pero la atribución del valor de la
     base (C1→C3) y del costo de los errores de la máquina (C3→C2) quedaría sin regla.
  2. *Prerregistrar una regla de lectura* (por ejemplo, el mismo criterio pareado en E3).
     Permite afirmar el valor de la base, pero abre un segundo contraste (ver decisión F).
- **Qué bloquea.** Nada inmediato. Condiciona cuánto puede afirmar la conclusión sobre el
  aporte de la base frente al de la extracción.

### C. Qué hacer si E3 tiene menos de 25 preguntas

- **Dónde se ve.** Tres textos no coinciden. La propuesta (§7) plantea ampliar a las 18 series
  de reserva o reformular E3 como análisis de casos, y deja la decisión abierta. El umbral del
  documento 06 (§1) dice que E3 "se reformula como análisis de casos". La decisión D12 dice
  que, si E3 no alcanza 25 con las once series de evaluación, "se reporta el número real y no
  se rellena el cupo". La estimación (notebook 01) es de ≈ 37 relaciones con IC [17 – 58]: el
  valor central alcanza; la cota inferior no.
- **Opciones.**
  1. *Ampliar con series de reserva.* Conserva la prueba cuantitativa de la hipótesis, pero
     suma horas de anotación (≈ 10–12 h para OE1 ya comprometidas, según la propuesta, §7) y obliga a declarar que el
     tamaño se fijó después de ver un resultado parcial.
  2. *Análisis de casos.* No suma horas y es defendible como aporte descriptivo, pero deja la
     hipótesis sin prueba cuantitativa en el único estrato diseñado para probarla.
  3. *Reportar el número real de preguntas* (D12) *y aplicar el criterio con la potencia que
     resulte.* No requiere trabajo adicional, pero con n < 25 la potencia baja del 57,5 %
     calculado (notebook 10) y un resultado no concluyente sería probable.
- **Qué bloquea.** La adjudicación de al menos una serie de evaluación entrega el dato que
  permite decidir; hasta entonces el tamaño de E3 es una proyección. Bloquea cerrar el
  diseño del Experimento B.

### D. No hay umbral para el recall del filtro léxico

- **Dónde se ve.** Documento 06, §2, y manual de anotación, §5: se reporta la cifra con su
  intervalo, sin regla de aceptación. La muestra aún no está anotada.
- **Opciones.**
  1. *Sin umbral* (estado actual). Honesto con lo desconocido, pero no define qué recall haría
     dudar de la cota de 92 pares.
  2. *Fijar una regla de reacción antes de anotar* (por ejemplo, si el recall por sitio queda
     bajo cierto valor, ampliar el filtro y repetir la anotación de candidatos). Da una
     acción clara, a costa de comprometer horas de anotación que hoy no están presupuestadas.
- **Qué bloquea.** No bloquea anotar la muestra. Sí condiciona qué se hace con el resultado,
  y cualquier cambio del filtro invalida los candidatos ya generados (`BLOCKER_VERSION`).

### E. `agreement_meets_threshold` usa 0,60 y los documentos dicen "sin umbral"

- **Dónde se ve.** `src/afg/annotation/agreement.py` define
  `agreement_meets_threshold(kappa, threshold=0.60)`, con el comentario de que es un corte
  convencional (Landis y Koch) y no un umbral de la tesis. Los documentos 03 y 06 y el
  manual dicen que el kappa de anotación no tiene umbral. La función solo se usa en una
  prueba (`tests/test_annotation.py`); no está conectada a ningún informe.
- **Opciones.**
  1. *Eliminar la función o dejarla marcada como auxiliar*, para que el código no sugiera un
     umbral que el diseño rechaza.
  2. *Adoptar 0,60 como regla de lectura* y actualizar los documentos. Coherente con el
     código, pero contradice la decisión de no obligar a coincidir (documento 06, §1).
- **Qué bloquea.** Nada, mientras la función no se use para decidir. Conviene resolverlo antes
  de reportar kappas para evitar una lectura ambigua.

### F. No hay corrección por comparaciones múltiples

- **Dónde se ve.** Solo una comparación tiene criterio (C2 − C1 en la corrección de respuesta
  de E3), así que el criterio principal no la necesita. Pero el análisis calcula muchas
  comparaciones descriptivas (dos pares de condiciones, cuatro estratos más el total, dos
  métricas), cada una con su intervalo del 95 %. No se busca ni se declara una corrección
  (por ejemplo, Bonferroni o Holm) en la documentación.
- **Opciones.**
  1. *No corregir y declararlo*: las comparaciones secundarias se presentan como
     exploratorias; con tantos intervalos del 95 %, alguno excluirá el 0 por azar.
  2. *Corregir las comparaciones secundarias.* Evita falsos hallazgos, a costa de intervalos
     más anchos con muestras ya pequeñas.
- **Qué bloquea.** No bloquea el criterio principal. Condiciona cómo se redacta cualquier
  afirmación derivada de los resultados secundarios.

### G. La propuesta no menciona D16

- **Dónde se ve.** `docs/propuesta.md` no contiene el criterio de éxito (ni D16 ni D17):
  solo dice que ninguna conclusión se apoyará en diferencias dentro de los intervalos
  (§5.0). D16 vive en el documento 06 y en `docs/decisions/README.md`.
- **Opciones.**
  1. *Actualizar la propuesta* para incorporar el criterio, de modo que el documento de
     referencia del proyecto lo contenga. Elimina la brecha, pero reabre un documento que se
     entregó.
  2. *Mantenerla como estaba* y declarar que la metodología (documento 06) la complementa.
     Evita tocar el documento entregado, pero el criterio de éxito no figura en la propuesta.
- **Qué bloquea.** Nada técnico. Afecta la consistencia entre lo prerregistrado y lo
  entregado al curso, y el pre-informe (§5–6) que debe citarlo.
