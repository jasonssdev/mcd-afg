| | |
|---|---|
| **Entrega** | Video de avance #1 (semana 2), AFG1 |
| **Fecha de envío** | Semana 2 del curso (fecha exacta por completar) |
| **Versión** | 1.0 |
| **Construido desde** | Versión previa de la propuesta, anterior a la auditoría de datos |
| **Estado** | Congelado tal como se envió. **No se edita.** |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Incorporación al repositorio del guion tal como se envió. | Registro del entregable. |

> **Aviso de lectura.** Refleja el diseño de la semana 2. La versión vigente de problema,
> objetivos y metodología está en `docs/avances/`.

---

# Guion final de grabación --- OpenKOS · Propuesta de tesis

**Duración total:** 05:00 exactos\
**Fuente:** Speaker Notes de la versión final de la PPT.\
**Uso:** texto de locución coordinado con los timecodes, animaciones y
microdemos definidos en la presentación.

------------------------------------------------------------------------

## Portada

**Timecode:** 00:00--00:04 · **Duración:** 00:04

*Sin locución. Mantener la lámina según el tiempo indicado en la PPT.*

------------------------------------------------------------------------

## Slide 1 --- Decisiones estructuradas

**Timecode:** 00:04--00:40 · **Duración:** 00:36

Estimado tutor y compañeros, muy buenos días. Mi nombre es \[NOMBRE DEL
EXPOSITOR\] y, en representación del equipo integrado por Gustavo
Martínez, Jason Sepúlveda y German Vega, presentaré nuestra propuesta de
tesis para el Magíster en Ciencia de Datos. El proyecto estudia la
representación estructurada de decisiones frente a la recuperación
aumentada, mediante una evaluación experimental con modelos de lenguaje
sobre transcripciones de reuniones. Las reuniones producen decisiones
constantemente, pero quedan registradas casi exclusivamente como texto
no estructurado. La pregunta que abre este trabajo es si aporta valor
representar de forma persistente esas decisiones, o si basta con
recuperar las transcripciones cuando se necesitan. OpenKOS aparece
únicamente como demostración práctica del enfoque; el objeto de la
investigación es la evaluación experimental.

------------------------------------------------------------------------

## Slide 2 --- Cuál es el problema

**Timecode:** 00:40--01:28 · **Duración:** 00:48

Las decisiones quedan registradas casi exclusivamente en texto no
estructurado. De ahí surgen tres dificultades. Primero, la
fragmentación. Una decisión rara vez está contenida en un solo pasaje:
se propone en un momento, se discute en otro y se cierra en un tercero.
Por eso recuperar un fragmento no equivale a reconstruir una decisión ni
la evidencia que la sustenta. Segundo, las decisiones evolucionan: se
introducen, se confirman o se revisan, y se reemplazan a lo largo de
varias sesiones. RAG consulta las transcripciones originales en cada
interacción, pero no mantiene una representación persistente de ese
historial. Tercero, el material es sensible. Esto no distingue nuestra
propuesta de RAG ---ambas condiciones pueden ejecutarse localmente---
pero condiciona el diseño: todo el estudio corre sobre infraestructura
local, lo que además controla la variable del modelo generador. Existen
antecedentes directos de detección de decisiones sobre este tipo de
corpus. El vacío es otro: falta una evaluación controlada que separe el
valor de una representación persistente de los errores introducidos por
su extracción automática, sobre todo en consultas longitudinales sobre
decisiones revisadas o reemplazadas. Y hay un riesgo que el propio
método introduce: un error de RAG es transitorio, mientras que una
decisión mal compilada persiste y adquiere apariencia de dato
verificado. Cuantificar esa asimetría es parte del proyecto, no un
supuesto previo.

------------------------------------------------------------------------

## Slide 3 --- Por qué utilizar Ciencia de Datos

**Timecode:** 01:28--02:08 · **Duración:** 00:40

¿Por qué la Ciencia de Datos? Porque convierte un problema que suele
tratarse como desarrollo de herramientas en uno que puede medirse y
refutarse. Primero, formaliza la extracción como una tarea supervisada
evaluable: detectar decisiones a partir de actos de diálogo se plantea
como clasificación y extracción de información. Eso nos permite comparar
la predicción del modelo contra anotaciones humanas de referencia sobre
el AMI Meeting Corpus, con precisión, cobertura y F1. Segundo, impone
estructura verificable sobre la salida del modelo: mediante esquemas de
validación estricta obligamos al modelo a producir objetos con
descripción, fecha, evidencia de origen y estado, y rechazamos de forma
determinista lo que no cumpla el esquema. Tercero, aporta el diseño para
un contraste controlado: mismo corpus, mismo modelo generador y tres
condiciones comparables, en lugar de un simple benchmark de
herramientas. Toda la inferencia se ejecuta localmente; eso es lo que
muestra esta breve demostración de OpenKOS.

**Microdemo:** OpenKOS Doctor + Init · ventana definida en la PPT:
02:00--02:07.

------------------------------------------------------------------------

## Slide 4 --- Objetivo del proyecto

**Timecode:** 02:08--02:48 · **Duración:** 00:40

Nuestro objetivo general es diseñar y evaluar un método para extraer
automáticamente decisiones desde transcripciones de reuniones mediante
modelos de lenguaje de ejecución local, representarlas de forma
estructurada conservando su contenido, evidencia y evolución temporal, y
determinar experimentalmente en qué condiciones esa representación
aporta valor en términos de calidad, trazabilidad o eficiencia frente a
RAG aplicado directamente sobre las transcripciones. La cinta resume ese
recorrido: el alcance experimental son las decisiones, no un sistema
general de gestión del conocimiento. La demostración ilustra la ingesta:
el texto se convierte en una representación persistente y consultable.
Ese objetivo se abre en dos preguntas que mantenemos separadas: una de
extracción y otra de utilidad de la representación.

FORMULACIÓN ACADÉMICA COMPLETA (referencia de guion, no se locuta
íntegra): PREGUNTA EXPERIMENTAL 1 · EXTRACCIÓN --- ¿Con qué nivel de
precisión pueden modelos de lenguaje locales detectar, normalizar y
vincular con evidencia las decisiones contenidas en transcripciones, en
comparación con métodos clásicos de NLP? PREGUNTA EXPERIMENTAL 2 ·
UTILIDAD DE LA REPRESENTACIÓN --- ¿En qué tipos de consulta una base
persistente y estructurada de decisiones responde con mayor calidad,
trazabilidad o eficiencia que un sistema RAG sobre las transcripciones?
La primera compara métodos de extracción; la segunda compara
representaciones y pipelines de consulta. Combinarlas ocultaría el valor
potencial de la representación detrás de los errores del extractor.

**Microdemo:** OpenKOS Ingest · ventana definida en la PPT:
02:32--02:42.

------------------------------------------------------------------------

## Slide 5 --- Metodología de evaluación

**Timecode:** 02:48--03:40 · **Duración:** 00:52

El diseño experimental compara tres condiciones sobre el mismo corpus,
con el mismo modelo generador y las mismas preguntas. La primera
condición es RAG documental: recuperación directa sobre las
transcripciones originales. La segunda es la base compilada manualmente:
el techo teórico, es decir, la representación estructurada sin errores
de extracción. La tercera es la base compilada automáticamente: el
sistema completo, con los errores del modelo incluidos. La segunda
condición es la que convierte el proyecto en un experimento y no en una
demostración. Sin ella, un mal resultado sería ambiguo: no sabríamos si
falló la idea de estructurar o si falló el modelo al extraer. Con ella,
ambas preguntas se analizan por separado. Trabajamos sobre el AMI
Meeting Corpus, que incluye series de reuniones de un mismo grupo; eso
permite evaluar consultas longitudinales sobre decisiones revisadas o
reemplazadas. Las tres condiciones responden el mismo conjunto de
preguntas y sus resultados se comparan cuantitativamente. La
demostración solo ilustra cómo una consulta devuelve una respuesta con
su evidencia.

**Microdemo:** OpenKOS Query · ventana definida en la PPT: 03:33--03:39.

------------------------------------------------------------------------

## Slide 6 --- Cuantificación del rendimiento

**Timecode:** 03:40--04:18 · **Duración:** 00:38

La validez del experimento se sostiene en cuatro dimensiones de
medición. Primero, el rendimiento de NLP: precisión, cobertura y F1 de
las decisiones extraídas, comparadas contra un ground truth anotado por
humanos sobre el AMI Meeting Corpus. Segundo, las citas: la tasa de
citas incorrectas y la verificación de que cada afirmación tenga
respaldo en el texto de origen; sin respaldo, se marca como posible
alucinación, no como alucinación confirmada. Tercero, las métricas
operativas del procesamiento local: latencia de inferencia y uso de
memoria, operacionalizado como RAM y VRAM. Cuarto, el comportamiento no
determinista: repetiremos la misma entrada en múltiples ejecuciones y
reportaremos la variabilidad, no un número único. Así no solo se
evaluará si el sistema responde, sino cuán trazable, eficiente y
reproducible es su comportamiento.

------------------------------------------------------------------------

## Slide 7 --- Cierre

**Timecode:** 04:18--04:55 · **Duración:** 00:37

Con esto cerramos la propuesta. El criterio de éxito es explícito:
producir la comparación, no ganarla. Todos los resultados son
informativos: que la base estructurada supere a RAG, que lo iguale, que
RAG resulte superior en consultas puntuales o que los métodos clásicos
basten para extraer. Cualquiera de ellos responde la pregunta de
investigación. Como el sistema evaluado lo desarrolla un integrante del
equipo, el protocolo, las métricas, el criterio de emparejamiento y los
umbrales se registran con fecha verificable antes de experimentar, y el
baseline RAG sigue buenas prácticas documentadas. El alcance
experimental son las decisiones; OpenKOS es solo la demostración
práctica del enfoque. Muchas gracias por su atención.

------------------------------------------------------------------------

## Slide final --- Muchas gracias

**Timecode:** 04:55--05:00 · **Duración:** 00:05

*Sin locución. Mantener la lámina según el tiempo indicado en la PPT.*

------------------------------------------------------------------------

## Control maestro

  Segmento                                                  Timecode    Duración
  ----------------------------------------------- ------------------ -----------
  Portada                                               00:00--00:04       00:04
  Slide 1 --- Decisiones estructuradas                  00:04--00:40       00:36
  Slide 2 --- Cuál es el problema                       00:40--01:28       00:48
  Slide 3 --- Por qué utilizar Ciencia de Datos         01:28--02:08       00:40
  Slide 4 --- Objetivo del proyecto                     02:08--02:48       00:40
  Slide 5 --- Metodología de evaluación                 02:48--03:40       00:52
  Slide 6 --- Cuantificación del rendimiento            03:40--04:18       00:38
  Slide 7 --- Cierre                                    04:18--04:55       00:37
  Slide final --- Muchas gracias                        04:55--05:00       00:05
  **TOTAL**                                         **00:00--05:00**   **05:00**

### Regla de sincronización

La PPT es la referencia de timing y animación. Durante la grabación, la
locución debe seguir literalmente este guion y respetar los bloques
temporales de cada slide. Los disparadores y offsets de las animaciones
permanecen documentados en las Speaker Notes de la presentación.
