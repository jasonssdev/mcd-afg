# Problema

| | |
|---|---|
| **Documento** | 01 — Problema |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.1 |
| **Fecha** | 2026-09-20 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial. Formulación del problema para AFG1. | Primera entrega del curso. |
| 1.1 | 2026-09-20 | Citas Hsueh & Moore 2007a/2007b; enlace a la propuesta renombrado. | Corrección bibliográfica y renombre de archivo. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## 1. El fenómeno

Las organizaciones pierden sus decisiones. No porque no queden registradas —hoy casi toda
reunión se transcribe— sino porque quedan como texto conversacional no estructurado: una
decisión no es una entidad recuperable, sino un pasaje difuso repartido entre varios turnos
de habla, casi nunca con un marcador lingüístico explícito. El problema se agrava cuando la
decisión cambia: un equipo la revisa en una reunión posterior, y ningún registro individual
contiene el hecho más importante, que es la relación entre ambas. Reconstruir esa trayectoria
exige leer todas las reuniones y recordar la primera al llegar a la última — exactamente lo
que ninguna organización hace de forma sostenida.

## 2. Por qué la recuperación aumentada (RAG) no basta

RAG (Lewis et al., 2020) recupera fragmentos relevantes ante una pregunta y sintetiza una
respuesta. Funciona cuando la respuesta cabe en un pasaje, pero tiene tres límites
estructurales aquí: no mantiene estado entre consultas; no representa la relación entre
pasajes distantes —que un fragmento de diciembre revierta uno de octubre no es propiedad de
ninguno de los dos, sino del par, y la similitud semántica no la captura—; y su unidad de
recuperación es el fragmento, no la decisión. No son defectos corregibles con mejor
*chunking*: son consecuencia de consultar el documento original en vez de una representación
construida. La alternativa de construir un índice estructurado antes de consultar se explora
activamente (notablemente GraphRAG; Edge et al., 2024), pero la evidencia disponible compara
sistemas completos entre sí, no aísla qué parte de la diferencia proviene de la
representación y qué parte del proceso que la construye.

## 3. Un objeto de anotación inestable, y un riesgo simétrico

Compilar decisiones con modelos de lenguaje introduce además un riesgo que RAG no tiene: un
error de extracción se escribe y se lee muchas veces, mientras que un error de síntesis en
RAG es efímero. Y el objeto mismo es inestable: Hsueh y Moore (2007a) anotaron sólo el 1,4 %
de los actos de diálogo de AMI como relacionados con decisiones; Fernández et al. (2008)
desarrollaron un esquema independiente sobre las mismas reuniones y, al comparar ambos
conjuntos sobre datos idénticos, reportan **kappa negativo y 12,22 % de solapamiento**. Dos
equipos competentes, el mismo corpus, desacuerdo peor que el azar.

## 4. El vacío específico

Ninguna capa de anotación publicada enlaza una decisión con su revisión en una reunión
posterior de la misma serie. Verificamos esto directamente contra la documentación del corpus
AMI: la capa `decisionlink` existe en el diseño —enlaza un `decision` con una `sentence` del
resumen, no con otra decisión—, es intra-reunión ("one file per observation") y **no
distribuye ningún dato**: 47 archivos `.decision.xml`, 288 elementos `<decision>`, cero
punteros a resúmenes. AMI diseñó el espacio para este enlace y lo dejó vacío.

## 5. Formulación del problema

> Falta una medición controlada que separe el valor de mantener una representación
> persistente y estructurada de decisiones, el costo de los errores de su extracción
> automática, y la contribución específica de representar la evolución de una decisión a
> través de una serie de reuniones — frente a consultar directamente las transcripciones con
> RAG.

## Cambios respecto de la propuesta original

La propuesta ya señalaba este vacío (§1.6). Lo que agrego aquí es la verificación directa
sobre la documentación del corpus —conteo de archivos y elementos de `decisionlink`—, que
antes era una lectura de la guía de anotación y ahora es evidencia contrastada.

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
| Hsueh & Moore, 1,4 % de actos anotados como decisión | [`../propuesta.md`](../propuesta.md) §1.4; `bibliography/refs.bib` `hsueh2007whatdecisions` |
| Fernández et al., kappa negativo y 12,22 % de solapamiento | [`../propuesta.md`](../propuesta.md) §1.4; `bibliography/refs.bib` `fernandez2008modelling` |
| `decisionlink`: 47 archivos, 288 elementos, cero punteros a resúmenes | Documentación de `ami_public_manual_1.6.2` (`corpusdoc/annot_decisionlink.html`, `AMI-metadata.xml`, `resource.xml`) y conteo directo sobre `decision/manual/`, verificado el 2026-09-20 |
| Formulación del problema | [`../propuesta.md`](../propuesta.md) §1.5 (reformulada) |
