# Guion — Presentación final, semana 8

| | |
|---|---|
| **Entrega** | Presentación final de AFG1 (semana 8) |
| **Fecha de envío** | (por completar al subir el video) |
| **Versión** | 1.0 |
| **Construido desde** | `docs/avances/01-jss-problema.md` v1.1 · `docs/avances/04-jss-bibliografia.md` v1.1 · `docs/avances/06-jss-metodologia.md` v1.2 · `docs/avances/05-jss-aspectos-eticos.md` v1.2 · `docs/avances/03-jss-objetivos.md` v2.1 |
| **Duración objetivo** | 9:15 (máximo permitido: 10:00) |
| **Formato** | Tres presentadores en cuatro bloques consecutivos, en este orden: Jason, Germán, Gustavo, Jason |
| **Extensión hablada** | 1.342 palabras: 265 + 315 + 347 + 415. A 145 palabras por minuto son 9:15; a 140, 9:35 |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-22 | Versión inicial del guion. | Preparación de la presentación final. |

## Qué pide el curso y dónde se cubre

| Requisito de la rúbrica | Bloque |
|---|---|
| Contextualización y presentación del problema | Bloque 1 — Jason |
| Trabajos relacionados (al menos 2, indicando cómo se relacionan) | Bloque 2 — Germán |
| Propuesta metodológica (metodología, fases, aporte de cada fase) | Bloque 3 — Gustavo |
| Alcances éticos (problemáticas, riesgos, stakeholders) | Bloque 4 — Jason |
| Calidad de la presentación (video, audio, material de apoyo) | Notas de grabación, todos los bloques |

## Reparto de tiempos

| Bloque | Persona | Tiempo | Mensaje central |
|---|---|---|---|
| Contextualización y problema | Jason Sepúlveda | 0:00 – 1:55 | El fenómeno, por qué RAG no basta y el vacío verificado en AMI |
| Trabajos relacionados | Germán Vega | 1:55 – 4:10 | Tres antecedentes, con un ejemplo y el "por qué importa" de cada uno |
| Propuesta metodológica | Gustavo Martínez | 4:10 – 6:35 | Diseño de tres condiciones, las cuatro fases y el aporte de cada una |
| Alcances éticos y cierre | Jason Sepúlveda | 6:35 – 8:55 | Tres principios, cada uno con un caso concreto, y las partes involucradas |

## Notas de grabación

- El texto está escrito para decirse, no para leerse. Frases cortas.
- Las palabras en **negrita** se apoyan con la voz.
- Cada bloque abre nombrando a quien habla y cierra pasando el turno; el bloque 4 cierra el video.
- Las cifras se muestran en pantalla como apoyo; en cámara se dicen solo las que van en el texto.
- **El margen sobre el tope de 10:00 es de 25 a 45 segundos.** Conviene cronometrar un ensayo completo antes de grabar. Si se pasa, los tres recortes previstos —en este orden— son: en el bloque 3, la oración subordinada "con el protocolo de alineamiento fijado antes de ver resultados"; en el bloque 4, la última oración del principio de justicia, sobre el eje de hablante nativo o no nativo; y en el bloque 4, la enumeración de partes involucradas, que se reduce a nombrarlas sin explicarlas. Los tres juntos liberan cerca de 35 segundos sin tocar ningún requisito de la rúbrica.
- **No recortar los ejemplos concretos.** El botón del control remoto (bloque 4), el caso del diseñador industrial que desaparece del registro (bloque 4) y el "por qué importa" de cada antecedente (bloque 2) son lo que hace entendibles esos bloques; sin ellos quedan abstractos.
- Si en la ronda de preguntas se cita Edge et al. (2024), debe declararse en voz alta como **preprint sin revisión por pares**, conforme a la convención de `docs/avances/04-jss-bibliografia.md`.
- Apoyo visual sugerido por bloque: (1) diagrama de una decisión repartida entre turnos de habla, y del vacío de `decisionlink` en AMI (47 archivos, 288 elementos, cero punteros); (2) tabla de los tres trabajos relacionados con su vínculo explícito; (3) tabla de las tres condiciones C1/C2/C3 y diagrama de las cuatro fases con su aporte; (4) tabla de los tres principios éticos y la lista de partes involucradas.

---

## Bloque 1 — Jason Sepúlveda (0:00 – 1:55)

Hola. Soy **Jason Sepúlveda**. Junto a **Germán Vega** y **Gustavo Martínez** presentamos el trabajo final de nuestro primer curso del proyecto de grado.

El fenómeno: las organizaciones pierden sus decisiones. No por falta de registro —hoy casi toda reunión se transcribe— sino porque una decisión no queda como una entidad recuperable, sino como un pasaje difuso repartido entre varios turnos de habla, casi nunca con un marcador explícito. Y se agrava cuando esa decisión cambia en una reunión posterior: ningún registro individual contiene el hecho más importante, que es la relación entre ambas.

¿Por qué la recuperación aumentada, RAG, no basta? No mantiene estado entre consultas; no representa la relación entre pasajes distantes —que un fragmento de diciembre revierta uno de octubre no es propiedad de ninguno de los dos, sino del par—; y su unidad de recuperación es el fragmento, no la decisión. No son defectos de *chunking*: son consecuencia de consultar el documento original en vez de una representación construida.

Y el vacío es real, verificado. Ninguna capa de anotación publicada enlaza una decisión con su revisión posterior. Lo contrastamos contra la documentación de AMI: la capa `decisionlink` existe en el diseño, pero enlaza una decisión con una oración del resumen, no con otra decisión, y no distribuye ningún dato — **47 archivos, 288 elementos, cero punteros**. AMI diseñó el espacio para ese enlace y lo dejó vacío.

De ahí el problema: falta una medición controlada que separe tres cosas — el valor de la representación, el costo de los errores al construirla, y el aporte de representar la evolución.

Germán presenta los trabajos relacionados.

## Bloque 2 — Germán Vega (1:55 – 4:10)

Gracias, Jason. Soy **Germán Vega**. Tres antecedentes: qué hizo cada uno y qué le falta.

**Hsueh y Moore (2007a) y Fernández et al. (2008)** anotaron decisiones sobre las mismas reuniones de AMI. Los primeros marcaron como relacionados con decisiones apenas el **1,4 %** de los actos de diálogo. Fernández et al. construyeron un esquema independiente y, comparando ambos conjuntos sobre datos idénticos, reportan **kappa negativo y 12,22 % de solapamiento**. En concreto: dos equipos expertos leyeron el mismo pasaje, uno dijo "esto es una decisión" y el otro dijo que no, con un desacuerdo peor que responder al azar. Por qué importa: si los expertos no coinciden, no podemos dar por buenas nuestras etiquetas solo porque las escribió una persona. Por eso el **36,4 %** de las series de evaluación se anota dos veces de forma independiente y se adjudica cada desacuerdo.

**Edge et al. (2024), GraphRAG**, propone la misma idea general que nosotros: construir un índice estructurado antes de consultar. Es la familia de soluciones más cercana. Su límite es que compara sistemas completos entre sí: si GraphRAG responde mejor que RAG, esa comparación no dice si la mejora vino de tener un grafo o del modelo que lo construyó. Por qué importa: esa es la ambigüedad que resuelve nuestro diseño, porque añade una condición donde la misma base la construye una persona y no un modelo.

**Murray et al. (2009)**, la tarea de auditoría de decisiones, es el antecedente más cercano sobre AMI: pusieron a cincuenta personas a reconstruir la historia de una decisión leyendo una serie completa. Confirma que la tarea es real y difícil. Su límite: el resultado fue un protocolo de evaluación humana, no datos. Nadie publicó el enlace entre reuniones como algo que una máquina pueda leer. Por qué importa: sin ese enlace no hay contra qué medir la extracción automática, y construirlo es nuestro primer objetivo.

Gustavo presenta la propuesta metodológica.

## Bloque 3 — Gustavo Martínez (4:10 – 6:35)

Gracias, Germán. Soy **Gustavo Martínez**.

El diseño central son **tres condiciones** con todo lo demás igual —mismo modelo, mismo hardware, mismo presupuesto de contexto—, porque sin esa restricción cualquier diferencia es inatribuible. **C1** es la práctica actual: RAG sobre las transcripciones, ajustado sobre desarrollo para que sea una línea base honesta. **C2** es nuestra propuesta: una base estructurada de decisiones construida automáticamente con un modelo local. **C3** es esa misma base, construida desde anotación humana.

Cuatro fases, y cada una aporta algo distinto.

**Fase 1, el conjunto de referencia.** Anotación humana de las decisiones y de su relación entre reuniones, con etiquetas cerradas y evidencia obligatoria. Aporta el patrón de comparación sin el cual ninguna otra fase mide nada. Las etiquetas las pone siempre una persona: si las produjera un modelo, C3 tendría errores por construcción y la brecha entre C2 y C3 no mediría nada.

**Fase 2, la extracción automática.** Mide precisión, cobertura y F1 contra esa referencia, con el protocolo de alineamiento fijado antes de ver resultados. Aporta el costo de construir la representación automáticamente.

**Fase 3, la utilidad funcional.** Las tres condiciones responden el mismo banco de preguntas, que separa hechos puntuales de preguntas de evolución. Aporta el valor de la representación.

**Fase 4, la atribución de error.** Para cada respuesta fallida de C2 determina si el hecho correcto estaba en la base —si no, error de extracción—, si fue recuperado —si no, error de recuperación— y, si lo fue, error de síntesis. Aporta en qué conviene invertir.

Los datos: el AMI Meeting Corpus, licencia CC BY 4.0. Seleccionamos **14 series** de cuatro reuniones del mismo equipo —**56 reuniones**— con **343 decisiones** y **3.071 pares posibles**, que un filtro léxico reduce a **92 candidatos** para anotación humana.

Y una honestidad sobre el estado: la viabilidad del estrato de evolución es **plausible, no demostrada**. Adjudicando a mano los candidatos de desarrollo, la tasa de positivos fue **45,5 %**, con intervalo de confianza del 95 % entre **21,3 % y 72,0 %**. El valor central alcanza el mínimo del estrato; la cota inferior, no.

Jason cierra con los alcances éticos.

## Bloque 4 — Jason Sepúlveda (6:35 – 8:55)

Gracias, Gustavo. Cerramos con los alcances éticos.

El marco es el **NIST AI Risk Management Framework 1.0** (Tabassi, 2023). Tratamos tres principios a fondo en vez de enumerar diez, con una regla: un principio que no se traduce en una cifra que reportamos es una buena intención, no un compromiso.

**Transparencia.** Toda decisión extraída debe mostrar el fragmento de transcripción que la respalda, y una respuesta sin fuente cuenta como falla aunque sea correcta. Un caso real de nuestros datos explica por qué: el resumen oficial de una reunión de AMI afirma que el equipo eliminó un botón del control remoto; fuimos a la transcripción y el botón se mantuvo. Un sistema que copiara ese resumen respondería con seguridad algo falso, y sin la evidencia al lado nadie podría notarlo.

**Justicia y equidad.** En estas reuniones quien dirige el proyecto concentra el **47,0 %** de los actos de decisión. Eso viene del material, no del sistema. El riesgo es amplificarlo: si se pregunta qué decidió el equipo sobre el material de la carcasa y solo se recupera lo que dijo quien preside, el diseñador industrial que propuso la idea desaparece del registro. Por eso no reportamos si el sistema lo recupera bien, sino si lo favorece **más de lo que ya lo favorece la fuente**. El eje de hablante nativo o no nativo queda como limitación declarada: la lengua materna está confundida con el lugar de grabación y aquí no se pueden separar.

**Responsabilidad.** Un error en una base persistente se escribe una vez y se lee muchas veces. Si la base registra mal una decisión y nadie la corrige, meses después deja de parecer un error y pasa a ser la premisa de una decisión nueva. No lo dejamos como advertencia: la fase 4 mide qué proporción de las respuestas equivocadas viene de errores grabados en la base.

**Partes involucradas**: los participantes del corpus, con identificadores anonimizados; quienes anotan; quienes revisan el proyecto de grado; y las organizaciones que adoptarían un sistema así.

Una precisión sobre privacidad: el corpus es público y no procesamos datos personales sensibles. Lo relevante no son estos datos, sino el despliegue. Ninguna organización adoptará una memoria de decisiones si eso implica enviar sus deliberaciones internas a un tercero. Por eso la ejecución local es un requisito de diseño, no una preferencia técnica.

Lo que sigue: cerrar la anotación y correr las tres condiciones en el segundo curso; atribuir los errores y concluir en el tercero.

Gracias por ver el video.

---

## Después de grabar

- Sube el video **una sola persona** del equipo.
- El enlace no debe tener restricciones de acceso ("cualquiera con el enlace puede ver").
- Publicar **una única entrada** en el foro de revisión entre equipos con el enlace.
- Revisar al equipo asignado: comentarios cualitativos como respuesta a su publicación en el foro. **No es voluntario.**
- Llenar el formulario con la evaluación cuantitativa.
- Registrar aquí la fecha exacta de envío.

## Trazabilidad de las cifras dichas en cámara

| Cifra | Dónde se verifica |
|---|---|
| 47 archivos, 288 elementos, cero punteros de `decisionlink` | `docs/avances/01-jss-problema.md` §4 |
| 1,4 % de actos de diálogo | Hsueh y Moore (2007a); `docs/avances/01-jss-problema.md` §3 |
| Kappa negativo y 12,22 % de solapamiento | Fernández et al. (2008); `docs/avances/01-jss-problema.md` §3 |
| 14 series / 56 reuniones / 343 decisiones / 3.071 pares / 92 candidatos | `docs/avances/02-jss-fuente-de-datos.md` §4.4; `config/corpus.toml` `[oe1]` |
| 36,4 % de las series de evaluación con doble anotación | `docs/avances/06-jss-metodologia.md` §5–6; `docs/decisions/0005-adr-development-evaluation-split.md` |
| 47,0 % de los actos de decisión en quien dirige el proyecto | `docs/avances/02-jss-fuente-de-datos.md` §4.6; `notebooks/00-jss-corpus-y-auditoria.ipynb` |
| El botón del control remoto: el resumen afirma una eliminación que la transcripción contradice | `docs/avances/02-jss-fuente-de-datos.md` §4.4; `docs/anotacion/manual-anotacion-oe1.md` §3 |
| 45,5 % de positivos, IC 95 % [21,3 % – 72,0 %] | `notebooks/01-jss-viabilidad-e3.ipynb` |
| CC BY 4.0 | `config/corpus.toml` |
| NIST AI RMF 1.0 (Tabassi, 2023) | `bibliography/refs.bib` `tabassi2023airmf` |
| Anidamiento lengua/sitio | `docs/decisions/README.md`, decisión D7 |
