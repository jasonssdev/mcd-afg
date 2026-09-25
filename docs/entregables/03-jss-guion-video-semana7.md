# Guion — Video de avance #3, semana 7

| | |
|---|---|
| **Entrega** | Video de avance #3: propuesta metodológica + descripción inicial de datos disponibles (semana 7, AFG1) |
| **Fecha de envío** | (por completar al subir el video) |
| **Versión** | 1.1 |
| **Construido desde** | `docs/avances/02-jss-fuente-de-datos.md` v1.1 · `docs/avances/06-jss-metodologia.md` v1.1 · `docs/avances/03-jss-objetivos.md` v2.0 |
| **Duración objetivo** | 5:00 (máximo permitido) |
| **Formato** | Tres presentadores, bloques consecutivos, en este orden: Jason, Germán, Gustavo |
| **Extensión hablada** | ≈ 690 palabras, a 140–150 palabras por minuto (≈ 4:35–4:55) |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial del guion. | Preparación del video de avance #3. |
| 1.1 | 2026-09-21 | Corrección de rutas en la tabla de evidencia (`docs/BACKLOG.md` → `docs/decisions/README.md`); la prosa no cambia. | Retiro de `docs/BACKLOG.md`: los enlaces quedaban muertos. |

## Qué pide el curso y dónde se cubre

| Requisito de la rúbrica | Bloque |
|---|---|
| Presentación de quien graba y del equipo | Jason, apertura |
| Objetivos de la semana | Jason |
| Pasos metodológicos y su justificación | Jason |
| Datos disponibles: origen, tipo, formato, cantidad, calidad | Germán |
| Cómo se abordaron los objetivos y qué tareas se hicieron | Germán y Gustavo |
| Mayores desafíos de la semana | Gustavo |
| Tareas de la próxima semana | Gustavo, cierre |

## Reparto de tiempos

| Bloque | Persona | Tiempo | Mensaje central |
|---|---|---|---|
| Apertura y metodología | Jason | 0:00 – 1:40 | Qué problema se resuelve, con qué pasos y por qué esos pasos |
| Datos | Germán | 1:40 – 3:15 | Qué datos hay, cuántos, en qué formato y qué calidad tienen |
| Desafíos y próximos pasos | Gustavo | 3:15 – 5:00 | Qué costó esta semana, qué sigue en la semana 8 y en AFG2 |

## Notas de grabación

- El texto está escrito para decirse, no para leerse. Frases cortas.
- Las palabras en **negrita** se apoyan con la voz.
- Cada bloque abre nombrando a quien habla y cierra pasando el turno.
- Las cifras se muestran en pantalla como apoyo; en cámara se dicen solo las que van en el texto.
- Apoyo visual sugerido por bloque: (1) tabla de las tres condiciones C1/C2/C3; (2) tabla de los cuatro N y el diagrama de la cadena de evidencia; (3) la tabla del plan por curso del README.

---

## Bloque 1 — Jason (0:00 – 1:40)

Hola. Soy **Jason Sepúlveda** y presento el video de avance de la semana 7 junto a **Germán Vega** y **Gustavo Martínez**.

Esta semana teníamos dos objetivos: cerrar la **propuesta metodológica** y describir los **datos**.

El problema, en una frase: las reuniones se transcriben, pero una decisión no queda como un dato recuperable, sino repartida entre varios turnos. Y cuando esa decisión **cambia** en una reunión posterior, ninguna transcripción registra la relación entre ambas.

La metodología convierte eso en una **comparación medible** entre tres condiciones. **C1**, la práctica actual: RAG directamente sobre las transcripciones. **C2**, nuestra propuesta: una base estructurada de decisiones construida automáticamente con un modelo de lenguaje local. **C3**: la misma base, construida desde **anotación humana**. Solo cambia la representación consultada; todo lo demás es igual.

Los pasos son cuatro. Uno: construir un **conjunto de referencia** de decisiones y sus relaciones entre reuniones, anotado por personas. Dos: medir la **extracción automática** contra esa referencia, con un protocolo de alineamiento fijado antes de ver resultados. Tres: evaluar las tres condiciones sobre un mismo **banco de preguntas**, que separa hechos puntuales de preguntas de evolución. Cuatro: **atribuir cada error** de C2 a su origen: extracción, recuperación o síntesis.

¿Por qué así? Porque separa tres cosas que la literatura confunde: el valor de la representación, el costo de los errores al construirla y el aporte de representar la evolución en el tiempo. Sin eso, un buen resultado no dice en qué conviene invertir.

Germán nos cuenta con qué datos hacemos esto.

## Bloque 2 — Germán (1:40 – 3:15)

Gracias, Jason. Soy **Germán Vega**.

**Origen.** Trabajamos con el **AMI Meeting Corpus**, de la Universidad de Edimburgo: cerca de cien horas de reuniones en inglés, con licencia **CC BY 4.0**.

**Tipo y formato.** No son solo transcripciones. El paquete de anotaciones trae varias **capas superpuestas** en XML: resúmenes con un encabezado de decisiones y enlaces de cada frase del resumen a los actos de diálogo que la respaldan. Eso da una **cadena de evidencia**: de cada decisión anotada se llega a las palabras exactas de la transcripción.

**Cantidad.** El corpus se organiza en **series de cuatro reuniones** del mismo equipo, y esa es nuestra unidad de muestreo: sin secuencia no hay evolución que medir. Tras auditar el paquete completo seleccionamos **14 series**, **56 reuniones**, balanceadas por sitio. Contienen **343 decisiones** anotadas y **3.071 pares posibles** entre reuniones. Un filtro léxico reduce esos pares a **92 candidatos** para anotación humana.

**Calidad.** Alta, pero no perfecta, y la medimos. El **92 por ciento** de las decisiones tiene evidencia identificable en la transcripción. Pero hay un caso en que el resumen oficial dice que se eliminó un botón y la transcripción muestra que se mantuvo. Por eso el protocolo obliga a contrastar contra la transcripción, nunca contra el resumen. Además separamos tres series de **desarrollo**, donde se ajustan parámetros, de once de **evaluación**, donde solo se reporta.

Gustavo cierra con los desafíos y lo que viene.

## Bloque 3 — Gustavo (3:15 – 5:00)

Gracias, Germán. Soy **Gustavo Martínez**.

El mayor desafío fue que **los datos cambiaron el plan**. La propuesta original se apoyaba en una capa de segmentación de decisiones que solo cubre seis series. Al medir el corpus completo, el resumen abstractivo cubría 33, y pasamos de 136 decisiones a las 343 que mencionó Germán.

El segundo fue un error propio. Una extrapolación hecha fuera del código estimó unos 170 pares candidatos; sobre las 14 series reales eran 712, y hubo que ajustar el filtro hasta los 92. La lección quedó como regla: **ninguna cifra se calcula fuera del paquete con tests**.

El tercero sigue abierto: cuántas relaciones reales entre reuniones existen. En una muestra pequeña de desarrollo, cerca de la mitad de los candidatos fueron relaciones verdaderas, pero el intervalo de confianza es amplio. Por eso la viabilidad del estrato de evolución la declaramos **plausible, no demostrada**.

La próxima semana es la entrega final del curso: cerramos los documentos de avance y la presentación. En paralelo empieza la **anotación humana**: Germán y yo anotamos de forma independiente y Jason adjudica los desacuerdos. Yo escribo el banco de preguntas y Germán lo valida.

Después: en AFG2 cerramos la anotación y corremos la extracción y la comparación de las tres condiciones; en AFG3 atribuimos los errores y escribimos las conclusiones.

Gracias por ver el video.

---

## Trazabilidad de las cifras dichas en cámara

| Cifra | Dónde se verifica |
|---|---|
| 14 series, 56 reuniones, 343 decisiones, 3.071 pares, 92 candidatos | `docs/avances/02-jss-fuente-de-datos.md` §4.4; `config/corpus.toml` `[oe1]` |
| 33 series / 649 vs 6 series / 136 (marco muestral) | `docs/avances/02-jss-fuente-de-datos.md` §4.1; `docs/decisions/README.md` D1 |
| 92,4 % de decisiones con evidencia | `docs/avances/02-jss-fuente-de-datos.md` §4.7; `notebooks/00-jss-corpus-y-auditoria.ipynb` |
| 170 → 712 → 92 (bloqueador) | `docs/decisions/README.md` D9 |
| Caso del botón turbo | `docs/anotacion/manual-anotacion-oe1.md` §3 |
| Viabilidad de E3: 45,5 % (5/11), IC 95 % [21,3 – 72,0 %] | `notebooks/01-jss-viabilidad-e3.ipynb` |
| 3 series de desarrollo / 11 de evaluación | `docs/decisions/0005-adr-development-evaluation-split.md` |
| Roles de anotación y banco de preguntas | `CONTRIBUTING.md` §1 |
| Plan por curso AFG1 / AFG2 / AFG3 | `README.md`, sección "Plan por curso"; `docs/avances/03-jss-objetivos.md` |
