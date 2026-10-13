# Metodología

| | |
|---|---|
| **Documento** | 06 — Metodología |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 2.2 |
| **Fecha** | 2026-10-13 |
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

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## El experimento en una página

Antes de los ocho pasos, lo esencial. El proyecto compara tres maneras de responder a la
pregunta "¿qué decidió el equipo sobre X, y cómo cambió?" sobre las mismas reuniones, con el
mismo modelo de lenguaje, el mismo computador y el mismo límite de texto que el modelo
puede leer de una vez. Se llaman **condiciones**:

| | Condición | Qué es | Para qué sirve en la comparación |
|---|---|---|---|
| **C1** | RAG documental | Buscar en las transcripciones los fragmentos parecidos a la pregunta y redactar una respuesta con ellos. Es la práctica actual. | El piso: lo que cualquiera haría hoy. |
| **C2** | Base construida por la máquina | Un modelo de lenguaje lee las transcripciones, extrae las decisiones y las guarda en una base con sus relaciones. Es la propuesta. | Lo que se evalúa. |
| **C3** | Base construida por personas | La misma base de C2, pero llenada con la anotación humana del conjunto de referencia. Sin errores de extracción. | Separa dos cosas: la distancia C1→C3 es el valor de tener la base; la distancia C3→C2 es el costo de los errores de la máquina. |

Sin C3 no se podría distinguir si una mala respuesta de C2 se debe a que la idea de la base
no sirve o a que la máquina la llenó mal. Esa es la limitación de los trabajos previos que
se señala en el documento 01, y la razón de ser de este diseño.

El trabajo se organiza en **cuatro fases**, en orden, porque cada una necesita la anterior:

1. **El conjunto de referencia.** Personas marcan a mano las decisiones de 14 series de
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

**Unidad de análisis.** Lo primero es fijar qué se va a contar. La unidad es la decisión
individual y el par de decisiones dentro de una serie (un par es una decisión de una
reunión frente a una decisión de otra reunión del mismo equipo). Para que algo cuente como
decisión tiene que cumplir tres condiciones: ser explícita (al menos un acto de diálogo, es
decir, una intervención de alguien, la formula o ratifica), aceptada (no queda como
propuesta abierta) y anclada (identifica el objeto y el contenido: sobre qué se decide y
qué). Las propuestas no aceptadas se registran como no-decisiones: hacen falta para medir
falsos positivos, es decir, los casos en que la máquina diga "decisión" donde no la hubo.

**Métricas de OE2** (fase 2): precisión, cobertura y F1 a nivel decisión; exactitud de tipo
y de dirección a nivel relación temporal, reportadas por separado. Precisión es qué parte de
lo que la máquina extrajo era realmente una decisión; cobertura, qué parte de las decisiones
reales encontró; F1 las combina. **Métricas de OE3** (fase 3): corrección de respuesta,
soporte de evidencia, citación correcta, corrección del rechazo (si el sistema sabe decir
"no hay información" cuando no la hay), y costo amortizado (§7).

**Umbrales operativos provisionales.** Un paso 1 sin números es una declaración de
intenciones. Se fijan ahora para que sea cuantitativo; se revisan en AFG2 con los primeros
datos y cualquier cambio se registra en `docs/decisions/`.

| Qué | Umbral | Qué pasa si no se cumple |
|---|---|---|
| Concordancia del alineamiento automático con el emparejamiento manual (100 pares) | ≥ 0,80 | Se revisa la grilla de τ y se repite la validación |
| Concordancia juez automático – humano (20 % de las respuestas) | kappa ≥ 0,70 | Se descarta el juicio automático y se reporta solo la evaluación humana |
| Tamaño del estrato E3 | ≥ 25 preguntas | E3 se reformula como análisis de casos con reporte cualitativo |
| Diferencia entre condiciones | Intervalos bootstrap del 95 % que no se solapan | No se afirma diferencia; se reporta como no concluyente |
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
si el intervalo bootstrap del 95 % de C2 queda por encima del de C1 sin solaparse; si los
intervalos se solapan, el resultado se reporta como no concluyente y nunca como éxito. Todo
lo demás es secundario y descriptivo: precisión, cobertura y F1 de OE2, exactitud de tipo y
de dirección, soporte de evidencia, citación, corrección del rechazo, costo amortizado, los
estratos E1, E2 y E4, y la comparación C2 frente a C3. Cómo se calculan los intervalos se
explica en los pasos 7–8.

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

Resumida aquí; el detalle completo —marco muestral, selección de 14 series, split
desarrollo/evaluación, los cuatro N, composición lingüística, autoría por rol, anclaje a
evidencia, riesgos y plan de saneamiento— está en
[`02-jss-fuente-de-datos.md`](02-jss-fuente-de-datos.md). El resultado que condiciona todo lo
que sigue: 14 series, 56 reuniones, 343 decisiones, 3.071 pares entre reuniones, 92 pares
candidatos tras el bloqueo. Esos 92 pares son los que las personas anotan en la fase 1.

**El filtro léxico y sus sesgos.** Como esos 92 pares condicionan todo el conjunto de
referencia, conviene explicar cómo se llega a ellos. Cada frase de decisión se pasa a
minúsculas, se conservan solo las palabras de al menos 3 letras y se descartan las palabras
vacías ("de", "que", "el"). Luego, para cada par de decisiones de reuniones distintas, se
calcula el **coeficiente de solapamiento**: palabras compartidas dividido por el tamaño de la
frase más corta. Se usa este coeficiente y no Jaccard porque una reversión suele ser una
frase corta posterior que apunta a una larga anterior: en el par del botón turbo, Jaccard da
0,118 y pierde el caso, mientras que el solapamiento da 0,400 y lo conserva. Un par es
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
entró en la elección del punto de operación; (5) el conjunto de referencia favorece a los
métodos léxicos (D6 evita el sesgo inverso, no este). Una comprobación medida: la proporción
de candidatos por sitio de grabación en el punto de operación es parecida (ES 44 pares,
3,2 %; IS 22, 3,1 %; TS 26, 2,6 %), pero eso **no** demuestra que la pérdida sea igual en
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

## 3–4. Diseño analítico y líneas base

*Fase 3: las tres condiciones y la regla de "todo lo demás igual".*

**Tres condiciones**, mismo modelo generativo, mismo modelo de *embeddings*, mismo hardware y
mismo presupuesto de contexto. Un modelo de *embeddings* convierte texto en números para
poder medir cuánto se parecen dos fragmentos; el presupuesto de contexto es cuánto texto
puede leer el modelo de una vez. Sin esta restricción, cualquier diferencia observada es
inatribuible: si C2 usara un modelo más grande que C1, no se sabría si ganó por la base o
por el modelo.

- **C1 — RAG documental.** Transcripciones segmentadas en fragmentos e indexadas con
  búsqueda híbrida (léxica, por palabras exactas, y densa, por parecido de significado).
  **Línea base honesta:** una línea base es el punto de comparación, y una línea base
  débil hace que cualquier propuesta parezca buena. Por eso los parámetros de segmentación
  y el número de fragmentos recuperados se ajustan sobre el conjunto de desarrollo (77
  decisiones, 11 candidatos), no se fijan arbitrariamente. Una línea base debilitada
  invalida el experimento completo.
- **C2 — Compilación automática.** Extracción con modelo local, persistencia con
  procedencia (cada decisión guardada con la reunión y el pasaje de donde salió), consulta
  sobre los objetos compilados.
- **C3 — Compilación desde la referencia.** Idéntica a C2 salvo que los objetos provienen de
  la anotación humana de OE1.

**El bloqueador de candidatos** pertenece a la fase 1, pero sigue el mismo principio. Es el
filtro que decide qué pares de decisiones se ofrecen a anotación humana, porque leer los
3.071 pares posibles no es viable. Se ajusta también sobre desarrollo, y exige coeficiente
de solapamiento ≥ 0,30 **y** al menos 2 tokens compartidos. El coeficiente de solapamiento
mide qué proporción de las palabras de la frase más corta aparece en la otra; un token es
una palabra. Se usa solapamiento y no Jaccard (que divide por el total de palabras distintas
de ambas frases y castiga a las frases cortas) porque Jaccard pierde el caso de regresión
del bloqueador: el par del botón turbo, Jaccard 0,118 frente a solapamiento 0,400. Ese par
es el de solape léxico más exigente medido en el piloto y **no** una relación confirmada: la
verificación contra transcripción mostró después que esa reversión no ocurrió (documento 02,
§4.4). Se conserva como prueba de que el filtro sigue dejando pasar frases cortas. Y se
exige el mínimo absoluto de tokens porque el coeficiente solo, sobre las 14 series reales,
seleccionaba 712 de 3.071 pares (23,2 %, ≈18 h de anotación) en vez del 5,5 % que sugería
el piloto; con el mínimo añadido, 92 (3,0 %, ≈2,3 h), sin perder el caso de prueba.

## 5–6. Modelado y validación

*Fases 1 y 2: con qué modelos se extrae, cómo se decide si acertaron y por qué la referencia
la hacen personas.*

**Modelos.** Modelos generativos de ejecución local (familia Qwen o equivalente, en escalas
contrastables) y un modelo de *embeddings* multilingüe. "Ejecución local" significa que
corren en un computador propio, sin enviar datos a servicios externos; "escalas
contrastables" significa tamaños de modelo distintos que se puedan comparar. Versiones
exactas, semilla, tamaño de ventana de contexto y parámetros de muestreo se fijan y se
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
similitud coseno de *embeddings* sobre el par (objeto, contenido) por encima de un umbral τ,
es decir, se consideran parecidas las decisiones cuya representación numérica supera cierto
parecido mínimo; (2) emparejamiento uno-a-uno por asignación de costo máximo —algoritmo
húngaro—, no por vecino más cercano codicioso: se busca el mejor emparejamiento global de
todas las decisiones a la vez, en lugar de asignar cada una a su vecina más parecida y
dejar que las últimas se queden sin pareja; (3) validación contra emparejamiento manual
sobre al menos 100 pares, con concordancia reportada; (4) todos los F1 se reportan como
**curva sobre τ**, no en un único punto, porque elegir un único τ permitiría escoger el que
dé mejor resultado. Se descartan PR-AUC y matrices de confusión como métricas principales
porque el sistema emite conjuntos en lenguaje natural, no puntajes sobre clases fijas;
Recall@K se conserva sólo para la etapa de recuperación dentro de C1 y C2.

**El filtro de candidatos y su punto de operación** es el mismo bloqueador de §3–4, aplicado
antes de la anotación humana: 92 pares candidatos de 3.071 posibles, versionado
(`BLOCKER_VERSION`) para que cambiar el punto de operación invalide explícitamente los
candidatos ya generados en vez de mezclarlos en silencio. Si el filtro cambia, los pares
anotados con el filtro anterior quedan marcados como de otra versión, no mezclados.

**Anotación humana, por qué no se automatiza.** Las etiquetas del conjunto de referencia las
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
Decision para toda la serie, frente a 29 decisiones en la anotación adjudicada del equipo.
Las decisiones extraídas agrupan temas completos y su cuerpo es un extracto de la
transcripción; OpenKOS ordena las decisiones solo por fecha de calendario, y las cuatro
reuniones de ES2015 comparten la misma fecha; y aplicar una revisión detectada exige una
confirmación humana por cada par. Con esa versión, C2 no podría responder E2 ni E3, y la
comparación C2 frente a C3 mediría sobre todo decisiones ausentes. Es una serie y una
corrida, con la versión 0.5.2 y no con la 0.5.4 que fija el ADR 0006; la medición se repite
con la versión que finalmente se fije. El plan: corregir OpenKOS (extracción a nivel de decisión, orden dentro de un mismo
día, aplicación automática opcional de revisiones dirigidas; `jasonssdev/openkos#1348`,
`#1349`, `#1350`), medir cada corrección sobre series de desarrollo contra la anotación
adjudicada y fijar una versión publicada antes de tocar cualquier serie de evaluación
(coherente con los ADR 0005 y 0006). Si no se alcanza ese nivel a tiempo, OE2 reporta el
resultado de extracción tal como sea y OE3 declara la limitación de C2; una C2 en ese estado
no se presenta como una comparación justa.

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
con pruebas.

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

## Glosario breve

| Término | Qué significa en este documento |
|---|---|
| Condición (C1, C2, C3) | Cada una de las tres maneras de responder preguntas que se comparan con todo lo demás igual. |
| Línea base | El punto de comparación (C1). Debe ser lo mejor que se pueda hacer con la práctica actual, no una versión débil. |
| Conjunto de referencia | Las decisiones y relaciones marcadas a mano, contra las que se mide la máquina. |
| Bloqueador | Filtro que reduce los 3.071 pares posibles a los 92 que las personas revisan. |
| Alineamiento | La regla para decidir si una decisión extraída por la máquina es la misma que una de la referencia. |
| τ (tau) | El parecido mínimo exigido en el alineamiento. Los resultados se reportan para varios valores, no para uno elegido. |
| Fuga | Usar información del futuro (reuniones posteriores) al anotar o extraer una decisión. |
| Juez automático | Un segundo modelo que califica si una respuesta es correcta; se comprueba contra personas sobre una muestra. |
| Costo amortizado | A partir de cuántas consultas compensa haber construido la base. |
| Intervalo de confianza (IC) | Rango de valores compatibles con lo observado, dado el tamaño de la muestra. Un IC ancho indica poca información. |
| Wilson | Método para calcular el IC de una proporción con pocos casos; no produce límites fuera de 0 y 1. |
| Bootstrap | Método para calcular un IC remuestreando con reemplazo los datos observados muchas veces y recalculando la métrica. |
| Sesgo | Desviación sistemática: del filtro (pierde cierto tipo de pares), de la fuente (el corpus ya favorece a ciertos roles) o del sistema (agrega una desviación propia). |
| Recall (cobertura) | De lo que realmente existe, qué proporción logra encontrar un filtro o un sistema. |

## Principios rectores

Se cierra con los dos principios que el curso exige para toda la metodología:

**Alineada al problema, no a una técnica de moda.** Cada elección metodológica —el
bloqueador, el protocolo de alineamiento, las tres condiciones— responde a una pregunta de
investigación declarada en el documento 03, no a la disponibilidad de una técnica.

**Transparente y reproducible.** Versiones exactas de modelos, semilla, ventana de contexto y
parámetros de muestreo publicados; el punto de operación del bloqueador versionado; y el
principio general del proyecto (`CONTRIBUTING.md` §7.1): si un número no puede reproducirse
desde `src/afg/` a través de un notebook, no entra en la tesis.

La versión 1.3 cambia la forma de contarlo, no el contenido: las cifras, los umbrales, el
diseño experimental y la numeración de secciones son los mismos de la versión 1.2. La
versión 2.0 agrega decisiones (D15, D16), el detalle del filtro y de los intervalos, y un
riesgo de C2; la numeración de secciones no cambia.

---

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| Las 8 secciones y el diseño experimental completo | [`../propuesta.md`](../propuesta.md) §5 |
| Cronología verificada vía `startTime` | [`../../config/corpus.toml`](../../config/corpus.toml), sección `[corpus.phases]` |
| Bloqueador: coeficiente ≥0,30 y `\|A∩B\|≥2`; 712 vs 92 | [`../decisions/README.md`](../decisions/README.md), decisiones D5 y D9 |
| Piloto: 3/6 casos confirmados; botón turbo falso | [`../anotacion/manual-anotacion-oe1.md`](../anotacion/manual-anotacion-oe1.md) §3; [`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb) |
| Viabilidad de E3 (provisional): 45,5 % [21,3–72,0 %], proyección ~37 [17–58] | [`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb) |
| Regla "todo número reproducible desde `src/afg/`" | [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) §7.1 |
| Filtro léxico: sesgos, comparación por sitio y Tarea C | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) §4.1; `src/afg/annotation/blocking.py` |
| Wilson y bootstrap percentil | [`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb) §2; `src/afg/evaluation/metrics.py` (`wilson_interval`, `bootstrap_ci`); [`../../config/experiments.toml`](../../config/experiments.toml) |
| Acumulación por serie (D15) y criterio de éxito (D16) | [`../decisions/README.md`](../decisions/README.md), decisiones D15 y D16 |
| Riesgo de C2 (4 frente a 29 decisiones en ES2015) | `jasonssdev/openkos#1348`, `#1349`, `#1350`; [`../decisions/0005-adr-development-evaluation-split.md`](../decisions/0005-adr-development-evaluation-split.md); [`../decisions/0006-adr-c1-rag-separado-con-respuesta-de-openkos.md`](../decisions/0006-adr-c1-rag-separado-con-respuesta-de-openkos.md) |
| Las cuatro fases y su aporte | [`03-jss-objetivos.md`](03-jss-objetivos.md), objetivos específicos OE1–OE4 |
