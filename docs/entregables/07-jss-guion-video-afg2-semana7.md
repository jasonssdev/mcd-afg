# Guion — Video de avance #3 de AFG2, semana 7: resultados preliminares

| | |
|---|---|
| **Entrega** | Video de avance #3 de AFG2 (semana 7) — resultados preliminares |
| **Fecha de envío** | Pendiente |
| **Versión** | 1.0 |
| **Construido desde** | `docs/avances/13-jss-conclusiones.md` v1.1 (fuente principal de las cifras) · `docs/avances/10-jss-confiabilidad-de-la-referencia.md`, `11-jss-resultados-experimento-a.md` y `12-jss-resultados-experimento-b.md` · `docs/avances/informes/02-jss-pre-informe.md` v1.4 (título y encuadre para un lector externo) · `notebooks/32-jss-figuras-video-resultados.ipynb` (seis figuras exportadas a `docs/entregables/figuras/resultados-*.png`) · `notebooks/15-jss-screen-de-modelos-openkos.ipynb` (última sección, solo para la frase sobre un modelo más nuevo) |
| **Duración objetivo** | 9:00 a 145 palabras por minuto (máximo de la rúbrica: 10:00) |
| **Formato** | Tres presentadores en cuatro bloques consecutivos, en este orden: Jason, Germán, Gustavo, Jason. Con diapositivas de apoyo, que se construyen después de este guion |
| **Extensión hablada** | 1.295 palabras: 255 + 375 + 260 + 405. A 145 palabras por minuto son 8:56; a 140, 9:15 |

> **Por qué existe este documento.** El profesor evalúa solo el video, así que los resultados
> deben verse y oírse en él. Este guion cuenta una historia: una promesa que falla y la
> investigación de por qué. La idea de organizar las decisiones en una base sonaba mejor que
> buscar en el texto; no lo fue, y un experimento de control mostró dónde se pierde el valor.
> Siguiendo la clase 4 del curso, cada resultado se reporta, se compara con la línea base y se
> interpreta (por qué y qué implica), y cada objetivo se cierra de forma explícita con un
> resultado. Los resultados negativos se muestran como resultados. Las técnicas y métricas se
> nombran en voz y se explican en palabras corrientes la primera vez que aparecen. Las cifras
> son de las series de evaluación; se dicen solo agregados e identificadores, nunca texto de
> decisiones, transcripciones ni respuestas.

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-11-19 | Versión inicial: guion del tercer video de avance de AFG2, centrado en los resultados preliminares, con plan de láminas. | Pauta de la semana 7 y avance 13 v1.1. Las láminas se construyen después, desde este guion. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## Qué pide el curso y dónde se cubre

Objetivo del video según la rúbrica: presentar resultados preliminares con evidencia, positiva
o negativa, y una interpretación inicial que reflexione sobre el avance, las limitaciones y los
próximos pasos. Nivel «logrado»: resultados claros y relevantes (métricas, gráficos,
comparaciones), interpretación que conecta los hallazgos con el problema, y próximos pasos
sugeridos. Formato: libre, con diapositivas de apoyo; máximo de 10 minutos. Las pautas de la
semana 7 piden además mostrar resultados negativos o inesperados y destacar cómo los resultados
validan o cuestionan la propuesta metodológica.

| Elemento del nivel «logrado» | Dónde se cubre |
|---|---|
| Resultados claros y relevantes (métricas, gráficos, comparaciones) | Sección 3 (kappa), sección 4 (corrección por condición y por tipo de pregunta), sección 5 (embudo de extracción y causas del error), sección 6 (costo) |
| Comparación con la línea base | Sección 4 (C1 frente a C2 y C3), sección 6 (C3 frente a C1) |
| Interpretación que conecta con el problema | Sección 5 (C3 como control: dónde se pierde el valor), sección 6 (qué significa) |
| Resultado negativo mostrado como resultado | Sección 4 (criterio D16 no respaldado, con dirección contraria) |
| Cada objetivo cerrado con un resultado | Secciones 3 a 6 (OE1, OE3, OE2 y OE4, veredicto objetivo por objetivo en la sección 6) |
| Limitaciones y dificultades | Sección 7 |
| Próximos pasos | Sección 8 |

## Reparto de tiempos

| Bloque | Persona | Palabras | Tiempo (145 ppm) | Mensaje central |
|---|---|---|---|---|
| 1 Gancho (0:00 – 0:45) y 2 Contexto y vara de medir (0:45 – 1:50) | Jason | 255 | 0:00 – 1:50 | La promesa (organizar decisiones en una base), el problema, las cuatro condiciones C0 a C3 y los cuatro objetivos OE1 a OE4 |
| 3 OE1 (1:50 – 2:45) y 4 OE3 (2:45 – 4:30) | Germán | 375 | 1:50 – 4:30 | Referencia confiable; la base automática responde peor que buscar en el texto; criterio D16 no respaldado |
| 5 El giro: C3 como control (4:30 – 6:15) | Gustavo | 260 | 4:30 – 6:15 | La diferencia entre C3 y C2 mide el costo de la extracción: la máquina encuentra 3 de cada 10 decisiones y la mitad de los errores nace al extraer |
| 6 Impacto y costo (6:15 – 7:20), 7 Limitaciones (7:20 – 8:10) y 8 Próximos pasos y cierre (8:10 – 9:00) | Jason | 405 | 6:15 – 9:00 | Con buenas decisiones la base gana; cuesta 2,7 veces más por consulta; veredicto por objetivo; límites; AFG3 |

Reparto por persona: Jason 255 + 405 palabras, Germán 375, Gustavo 260. Los tiempos por
sección están en los títulos de cada una; las palabras por sección, en la tabla de trazabilidad
de más abajo.

## Notas de grabación

- El texto está escrito para decirse, no para leerse. Frases cortas, una idea por oración.
- En el texto hablado cada presentador dice «yo» y «nosotros»: es la excepción a la regla
  impersonal del repositorio, que sigue valiendo para las partes escritas de este documento.
- Cada bloque abre nombrando a quien habla (la primera vez, solo con el nombre de pila) y cierra
  pasando el turno.
- Los nombres de técnicas y métricas se dicen en inglés tal como son (RAG, *baseline*, *ground
  truth*, kappa de Cohen, *recall*, F1, τ se dice «tau»; `qwen3:8b` se dice «quen tres, ocho be»;
  `gpt-oss:20b`, «yi pi ti oss, veinte be»). Cada una se explica en la misma oración en que
  aparece.
- Las citas entre comillas angulares que empiezan con ▶ no se dicen: marcan el momento en que
  cambia la lámina, con su título (la conclusión), la imagen y el texto mínimo en pantalla.
- Cronometrar un ensayo completo antes de grabar. Si se pasa de 10:00, recortar primero la frase
  del modelo más nuevo (sección 7) y luego los intervalos de D16 (sección 4); no los objetivos
  ni las explicaciones de las métricas.
- Todas las cifras salen de `docs/avances/13-jss-conclusiones.md` v1.1 y de los documentos y
  notebooks que cita. Ninguna se calcula aquí. Son de las once series de evaluación, una corrida
  formal por experimento, un solo modelo local: describen ese caso y no se generalizan.

---

## Bloque 1 — Jason (0:00 – 1:50)

### Sección 1 — Gancho (0:00 – 0:45)

> **▶ Lámina 1 — se muestra al empezar.**
>
> Título (conclusión): «Ordenar las decisiones en una base parecía mejor que buscar en el texto». Visual: solo texto grande. Texto en pantalla: la pregunta «¿Sirve más una base de decisiones que buscar en el texto?» y, abajo, «Spoiler: no, pero un control mostró dónde se pierde el valor». Sin cifras.

Hola, soy **Jason**. Junto a Germán y Gustavo presentamos los resultados preliminares de nuestro proyecto. Empiezo con una pregunta. Hoy casi toda reunión se transcribe, pero las decisiones, y cómo cambian de una reunión a otra, quedan enterradas en texto conversacional. ¿Sirve más ordenarlas en una base que simplemente buscar en el texto? Una base permitiría preguntar por una decisión y por su historia, sin releer reuniones enteras. Nuestra hipótesis decía que sí. Los resultados dicen que no, al menos no como lo hicimos. Pero un experimento de control nos mostró exactamente dónde se pierde el valor, y de eso trata este video.

### Sección 2 — Contexto y vara de medir (0:45 – 1:50)

> **▶ Lámina 2 — se muestra al decir «Comparamos cuatro condiciones».**
>
> Título (conclusión): «Cuatro condiciones, de menos a más ayuda». Visual: tabla de cuatro filas, una por condición, con una frase corta cada una. Texto en pantalla: C0 sin ayuda (piso) · C1 búsqueda en el texto, RAG (*baseline*) · C2 base automática (OpenKOS con `qwen3:8b`) · C3 base con decisiones humanas (control). Pie: «El mismo modelo responde en las cuatro».
>
> **▶ Lámina 3 — se muestra al decir «Los objetivos son cuatro».**
>
> Título (conclusión): «Cada objetivo se cierra con un resultado». Visual: tira de cuatro casillas, una por objetivo, vacías de resultado (se completan en la lámina 13). Texto en pantalla: OE1 referencia humana · OE2 qué encuentra la máquina · OE3 quién responde mejor · OE4 dónde nace el error.

Comparamos **cuatro condiciones**, de menos a más ayuda. **C0**, sin ayuda: el modelo responde solo con lo que ya sabe; es nuestro piso, lo mínimo que se obtiene sin ninguna ayuda. **C1**, la línea base, o *baseline*: busca en el texto los fragmentos más parecidos a la pregunta, la técnica llamada **RAG**, recuperación aumentada por generación. **C2**, la base automática: un sistema llamado OpenKOS, con el modelo **qwen3:8b**, extrae las decisiones de las transcripciones y las guarda en una base. **C3**, el control: la misma base, pero con decisiones hechas por personas.

Los **objetivos son cuatro**. **OE1**: construir una referencia humana, lo que se llama *ground truth*. **OE2**: medir cuánto de esa referencia encuentra la máquina. **OE3**: comparar las cuatro condiciones. **OE4**: cuando C2 falla, saber en qué etapa nació el error. En todas las condiciones responde el mismo modelo, qwen3:8b, y un **juez automático**, otro modelo llamado gpt-oss:20b, califica cada respuesta.

---

## Bloque 2 — Germán (1:50 – 4:30)

### Sección 3 — OE1: la referencia (1:50 – 2:45)

> **▶ Lámina 4 — se muestra al decir «Parto por OE1».**
>
> Título (conclusión): «Dos personas coinciden bien en qué es una relación». Visual: `resultados-oe1-kappa.png` (kappa de existencia y de tipo sobre las bandas de Landis y Koch). Texto en pantalla: «14 series · 358 decisiones · 46 relaciones». Pie: «7 de 11 series de evaluación anotadas por una sola persona».

Soy **Germán**. Parto por OE1, la referencia. Dos personas anotaron por separado qué decisiones se relacionan entre reuniones. El resultado es una referencia de **14 series, 358 decisiones y 46 relaciones**. Para saber si es confiable usamos el **kappa de Cohen**, que mide cuánto coinciden dos personas descontando el azar. Una relación ocurre cuando una decisión posterior cambia o matiza una anterior. Para decidir si existe una relación, el kappa es **0,783**: en la escala de Landis y Koch, un acuerdo sustancial, una guía de lectura y no una prueba. Para decidir de qué tipo es la relación, **0,554**: moderado. La dirección de la relación no tiene kappa, porque casi no hubo variación: el acuerdo fue del 100 %. Una limitación importante: en 7 de las 11 series de evaluación anotó una sola persona, y ahí no hay medida de acuerdo.

### Sección 4 — OE3: la comparación (2:45 – 4:30)

> **▶ Lámina 5 — se muestra al decir «Sigo con OE3».**
>
> Título (conclusión): «La base automática responde peor que buscar en el texto». Visual: `resultados-oe3-total.png` (corrección total: C0 0,16 · C1 0,72 · C2 0,49 · C3 0,80). Texto en pantalla: solo el título y la figura; pie «99 preguntas, mismo modelo, juez automático».
>
> **▶ Lámina 6 — se muestra al decir «Separemos por tipo de pregunta».**
>
> Título (conclusión): «La brecha crece en las preguntas de evolución». Visual: `resultados-oe3-por-tipo.png` (hecho puntual, estado vigente y evolución para C1, C2 y C3). Texto en pantalla: «Evolución: C1 0,54 · C2 0,17 · C3 0,71».
>
> **▶ Lámina 7 — se muestra al decir «El criterio principal».**
>
> Título (conclusión): «El criterio principal no se respalda, y la dirección es la contraria». Visual: solo texto con una línea numérica simple del intervalo. Texto en pantalla: «D16: C2 menos C1 en evolución = −0,38 (intervalo de 95 %: −0,61 a −0,14)». Pie: «Sin el tipo “sin respuesta”: abstenerse cuenta como acierto».

Sigo con **OE3**, la comparación. Respondimos las mismas 99 preguntas con cada condición, y el juez calificó si cada respuesta decía lo mismo que la de referencia. Esta es la proporción de respuestas correctas. C0, sin ayuda: **0,16**, lo esperable si el modelo no ve ningún texto. C1, buscar en el texto: **0,72**. C2, la base automática: **0,49**. Y C3, la base con decisiones humanas: **0,80**. La base automática responde peor que buscar en el texto, y la base con decisiones humanas incluso lo supera. Esa distancia es el corazón de lo que sigue.

Separemos por **tipo de pregunta**: un hecho puntual, donde C1 y C3 aciertan 0,72 y C2 solo 0,43; el estado vigente de una decisión, donde C1 llega a 0,64, C2 a 0,35 y C3 a 0,76; o su evolución a lo largo de varias reuniones. En evolución, donde la base debía lucirse, C2 cae a **0,17**; el RAG llega a **0,54** y C3, a **0,71**. El **criterio principal** del proyecto, que llamamos D16, decía que la base automática superaría al texto justamente en evolución. La diferencia salió de **menos 0,38**, con un intervalo de confianza de 95 %, un rango plausible, de menos 0,61 a menos 0,14, completamente bajo cero. No se respalda, y la dirección es la contraria. Dejamos fuera las preguntas sin respuesta en los datos, porque abstenerse cuenta como acierto e infla a quien más se abstiene.

---

## Bloque 3 — Gustavo (4:30 – 6:15)

### Sección 5 — El giro: C3 como control (4:30 – 6:15)

> **▶ Lámina 8 — se muestra al decir «Aquí viene el giro».**
>
> Título (conclusión): «La diferencia entre C3 y C2 mide lo que cuesta extraer automáticamente». Visual: diagrama simple de dos filas, C2 y C3, con la misma caja «código de consulta» y distintas cajas «decisiones» (máquina / personas). Texto en pantalla: «Mismo código de consulta; solo cambian las decisiones». Cifra de apoyo: «Evolución: 0,17 → 0,71».
>
> **▶ Lámina 9 — se muestra al decir «Entonces medimos OE2».**
>
> Título (conclusión): «La máquina encuentra 3 de cada 10 decisiones». Visual: `resultados-oe2-embudo.png` (100 decisiones humanas frente a 31 encontradas). Texto en pantalla: «Precisión 0,149 · recall 0,308 · F1 0,201 (τ = 0,70)». Pie: «Regla de alineamiento validada por una persona: 0,825 (criterio 0,80)».
>
> **▶ Lámina 10 — se muestra al decir «Por último, OE4».**
>
> Título (conclusión): «La mitad de los errores nace al extraer». Visual: `resultados-oe4-causas.png` (extracción 21, recuperación 11, síntesis 11, de 43 respuestas incorrectas). Texto en pantalla: solo el título y la figura.

Soy **Gustavo**. Aquí viene el giro. C2 y C3 usan exactamente el mismo código para consultar la base; solo cambian las decisiones. Por eso la distancia entre C3 y C2 mide cuánto cuestan los errores de la extracción automática. Y es grande: en evolución, de **0,17 a 0,71**. El código de consulta no es lo que limita a C2: lo que lo limita son las decisiones que recibe.

Entonces medimos **OE2**: ¿cuánto encuentra la máquina? De cada 100 decisiones de la referencia humana, encuentra unas **31**. Usamos un umbral de similitud, **tau, de 0,70**, que define cuándo dos decisiones cuentan como la misma. La **precisión** es 0,149: de lo que la máquina propone, esa fracción es correcta. El **recall** es 0,308: de lo que las personas marcaron, esa fracción encuentra. El **F1**, que resume ambas, es 0,201. Si miramos solo las relaciones, encuentra 11 de 111 de extremo a extremo, y 11 de 24 cuando ya halló sus dos decisiones. Repetir la extracción da casi lo mismo, así que no es azar: es una propiedad de este modelo y esta configuración. Y una persona verificó a mano la regla de alineamiento: concordancia de 0,825, sobre el criterio de 0,80.

Por último, **OE4**. De 43 respuestas incorrectas de C2 en hechos puntuales, **21** nacen en la extracción, 11 en la recuperación y 11 en la síntesis, que es redactar la respuesta. El dato se pierde sobre todo al extraer. Ojo: el diseño de la extracción de OpenKOS y la capacidad del modelo pequeño están confundidos, y este experimento no los separa.

---

## Bloque 4 — Jason (6:15 – 9:00)

### Sección 6 — Impacto y costo (6:15 – 7:20)

> **▶ Lámina 11 — se muestra al decir «Vuelvo yo».**
>
> Título (conclusión): «Con buenas decisiones, la base supera al texto, sobre todo en evolución». Visual: dos pares de cifras grandes, sin figura nueva. Texto en pantalla: «Total: C3 0,80 · C1 0,72. Evolución: C3 0,71 · C1 0,54». Pie: «Lectura descriptiva: esta comparación no estaba preregistrada».
>
> **▶ Lámina 12 — se muestra al decir «Y tiene un costo».**
>
> Título (conclusión): «Cada consulta a la base cuesta 2,7 veces más tiempo que buscar en el texto». Visual: `resultados-costo-latencia.png` (segundos por consulta de cada condición; C1 5,7 s, C2 15,3 s). Texto en pantalla: «Sin punto de equilibrio». Pie: «Tiempo de pared en una sola máquina».
>
> **▶ Lámina 13 — se muestra al decir «Objetivo por objetivo».**
>
> Título (conclusión): «Los cuatro objetivos tienen un resultado». Visual: la tira de cuatro casillas de la lámina 3, ahora completa. Texto en pantalla: OE1 acuerdo sustancial (kappa 0,783) · OE2 recall 0,308 · OE3 C1 0,72 frente a C2 0,49 · OE4 21 de 43 al extraer.

Vuelvo yo. ¿Qué significa todo esto? Con buenas decisiones, la base supera al RAG, sobre todo en evolución: **0,71 frente a 0,54**. Es una lectura descriptiva, porque esa comparación no estaba preregistrada, y C3 no es un techo: sus conceptos y fuentes siguen siendo automáticos. Y tiene un costo: una consulta a la base tarda **15,3 segundos**, frente a **5,7** del RAG, unas **2,7 veces** más. Construir la base, además, toma horas. Por eso no existe punto de equilibrio: nunca sale más barata por consulta. En palabras simples: estos resultados no respaldan reemplazar la búsqueda de texto por una base automática con un modelo pequeño; el resultado negativo es un resultado. Objetivo por objetivo: OE1, cumplido, con acuerdo sustancial. OE2, la extracción es el eslabón débil. OE3, el texto gana a la base automática. OE4, el error nace sobre todo al extraer.

### Sección 7 — Limitaciones (7:20 – 8:10)

> **▶ Lámina 14 — se muestra al decir «Las limitaciones».**
>
> Título (conclusión): «Las cifras describen este caso y no se generalizan». Visual: lista de cuatro viñetas cortas. Texto en pantalla: un solo modelo local pequeño · una corrida formal por experimento · extractor elegido con series de desarrollo · «sin respuesta» inflado por la abstención · H4 no evaluable con el juez automático.

Las **limitaciones**. Usamos un solo modelo local pequeño y una corrida formal por experimento, así que las cifras no se generalizan a otros modelos. El extractor se eligió con series de desarrollo. El tipo de pregunta sin respuesta está inflado por la abstención. Son 99 preguntas, así que los intervalos son anchos y las cifras por tipo son descriptivas. El juez es más estricto con C0 que las personas, por lo que su 0,16 probablemente está subestimado. Y la hipótesis H4, sobre respuestas que suenan seguras pero están desactualizadas, no se pudo evaluar con el juez automático. Probamos después un modelo más nuevo, Qwen3.8 de 27 mil millones de parámetros, y no habría cambiado la elección del extractor: su F1 quedó bajo el de qwen3.6:27b y no cumplió el margen registrado en una de las dos series.

### Sección 8 — Próximos pasos y cierre (8:10 – 9:00)

> **▶ Lámina 15 — se muestra al decir «Para AFG3».**
>
> Título (conclusión): «Tres pasos para AFG3: la extracción, el juez y la referencia». Visual: tres casillas numeradas. Texto en pantalla: 1 extractor más grande (H3) · 2 un juez que pueda evaluar H4 · 3 ampliar la doble anotación.
>
> **▶ Lámina 16 — se muestra al decir «Volviendo a la pregunta inicial».**
>
> Título (conclusión): «La idea funciona cuando las decisiones son buenas; falla obtenerlas automáticamente». Visual: solo texto, con la pregunta de la lámina 1 y la respuesta. Texto en pantalla: «Decisiones buenas: C3 0,80 · Extracción automática con un modelo pequeño: C2 0,49».

Para **AFG3** proponemos tres pasos. Probar un extractor más grande, un modelo de mayor escala que ya está configurado pero no se corrió, y que pondría a prueba la hipótesis H3: si la dirección de las relaciones sigue fallando con modelos mayores. Construir un juez que pueda evaluar H4, con respuestas desactualizadas preparadas a propósito, porque hoy el juez automático no permite ponerla a prueba. Y ampliar la doble anotación a las series que tienen un solo anotador. Además, una hipótesis a probar: que una persona confirme las decisiones al capturarlas, con la búsqueda de texto como respaldo. Volviendo a la pregunta inicial: la idea funciona cuando las decisiones son buenas; lo que falla es obtenerlas automáticamente con un modelo pequeño. Muchas gracias por su atención.

---

## Trazabilidad de las cifras dichas en cámara

Cada fila lista una cifra, dónde se dice y su fuente. Las series son de evaluación: ninguna fila contiene texto de decisiones, transcripciones ni respuestas.

| Sección | Palabras | Cifra o dato | Fuente |
|---|---|---|---|
| 1 | 103 | Sin cifras; el problema y la hipótesis | 13, «En una página» y §1 |
| 2 | 152 | Cuatro condiciones C0 a C3; objetivos OE1 a OE4; generador `qwen3:8b`, juez `gpt-oss:20b` | 13, §1 y §2; 12, tabla de configuración (modelo generador y juez) |
| 3 | 141 | 14 series, 358 decisiones, 46 relaciones | 13, §2 (OE1); nb. 31 §2.1 |
| 3 |  | kappa 0,783 (existencia) y 0,554 (tipo); acuerdo del 100 % en la dirección; sustancial y moderado (Landis y Koch) | 13, §2 (OE1); 10 (escala de Landis y Koch); nb. 32 §1, figura `resultados-oe1-kappa.png` |
| 3 |  | 7 de las 11 series de evaluación con un solo anotador | 13, §2.1 y §7 |
| 4 | 234 | Corrección total: C0 0,16 · C1 0,72 · C2 0,49 · C3 0,80; 99 preguntas | 13, §2.3 y §7; nb. 32 §2, `resultados-oe3-total.png` |
| 4 |  | Por tipo: hecho puntual C1 0,72, C2 0,43, C3 0,72; estado vigente C1 0,64, C2 0,35, C3 0,76; evolución C1 0,54, C2 0,17, C3 0,71 | 13, §2.3; nb. 32 §3, `resultados-oe3-por-tipo.png` |
| 4 |  | D16: diferencia C2 − C1 en evolución −0,38, intervalo de 95 % de −0,61 a −0,14 | 13, §3; 12, §3.2 |
| 4 |  | Tipo «sin respuesta» excluido por la abstención | 13, §2.3 (nota bajo la tabla); nb. 32 §3 |
| 5 | 260 | Evolución 0,17 → 0,71 (C2 y C3 comparten el código de consulta) | 13, §1 y §4 punto 1 |
| 5 |  | 31 de cada 100 decisiones; precisión 0,149, recall 0,308, F1 0,201, τ = 0,70 | 13, §2 (OE2) y §2.2; nb. 32 §4, `resultados-oe2-embudo.png` |
| 5 |  | Relaciones: 11 de 111 de extremo a extremo, 11 de 24 con las dos decisiones halladas | 13, §2 (OE2) |
| 5 |  | Repeticiones estables; concordancia de la regla de alineamiento 0,825 frente al criterio 0,80 | 13, §2.2 |
| 5 |  | OE4: 21, 11 y 11 de 43 respuestas incorrectas en hechos puntuales (48,8 %, 25,6 %, 25,6 %); diseño de OpenKOS y modelo confundidos | 13, §2.4 y §4 punto 2; nb. 32 §5, `resultados-oe4-causas.png` |
| 6 | 142 | C3 0,80 y C1 0,72 en el total; evolución 0,71 y 0,54; lectura descriptiva sin contraste preregistrado; C3 no es un techo | 13, §2.3 y §4 puntos 3 y 4 |
| 6 |  | 15,3 s (C2) frente a 5,7 s (C1), 2,7 veces; construir la base toma horas; sin punto de equilibrio | 13, §5; nb. 32 §6, `resultados-costo-latencia.png` |
| 6 |  | Veredicto por objetivo (OE1 a OE4) | 13, «En una página» y §2 |
| 7 | 137 | Un modelo pequeño, una corrida formal, 99 preguntas, intervalos anchos; H4 no evaluable; juez más estricto con C0 | 13, §7 y §3 |
| 7 |  | Extractor elegido con series de desarrollo; Qwen3.8 27B con F1 bajo qwen3.6:27b y margen no cumplido en TS3009; no cambia la elección del extractor | nb. 15, última sección («Qwen3.8 27B en el *screen*») y ADR 0015 |
| 8 | 126 | Extractor más grande y H3; juez que pueda evaluar H4; ampliar la doble anotación; una persona en el circuito como hipótesis | 13, §6 y §8; §8.3 (juez para H4) |

Las fuentes se citan por número de avance (13 = `docs/avances/13-jss-conclusiones.md`, 12 = `12-jss-resultados-experimento-b.md`, 10 = `10-jss-confiabilidad-de-la-referencia.md`), sección y notebook (nb.).

## Plan de láminas

El mazo se construye después de este guion, a partir de esta tabla. Una idea por lámina, con la conclusión como título y el mínimo de texto; los gráficos parten de cero y se leen al tamaño de un video (clase 4 de AFG2).

| N.º | Título (conclusión) | Visual | Presenta | Tiempo |
|---|---|---|---|---|
| 1 | Ordenar las decisiones en una base parecía mejor que buscar en el texto | Texto grande: pregunta y adelanto de la respuesta | Jason | 0:00 – 0:45 |
| 2 | Cuatro condiciones, de menos a más ayuda | Tabla C0 a C3 | Jason | 0:45 – 1:20 |
| 3 | Cada objetivo se cierra con un resultado | Tira de cuatro casillas OE1 a OE4 (vacía) | Jason | 1:20 – 1:50 |
| 4 | Dos personas coinciden bien en qué es una relación | `resultados-oe1-kappa.png` | Germán | 1:50 – 2:45 |
| 5 | La base automática responde peor que buscar en el texto | `resultados-oe3-total.png` | Germán | 2:45 – 3:20 |
| 6 | La brecha crece en las preguntas de evolución | `resultados-oe3-por-tipo.png` | Germán | 3:20 – 4:05 |
| 7 | El criterio principal no se respalda, y la dirección es la contraria | Texto con el intervalo de D16 | Germán | 4:05 – 4:30 |
| 8 | La diferencia entre C3 y C2 mide lo que cuesta extraer automáticamente | Diagrama C2 y C3 con el mismo código de consulta | Gustavo | 4:30 – 5:00 |
| 9 | La máquina encuentra 3 de cada 10 decisiones | `resultados-oe2-embudo.png` | Gustavo | 5:00 – 5:40 |
| 10 | La mitad de los errores nace al extraer | `resultados-oe4-causas.png` | Gustavo | 5:40 – 6:15 |
| 11 | Con buenas decisiones, la base supera al texto, sobre todo en evolución | Dos pares de cifras (C3 y C1) | Jason | 6:15 – 6:45 |
| 12 | Cada consulta a la base cuesta 2,7 veces más tiempo que buscar en el texto | `resultados-costo-latencia.png` | Jason | 6:45 – 7:05 |
| 13 | Los cuatro objetivos tienen un resultado | Tira OE1 a OE4 completa | Jason | 7:05 – 7:20 |
| 14 | Las cifras describen este caso y no se generalizan | Lista de limitaciones | Jason | 7:20 – 8:10 |
| 15 | Tres pasos para AFG3: la extracción, el juez y la referencia | Tres casillas numeradas | Jason | 8:10 – 8:40 |
| 16 | La idea funciona cuando las decisiones son buenas; falla obtenerlas automáticamente | Texto: pregunta inicial y respuesta | Jason | 8:40 – 9:00 |
