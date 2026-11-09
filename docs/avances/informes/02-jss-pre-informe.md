# Compilar o recuperar: una medición controlada del valor de una base persistente de decisiones frente a un RAG convencional

Pre-informe de la Actividad Final de Graduación II, redactado después de los experimentos formales.

| | |
|---|---|
| **Documento** | 02 — Pre-informe AFG2, redactado después de los experimentos formales |
| **Universidad** | Pontificia Universidad Católica de Chile |
| **Programa** | Magíster en Ciencia de Datos |
| **Curso** | MDS 3060, Actividad Final de Graduación II |
| **Autores** | Jason Sepúlveda S., Germán Vega, Gustavo Martínez |
| **Tutor** | Jean Philipe Fuentes Bordagaray |
| **Versión** | 1.3 |
| **Fecha** | 2026-11-09 |
| **Estado** | En revisión para envío |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 0.1 | 2026-11-07 | Borrador inicial, redactado a partir de los avances 01 a 13 (en particular 10 a 13) y de las tablas finales. Documento aparte del [pre-informe 01](01-jss-pre-informe.md), que se escribió antes de los experimentos y no se modifica. No se ha enviado. | Las dos corridas formales, las verificaciones humanas y las conclusiones quedaron completas (épica #288); el pre-informe de AFG2 se entrega el 2026-11-09 y debe reportar resultados formales y no preliminares. |
| 0.2 | 2026-11-07 | Se verifican en arXiv las dos referencias pendientes heredadas del 01 (título, autores y DOI coinciden; siguen como *preprint*) y la cita de OpenKOS apunta a la publicación de v0.7.0. | Pendientes de verificación heredados del pre-informe 01. |
| 1.0 | 2026-11-07 | Versión para envío, sin cambios de contenido respecto de la 0.2. El PDF enviado se registra en una fila nueva al enviarse. | Decisión de jss de cerrar el borrador antes de la entrega del 2026-11-09. |
| 1.1 | 2026-11-08 | Incorpora una figura del EDA, precisa el diseño de B, documenta el desacuerdo de q015 y corrige referencias. | Revisión con la rúbrica de AFG2 y contraste con el Notebook 30 y el Avance 12. |
| 1.2 | 2026-11-09 | Revisión para un lector externo: se retiran o definen los identificadores internos (registros de decisión, criterio D16, cuadernos, avances, claves de pregunta), se definen los términos que el texto usaba sin explicar (tipos de relación, control nulo, vista estricta, concordancia del alineamiento, sitios ES/IS/TS, fases de anotación, abstención), se explica que los 111 enlaces son 37 relaciones por 3 repeticiones, se declara el origen del banco de preguntas y el equipo donde se midieron los tiempos, se agregan referencias (Cohen, Landis y Koch, modelos y bibliotecas, repositorio del proyecto), el Anexo C pasa a ser de reproducibilidad y se completa la portada. Ninguna cifra cambia. | Las personas que evalúan no tienen acceso al repositorio; el tutor confirmó el encuadre de la sección 5 («el modelo» es el procedimiento completo con que cada condición responde). |
| 1.3 | 2026-11-09 | Incorpora las observaciones de G. Vega (PR #320), adaptadas a la v1.2: la sección 4.3 se reescribe con la fórmula del *overlap coefficient*, la comparación con Jaccard y la lectura de la pérdida del filtro; OpenKOS se nombra en OE3, H1 y 5.2; se definen el resumen redactado a mano y el acto de diálogo; las limitaciones de datos pasan a lista; se agregan la leyenda de estratos de la Tabla 4, los sitios en la Figura 2 y el valor sin redondear de la diferencia principal (−0,375), que explica por qué restar la Tabla 4 da −0,37. Ninguna cifra cambia. | Aporte de un integrante del equipo, revisado contra las fuentes (registro de decisión 0020, tablas finales del Experimento B). |

> **Cómo versionar.** Un cambio de redacción sube el decimal (0.1 → 0.2). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero y **debe declarar la evidencia
> que lo motivó**. El historial nunca se reescribe: se agrega una fila. El PDF enviado en
> cada entrega se registra aquí, con su fecha y su versión.

---

## 1. Introducción

### 1.1 Tema y relevancia

Una transcripción conserva lo que se dijo en una reunión. Reconstruir lo acordado exige seguir la conversación y, a veces, contrastarla con el resumen. En la cuarta reunión de uno de los equipos del corpus AMI (sección 3), el resumen oficial afirma que el equipo eliminó el botón «turbo» de un control remoto. La transcripción muestra que el equipo decidió conservarlo.

La respuesta habitual a «¿qué se decidió sobre X?» es la recuperación aumentada (RAG; Lewis et al., 2020): se buscan los fragmentos más parecidos a la pregunta y un modelo de lenguaje redacta con ellos. Este trabajo mide si conviene compilar las decisiones en una base persistente que registre su evolución, y cuánto cuesta que la construya una máquina que se equivoca. Importa porque un error de extracción en una base compilada se escribe una vez y se lee en cada consulta, y porque la evidencia disponible compara sistemas completos sin separar el valor de la estructura del de quien la construye (Edge et al., 2024).

### 1.2 Objetivos e hipótesis

**Objetivo general.** Diseñar, implementar y evaluar un método de extracción automática y representación persistente de decisiones organizacionales, incluida su evolución entre reuniones, con modelos de lenguaje de ejecución local, para cuantificar por separado el valor del sistema compilado frente a un RAG convencional, el costo de los errores de su extracción y las condiciones en que el resultado neto supera a ese RAG.

- **OE1.** Construir un *ground truth* de decisiones con enlaces de evolución, con confiabilidad medida por kappa de Cohen.
- **OE2.** Medir la calidad de la extracción automática (precision, recall y F1) contra ese *ground truth*.
- **OE3.** Medir la utilidad funcional de tres condiciones (RAG convencional, base compilada por máquina con OpenKOS y base con decisiones humanas) sobre un mismo banco de preguntas.
- **OE4.** Atribuir cada error de la base de máquina a su etapa de origen: extracción, recuperación o síntesis.

La hipótesis principal (H1) es que la base compilada (construida con OpenKOS, sección 5.1) supera al RAG convencional en preguntas de evolución de una decisión, con diferencia pequeña o nula en hechos puntuales. Otras tres, declaradas antes de ejecutar nada: la brecha entre base humana y de máquina es mayor en relaciones temporales que en decisiones (H2); la dirección de una relación es un modo de falla dominante, sin mejora proporcional al tamaño del modelo (H3); y el RAG da más respuestas seguras pero desactualizadas (H4).

### 1.3 Alcance

La referencia humana (OE1) cubre 14 series. Los experimentos formales usan las 11 series de evaluación y un generador local pequeño. El Experimento A mide la extracción (OE2). El B compara la respuesta a preguntas (OE3) y atribuye los fallos de la base automática en preguntas de hecho puntual (OE4). Los resultados corresponden a este corpus y a esta configuración. Cada decisión de diseño se registró antes de la corrida correspondiente en el repositorio público del proyecto (Anexo C).

## 2. Caracterización del problema

### 2.1 Identificación y análisis del problema

Las decisiones se pierden por tres razones: se reparten entre varios turnos (propuesta, objeción, acuerdo implícito); nadie las anuncia, así que nada distingue el pasaje donde se decidió algo de uno donde solo se conversó; y cuando se revisan en una reunión posterior, el cambio no queda escrito en ninguna transcripción. La dificultad alcanza a las propias personas, que no coinciden en qué es una decisión: Hsueh y Moore (2007) encontraron que son solo el 1,4 % de los actos de diálogo del corpus AMI, y Fernández et al. (2008) repitieron la marca con un criterio propio, con un acuerdo peor que el azar (kappa negativo, 12,22 % de solapamiento). Una etiqueta hay que medirla, venga de una persona o de un modelo.

Aquí una **relación** une dos decisiones de reuniones distintas de la misma serie; tiene un **tipo** entre cinco (*introduce*, *reafirma*, *refina*, *revierte*, *reemplaza*) y una **dirección**, que dice cuál decisión revisa a cuál. Las tres últimas son relaciones de **evolución**: una decisión posterior modifica, anula o sustituye a una anterior.

En el RAG convencional de este estudio, cada consulta recupera fragmentos de la transcripción. Para reconstruir una reversión, tiene que recuperar los dos pasajes pertinentes y el generador debe inferir cómo se relacionan. Una base compilada permite recuperar la decisión y su enlace directamente. Su utilidad depende de que la extracción haya registrado ambos con precisión.

### 2.2 Contextualización en el campo de estudio

Hsueh y Moore (2007) y Fernández et al. (2008) intentaron detectar decisiones automáticamente sobre el mismo corpus AMI, y Murray et al. (2009) mostraron con personas que reconstruir la historia de una decisión es difícil. GraphRAG (Edge et al., 2024) y LightRAG (Guo et al., 2025) construyen un índice estructurado antes de consultar, pero comparan sistemas completos y no separan el aporte del índice del de quien lo construyó. Las respuestas que cambian con la fecha (Liska et al., 2022; Vu et al., 2024) sustentan H4, y la memoria organizacional (Walsh y Ungson, 1991) y la racionalidad de diseño (Buckingham Shum y Hammond, 1994) discuten el costo de registrar decisiones.

La laguna se puede comprobar en los propios datos del corpus. AMI diseñó una capa de anotación, `decisionlink`, para enlazar decisiones, pero solo enlaza una decisión con una frase del resumen, redactado a mano, de la *misma* reunión y no distribuye datos: 47 archivos de decisiones, 288 decisiones marcadas y cero enlaces entre ellas. Falta, entonces, una medición controlada que separe el valor de compilar las decisiones, es decir, de organizarlas en un índice estructurado antes de consultar, frente a un RAG convencional, el costo de los errores de su extracción y la contribución de representar su evolución temporal.

## 3. Caracterización de los datos

### 3.1 Origen, permisos, tipo y relevancia

Los datos son el AMI Meeting Corpus (Carletta et al., 2006): unas 100 horas de reuniones grabadas en tres centros europeos, ES (Edimburgo), IS (Idiap) y TS (TNO), cerca de dos tercios con un escenario en que un equipo de cuatro personas, cada una con un rol asignado, diseña un control remoto en cuatro reuniones consecutivas. La licencia es CC BY 4.0, que permite usar y redistribuir citando la fuente (AMI Meeting Corpus, s.f.); se verificó en la página oficial y no en los artículos del corpus, que describen un régimen anterior más restrictivo. Los participantes están anonimizados y no se intenta reidentificarlos.

Cada equipo se reúne cuatro veces; ese bloque es una **serie**, la unidad con que se elige y se anota. Una decisión es una frase del apartado «Decisiones» del resumen que se redactó a mano para cada reunión, y su evidencia son los actos de diálogo (los enunciados anotados en la transcripción) enlazados a ella. De 33 series completas se seleccionaron 14, equilibradas por sitio y, dentro de cada sitio, las de más decisiones: 56 reuniones, 343 frases candidatas de decisión y 3.071 pares entre reuniones (una candidata de una reunión frente a otra de una reunión distinta de la misma serie), de los que un filtro léxico deja 92 para anotación humana (sección 4.3). Las personas anotaron en español y la referencia se tradujo al inglés para compararla, texto con texto, con lo que la máquina extrae de las transcripciones. Tras el etiquetado humano, la referencia final tiene **358 decisiones** (las personas descartaron 49 frases que no eran decisiones y reemplazaron 24 frases compuestas por 88 decisiones hijas) y **46 relaciones**.

### 3.2 Partición y fuga declarada

**Tabla 1.** Partición de las 14 series (decisiones de la referencia final).

| Partición | Series | Decisiones | Uso |
|---|---|---|---|
| Desarrollo | 3 (ES2015, IS1004, TS3009) | 80 | Ajustar parámetros |
| Evaluación | 11 (4 ES, 4 IS, 3 TS) | 278 | Solo reportar, tras congelar |
| de ellas, doble anotación | 4 (ES2008, ES2016, IS1003, TS3005) | — | Medir confiabilidad (36,4 % de la evaluación) |

Nada se entrena: la partición separa dónde se toman decisiones de diseño de dónde se reportan resultados, y todo lo ajustado en desarrollo se congeló antes de tocar evaluación. De las series de evaluación solo se publican identificadores y cifras agregadas, nunca texto de decisiones, respuestas o transcripciones; es una decisión del proyecto. Existe una **fuga declarada**: dos umbrales con que el motor de extracción parte las fuentes largas se fijaron en agosto de 2026 con mediciones sobre una serie de evaluación (TS3005); lo medido fue si la llamada al modelo colapsaba, no si lo extraído coincidía con el *ground truth*.

### 3.3 Calidad y limitaciones

**Calidad.** A partir de los metadatos del corpus se construyó un conjunto tabular de reuniones, hablantes y decisiones con 77 variables. Solo tres tienen celdas vacías: hora de inicio (32 de 56 reuniones, 57,1 %), lengua materna (64 de 224 hablantes, 28,6 %) y evidencia de la decisión (26 de 343, 7,6 %); los dos primeros son estructurales. No se imputa nada: estimar la evidencia de una decisión fabricaría un respaldo inexistente. Hay 4 frases idénticas y 8 casi idénticas, siempre en reuniones consecutivas (decisiones reafirmadas). Cuatro métodos de detección de valores extremos marcaron 15 de las 56 reuniones; la única marcada por los cuatro es una reunión real, larga y muy conversada, y todo se conservó con una marca.

**Limitaciones de los datos.**

- *Dominio único y habla actuada*: no se afirma generalización.
- *El material de origen contiene errores*, como el resumen del botón turbo; por eso se contrasta contra la transcripción.
- *Lengua materna y sitio van juntos*: de 189 participantes, 91 son nativos de inglés, 96 no nativos y 2 desconocidos; se balancea por sitio.
- *La muestra no es aleatoria*: los resultados describen estas 14 series.

Las limitaciones de método están en la sección 7.2 y el Anexo A.

## 4. Análisis exploratorio de datos

### 4.1 Patrones, tendencias y anomalías

![Distribución de decisiones por posición de la reunión en la serie](../../entregables/figuras/eda-decisiones-por-posicion.png)

**Figura 1.** Decisiones por reunión según su posición en las 14 series; a–d son la primera a la cuarta reunión de cada serie. Las cifras sobre cada caja indican la mediana.

La mediana de la primera reunión es 3,5 decisiones y en las siguientes va de 6,5 a 8,0. La primera reunión aporta 51 de las 343 frases candidatas (14,9 %). La proporción de frases sin evidencia sube del 0 % en la primera al 11,5 % en la última. Así, las reuniones posteriores concentran más decisiones y también más casos cuyo respaldo requiere revisión. Una serie completa ocupa entre 1,6 y 2,8 veces la ventana de 12.288 tokens del modelo de lenguaje usado como generador (sección 5.2), por lo que es necesario segmentar o recuperar contexto.

### 4.2 Sesgo por rol del hablante

Cada participante tiene un rol: jefe de proyecto (PM), diseñador industrial (ID), experto en marketing (ME) y diseñador de interfaz (UI).

![El jefe de proyecto enuncia casi la mitad de las decisiones, en los tres sitios](../../entregables/figuras/eda-decisiones-por-rol.png)

**Figura 2.** Porcentaje de los actos de diálogo que respaldan decisiones, por rol (izquierda, 685 actos en las 14 series), y porcentaje atribuido al PM en cada sitio de grabación (derecha; ES: Universidad de Edimburgo, IS: Instituto Idiap, TS: TNO). La línea punteada es el reparto uniforme.

El PM respalda el 47,0 % de los actos, casi el doble de un reparto uniforme; siguen ID (22,8 %), ME (15,3 %) y UI (14,9 %), y en cada sitio el PM se mantiene entre 44 % y 50 %. Si el sistema recuperara mejor lo que dice quien preside, el diseñador que propuso una idea desaparecería del registro: amplificaría la jerarquía. Por eso los resultados se publican por rol solo como agregados (sección 6.2).

### 4.3 El filtro léxico (*blocking*) y su sensibilidad

Para construir la referencia de relaciones hay que comparar cada decisión con las de las otras reuniones de su serie: 3.071 pares, casi todos sin relación entre sí. Anotarlos todos a mano tomaría unas 77 horas. Por eso un filtro léxico (*blocking*) selecciona antes los pares candidatos: conserva los que comparten al menos 2 palabras de contenido y alcanzan un *overlap coefficient* de al menos 0,30, definido como

*overlap*(A, B) = |A ∩ B| / mín(|A|, |B|),

donde A y B son los conjuntos de palabras de contenido de las dos frases. Quedan 92 pares (3,0 %, unas 2,3 horas de anotación).

Se prefirió esta medida al índice de Jaccard, |A ∩ B| / |A ∪ B|, por la asimetría de longitud entre las frases. Una reversión suele formularse como una frase breve que apunta a una decisión anterior extensa, y Jaccard la penaliza porque divide por la unión de ambas. En el par de control del botón turbo, Jaccard da 0,118 y descarta el par; el *overlap coefficient* da 0,400 y lo conserva.

Todo filtro de este tipo deja fuera relaciones reales. Para medir cuántas, se anotó una muestra aleatoria de 200 pares rechazados, 50 en cada una de cuatro series. El *recall* estimado del filtro es 0,407 (intervalo de Wilson al 95 % de 0,245 a 0,596): de cada diez relaciones reales conserva unas cuatro y descarta cerca de seis. El sesgo medido va contra las frases muy cortas. Por eso los 92 pares son lo máximo que el filtro permite anotar, no el universo de relaciones del corpus, y la referencia de relaciones se declara incompleta (Anexo A).

## 5. Modelo de aprendizaje de máquinas

### 5.1 Qué es «el modelo» y qué recibe cada condición

El proyecto **no entrena ningún modelo**. Se evalúa el procedimiento completo con que cada condición responde: qué recupera, cómo lo representa y cómo redacta con ello. Los modelos ya entrenados se ejecutan localmente con Ollama, versión 0.32.9 (Ollama, 2026). OpenKOS 0.7.0 (Sepúlveda, 2026) es el instrumento que compila y consulta la base. Es un programa de código abierto desarrollado antes por un integrante del equipo, no un aporte de la tesis.

La **base compilada** se construye reunión por reunión: el extractor lee cada transcripción en orden cronológico y escribe objetos con procedencia (decisiones, conceptos, eventos, proyectos y fuentes), cada uno con el fragmento que lo respalda, y al alinear las decisiones de reuniones sucesivas escribe los enlaces entre ellas. Una consulta recupera cualquiera de esos objetos.

**Tabla 2.** Condiciones del Experimento B. Las cuatro usan el mismo generador y reciben las mismas preguntas.

| Condición | Qué recibe el modelo para responder | Papel |
|---|---|---|
| C0 | Responde sin recuperar contexto. | Referencia descriptiva |
| C1 | Recupera hasta cinco fragmentos de la transcripción mediante búsqueda híbrida y responde en una llamada. | **Línea base** |
| C2 | Recupera objetos de la base compilada. OpenKOS comprueba si el contexto alcanza antes de responder. | Propuesta evaluada |
| C3 | Aplica la consulta de C2 a una copia de su base en que las decisiones y sus enlaces son los de la referencia humana; los demás objetos siguen siendo los de la máquina. | Control con decisiones de referencia |

C1–C2 compara dos sistemas completos, porque cambian la representación y el procedimiento de respuesta. C2–C3 mantiene la consulta y mide el efecto conjunto de sustituir las decisiones y sus enlaces.

### 5.2 Modelos, parámetros y su justificación

El generador es Qwen3 de 8 mil millones de parámetros (Qwen Team, 2025) en las cuatro condiciones, y también el extractor de OpenKOS, porque forma parte del sistema evaluado; en desarrollo, un modelo de la misma familia con 27 mil millones mejoró el F1 con mayor tiempo de extracción (Anexo A). La recuperación densa y el alineamiento usan BGE-M3 (Chen et al., 2024), un modelo de *embeddings* multilingüe; la verificación de suficiencia de C2 y C3 usa Gemma 4 de 26 mil millones de parámetros con 4 mil millones activos (Google DeepMind, s.f.), empaquetado en OpenKOS. El juez automático es gpt-oss de 20 mil millones (OpenAI, 2025), elegido por su acuerdo con las personas, su estabilidad ante el orden de las respuestas y su latencia; su familia es distinta de la del generador para limitar la autopreferencia (Panickssery et al., 2024; Wang et al., 2024; Zheng et al., 2023). Las etiquetas de cada modelo en Ollama están en la Tabla A1.

C1 segmenta la transcripción con el divisor recursivo por caracteres de LangChain (LangChain, 2026) en fragmentos de hasta 1.200 caracteres sin solapamiento y recupera los cinco mejores (K = 5). Se evaluaron 32 configuraciones sobre 17 preguntas de desarrollo y se eligió por el *recall* de la evidencia que llega al generador, con el mismo presupuesto de texto que en C2. Una decisión extraída se alinea con una de referencia cuando la similitud coseno entre sus *embeddings* de BGE-M3 alcanza τ = 0,70; se comprobó la sensibilidad a 0,75 y 0,80. Temperaturas, semilla, ventana de contexto y repeticiones están en el Anexo A.

### 5.3 Métricas y criterio de éxito

OE1 se mide con kappa de Cohen (Cohen, 1960) en existencia, tipo y dirección de las relaciones por separado, sin umbral. OE2, con precision, recall y F1 sobre τ, y con existencia, tipo y dirección de las relaciones. OE3, con la corrección de la respuesta calificada por el juez, por estrato: hecho puntual (E1), estado vigente (E2), evolución (E3) y sin respuesta (E4); una abstención es incorrecta en E1 a E3 y correcta en E4. OE4, con reglas fijas de una sola categoría por error.

El equipo redactó el banco de preguntas a partir de la referencia humana de las 11 series de evaluación, con respuesta esperada, evidencia y, en E3, el estado anterior de la decisión. Como C3 recibe esa misma referencia, es un escenario de control con acceso al contenido del que salieron las preguntas.

La comparación principal, fijada de antemano como D16, mide la diferencia de corrección entre C2 y C1 en E3, las preguntas sobre la evolución de una decisión. Se calcula un intervalo *bootstrap* del 95 % con 10.000 remuestreos pareados por pregunta. H1 se respalda si todo el intervalo queda por encima de 0. Si incluye 0, la comparación es no concluyente. Si queda por debajo, la dirección es contraria a la hipótesis. Para la verificación de la corrección se fija un kappa mínimo de 0,70 entre el juez y la revisión humana de una muestra estratificada de aproximadamente el 20 % de las respuestas.

### 5.4 Línea base

**C1** es la línea base porque resuelve la misma tarea sobre las transcripciones con recuperación léxica y semántica ajustada en desarrollo; **C0** describe el generador sin contexto. La extracción se presenta como una curva de sensibilidad a τ.

## 6. Resultados obtenidos

Los resultados son formales: una corrida por experimento sobre las 11 series de evaluación, congeladas antes de correr. Como se usó un solo modelo, los intervalos describen la variación entre reuniones o preguntas, no entre modelos.

### 6.1 Confiabilidad de la referencia (OE1)

La guía de anotación se calibró primero sobre dos series de desarrollo, que no se reportan. En las cuatro series de evaluación con doble anotación, dos personas anotaron por separado y una tercera resolvió los desacuerdos (Figura 3).

![Kappa de Cohen y acuerdo simple por pregunta de anotación: existencia 0,783 con 37 pares, tipo 0,554 con 18 pares y dirección indefinida con 37 pares](../../entregables/figuras/referencia-acuerdo-oe1.png)

**Figura 3.** Acuerdo entre anotadores en las cuatro series con doble anotación. A la izquierda, kappa de Cohen. A la derecha, porcentaje de pares con la misma etiqueta.

Las dos personas coinciden en si dos decisiones están enlazadas (kappa de 0,783; acuerdo de 89,2 % en 37 pares) y menos en el tipo de enlace (kappa de 0,554; 72,2 % en los 18 pares que ambas enlazaron): sustancial y moderado en la escala de lectura de Landis y Koch (1977). La dirección no tiene kappa: en los 37 pares ambas marcaron la misma y, con un solo valor posible, el kappa no existe. De las 14 series, 6 tienen referencia adjudicada tras doble anotación y 8 tienen un solo anotador; en evaluación son 4 y 7, y esa parte no tiene medida de acuerdo. La referencia de evaluación tiene 278 decisiones y 37 relaciones, de las que 24 son de evolución (*refina*, *revierte* o *reemplaza*).

### 6.2 Extracción automática (OE2, Experimento A)

Se extrajo con el generador en las 11 series, con 3 repeticiones (33 corridas completas, sin errores). Con el criterio principal (τ = 0,70), la máquina encuentra cerca de 3 de cada 10 decisiones de la referencia y solo cerca de 1,5 de cada 10 de lo que extrae coincide con ella.

**Tabla 3.** Decisiones, totales de las 33 corridas (intervalo de 95 % por remuestreo de reuniones).

| τ | Lectura | Precision | Recall | F1 |
|---|---|---|---|---|
| 0,70 | principal | 0,149 [0,117; 0,184] | 0,308 [0,247; 0,373] | **0,201** [0,161; 0,240] |
| 0,75 | sensibilidad | 0,100 | 0,206 | 0,134 |
| 0,80 | sensibilidad | 0,050 | 0,104 | 0,068 |

La medida es estable entre repeticiones (F1 de 0,201 ± 0,003) y supera el piso del azar: un control nulo, que cruza lo extraído de una serie con la referencia de otra, cubre el 13,8 % de la referencia con τ = 0,70. Entre series el F1 va de 0,130 a 0,260, con intervalos amplios. Por rol, el recall más bajo es el de UI (0,128) y el más alto entre los roles identificados el de PM (0,347). La precision baja no se interpreta como «la máquina inventa»: una decisión que no figura en la referencia puede ser un error o una decisión real que las personas no registraron.

**Relaciones.** Las 37 relaciones de la referencia, buscadas en cada una de las 3 repeticiones, dan 111 ocasiones de encontrar un enlace. De extremo a extremo se encuentra 1 de cada 10 (11 de 111, recall 0,099). Casi toda la pérdida viene de antes: un enlace solo puede encontrarse si se hallaron sus dos decisiones, y eso ocurre en 24 de las 111; entre esas 24, la máquina encuentra 11 (recall 0,458; precision 0,407). En los 11 acertó la dirección en todos y el tipo en 6, o en 3 si *revierte* y *reemplaza* se cuentan como etiquetas distintas.

**Validez de la medición.** Una persona verificó a mano la regla de alineación en 100 pares (50 que la regla empareja y 50 que descarta). La concordancia (pares coincidentes sobre la unión de los pares que emparejan la regla y la persona) fue 0,825 y cumple el criterio de 0,80; el acuerdo simple fue de 90 de 100 y el kappa de 0,800. De los 10 desacuerdos, 7 son pares que la regla descarta y la persona empareja, así que las cifras quedan algo por debajo de lo real; el tamaño de ese sesgo no está medido.

### 6.3 Respuesta a preguntas (OE3, Experimento B)

Se hicieron 99 preguntas (25 en E1, 25 en E2, 24 en E3 y 25 en E4), cada una a las 4 condiciones con 3 repeticiones (1.188 registros, ninguno con error), calificadas por el juez.

**Tabla 4.** Corrección (fracción de respuestas correctas) por condición y estrato.

| Condición | E1 | E2 | E3 | E4 | Total [IC 95 %] |
|---|---|---|---|---|---|
| C0 | 0,17 | 0,04 | 0,01 | 0,40 | 0,16 [0,09; 0,23] |
| C1 | 0,72 | 0,64 | 0,54 | 0,96 | 0,72 [0,63; 0,80] |
| C2 | 0,43 | 0,35 | 0,17 | 1,00 | 0,49 [0,39; 0,58] |
| C3 | 0,72 | 0,76 | 0,71 | 1,00 | 0,80 [0,72; 0,87] |

*Estratos:* E1, hecho puntual; E2, estado vigente; E3, evolución; E4, sin respuesta.

En E4 lo correcto es abstenerse; C2 y C3 lo hacen siempre, de modo que ese 1,00 no mide capacidad de responder.

**El criterio principal no se respalda.** La diferencia C2 − C1 en E3 es −0,38 (−0,375 sin redondear; restar las cifras ya redondeadas de la Tabla 4 da −0,37) y su intervalo de 95 % va de −0,61 a −0,14: queda por completo por debajo de 0, es decir, la dirección observada es la contraria a la esperada y C1 supera a C2. El resultado es el mismo en hechos puntuales (−0,29 [−0,49; −0,08]) y estado vigente (−0,29 [−0,51; −0,08]), y en el total (−0,23 [−0,33; −0,13]). H1 no se respalda para C2. Parte de la brecha de C2 es abstención: cuando le falta el dato, no responde (sección 6.5).

La segunda hipótesis queda sin respuesta: la brecha C3 − C2 es de 0,54 en E3 y de 0,29 en E1, y la diferencia entre ambas (0,25) tiene intervalo de −0,04 a 0,54, que incluye 0. La tercera tampoco se resuelve; se mide en el Experimento A, donde de los 11 enlaces detectados ninguno tiene la dirección equivocada (cota superior de Wilson al 95 %: 0,259) y 5 tienen el tipo equivocado; son pocos casos y una sola escala de modelo, así que la cláusula sobre el tamaño no se evalúa. La cuarta no es evaluable: en los 42 ítems de la muestra de verificación en que el juez calificó si la respuesta estaba desactualizada, ni el juez ni las personas marcaron ninguna, y no hay tasa que comparar.

**C3 frente a C1.** C3 iguala a C1 en E1 (0,72 las dos) y la supera en valor numérico en E2 y E3 (0,76 y 0,71 frente a 0,64 y 0,54); la comparación no se preregistró ni se contrastó, así que es descriptiva y no sostiene significancia.

### 6.4 Validez del juez automático

El verificador humano revisó a ciegas 240 respuestas, 60 por condición, sin ver la condición ni el veredicto del juez. El kappa de corrección (0,807) supera el umbral de 0,70; el de la métrica secundaria de evidencia respaldada (0,438) queda por debajo y la limita a una lectura descriptiva. El desglose por condición es exploratorio: en C0 el acuerdo es el menor (0,484) y el juez da menos respuestas correctas que la persona (16,7 % frente a 28,3 %), así que las diferencias frente a C0 podrían estar sobreestimadas; el criterio principal y H2 comparan otras condiciones. Un caso de la muestra, marcado incorrecto por el juez y correcto por la persona, ilustra un error individual del juez; las tasas formales conservan el veredicto del juez bajo el criterio de acuerdo global fijado antes de la corrida.

### 6.5 Atribución del error (OE4)

El juez marcó 43 respuestas de C2 como incorrectas en E1, contando las tres repeticiones. La extracción fue la etapa más frecuente, con 21 de esos 43 casos.

**Tabla 5.** Etapa del fallo de C2 en hechos puntuales.

| Etapa | Casos (sobre 43) | Proporción | Detalle de las 40 etiquetadas a mano |
|---|---|---|---|
| Extracción | 21 | **48,8 %** | 21 (52,5 %) |
| Recuperación | 11 | 25,6 % | 11 (27,5 %) |
| Síntesis | 11 | 25,6 % | 8 (20,0 %) |

De los 43 casos, 40 los etiquetó una persona y 3 los atribuye a la síntesis una regla automática que compara palabras, no significados. Coherente con esto, C2 se abstiene mucho cuando le falta el dato: 36 %, 51 % y 71 % de sus respuestas en E1, E2 y E3, abstenciones que cuentan como incorrectas.

### 6.6 Costo y latencia

Son tiempos de pared, es decir, tiempo transcurrido medido con el reloj, de un solo equipo, un MacBook Pro de 16 pulgadas (2024) con chip Apple M4 Pro y 48 GB de memoria unificada, con macOS 27; los tokens y la memoria no se registraron. El tiempo promedio por consulta es de 4,2 s en C0, 5,7 s en C1, 15,3 s en C2 y 14,5 s en C3 (C2 tarda unas 2,7 veces C1); el juez tarda 6,3 s por respuesta. Extraer las once series (tres repeticiones) tomó 11,8 horas y compilar la base de una repetición, 3,9 horas. El diseño suponía que, tras construir la base, cada consulta costaría menos que una consulta RAG y la inversión se recuperaría en algún número de consultas. No ocurrió: una consulta a la base es más lenta que una de texto, así que el punto de equilibrio **no existe**.

## 7. Discusión y conclusiones

### 7.1 Discusión frente a la literatura

Al recuperar texto, la corrección total sube de 0,16 a 0,72, en línea con la premisa del RAG (Lewis et al., 2020). El menor acuerdo con el juez en C0 limita la lectura de esa brecha (sección 6.4). Los estudios de índices estructurados comparan sistemas completos (Edge et al., 2024; Guo et al., 2025). Aquí se mantiene la consulta entre C2 y C3. Al incorporar las decisiones y enlaces de la referencia, la corrección en E3 pasa de 0,17 a 0,71. El resultado es consistente con la propagación de errores desde la extracción (Cai y O'Connor, 2025). La precisión de extracción de 0,149 también es compatible con el riesgo de memoria contaminada descrito por Zhang y Li (2026), cuya magnitud queda por medir. El kappa de existencia de 0,783 documenta el acuerdo con esta guía y este procedimiento de anotación, que difieren de los usados por Fernández et al. (2008).

### 7.2 Aprendizajes, fallas, riesgos y limitaciones

**La extracción concentra la mayor proporción de fallos de C2 en E1** (48,8 %). El experimento prueba juntos el diseño de extracción y el modelo local. El 0,80 total de C3 describe un escenario de control que recibe la misma referencia de la que salió el banco de preguntas (sección 5.3).

Los resultados proceden de un solo corpus y una corrida formal por experimento. Siete de las once series de evaluación tienen un solo anotador. Los intervalos son amplios con 25 preguntas por estrato (24 en E3), y los pocos enlaces detectados limitan H3. La verificación del juez deja abierta la evaluación de evidencia y de respuestas desactualizadas. El Anexo A resume estas limitaciones y su tratamiento.

### 7.3 Ética integrada

Tres principios organizan el trabajo, y cada uno se traduce en algo que se mide. *Transparencia*: toda decisión conserva el fragmento que la respalda, y una afirmación sin fuente cuenta como falla aunque sea correcta; el resultado contrario al esperado se reporta como tal, no como «inconcluso». *Equidad*: el sesgo por rol se mide y se publica solo agregado, y el eje nativo/no-nativo queda como limitación por no ser separable del sitio. *Responsabilidad*: la cifra principal de OE4 es la proporción de errores atribuibles a la extracción, el que persiste. La ejecución local es un requisito de diseño, y de las series de evaluación no se publica texto. El marco de riesgos es el del NIST (Tabassi, 2023).

### 7.4 Conclusiones y próximos pasos

En esta corrida, el RAG convencional obtuvo 0,72 de corrección total frente a 0,49 de la base automática, con menor tiempo por consulta en el RAG; no existe punto de equilibrio. Un resultado negativo es informativo: acota el valor de compilar en este dominio. Al sustituir las decisiones y los enlaces por los de referencia bajo la misma consulta de OpenKOS, la corrección total llegó a 0,80. La extracción automática encontró el 30,8 % de las decisiones de referencia, lo que orienta el trabajo siguiente hacia la calidad del contenido de la base.

Los pasos siguientes hacia AFG3 son: (1) correr el modelo de mayor escala, ya configurado pero no ejecutado, para separar diseño de extracción y capacidad del modelo y evaluar la cláusula de tamaño de H3; (2) probar, como **hipótesis y no como resultado**, que personas confirmen o corrijan las decisiones al capturarlas, con la búsqueda de texto como respaldo, midiendo el esfuerzo humano; (3) un juez capaz de evaluar H4 y la evidencia; (4) ampliar la referencia con doble anotación de las series de un solo anotador; y (5) un contraste preregistrado de C3 frente a C1 y una medición de costo completa.

## 8. Referencias

AMI Meeting Corpus. (s.f.). *Licence* [Página web]. University of Edinburgh. Recuperado el 20 de septiembre de 2026, de https://groups.inf.ed.ac.uk/ami/corpus/license.shtml

Buckingham Shum, S. J., y Hammond, N. (1994). Argumentation-based design rationale: What use at what cost? *International Journal of Human-Computer Studies*, *40*(4), 603–652. https://doi.org/10.1006/ijhc.1994.1029

Cai, E., y O'Connor, B. (2025). *Understanding the effect of knowledge graph extraction error on downstream graph analyses: A case study on affiliation graphs* (arXiv:2506.12367) [Preprint, sin revisión por pares]. https://doi.org/10.48550/arXiv.2506.12367

Carletta, J., Ashby, S., Bourban, S., Flynn, M., Guillemot, M., Hain, T., Kadlec, J., Karaiskos, V., Kraaij, W., Kronenthal, M., Lathoud, G., Lincoln, M., Lisowska, A., McCowan, I., Post, W., Reidsma, D., y Wellner, P. (2006). The AMI Meeting Corpus: A pre-announcement. En *Machine Learning for Multimodal Interaction (MLMI 2005)* (Lecture Notes in Computer Science, vol. 3869, pp. 28–39). Springer. https://doi.org/10.1007/11677482_3

Chen, J., Xiao, S., Zhang, P., Luo, K., Lian, D., y Liu, Z. (2024). *M3-Embedding: Multi-linguality, multi-functionality, multi-granularity text embeddings through self-knowledge distillation* (arXiv:2402.03216) [Preprint, sin revisión por pares]. https://doi.org/10.48550/arXiv.2402.03216

Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and Psychological Measurement*, *20*(1), 37–46. https://doi.org/10.1177/001316446002000104

Edge, D., Trinh, H., Cheng, N., Bradley, J., Chao, A., Mody, A., Truitt, S., Metropolitansky, D., Ness, R. O., y Larson, J. (2024). *From local to global: A graph RAG approach to query-focused summarization* (arXiv:2404.16130) [Preprint, sin revisión por pares]. https://doi.org/10.48550/arXiv.2404.16130

Fernández, R., Frampton, M., Ehlen, P., Purver, M., y Peters, S. (2008). Modelling and detecting decisions in multi-party dialogue. En *Proceedings of the 9th SIGdial Workshop on Discourse and Dialogue* (pp. 156–163). Association for Computational Linguistics. https://aclanthology.org/W08-0125/

Google DeepMind. (s.f.). *Gemma 4 model card* [Documentación técnica]. Google AI for Developers. Recuperado el 9 de noviembre de 2026, de https://ai.google.dev/gemma/docs/core/model_card_4

Guo, Z., Xia, L., Yu, Y., Ao, T., y Huang, C. (2025). LightRAG: Simple and fast retrieval-augmented generation. En *Findings of the Association for Computational Linguistics: EMNLP 2025* (pp. 10746–10761). Association for Computational Linguistics. https://doi.org/10.18653/v1/2025.findings-emnlp.568

Hsueh, P.-Y., y Moore, J. D. (2007). What decisions have you made? Automatic decision detection in meeting conversations. En *Human Language Technologies 2007: The Conference of the North American Chapter of the Association for Computational Linguistics; Proceedings of the Main Conference* (pp. 25–32). Association for Computational Linguistics. https://aclanthology.org/N07-1004/

LangChain. (2026). *langchain-text-splitters* (Versión 1.1.3) [Software]. https://github.com/langchain-ai/langchain

Landis, J. R., y Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, *33*(1), 159–174. https://doi.org/10.2307/2529310

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., y Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. En *Advances in Neural Information Processing Systems 33* (pp. 9459–9474).

Liska, A., Kocisky, T., Gribovskaya, E., Terzi, T., Sezener, E., Agrawal, D., De Masson D'Autume, C., Scholtes, T., Zaheer, M., Young, S., Gilsenan-Mcmahon, E., Austin, S., Blunsom, P., y Lazaridou, A. (2022). StreamingQA: A benchmark for adaptation to new knowledge over time in question answering models. En *Proceedings of the 39th International Conference on Machine Learning* (Vol. 162, pp. 13604–13622). PMLR. https://proceedings.mlr.press/v162/liska22a.html

Murray, G., Kleinbauer, T., Poller, P., Becker, T., Renals, S., y Kilgour, J. (2009). Extrinsic summarization evaluation: A decision audit task. *ACM Transactions on Speech and Language Processing*, *6*(2), 1–29. https://doi.org/10.1145/1596517.1596518

Ollama. (2026). *Ollama* (Versión 0.32.9) [Software]. https://github.com/ollama/ollama

OpenAI. (2025). *gpt-oss-120b & gpt-oss-20b model card* (arXiv:2508.10925) [Preprint, sin revisión por pares]. https://doi.org/10.48550/arXiv.2508.10925

Panickssery, A., Bowman, S. R., y Feng, S. (2024). LLM evaluators recognize and favor their own generations. En *Advances in Neural Information Processing Systems 37 (NeurIPS 2024)* (pp. 68772–68802).

Qwen Team. (2025). *Qwen3 technical report* (arXiv:2505.09388) [Preprint, sin revisión por pares]. https://doi.org/10.48550/arXiv.2505.09388

Sepúlveda, J. (2026). *OpenKOS* (Versión 0.7.0) [Software]. GitHub. https://github.com/jasonssdev/openkos/releases/tag/v0.7.0

Sepúlveda, J., Vega, G., y Martínez, G. (2026). *mcd-afg: Compilar o recuperar, código, cuadernos y tablas de resultados* [Software]. GitHub. https://github.com/jasonssdev/mcd-afg

Tabassi, E. (2023). *Artificial intelligence risk management framework (AI RMF 1.0)* (NIST AI 100-1). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.AI.100-1

Vu, T., Iyyer, M., Wang, X., Constant, N., Wei, J., Wei, J., Tar, C., Sung, Y.-H., Zhou, D., Le, Q., y Luong, T. (2024). FreshLLMs: Refreshing large language models with search engine augmentation. En *Findings of the Association for Computational Linguistics: ACL 2024* (pp. 13697–13720). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.findings-acl.813

Walsh, J. P., y Ungson, G. R. (1991). Organizational memory. *Academy of Management Review*, *16*(1), 57–91. https://doi.org/10.5465/amr.1991.4278992

Wang, P., Li, L., Chen, L., Cai, Z., Zhu, D., Lin, B., Cao, Y., Kong, L., Liu, Q., Liu, T., y Sui, Z. (2024). Large language models are not fair evaluators. En *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (ACL 2024)* (pp. 9440–9450). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.acl-long.511

Zhang, Y., y Li, S. (2026). *ConsistencyGate: Preventing memory contamination in LLM agents via self-consistency admission control* (arXiv:2607.22962) [Preprint, sin revisión por pares]. https://doi.org/10.48550/arXiv.2607.22962

Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., y Stoica, I. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. En *Advances in Neural Information Processing Systems 36 (NeurIPS 2023), Datasets and Benchmarks Track* (pp. 46595–46623).

---

## Anexo A. Modelos por rol, candidatos y riesgos

Parámetros fijados por diseño: temperatura de 0,1 en el generador y 0,0 en el juez, semilla 42, ventana de 12.288 tokens y tres repeticiones por pregunta. C1 usa fragmentos de hasta 1.200 caracteres, sin solapamiento, con K = 5; C2 y C3 consultan OpenKOS con un límite de 5 objetos.

**Tabla A1.** Modelos por rol, con la etiqueta con que Ollama los identifica.

| Rol | Modelo (etiqueta) | ¿Se comparó con alternativas? | Fundamento |
|---|---|---|---|
| Generador de respuestas (C0 a C3) | Qwen3 8B (`qwen3:8b`) | No | Regla del mismo modelo generativo; local; modelo por defecto de OpenKOS |
| *Embeddings* (recuperación y alineamiento) | BGE-M3 (`bge-m3`) | No | Multilingüe; adoptado por OpenKOS por fiabilidad en documentos largos |
| Extractor de la base compilada (C2, C3) | Qwen3 8B (`qwen3:8b`), con una pasada dedicada a decisiones | Sí: tamizaje de cuatro modelos | Reglas fijadas antes de correr; costo; es el modelo del producto evaluado |
| Verificación de suficiencia (C2, C3) | Gemma 4 26B-A4B (`gemma4:26b-a4b`) | No | Empaquetado en OpenKOS 0.7.0; C1 no tiene este paso |
| Juez automático | gpt-oss 20B (`gpt-oss:20b`) | Sí: calibración de tres candidatos | Umbrales fijados antes de correr; familia distinta del generador |

**Tabla A2.** Tamizaje del extractor (desarrollo): F1 de decisiones con τ = 0,60 (el umbral se recalibró a 0,70 después de traducir la referencia), cinco corridas por modelo y serie. Un candidato avanza si supera al modelo del producto en ambas series por un margen fijado de antemano.

| Modelo (etiqueta) | F1 en ES2015 | F1 en TS3009 | Resultado |
|---|---|---|---|
| Qwen3 8B (`qwen3:8b`) | 0,290 | 0,300 | Elegido (modelo del producto) |
| Qwen3 14B (`qwen3:14b`) | 0,387 | 0,493 | No avanza (margen en ES2015: 0,097 de 0,099 exigidos) |
| Qwen3.6 27B (`qwen3.6:27b`) | 0,485 | 0,457 | Avanza; descartado por costo y por no ser el modelo del producto |
| Qwen3.6 35B-A3B (`qwen3.6:35b-a3b`) | 0,461 | 0,405 | Avanza; no pasa la confirmación con 15 corridas |

**Tabla A3.** Calibración del juez (desarrollo) sobre 42 respuestas etiquetadas por personas.

| Candidato (etiqueta) | Kappa con personas (umbral ≥ 0,70) | Consistencia ante el orden (≥ 0,90) | Latencia por llamada | Resultado |
|---|---|---|---|---|
| Mistral Small 3.2 24B (`mistral-small3.2:24b`) | 0,951 | 0,952 | 5,5 s | Cumple todo |
| Selene Mini (`atla/selene-mini:q8_0`) | 0,485 | 0,738 | 3,0 s | Falla kappa y orden |
| gpt-oss 20B (`gpt-oss:20b`) | 0,951 | 0,952 | 3,2 s | Cumple todo; gana por rapidez |

**Tabla A4.** Riesgos declarados y su tratamiento.

| Riesgo o limitación | Mitigación |
|---|---|
| Dominio único; habla actuada | No se afirma generalización |
| Referencia anotada en español y traducida al inglés | La traducción nunca es una etiqueta; τ se calibró después de traducir |
| C1 − C2 no separa representación de etapa de respuesta | Se declara; C3 − C2 no tiene esta limitación |
| Fuga: dos umbrales de troceo medidos con una serie de evaluación | Lo medido fue un colapso, no un acierto; se declara |
| Poca potencia: con 24 preguntas en E3 y una mejora real de 0,15, el criterio la detecta cerca del 57,5 % de las veces (simulación con 25 preguntas) | Intervalos pareados; lo no concluyente no se reporta como éxito |
| Juez estricto con C0 y no confiable para evidencia | Verificación humana de 240 respuestas; el criterio principal y H2 no dependen de C0 |
| Referencia de un solo anotador en 7 de 11 series de evaluación | Se declara; la confiabilidad se midió en las 4 series con doble anotación |
| Diseño de extracción y capacidad del modelo confundidos | Se declara; el modelo grande queda como trabajo futuro |
| El filtro pierde relaciones entre frases cortas | Declarado; recall medido de 0,407 con 200 pares rechazados |
| El banco de preguntas se redactó desde la referencia que recibe C3 | Se declara; C3 se lee como control, no como techo |

## Anexo B. Glosario breve

| Término | Significado en este documento |
|---|---|
| Serie | Cuatro reuniones consecutivas del mismo equipo; unidad de selección y de anotación |
| Sitio (ES, IS, TS) | Centro donde se grabó la serie: Edimburgo, Idiap o TNO; el prefijo del identificador de cada serie |
| Decisión | Frase del apartado «Decisiones» del resumen redactado a mano para una reunión, con los actos de diálogo que la respaldan |
| Acto de diálogo | Unidad en que AMI segmenta la transcripción: aproximadamente un enunciado con una función (proponer, aceptar, preguntar, informar) |
| Relación | Enlace entre dos decisiones de reuniones distintas de la misma serie, con un tipo (*introduce*, *reafirma*, *refina*, *revierte*, *reemplaza*) y una dirección; las tres últimas son relaciones de evolución |
| *Ground truth* | Decisiones y relaciones marcadas a mano, contra las que se mide todo lo demás |
| RAG | Recuperación aumentada: buscar fragmentos parecidos a la pregunta y redactar con ellos |
| Base compilada | Conjunto de objetos con procedencia (decisiones, enlaces, conceptos, eventos, proyectos, fuentes) que OpenKOS construye una vez a partir de las transcripciones y consulta después |
| OpenKOS | Programa de código abierto, anterior a la tesis, que compila y consulta la base |
| Condición (C0 a C3) | Cada uno de los cuatro procedimientos con que se responde la misma pregunta: sin contexto, RAG convencional, base automática, base con decisiones de referencia |
| Abstención | Respuesta en que el sistema declara que no encuentra el dato; correcta en E4, incorrecta en E1 a E3 |
| Juez automático | Modelo de lenguaje que califica cada respuesta como correcta o incorrecta; su acuerdo con personas se mide con kappa |
| Kappa de Cohen | Acuerdo entre dos anotadores descontando el azar; 0 es azar, 1 es acuerdo total |
| τ | Umbral de similitud coseno entre *embeddings* a partir del cual una decisión extraída se considera «la misma» que una de referencia |
| Precision, recall, F1 | Qué parte de lo extraído está en la referencia; qué parte de la referencia se encontró; un solo número que combina ambos |
| Filtro léxico (*blocking*) | Regla automática que reduce los pares a anotar según las palabras que comparten |
| *Bootstrap* | Repetir un cálculo sobre muestras al azar del mismo conjunto para estimar su variación |
| E1 a E4 | Estratos de preguntas: hecho puntual, estado vigente, evolución y sin respuesta |
| D16 | Criterio principal fijado de antemano: intervalo de la diferencia C2 − C1 en E3 por encima de 0 |

## Anexo C. Reproducibilidad y trazabilidad

El código, los cuadernos, las tablas de resultados y los registros de decisión del proyecto están en el repositorio público https://github.com/jasonssdev/mcd-afg (Sepúlveda, Vega y Martínez, 2026). La versión que corresponde a este informe se marca con una etiqueta de Git al enviarse y se registra en el historial de versiones. Por una decisión del proyecto, el repositorio no contiene texto de las series de evaluación (decisiones, respuestas ni transcripciones): solo identificadores y cifras agregadas.

Cada cifra del informe proviene de un documento de avance del proyecto; ninguna se calculó aquí. Las cifras de los resultados remiten al cuaderno 31 (`notebooks/31-jss-resultados-finales.ipynb`) y a las tablas `reports/tables/final-*`.

| Cifra o afirmación | Sección del informe | Fuente en el repositorio |
|---|---|---|
| 1,4 %; kappa negativo; 12,22 %; 47 archivos, 288 decisiones, 0 enlaces | 2.1, 2.2 | Avance 01 |
| Licencia; selección y sitios; 14 series, 56 reuniones, 343 frases, 3.071 pares, 92; 189 participantes | 3.1, 3.3 | Avances 02 y 07 |
| 358 decisiones, 46 relaciones; 49 descartadas, 24 reemplazadas por 88; 80 y 278 por partición; tipos de relación | 2.1, 3.1, 3.2, 6.1 | Avance 10, «La referencia final»; registro de decisión 0021 |
| Fuga declarada (TS3005); variables, faltantes y valores extremos; EDA; filtro léxico y recall 0,407 | 3.2 a 4.3 | Avances 07, 08 y 09; registro de decisión 0020 (muestra aleatoria de 4 × 50 pares rechazados) |
| Modelos, tamizaje, calibración del juez, configuración de C1, τ, criterio D16 | 5, Anexo A | Avances 08 y 09; registros de decisión 0007, 0012 y 0014 |
| Qué recibe cada condición; composición de la base de C3 | 5.1 | Avance 12, §2.2; registro de decisión 0013 |
| Kappa 0,783 / 0,554; 37 y 18 pares; 89,2 % y 72,2 %; adjudicación 6 de 14 y 4 de 11; fases de anotación | 6.1 | Avance 10 |
| Precision, recall y F1 por τ; 33 corridas; ± 0,003; control nulo 13,8 %; F1 por serie; recall por rol | 6.2 | Avance 11, §2 y §3; tabla `final-a-headline` |
| Relaciones 11/111, 24/111, 11/24, 0,458, 0,407, dirección 11/11, tipo 6/11 y 3/11 | 6.2 | Avance 11, §4; tabla `final-a-relations` |
| Validación manual: concordancia 0,825; 90/100; kappa 0,800; 7 omisiones | 6.2 | Avance 11, §5 |
| Corrección por condición y estrato; D16 −0,38 [−0,61; −0,14]; diferencias secundarias; 1.188 registros; origen del banco | 5.3, 6.3 | Avance 12, §2, §3 y §4; tablas `final-b-cells` y `final-b-paired` |
| H2 (0,54; 0,29; 0,25 [−0,04; 0,54]); H3 (0 de 11, 0,259; 5 de 11); H4 (42 ítems) | 6.3 | Avance 11, §6; Avance 12, §3.3 y §4.1; registros de decisión 0017 y 0018 |
| Juez: 0,807; 0,438; 0,484; 16,7 % y 28,3 %; 240 respuestas; desacuerdo individual | 6.4 | Avance 12, §4 |
| OE4: 43; 21 / 11 / 11; 40 etiquetadas 21 / 11 / 8; abstención 36 %, 51 %, 71 % | 6.5 | Avance 12, §5 y §6; tabla `final-oe4-stages` |
| Costos: promedios 4,2; 5,7; 15,3; 14,5; 6,3 s; 11,8 h; 3,9 h; sin punto de equilibrio | 6.6 | Avance 13, §5; tablas `final-cost-latency` y `final-break-even` |
| Límites y trabajo futuro | 7.2, 7.4 | Avance 13, §7 y §8 |

Referencias verificadas el 2026-11-07 y el 2026-11-09: las dos entradas de arXiv heredadas del pre-informe 01 (Zhang y Li, 2026; Cai y O'Connor, 2025) existen con el título, los autores y el DOI citados y siguen sin publicación revisada por pares; OpenKOS se cita como software con su versión y publicación; Cohen (1960), Landis y Koch (1977), Murray et al. (2009), Hsueh y Moore (2007), Fernández et al. (2008), Yang et al. (2025), Chen et al. (2024) y OpenAI (2025) se cotejaron con sus registros de DOI, ACL Anthology o arXiv.
