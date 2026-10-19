# Metodología

| | |
|---|---|
| **Documento** | 06 — Metodología |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 6.0 |
| **Fecha** | 2026-10-19 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial. Metodología (8 pasos) para AFG1. | Primera entrega del curso. |
| 1.1 | 2026-09-20 | Redacción en voz de equipo; referencia a CONTRIBUTING | Consistencia de voz y de convenciones citadas |
| 1.2 | 2026-09-20 | Umbrales operativos provisionales en el paso 1 | Revisión final de AFG1: el paso 1 debe ser cuantitativo |
| 1.3 | 2026-10-01 | Reescritura completa de la redacción: se abre con las tres condiciones y las cuatro fases contadas como una secuencia con su razón, cada paso explica qué se hace y por qué, cada término técnico se explica al aparecer y se agrega un glosario breve. Las cifras, los umbrales, el diseño experimental y la numeración de secciones no cambian. | Retroalimentación de la revisión entre equipos de la semana 8: el problema y la metodología no se entendían, menos aún para una audiencia no técnica. |
| 2.0 | 2026-10-13 | Se agregan el detalle del filtro léxico y sus sesgos con su plan de medición (§2), el cálculo de los intervalos de confianza (§7–8), el criterio de éxito principal del proyecto (D16, §1), la acumulación de reuniones por serie (D15, §1) y el riesgo de C2 observado en una prueba sobre ES2015 (§7–8). | Retroalimentación del profesor sobre la metodología (AFG1/avance): faltaba el detalle del filtro y sus sesgos, el cálculo de los intervalos, las métricas de éxito y la definición de cuántas reuniones acumula cada evaluación. |
| 2.1 | 2026-10-13 | Se actualiza el estado de la Tarea C (§2): la muestra de recall pasa de una serie (IS1004) a cuatro, IS1004 más una serie de evaluación por sitio (ES2016, IS1003, TS3005), generadas con la misma semilla y sin anotar todavía. Cambio de estado y redacción; no altera cifras ni umbrales. | Poder reportar el recall del filtro por sitio, como pide la retroalimentación del profesor sobre el sesgo del filtro. |
| 2.2 | 2026-10-13 | La primera mención de la Tarea C en §2 dice "50 pares por serie". | La redacción de la versión 2.1 podía leerse como 50 pares en total. |
| 3.0 | 2026-10-13 | Se agrega la calibración de la anotación y su resultado (§5–6): la calibración sobre ES2015 dio un acuerdo bajo, se corrigió la guía de anotación (leer la transcripción de la reunión cuando la evidencia enlazada no alcanza, y un criterio para decidir qué cuenta como decisión) y se agrega una recalibración sobre TS3009 antes de las series de control. TS3009 pasa a doble anotación: las series doblemente anotadas pasan de 5 a 6. El 36,4 % de doble anotación de la evaluación no cambia. | Resultado de la calibración sobre ES2015: kappa de estado 0,094 (13 de 29 filas en acuerdo); 14 de los 16 desacuerdos eran de umbral. El protocolo exige corregir la guía y volver a calibrar antes de tocar una serie de evaluación ([`../../notebooks/04-jss-anotacion-f1-calibracion.ipynb`](../../notebooks/04-jss-anotacion-f1-calibracion.ipynb)). |
| 3.1 | 2026-10-14 | Se registra la elección del juez automático (§5–6): `gpt-oss:20b`, elegido entre tres candidatos con una calibración propia sobre ES2015 y umbrales fijados antes de ver resultados. Se declara una limitación de esa calibración. No cambian cifras previas ni umbrales. | La metodología preveía un juez automático sin nombrarlo; la calibración ([`../../notebooks/05-jss-seleccion-juez.ipynb`](../../notebooks/05-jss-seleccion-juez.ipynb)) ya permite fijarlo. |
| 3.2 | 2026-10-15 | Se registra el ajuste de la línea base C1 (§3–4): se ajustó sobre ES2015 con una regla fijada antes de correr, midiendo la evidencia sobre el texto que realmente llega al modelo; resultado de 1.200 caracteres por fragmento, 1 turno de solapamiento y 5 fragmentos. Se declara que las fechas de las reuniones llevan hora (§7–8): real cuando AMI la trae (6 de 14 series) y sintética, solo para preservar el orden, cuando no (8 de 14). La versión de OpenKOS a fijar queda abierta mientras se corrige (se suma `jasonssdev/openkos#1384` al plan). No cambian otras cifras ni umbrales. | El ajuste de C1 y la decisión sobre las fechas ya tienen evidencia propia ([ADR 0007](../decisions/0007-adr-ajuste-c1-y-presupuesto-de-contexto.md) y su enmienda, [notebook 06](../../notebooks/06-jss-ajuste-c1.ipynb); [ADR 0008](../decisions/0008-adr-fechas-de-reunion-para-openkos.md), [notebook 08](../../notebooks/08-jss-fechas-de-reunion.ipynb)). |
| 3.3 | 2026-10-15 | Se define la citación correcta (§1): una respuesta cuenta como bien citada cuando al menos una de sus fuentes citadas contiene alguna de las intervenciones que las personas marcaron como evidencia de la pregunta; además se informa, como cifra secundaria, qué fracción de lo citado es pertinente. Se declara el riesgo de que la regla favorezca a quien cita fragmentos grandes y el compromiso de revisarlo con los primeros datos de C2, antes de evaluar. No cambian otras cifras ni umbrales. | Análisis de la regla sobre la corrida de humo de ES2015: exigir que todas las fuentes coincidieran castigaba respuestas correctas con una cita válida más un repaso posterior ([ADR 0009](../decisions/0009-adr-regla-de-citacion-correcta.md), [notebook 09](../../notebooks/09-jss-regla-de-citacion.ipynb)). |
| 3.4 | 2026-10-15 | Se registran cuatro decisiones del análisis del Experimento B antes de correr cualquier evaluación (§1, §5–6, §7–8). (1) Criterio D16: el criterio principal pasa a ser que el intervalo bootstrap del 95 % de la **diferencia pareada** C2 − C1 en E3 quede por encima de 0; la no superposición de los intervalos independientes, que era la redacción de la versión 2.0, se conserva como cifra de robustez. Es una enmienda de un criterio prerregistrado el 2026-10-13, hecha antes de que exista cualquier corrida de evaluación. (2) Verificación humana del juez: el veredicto es por etiqueta (la corrección decide el juicio automático de la métrica principal; el soporte de evidencia tiene su propia marca de confiable o no confiable) y siempre se informan el acuerdo observado y la prevalencia junto al kappa. (3) Un kappa indefinido sigue contando como «no cumple». (4) La muestra humana toma una corrida sorteada por pregunta y condición, con el 20 % de las respuestas juzgadas como tamaño. No cambian otros umbrales ni cifras. | El criterio D16 se probó con una simulación de potencia con datos sintéticos: con las 25 preguntas mínimas de E3 y una mejora verdadera de 15 a 20 puntos, el criterio pareado declara respaldada la hipótesis en 58 % a 80 % de los experimentos y el de no solapamiento en 10 % a 28 % (con dificultad compartida moderada entre condiciones), con falsos positivos de a lo más 4,5 % y 0,8 % ([ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md), [notebook 10](../../notebooks/10-jss-potencia-criterio-d16.ipynb)). Las otras tres decisiones se apoyan en razones de principio, expuestas en el mismo ADR. |
| 3.5 | 2026-10-15 | Se registran dos decisiones provisionales de la puntuación del Experimento A (§1) y se declara una limitación de los intervalos. (1) Ámbito de la alineación: una decisión extraída solo puede emparejarse con una decisión de referencia cuya reunión esté entre las reuniones de origen de la extraída; la alineación sobre toda la serie se calcula aparte, como análisis de sensibilidad. (2) Rol de una decisión con evidencia de varias personas: el rol que más habló es el principal; contar la decisión en cada rol involucrado es el análisis de sensibilidad. Ambas decisiones son provisionales y se confirman o cambian con un análisis sobre la primera extracción real de una serie de desarrollo. No cambian otras cifras ni umbrales. | La decisión extraída puede reunir en un solo concepto una decisión repetida en varias reuniones, y la referencia de ES2015 tiene 9 de 27 decisiones con evidencia de más de un rol; sin extracción real no hay datos para elegir con evidencia (issue #99, bloqueado por #95). |
| 3.6 | 2026-10-15 | Se declara que el banco admite hasta 40 preguntas de E3 (§1, umbral del estrato E3). El mínimo prerregistrado de 25 por estrato no cambia; las filas de E3 sobre ese mínimo son opcionales y quedan vacías si el material de evolución no alcanza. | Aumentar la probabilidad de detectar una mejora real más pequeña en E3: la simulación de potencia da alrededor de 57 % con 25 preguntas y 76 % con 40 para una mejora de 15 puntos ([notebook 10](../../notebooks/10-jss-potencia-criterio-d16.ipynb)); el tope lo fija el material disponible ([notebook 01](../../notebooks/01-jss-viabilidad-e3.ipynb)). |
| 3.7 | 2026-10-15 | Se agregan referencias cruzadas a los documentos [07](07-jss-analisis-exploratorio.md), [08](08-jss-metricas-y-criterio-de-exito.md) y [09](09-jss-modelos-y-justificacion.md), donde ahora vive el detalle del filtro léxico, de las métricas y del criterio D16, y de las condiciones, el juez y los parámetros: una nota «Documentos relacionados» al inicio y una línea de remisión al comienzo de las secciones 1, 2, 3–4 y 5–6. No se elimina contenido y no cambia ninguna cifra, umbral ni decisión. | Los documentos 07 a 09 de AFG2 desarrollan partes de esta metodología; sin enlaces, el lector no sabe dónde está el detalle. |
| 3.8 | 2026-10-15 | Se usan los nombres estándar de métricas y técnicas sin traducir (ground truth, precision, recall, accuracy, LLM-as-a-judge, baseline, overlap coefficient, context window, cosine similarity, filtro léxico (*blocking*)). | Convención del equipo: los nombres de métricas y técnicas no se traducen. |
| 3.9 | 2026-10-15 | Se declara que el banco de preguntas y la calibración del LLM-as-a-judge están en inglés, con su límite (§5–6); las cifras de ES2015 (4 extraídas frente a 29 decisiones, kappa 0,094) indican su denominador (29 decisiones con acuerdo evaluado; 27 decisiones finales; 34 filas en el archivo adjudicado); se indica la fuente de las tasas por sitio del filtro léxico (§2); se reescribe en presente un párrafo que describía versiones anteriores; se agregan filas de trazabilidad. No cambia ninguna cifra, umbral ni decisión. | Auditoría de gobernanza del 2026-10-15: el idioma del banco no estaba declarado y las cifras de ES2015 parecían contradecirse por usar denominadores distintos sin decirlo. |
| 4.0 | 2026-10-16 | Se ratifican las dos decisiones que la versión 3.5 dejó como provisionales y se cambia el intervalo principal del Experimento A (§1, §7–8). (1) Ámbito de la alineación: el principal son las reuniones de origen; la serie completa se informa siempre al lado como sensibilidad. (2) Rol de una decisión con evidencia de varias personas: el principal es el rol mayoritario (empate: el turno más temprano); cada rol involucrado se informa como sensibilidad. (3) Intervalos: el intervalo principal de los resultados agrupados de precision, recall y F1 pasa a ser un bootstrap que remuestrea reuniones completas; el intervalo de Wilson (precision, recall) y el bootstrap por decisión (F1) se informan al lado como referencia. Se declara su limitación: con pocas reuniones (una serie tiene 4, lo que da solo 35 remuestreos distintos) el bootstrap por reuniones es burdo y frágil. No se fija el umbral τ ni cambia ningún otro umbral. | Análisis del [notebook 14](../../notebooks/14-jss-alineacion-experimento-a.ipynb) sobre la primera extracción real de ES2015 (serie de desarrollo, OpenKOS 0.5.5 provisional): las cifras difieren según el ámbito (F1 con τ = 0,60: 0,29 en la misma reunión y 0,43 en toda la serie), el rol cambia la cobertura en menos de 0,08, y los intervalos por reuniones son de 1,5 a 2,4 veces más anchos en recall y F1 con τ = 0,60. El cargador de referencia encuentra 6 de 27 decisiones de ES2015 con más de un rol (el 9 del issue #99 no se reproduce). Razonamiento completo: [ADR 0011](../decisions/0011-adr-alineacion-rol-e-intervalos-del-experimento-a.md). |
| 4.1 | 2026-10-18 | Se declara, como limitación acotada (§7–8), que dos umbrales de troceo de OpenKOS se fijaron con mediciones sobre TS3005, una serie de evaluación. Es un cambio de redacción: no cambia cifras ni umbrales. | Issue #145. Los umbrales deciden cuándo se trocea una fuente, no qué se extrae, pero se ajustaron mirando una serie de evaluación, lo que contradice la regla del [ADR 0005](../decisions/0005-adr-development-evaluation-split.md) si no se declara. El análisis se hizo sobre el código y el historial de OpenKOS (commits `578dea3d`, `0c96ad9c` y `58b9e699`). |
| 5.0 | 2026-10-19 | Se declara, como elección metodológica y limitación (§1), que el texto de referencia que se compara con las extracciones del Experimento A es una traducción automática al inglés de las etiquetas humanas. Las etiquetas siguen siendo las humanas, en español; la traducción no cambia ningún estado ni etiqueta. No cambian cifras ni umbrales, y no se fija τ. | Issue #141. La extracción sale en inglés, el idioma original de las transcripciones, y la referencia está en español: la similitud entre una frase en inglés de AMI y su propia anotación en español tiene mediana 0,69 (ES2015) y 0,72 (TS3009), y solo 3 de 27 y 3 de 21 llegan a 0,80 ([notebook 15](../../notebooks/15-jss-screen-de-modelos-openkos.ipynb), §6.4). Método: [`../anotacion/traduccion-referencia.md`](../anotacion/traduccion-referencia.md); protocolo: [`../protocols/alignment.md`](../protocols/alignment.md) 2.0. |
| 6.0 | 2026-10-19 | Se fija el umbral τ del Experimento A (§1, §5–6): **τ principal = 0,70**, con 0,75 y 0,80 como análisis de sensibilidad y la curva completa siempre al lado. Se aparta de la regla fijada antes de ver los resultados (`max(τ_nulo, τ_juez)`, que daba 0,80), porque el control nulo cruza dos equipos de AMI con el mismo encargo de diseño y por eso sobrestima el azar; el desvío responde a ese defecto del control, no a la cobertura que resulta. El juez automático complementa la validación manual del protocolo y no la sustituye; la concordancia del juez con una persona sobre 50 pares queda pendiente. No cambian otros umbrales ni cifras. | Issue #142. Cobertura nula 0,138, 0,053 y 0,015 con τ = 0,70, 0,75 y 0,80; proporción de «sí» del juez a lo más 0,32 por debajo de 0,70 y al menos 0,76 en cada bin desde 0,70 ([ADR 0012](../decisions/0012-adr-umbral-tau-del-experimento-a.md), [notebook 17](../../notebooks/17-jss-tau-referencia-en.ipynb)); protocolo [`../protocols/alignment.md`](../protocols/alignment.md) 3.0. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## Documentos relacionados

Este documento fija el diseño completo. Tres documentos posteriores desarrollan partes de él
con más detalle y con las cifras ya medidas:

- [Documento 07, análisis exploratorio](07-jss-analisis-exploratorio.md): la calidad de los
  datos y el filtro léxico (*blocking*) en lenguaje simple (§7).
- [Documento 08, métricas y criterio de éxito](08-jss-metricas-y-criterio-de-exito.md): qué se
  mide en cada objetivo, con qué umbral o intervalo, y el criterio D16 (§6).
- [Documento 09, modelos y su justificación](09-jss-modelos-y-justificacion.md): las tres
  condiciones, el LLM-as-a-judge (un segundo modelo que califica las respuestas) y los parámetros, con su evidencia.

## El experimento en una página

Antes de los ocho pasos, lo esencial. El proyecto compara tres maneras de responder a la
pregunta "¿qué decidió el equipo sobre X, y cómo cambió?" sobre las mismas reuniones, con el
mismo modelo de lenguaje, el mismo computador y el mismo límite de texto que el modelo
puede leer de una vez. Se llaman **condiciones**:

| | Condición | Qué es | Para qué sirve en la comparación |
|---|---|---|---|
| **C1** | RAG documental | Buscar en las transcripciones los fragmentos parecidos a la pregunta y redactar una respuesta con ellos. Es la práctica actual. | El piso: lo que cualquiera haría hoy. |
| **C2** | Base construida por la máquina | Un modelo de lenguaje lee las transcripciones, extrae las decisiones y las guarda en una base con sus relaciones. Es la propuesta. | Lo que se evalúa. |
| **C3** | Base construida por personas | La misma base de C2, pero llenada con la anotación humana del ground truth (las decisiones marcadas a mano). Sin errores de extracción. | Separa dos cosas: la distancia C1→C3 es el valor de tener la base; la distancia C3→C2 es el costo de los errores de la máquina. |

Sin C3 no se podría distinguir si una mala respuesta de C2 se debe a que la idea de la base
no sirve o a que la máquina la llenó mal. Esa es la limitación de los trabajos previos que
se señala en el documento 01, y la razón de ser de este diseño.

El trabajo se organiza en **cuatro fases**, en orden, porque cada una necesita la anterior:

1. **El ground truth.** Personas marcan a mano las decisiones de 14 series de
   reuniones y cómo se relacionan entre reuniones. Aporta el patrón contra el cual se mide
   todo lo demás; sin él, ninguna otra fase mide nada.
2. **La extracción automática.** Se mide qué tan bien la máquina encuentra esas mismas
   decisiones y relaciones. Aporta el costo de construir la base automáticamente.
3. **La utilidad funcional.** Las tres condiciones responden el mismo banco de preguntas.
   Aporta el valor de la base, ya con sus errores incluidos.
4. **La atribución de error.** Para cada respuesta equivocada de C2 se determina dónde nació
   el error. Aporta saber en qué conviene invertir.

Los ocho pasos que siguen son el esqueleto que exige el curso. Cada paso está lleno con el
diseño real del proyecto, no con una descripción genérica, y en cada uno se indica a qué
fase pertenece.

## 1. Problema y métricas

*Fases 1 a 3: qué se cuenta y cómo se mide.*

*Más detalle:* todas las métricas con su umbral y su estado, en el [documento 08](08-jss-metricas-y-criterio-de-exito.md) (§3 y §4); el criterio de éxito D16, en su [§6](08-jss-metricas-y-criterio-de-exito.md#6-cómo-sabremos-si-el-experimento-tuvo-éxito).

**Unidad de análisis.** Lo primero es fijar qué se va a contar. La unidad es la decisión
individual y el par de decisiones dentro de una serie (un par es una decisión de una
reunión frente a una decisión de otra reunión del mismo equipo). Para que algo cuente como
decisión tiene que cumplir tres condiciones: ser explícita (al menos un acto de diálogo, es
decir, una intervención de alguien, la formula o ratifica), aceptada (no queda como
propuesta abierta) y anclada (identifica el objeto y el contenido: sobre qué se decide y
qué). Las propuestas no aceptadas se registran como no-decisiones: hacen falta para medir
falsos positivos, es decir, los casos en que la máquina diga "decisión" donde no la hubo.

**Métricas de OE2** (fase 2): precision, recall y F1 a nivel decisión; accuracy de tipo
y de dirección a nivel relación temporal (la fracción de relaciones clasificadas bien), reportadas por separado. Precision es qué parte de
lo que la máquina extrajo era realmente una decisión; recall, qué parte de las decisiones
reales encontró; F1 las combina. **Métricas de OE3** (fase 3): corrección de respuesta,
soporte de evidencia, citación correcta, corrección del rechazo (si el sistema sabe decir
"no hay información" cuando no la hay), y costo amortizado (§7).

**Dos decisiones de la puntuación de OE2 (ADR 0011).** La puntuación calcula siempre, junto a cada valor principal, una alternativa de sensibilidad (un análisis de sensibilidad repite el cálculo con la otra opción para ver cuánto cambia el resultado). Ambos valores se fijaron por defecto antes de que existiera una extracción real y se ratificaron el 2026-10-16 con el análisis de la primera extracción real de ES2015, una serie de desarrollo ([notebook 14](../../notebooks/14-jss-alineacion-experimento-a.ipynb), [ADR 0011](../decisions/0011-adr-alineacion-rol-e-intervalos-del-experimento-a.md)). (1) **Ámbito de la alineación.** Una decisión extraída solo puede emparejarse con una decisión de referencia si la reunión de esta última figura entre las reuniones de origen de la extraída: el sistema puede reunir en un solo concepto una decisión repetida en varias reuniones, de modo que la extraída puede tener más de una reunión de origen. Es el ámbito principal. La alineación sobre toda la serie, sin esa restricción, se informa siempre al lado como sensibilidad. (2) **Rol del hablante.** Cuando la evidencia de una decisión proviene de personas con roles distintos, el rol que más habló es el principal (empate: el turno más temprano); la sensibilidad cuenta la decisión en cada rol involucrado, tanto en recall como, cuando se conoce el rol de lo extraído, en precision. Ni el análisis ni el ADR 0011 fijan el umbral τ de la alineación; se fijó después, con la referencia en inglés (ADR 0012, versión 6.0: τ principal 0,70, con 0,75 y 0,80 como sensibilidad). **Intervalos.** El intervalo principal de los resultados agrupados de precision, recall y F1 es un bootstrap que remuestrea reuniones completas, porque las decisiones de una misma reunión comparten contexto y tratarlas como independientes es optimista; el intervalo de Wilson (precision y recall) y el bootstrap por decisión (F1) se informan al lado como referencia. Limitación declarada: con pocas reuniones el bootstrap por reuniones es burdo; una serie tiene 4, lo que da solo 35 remuestreos distintos y un intervalo frágil, que se estabiliza al agrupar varias series de evaluación.

**Idioma de la referencia (issue #141).** Las transcripciones de AMI y lo que extrae la máquina están en inglés, mientras que las etiquetas humanas de la referencia están en español. Como el emparejamiento se decide por parecido de significado entre textos, comparar un texto en inglés con otro en español pone un techo artificial al resultado, que viene del cambio de idioma y no de la extracción. Por eso el texto de referencia que se compara es una **traducción automática al inglés** de las etiquetas humanas. Las etiquetas siguen siendo las humanas, en español: la traducción no cambia ningún estado ni ninguna etiqueta y no es una etiqueta. Se traduce solo la etiqueta, sin consultar la transcripción para redactarla ni ninguna salida de extracción, para no acercar artificialmente la referencia a lo extraído. Una validación comprueba que cada decisión de referencia tiene su traducción y que esta no quedó desactualizada si cambia la adjudicación. Limitación declarada: la traducción no la revisa una persona, de modo que un error de traducción actuaría como ruido en la referencia y podría bajar o subir algo la coincidencia; la cifra se acompaña de esta salvedad. Método y reglas: [`../anotacion/traduccion-referencia.md`](../anotacion/traduccion-referencia.md).

**Citación correcta (ADR 0009).** Esta métrica busca el caso en que la respuesta es correcta
pero la fuente que cita no la respalda. En términos simples: una respuesta cita uno o varios
pasajes de las reuniones; cada pasaje "acierta" si contiene al menos una de las
intervenciones que las personas marcaron como la evidencia de esa pregunta. La citación se da
por **correcta cuando al menos un pasaje acierta**, e **incorrecta cuando ninguno acierta o
cuando la respuesta no cita nada** (una afirmación sin fuente cuenta como falla aunque sea
correcta). Se descartó exigir que *todos* los pasajes acierten, porque castigaba por igual
citar una fuente ajena y citar la fuente correcta junto con un repaso válido de la misma
idea. Como la regla admite citar de más, se informa además la **precision de la citación**
(la fracción de los pasajes citados que aciertan), que deja a la vista a quien cita todo.
Queda un riesgo declarado: C1 cita fragmentos grandes y C2 y C3 citarán decisiones más
puntuales, de modo que la regla podría favorecer a C1; se revisará con los primeros datos de
C2, antes de correr la evaluación.

**Umbrales operativos provisionales.** Un paso 1 sin números es una declaración de
intenciones. Se fijan ahora para que sea cuantitativo; se revisan en AFG2 con los primeros
datos y cualquier cambio se registra en `docs/decisions/`.

| Qué | Umbral | Qué pasa si no se cumple |
|---|---|---|
| Concordancia del alineamiento automático con el emparejamiento manual (100 pares) | ≥ 0,80 | Se revisa la grilla de τ y se repite la validación |
| Concordancia LLM-as-a-judge – humano (20 % de las respuestas, una corrida por pregunta y condición), por etiqueta | kappa ≥ 0,70 | Si falla la corrección de respuesta, se descarta el juicio automático de la métrica principal y se reporta solo la evaluación humana; si falla el soporte de evidencia, esa métrica se reporta solo con evaluación humana o marcada como no confiable |
| Tamaño del estrato E3 | ≥ 25 preguntas (el banco admite hasta 40) | E3 se reformula como análisis de casos con reporte cualitativo |
| Diferencia entre condiciones (criterio principal D16) | Intervalo bootstrap del 95 % de la diferencia pareada C2 − C1 por encima de 0 | No se afirma diferencia; se reporta como no concluyente |
| Kappa de la anotación (existencia, tipo, dirección) | Sin umbral de aceptación, por diseño | Se reporta tal como salga; un kappa bajo es un hallazgo (documento 01, §3) |

La última fila merece una explicación. Kappa es la medida de acuerdo entre dos anotadores
que descuenta las coincidencias por azar. El documento 01 muestra que dos equipos expertos
obtuvieron un kappa negativo anotando decisiones sobre este mismo corpus. Si aquí se
exigiera un kappa mínimo, se estaría obligando a los anotadores a ponerse de acuerdo en
lugar de medir cuánto se ponen de acuerdo de verdad.

**Criterio de éxito del proyecto (D16).** Los umbrales de la tabla anterior son umbrales de
validez: dicen si la medición es confiable, no si el proyecto tuvo éxito. El criterio de
éxito principal se fija aquí, antes de correr el experimento, para que no pueda ajustarse a
los resultados: la **corrección de respuesta en el estrato E3** (las preguntas sobre cómo
cambió una decisión), **C2 frente a C1**. La hipótesis del proyecto se considera respaldada
si el intervalo bootstrap del 95 % de la **diferencia pareada C2 − C1** queda por encima de 0.
La diferencia pareada se calcula pregunta por pregunta: como C1 y C2 responden las mismas
preguntas, una pregunta difícil lo es para las dos y esa dificultad común se cancela en la
diferencia. Si el intervalo incluye el 0, el resultado se reporta como no concluyente y nunca
como éxito. Como cifra de **robustez** se informa además si los intervalos del 95 % de C2 y de
C1, calculados cada uno por separado, se solapan; esa cifra acompaña al criterio principal y no
lo reemplaza. Todo lo demás es secundario y descriptivo: precision, recall y F1 de OE2,
accuracy de tipo y de dirección, soporte de evidencia, citación, corrección del rechazo, costo
amortizado, los estratos E1, E2 y E4, y la comparación C2 frente a C3. Cómo se calculan los
intervalos se explica en los pasos 7–8.

> **Enmienda del criterio D16 (2026-10-15, versión 3.4).** *Redacción superada* (versión 2.0,
> 2026-10-13): la hipótesis se considera respaldada «si el intervalo bootstrap del 95 % de C2
> queda por encima del de C1 sin solaparse». Se cambió antes de que exista cualquier corrida de
> evaluación, de modo que ningún dato pudo influir en la elección. La razón es que, con las 25
> preguntas mínimas de E3, esa lectura casi nunca permite concluir aunque la mejora sea real:
> una simulación con datos sintéticos da 10 % a 28 % de detección para mejoras de 15 a 20 puntos
> (con dificultad compartida moderada), frente a 58 % a 80 % del criterio pareado, con falsos positivos por debajo del 5 % en ambos
> ([ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md),
> [notebook 10](../../notebooks/10-jss-potencia-criterio-d16.ipynb)).

**Acumulación de reuniones (D15).** Cada pregunta se responde después de haber procesado la
serie completa (4 reuniones), en orden cronológico y sin acceso a reuniones futuras durante
la extracción. E2 pregunta por el estado vigente al cierre de la serie; E3, por cómo cambió
una decisión a lo largo de ella. Cada condición ve solamente esa serie: C1 recupera
fragmentos únicamente de las transcripciones de la serie; C2 usa un espacio de trabajo de
OpenKOS por serie, con las cuatro reuniones ingestadas en orden; C3 usa una base construida
con la anotación adjudicada de esa serie. La razón: las 14 series son la misma tarea de
diseño (un control remoto), de modo que mezclarlas permitiría que una pregunta sobre una
serie recuperara decisiones de otra. Se descartó un corte variable *k* (la pregunta se hace
tras la reunión 2, 3 o 4), que daría una curva por número de reuniones acumuladas, porque
exige hasta 2,25 veces las corridas de extracción de C2 y una respuesta de referencia por
corte; queda como análisis secundario opcional. La anotación y sus CSV no cambian.

**Horizonte para evitar fuga.** Una fuga ocurre cuando el sistema, o el anotador, usa
información que en la vida real todavía no existía. Para evitarla, la anotación de
relaciones temporales se hace en orden cronológico dentro de cada serie, sin acceso a
reuniones posteriores al momento de anotar cada decisión. La extracción automática procesa
las reuniones en orden y no puede consultar reuniones futuras. La cronología está verificada
empíricamente vía `startTime` en `meetings.xml` (IS1004: 11:03 → 12:03 → 14:13 → 15:34 el
mismo día), no asumida.

## 2. Auditoría de datos

*Fase 1: con qué material se trabaja.*

*Más detalle:* la calidad de los datos, en el [documento 07](07-jss-analisis-exploratorio.md) (§4); la regla del filtro léxico explicada en lenguaje simple, en su [§7](07-jss-analisis-exploratorio.md#7-el-filtro-léxico-en-lenguaje-simple).

Resumida aquí; el detalle completo —marco muestral, selección de 14 series, split
desarrollo/evaluación, los cuatro N, composición lingüística, autoría por rol, anclaje a
evidencia, riesgos y plan de saneamiento— está en
[`02-jss-fuente-de-datos.md`](02-jss-fuente-de-datos.md). El resultado que condiciona todo lo
que sigue: 14 series, 56 reuniones, 343 decisiones, 3.071 pares entre reuniones, 92 pares
candidatos tras el filtro léxico. Esos 92 pares son los que las personas anotan en la fase 1.

**El filtro léxico y sus sesgos.** Como esos 92 pares condicionan todo el conjunto de
referencia, conviene explicar cómo se llega a ellos. Cada frase de decisión se pasa a
minúsculas, se conservan solo las palabras de al menos 3 letras y se descartan las palabras
vacías ("de", "que", "el"). Luego, para cada par de decisiones de reuniones distintas, se
calcula el **overlap coefficient**: palabras compartidas dividido por el tamaño de la
frase más corta. Se usa este coeficiente y no Jaccard porque una reversión suele ser una
frase corta posterior que apunta a una larga anterior: en el par del botón turbo, Jaccard da
0,118 y pierde el caso, mientras que el overlap coefficient da 0,400 y lo conserva. Un par es
candidato si el coeficiente es ≥ 0,30 **y** comparte al menos 2 palabras. Solo con el
coeficiente pasarían 712 de 3.071 pares (23,2 %, ≈18 h de anotación); con ambas condiciones,
92 (3,0 %, ≈2,3 h). El punto de operación está acotado por ambos lados: si el umbral sube
sobre 0,40 o el mínimo de palabras sobre 2, se pierde el par del botón turbo, el único par
revisado a mano cuyas frases describen una reversión (la transcripción mostró después que el
resumen se equivoca, pero el filtro solo lee las frases, así que el par sigue sirviendo de
control); si se relaja, vuelven los 712.

Un filtro así introduce sesgos que se declaran: (1) se pierden las paráfrasis con
vocabulario distinto; (2) se penaliza a las frases muy cortas, y las reversiones tienden a
ser cortas; (3) la cota se calibró con un solo par de control; (4) el presupuesto de horas
entró en la elección del punto de operación; (5) el ground truth favorece a los
métodos léxicos (D6 evita el sesgo inverso, no este). Una comprobación medida: la proporción
de candidatos por sitio de grabación en el punto de operación es parecida (ES 44 pares,
3,2 %; IS 22, 3,1 %; TS 26, 2,6 %; pares por sitio del [ADR 0004](../decisions/0004-adr-oe1-series-selection.md) y tasas en el [notebook 00](../../notebooks/00-jss-corpus-y-auditoria.ipynb) §4.1, sin tabla versionada aparte), pero eso **no** demuestra que la pérdida sea igual en
cada sitio. La mitigación es la **Tarea C**: 50 pares por serie que el filtro rechazó, muestreados al
azar con semilla fija y anotados con las mismas reglas; toda relación real entre ellos es un
falso negativo, y con eso se reporta el recall del filtro (qué proporción de las relaciones
reales deja pasar) con un intervalo bootstrap. Estado real: la muestra está generada pero no
anotada. Cubre IS1004 (serie de desarrollo y una de las dos de menor tasa) y una serie de
evaluación por sitio de grabación (ES2016, IS1003 y TS3005), con la misma semilla y 50 pares
por serie; así el recall puede reportarse por sitio y en conjunto, y responder la pregunta del
sesgo. Mientras tanto, 92 es la cota superior de lo que este filtro permite anotar, no de las
relaciones que existen en el corpus. La evidencia está en
[`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb)
§4.1 y la implementación en `src/afg/annotation/blocking.py`.

## 3–4. Diseño analítico y baselines

*Fase 3: las tres condiciones y la regla de "todo lo demás igual".*

*Más detalle:* cada condición, sus técnicas y sus parámetros, con la evidencia de cada elección, en el [documento 09](09-jss-modelos-y-justificacion.md) (§2 y §3).

**Tres condiciones**, mismo modelo generativo, mismo modelo de *embeddings*, mismo hardware y
mismo presupuesto de contexto. Un modelo de *embeddings* convierte texto en números para
poder medir cuánto se parecen dos fragmentos; el presupuesto de contexto es cuánto texto
puede leer el modelo de una vez. Sin esta restricción, cualquier diferencia observada es
inatribuible: si C2 usara un modelo más grande que C1, no se sabría si ganó por la base o
por el modelo.

- **C1 — RAG documental.** Transcripciones segmentadas en fragmentos e indexadas con
  búsqueda híbrida (léxica, por palabras exactas, y densa, por parecido de significado).
  **Baseline honesto:** un baseline es el punto de comparación, y un baseline
  débil hace que cualquier propuesta parezca buena. Por eso los parámetros de segmentación
  y el número de fragmentos recuperados se ajustan sobre el conjunto de desarrollo (77
  decisiones, 11 candidatos), no se fijan arbitrariamente. Un baseline debilitado
  invalida el experimento completo. El ajuste se hizo sobre la serie de desarrollo ES2015,
  con una regla fijada antes de correr y con una medida precisa: el recall de evidencia
  (qué parte de los pasajes que respaldan la respuesta aparece entre lo recuperado), contado
  sobre el texto que de verdad le llega al modelo una vez aplicado el límite de contexto de
  OpenKOS, y no sobre los fragmentos completos, que el modelo no llega a leer enteros. El
  resultado son fragmentos de a lo más 1.200 caracteres, con 1 turno de solapamiento (el
  último turno de un fragmento se repite al inicio del siguiente) y K = 5 fragmentos
  recuperados. Como las tres condiciones recortan el contexto con las mismas funciones, las
  tres reciben a lo más el mismo contexto, unos 7.400 caracteres, por construcción. La
  evidencia está en el [ADR 0007](../decisions/0007-adr-ajuste-c1-y-presupuesto-de-contexto.md)
  (con su enmienda del 2026-10-15) y en el
  [notebook 06](../../notebooks/06-jss-ajuste-c1.ipynb).
- **C2 — Compilación automática.** Extracción con modelo local, persistencia con
  procedencia (cada decisión guardada con la reunión y el pasaje de donde salió), consulta
  sobre los objetos compilados.
- **C3 — Compilación desde la referencia.** Idéntica a C2 salvo que los objetos provienen de
  la anotación humana de OE1.

**El filtro léxico de candidatos** pertenece a la fase 1, pero sigue el mismo principio. Es el
filtro que decide qué pares de decisiones se ofrecen a anotación humana, porque leer los
3.071 pares posibles no es viable. Se ajusta también sobre desarrollo, y exige overlap
coefficient ≥ 0,30 **y** al menos 2 tokens compartidos. El overlap coefficient
mide qué proporción de las palabras de la frase más corta aparece en la otra; un token es
una palabra. Se usa el overlap coefficient y no Jaccard (que divide por el total de palabras distintas
de ambas frases y castiga a las frases cortas) porque Jaccard pierde el caso de regresión
del filtro léxico: el par del botón turbo, Jaccard 0,118 frente a overlap coefficient 0,400. Ese par
es el de solape léxico más exigente medido en el piloto y **no** una relación confirmada: la
verificación contra transcripción mostró después que esa reversión no ocurrió (documento 02,
§4.4). Se conserva como prueba de que el filtro sigue dejando pasar frases cortas. Y se
exige el mínimo absoluto de tokens porque el coeficiente solo, sobre las 14 series reales,
seleccionaba 712 de 3.071 pares (23,2 %, ≈18 h de anotación) en vez del 5,5 % que sugería
el piloto; con el mínimo añadido, 92 (3,0 %, ≈2,3 h), sin perder el caso de prueba.

## 5–6. Modelado y validación

*Fases 1 y 2: con qué modelos se extrae, cómo se decide si acertaron y por qué la referencia
la hacen personas.*

*Más detalle:* la elección y la calibración del LLM-as-a-judge, en el [documento 09](09-jss-modelos-y-justificacion.md) (§4); la cuenta de parámetros, en su §5.

**Modelos.** Modelos generativos de ejecución local (familia Qwen o equivalente, en escalas
contrastables) y un modelo de *embeddings* multilingüe. "Ejecución local" significa que
corren en un computador propio, sin enviar datos a servicios externos; "escalas
contrastables" significa tamaños de modelo distintos que se puedan comparar. Versiones
exactas, semilla, tamaño de la context window (lo que el modelo lee de una vez) y parámetros de muestreo se fijan y se
publican, para que cualquiera pueda repetir la corrida.

**Varianza no determinista.** La extracción con un modelo de lenguaje no es determinista
aun con temperatura baja: la misma transcripción, procesada dos veces, puede dar listas de
decisiones ligeramente distintas. Por eso cada configuración se ejecuta un **mínimo de tres
veces**, reportando media y dispersión, no una corrida única. Una sola corrida podría ser la
afortunada o la desafortunada.

**Protocolo de alineamiento.** Cuando la máquina extrae "se mantiene el botón turbo" y la
referencia dice "el equipo conserva el botón turbo", ¿es la misma decisión? Hace falta una
regla fija para decidirlo, acordada antes de ver resultados. El protocolo determina si una
decisión extraída corresponde a una de referencia en cuatro pasos: (1) candidatos por
cosine similarity de *embeddings* sobre el par (objeto, contenido) por encima de un umbral τ,
es decir, se consideran parecidas las decisiones cuya representación numérica supera cierto
parecido mínimo; (2) emparejamiento uno-a-uno por asignación de costo máximo —algoritmo
húngaro—, no por vecino más cercano codicioso: se busca el mejor emparejamiento global de
todas las decisiones a la vez, en lugar de asignar cada una a su vecina más parecida y
dejar que las últimas se queden sin pareja; (3) validación contra emparejamiento manual
sobre al menos 100 pares, con concordancia reportada; (4) todos los F1 se reportan como
**curva sobre τ**, no en un único punto, porque elegir un único τ permitiría escoger el que
dé mejor resultado. El τ principal es 0,70, con 0,75 y 0,80 como sensibilidad, y la curva completa siempre al lado ([ADR 0012](../decisions/0012-adr-umbral-tau-del-experimento-a.md)); el juez automático complementa la validación manual del paso (3), no la sustituye. Se descartan PR-AUC y matrices de confusión como métricas principales
porque el sistema emite conjuntos en lenguaje natural, no puntajes sobre clases fijas;
Recall@K se conserva sólo para la etapa de recuperación dentro de C1 y C2.

**El filtro de candidatos y su punto de operación** es el mismo filtro léxico de §3–4, aplicado
antes de la anotación humana: 92 pares candidatos de 3.071 posibles, versionado
(`BLOCKER_VERSION`) para que cambiar el punto de operación invalide explícitamente los
candidatos ya generados en vez de mezclarlos en silencio. Si el filtro cambia, los pares
anotados con el filtro anterior quedan marcados como de otra versión, no mezclados.

**Anotación humana, por qué no se automatiza.** Las etiquetas del ground truth las
pone siempre un humano. Si un modelo las produjera, la condición C3 tendría errores de
extracción por construcción y la brecha C2 − C3 —que es todo OE4— dejaría de medir nada: se
estaría comparando los errores de una máquina contra los errores de otra. Los modelos sólo
proponen candidatos, resuelven evidencia y calculan acuerdo.

**Kappa por existencia, tipo y dirección**, nunca combinado, sobre el 36,4 % de la
evaluación (control de doble anotación: ES2008, ES2016, IS1003, TS3005), con adjudicación
documentada para todo desacuerdo. Son tres preguntas distintas (¿se relacionan? ¿cómo? ¿en
qué dirección?) y se reporta el acuerdo en cada una, porque una sola cifra ocultaría dónde
está el desacuerdo. Adjudicar es que una tercera persona, que no anotó, resuelva cada
desacuerdo y deje escrito por qué.

**Calibración antes de anotar lo que se reporta.** Antes de las series de control, las dos
personas que anotan trabajan por separado sobre una serie de desarrollo, ES2015, que no entra
en la evaluación. Su único fin es comprobar que ambas entienden la guía igual; su acuerdo es
un diagnóstico y no se reporta en la tesis. El resultado fue bajo: coincidieron en 13 de 29
decisiones (kappa de 0,094, apenas sobre el azar), y 14 de los 16 desacuerdos tenían la misma
forma: una persona aceptaba la frase como decisión y la otra la rechazaba por falta de
respaldo. La causa estaba en la guía, no en las personas. La guía pedía juzgar cada frase solo
con el fragmento de diálogo que el corpus enlaza a ella, que a menudo es muy corto; quien la
aplicó al pie de la letra rechazaba frases que la conversación completa sí respaldaba. La guía
se corrigió en tres puntos: si ese fragmento no alcanza, se lee la transcripción de la misma
reunión (nunca de reuniones posteriores); una frase se rechaza por falta de respaldo solo si
la conversación la contradice o no la contiene; y se agregó un criterio para decidir cuándo
una propuesta llegó a ser decisión. Como lo exige el protocolo, se vuelve a calibrar antes
de tocar una serie de evaluación: las dos personas anotan otra serie de desarrollo, TS3009,
con la guía corregida, y solo después comienzan las series de control. TS3009 sigue en el
ground truth, ahora con doble anotación; las series doblemente anotadas pasan de
cinco a seis, y la proporción de doble anotación sobre la evaluación (36,4 %) no cambia.

**El LLM-as-a-judge, elegido con evidencia propia.** El Experimento B produce unas 900
respuestas, demasiadas para calificarlas a mano. Las califica un LLM-as-a-judge: un segundo
modelo que lee la pregunta, la respuesta de referencia, la respuesta del sistema y el pasaje de
la transcripción donde está la evidencia, y decide si la respuesta es correcta y si cada
afirmación está respaldada por la transcripción. Para no favorecer sus propias respuestas, el
LLM-as-a-judge no puede ser de la familia de ningún modelo que use OpenKOS (ni Qwen ni Gemma). Ningún
ranking público mide esta tarea, así que se eligió con una prueba propia: una persona del
equipo escribió 21 preguntas sobre ES2015 y etiquetó a mano 42 respuestas, y cada uno de los
tres candidatos calificó esas mismas respuestas. Los requisitos se fijaron antes de correr
ningún candidato: acuerdo con las personas de kappa 0,70 o más, el mismo veredicto al cambiar
el orden en que se presentan las respuestas, el mismo veredicto con distintas semillas, no
premiar las respuestas por ser largas y reconocer cuándo la pregunta no tiene respuesta.

`gpt-oss:20b` y `mistral-small3.2:24b` cumplieron todos los requisitos, con el mismo acuerdo
(kappa 0,95); la regla fijada de antemano desempata por rapidez y `gpt-oss:20b` tarda 3,2
segundos por respuesta frente a 5,5. `atla/selene-mini`, un modelo pequeño entrenado para evaluar, no los cumplió:
cambiaba de veredicto según el orden de presentación. Para comprobar que las etiquetas humanas
son confiables, una segunda persona etiquetó 15 de las respuestas por separado: coincidieron en
15 de 15 sobre si la respuesta es correcta (kappa 1,00) y en 14 de 15 sobre si está respaldada
(kappa 0,87).

La calibración tiene una limitación que se declara: el identificador de cada respuesta dejaba
ver cómo se había generado (con o sin la evidencia), de modo que quienes etiquetaron podían
saberlo. El equipo decidió declararlo en lugar de volver a etiquetar; los casos en que las
etiquetas contradicen ese identificador indican que se etiquetó por el contenido, pero el
acuerdo podría estar algo inflado. Otra limitación es el idioma: la calibración se hizo con
preguntas y respuestas en inglés sobre transcripciones en inglés, y el banco de preguntas del
Experimento B también se escribe en inglés (las transcripciones del corpus y la recuperación
léxica de C1 trabajan sobre texto en inglés). El acuerdo medido no se extiende a preguntas en
español. Como protección adicional, el Experimento B mantiene la
verificación humana sobre el 20 % de las respuestas (§1) y la decide **por etiqueta**, porque
las dos etiquetas del LLM-as-a-judge no se usan igual. La **corrección de respuesta** es la métrica del
criterio principal (D16): si su acuerdo con las personas cae bajo 0,70 (kappa), el juicio
automático se descarta y esa métrica se reporta solo con evaluación humana. El **soporte de
evidencia** es secundario y tiene su propia marca: si su kappa cae bajo 0,70, se reporta solo
con evaluación humana o marcada como no confiable, sin afectar a la métrica principal. Un
kappa que no se puede calcular (el LLM-as-a-judge y las personas usan una sola clase de respuesta) cuenta como
«no cumple»; en todos los casos se informan además el **acuerdo observado** (la fracción de
respuestas en que coinciden) y la **prevalencia** (la fracción de «sí» de cada lado), porque
un kappa solo puede engañar cuando casi todas las respuestas son de una misma clase. La muestra
toma **una corrida sorteada por cada pregunta y condición**, y no todas las corridas, porque las
corridas de una pregunta son mediciones repetidas del mismo ítem y el análisis cuenta
preguntas; su tamaño es el 20 % de las respuestas juzgadas de cada condición y estrato, con tope
en las preguntas disponibles ([ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md)).

## 7–8. Análisis de errores y operación

*Fase 4: dónde nace cada error, y qué significaría usar esto de verdad.*

**Atribución determinista de error (OE4).** Para cada respuesta fallida de C2 se aplican
tres preguntas en orden fijo: se verifica primero si el hecho correcto existe en la base
compilada (si no, es error de **extracción**: la máquina lo anotó mal o no lo anotó); si
existe, si fue recuperado (si no, es error de **recuperación**: estaba, pero el sistema no lo
encontró al responder); si fue recuperado, es error de **síntesis** (lo encontró y aun así
redactó algo que lo contradice). Determinista quiere decir que son reglas fijas, no un
juicio caso a caso, y que cada error cae en una y sólo una categoría.

**Modos de falla documentados hasta ahora.** El piloto identificó seis relaciones "a ojo",
sin trazar transcripción; al contrastarlas, sólo **3 de 6 (50 %) se confirmaron**. Un caso —el
supuesto reemplazo del botón turbo por eliminación, IS1004c → IS1004d— resultó **falso**: el
resumen abstractivo de AMI afirma una eliminación que la transcripción contradice. La señal
`evidencia = 0 actos` (una decisión del resumen que no apunta a ningún pasaje de la
conversación) predijo el error antes de leer la transcripción, lo que respalda exigir
evidencia obligatoria como parte de la definición de decisión (§1).

**Riesgo de C2: la extracción de OpenKOS aún no alcanza para E2 y E3.** Una prueba sobre la
serie de desarrollo ES2015 con OpenKOS 0.5.2 (modelo local qwen3:8b) extrajo 4 objetos
Decision para toda la serie, frente a 29 decisiones con acuerdo evaluado en la anotación adjudicada del equipo (27 son decisiones finales; el archivo adjudicado tiene 34 filas).
Las decisiones extraídas agrupan temas completos y su cuerpo es un extracto de la
transcripción; OpenKOS ordena las decisiones solo por fecha de calendario, y las cuatro
reuniones de ES2015 comparten la misma fecha; y aplicar una revisión detectada exige una
confirmación humana por cada par. Con esa versión, C2 no podría responder E2 ni E3, y la
comparación C2 frente a C3 mediría sobre todo decisiones ausentes. Es una serie y una
corrida, con la versión 0.5.2; la medición se repite con la versión que finalmente se
fije. La versión a fijar queda abierta mientras OpenKOS se corrige. El plan: corregir OpenKOS
(extracción a nivel de decisión, orden dentro de un mismo día, aplicación automática opcional
de revisiones dirigidas, y la pérdida de la marca de atribución `USED:` cuando se escribe al
final de una oración, que afecta solo la tasa de citación; `jasonssdev/openkos#1348`,
`#1349`, `#1350` y `#1384`), medir cada corrección sobre series de desarrollo contra la
anotación adjudicada y fijar una versión publicada antes de tocar cualquier serie de
evaluación, registrándola en cada corrida (coherente con los ADR 0005 y 0006).

El orden dentro de un mismo día ya tiene una solución en el lado del proyecto. Importa porque
de él depende qué decisión se considera posterior a cuál, es decir, cuál reemplaza a cuál, y
con eso la respuesta a las preguntas del estrato E3 (cómo cambió una decisión). Por eso la
fecha de cada reunión que se entrega a OpenKOS ahora lleva hora: la hora real de inicio del
corpus AMI cuando existe (6 de las 14 series) y, cuando no existe (8 de las 14), una hora
sintética que solo preserva el orden de las reuniones a, b, c y d, que es el del escenario de
AMI. Esas horas sintéticas son una desviación declarada: no ocurrieron y no sirven para medir
tiempos ni intervalos entre reuniones. Los resultados se podrán comparar por origen de la hora
para comprobar que la diferencia no mueve las cifras. El detalle está en el
[ADR 0008](../decisions/0008-adr-fechas-de-reunion-para-openkos.md) y en el
[notebook 08](../../notebooks/08-jss-fechas-de-reunion.ipynb). Si no se alcanza ese nivel a tiempo, OE2 reporta el
resultado de extracción tal como sea y OE3 declara la limitación de C2; una C2 en ese estado
no se presenta como una comparación justa.

**Limitación: dos umbrales de troceo de OpenKOS se fijaron con una serie de evaluación (issue #145).** Antes de extraer, OpenKOS decide si una fuente se procesa en una sola llamada al modelo o si se trocea (*chunking*: partirla en ventanas de texto consecutivas y hacer una llamada por ventana). Esa decisión depende del largo del texto, con dos umbrales: 18.000 caracteres (`_CHUNK_THRESHOLD`) para textos que no son reuniones y 12.000 (`_MEETING_CHUNK_THRESHOLD`) para fuentes con forma de transcripción de reunión, que son las del proyecto. Ambos se fijaron en agosto de 2026, antes de la división desarrollo/evaluación del [ADR 0005](../decisions/0005-adr-development-evaluation-split.md) (20 de septiembre), con mediciones del modelo `qwen3:8b` sobre dos reuniones de TS3005, una serie de evaluación según ese ADR. TS3005b, de 40,8 KB, devolvía un único objeto de tipo Event en todas las corridas de llamada única, y partida en ventanas de unos 4 KB devolvía 9 (commit `578dea3d`, 7 de agosto). TS3005a, de 16.440 caracteres, agotaba el límite de generación de 8.192 en 2 de 3 corridas con llamada única y en 0 de 3 una vez troceada (commit `0c96ad9c`, 15 de agosto). Los valores siguen iguales en OpenKOS `2bc2c8fe` y ninguna medición posterior extiende ese uso (épica `jasonssdev/openkos#1556`). La regla del ADR 0005 pide congelar sobre desarrollo todo parámetro ajustado, de modo que esto se declara en lugar de omitirse.

*Qué controlan.* Solo el momento en que se trocea una fuente; no controlan qué se considera una decisión ni cómo se puntúa. Para C2 importan en un punto: el pase de decisiones de OpenKOS, que extrae las decisiones de una transcripción, recorre las mismas ventanas que la extracción de conceptos, de modo que el umbral determina si ese pase corre una vez sobre toda la reunión o una vez por ventana. Por eso pueden alterar qué decisiones aparecen, aunque no lo hacen mirando ninguna respuesta de la evaluación.

*Por qué no se espera que sesguen la evaluación.* (1) Lo que se midió fue si la llamada al modelo colapsaba o se cortaba, no si lo extraído coincidía con la referencia de la tesis: el código y su historial no usan la anotación adjudicada del proyecto. (2) Los umbrales no codifican contenido de TS3005; son un criterio de largo del texto, y cualquier reunión larga queda por encima de ellos, de modo que otra serie de evaluación se trocea igual. (3) El modelo medido es el generador declarado en el [documento 09](09-jss-modelos-y-justificacion.md) (`qwen3:8b`), así que la medición describe la configuración que se evalúa. (4) La versión de OpenKOS se registra en cada corrida.

*Qué queda como limitación.* (a) La medición de TS3005b contó cuántos objetos Decision admite su capa de anotación (3): es información de una serie de evaluación sobre la cantidad de decisiones, no sobre su contenido. (b) Cada valor se midió con pocas corridas (3 por brazo para TS3005a) y en dos reuniones; no se probó otro valor, y OpenKOS lo dice así. (c) Las reuniones cuyo largo cae entre 12.000 y 18.000 caracteres son las que un valor distinto cambiaría de camino; este documento no cuenta cuántas son por serie, porque esa cifra no sale todavía de ninguna función de `src/afg` ni de un notebook (el largo de cada reunión sí está en el manifiesto que muestra el [notebook 02](../../notebooks/02-jss-transcripciones.ipynb)). Si el análisis de resultados mostrara que la diferencia entre C2 y las demás condiciones se concentra en esas reuniones, esta limitación debe recalcularse con esa cuenta y reportarse junto a los resultados. No se enmienda el ADR 0005: sus consecuencias se cumplen en lo esencial, porque los valores no se ajustaron para acertar una respuesta de evaluación, y la excepción queda declarada aquí.

**Punto de equilibrio amortizado**, la métrica operativa que reemplaza a la latencia aislada.
Construir la base cuesta una vez; cada consulta sobre ella cuesta menos que una consulta
RAG, que vuelve a leer las transcripciones. La pregunta no es cuánto tarda una consulta, sino
a partir de cuántas consultas (n) se recupera lo invertido en construir:

> `costo_compilación + n · costo_consulta_estructurada  <  n · costo_consulta_RAG`

**Cómo se calculan los intervalos.** Un intervalo de confianza es el rango de valores
compatibles con lo observado, dado el tamaño de la muestra. Se usan dos métodos, cada uno
por una razón. Para una **proporción única con pocos casos** (la tasa de positivos, 5 de 11)
se usa el intervalo de **Wilson**: la aproximación normal (Wald) puede dar límites fuera de
[0, 1] y se reduce a ancho cero cuando se observan 0 casos o todos. Está implementado en
`afg.evaluation.metrics.wilson_interval` y se muestra en
[`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb)
§2; la proyección a los 81 candidatos de evaluación escala los límites del intervalo (≈37,
IC [17 – 58]). Para **todo resultado experimental** se usa **bootstrap percentil**: se
remuestrean las preguntas con reemplazo 10.000 veces, se recalcula la métrica en cada
remuestreo y se toman los percentiles 2,5 % y 97,5 % de los valores obtenidos. Los
parámetros están en `config/experiments.toml` (`bootstrap_resamples = 10_000`,
`bootstrap_confidence_level = 0.95`) y la función es `afg.evaluation.metrics.bootstrap_ci`,
con pruebas. La comparación entre condiciones (D16) aplica el mismo método a la **diferencia
pareada** por pregunta, C2 − C1.

Los resultados agrupados de precision, recall y F1 de OE2 (Experimento A) tienen una excepción: sus
decisiones no son independientes, porque las de una misma reunión comparten contexto, así que el
intervalo **principal** es un bootstrap percentil que remuestrea **reuniones completas**
(`afg.evaluation.scoring.meeting_cluster_intervals`, con los mismos 10.000 remuestreos, nivel 95 % y
semilla de `config/experiments.toml`). El intervalo de Wilson (precision, recall) y el bootstrap por
decisión (F1) se informan al lado como **referencia**. Con pocas reuniones el principal es burdo (una
serie tiene 4, con solo 35 remuestreos distintos), de modo que para una serie suelta es frágil
(ADR 0011).

**Qué significaría operar esto en una organización real.** El experimento completo depende
de que exista suficiente material de evolución entre reuniones para sostener el estrato E3
del banco de preguntas (las preguntas del tipo "¿cómo cambió la decisión sobre X?"). Esto es
**provisional**: adjudicando a mano los 11 candidatos de desarrollo, la tasa de positivos
fue 45,5 % (5/11), IC 95 % Wilson [21,3 % – 72,0 %], proyectando a evaluación ~37
relaciones, IC [17 – 58]. El intervalo de confianza (IC) expresa el rango en que podría
estar la cifra real dado lo poco que se ha visto; con 11 casos, es ancho. E3 exige ≥25
preguntas: el valor central alcanza, **la cota inferior del intervalo no**. Sigue siendo
**plausible, no demostrado** — la resolución final requiere adjudicar a mano al menos una
serie de evaluación, trabajo humano todavía pendiente.

El mínimo de E3 sigue siendo 25, pero el banco admite hasta 40 preguntas de ese estrato: se
escriben tantas como el material permita, para aumentar la probabilidad de detectar una mejora
más pequeña (con 25 preguntas una mejora real de 15 puntos se detecta alrededor de 57 % de las
veces; con 40, alrededor de 76 %, según el
[notebook 10](../../notebooks/10-jss-potencia-criterio-d16.ipynb)). El tope lo fija el material
de evolución disponible (~37 relaciones proyectadas, [notebook 01](../../notebooks/01-jss-viabilidad-e3.ipynb)),
no el esfuerzo; si se queda corto de 40, se declara como limitación de potencia.

## Glosario breve

| Término | Qué significa en este documento |
|---|---|
| Condición (C1, C2, C3) | Cada una de las tres maneras de responder preguntas que se comparan con todo lo demás igual. |
| Baseline | El punto de comparación (C1). Debe ser lo mejor que se pueda hacer con la práctica actual, no una versión débil. |
| Ground truth | Las decisiones y relaciones marcadas a mano, contra las que se mide la máquina. |
| Filtro léxico | Filtro (*blocking*) que reduce los 3.071 pares posibles a los 92 que las personas revisan. |
| Alineamiento | La regla para decidir si una decisión extraída por la máquina es la misma que una de la referencia. |
| τ (tau) | El parecido mínimo exigido en el alineamiento. Los resultados se reportan para varios valores; el principal es 0,70, con 0,75 y 0,80 como sensibilidad (ADR 0012). |
| Fuga | Usar información del futuro (reuniones posteriores) al anotar o extraer una decisión. |
| LLM-as-a-judge | Un segundo modelo que califica si una respuesta es correcta; se comprueba contra personas sobre una muestra. |
| Costo amortizado | A partir de cuántas consultas compensa haber construido la base. |
| Intervalo de confianza (IC) | Rango de valores compatibles con lo observado, dado el tamaño de la muestra. Un IC ancho indica poca información. |
| Wilson | Método para calcular el IC de una proporción con pocos casos; no produce límites fuera de 0 y 1. |
| Bootstrap | Método para calcular un IC remuestreando con reemplazo los datos observados muchas veces y recalculando la métrica. |
| Sesgo | Desviación sistemática: del filtro (pierde cierto tipo de pares), de la fuente (el corpus ya favorece a ciertos roles) o del sistema (agrega una desviación propia). |
| Kappa | Medida de acuerdo entre dos personas que descuenta el acuerdo que se daría por azar: 1 es acuerdo total y 0 es lo mismo que el azar. |
| Calibración | Anotación de prueba sobre una serie que no se evalúa, para comprobar que las personas entienden la guía igual antes de anotar lo que se reporta. |
| Recall | De lo que realmente existe, qué proporción logra encontrar un filtro o un sistema. |

## Principios rectores

Se cierra con los dos principios que el curso exige para toda la metodología:

**Alineada al problema, no a una técnica de moda.** Cada elección metodológica —el
filtro léxico, el protocolo de alineamiento, las tres condiciones— responde a una pregunta de
investigación declarada en el documento 03, no a la disponibilidad de una técnica.

**Transparente y reproducible.** Versiones exactas de modelos, semilla, context window y
parámetros de muestreo publicados; el punto de operación del filtro léxico versionado; y el
principio general del proyecto (`CONTRIBUTING.md` §7.1): si un número no puede reproducirse
desde `src/afg/` a través de un notebook, no entra en la tesis.

---

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| Las 8 secciones y el diseño experimental completo | [`../propuesta.md`](../propuesta.md) §5 |
| Cronología verificada vía `startTime` | [`../../config/corpus.toml`](../../config/corpus.toml), sección `[corpus.phases]` |
| Filtro léxico: coeficiente ≥0,30 y `\|A∩B\|≥2`; 712 vs 92 | [`../decisions/README.md`](../decisions/README.md), decisiones D5 y D9 |
| Piloto: 3/6 casos confirmados; botón turbo falso | [`../anotacion/manual-anotacion-oe1.md`](../anotacion/manual-anotacion-oe1.md) §3; [`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb) |
| Viabilidad de E3 (provisional): 45,5 % [21,3–72,0 %], proyección ~37 [17–58] | [`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb) |
| Referencia en inglés: traducción automática, no etiqueta; completa y vigente por validación | [`../anotacion/traduccion-referencia.md`](../anotacion/traduccion-referencia.md); `src/afg/evaluation/translation.py` |
| Regla "todo número reproducible desde `src/afg/`" | [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) §7.1 |
| Filtro léxico: sesgos, comparación por sitio y Tarea C | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) §4.1; `src/afg/annotation/blocking.py` |
| Wilson y bootstrap percentil | [`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb) §2; `src/afg/evaluation/metrics.py` (`wilson_interval`, `bootstrap_ci`); [`../../config/experiments.toml`](../../config/experiments.toml) |
| Acumulación por serie (D15) y criterio de éxito (D16) | [`../decisions/README.md`](../decisions/README.md), decisiones D15 y D16 |
| Enmienda de D16 (diferencia pareada), decisión de la verificación humana del LLM-as-a-judge, kappa indefinido y muestra de una corrida por pregunta | [`../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md`](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md); [`../../notebooks/10-jss-potencia-criterio-d16.ipynb`](../../notebooks/10-jss-potencia-criterio-d16.ipynb); `src/afg/experiments/power.py` |
| Ratificación del ámbito de alineación y del rol, e intervalo principal por reuniones del Experimento A | [`../decisions/0011-adr-alineacion-rol-e-intervalos-del-experimento-a.md`](../decisions/0011-adr-alineacion-rol-e-intervalos-del-experimento-a.md); [`../../notebooks/14-jss-alineacion-experimento-a.ipynb`](../../notebooks/14-jss-alineacion-experimento-a.ipynb); `src/afg/evaluation/scoring.py` (`meeting_cluster_intervals`, `pool_scores`) |
| Ajuste de C1: 1.200 caracteres, 1 turno de solapamiento, K = 5; contexto de unos 7.400 caracteres | [`../decisions/0007-adr-ajuste-c1-y-presupuesto-de-contexto.md`](../decisions/0007-adr-ajuste-c1-y-presupuesto-de-contexto.md) (enmienda 2026-10-15); [`../../notebooks/06-jss-ajuste-c1.ipynb`](../../notebooks/06-jss-ajuste-c1.ipynb) |
| Fechas de reunión: hora real en 6 de 14 series, sintética en 8 | [`../decisions/0008-adr-fechas-de-reunion-para-openkos.md`](../decisions/0008-adr-fechas-de-reunion-para-openkos.md); [`../../notebooks/08-jss-fechas-de-reunion.ipynb`](../../notebooks/08-jss-fechas-de-reunion.ipynb) |
| Riesgo de C2 (4 extraídas frente a 29 decisiones con acuerdo evaluado en ES2015; 27 finales, 34 filas) | [`../../data/processed/decisions/ES2015.decisions.adjudicated.csv`](../../data/processed/decisions/ES2015.decisions.adjudicated.csv); `jasonssdev/openkos#1348`, `#1349`, `#1350`, `#1384`; [`../decisions/0005-adr-development-evaluation-split.md`](../decisions/0005-adr-development-evaluation-split.md); [`../decisions/0006-adr-c1-rag-separado-con-respuesta-de-openkos.md`](../decisions/0006-adr-c1-rag-separado-con-respuesta-de-openkos.md) |
| Umbrales de troceo de OpenKOS fijados con TS3005 (18.000 y 12.000 caracteres) | OpenKOS, `src/openkos/extraction/concept.py` en los commits `58b9e699` y `2bc2c8fe`; historial `578dea3d` y `0c96ad9c`; issue #145; [`../decisions/0005-adr-development-evaluation-split.md`](../decisions/0005-adr-development-evaluation-split.md) |
| Calibración: kappa 0,094 en ES2015, guía corregida y recalibración sobre TS3009 | [`../../notebooks/04-jss-anotacion-f1-calibracion.ipynb`](../../notebooks/04-jss-anotacion-f1-calibracion.ipynb); [`../anotacion/manual-anotacion-oe1.md`](../anotacion/manual-anotacion-oe1.md) §2 y §6; [`../anotacion/asignacion/README.md`](../anotacion/asignacion/README.md) (Fase 1) |
| LLM-as-a-judge: `gpt-oss:20b`, kappa 0,95; acuerdo humano 1,00 y 0,87; limitación del identificador | [`../../notebooks/05-jss-seleccion-juez.ipynb`](../../notebooks/05-jss-seleccion-juez.ipynb); [`../../config/experiments.toml`](../../config/experiments.toml), sección `[judge]`; [`../anotacion/calibracion-juez.md`](../anotacion/calibracion-juez.md) |
| Las cuatro fases y su aporte | [`03-jss-objetivos.md`](03-jss-objetivos.md), objetivos específicos OE1–OE4 |
