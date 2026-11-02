# Métricas y criterio de éxito

| | |
|---|---|
| **Documento** | 08 — Métricas y criterio de éxito |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 7.0 |
| **Fecha** | 2026-11-02 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-10-15 | Versión inicial. Reúne en un solo lugar qué se mide, sobre qué objeto, cómo se calcula, qué umbral o intervalo aplica y cómo se sabrá si el experimento tuvo éxito; declara las decisiones que siguen abiertas. No fija ninguna cifra ni regla nueva: cada dato remite al documento, ADR, configuración o notebook donde ya está definido. | Retroalimentación del profesor: faltaba tener claras las métricas del proyecto. El material del curso pide métricas aunque sean preliminares, como línea base (pre-informe del curso, p. 12, pregunta frecuente 5). |
| 1.1 | 2026-10-15 | Se usan los nombres estándar de métricas y técnicas sin traducir (ground truth, precision, recall, accuracy, LLM-as-a-judge, filtro léxico (*blocking*)). | Convención del equipo: los nombres de métricas y técnicas no se traducen. |
| 1.2 | 2026-10-15 | Se agrega la sección «Trazabilidad», con las funciones, pruebas, notebooks y decisiones en que se apoya cada métrica. No cambia ninguna cifra, decisión ni sección anterior. | Auditoría de gobernanza del 2026-10-15: los documentos 06 a 09 no tenían la sección de trazabilidad que sí tienen los documentos 01 a 05. |
| 1.3 | 2026-10-15 | La sección E de decisiones abiertas pasa a resuelta: la función `agreement_meets_threshold` se eliminó del código. No cambia ninguna cifra ni métrica. | Corrección de código del 2026-10-15 (rama `fix/auditoria-codigo`): el código sugería un umbral de kappa que el diseño rechaza. |
| 2.0 | 2026-11-01 | §4.1 y la tabla de métricas pasan de «series de control pendientes» a los kappas medidos de la Fase 2: existencia 0,783 (37 pares), tipo 0,554 (18 pares), dirección indefinida (acuerdo total). | Las cuatro series de control quedaron adjudicadas (notebook 18, §6.1; `reports/tables/agreement-pooled.csv`). Detalle en el [documento 10](10-jss-confiabilidad-de-la-referencia.md). |
| 3.0 | 2026-11-01 | C1 pasa a ser un RAG convencional, así que el contraste C1 frente a C2/C3 se lee como el valor del sistema compilado frente a un RAG convencional, que no puede repartirse entre representación y etapa de respuesta. La tasa de respuestas confiadas pero desactualizadas (H4) se mide entre las preguntas que cada condición responde, y la abstención se reporta aparte como corrección del rechazo. No cambian el criterio de éxito (D16/D17), las métricas ni las cifras. | Decisión del 2026-11-01 ([ADR 0014](../decisions/0014-adr-c1-como-rag-convencional.md)). |
| 4.0 | 2026-11-01 | Se corrigen cuatro afirmaciones que habían quedado atrás. (1) τ sí tiene regla de selección: el ADR 0012 lo fijó el 2026-10-19 (principal 0,70; 0,75 y 0,80 de sensibilidad), y lo que sigue sin existir es un criterio de éxito para OE1 y OE2 (§4.3 y decisión abierta A, que cambia de título). (2) La versión de OpenKOS está fijada en la 0.7.0, así que el riesgo observado en la extracción (§4.3) se actualiza: con la 0.7.0 la máquina extrae entre 69 y 71 decisiones por corrida en ES2015 frente a 27 de la referencia adjudicada, lo que anticipa una precision baja más que un recall bajo (antes: 4 objetos con la 0.5.2). (3) La muestra de *recall* del filtro léxico (§4.2 y tabla de métricas) ya no está «sin anotar»: tres de las cuatro muestras (ES2016, IS1003 y TS3005, 50 pares cada una) tienen anotación y falta la de IS1004 (#203) y la función que calcula el *recall* (#205). (4) Las referencias al documento 09 siguen su numeración actual (§5 a §7 para las condiciones, §6.3 para el LLM-as-a-judge). | ADR 0012 (τ) y ADR 0006, enmienda del 2026-11-01 (versión); extracción repetida con la 0.7.0 ([notebook 19](../../notebooks/19-jss-modelos.ipynb), §1.4); archivos `data/processed/relations/*.recall-sample.gv.csv` de ES2016, IS1003 y TS3005. |
| 4.1 | 2026-11-01 | El intervalo del *recall* del filtro léxico pasa de bootstrap a Wilson al 95 %: con 50 pares por serie es esperable no hallar ningún falso negativo, y en ese caso el bootstrap da [0; 0], una certeza que la muestra no tiene. La función del cálculo está lista (#205) y la cifra preliminar, con tres de las cuatro muestras, está en el notebook 18, §8. | Decisión de jss del 2026-11-01; manual de anotación, §5. |
| 5.0 | 2026-11-02 | La métrica de relaciones de OE2 pasa de «Accuracy de tipo y de dirección, pendiente» a existencia, tipo y dirección con el diseño del ADR 0016 (principal de extremo a extremo y condicionada; sensibilidades de tipo estricto y de dirección desconocida excluida), con su medición de desarrollo (§4.3). El estado del recall del filtro léxico (§4.2) deja de decir que falta la función (#205). | [ADR 0016](../decisions/0016-adr-relaciones-temporales-de-openkos.md) (issue #96) y [notebook 22](../../notebooks/22-jss-relaciones-temporales-openkos.ipynb). El §4.2 había quedado atrás de la versión 4.1, que ya declaraba lista la función (`annotation/recall.py`). |
| 5.1 | 2026-11-02 | La medición de desarrollo de las relaciones de OE2 incorpora IS1004 (§4.3 y tabla de métricas), que antes figuraba sin puntuar: se puntúa con la referencia de su único anotador y su traducción automática. Pasan a ser 9 relaciones de oro en tres series. | Issue #229, issue #204 y [notebook 22](../../notebooks/22-jss-relaciones-temporales-openkos.ipynb). |
| 5.2 | 2026-11-02 | Se registra la concordancia del juez de τ con una persona (50 pares) y su consecuencia para leer las métricas de alineación del Experimento A: con τ = 0,70 son un piso conservador. Se mantiene τ = 0,70; no cambian umbrales ni criterios de éxito. | Acuerdo de 43 de 50 pares (86 %), kappa 0,716 (IC 95 % de 0,520 a 0,880); los 7 desacuerdos son del juez en «no» y la persona en «sí»; por debajo de 0,70 el juez dice «sí» en el 21 % de los pares y la persona en el 42 % ([ADR 0012](../decisions/0012-adr-umbral-tau-del-experimento-a.md), [notebook 17](../../notebooks/17-jss-tau-referencia-en.ipynb) §8). Evidencia limitada: 24 pares bajo el umbral, una sola persona que además adjudica y mantiene el proyecto, y solo ES2015 y TS3009. |
| 6.0 | 2026-11-02 | La tasa de respuestas confiadas pero desactualizadas (H4) recibe su definición operativa: entre las preguntas E3 respondidas (sin abstención), la proporción cuya respuesta el juez marca como desactualizada, es decir, que presenta como vigente el estado anterior de la decisión, declarado por quien escribe la pregunta en la columna nueva `superseded_answer` del banco. La comparación es la diferencia pareada C1 − C2 y C1 − C3, y H4 se respalda si el intervalo bootstrap del 95 % de la diferencia queda por encima de 0. La tasa de respuestas incorrectas entre las respondidas se informa como cota superior. El campo del juez se valida con el acuerdo juez-humano, con el mismo umbral de kappa que la corrección. No cambian el criterio de éxito (D16/D17) ni las demás métricas. | Decisión del 2026-11-02 ([ADR 0017](../decisions/0017-adr-medicion-de-h4.md), issue #241): los documentos fijaban el denominador de H4 pero no cómo reconocer una respuesta desactualizada, y ni el juez ni el banco lo distinguían. |
| 7.0 | 2026-11-02 | H2 y H3 reciben su definición operativa y sus reglas de lectura, fijadas antes de los resultados de evaluación. H2 se mide en el Experimento B: la diferencia entre la brecha de corrección C3 − C2 en E3 (relaciones) y en E1 (decisiones; E2 no entra), con bootstrap independiente por estrato; se respalda si el intervalo del 95 % queda por encima de 0, es contraria si queda por debajo y no es calculable sin C3, C2 o alguno de los estratos. La brecha de extracción del Experimento A (1 menos el recall de relaciones frente a la de decisiones) queda como cifra complementaria y declarada sesgada. H3 se mide en el Experimento A entre los enlaces detectados (error de dirección frente a error de tipo, con intervalos que no se solapan); su cláusula de escala de modelo no se mide. Antes la lectura de H2 que sugería el §4.3 era la cifra condicionada del Experimento A. No cambian el criterio de éxito (D16/D17) ni las demás métricas. | Decisión del 2026-11-02 ([ADR 0018](../decisions/0018-adr-medicion-de-h2-y-h3.md), issue #242): los documentos nombraban las hipótesis pero no decían sobre qué datos se calcula la brecha ni cuándo se respaldan. C3 y C2 son condiciones del Experimento B, y la brecha es el costo de los errores de extracción. |
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
  construye el ground truth (la referencia de decisiones marcadas a mano), anotado por personas. OE2 mide qué tan bien extrae
  decisiones la máquina (Experimento A). OE3 compara la utilidad de tres condiciones al
  responder preguntas (Experimento B). OE4 atribuye cada error a su etapa.
- **C1, C2 y C3.** Las tres condiciones que se comparan. C1 busca fragmentos de texto y
  redacta con ellos, con una instrucción genérica y una sola llamada (un RAG convencional); C2
  consulta una base de decisiones construida por la máquina; C3
  consulta la misma base construida por personas ([documento 09](09-jss-modelos-y-justificacion.md), §5).
- **Estrato.** Grupo de preguntas del mismo tipo: E1 (hecho puntual), E2 (estado vigente), E3
  (evolución de una decisión, el que prueba la tesis) y E4 (sin respuesta en el material).
- **τ (tau).** Umbral de similitud a partir del cual una decisión extraída por la máquina y una
  de la referencia se consideran candidatas a ser la misma (§4.3).
- **OpenKOS.** Motor de código abierto con el que se construye y consulta la base de decisiones
  de C2 y C3 ([documento 09](09-jss-modelos-y-justificacion.md), §6.4).

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
  no puede responder (estrato E4). Aquí sería un error. La abstención no cuenta como respuesta
  confiada pero desactualizada: esa tasa (H4) se mide entre las preguntas que cada condición
  efectivamente responde, y las abstenciones se reportan aparte como corrección del rechazo.

Cada métrica de este documento mide una de esas facetas: si la respuesta acierta (corrección),
si lo que dice tiene respaldo en la transcripción (soporte de evidencia), si la cita apunta al
lugar correcto (citación correcta) y si el sistema sabe callar cuando corresponde (corrección
del rechazo).

## 2. Cómo leer este documento: seis ideas

### 2.1 Umbrales de validez y criterio de éxito son cosas distintas

El proyecto usa dos clases de regla que conviene no mezclar.

- Un **umbral de validez** responde: *¿se puede confiar en la medición?* Por ejemplo, si el
  LLM-as-a-judge (un segundo modelo que califica las respuestas) coincide poco con las
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

### 2.4 Precision, recall y F1

Miden la extracción de decisiones (OE2). Ejemplo ilustrativo: la referencia tiene 16 decisiones
reales y la máquina extrae 10, de las cuales 8 son reales y 2 son sobras.

- **Precision**: de lo extraído, qué parte era correcta. 8 de 10 = 0,80.
- **Recall**: de lo que existe, qué parte se encontró. 8 de 16 = 0,50.
- **F1**: un solo número que combina ambas y baja si cualquiera es baja:
  2 × 0,80 × 0,50 / (0,80 + 0,50) ≈ 0,62.

Una máquina que extrae poco y acierta siempre tiene precision alta y recall bajo; el F1
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
| **Kappa de anotación** (existencia, tipo, dirección) | Cuánto coinciden dos personas al marcar si dos decisiones se relacionan, cómo y en qué sentido | Series de control con doble anotación (4 de las 11 series de evaluación, 36,4 %; más 2 series de calibración de desarrollo) | Kappa de Cohen, un valor por cada uno de los tres ejes, nunca combinados | **Sin umbral de aceptación, por diseño.** Se reporta tal como salga; un kappa bajo es un hallazgo | Doc. 06 §1 y §5–6; manual de anotación §6; `annotation/agreement.py` | Medida en las cuatro series de control (Fase 2): existencia 0,783 (37 pares), tipo 0,554 (18 pares), dirección indefinida por acuerdo total (notebook 18, §6.1; documento 10) |
| **Recall del filtro léxico** (*blocking*) | Qué parte de las relaciones reales deja pasar el filtro que decide qué pares se anotan | 200 pares rechazados (50 por serie × IS1004, ES2016, IS1003, TS3005) | Relaciones reales halladas entre los rechazados, sobre el total muestreado; por sitio y en conjunto, con intervalo de Wilson al 95 % (no bootstrap: con cero hallazgos daría [0; 0]) | **Sin umbral.** Se reporta la cifra y su intervalo | Doc. 06 §2; manual de anotación §5; `annotation/blocking.py`; `config/annotation.toml` `[annotation.recall_sample]` | Muestras generadas; anotadas las de ES2016, IS1003 y TS3005 (50 pares cada una); la función del cálculo está lista (#205) y la cifra preliminar, con tres de cuatro muestras, está en el [notebook 18](../../notebooks/18-jss-anotacion-f2-adjudicacion.ipynb), §8; falta la muestra de IS1004 (#203) |
| **Precision, recall y F1** (OE2) | Qué tan bien la máquina encuentra las decisiones de la referencia | Decisiones extraídas por la máquina frente a las 343 de la referencia | Conteos de aciertos, sobras y faltantes tras el alineamiento (§4.3); F1 como **curva sobre τ** | Sin umbral ni criterio de éxito; curva con τ de 0,50 a 0,90 en pasos de 0,05 | Propuesta §5.4 y §5.6; [`docs/protocols/alignment.md`](../protocols/alignment.md); [`config/experiments.toml`](../../config/experiments.toml) `[alignment]` | Implementada. Pendiente de medir (no hay extracción real de evaluación) |
| **Existencia, tipo y dirección de las relaciones** (OE2) | Si la máquina encuentra las relaciones entre decisiones, acierta cuál es y cuál revisa a cuál | Relaciones adjudicadas de la Tarea B frente a las de `openkos revisions` | Precision, recall y F1 del enlace; fracción de relaciones con tipo (o sentido) igual a la referencia; se reportan por separado. Principal: de extremo a extremo, con «revierte» y «reemplaza» como una clase y la dirección desconocida como error; segunda cifra condicionada a la alineación; sensibilidades: tipo estricto y dirección desconocida excluida | Sin umbral | Propuesta §5.6; [ADR 0016](../decisions/0016-adr-relaciones-temporales-de-openkos.md); `evaluation/relations.py` | Implementada y medida solo en desarrollo (ES2015, IS1004, TS3009; [notebook 22](../../notebooks/22-jss-relaciones-temporales-openkos.ipynb)). Pendiente en evaluación |
| **Concordancia del alineamiento** | Si la regla automática que empareja decisiones coincide con el emparejamiento manual | Muestra de al menos 100 pares | Pares coincidentes entre ambos emparejamientos sobre la unión de pares emparejados | **≥ 0,80**; si no, se revisa la grilla de τ y se repite | Doc. 06 §1; [`docs/protocols/alignment.md`](../protocols/alignment.md); `evaluation/alignment.py` (`concordance`) | Implementada. Pendiente de medir |
| **Corrección de respuesta** (OE3) | Si la respuesta acierta frente a la referencia | Preguntas del banco; **métrica principal en el estrato E3** | Promedio por pregunta de las corridas calificadas por el LLM-as-a-judge; IC bootstrap | Ver criterio D16 (§6): IC de la diferencia pareada C2 − C1 por encima de 0 | Doc. 06 §1; D16 y D17 (`docs/decisions/README.md`); [ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md); `experiments/analysis.py` | Implementada. Pendiente de medir |
| **Soporte de evidencia** (OE3) | Si cada afirmación de la respuesta tiene respaldo en la transcripción | Preguntas del banco | Marca del LLM-as-a-judge por respuesta; promedio por pregunta | Secundaria y descriptiva. Verificación humana con su propia marca de confiable o no confiable (kappa ≥ 0,70) | Propuesta §5.6; [ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md) | Implementada. Pendiente |
| **Citación correcta** y **precision de la citación** (OE3) | Si la fuente citada contiene la evidencia de la pregunta; qué fracción de lo citado es pertinente | Respuestas a preguntas con respuesta (no E4) | Correcta si **al menos un** pasaje citado toca la evidencia; sin cita cuenta como falla. Precision = pasajes que aciertan / pasajes citados | Secundaria y descriptiva. Riesgo declarado: podría favorecer a C1, que cita fragmentos grandes | [ADR 0009](../decisions/0009-adr-regla-de-citacion-correcta.md); doc. 06 §1; `evaluation/citation.py` | Implementada. Pendiente |
| **Corrección del rechazo** (OE3) | Si el sistema sabe decir "no hay información" cuando no la hay | Estrato E4 (preguntas sin respuesta) | Fracción de preguntas E4 en que el sistema se abstiene | Secundaria y descriptiva | Propuesta §5.6; `experiments/analysis.py` | Implementada. Pendiente |
| **Respuestas desactualizadas entre las respondidas** (H4, OE3) | Si una respuesta E3 presenta como vigente el estado anterior de la decisión, y si C1 lo hace más que C2 y C3 | E3, solo respuestas sin abstención | Promedio por pregunta de la marca `outdated` del LLM-as-a-judge; diferencia pareada C1 − C2 y C1 − C3 con IC bootstrap | Secundaria y descriptiva. H4 se respalda si el IC de la diferencia queda por encima de 0. Marca verificada por una persona con el umbral de kappa de la corrección; la tasa de incorrectas entre las respondidas es la cota superior | [ADR 0017](../decisions/0017-adr-medicion-de-h4.md); `experiments/analysis.py`; `evaluation/judge.py` | Implementada. Pendiente |
| **Brecha C3 − C2 en relaciones frente a decisiones** (H2, OE3) | Si los errores de extracción cuestan más respuestas correctas en las preguntas de relación que en las de decisión | E3 (relaciones) y E1 (decisiones), preguntas juzgadas en C3 y en C2; E2 no entra | Diferencia de corrección C3 − C2 por pregunta, promedio por estrato; diferencia de brechas E3 menos E1 con bootstrap que remuestrea las preguntas de cada estrato por separado | Secundaria y descriptiva. H2 se respalda si el IC del 95 % queda por encima de 0, es contraria si queda por debajo, y no es calculable sin C3, C2 o alguno de los estratos | [ADR 0018](../decisions/0018-adr-medicion-de-h2-y-h3.md); `experiments/analysis.py` | Implementada. Pendiente en evaluación |
| **Dirección como modo de falla** (H3, OE2) | Si, entre los enlaces que la máquina detecta, la dirección falla más que el tipo | Enlaces detectados (aciertos de existencia) del Experimento A | Tasa de error de dirección (invertida o desconocida) y de tipo con intervalo de Wilson; modo más frecuente por conteo | Secundaria y descriptiva. H3 se respalda si el IC de la tasa de dirección queda por encima del de tipo. La cláusula de escala de modelo no se mide (extensión con `qwen3:32b`) | [ADR 0018](../decisions/0018-adr-medicion-de-h2-y-h3.md); `experiments/hypotheses.py` | Implementada. Solo en desarrollo (1 enlace detectado) |
| **Costo amortizado** (OE3) | Desde cuántas consultas compensa haber construido la base | C2 (y C3) frente a C1 | Menor *n* tal que `costo_compilación + n · costo_consulta_estructurada < n · costo_consulta_RAG` | Si la consulta estructurada no es más barata que la RAG, no hay punto de equilibrio y eso es un resultado | Propuesta §5.6; doc. 06 §7–8; `evaluation/amortization.py` | Implementada. Pendiente |
| **Recall@K de recuperación** | Si entre los K fragmentos recuperados está la evidencia | Solo la etapa de recuperación de C1 y C2 | Fracción de la evidencia de referencia que aparece entre los K recuperados | Sin umbral; se usa para ajustar C1 sobre ES2015 con una regla fijada antes de correr | Propuesta §5.4; [ADR 0007](../decisions/0007-adr-ajuste-c1-y-presupuesto-de-contexto.md); `config/experiments.toml` `[retrieval.tuning]` | Implementada y usada en desarrollo ([notebook 06](../../notebooks/06-jss-ajuste-c1.ipynb)) |
| **Atribución del error** (OE4) | En qué etapa nació cada respuesta fallida de C2 | Respuestas fallidas de C2 | Reglas fijas en orden: extracción, luego recuperación, luego síntesis | Cada error cae en una y solo una categoría; la proporción atribuible a extracción es la cifra principal | Doc. 03 (OE4); doc. 06 §7–8; `evaluation/attribution.py` | Implementada. Pendiente |
| **Concordancia LLM-as-a-judge–humano** | Si el LLM-as-a-judge coincide con las personas | 20 % de las respuestas juzgadas (una corrida sorteada por pregunta y condición), por etiqueta | Kappa de Cohen; siempre se informan también el acuerdo observado y la prevalencia | **Kappa ≥ 0,70** por etiqueta; kappa indefinido cuenta como «no cumple» | Doc. 06 §1 y §5–6; [ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md); `evaluation/judge_human_check.py` | Implementada. Pendiente sobre el Experimento B |
| **Calibración del LLM-as-a-judge** | Si un modelo candidato sirve de LLM-as-a-judge | 42 respuestas etiquetadas a mano sobre ES2015 | Kappa y otras cinco comprobaciones ([documento 09](09-jss-modelos-y-justificacion.md), §6.3) | Seis requisitos fijados antes de correr ([`config/experiments.toml`](../../config/experiments.toml) `[judge.calibration]`) | Doc. 06 §5–6; [notebook 05](../../notebooks/05-jss-seleccion-juez.ipynb) | **Medida**: `gpt-oss:20b` cumple todos; kappa 0,951 |
| **Viabilidad de E3** | Si habrá suficientes relaciones reales para sostener el estrato que prueba la tesis | 11 pares candidatos adjudicados de desarrollo | Proporción de relaciones reales; IC de Wilson; proyección a evaluación | E3 exige ≥ 25 preguntas. Provisional | Doc. 06 §7–8; D12; [notebook 01](../../notebooks/01-jss-viabilidad-e3.ipynb) | **Medida**: 45,5 % (5/11), IC [21,3 – 72,0 %]; proyección ≈ 37 relaciones, IC [17 – 58] |
| **Potencia del criterio D16** | Con 25 preguntas, qué tan seguido el criterio detecta una mejora real | Simulación con datos sintéticos | 1.000 experimentos simulados por escenario | Informativa; no es un umbral | D17; [ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md); [notebook 10](../../notebooks/10-jss-potencia-criterio-d16.ipynb); `experiments/power.py` | **Medida** (sintética): 57,5 % para +0,15 y 79,5 % para +0,20 (n = 25, base 0,5) |

## 4. Las métricas, objetivo por objetivo

### 4.1 OE1: el ground truth y su confiabilidad

**Qué se mide.** Antes de medir a la máquina hay que medir a las personas. OE1 construye el
ground truth (14 series, 56 reuniones, 343 decisiones) y debe demostrar que dos
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

**Lo medido.** La calibración sobre ES2015 dio un kappa de estado de 0,094 (13 de 29 filas
en acuerdo), porque la guía no tenía un criterio de umbral; se corrigió la guía y se recalibró
sobre TS3009 (notebook 04; documento 06, §5–6). Esa cifra es diagnóstica y no se reporta. Sobre
las cuatro series de control, los kappas que sí se reportan son existencia 0,783 (37 pares) y
tipo 0,554 (18 pares); la dirección no tiene kappa porque el acuerdo fue total (notebook 18,
§6.1). La lectura completa está en el [documento 10](10-jss-confiabilidad-de-la-referencia.md).

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
pareja entre sitios; una pérdida alta no invalida el ground truth, pero obliga a
declararlo como limitación.

**Estado.** Las cuatro muestras están generadas. Tres (ES2016, IS1003 y TS3005, 50 pares cada
una) ya tienen anotación; falta la de IS1004 (#203). La función que calcula el recall con ellas
existe (#205, `annotation/recall.py`, con intervalo de Wilson) y la cifra preliminar, con tres de
las cuatro muestras, está en el notebook 18, §8.

### 4.3 OE2: la extracción automática

**Qué se mide.** Qué tan bien la máquina reencuentra las decisiones de la referencia
(precision, recall y F1) y, sobre las relaciones, qué tan bien acierta su tipo y su
dirección.

**Cómo se mide.** Para decidir si una decisión extraída es "la misma" que una de la
referencia hace falta una regla fija (`docs/protocols/alignment.md`): se consideran
candidatas las parejas cuya similitud supera un umbral τ; se empareja una a una de la mejor
manera global posible (algoritmo húngaro, no vecino más cercano); y la regla automática se
contrasta con un emparejamiento manual de al menos 100 pares (concordancia ≥ 0,80). Como
elegir un único τ permitiría escoger el más favorable, **el F1 se reporta como curva** sobre
la grilla 0,50 a 0,90. Dos reglas provisionales de puntuación (ámbito de la alineación y rol
del hablante) se confirmarán con la primera extracción real (documento 06, §1).

**Relaciones temporales ([ADR 0016](../decisions/0016-adr-relaciones-temporales-de-openkos.md)).** Sobre las relaciones se puntúan tres cosas: la existencia
del enlace (precision, recall y F1), su tipo y su dirección. El valor principal es de extremo a
extremo (una relación cuyas decisiones no se alinearon cuenta como omitida), une «revierte» y
«reemplaza» en una clase y cuenta como error la dirección desconocida; la segunda cifra se condiciona
a las relaciones con ambas decisiones alineadas y es la que separa la extracción de relaciones de
la de decisiones. Las sensibilidades son el tipo estricto y la dirección desconocida excluida. Con esa cifra y la de decisiones, `a-report` calcula una brecha de extracción complementaria (no es H2, que se mide en el Experimento B) y la medición de H3 ([ADR 0018](../decisions/0018-adr-medicion-de-h2-y-h3.md)).
La medición de desarrollo ([notebook 22](../../notebooks/22-jss-relaciones-temporales-openkos.ipynb)) cubre ES2015 (tres corridas), IS1004 (una) y TS3009 (una); con 9 relaciones de
oro es solo una señal: casi todos los enlaces de la máquina caen sobre decisiones que no se alinean
con la referencia (1 de 75 en ES2015, 3 de 26 en TS3009 y 0 de 6 en IS1004 tienen sus dos decisiones alineadas), y
el único enlace de oro alineado que la máquina encontró, en TS3009, tiene tipo y dirección correctos. En IS1004, que se puntúa con la referencia de su único anotador y una traducción automática al inglés (#204, #229), el enlace de oro con ambas decisiones alineadas no se encontró.

**Cómo leer el resultado.** Se leen la curva completa y si el orden entre condiciones cambia a
lo largo de τ; si cambia, se declara. Cada corrida se repite al menos tres veces y se reporta
media y dispersión, porque la extracción con un modelo de lenguaje no es determinista. **No
existe un criterio de éxito para OE2** (ver decisión abierta A); τ sí está fijado: 0,70 como valor
principal, con 0,75 y 0,80 de sensibilidad ([ADR 0012](../decisions/0012-adr-umbral-tau-del-experimento-a.md)). El juez que respalda ese valor coincide con una persona en 43 de 50 pares (86 %, kappa 0,716) pero es más estricto que ella, así que el recall y el F1 de alineación con τ = 0,70 deben leerse como un piso conservador, en contra de la máquina.

Un riesgo ya observado: una primera prueba sobre ES2015 con OpenKOS 0.5.2 extrajo 4 objetos
Decision frente a 29 en la anotación adjudicada. Con la versión fijada (0.7.0), la máquina extrae
entre 69 y 71 decisiones por corrida frente a 27 de la referencia adjudicada ([notebook 19](../../notebooks/19-jss-modelos.ipynb),
§1.4). Es una serie y un modelo, pero anticipa una precision baja (decisiones de más) más que un
recall bajo.

### 4.4 OE3: la utilidad funcional (Experimento B)

**Qué se mide.** Las tres condiciones responden el mismo banco de preguntas, en cuatro
estratos: E1 (hecho puntual, donde se espera paridad), E2 (estado vigente), E3 (evolución de
una decisión: el estrato que prueba la tesis) y E4 (sin respuesta en el material). El mínimo
es de 25 preguntas por estrato; E3 admite hasta 40.

**Cómo se mide.** Las respuestas (al menos unas 900: 100 preguntas como mínimo × 3
condiciones × 3 corridas; hasta 115 preguntas si E3 llega a 40) las califica un LLM-as-a-judge,
`gpt-oss:20b`. Se eligió con una prueba propia sobre 42 respuestas de ES2015
etiquetadas a mano, con seis requisitos fijados antes de correr (acuerdo con las personas,
estabilidad ante cambios de orden y de semilla, accuracy en E4, formato válido y no premiar la
verbosidad); cumplió todos (kappa 0,951). El detalle de la elección está en el
[documento 09](09-jss-modelos-y-justificacion.md), §6.3. Como protección adicional, una persona
vuelve a juzgar el 20 % de las respuestas del experimento y la concordancia debe alcanzar
kappa ≥ 0,70 **por etiqueta**:

- Si falla la **corrección de respuesta**, se descarta el juicio automático de la métrica
  principal y se reporta solo la evaluación humana.
- Si falla el **soporte de evidencia**, esa métrica se reporta solo con evaluación humana o
  marcada como no confiable; no afecta a la métrica principal.

Las métricas secundarias se leen así:

- **Soporte de evidencia**: ¿cada afirmación está respaldada por la transcripción?
- **Citación correcta**: ¿al menos una fuente citada contiene la evidencia marcada por las
  personas? Se informa además la precision de la citación, que deja a la vista a quien cita
  de más (ADR 0009).
- **Corrección del rechazo (E4)**: ¿se abstiene el sistema donde no hay respuesta? C1 se
  abstiene respondiendo una frase fija; C2 y C3 lo deciden con la verificación de suficiencia
  de OpenKOS. Por eso las abstenciones se reportan aparte y la tasa de respuestas confiadas
  pero desactualizadas (H4) se calcula solo sobre las respondidas.
- **Respuestas desactualizadas entre las respondidas (H4, E3)**: ¿qué proporción de las
  respuestas E3 que da cada condición presenta como vigente el estado anterior de la decisión?
  Quien escribe la pregunta declara ese estado anterior en el banco (`superseded_answer`), el
  juez marca si la respuesta lo presenta como vigente, y se compara C1 con C2 y C1 con C3 pregunta
  a pregunta. H4 se respalda si el intervalo de la diferencia queda por encima de 0. La tasa de
  respuestas incorrectas entre las respondidas se informa al lado como cota superior, y una
  persona verifica la marca del juez con el mismo umbral de kappa que la corrección
  ([ADR 0017](../decisions/0017-adr-medicion-de-h4.md)).
- **Brecha C3 − C2 en relaciones frente a decisiones (H2, E3 y E1)**: para cada pregunta
  juzgada en C3 y en C2 se toma la diferencia de corrección C3 − C2; H2 es la brecha de E3
  (preguntas de relación) menos la de E1 (preguntas de decisión). E2 no entra, porque exige
  saber qué versión prevalece. El intervalo remuestrea por separado las preguntas de cada
  estrato; H2 se respalda si queda por encima de 0 y es contraria si queda por debajo
  ([ADR 0018](../decisions/0018-adr-medicion-de-h2-y-h3.md)).
- **Costo amortizado**: ¿a partir de cuántas consultas se recupera la inversión de construir
  la base?

**Cómo leer el resultado.** Todo resultado lleva su intervalo bootstrap del 95 %, y ninguna
conclusión se apoya en diferencias que caigan dentro de él (propuesta §5.0). Todas las
métricas secundarias son descriptivas: ninguna decide el éxito.

La limitación de la calibración del LLM-as-a-judge (el identificador de cada respuesta dejaba ver cómo
se había generado, así que el acuerdo podría estar algo inflado) se declara en el
[documento 09](09-jss-modelos-y-justificacion.md), §6.3; la verificación humana del 20 % es la
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
1.000 experimentos por escenario) dio, con n = 25, accuracy base de C1 de 0,5 y dificultad
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

**Qué no entra al criterio.** Precision, recall y F1; accuracy de tipo y de dirección;
soporte de evidencia; citación; corrección del rechazo; costo amortizado; los estratos E1, E2
y E4; y la comparación de C2 con C3 son secundarios y descriptivos (D16). Un buen F1 de OE2 no
compensa un resultado no concluyente en E3, ni al revés.

**Condiciones previas para que el veredicto cuente.** Que el kappa de corrección de respuesta
entre el LLM-as-a-judge y las personas alcance 0,70 (si no, ese veredicto se reporta solo con evaluación
humana); que E3 alcance el tamaño mínimo (ver decisión abierta C); y que se fije una versión
publicada de OpenKOS antes de tocar una serie de evaluación (cumplido: `==0.7.0`; documento 06, §7–8).

## 7. Decisiones abiertas

Lo que sigue **se declara, no se decide**: son puntos que el equipo debe resolver. Para cada
uno se indica dónde se manifiesta, las opciones con su contrapartida y qué bloquea.

### A. No hay criterio de éxito para OE1 y OE2

- **Dónde se ve.** D16 define el éxito solo para OE3/E3. En OE1 el kappa se reporta "sin
  umbral por diseño" (documento 06, §1); en OE2 el F1 es una curva sobre τ sin regla de
  lectura (τ sí está fijado, ADR 0012, con su concordancia juez-persona ya medida; propuesta §5.4; documento 03, criterio de cumplimiento de OE2:
  "reportados como curva sobre τ").
- **Opciones.**
  1. *Dejarlo descriptivo* (estado actual). Evita fijar umbrales sin datos, pero el lector
     no sabe qué F1 o kappa se consideraría "bueno".
  2. *Fijar rangos de lectura antes de ver resultados* (por ejemplo, bandas de F1 o el
     criterio de Landis y Koch). Da una referencia, a costa de introducir cortes arbitrarios.
  3. *Fijar una regla de selección de τ* (por ejemplo, reportar el τ de máximo F1 y declararlo
     optimista, o el τ que maximiza la concordancia con el emparejamiento manual). **Ya resuelta:**
     el ADR 0012 fijó τ principal = 0,70, con 0,75 y 0,80 de sensibilidad y la curva completa
     siempre al lado.
- **Qué bloquea.** No bloquea correr nada. Afecta cómo se resume OE2 en el informe y qué se
  responde si se pregunta "¿la extracción fue buena?".

### B. C3 frente a C2 y C1 es solo descriptivo

- **Dónde se ve.** D16 lista "C2 frente a C3" entre las métricas secundarias; el código
  calcula las comparaciones C2–C1 y C2–C3 con la misma maquinaria (`SECONDARY_PAIRS`), pero
  solo la primera tiene criterio. No hay regla para leer C3 frente a C1.
- **Opciones.**
  1. *Mantenerlo descriptivo.* Simple y coherente con D16, pero la atribución del valor del
     sistema compilado frente a un RAG convencional (C1→C3; no se reparte entre representación
     y etapa de respuesta, ADR 0014) y del costo de los errores de la máquina (C3→C2) quedaría sin regla.
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

### E. `agreement_meets_threshold` usaba 0,60 y los documentos dicen "sin umbral" (resuelto)

- **Dónde se veía.** `src/afg/annotation/agreement.py` definía
  `agreement_meets_threshold(kappa, threshold=0.60)`, un corte convencional (Landis y Koch) que
  no era un umbral de la tesis. Los documentos 03 y 06 y el manual dicen que el kappa de
  anotación no tiene umbral. La función solo se usaba en una prueba; no estaba conectada a
  ningún informe.
- **Resolución (2026-10-15).** Se eliminó la función y su prueba (rama `fix/auditoria-codigo`,
  commit `c9f6b63`), porque `config/annotation.toml` no define ningún umbral de kappa y el
  diseño no obliga a coincidir (documento 06, §1). El código ya no sugiere un umbral que el
  diseño rechaza.
- **Qué bloquea.** Nada.

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

---

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| Kappa de Cohen y acuerdo entre quienes anotan (OE1) | `src/afg/annotation/agreement.py`, `src/afg/evaluation/metrics.py` (`cohen_kappa`); `tests/test_agreement.py`, `tests/test_metrics.py` |
| Precision, recall y F1; exactitud de tipo y de dirección; intervalos Wilson y bootstrap | `src/afg/evaluation/metrics.py`; `tests/test_metrics.py` |
| Alineamiento de decisiones extraídas con las de referencia (OE2) | `src/afg/evaluation/alignment.py`, `src/afg/evaluation/scoring.py`; `tests/test_alignment.py`, `tests/test_scoring.py`; [`../protocols/alignment.md`](../protocols/alignment.md) |
| Citación correcta y precisión de las citas (OE3) | `src/afg/evaluation/citation.py`; `tests/test_citation.py`; [`../decisions/0009-adr-regla-de-citacion-correcta.md`](../decisions/0009-adr-regla-de-citacion-correcta.md) |
| Atribución del error a su etapa (OE4) y costo amortizado | `src/afg/evaluation/attribution.py`, `src/afg/evaluation/amortization.py`; `tests/test_attribution.py`, `tests/test_amortization.py` |
| Análisis del Experimento B: tasas, intervalos y diferencia pareada C2 − C1 | `src/afg/experiments/analysis.py`; `tests/test_experiment_b_analysis.py`; `afg experiment b-report` |
| Potencia del criterio D16 por simulación | `src/afg/experiments/power.py`; `tests/test_experiment_b_power.py`; [`../../notebooks/10-jss-potencia-criterio-d16.ipynb`](../../notebooks/10-jss-potencia-criterio-d16.ipynb) |
| Enmienda D17 y verificación humana del LLM-as-a-judge | [`../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md`](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md); `src/afg/evaluation/judge_human_check.py`; `tests/test_judge_human_check.py` |
| Umbrales y parámetros prerregistrados | [`../../config/experiments.toml`](../../config/experiments.toml) |
