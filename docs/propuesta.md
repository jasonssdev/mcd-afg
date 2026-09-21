# Evaluación experimental de la extracción automática y la representación persistente de decisiones organizacionales y su evolución entre reuniones, frente a Recuperación Aumentada (RAG)

## 1. Definición del Problema

### 1.1 El fenómeno

Las organizaciones pierden sus decisiones. No porque no queden registradas —hoy casi toda reunión se transcribe— sino porque quedan registradas como **texto conversacional no estructurado**, donde una decisión no es una entidad recuperable sino un pasaje difuso repartido entre varios turnos de habla, frecuentemente sin marcador lingüístico explícito.

El problema se agrava cuando la decisión **cambia**. Un equipo decide algo en la reunión de octubre, lo matiza en noviembre y lo revierte en diciembre. Las tres reuniones quedan transcritas; ninguna de las tres contiene el hecho más importante, que es la **relación** entre ellas. Reconstruir esa trayectoria exige leer las tres y recordar la primera al llegar a la tercera — exactamente lo que ninguna organización hace de forma sostenida.

### 1.2 Por qué RAG no lo resuelve

El enfoque estándar para consultar este material es la Recuperación Aumentada (RAG): ante una pregunta, se recuperan fragmentos relevantes de las transcripciones y se sintetiza una respuesta. RAG es efectivo para preguntas cuya respuesta está contenida en un pasaje, pero tiene una limitación estructural para este dominio:

- **No mantiene estado entre consultas.** El razonamiento hecho para responder una pregunta se descarta; la décima consulta parte tan ignorante como la primera.
- **No representa la relación entre pasajes distantes.** Que un fragmento de diciembre *revierta* uno de octubre no es una propiedad de ninguno de los dos fragmentos, sino del par. La recuperación por similitud semántica no la captura: precisamente porque ambos hablan del mismo tema, compiten entre sí por el mismo espacio de contexto, y el sistema puede recuperar uno u otro indistintamente sin señal de cuál es vigente.
- **Su unidad de recuperación es el fragmento, no la decisión.** No hay garantía de que los límites del *chunk* coincidan con los límites del acto decisorio.

Estas no son deficiencias de implementación corregibles con mejor *chunking* o mejor *embedding*; son consecuencia de que la representación sea el documento original.

La alternativa —construir un grafo o índice estructurado antes de consultar— está siendo explorada activamente (notablemente GraphRAG, Edge et al., 2024), pero la evidencia disponible compara sistemas completos entre sí, no aísla **qué parte de la diferencia proviene de la representación y qué parte del proceso que la construye**.

### 1.3 El riesgo simétrico

Compilar decisiones en una base estructurada mediante Modelos de Lenguaje introduce un riesgo que RAG no tiene. En RAG, un error de síntesis es efímero: afecta una respuesta y desaparece. En una base persistente, un error de extracción **se escribe y se lee muchas veces**: adquiere la apariencia de hecho verificado, se convierte en premisa de razonamientos posteriores, y contamina la memoria que pretendía preservar.

La literatura establecida mide exhaustivamente la exactitud de la extracción en una pasada (Text2KGBench; Zhu et al., 2024; Xu et al., 2024) y la incertidumbre en la construcción de grafos de conocimiento (Jarnac et al., 2025). Lo que no está medido de forma rigurosa y revisada por pares es **el costo aguas abajo de persistir un error de extracción** — cuánto de la degradación final de un sistema se explica por errores que quedaron escritos, frente a errores de recuperación o de síntesis. Los dos trabajos que más se acercan son preprints sin revisión (Cai & O'Connor, 2025; Zhang & Li, 2026).

### 1.4 Evidencia de que el objeto mismo es inestable

Un obstáculo previo, y poco reconocido, es que **"decisión" no es todavía un objetivo de anotación estable**. La evidencia publicada es contundente:

- Hsueh & Moore (2007a) anotaron actos de diálogo relacionados con decisiones en AMI: **554 de 37.400 actos, un 1,4%** del total.
- Fernández et al. (2008) desarrollaron un esquema independiente sobre **las mismas 17 reuniones**, con acuerdo interno razonable (kappa 0,63–0,73 entre sus propios anotadores).
- Al comparar ambos conjuntos de anotaciones sobre datos idénticos, Fernández et al. reportan **kappa negativo y sólo 12,22% de solapamiento**.

Dos equipos competentes, el mismo corpus, el mismo constructo nominal, y desacuerdo peor que el azar. Esto no invalida la línea de trabajo: indica que cualquier evaluación seria debe **operacionalizar "decisión" de forma más restringida y verificable** que como se ha hecho hasta ahora, y reportar su propia confiabilidad de anotación en lugar de asumirla.

### 1.5 Formulación

> **El problema central es la ausencia de una medición controlada que separe tres cosas hoy confundidas: el valor de mantener una representación persistente y estructurada de decisiones; el costo de los errores que introduce su extracción automática; y la contribución específica de representar la evolución temporal de una decisión a lo largo de una serie de reuniones.**

Sin esa separación, un resultado favorable a un sistema estructurado no permite saber si conviene invertir en mejores extractores, en mejores representaciones, o en ninguna de las dos.

### 1.6 El vacío específico que este trabajo aborda

Hasta donde alcanza la revisión realizada, **ninguna capa de anotación, conjunto de datos o trabajo publicado enlaza una decisión de una reunión con su revisión, reafirmación o reversión en una reunión posterior de la misma serie**.

Los antecedentes más cercanos y su distancia al problema:

| Antecedente | Qué hace | Por qué no cierra el vacío |
|---|---|---|
| Murray et al. (2009), *Decision Audit Task* | Pide a 50 sujetos humanos rastrear la historia de una decisión a través de las cuatro reuniones de la serie ES2008 | Protocolo de evaluación humana sobre **una serie y un hilo decisorio**; no libera anotación estructurada |
| Marcas `external` y `recap` de la guía de *Decision Discussion Segmentation* de AMI | Señalan que una decisión viene de fuera de la reunión o que se está repasando una previa | Son **banderas binarias sin puntero**: no indican *cuál* decisión previa ni *de qué* reunión, y `external` mezcla decisiones de reuniones anteriores con requisitos inyectados por el escenario |
| AMIDA *Automatic Content Linking Device* | Recupera fragmentos de reuniones pasadas durante una reunión en curso | Recuperación por palabras clave; sin representación de decisión ni enlace decisión-a-decisión |
| Benchmarks de memoria multisesión (LoCoMo, LongMemEval y sucesores) | Evalúan memoria a través de sesiones | **Completamente sintéticos**; se motivan con escenarios de reuniones pero no usan datos reales de reuniones |

La estructura de AMI hace este vacío especialmente llamativo: el corpus fue diseñado con series de cuatro reuniones del mismo equipo precisamente porque, en palabras de Carletta (2007), *"los equipos de diseño a menudo quieren revisitar decisiones anteriores para averiguar por qué se tomaron"*. El sustrato existe desde 2006 y el enlace nunca se anotó.

---

## 2. Objetivo General

Diseñar, implementar y evaluar experimentalmente un método de extracción automática y representación persistente de decisiones organizacionales —incluyendo su evolución a través de reuniones sucesivas— utilizando modelos de lenguaje de ejecución local, con el fin de **cuantificar por separado** el valor aportado por la representación, el costo introducido por los errores de su extracción automática, y las condiciones bajo las cuales el resultado neto supera a un sistema RAG aplicado directamente sobre las transcripciones originales.

---

## 3. Objetivos Específicos

### OE1 — Construir un conjunto de referencia de decisiones con evolución entre reuniones

Derivar un conjunto de referencia **a partir de las capas de anotación ya existentes en AMI**, extendiéndolas con la única anotación que el corpus no posee: el enlace temporal entre reuniones.

- **Base reutilizada:** los encabezados `DECISIONS` de los resúmenes abstractivos, enlazados a actos de diálogo a través del resumen extractivo (la misma operacionalización de Hsueh & Moore, lo que preserva comparabilidad con la literatura), y la capa *Decision Discussion Segmentation*, presente en 47 reuniones del corpus.
- **Anotación nueva:** para cada par de decisiones dentro de una misma serie, una relación tipada del conjunto cerrado
  `{ introduce, reafirma, refina, revierte, reemplaza, no-relacionada }`,
  con la reunión y el segmento de origen como evidencia obligatoria.
- **Confiabilidad declarada:** doble anotación independiente sobre al menos el 25% de las series, reporte de kappa de Cohen, y protocolo de adjudicación documentado. Dado el antecedente de kappa negativo entre esquemas previos (§1.4), este objetivo **no asume** que el constructo sea estable: lo mide.

> Este conjunto de referencia es el primer aporte del trabajo y es útil con independencia del resultado experimental.

### OE2 — Medir la calidad de la extracción automática (Experimento A)

Cuantificar la capacidad de modelos de lenguaje de ejecución local para extraer decisiones y sus relaciones temporales, contra el conjunto de referencia de OE1.

- **Nivel decisión:** precisión, cobertura y F1, bajo un protocolo de alineamiento declarado explícitamente (§5.4).
- **Nivel relación temporal:** exactitud de la etiqueta y, reportada por separado, **exactitud de la dirección** — si el sistema identifica correctamente cuál decisión revisa a cuál, o invierte el sentido.
- **Estratificación obligatoria por rol del hablante** (§6.3). El eje nativo/no nativo de inglés **ya no es estratificación obligatoria**: baja a limitación declarada, porque la lengua materna está perfectamente anidada en el sitio de grabación (decisiones **D7** y **D8**; §5.1 y §6.3).

### OE3 — Medir la utilidad funcional en tres condiciones (Experimento B)

Comparar el desempeño frente a un mismo banco de preguntas estratificado bajo tres condiciones:

| | Condición | Rol |
|---|---|---|
| **C1** | RAG documental sobre las transcripciones originales | **Piso** — la práctica actual |
| **C2** | Base estructurada construida automáticamente | **La propuesta bajo evaluación** |
| **C3** | Base estructurada construida desde la anotación de OE1 | **Referencia superior** — la misma representación sin errores de extracción |

- **Calidad:** corrección de la respuesta y **soporte de evidencia** (si cada afirmación es atribuible a una fuente identificada, en la línea de Rashkin et al., 2023), más **corrección del rechazo**: qué hace cada condición ante una pregunta que el material no puede responder.
- **Operativas:** consumo de memoria, y **costo amortizado** — no latencia aislada, sino el punto de equilibrio en número de consultas a partir del cual el costo total de compilar más consultar es inferior al de consultar repetidamente (§5.6).

> **C3 no se denomina "techo teórico".** Una anotación humana con confiabilidad medida es una *referencia*, no un límite superior demostrable; llamarla techo sería una afirmación más fuerte que la evidencia disponible, especialmente dado el §1.4.

### OE4 — Atribuir el error final a su etapa de origen

Para cada respuesta incorrecta o sin soporte producida bajo C2, determinar si el error se originó en la **extracción** (el hecho quedó mal escrito en la base), en la **recuperación** (el hecho correcto existía pero no fue recuperado) o en la **síntesis** (el material correcto fue recuperado y la respuesta lo contradice).

Este objetivo es lo que conecta los Experimentos A y B y es el que aborda directamente el vacío identificado en §1.3. La comparación C2 contra C3 aísla el efecto total del error de extracción; la atribución por etapa lo descompone.

---

## 4. Hipótesis

Se declaran antes de la ejecución para evitar reinterpretación posterior de los resultados.

| | Hipótesis | Fundamento |
|---|---|---|
| **H1** | C2 y C3 superarán a C1 en preguntas de **evolución** (*¿cambió la decisión sobre X?*), con diferencia pequeña o nula en preguntas de **hecho puntual** | La ventaja de la representación es relacional; donde no hay relación que representar, no debería haber ventaja |
| **H2** | La brecha C3 − C2 será **mayor en las relaciones temporales que en la identificación de decisiones** | Extraer que algo se decidió es más fácil que extraer correctamente que una decisión reemplaza a otra |
| **H3** | La **dirección** de las relaciones temporales será un modo de falla dominante, y no mejorará proporcionalmente con el tamaño del modelo | Observación preliminar en el sistema instrumento: ~25% de direcciones invertidas, sin mejora al pasar de un modelo de 8B a uno de 27B, aunque la exactitud del *tipo* de relación sí mejoró sustancialmente |
| **H4** | C1 exhibirá mayor tasa de respuestas **confiadas pero desactualizadas** ante preguntas de evolución | Consistente con lo reportado por RealTime QA cuando la recuperación es insuficiente |

**Plan ante resultado negativo.** Si H1 no se sostiene —si RAG documental iguala a la representación estructurada incluso en preguntas de evolución— el resultado es igualmente publicable y constituye el aporte principal: sería la primera medición controlada que acota el valor de compilar en este dominio. El trabajo está diseñado para que **el aporte sea la medición, no el sistema**. Ninguna conclusión del proyecto depende de que la representación estructurada gane.

---

## 5. Metodología

### 5.0 Selección del corpus y verificación previa

**Corpus:** AMI Meeting Corpus (Carletta et al., 2006; Carletta, 2007). ~100 horas, en torno a 170 reuniones, de las cuales aproximadamente dos tercios corresponden al escenario de diseño de un control remoto de televisión, organizado en **series de cuatro reuniones con los mismos cuatro participantes** (*Project kick-off*, *Functional design*, *Conceptual design*, *Detailed design*). Licencia **CC BY 4.0**. La página de licencia declara esos términos pero **no declara fecha de entrada en vigor** (verificado el 2026-09-20); abril de 2017 es la fecha de publicación del paquete de anotaciones `ami_public_manual_1.6.2.zip`, de modo que la fecha a menudo repetida es una inferencia sobre cuándo empezaron a regir los términos, no una afirmación del licenciante, y no debe presentarse como fecha de la licencia. Debe citarse la página de licencia vigente, no los artículos originales, que describen una licencia anterior, más restrictiva.

**Muestra, en dos niveles:**

- **Experimento A (extracción):** las **47 reuniones** que cuentan con la capa *Decision Discussion Segmentation* (DDS). No requieren series completas. El conteo se verificó en el paso cero por descubrimiento directo de los archivos de anotación, no por el inventario publicado.
- **Experimento B y OE1 (evolución):** **14 series completas — 56 reuniones y 343 frases de decisión.** No son las 6 series que llevan la capa DDS, sino una selección hecha sobre el marco muestral del resumen abstractivo, que es el que el paso cero obligó a adoptar (ver más abajo). El criterio de selección, la evidencia que lo respalda y las alternativas descartadas están en [ADR 0004](decisions/0004-adr-oe1-series-selection.md): `summlink` presente en las cuatro reuniones de la serie —sin él una decisión no puede anclarse a evidencia y falla la condición 3 de §5.2—, inclusión obligatoria de las 6 series DDS como subconjunto de validación, balance por sitio de grabación (5 ES / 5 IS / 4 TS) y, dentro de cada sitio, volumen de decisiones. La lista queda congelada en `config/corpus.toml`, sección `[oe1]`; cambiarla invalidaría cualquier anotación producida bajo ella.

**Partición desarrollo / evaluación.** Tres cosas se ajustan en este diseño —los parámetros de segmentación y recuperación de C1 (§5.3), la grilla del umbral τ de alineamiento (§5.4) y el punto de operación del bloqueador de candidatos— y ninguna puede ajustarse sobre los datos cuyos resultados se reportan. De ahí la partición fijada en el [ADR 0005](decisions/0005-adr-development-evaluation-split.md): **desarrollo, ES2015, IS1004 y TS3009 — 77 decisiones y 11 pares candidatos**; **evaluación, las otras 11 series — 266 decisiones y 81 pares candidatos**. No es una partición de entrenamiento y prueba: nada se entrena aquí; separa los datos usados para *elegir* de los usados para *reportar*. Las cifras de desarrollo pueden ilustrar el método, nunca entrar en una tabla de resultados.

**Paso cero — ejecutado el 2026-09-20, antes de comprometer el diseño.** Se descargaron las anotaciones manuales y se verificaron empíricamente las tres cosas que el diseño daba por supuestas. No fue un trámite: su resultado cambió el marco muestral.

- **(a) Completitud y legibilidad.** Las capas se inventariaron por conteo directo de archivos: 142 resúmenes abstractivos, 137 `summlink`, 47 DDS, 556 de actos de diálogo y 687 de palabras. Las 6 series DDS están completas y sus archivos parsean sin error.
- **(b) Cuántas decisiones distintas contienen.** Aquí el paso cero modificó el diseño. El marco muestral previsto —la capa DDS— ofrece **6 series completas y 136 decisiones**; el marco alternativo —los encabezados `DECISIONS` del resumen abstractivo— ofrece **33 series completas y 649 decisiones**. Se adoptó el segundo (decisión **D1**) y la capa DDS pasa a **subconjunto de validación** en las series que llevan ambas (**D2**). De ese marco ampliado salen las 14 series de la muestra.
- **(c) Cuántos enlaces entre reuniones existen realmente.** Es el número que determina la viabilidad del proyecto y el único de los tres que **sigue sin medirse directamente**. Lo medido es su cota superior y el trabajo de adjudicación que implica: las 14 series contienen **3.071 pares de decisiones entre reuniones**, de los cuales el bloqueador de candidatos selecciona **92 (3,0 %)**. Cuántos de esos 92 son relaciones reales es lo que la anotación humana de OE1 debe establecer; la estimación provisional disponible se discute a continuación y sus consecuencias, en §7.

**Potencia estadística — declarada, no omitida.** La muestra medida no hace simplemente más fuerte el argumento anterior: **desplaza la restricción vinculante**, y por eso conviene separar los dos niveles.

- **Nivel decisión (OE2, Experimento A).** La base es de **343 frases de decisión medidas**, 266 de ellas en evaluación — no la estimación previa de entre 90 y 100 decisiones, derivada de ~4 segmentos decisorios por reunión sobre la muestra anterior de 24. Es una base materialmente mayor y deja de ser el factor limitante: sostiene estimaciones con intervalos de confianza reportados y pruebas pareadas por pregunta.
- **Nivel relación (OE3 / estrato E3, Experimento B).** La restricción no es el número de decisiones sino el de **relaciones reales entre reuniones**, y ese número **todavía no está establecido**. La única estimación disponible procede de adjudicar contra transcripción los **11 pares candidatos de desarrollo**: tasa de positivos **45,5 % (5/11), IC 95 % de Wilson [21,3 % – 72,0 %]**, que extrapolada a los 81 candidatos de evaluación da **≈ 37 relaciones reales, IC [17 – 58]**. Esa estimación es **provisional y no es conjunto de referencia**: las etiquetas las puso un procedimiento automático, no un anotador, y n = 11 es demasiado pequeño para cerrar el intervalo. Sirve para decidir si vale la pena invertir las horas de anotación, no para reportar un resultado.

Los compromisos declarados no cambian, porque siguen siendo los correctos: todos los resultados se reportarán con intervalos de confianza por *bootstrap*; ninguna conclusión se apoyará en diferencias que caigan dentro de ellos; y no se harán **afirmaciones de significancia sobre diferencias pequeñas**.

### 5.1 Auditoría de datos y riesgos declarados

- **Sesgo de dominio:** todas las reuniones del escenario tratan el mismo producto. La generalización a otros dominios organizacionales no es evaluable con este corpus y no se afirmará.
- **Habla actuada:** los participantes representan roles asignados en un escenario controlado. Las decisiones son reales en cuanto actos conversacionales, pero las consecuencias organizacionales son simuladas.
- **Composición lingüística:** el corpus incluye deliberadamente una alta proporción de hablantes no nativos de inglés, y la cifra **ya está medida**: **189 participantes — 91 nativos de inglés, 96 no nativos y 2 desconocidos**. Ningún artículo del corpus la publica, de modo que se reporta como derivación propia. La fuente es el atributo `native_language` del archivo de recursos del corpus, no la heurística del tercer carácter del identificador de participante que esta propuesta suponía: esa heurística acierta en 187 de 189 casos, pero fabrica un valor para toda la serie TS3005, cuyos participantes no figuran en el archivo. Medido en el paso cero (`notebooks/00-jss-corpus-y-auditoria.ipynb`; avance 02, §4.5). Lo medido, además, cambia el uso del dato: la lengua materna está **perfectamente anidada en el sitio de grabación**, de modo que la composición lingüística es una **limitación declarada** del corpus y no un eje de estratificación (**D7**, **D8**; §6.3).
- **Fuga de información:** la anotación de relaciones temporales se realiza **en orden cronológico dentro de cada serie**, sin acceso a reuniones posteriores al momento de anotar cada decisión. Análogamente, la extracción automática procesa las reuniones en orden y no puede consultar reuniones futuras.
- **Segmentación por tópico como proxy:** se descarta. Hsueh & Moore reportan que los límites de discusión decisoria coinciden con límites de tópico **menos de la mitad de las veces**.

### 5.2 Operacionalización de "decisión"

Dado el §1.4, el constructo se define de forma restrictiva y verificable. Una **decisión** es un compromiso sobre una acción o propiedad del producto que satisface las tres condiciones:

1. **Explícita:** existe al menos un acto de diálogo en el que se formula o se ratifica.
2. **Aceptada:** no queda como propuesta abierta al cierre del segmento.
3. **Anclada:** identifica un objeto de decisión (qué se decide) y un contenido (qué se decidió al respecto).

Las propuestas no aceptadas, las preguntas abiertas y las opiniones se registran como **no-decisiones** y forman parte del conjunto de referencia — se necesitan para medir falsos positivos.

Cada decisión se representa con: identificador, objeto de decisión, contenido, reunión de origen, evidencia (rango de actos de diálogo), estado, y relaciones a decisiones previas.

### 5.3 Las tres condiciones

Las tres comparten **el mismo modelo generativo, el mismo modelo de *embeddings*, el mismo hardware y el mismo presupuesto de contexto**. Lo único que varía es la representación consultada. Sin esta restricción, cualquier diferencia observada es inatribuible.

- **C1 — RAG documental.** Transcripciones segmentadas, indexadas y recuperadas por búsqueda híbrida (léxica + densa). Debe ser una línea base **honesta**: parámetros de segmentación y número de fragmentos recuperados ajustados sobre un conjunto de desarrollo separado, no fijados arbitrariamente. Una línea base debilitada invalida el experimento completo.
- **C2 — Compilación automática.** Extracción con modelo local, persistencia con procedencia, consulta sobre los objetos compilados.
- **C3 — Compilación desde la referencia.** Idéntica a C2 salvo que los objetos provienen de la anotación de OE1.

### 5.4 Protocolo de alineamiento

*Esta es la pieza metodológica que decide si los números de OE2 significan algo.*

Una decisión extraída no coincidirá textualmente con la anotada. Determinar si corresponden requiere un procedimiento declarado antes de mirar los resultados:

1. **Candidatos:** pares con similitud coseno de *embeddings* sobre el par (objeto de decisión, contenido) por encima de un umbral τ.
2. **Restricción:** el emparejamiento es uno-a-uno, resuelto como asignación de costo máximo (algoritmo húngaro), no por vecino más cercano codicioso — evita que varias extracciones reclamen la misma decisión de referencia.
3. **Validación:** el protocolo automático se contrasta contra emparejamiento manual sobre una muestra de al menos 100 pares; se reporta su concordancia.
4. **Sensibilidad:** todos los F1 se reportan **como curva sobre τ**, no en un único punto. Si el ordenamiento entre condiciones cambia según τ, se declara.

> Se descartan explícitamente **PR-AUC** y **matrices de confusión** como métricas principales: ambas presuponen un clasificador que emite puntajes sobre clases fijas. El sistema evaluado emite conjuntos de objetos en lenguaje natural. **Recall@K se conserva**, pero únicamente para evaluar la etapa de recuperación dentro de C1 y C2, donde sí existe un ranking.

### 5.5 Banco de preguntas

Construido **desde la anotación de OE1**, de modo que cada pregunta tenga respuesta de referencia derivada de la evidencia, y estratificado en cuatro categorías. La estratificación no es cosmética: es la que permite contrastar H1.

| Estrato | Forma | Qué discrimina |
|---|---|---|
| **E1 — Hecho puntual** | *¿Qué se decidió sobre el material de la carcasa?* | Caso donde se espera **paridad**; si C2 pierde aquí, hay una regresión que explicar |
| **E2 — Estado vigente** | *¿Cuál es la decisión vigente sobre el menú en pantalla?* | Requiere saber cuál de varias versiones prevalece |
| **E3 — Evolución** | *¿Cambió la decisión sobre el compartimento deslizante? ¿En qué reunión y por qué?* | **El estrato que prueba la tesis** |
| **E4 — Incontestable** | Preguntas adyacentes al dominio sin respuesta en el material | Mide si el sistema **se abstiene** o fabrica |

Mínimo 25 preguntas por estrato, construidas por una persona distinta de quien ejecuta los sistemas, y validadas por una segunda.

### 5.6 Métricas

**Extracción (OE2).** Precisión, cobertura y F1 a nivel decisión bajo §5.4. Para relaciones temporales, se reportan por separado: existencia del enlace, tipo de relación y **dirección**. Estratificado por **rol del hablante**; el eje nativo/no nativo no se estratifica y se reporta como limitación (§6.3).

**Respuesta (OE3).** Corrección respecto de la referencia; **tasa de soporte de evidencia** (proporción de afirmaciones atribuibles a una fuente identificada); **tasa de citación correcta** (la fuente citada respalda efectivamente la afirmación — distinta de la anterior, y la que detecta el modo de falla más peligroso: respuesta correcta con cita que no la sustenta); y **corrección del rechazo** sobre E4.

**Operativas (OE3).** Memoria residente máxima; tiempo de compilación por reunión; tiempo por consulta; y

> **Punto de equilibrio amortizado** = número de consultas *n* a partir del cual
> `costo_compilación + n · costo_consulta_estructurada  <  n · costo_consulta_RAG`

Esta métrica reemplaza a la latencia aislada porque la comparación real no es consulta contra consulta: es una inversión inicial alta con consultas baratas frente a cero inversión con consultas caras. El punto de equilibrio es la cifra que una organización necesita para decidir, y su ausencia es la razón por la que este tipo de comparación suele ser poco concluyente.

**Atribución de error (OE4).** Cada respuesta fallida de C2 se clasifica en extracción / recuperación / síntesis mediante un procedimiento determinista: se verifica primero si el hecho correcto existe en la base compilada (si no, es extracción); si existe, si fue recuperado (si no, es recuperación); si fue recuperado, es síntesis.

### 5.7 Protocolo de evaluación de respuestas

La evaluación combina juicio automático y humano, con salvaguardas explícitas contra sesgos documentados:

- **Anonimización y aleatorización del orden** de las respuestas antes de evaluar — los evaluadores automáticos presentan sesgo de posición documentado (Wang et al., 2024).
- **El modelo juez pertenece a una familia distinta** de la del modelo extractor. Ejecutar todo localmente hace fácil caer en que juez y extractor sean el mismo modelo, y los evaluadores favorecen sus propias generaciones (Panickssery et al., 2024).
- **Validación humana sobre al menos el 20%** de las respuestas, con reporte de concordancia juez-humano. Si la concordancia es baja, el juicio automático se descarta y se reporta únicamente la evaluación humana sobre la submuestra, con la pérdida de potencia que ello implica.

### 5.8 Modelado y reproducibilidad

Modelos generativos de ejecución local (familia Qwen o equivalente, en escalas contrastables) y modelo de *embeddings* multilingüe, seleccionados por ajustarse a las restricciones operativas de hardware disponible. Se fijan y publican: versiones exactas de modelos, semilla, tamaño de ventana de contexto y parámetros de muestreo.

**Varianza entre ejecuciones.** La extracción con LLM no es determinista aun con temperatura baja. Cada configuración se ejecuta **un mínimo de tres veces** y se reporta media y dispersión, no una ejecución única. Observaciones preliminares en el sistema instrumento muestran variación material en el número de objetos extraídos sobre entrada idéntica; ignorarla produciría diferencias espurias entre condiciones.

### 5.9 Instrumento

La implementación se realiza sobre **OpenKOS**, motor de compilación de conocimiento local desarrollado previamente por uno de los integrantes del equipo (Jason Sepúlveda) (código abierto, Apache-2.0), que ya provee ingesta, extracción tipada con procedencia, almacenamiento en formato abierto, recuperación híbrida y verificación de suficiencia de contexto.

**La distinción es importante para la evaluación del proyecto de título:**

| | |
|---|---|
| **Preexistente (instrumento)** | El motor, su pipeline de extracción, su capa de persistencia y su superficie de consulta |
| **Aporte de este trabajo** | El conjunto de referencia con enlaces temporales; la representación de evolución de decisiones; el diseño experimental de tres condiciones; el protocolo de alineamiento; y la medición de atribución de error |

Usar un instrumento existente reduce el riesgo de ejecución y concentra el esfuerzo en la pregunta de investigación. El aporte evaluable es la medición, no la construcción del motor.

### 5.10 Análisis de errores

Inspección cualitativa sistemática de los modos de falla, con al menos: decisiones no detectadas por ausencia de marcador explícito; falsos positivos sobre propuestas no aceptadas; enlaces temporales invertidos; y confusión entre decisiones recurrentes sobre el mismo objeto. Cada modo se ilustra con ejemplos del corpus y se cuantifica su frecuencia.

---

## 6. Alcances Éticos

### 6.1 Una aclaración necesaria sobre privacidad

**El corpus AMI es público y está licenciado CC BY 4.0. Este proyecto no procesa datos personales sensibles.** El argumento de privacidad no se refiere a los datos del experimento, sino a la **condición de despliegue** del método: un sistema de memoria de decisiones sólo es adoptable en una organización real si puede operar sin enviar deliberaciones internas a servicios de terceros. La ejecución local es por tanto un **requisito de diseño que la evaluación debe respetar para que sus resultados sean transferibles**, no una medida de protección del material experimental.

Esta distinción se declara explícitamente porque confundirla debilitaría tanto el argumento ético como el metodológico.

### 6.2 Transparencia y explicabilidad

Se operacionaliza como una propiedad medible, no como una aspiración: **toda decisión extraída mantiene trazabilidad hacia el fragmento de transcripción que la respalda**, y la tasa de soporte de evidencia (§5.6) es una métrica reportada del experimento, no una característica declarada del sistema. Una afirmación sin fuente identificable cuenta como falla aunque sea correcta.

### 6.3 Justicia y equidad

Medición proactiva de desempeño desigual en la extracción. El **análisis primario es el rol del hablante**; la condición nativo / no nativo baja a **limitación declarada** (decisión **D7**).

- **Rol del hablante** (Project Manager, Marketing Expert, User Interface Designer, Industrial Designer). Es el eje primario, y su tasa base está medida: el PM concentra el 47,0 % de los actos de decisión atribuidos, proporción que se mantiene entre 44 % y 50 % en cada sitio por separado, lo que indica que es estructural y no un artefacto de la muestra. La pregunta que se reporta no es si la cobertura del PM es alta —el 47 % refleja el corpus—, sino **si el sistema lo favorece más de lo que ya lo favorece el material fuente**: cobertura del sistema por rol contra la proporción base del corpus. Un sistema que extrae mejor las decisiones enunciadas por quien preside la reunión amplifica la jerarquía existente en el registro organizacional.
- **Condición de hablante nativo / no nativo de inglés — limitación declarada, no estratificación.** El eje conserva su interés: tiene análogo directo en atributos protegidos en contextos reales, y el corpus fue construido con alta proporción de hablantes no nativos precisamente por su dificultad de reconocimiento. Pero en AMI no es estratificable, y la razón no es de tamaño muestral: la lengua materna está **perfectamente anidada en el sitio de grabación** —Edinburgh casi todo nativo, Idiap mayoritariamente no nativo, y el bloque TNO sin un solo participante registrado en `participants.xml`—, de modo que cualquier diferencia atribuida a la lengua sería indistinguible de un efecto de sitio (**D7**, **D8**). Por eso la muestra se balancea por sitio (§5.0) y la composición lingüística se reporta como propiedad del corpus (§5.1). Declarar esta incapacidad medida es en sí mismo información: vale más que una estratificación que en realidad mide otra cosa y la disfraza de lengua.

El eje de rol se reporta aunque no se detecte diferencia; un resultado nulo con potencia declarada también es información.

### 6.4 Responsabilidad

El proyecto asume explícitamente el riesgo de compilar errores en la memoria organizacional y lo convierte en objeto de medición (OE4) en lugar de en advertencia. Se reportará, como cifra principal y no como nota al pie, la **proporción de respuestas incorrectas de C2 atribuibles a errores persistidos en la extracción**.

Marco de referencia: NIST AI Risk Management Framework 1.0 (funciones *Measure* y *Manage*), aplicado a las categorías de riesgo pertinentes: validez, transparencia y sesgo.

### 6.5 Uso del corpus

Atribución conforme a CC BY 4.0. Los identificadores de participante se conservan en su forma anonimizada original; no se intenta reidentificación. Los resultados estratificados por hablante se reportan agregados por categoría, nunca por individuo.

---

## 7. Alcances y Limitaciones

Declarados por adelantado para acotar las conclusiones defendibles.

**Dentro del alcance:** extracción de decisiones y sus relaciones temporales en series de reuniones del escenario AMI; comparación controlada de tres representaciones; medición de atribución de error; ejecución íntegramente local.

**Fuera del alcance, y no se afirmará nada al respecto:**

- **Generalización a otros dominios.** Un solo escenario, un solo tipo de producto.
- **Generalización a otros idiomas.** Corpus íntegramente en inglés. El motor es multilingüe, pero eso no se evalúa aquí.
- **Reuniones organizacionales reales con consecuencias reales.** AMI es escenario actuado.
- **Operación en tiempo real** durante la reunión.
- **Escenarios multiusuario**, permisos o gobernanza.
- **Robustez ante error de reconocimiento automático del habla.** Se trabaja sobre transcripciones manuales. La degradación bajo ASR es una extensión natural, no parte de este trabajo.
- **Afirmaciones de significancia sobre diferencias pequeñas**, por la limitación de potencia declarada en §5.0.

**Riesgo principal del proyecto y su mitigación.** Que el número de **relaciones reales entre reuniones** no alcance para sostener el estrato E3. El riesgo ya no se formula sobre las 6 series de la versión anterior de esta propuesta, porque la muestra cambió (§5.0); la evidencia disponible lo vuelve además más estrecho y mejor documentado. E3 exige **un mínimo de 25 preguntas** (§5.5). La estimación provisional de §5.0 da **≈ 37 relaciones reales en las 11 series de evaluación, con IC 95 % [17 – 58]**: **el valor central deja holgura; la cota inferior no alcanza el mínimo.** E3 es por tanto **plausible pero no establecido**, y con n = 11 pares adjudicados eso es exactamente todo lo que puede afirmarse.

**Mitigación en curso.** Estrechar el intervalo adjudicando una serie completa de **evaluación** contra transcripción. Es trabajo humano de anotación, no una repetición del cómputo: el intervalo es ancho porque hay pocos pares adjudicados, no porque el procedimiento sea inestable. Sólo se ha adjudicado desarrollo, porque leer el contenido de evaluación antes de anotarlo lo contamina.

**Alternativas si la adjudicación confirma la cota inferior.** Siguen siendo válidas las dos ya previstas: ampliar la muestra a las 18 series de reserva —que quedaron deliberadamente sin inspeccionar para esto—, anotando manualmente lo que falte; o reformular E3 como análisis de casos con reporte cualitativo. La decisión se toma en la primera fase, no al final.

> **Punto de decisión abierto.** Las dos alternativas no son equivalentes y la evidencia disponible no elige entre ellas. **(a) Ampliar la muestra** conserva el contraste cuantitativo con el que se pone a prueba H1, pero suma horas de anotación humana a un presupuesto ya comprometido (≈ 10–12 h para OE1) y obliga a declarar que el tamaño muestral se fijó después de ver un resultado parcial. **(b) Reformular E3 como análisis de casos** no añade horas y es defendible como aporte descriptivo —el vacío de §1.6 se cubre igual, porque el conjunto de referencia existe con independencia del resultado experimental—, pero deja H1 sin prueba cuantitativa en el único estrato diseñado para probarla. Debe resolverse cuando la adjudicación de la serie de evaluación entregue el intervalo estrechado, y no antes.

**Una restricción relacionada, y no menor.** El punto de operación del bloqueador de candidatos fue una decisión de diseño con costo medido (decisión **D9**), no un detalle de implementación: exigiendo sólo coeficiente de solapamiento ≥ 0,30, selecciona **712 de 3.071 pares (23,2 %)**, del orden de **18 horas** de adjudicación humana; añadiendo el mínimo absoluto `|A∩B| ≥ 2`, **92 (3,0 %)**, del orden de **2,3 horas**. Ese punto de operación **acota por arriba** las relaciones que la anotación puede llegar a encontrar, de modo que su cobertura no es un supuesto sino algo que debe medirse: la muestra de pares rechazados prevista en el plan de anotación existe exactamente para eso.

---

## 8. Bibliografía

> Todas las entradas fueron verificadas contra fuente primaria (ACL Anthology, Crossref, DOI del editor, w3.org, nist.gov). Se indica cuando un trabajo es **preprint sin revisión por pares**, condición que debe declararse al citarlo.

### 8.1 Corpus y detección de decisiones en reuniones

- Carletta, J., Ashby, S., Bourban, S., Flynn, M., Guillemot, M., Hain, T., Kadlec, J., Karaiskos, V., Kraaij, W., Kronenthal, M., Lathoud, G., Lincoln, M., Lisowska, A., McCowan, I., Post, W., Reidsma, D., & Wellner, P. (2006). The AMI Meeting Corpus: A Pre-announcement. En *Machine Learning for Multimodal Interaction (MLMI 2005)*, LNCS 3869, 28–39. Springer. DOI 10.1007/11677482_3
- Carletta, J. (2007). Unleashing the killer corpus: experiences in creating the multi-everything AMI Meeting Corpus. *Language Resources and Evaluation*, 41(2), 181–190. DOI 10.1007/s10579-007-9040-x — *autoría individual; revista, no LREC*
- Renals, S., Hain, T., & Bourlard, H. (2007). Recognition and Understanding of Meetings: The AMI and AMIDA Projects. *IEEE ASRU 2007*.
- Hsueh, P.-Y., & Moore, J. D. (2007a). What Decisions Have You Made?: Automatic Decision Detection in Meeting Conversations. *NAACL-HLT 2007*, 25–32. ACL Anthology N07-1004.
- Hsueh, P.-Y., & Moore, J. D. (2007b). Automatic Decision Detection in Meeting Speech. *MLMI 2007*, LNCS 4892, 168–179. Springer. DOI 10.1007/978-3-540-78155-4_15 — *Springer fecha el volumen en 2008; son dos artículos distintos, no confundir con el anterior*
- Fernández, R., Frampton, M., Ehlen, P., Purver, M., & Peters, S. (2008). Modelling and Detecting Decisions in Multi-party Dialogue. *Proc. 9th SIGdial Workshop on Discourse and Dialogue*, 156–163. ACL Anthology W08-0125.
- Bui, T. H., Frampton, M., Dowding, J., & Peters, S. (2009). Extracting Decisions from Multi-Party Dialogue Using Directed Graphical Models and Semantic Similarity. *Proc. SIGDIAL 2009*, 235–243. ACL Anthology W09-3934.
- Murray, G., Kleinbauer, T., Poller, P., Becker, T., Renals, S., & Kilgour, J. (2009). Extrinsic Summarization Evaluation: A Decision Audit Task. *ACM Transactions on Speech and Language Processing*, 6(2).
- Zhong, M., Yin, D., Yu, T., Zaidi, A., Mutuma, M., Jha, R., Hassan Awadallah, A., Celikyilmaz, A., Liu, Y., Qiu, X., & Radev, D. (2021). QMSum: A New Benchmark for Query-based Multi-domain Meeting Summarization. *NAACL-HLT 2021*, 5905–5921. DOI 10.18653/v1/2021.naacl-main.472
- Rennard, V., Shang, G., Hunter, J., & Vazirgiannis, M. (2023). Abstractive Meeting Summarization: A Survey. *TACL*, 11, 861–884. DOI 10.1162/tacl_a_00578

### 8.2 Recuperación aumentada y estructuración

- Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. *NeurIPS 33*, 9459–9474. arXiv:2005.11401
- Edge, D., Trinh, H., Cheng, N., Bradley, J., Chao, A., Mody, A., Truitt, S., Metropolitansky, D., Ness, R. O., & Larson, J. (2024). From Local to Global: A Graph RAG Approach to Query-Focused Summarization. arXiv:2404.16130 — **preprint sin revisión por pares**
- Guo, Z., Xia, L., Yu, Y., Ao, T., & Huang, C. (2025). LightRAG: Simple and Fast Retrieval-Augmented Generation. *Findings of ACL: EMNLP 2025*, 10746–10761. DOI 10.18653/v1/2025.findings-emnlp.568
- Es, S., James, J., Espinosa Anke, L., & Schockaert, S. (2024). RAGAs: Automated Evaluation of Retrieval Augmented Generation. *EACL 2024: System Demonstrations*, 150–158. DOI 10.18653/v1/2024.eacl-demo.16
- Saad-Falcon, J., Khattab, O., Potts, C., & Zaharia, M. (2024). ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems. *NAACL-HLT 2024*, 338–354. DOI 10.18653/v1/2024.naacl-long.20

### 8.3 Extracción de información y construcción de bases de conocimiento con LLM

- Dagdelen, J., Dunn, A., Lee, S., Walker, N., Rosen, A. S., Ceder, G., Persson, K. A., & Jain, A. (2024). Structured information extraction from scientific text with large language models. *Nature Communications*, 15, 1418. DOI 10.1038/s41467-024-45563-x
- Wadhwa, S., Amir, S., & Wallace, B. (2023). Revisiting Relation Extraction in the era of Large Language Models. *ACL 2023*, 15566–15589. DOI 10.18653/v1/2023.acl-long.868
- Xu, D., Chen, W., Peng, W., Zhang, C., Xu, T., Zhao, X., Wu, X., Zheng, Y., Wang, Y., & Chen, E. (2024). Large language models for generative information extraction: a survey. *Frontiers of Computer Science*, 18(6), 186357. DOI 10.1007/s11704-024-40555-y
- Mihindukulasooriya, N., Tiwari, S., Enguix, C. F., & Lata, K. (2023). Text2KGBench: A Benchmark for Ontology-Driven Knowledge Graph Generation from Text. *ISWC 2023*, LNCS, 247–265. DOI 10.1007/978-3-031-47243-5_14
- Zhu, Y., Wang, X., Chen, J., Qiao, S., Ou, Y., Yao, Y., Deng, S., Chen, H., & Zhang, N. (2024). LLMs for knowledge graph construction and reasoning: recent capabilities and future opportunities. *World Wide Web*, 27(5), art. 58. DOI 10.1007/s11280-024-01297-w
- Jarnac, L., Chabot, Y., & Couceiro, M. (2025). Uncertainty Management in the Construction of Knowledge Graphs: A Survey. *Transactions on Graph Data and Knowledge*, 3(1), 3:1–3:48. DOI 10.4230/TGDK.3.1.3
- Cai, E., & O'Connor, B. (2025). Understanding the Effect of Knowledge Graph Extraction Error on Downstream Graph Analyses: A Case Study on Affiliation Graphs. arXiv:2506.12367 — **preprint sin revisión por pares**
- Zhang, Y., & Li, S. (2026). ConsistencyGate: Preventing Memory Contamination in LLM Agents via Self-Consistency Admission Control. arXiv:2607.22962 — **preprint sin revisión por pares; ver nota en §9**

### 8.4 Alucinación, atribución y evaluación

- Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., Bang, Y. J., Madotto, A., & Fung, P. (2023). Survey of Hallucination in Natural Language Generation. *ACM Computing Surveys*, 55(12), art. 248. DOI 10.1145/3571730 — *fuente de la distinción intrínseca/extrínseca*
- Huang, L., et al. (2025). A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions. *ACM TOIS*, 43(2), art. 42. DOI 10.1145/3703155
- Rashkin, H., Nikolaev, V., Lamm, M., Aroyo, L., Collins, M., Das, D., Petrov, S., Tomar, G. S., Turc, I., & Reitter, D. (2023). Measuring Attribution in Natural Language Generation Models. *Computational Linguistics*, 49(4), 777–840. DOI 10.1162/coli_a_00486
- Bohnet, B., et al. (2022). Attributed Question Answering: Evaluation and Modeling for Attributed Large Language Models. arXiv:2212.08037 — **preprint sin revisión por pares**
- Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. *NeurIPS 2023 Datasets and Benchmarks*, 46595–46623.
- Wang, P., Li, L., Chen, L., Cai, Z., Zhu, D., Lin, B., Cao, Y., Liu, Q., Liu, T., & Sui, Z. (2024). Large Language Models are not Fair Evaluators. *ACL 2024*, 9440–9450. DOI 10.18653/v1/2024.acl-long.511
- Panickssery, A., Bowman, S. R., & Feng, S. (2024). LLM Evaluators Recognize and Favor Their Own Generations. *NeurIPS 2024*, 68772–68802.

### 8.5 Temporalidad del conocimiento

- Liska, A., Kocisky, T., Gribovskaya, E., Terzi, T., Sezener, E., Agrawal, D., de Masson d'Autume, C., Scholtes, T., Zaheer, M., Young, S., Gribovskaya, E., Molloy, R., Lazaridou, A., & Blunsom, P. (2022). StreamingQA: A Benchmark for Adaptation to New Knowledge over Time in Question Answering Models. *ICML 2022*, PMLR 162, 13604–13622.
- Vu, T., Iyyer, M., Wang, X., Constant, N., Wei, J., Wei, J., Tar, C., Sung, Y.-H., Zhou, D., Le, Q., & Luong, T. (2024). FreshLLMs: Refreshing Large Language Models with Search Engine Augmentation. *Findings of ACL 2024*, 13697–13720. DOI 10.18653/v1/2024.findings-acl.813
- Kasai, J., Sakaguchi, K., Le Bras, R., Asai, A., Yu, X., Radev, D., Smith, N. A., Choi, Y., & Inui, K. (2023). RealTime QA: What's the Answer Right Now? *NeurIPS 2023 Datasets and Benchmarks*, 49025–49043.
- Chen, W., Wang, X., & Wang, W. Y. (2021). A Dataset for Answering Time-Sensitive Questions. *NeurIPS 2021 Datasets and Benchmarks*. arXiv:2108.06314
- Dhingra, B., Cole, J. R., Eisenschlos, J. M., Gillick, D., Eisenstein, J., & Cohen, W. W. (2022). Time-Aware Language Models as Temporal Knowledge Bases. *TACL*, 10, 257–273. DOI 10.1162/tacl_a_00459
- Cai, B., Xiang, Y., Gao, L., Zhang, H., Li, Y., & Li, J. (2023). Temporal Knowledge Graph Completion: A Survey. *IJCAI-23 Survey Track*, 6545–6553. DOI 10.24963/ijcai.2023/734
- Kulkarni, K., & Michels, J.-E. (2012). Temporal features in SQL:2011. *ACM SIGMOD Record*, 41(3), 34–43. DOI 10.1145/2380776.2380786 — *define tiempo de validez frente a tiempo de transacción*

### 8.6 Memoria organizacional y racionalidad de diseño

- Walsh, J. P., & Ungson, G. R. (1991). Organizational Memory. *Academy of Management Review*, 16(1), 57–91. DOI 10.5465/amr.1991.4278992
- Stein, E. W. (1995). Organization memory: Review of concepts and recommendations for management. *International Journal of Information Management*, 15(1), 17–32. DOI 10.1016/0268-4012(94)00003-C
- Klammer, A., & Gueldenberg, S. (2019). Unlearning and forgetting in organizations: a systematic review of literature. *Journal of Knowledge Management*, 23(5), 860–888. DOI 10.1108/JKM-05-2018-0277
- Kunz, W., & Rittel, H. W. J. (1970). *Issues as Elements of Information Systems*. Working Paper No. 131, Institute of Urban and Regional Development, University of California, Berkeley. — *fuente primaria de IBIS*
- Buckingham Shum, S. J., & Hammond, N. (1994). Argumentation-based design rationale: what use at what cost? *International Journal of Human-Computer Studies*, 40(4), 603–652. DOI 10.1006/ijhc.1994.1029
- Grudin, J. (1996). Evaluating Opportunities for Design Capture. En Moran & Carroll (eds.), *Design Rationale: Concepts, Techniques, and Use*, cap. 21. Lawrence Erlbaum.
- Zhou, X., Li, R., Liang, P., Zhang, B., Shahin, M., Li, Z., & Yang, C. (2026). Using LLMs in Generating Design Rationale for Software Architecture Decisions. *ACM TOSEM*, 35(8), 1–38. DOI 10.1145/3785010

### 8.7 Procedencia y marcos de riesgo

- Lebo, T., Sahoo, S., & McGuinness, D. (eds.) (2013). *PROV-O: The PROV Ontology*. W3C Recommendation, 30 de abril de 2013.
- Singh, J., Cobbe, J., & Norval, C. (2019). Decision Provenance: Harnessing Data Flow for Accountable Systems. *IEEE Access*, 7, 6562–6574. DOI 10.1109/ACCESS.2018.2887201
- Tabassi, E. (2023). *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*. NIST AI 100-1, 26 de enero de 2023. DOI 10.6028/NIST.AI.100-1 — *NIST indica que se encuentra en revisión*
- Open Knowledge Format (OKF) — especificación v0.1 (borrador), Google Cloud, 2026. — *formato de la representación persistente; borrador, citar como tal*

---

## 9. Nota sobre la afirmación de novedad

Durante la preparación de esta versión se identificó un preprint de julio de 2026 —Zhang & Li, *ConsistencyGate*— que nombra explícitamente el modo de falla central de este trabajo: la "contaminación de memoria", donde un hecho alucinado escrito una vez *persiste como premisa falsa para cada paso subsiguiente*, y publica tres conjuntos de evaluación al respecto.

**Debe leerse antes de fijar la afirmación de novedad de la tesis.** Puede acotarla. Puede también aportar metodología de medición directamente reutilizable para OE4.

Esto no compromete el proyecto: el aporte central sigue siendo el enlace temporal entre decisiones en un corpus real de reuniones —vacío que sigue sin cubrirse— y el diseño de tres condiciones que separa el valor de la representación del costo de su extracción. Pero la afirmación debe formularse después de leer ese trabajo, no antes.
