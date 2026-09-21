# Metodología

| | |
|---|---|
| **Documento** | 06 — Metodología |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.2 |
| **Fecha** | 2026-09-20 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial. Metodología (8 pasos) para AFG1. | Primera entrega del curso. |
| 1.1 | 2026-09-20 | Redacción en voz de equipo; referencia a CONTRIBUTING | Consistencia de voz y de convenciones citadas |
| 1.2 | 2026-09-20 | Umbrales operativos provisionales en el paso 1 | Revisión final de AFG1: el paso 1 debe ser cuantitativo |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

Se sigue el esqueleto de 8 pasos del curso. Cada paso está lleno con el diseño real del
proyecto, no con una descripción genérica.

## 1. Problema y métricas

**Unidad de análisis:** la decisión individual y el par de decisiones dentro de una serie.
Una decisión es un compromiso sobre una acción o propiedad del producto que es explícita
(al menos un acto de diálogo la formula o ratifica), aceptada (no queda como propuesta
abierta) y anclada (identifica objeto y contenido). Las propuestas no aceptadas se registran
como no-decisiones: se necesitan para medir falsos positivos.

**Métricas de OE2:** precisión, cobertura y F1 a nivel decisión; exactitud de tipo y de
dirección a nivel relación temporal, reportadas por separado. **Métricas de OE3:** corrección
de respuesta, soporte de evidencia, citación correcta, corrección del rechazo, y costo
amortizado (§7).

**Umbrales operativos provisionales.** Se fijan ahora para que el paso 1 sea cuantitativo;
se revisan en AFG2 con los primeros datos y cualquier cambio se registra en
`docs/decisions/`.

| Qué | Umbral | Qué pasa si no se cumple |
|---|---|---|
| Concordancia del alineamiento automático con el emparejamiento manual (100 pares) | ≥ 0,80 | Se revisa la grilla de τ y se repite la validación |
| Concordancia juez automático – humano (20 % de las respuestas) | kappa ≥ 0,70 | Se descarta el juicio automático y se reporta solo la evaluación humana |
| Tamaño del estrato E3 | ≥ 25 preguntas | E3 se reformula como análisis de casos con reporte cualitativo |
| Diferencia entre condiciones | Intervalos bootstrap del 95 % que no se solapan | No se afirma diferencia; se reporta como no concluyente |
| Kappa de la anotación (existencia, tipo, dirección) | Sin umbral de aceptación, por diseño | Se reporta tal como salga; un kappa bajo es un hallazgo (documento 01, §1.4) |

**Horizonte para evitar fuga.** La anotación de relaciones temporales se hace en orden
cronológico dentro de cada serie, sin acceso a reuniones posteriores al momento de anotar
cada decisión. La extracción automática procesa las reuniones en orden y no puede consultar
reuniones futuras. La cronología está verificada empíricamente vía `startTime` en
`meetings.xml` (IS1004: 11:03 → 12:03 → 14:13 → 15:34 el mismo día), no asumida.

## 2. Auditoría de datos

Resumida aquí; el detalle completo —marco muestral, selección de 14 series, split
desarrollo/evaluación, los cuatro N, composición lingüística, autoría por rol, anclaje a
evidencia, riesgos y plan de saneamiento— está en
[`02-jss-fuente-de-datos.md`](02-jss-fuente-de-datos.md). El resultado que condiciona todo lo
que sigue: 14 series, 56 reuniones, 343 decisiones, 3.071 pares entre reuniones, 92 pares
candidatos tras el bloqueo.

## 3–4. Diseño analítico y líneas base

**Tres condiciones**, mismo modelo generativo, mismo modelo de *embeddings*, mismo hardware y
mismo presupuesto de contexto — sin esta restricción, cualquier diferencia observada es
inatribuible:

- **C1 — RAG documental.** Transcripciones segmentadas e indexadas con búsqueda híbrida
  (léxica + densa). **Línea base honesta:** parámetros de segmentación y número de
  fragmentos recuperados se ajustan sobre el conjunto de desarrollo (77 decisiones, 11
  candidatos), no se fijan arbitrariamente. Una línea base debilitada invalida el experimento
  completo.
- **C2 — Compilación automática.** Extracción con modelo local, persistencia con
  procedencia, consulta sobre los objetos compilados.
- **C3 — Compilación desde la referencia.** Idéntica a C2 salvo que los objetos provienen de
  la anotación humana de OE1.

**El bloqueador de candidatos** —que decide qué pares de decisiones se ofrecen a anotación
humana— se ajusta también sobre desarrollo, y es un ejemplo del mismo principio aplicado a
una etapa previa: exige coeficiente de solapamiento ≥ 0,30 **y** al menos 2 tokens
compartidos. Se usa solapamiento y no Jaccard porque Jaccard pierde el caso de regresión del
bloqueador —el par del botón turbo, Jaccard 0,118 frente a solapamiento 0,400—, que es el par
de solape léxico más exigente medido en el piloto y **no** una relación confirmada: la
verificación contra transcripción mostró después que esa reversión no ocurrió (documento 02,
§4.4); y se exige el mínimo absoluto de tokens porque el coeficiente solo, sobre las 14
series reales, seleccionaba 712 de 3.071 pares (23,2 %, ≈18 h de anotación) en vez del 5,5 %
que sugería el piloto — con el mínimo añadido, 92 (3,0 %, ≈2,3 h), sin perder el caso de
prueba.

## 5–6. Modelado y validación

**Modelos.** Modelos generativos de ejecución local (familia Qwen o equivalente, en escalas
contrastables) y un modelo de *embeddings* multilingüe. Versiones exactas, semilla, tamaño de
ventana de contexto y parámetros de muestreo se fijan y se publican.

**Varianza no determinista.** La extracción con LLM no es determinista aun con temperatura
baja. Cada configuración se ejecuta un **mínimo de tres veces**, reportando media y
dispersión, no una corrida única.

**Protocolo de alineamiento.** Determina si una decisión extraída corresponde a una de
referencia: (1) candidatos por similitud coseno de *embeddings* sobre el par (objeto,
contenido) por encima de un umbral τ; (2) emparejamiento uno-a-uno por asignación de costo
máximo —algoritmo húngaro—, no por vecino más cercano codicioso; (3) validación contra
emparejamiento manual sobre al menos 100 pares, con concordancia reportada; (4) todos los F1
se reportan como **curva sobre τ**, no en un único punto. Se descartan PR-AUC y matrices de
confusión como métricas principales porque el sistema emite conjuntos en lenguaje natural, no
puntajes sobre clases fijas; Recall@K se conserva sólo para la etapa de recuperación dentro
de C1 y C2.

**El filtro de candidatos y su punto de operación** es el mismo bloqueador de §3–4, aplicado
antes de la anotación humana: 92 pares candidatos de 3.071 posibles, versionado
(`BLOCKER_VERSION`) para que cambiar el punto de operación invalide explícitamente los
candidatos ya generados en vez de mezclarlos en silencio.

**Anotación humana, por qué no se automatiza.** Las etiquetas del conjunto de referencia las
pone siempre un humano. Si un modelo las produjera, la condición C3 tendría errores de
extracción por construcción y la brecha C2 − C3 —que es todo OE4— dejaría de medir nada. Los
modelos sólo proponen candidatos, resuelven evidencia y calculan acuerdo.

**Kappa por existencia, tipo y dirección**, nunca combinado, sobre el 36,4 % de la
evaluación (control de doble anotación: ES2008, ES2016, IS1003, TS3005), con adjudicación
documentada para todo desacuerdo.

## 7–8. Análisis de errores y operación

**Atribución determinista de error (OE4).** Para cada respuesta fallida de C2: se verifica
primero si el hecho correcto existe en la base compilada (si no, es error de **extracción**);
si existe, si fue recuperado (si no, es error de **recuperación**); si fue recuperado, es
error de **síntesis**.

**Modos de falla documentados hasta ahora.** El piloto identificó seis relaciones "a ojo",
sin trazar transcripción; al contrastarlas, sólo **3 de 6 (50 %) se confirmaron**. Un caso —el
supuesto reemplazo del botón turbo por eliminación, IS1004c → IS1004d— resultó **falso**: el
resumen abstractivo de AMI afirma una eliminación que la transcripción contradice. La señal
`evidencia = 0 actos` predijo el error antes de leer la transcripción, lo que respalda exigir
evidencia obligatoria como parte de la definición de decisión (§1).

**Punto de equilibrio amortizado**, la métrica operativa que reemplaza a la latencia aislada:

> `costo_compilación + n · costo_consulta_estructurada  <  n · costo_consulta_RAG`

**Qué significaría operar esto en una organización real.** El experimento completo depende
de que exista suficiente material de evolución entre reuniones para sostener el estrato E3 del
banco de preguntas. Esto es **provisional**: adjudicando a mano los 11 candidatos de
desarrollo, la tasa de positivos fue 45,5 % (5/11), IC 95 % Wilson [21,3 % – 72,0 %],
proyectando a evaluación ~37 relaciones, IC [17 – 58]. E3 exige ≥25 preguntas: el valor
central alcanza, **la cota inferior del intervalo no**. Sigue siendo **plausible, no
demostrado** — la resolución final requiere adjudicar a mano al menos una serie de
evaluación, trabajo humano todavía pendiente.

## Principios rectores

Se cierra con los dos principios que el curso exige para toda la metodología:

**Alineada al problema, no a una técnica de moda.** Cada elección metodológica —el
bloqueador, el protocolo de alineamiento, las tres condiciones— responde a una pregunta de
investigación declarada en el documento 03, no a la disponibilidad de una técnica.

**Transparente y reproducible.** Versiones exactas de modelos, semilla, ventana de contexto y
parámetros de muestreo publicados; el punto de operación del bloqueador versionado; y el
principio general del proyecto (`CONTRIBUTING.md` §7.1): si un número no puede reproducirse
desde `src/afg/` a través de un notebook, no entra en la tesis.

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
