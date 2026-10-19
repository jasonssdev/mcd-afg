# Modelos y su justificación

| | |
|---|---|
| **Documento** | 09 — Modelos y su justificación |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 2.0 |
| **Fecha** | 2026-10-19 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-10-15 | Versión inicial. Reúne en un solo documento los modelos y técnicas del proyecto, la justificación de cada elección con su evidencia, las primeras pruebas realizadas y las dificultades abiertas. No introduce decisiones ni cifras nuevas: cada dato remite al registro de decisiones, a la configuración o al notebook donde ya consta. | Entrega del video de modelado de datos (semana 4) y sección «Modelo de aprendizaje de máquinas» del pre-informe. |
| 1.1 | 2026-10-15 | Se usan los nombres estándar de métricas y técnicas sin traducir (ground truth, baseline, accuracy, precision, LLM-as-a-judge, context window, cosine similarity). | Convención del equipo: los nombres de métricas y técnicas no se traducen. |
| 1.2 | 2026-10-15 | Se agrega la sección «Trazabilidad»; se corrige la referencia del recuento de unas 900 respuestas (notebook 07, el motor de corrida) y se indican los denominadores de las cifras de ES2015 (29 decisiones con acuerdo evaluado; 27 decisiones finales). El pendiente de confirmación con el tutor indica responsable y fecha. No cambia ninguna cifra ni decisión. | Auditoría de gobernanza del 2026-10-15: el recuento citaba el notebook 05 (selección del juez) en lugar del 07; las cifras de ES2015 usaban denominadores distintos sin decirlo; el pendiente no tenía responsable. |
| 1.3 | 2026-10-15 | Se retira la mención al extra `retrieval` (`rank-bm25`): el canal léxico BM25 está implementado en el paquete y la dependencia se eliminó de `pyproject.toml`. No cambia ninguna cifra ni decisión. | Corrección de código del 2026-10-15 (rama `fix/auditoria-codigo`): la dependencia declarada no se importaba en ninguna parte. |
| 2.0 | 2026-10-19 | La dificultad 7 deja de decir que τ sigue sin fijarse y remite al ADR 0012 (τ principal 0,70; 0,75 y 0,80 como sensibilidad). | El ADR 0012 fijó τ con el notebook 17: el juez marca la misma decisión en ≤ 0,32 de los pares bajo 0,70 y en ≥ 0,76 desde 0,70. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## Un caso para entrar en materia

En una de las series del corpus AMI (IS1004), un equipo diseña un control remoto a lo largo de
cuatro reuniones. El resumen oficial de la cuarta reunión afirma que el equipo eliminó el botón
«turbo»; al leer la transcripción completa, el botón se mantuvo (el caso se detalla en el
[documento 07](07-jss-analisis-exploratorio.md) y en el [documento 08](08-jss-metricas-y-criterio-de-exito.md), §1).
Una pregunta como *¿se mantuvo el botón turbo?* es el tipo que motiva todo el proyecto
([documentos 01](01-jss-problema.md) y [03](03-jss-objetivos.md)).

Hay dos maneras de intentar responderla con un modelo de lenguaje, es decir, un programa
entrenado con enormes cantidades de texto que redacta respuestas en lenguaje natural:

- **Buscar en el texto (C1).** El sistema trocea las transcripciones en fragmentos, busca
  los cinco más parecidos a la pregunta y le pide al modelo que redacte la respuesta solo con
  ellos. Si la decisión original quedó en un fragmento de una reunión y su revisión en uno de
  otra, la respuesta será buena solo si **ambos** fragmentos están entre los cinco elegidos.
  Nada en el sistema sabe que los dos hablan de lo mismo.
- **Consultar una base de decisiones (C2 y C3).** Antes de que llegue la pregunta, otro
  proceso leyó las reuniones y dejó guardada cada decisión, como la del botón turbo, en un
  registro propio, con la reunión y el pasaje de donde salió, y con la relación entre
  decisiones de reuniones distintas (por ejemplo, «esta decisión reemplaza a aquella»). Al
  preguntar, el sistema recupera esos registros, que ya llevan el hilo de la historia.

La diferencia entre ambos caminos es la que el proyecto quiere medir. Este documento explica
**con qué modelos y técnicas se hace esa medición, por qué se eligieron y qué se ha probado
hasta ahora**. El caso ilustra el mecanismo y no es un resultado, porque el experimento todavía
no se ha corrido (sección 6).

## 1. Qué es «el modelo» en este proyecto

Este proyecto **no entrena un modelo de aprendizaje de máquinas clásico**, de los que se
ajustan con datos de entrenamiento para predecir una etiqueta. No hay conjunto de
entrenamiento ni de prueba en ese sentido; el registro de decisiones lo explica al fijar la
partición desarrollo/evaluación: «no es train/test: nada se entrena» (D10, ADR 0005).

Lo que sí hay, y lo que este documento llama «modelos», son tres cosas de naturaleza
distinta:

| Papel | Qué es | Dónde está |
|---|---|---|
| **Sistemas bajo comparación** | Las tres condiciones: C1 (buscar en fragmentos de texto), C2 (base de decisiones construida por la máquina) y C3 (la misma base, construida por personas). Son las «hipótesis de modelado» que el proyecto contrasta. | Secciones 3.1 a 3.3 |
| **Modelos de lenguaje que las componen** | Un modelo que **genera** las respuestas, un modelo de *embeddings* (convierte texto en números para medir qué tan parecidos son dos textos) y el modelo que **extrae** decisiones al construir la base de C2. | Sección 3 y tabla de la sección 5 |
| **Instrumento de evaluación** | El **LLM-as-a-judge**: un segundo modelo de lenguaje que califica si cada respuesta es correcta. No es un modelo a evaluar, es la regla de medir. | Sección 4 |

**Por qué este encuadre responde a la pauta.** El curso pide «al menos un modelo» y que se
explique la elección de técnicas, librerías y parámetros. La pregunta de este proyecto no es
«qué algoritmo predice mejor una etiqueta», sino «¿una base estructurada de decisiones
responde mejor que buscar en el texto?». Los candidatos a modelo son, por lo tanto, los
sistemas que se comparan, y cada uno tiene técnicas, librerías y parámetros que se pueden
justificar con evidencia. Es la lectura de que el modelo debe ser consecuencia del problema:
primero se define qué se quiere contestar y después se eligen las piezas. Además, la
configuración de cada pieza queda fijada y registrada, de modo que cualquiera puede repetir
la corrida.

> **Por confirmar con el tutor** (responsable: jss; abierto desde 2026-10-15, sin respuesta
> todavía). Este encuadre es una interpretación del equipo sobre cómo
> aplicar la pauta de modelado a un proyecto sin modelo entrenado. Conviene confirmarlo con el
> tutor antes de la entrega, en particular si acepta que el LLM-as-a-judge se presente como instrumento
> y no como modelo bajo prueba.

## 2. Qué es igual en las tres condiciones

Para que una diferencia entre C1, C2 y C3 se pueda atribuir a la forma de organizar la
información, todo lo demás se mantiene igual. La configuración común está fijada en
`config/experiments.toml` (sección `[shared_budget]`) y se justifica en el ADR 0006:

- el mismo modelo generativo, `qwen3:8b`;
- el mismo modelo de *embeddings*, `bge-m3`;
- el mismo límite de texto que el modelo lee de una vez (su «context window»);
- las mismas instrucciones para redactar la respuesta (los *prompts* de **OpenKOS**, el motor
  de código abierto con que se construye y consulta la base de decisiones de C2 y C3, sección
  3.2; copiados byte a byte en C1 y verificados con una huella digital, ADR 0006);
- los mismos valores de temperatura y semilla, y el mismo hardware.

Un **parámetro** es un valor que se fija antes de correr y que condiciona el comportamiento
del sistema (por ejemplo, cuántos fragmentos se recuperan). Los parámetros comunes son:

| Parámetro | Valor | Qué significa |
|---|---|---|
| `generative_model` | `qwen3:8b` | Modelo que redacta la respuesta; ejecución local, sin enviar datos a terceros. |
| `embedding_model` | `bge-m3` | Modelo multilingüe que convierte texto en números para medir parecido. |
| `context_window_tokens` | 12.288 | Tamaño de la context window (valor por defecto de OpenKOS, ADR 0006). |
| `max_generation_tokens` | 8.192 | Largo máximo de la respuesta generada. |
| `temperature` | 0,1 | Grado de azar al redactar; un valor bajo vuelve las respuestas más estables. |
| `seed` | 42 | Semilla del azar, para poder repetir la corrida. |
| `runs_per_config` | 3 | Cada configuración se corre tres veces y se informa media y dispersión. |

Fuente de todos los valores: `config/experiments.toml`, `[shared_budget]`. La versión exacta
del modelo (la etiqueta completa) está pendiente de fijar antes del Experimento A y B,
según el comentario de la propia configuración. Un detalle de implementación: C1 no envía
`top_p` (0,9 en la configuración) porque OpenKOS tampoco lo envía, y así las condiciones
reciben las mismas opciones (`src/afg/conditions/c1_document_rag.py`).

## 3. Las tres condiciones

### 3.1 C1: buscar fragmentos de texto y redactar con ellos (RAG)

**Qué hace, en simple.** RAG significa *generación aumentada por recuperación*: antes de
contestar, el sistema recupera del texto disponible los pasajes más relacionados con la
pregunta y se los entrega al modelo para que redacte la respuesta con ellos. Es lo que
cualquier organización haría hoy con sus transcripciones, y por eso es el baseline: el
punto de comparación contra el cual se mide la propuesta.

**Por qué se eligió.** Responde a la pregunta del proyecto en su forma más directa: si la
decisión cambia entre reuniones, ¿basta con buscar texto? Si la respuesta fuera sí, el
hallazgo sería igualmente publicable (propuesta, plan ante resultado negativo). Una línea
base débil haría que cualquier propuesta pareciera buena, por lo que el diseño exige que sea
**honesta**: sus parámetros se ajustan con datos, no se fijan a ojo (ADR 0006 y 0007).

**Técnicas.**

- *Fragmentación (chunking).* Las transcripciones se parten en trozos de turnos de habla
  completos, con un tope de caracteres y con un turno compartido entre trozos consecutivos
  para no cortar una idea por la mitad.
- *Recuperación híbrida.* Dos buscadores se combinan: uno **léxico** (por palabras exactas,
  con el método BM25) y uno **denso** (por parecido de significado, con los *embeddings* de
  `bge-m3`). Sus listas se fusionan con *reciprocal rank fusion*, una regla que premia a los
  fragmentos bien ubicados en ambas listas (`rrf_k` = 60, el mismo valor que usa OpenKOS).
- *Redacción.* El modelo `qwen3:8b` decide primero si el contexto alcanza para responder
  (si no, se abstiene) y luego redacta citando qué bloques usó, con las instrucciones de
  OpenKOS copiadas sin adaptar (ADR 0006).

**Librerías.** El buscador BM25 está implementado dentro del proyecto
(`src/afg/conditions/c1_retrieval.py`, con las constantes habituales k1 = 1,5 y b = 0,75) y
los *embeddings* y la generación se piden al servidor local de modelos Ollama. En
`pyproject.toml` figuran los extras opcionales `ollama>=0.4` (modelos locales) y
`sentence-transformers>=3.3` (*embeddings*, protocolo de alineación). El canal léxico BM25 está
implementado dentro del paquete (`src/afg/conditions/c1_retrieval.py`), sin dependencia externa.

**Parámetros clave y evidencia.** El tamaño del fragmento, el solapamiento y el número de
fragmentos recuperados (K) se ajustaron sobre ES2015, una serie de desarrollo, con una regla
**fijada antes de correr** (commit `cfce5af`): 4 tamaños × 2 solapamientos × 4 valores de K
= 32 configuraciones, y la métrica es el *recall de evidencia*, es decir, qué parte de los
pasajes que respaldan la respuesta llega efectivamente al modelo. Resultado:

| Parámetro | Valor | Significado |
|---|---|---|
| `max_chars` | 1.200 | Tamaño máximo de un fragmento, en caracteres. |
| `overlap_turns` | 1 | Turnos que se repiten entre fragmentos consecutivos. |
| `k` | 5 | Fragmentos entregados al modelo. |

Evidencia: ADR 0007 (con su enmienda del 2026-10-15), notebook 06 y
`config/experiments.toml`, `[retrieval.c1]`. La medición inicial contó la evidencia sobre
fragmentos completos y eligió 1.600 / 0 / 8; al comprobar que OpenKOS recorta el contexto a
unos 7.400 caracteres, se repitió el ajuste contando solo el texto que de verdad llega al
modelo y el ganador cambió. Es un ejemplo de corrección declarada: con K = 8 el recall
entregado cae a 0,446, mientras que la configuración final entrega 0,569, con algún acto de
referencia entregado en 11 de las 17 preguntas (notebook 06, secciones 5 y 7).

**Limitaciones.**

- El ajuste usa una sola serie y 17 preguntas; la diferencia entre las dos mejores
  configuraciones (0,583 y 0,569) está dentro del ruido y la desempata la regla, no la
  evidencia (ADR 0007).
- El recall es un piso: AMI suele enlazar un solo acto de diálogo por respuesta, así que un
  fragmento puede contener la respuesta y contar igual como fallo (seis preguntas sin ningún
  acierto, notebook 06, sección 9).
- Las instrucciones de OpenKOS hablan de *concepts* y de *compiled bundle*, lo que no
  describe fragmentos de transcripción. Se copiaron igual, y se declara como limitación
  (ADR 0006, decisión 4).
- C1 no puede, por diseño, saber que dos fragmentos de reuniones distintas tratan de la misma
  decisión; esa es justamente la debilidad que C2 y C3 intentan superar.

### 3.2 C2: base de decisiones construida por la máquina

**Qué hace, en simple.** Un modelo de lenguaje lee las reuniones de una serie en orden
cronológico, extrae las decisiones y las guarda como registros con procedencia (reunión y
pasaje de origen), junto con las relaciones entre decisiones de reuniones distintas. Para
responder, el sistema recupera esos registros y el mismo modelo generativo de C1 redacta la
respuesta. Es la propuesta que se evalúa.

**Por qué se eligió.** Una decisión rara vez cabe en un turno y, cuando cambia, el cambio
no queda registrado en ningún lado (documento 01). Una base que guarda cada decisión como
objeto y la enlaza con sus versiones anteriores ataca exactamente esas dos pérdidas. La
hipótesis H1 apuesta a que la ventaja se verá sobre todo en preguntas de evolución (E3), no
en datos puntuales (documento 03).

**Técnicas.** La extracción y la consulta las hace **OpenKOS**, un motor de código abierto
(con licencia Apache-2.0, que permite usar, modificar y redistribuir el software) de ingesta,
extracción tipada con procedencia, almacenamiento en el formato abierto OKF (*Open Knowledge
Format*, una especificación para guardar conocimiento estructurado) y recuperación híbrida, desarrollado previamente por uno de los integrantes del
equipo. El [ADR 0003](../decisions/0003-adr-openkos-as-instrument.md) lo define como **instrumento**, no como aporte del proyecto: el aporte
es la medición. Por eso todo contacto con OpenKOS pasa por un único adaptador y solo por su
línea de comandos, nunca importando sus módulos internos (ADR 0003 y 0006). C2 responde con
`openkos query` sin modificar y con `--limit 5`, valor por defecto de OpenKOS que se
conserva a propósito (ADR 0007, decisión 5).

**Modelos y parámetros.** Responde con `qwen3:8b` y `bge-m3`, igual que C1 (sección 2). Al
compilar, OpenKOS usa además otros modelos, como su adjudicador interno de la familia Gemma
(ADR 0006, contexto). Las fechas de las reuniones se entregan a OpenKOS con hora, porque las
cuatro reuniones de una serie comparten fecha y, sin hora, no habría orden entre ellas: se
usa la hora real del corpus en 6 de las 14 series y una hora sintética que solo preserva el
orden a, b, c, d en las 8 restantes (ADR 0008, notebook 08). Es una desviación declarada, no
un dato temporal.

**Evidencia de que el riesgo es real.** Una prueba sobre ES2015 con OpenKOS 0.5.2 y
`qwen3:8b` extrajo 4 objetos de decisión para toda la serie, frente a 29 decisiones con acuerdo
evaluado en la anotación adjudicada del equipo (27 son decisiones finales; documento 06, §7–8). Es una serie y una corrida, con una
versión que ya no es la candidata; por eso se está corrigiendo OpenKOS antes de fijar la
versión (sección 6).

**Limitaciones.**

- El formato OKF es un borrador sin versión estable; si cambia, las bases no se migran, se
  recompilan (ADR 0003, riesgo registrado).
- Con la versión probada, la extracción no alcanza para las preguntas de estado actual (E2) y
  de evolución (E3), que son el objeto del estudio (documento 06).
- La dirección de las relaciones (cuál decisión reemplaza a cuál) es un modo de falla
  esperado (hipótesis H3); es una observación informal previa, no una medición del proyecto.
- Los resultados dependen de una versión de OpenKOS que aún no está fijada (issue #94).

### 3.3 C3: la misma base, construida por personas

**Qué hace, en simple.** Es la misma base de decisiones de C2, pero llenada con la anotación
humana del ground truth: personas marcaron a mano las decisiones y sus relaciones.
No tiene errores de extracción.

**Por qué se eligió.** Sin C3, una mala respuesta de C2 no se podría atribuir: no sabríamos
si la idea de la base no sirve o si la máquina la llenó mal. La distancia C1 → C3 mide el
valor de tener la base; la distancia C3 → C2 mide el costo de los errores de la máquina
(documento 03, OE3). Por eso las etiquetas del ground truth las pone siempre una
persona (D3): si un modelo las produjera, C3 heredaría errores por construcción y la
comparación dejaría de medir algo (documento 06, §5–6).

**Técnicas y parámetros.** Idénticos a C2 en consulta y modelos; solo cambia el origen de los
objetos. La calidad de la anotación se controla con acuerdo entre anotadores (kappa) y
adjudicación de los desacuerdos (documento 06, §5–6).

**Limitaciones.** C3 es una *referencia*, no un «techo teórico»: una anotación humana con
fiabilidad medida no es un límite superior demostrable (docstring de
`src/afg/conditions/c3_compiled_gold.py` y documento 03). Además, la calibración de las dos
personas que anotan en ES2015 dio un acuerdo bajo (kappa de 0,094, 13 de 29 decisiones con acuerdo evaluado), lo
que llevó a corregir la guía y a recalibrar con otra serie antes de las series de control
(documento 06, §5–6; issues #78 y #79 para TS3009).

## 4. El LLM-as-a-judge: un instrumento de medida

**Qué es y por qué hace falta.** El Experimento B genera al menos unas 900 respuestas (100
preguntas como mínimo × 3 condiciones × 3 corridas, notebook 07; hasta 115 preguntas si E3 llega a 40). Calificarlas a mano es inviable para un
equipo de tres personas, así que las califica un **LLM-as-a-judge**: un segundo modelo de
lenguaje que lee la pregunta, la respuesta de referencia, la respuesta del sistema y el
pasaje de la transcripción donde está la evidencia, y decide si la respuesta es correcta y si
cada afirmación tiene respaldo. A cambio, una persona verifica al menos el 20 % de lo que el
LLM-as-a-judge califica (`human_validation_fraction` = 0,20).

**Por qué no es un modelo bajo prueba.** Su veredicto no es una predicción que se evalúe: es
el aparato con el que se mide. Por eso se lo valida contra personas antes de usarlo y se lo
vuelve a verificar durante el experimento.

**Criterios de elección, fijados antes de ver resultados.** Un LLM-as-a-judge de la misma familia que
el modelo que extrae podría favorecer sus propias respuestas, por lo que se excluyeron las
familias Qwen (extractor de OpenKOS) y Gemma (adjudicador interno de OpenKOS). Se probaron
tres candidatos sobre un conjunto propio: 21 preguntas de ES2015 escritas por una persona y
42 respuestas etiquetadas a mano, porque ningún ranking público mide esta tarea. Los umbrales
se declararon antes de correr cualquier candidato (`config/experiments.toml`,
`[judge.calibration]`):

| Criterio | Umbral | Qué protege |
|---|---|---|
| Acuerdo con las personas (kappa de Cohen, sobre «correcta») | ≥ 0,70 | Que juzgue como lo haría una persona. |
| Consistencia al invertir el orden de presentación | ≥ 0,90 | Que no dependa de qué texto aparece primero. |
| Consistencia entre semillas | ≥ 0,95 | Que el veredicto sea estable. |
| Accuracy en preguntas sin respuesta (E4) | ≥ 0,80 | Que reconozca cuando no hay respuesta. |
| Salidas válidas | ≥ 0,99 | Que el formato de salida se pueda leer. |
| Cambio de veredicto al alargar una respuesta errada | ≤ 0,10 | Que no premie la verbosidad. |

**Resultados** (notebook 05, sección 9; serie de desarrollo ES2015, 42 ítems):

| Candidato | kappa (correcta) | Orden | Latencia por llamada | Cumple todos los umbrales |
|---|---|---|---|---|
| `mistral-small3.2:24b` | 0,951 | 0,952 | 5,5 s | Sí |
| `atla/selene-mini:q8_0` | 0,485 | 0,738 | 3,0 s | No (kappa y orden) |
| **`gpt-oss:20b`** | **0,951** | 0,952 | **3,2 s** | **Sí** |

Dos candidatos cumplen todo con el mismo kappa; la regla fijada de antemano desempata por
rapidez y gana `gpt-oss:20b`, de la familia OpenAI de pesos abiertos, distinta de Qwen. Se
descartaron además `phi4:14b` (contexto de 16 K insuficiente), Llama 3.3 70B (43 GB, no cabe
en el hardware) y las destilaciones de DeepSeek-R1 de base Qwen (heredan la familia del
extractor) (notebook 05, sección 3.2). Parámetros del LLM-as-a-judge: temperatura 0, semilla fija,
razonamiento acotado a nivel `low` (los modelos de razonamiento, sin ese tope, piensan largo
antes de dar el veredicto y la corrida sería impracticable), y una ventana de 5 turnos de
diálogo antes y después de la evidencia (`[judge]` y `[judge.calibration.think]`).

**Fiabilidad de las etiquetas humanas.** Una segunda persona etiquetó 15 ítems por separado:
coincidió en 15 de 15 sobre «correcta» (kappa 1,00) y en 14 de 15 sobre «respaldada» (kappa
0,87).

**Limitaciones declaradas.**

- Muestra pequeña (42 ítems): los intervalos de kappa son anchos.
- Una sola serie, con pocos casos de evolución (E3).
- Las respuestas de calibración las generó `qwen3:8b`, no las tres condiciones.
- El identificador de cada ítem delataba cómo se generó la respuesta, de modo que quienes
  etiquetaron podían saberlo. Se declaró en lugar de reetiquetar; el acuerdo podría estar algo
  inflado y no se puede cuantificar cuánto (notebook 05, sección 9.2).
- El LLM-as-a-judge no evalúa las citas: su corrección se calcula con una regla determinista (ADR 0009),
  porque el LLM-as-a-judge no sabe qué fuentes citó la respuesta.

## 5. Resumen: componentes, técnicas, parámetros y evidencia

| Componente | Técnica / librería | Parámetro clave | Valor | Por qué | Evidencia |
|---|---|---|---|---|---|
| Generador (C1, C2, C3) | `qwen3:8b`, local, vía Ollama | `temperature` / `seed` | 0,1 / 42 | Mismo modelo en las tres condiciones para atribuir la diferencia a la representación | [`config/experiments.toml`](../../config/experiments.toml) `[shared_budget]`; [ADR 0006](../decisions/0006-adr-c1-rag-separado-con-respuesta-de-openkos.md) |
| Generador | Context window | `context_window_tokens` | 12.288 | Valor por defecto de OpenKOS; contexto efectivo de unos 7.400 caracteres | [ADR 0006](../decisions/0006-adr-c1-rag-separado-con-respuesta-de-openkos.md); [ADR 0007](../decisions/0007-adr-ajuste-c1-y-presupuesto-de-contexto.md) (enmienda) |
| *Embeddings* (C1, C2, C3) | `bge-m3` | Modelo | `bge-m3` | Multilingüe; mismo modelo en las tres condiciones | `[shared_budget]`; [ADR 0006](../decisions/0006-adr-c1-rag-separado-con-respuesta-de-openkos.md) |
| C1 fragmentación | Turnos completos con tope de caracteres | `max_chars` | 1.200 | Ganador de la regla prerregistrada sobre ES2015 | [ADR 0007](../decisions/0007-adr-ajuste-c1-y-presupuesto-de-contexto.md) (enmienda); [notebook 06](../../notebooks/06-jss-ajuste-c1.ipynb) |
| C1 fragmentación | Solapamiento de turnos | `overlap_turns` | 1 | Ídem | [ADR 0007](../decisions/0007-adr-ajuste-c1-y-presupuesto-de-contexto.md); [notebook 06](../../notebooks/06-jss-ajuste-c1.ipynb) |
| C1 recuperación | BM25 + densa, fusión RRF | `k` / `rrf_k` | 5 / 60 | K ganador; `rrf_k` igual al de OpenKOS | `[retrieval.c1]`, `[retrieval]`; [notebook 06](../../notebooks/06-jss-ajuste-c1.ipynb) |
| C1 redacción | Prompts de OpenKOS copiados | Huella SHA-256 | Verificada por prueba | Que la instrucción no explique la diferencia entre condiciones | [ADR 0006](../decisions/0006-adr-c1-rag-separado-con-respuesta-de-openkos.md), decisiones 3 y 8 |
| C2 y C3 consulta | `openkos query`, sin modificar | `--limit` | 5 | Valor por defecto de OpenKOS; presupuesto de texto igual, no K igual | [ADR 0007](../decisions/0007-adr-ajuste-c1-y-presupuesto-de-contexto.md), decisiones 3 a 5 |
| C2 orden de reuniones | Fecha de evento con hora real o sintética | `time_source` | `ami` (6 series) / `synthetic` (8) | Las cuatro reuniones comparten fecha; hace falta un orden | [ADR 0008](../decisions/0008-adr-fechas-de-reunion-para-openkos.md); [notebook 08](../../notebooks/08-jss-fechas-de-reunion.ipynb) |
| C2 extracción | OpenKOS (instrumento) | Versión | Por fijar | Se espera la versión con las correcciones | [ADR 0006](../decisions/0006-adr-c1-rag-separado-con-respuesta-de-openkos.md) (enmienda); issue #94 |
| LLM-as-a-judge | `gpt-oss:20b` | `min_kappa_correct` | ≥ 0,70 (obtenido 0,951) | Cumple todos los umbrales y es el más rápido entre los que cumplen; familia distinta a Qwen y Gemma | [notebook 05](../../notebooks/05-jss-seleccion-juez.ipynb); `[judge]` |
| LLM-as-a-judge | Razonamiento acotado | `think` | `low` | Hacer viable una corrida de cientos de llamadas | `[judge.calibration.think]` |
| LLM-as-a-judge | Verificación humana | `human_validation_fraction` | 0,20 | Validar el instrumento durante el experimento | `[evaluation]`; [ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md) |
| Protocolo de alineación (Experimento A) | Cosine similarity (parecido entre representaciones numéricas) + emparejamiento uno a uno (algoritmo húngaro, `scipy`) | `tau_grid` | 0,50 a 0,90 en pasos de 0,05 | Informar F1 como curva sobre τ, no en un solo punto | `[alignment]`; [documento 06](06-jss-metodologia.md), §5–6 |
| Análisis estadístico | *Bootstrap* sobre preguntas | Remuestreos / confianza | 10.000 / 0,95 | Cada resultado lleva intervalo de confianza | `[evaluation]`; [notebook 10](../../notebooks/10-jss-potencia-criterio-d16.ipynb) |
| Criterio principal | Diferencia pareada C2 − C1 en E3 | Intervalo del 95 % | Por encima de 0 | Mayor potencia que comparar intervalos por separado, con falso positivo bajo 5 % | [ADR 0010](../decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md); [notebook 10](../../notebooks/10-jss-potencia-criterio-d16.ipynb) |

## 6. Primeras pruebas y dificultades

El curso valora que se muestren los intentos y los obstáculos. Esta sección separa con
claridad lo que ya corrió de lo que sigue bloqueado.

### 6.1 Qué ya corrió

- **Ajuste de C1** sobre ES2015: 32 configuraciones con una regla fijada antes de correr; se
  encontró y corrigió un error de medición (contar fragmentos completos en lugar del texto
  entregado) y el ganador cambió de 1.600 / 0 / 8 a 1.200 / 1 / 5 (ADR 0007, notebook 06).
- **Selección del LLM-as-a-judge** entre tres candidatos con 42 ítems etiquetados por personas (notebook
  05). Resultado: `gpt-oss:20b`, con el límite de validez declarado en la sección 4.
- **Corrida de humo de C1** sobre 21 preguntas de calibración de ES2015: el motor del
  Experimento B funciona de punta a punta con C1 y el LLM-as-a-judge reales, sin errores en los 21
  registros y con reanudación verificada. Tardó 272 segundos (184 respondiendo y 88 juzgando).
  Son cifras de desarrollo, no resultados: «no se concluye nada sobre la calidad de C1»
  ([notebook 07](../../notebooks/07-jss-runner-experimento-b.ipynb), sección 8).
- **Fechas de reunión** para ordenar las decisiones de una serie, analizadas sobre las 14
  series (ADR 0008, notebook 08).
- **Análisis de potencia** del criterio principal por simulación, sin ejecutar modelos
  (notebook 10): con 25 preguntas en E3 y una diferencia verdadera de +0,15, el criterio de
  diferencia pareada declara «respaldada» en 57,5 % de los experimentos simulados, frente a
  10,4 % del criterio de intervalos separados (dispersión de dificultad 1 y accuracy base 0,5).
- **Primer intento de extracción** con OpenKOS 0.5.2 sobre ES2015: 4 objetos frente a 29
  decisiones con acuerdo evaluado en la referencia (documento 06, §7–8).

### 6.2 Dificultades encontradas y siguiente paso

1. **El recorte de contexto de OpenKOS invalidó una medición propia.** La cifra de 13.516
   caracteres con que se justificó el primer ajuste de C1 se midió antes de que OpenKOS
   limitara el contexto. Se detectó, se repitió el ajuste y se documentó como enmienda sin
   borrar el registro original (ADR 0007).
2. **La marca de atribución se pierde en algunos casos.** En 2 de 21 respuestas de la corrida
   de humo, el modelo escribió `USED:` al final de la frase y OpenKOS 0.5.4 solo lo reconoce
   al inicio de línea; se citaron todos los fragmentos y la precision de la citación bajó
   (0,33 y 0,50). Afecta solo a la citación, no a la corrección. Se corrige en OpenKOS; el
   siguiente paso es portar la corrección a C1 cuando se publique y repetir la corrida de humo
   (issue #87).
3. **La regla de citación tuvo que revisarse.** La primera versión exigía que *todas* las
   citas respaldaran la respuesta y rechazaba 8 de 13 respuestas, y 7 de esas 8 eran correctas; se cambió a «al
   menos una» y se informa la precision aparte (ADR 0009, notebook 09). Queda abierto si el
   tamaño distinto de las citas de C1 y C2 sesga la comparación (issue #97).
4. **La versión de OpenKOS no está fijada.** La 0.5.4 trae `query --json` pero no el paso de
   decisión por reunión ni el orden dentro de un mismo día; las correcciones están en curso en
   OpenKOS (`#1348`, `#1349`, `#1350`, `#1384`). Hasta fijar la versión no se corre ninguna
   evaluación (issue #94). Además, `pyproject.toml` todavía pide `openkos>=0.2.14`, que no
   coincide con lo decidido. Siguiente paso: fijar la versión cuando se publique, enmendar el
   ADR 0006 y actualizar `pyproject.toml` y `uv.lock`.
5. **C2 y C3 no se pueden ejecutar todavía.** El lector de la salida de OpenKOS y la corrida
   real de extracción dependen de esa versión (issue #95), y C3 depende de la anotación
   individual de la Fase 3 (issue #23, #30, #31). Ambas condiciones lanzan hoy un error
   explícito de «sin implementar». Siguiente paso: completar el adaptador y la condición C2 y
   repetir la prueba de extracción sobre ES2015 con la versión fijada.
6. **Las relaciones temporales no salen de forma automática.** OpenKOS deja sus hallazgos de
   revisiones en una tabla interna que no es un contrato estable; hay que mapearlos a los
   tipos de relación de la tesis, con dirección (issue #96).
7. **Ámbito del Experimento A decidido, τ pendiente.** El ámbito principal de la alineación es
   la reunión de origen (la serie completa queda como sensibilidad), el rol principal es el
   mayoritario (cada rol, como sensibilidad) y el intervalo principal es un bootstrap por reuniones
   (Wilson y bootstrap por decisión, como referencia); con pocas reuniones ese intervalo es
   frágil ([ADR 0011](../decisions/0011-adr-alineacion-rol-e-intervalos-del-experimento-a.md),
   issue #99). El umbral τ principal es 0,70, con 0,75 y 0,80 como sensibilidad, fijado sobre series de desarrollo con la referencia en inglés ([ADR 0012](../decisions/0012-adr-umbral-tau-del-experimento-a.md), issue #142).
8. **Anotación humana en curso.** Las recalibraciones, las series de control y el banco de
   preguntas siguen abiertos (issues #19, #27 a #33, #78 y #79); sin ellos no existen C3 ni
   el banco con que se mide. Siguiente paso: cerrar la anotación de referencia para poder
   construir C3 (issues #29 a #31).

---

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| Modelos, versiones y presupuesto compartido (`qwen3:8b`, `qwen3:32b`, `bge-m3`, juez) | [`../../config/experiments.toml`](../../config/experiments.toml) (`[shared_budget]`, `[judge]`) |
| Ajuste de C1: 32 configuraciones, ganador 1.200 / 1 / 5 | [`../../notebooks/06-jss-ajuste-c1.ipynb`](../../notebooks/06-jss-ajuste-c1.ipynb); [`../../reports/c1-tuning/resultados.json`](../../reports/c1-tuning/resultados.json); `src/afg/conditions/c1_tuning.py`; [`../decisions/0007-adr-ajuste-c1-y-presupuesto-de-contexto.md`](../decisions/0007-adr-ajuste-c1-y-presupuesto-de-contexto.md) |
| C1: segmentación, recuperación híbrida y presupuesto de contexto | `src/afg/conditions/c1_chunking.py`, `c1_retrieval.py`, `c1_document_rag.py`, `c1_prompt_budget.py`; `tests/test_c1_chunking.py`, `test_c1_retrieval.py`, `test_c1_document_rag.py`, `test_c1_prompt_budget.py` |
| C1 separado de OpenKOS, respuesta con los prompts de OpenKOS | [`../decisions/0006-adr-c1-rag-separado-con-respuesta-de-openkos.md`](../decisions/0006-adr-c1-rag-separado-con-respuesta-de-openkos.md); `src/afg/conditions/answer_prompts.py` |
| Selección del LLM-as-a-judge: tres candidatos, 42 ítems, `gpt-oss:20b` | [`../../notebooks/05-jss-seleccion-juez.ipynb`](../../notebooks/05-jss-seleccion-juez.ipynb); [`../../reports/judge-calibration/resultados.json`](../../reports/judge-calibration/resultados.json); [`../anotacion/calibracion-juez.md`](../anotacion/calibracion-juez.md) |
| Acuerdo humano de la calibración del juez (1,00 y 0,87) | [`../../reports/judge-calibration/acuerdo-humano.json`](../../reports/judge-calibration/acuerdo-humano.json) |
| Corrida de humo de C1 sobre ES2015 (21 registros, 272 s) | [`../../notebooks/07-jss-runner-experimento-b.ipynb`](../../notebooks/07-jss-runner-experimento-b.ipynb); [`../../reports/experiment-b/humo-c1-es2015/manifest.json`](../../reports/experiment-b/humo-c1-es2015/manifest.json) |
| Regla de citación correcta | [`../../notebooks/09-jss-regla-de-citacion.ipynb`](../../notebooks/09-jss-regla-de-citacion.ipynb); [`../decisions/0009-adr-regla-de-citacion-correcta.md`](../decisions/0009-adr-regla-de-citacion-correcta.md) |
| Fechas de reunión para OpenKOS | [`../../notebooks/08-jss-fechas-de-reunion.ipynb`](../../notebooks/08-jss-fechas-de-reunion.ipynb); [`../decisions/0008-adr-fechas-de-reunion-para-openkos.md`](../decisions/0008-adr-fechas-de-reunion-para-openkos.md) |
| Potencia del criterio principal | [`../../notebooks/10-jss-potencia-criterio-d16.ipynb`](../../notebooks/10-jss-potencia-criterio-d16.ipynb) |
| Primer intento de extracción de C2: 4 objetos frente a 29 decisiones con acuerdo evaluado (27 finales) | [`06-jss-metodologia.md`](06-jss-metodologia.md) §7–8; [`../../data/processed/decisions/ES2015.decisions.adjudicated.csv`](../../data/processed/decisions/ES2015.decisions.adjudicated.csv) |
