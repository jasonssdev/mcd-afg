# Problema

| | |
|---|---|
| **Documento** | 01 — Problema |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.2 |
| **Fecha** | 2026-10-01 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial. Formulación del problema para AFG1. | Primera entrega del curso. |
| 1.1 | 2026-09-20 | Citas Hsueh & Moore 2007a/2007b; enlace a la propuesta renombrado. | Corrección bibliográfica y renombre de archivo. |
| 1.2 | 2026-10-01 | Reescritura completa de la redacción: el problema se cuenta desde un caso real del corpus, cada término técnico se explica al aparecer y se agrega un glosario breve. Las cifras, las referencias y la formulación del problema no cambian. | Retroalimentación de la revisión entre equipos de la semana 8: el problema y la metodología no se entendían, menos aún para una audiencia no técnica. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## Una historia que ocurre en cualquier organización

Un equipo de cuatro personas diseña un producto a lo largo de varias reuniones. En la
tercera deciden incluir cierta función. En la cuarta vuelven sobre el tema y la discuten de
nuevo. Meses después alguien pregunta: ¿qué decidimos al final sobre esa función, y por qué
cambiamos de idea?

Para responder hay que hacer tres cosas: encontrar el momento de la tercera reunión en que
se tomó la decisión, encontrar el momento de la cuarta en que se revisó, y darse cuenta de
que ambos momentos hablan de lo mismo. Nadie hace esto de forma sostenida. Lo habitual es
preguntarle a quien estuvo presente y confiar en su memoria, o leer el resumen de la última
reunión y dar por hecho que está bien.

Este caso no es hipotético. Proviene de los datos con los que trabaja este proyecto: el
corpus AMI, una colección pública de reuniones reales grabadas y transcritas, en las que
equipos de cuatro personas diseñan un control remoto a lo largo de cuatro reuniones. En una
de esas series, el resumen oficial de la cuarta reunión afirma que el equipo eliminó el
botón "turbo" del control remoto. Al leer la transcripción completa, el botón se mantuvo. El
registro que cualquiera habría consultado para saber qué se decidió estaba equivocado, y
nada en ese registro permitía notarlo.

## 1. Dónde se pierde una decisión

Las organizaciones pierden sus decisiones, y no por falta de registro: hoy casi toda
reunión se graba y se transcribe. Se pierden por tres razones que se suman.

**La decisión no está en un solo lugar.** Una transcripción es la conversación escrita tal
cual ocurrió, dividida en turnos de habla: cada vez que alguien toma la palabra es un turno.
Una decisión rara vez cabe en un turno. Alguien propone, otra persona objeta, una tercera
sugiere una variante y el acuerdo final se da por sobreentendido. La decisión existe, pero
está repartida entre varios turnos y ninguno de ellos la contiene completa.

**Nadie anuncia "esto es una decisión".** En la conversación real casi nunca aparece una
frase que marque el momento. Para un lector, y más aún para un programa, no hay una señal
clara que distinga el pasaje en que se decidió algo del pasaje en que solo se conversó.

**Cuando la decisión cambia, el cambio no queda en ningún lado.** Si en una reunión
posterior el equipo revisa lo acordado, la transcripción de esa reunión registra la nueva
conversación, pero no registra que esa conversación modifica una decisión anterior. El
hecho más importante, la relación entre las dos reuniones, no está escrito en ninguna de
las dos. Reconstruirlo exige leer todas las reuniones y recordar la primera al llegar a la
última.

## 2. Por qué no basta con buscar en las transcripciones

La respuesta más común hoy a "¿qué se decidió sobre X?" es una técnica llamada
**recuperación aumentada**, conocida por su sigla en inglés, RAG (Lewis et al., 2020). La
idea es simple: ante una pregunta, un sistema busca en los documentos los fragmentos que
más se parecen a la pregunta, y un modelo de lenguaje redacta una respuesta a partir de esos
fragmentos. Funciona como un buscador al que se le agrega un redactor. Y funciona bien
cuando la respuesta cabe en un pasaje.

El problema de este proyecto no cabe en un pasaje, y RAG tiene aquí tres límites que no se
arreglan buscando mejor.

- **No recuerda nada entre una pregunta y la siguiente.** Cada consulta empieza de cero.
  No hay un lugar donde quede guardado "esto se decidió en octubre y se revirtió en
  diciembre" para la próxima vez que alguien pregunte.
- **No ve la relación entre dos pasajes lejanos.** Que un fragmento de diciembre revierta
  uno de octubre no es una propiedad de ninguno de los dos fragmentos por separado: es una
  propiedad del par. RAG recupera fragmentos que se parecen a la pregunta, y dos pasajes
  que se contradicen no necesariamente se parecen entre sí.
- **Recupera fragmentos, no decisiones.** La unidad con la que trabaja es el trozo de texto,
  del tamaño que se haya elegido al partir los documentos. Una decisión repartida entre
  varios turnos puede quedar cortada en dos trozos, o mezclada con otra.

Estos límites no se corrigen partiendo los documentos de otra manera. Son consecuencia de
consultar el documento original en lugar de consultar algo construido a partir de él: una
base donde cada decisión sea una entrada propia, con su fecha, su evidencia y sus
relaciones con otras decisiones.

Esa alternativa, construir primero un índice estructurado y consultar después, ya se
explora. El caso más conocido es GraphRAG (Edge et al., 2024). Pero la evidencia disponible
compara sistemas completos entre sí: si el sistema con índice responde mejor, no se sabe
cuánto de la mejora viene de tener el índice y cuánto del modelo que lo construyó. Es como
comparar dos restaurantes sin saber si la diferencia está en la receta o en quien cocina.

## 3. Construir la base también tiene riesgos

Si la solución es construir una base de decisiones, alguien tiene que construirla. Hacerlo
con un modelo de lenguaje tiene un riesgo que RAG no tiene. En RAG, un error en la
respuesta dura lo que dura esa respuesta; la próxima pregunta vuelve a leer los documentos
originales. En una base construida, un error de extracción se escribe una vez y se lee
todas las veces que alguien consulte. Si nadie lo corrige, con el tiempo deja de parecer un
error y pasa a ser la premisa de decisiones nuevas.

Y hay un segundo riesgo, anterior al modelo: ni siquiera las personas coinciden en qué es
una decisión. Hsueh y Moore (2007a) marcaron, sobre las reuniones del corpus AMI, qué partes
de la conversación tenían que ver con decisiones: apenas el **1,4 %** de los actos de
diálogo. Fernández et al. (2008) hicieron lo mismo sobre las mismas reuniones con un
criterio propio. Al comparar ambos resultados sobre datos idénticos, el acuerdo entre los
dos equipos fue **peor que el azar**: un kappa negativo, con solo un **12,22 %** de
solapamiento entre lo que uno y otro marcaron. Kappa es una medida de acuerdo que descuenta
las coincidencias que se darían por casualidad; cero es lo que se esperaría eligiendo al
azar, y un valor negativo significa que coincidieron menos que eso. Dos equipos competentes,
el mismo material, y no se pusieron de acuerdo en qué era una decisión.

Si las personas no coinciden, una etiqueta no puede darse por buena solo porque la escribió
una persona. Y si la base la construye un modelo, tampoco puede darse por buena solo porque
la escribió el modelo. Hace falta medir.

## 4. Nadie ha construido el mapa

Para medir hace falta una referencia: un conjunto de reuniones donde ya se sepa, con
certeza, qué decisiones hay y cuáles revisan a cuáles. Ese conjunto no existe.

El corpus AMI es el más completo en este terreno. Además de las grabaciones y las
transcripciones, incluye capas de anotación hechas a mano: marcas que indican, por ejemplo,
qué pasajes son decisiones y qué dice el resumen de cada reunión. En su diseño existe
incluso una capa llamada `decisionlink`, pensada para enlazar decisiones. Se verificó
directamente contra la documentación del corpus qué contiene esa capa, y el resultado es
revelador en tres puntos:

1. Enlaza una decisión con una oración del resumen de la misma reunión, no con otra
   decisión.
2. Trabaja reunión por reunión, por construcción. No puede expresar que una decisión de la
   cuarta reunión modifica una de la tercera.
3. No distribuye ningún dato. Los archivos de decisiones del corpus son **47**, contienen
   **288** decisiones marcadas, y hay **cero** enlaces entre ellas.

AMI diseñó el espacio para este enlace y lo dejó vacío. Ninguna capa de anotación publicada
conecta una decisión con su revisión en una reunión posterior de la misma serie.

## 5. El problema, en una frase

> Falta una medición controlada que separe el valor de mantener una representación
> persistente y estructurada de decisiones, el costo de los errores de su extracción
> automática, y la contribución específica de representar la evolución de una decisión a
> través de una serie de reuniones — frente a consultar directamente las transcripciones con
> RAG.

Dicho de otro modo: se quiere medir, con todo lo demás igual, tres cosas que hoy están
mezcladas. Cuánto ayuda tener una base de decisiones en lugar de buscar en las
transcripciones. Cuánto cuesta que esa base la construya una máquina y se equivoque. Y
cuánto aporta, dentro de esa base, registrar que una decisión cambió con el tiempo.

## Glosario breve

| Término | Qué significa en este documento |
|---|---|
| Transcripción | La conversación de una reunión pasada a texto, tal como se dijo. |
| Turno de habla | Cada intervención de una persona en la conversación. Una decisión suele repartirse entre varios. |
| Corpus AMI | Colección pública de reuniones reales grabadas, transcritas y anotadas a mano. Cerca de dos tercios corresponden a equipos que diseñan un control remoto en series de cuatro reuniones. |
| Anotación | Marcar a mano, sobre la transcripción, qué pasajes son decisiones y cómo se relacionan. Es el trabajo humano que produce la referencia contra la que se mide todo lo demás. |
| RAG | Recuperación aumentada: buscar los fragmentos de texto más parecidos a una pregunta y redactar una respuesta con ellos. |
| Kappa | Medida de acuerdo entre dos personas que descuenta las coincidencias por azar. Cero equivale a elegir al azar; negativo, a coincidir menos que eso. |

## Cambios respecto de la propuesta original

La propuesta ya señalaba este vacío (§1.6). Lo que se agrega aquí es la verificación directa
sobre la documentación del corpus —conteo de archivos y elementos de `decisionlink`—, que
antes era una lectura de la guía de anotación y ahora es evidencia contrastada. La versión
1.2 cambia la forma de contarlo, no el contenido: las cifras, las referencias y la
formulación del problema son las mismas de la versión 1.1.

## Referencias

Fernández, R., Frampton, M., Ehlen, P., Purver, M., & Peters, S. (2008). Modelling and
detecting decisions in multi-party dialogue. En *Proceedings of the 9th SIGdial Workshop on
Discourse and Dialogue* (pp. 156–163). Association for Computational Linguistics.

Hsueh, P.-Y., & Moore, J. D. (2007a). What decisions have you made? Automatic decision
detection in meeting conversations. En *Proceedings of NAACL-HLT 2007* (pp. 25–32).
Association for Computational Linguistics.

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis,
M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation
for knowledge-intensive NLP tasks. En *Advances in Neural Information Processing Systems 33*
(pp. 9459–9474).

Edge, D., Trinh, H., Cheng, N., Bradley, J., Chao, A., Mody, A., Truitt, S., Metropolitansky,
D., Ness, R. O., & Larson, J. (2024). *From local to global: A graph RAG approach to
query-focused summarization* (arXiv:2404.16130) [Preprint, sin revisión por pares].

---

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| El botón turbo: el resumen de IS1004d afirma una eliminación que la transcripción contradice | [`02-jss-fuente-de-datos.md`](02-jss-fuente-de-datos.md) §5; [`../anotacion/manual-anotacion-oe1.md`](../anotacion/manual-anotacion-oe1.md) §3; [`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb) |
| Estructura del corpus: series de cuatro reuniones, escenario del control remoto | [`02-jss-fuente-de-datos.md`](02-jss-fuente-de-datos.md) §1 y §2 |
| Hsueh & Moore, 1,4 % de actos anotados como decisión | [`../propuesta.md`](../propuesta.md) §1.4; `bibliography/refs.bib` `hsueh2007whatdecisions` |
| Fernández et al., kappa negativo y 12,22 % de solapamiento | [`../propuesta.md`](../propuesta.md) §1.4; `bibliography/refs.bib` `fernandez2008modelling` |
| `decisionlink`: 47 archivos, 288 elementos, cero punteros a resúmenes | Documentación de `ami_public_manual_1.6.2` (`corpusdoc/annot_decisionlink.html`, `AMI-metadata.xml`, `resource.xml`) y conteo directo sobre `decision/manual/`, verificado el 2026-09-20 |
| Formulación del problema | [`../propuesta.md`](../propuesta.md) §1.5 (reformulada) |
