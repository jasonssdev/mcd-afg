# Fuente de datos

| | |
|---|---|
| **Documento** | 02 — Fuente de datos |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.1 |
| **Fecha** | 2026-09-20 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial. Fuente de datos, auditoría y riesgos para AFG1. | Primera entrega del curso. |
| 1.1 | 2026-09-20 | Redacción en voz impersonal / de equipo. | El proyecto es de un equipo de tres personas; ningún documento se redacta en primera persona singular. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## 1. El corpus y su licencia

Se trabaja sobre el **AMI Meeting Corpus** (Carletta et al., 2006; Carletta, 2007), ~100 horas
de reuniones grabadas, de las cuales cerca de dos tercios corresponden al escenario de
diseño de un control remoto. Se descarga el paquete de anotaciones manuales
`ami_public_manual_1.6.2.zip` (22,9 MB comprimido, 228 MB extraído) desde la página oficial
del corpus.

**Licencia: CC BY 4.0.** Se cita la página de licencia como
autoridad de los términos de uso, no los artículos originales del corpus (Carletta et al.,
2006; Carletta, 2007), que describen una licencia anterior más restrictiva —esta es una
condición explícita del curso para el uso de fuentes de datos públicas, y una advertencia que
el equipo debía verificar antes de asumir el régimen de uso.

## 2. La estructura en series y por qué importa

El corpus está organizado en **series de cuatro reuniones** con los mismos cuatro
participantes (*kick-off*, diseño funcional, diseño conceptual, diseño detallado). Esta
estructura es la que hace posible el objetivo central del proyecto: sin una secuencia
temporal de reuniones del mismo equipo sobre el mismo objeto, no existe "evolución de una
decisión" que medir. Por eso la unidad de muestreo para OE1 y para el Experimento B no es la
reunión, sino la **serie completa**.

## 3. Capas usadas y cadena de evidencia

Cuatro capas de anotación, verificadas por conteo directo de archivos sobre el paquete
descargado: `abstractive` (142 archivos, resúmenes con encabezados `DECISIONS`), `summlink`
(137, enlaza frases del resumen a actos de diálogo), `decision/manual` — la capa *Decision
Discussion Segmentation* o DDS (47) — y `dialogueAct` (556) y `words` (687) como soporte de
evidencia. De las 56 reuniones seleccionadas (ver §4), 54 tienen además la capa `topic`.

La cadena de evidencia de cada decisión es: **resumen abstractivo → `summlink` → acto de
diálogo → palabras**. Es la misma operacionalización que usan Hsueh y Moore (2007), lo que
preserva comparabilidad con la literatura.

## 4. Auditoría de datos

### 4.1 Marco muestral

Se midieron dos marcos posibles y se eligió el primero (decisión D1 del registro de
decisiones): **33 series
completas** con resumen abstractivo en sus cuatro reuniones (649 decisiones), frente a sólo
**6 series** con la capa DDS completa (136 decisiones). La capa DDS no se descarta: pasa a
**subconjunto de validación** dentro de las series que la tienen (D2). De las 33, **32**
tienen además `summlink` completo; **TS3012** queda inelegible por tenerlo sólo en 3 de 4
reuniones.

### 4.2 Selección de 14 series

De las 32 series elegibles se seleccionaron **14** (56 reuniones), con el criterio de **balancear
por sitio de grabación** (ES / IS / TS) y no por lengua materna —ver §5 sobre por qué la
lengua no es la variable balanceable—, prefiriendo dentro de cada sitio las series de mayor
volumen de decisiones. El resultado: **343 frases `DECISIONS`**, **3.071 pares de decisiones
entre reuniones**, y, tras el filtro de candidatos (§4.4), **92 pares candidatos**. Detalle
del criterio y las series descartadas en
[`../decisions/0004-adr-oe1-series-selection.md`](../decisions/0004-adr-oe1-series-selection.md).

### 4.3 Partición desarrollo / evaluación

No es un *train/test split*: nada se ajusta con aprendizaje automático. Separa los datos
usados para **tomar decisiones de diseño** (parámetros de C1, el umbral de alineamiento τ, el
punto de operación del bloqueador de candidatos) de los datos usados para **reportar
resultados**.

- **Desarrollo:** ES2015, IS1004, TS3009 — 77 decisiones / 11 candidatos.
- **Evaluación:** 11 series — 266 decisiones / 81 candidatos, con balance de sitio 4 ES / 4
  IS / 3 TS.
- **Control de doble anotación** (≥25 % exigido por OE1): ES2008, ES2016, IS1003, TS3005
  — 36,4 % de la evaluación.

Todo parámetro ajustado en desarrollo se congela antes de tocar evaluación. Detalle en
[`../decisions/0005-adr-development-evaluation-split.md`](../decisions/0005-adr-development-evaluation-split.md).

### 4.4 Los cuatro N

| Nivel | N | Estado |
|---|---|---|
| Reuniones | 56 (14 series × 4) | Medido, fijo |
| Frases `DECISIONS` | 343 | Medido, fijo |
| Pares entre reuniones | 3.071 | Medido, fijo |
| Pares candidatos (bloqueador) | 92 | Medido, fijo |

El bloqueador exige **coeficiente de solapamiento ≥ 0,30 y `\|A∩B\| ≥ 2`** simultáneamente.
Sólo con el coeficiente, el bloqueador seleccionaba 712 de 3.071 pares (23,2 %, ≈18 h de
anotación); con el mínimo absoluto de tokens compartidos añadido, 92 (3,0 %, ≈2,3 h), sin
perder el **caso de regresión** del bloqueador: el par del botón turbo, `IS1004c` →
`IS1004d` (D9).

Ese par **no es una relación confirmada**. La verificación contra transcripción mostró que la
reversión que el resumen abstractivo afirmaba nunca ocurrió (§5;
[`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb)),
y el caso se conserva precisamente por su forma léxica: es el par de solape más exigente
medido en el piloto —solapamiento 0,400 frente a Jaccard 0,118 (D5)— y por eso acota el punto
de operación por ambos lados, umbral ≤ 0,40 **y** mínimo ≤ 2. Que la relación resultara falsa
no debilita la prueba de regresión: lo que el caso fija es la sensibilidad del bloqueador a
una frase corta, no la existencia de un enlace.

### 4.5 Composición lingüística

189 participantes en el corpus: **91 nativos de inglés, 96 no nativos, 2 desconocidos**. La
lengua materna está **perfectamente anidada en el sitio de grabación**: Edinburgh (ES) es
casi todo nativo, Idiap (IS) es mayoritariamente no nativo, y **TNO (TS) no tiene ningún
participante registrado en `participants.xml`**. En AMI no es posible separar "hablante no
nativo" de "grabado en Idiap" — es la razón estructural, no de tamaño muestral, por la que
se balancea por sitio y no por lengua (§5).

### 4.6 Autoría por rol

Sobre 685 actos atribuidos en las 14 series: **PM 47,0 % · ID 22,8 % · ME 15,3 % · UI
14,9 %**. La proporción del PM se mantiene entre 44 % y 50 % en cada sitio por separado, lo
que indica que es **estructural** (quien preside habla y decide más) y no un artefacto de la
muestra.

### 4.7 Anclaje a evidencia

**317 de 343 decisiones (92,4 %)** tienen al menos un acto de diálogo como evidencia
identificada por la cadena del §3.

### 4.8 Segmentación por tópico como proxy — descartada

La propuesta cita a Hsueh y Moore para descartar los límites de tópico como proxy de límites
decisorios ("menos de la mitad de las veces"). **Se midió esto directamente sobre la muestra del proyecto**:
9,0 % de coincidencia de fronteras con tolerancia de 5 palabras, y sólo 16,5 % con 80
palabras — muy por debajo de lo que reporta la literatura. Es una medición propia, no una
cita, y confirma con más fuerza la decisión de no usarlo.

## 5. Riesgos declarados

- **Sesgo de dominio.** Todas las reuniones tratan el mismo producto (un control remoto).
  No se afirmará generalización a otros dominios.
- **Habla actuada.** Los participantes siguen un guion de escenario; las decisiones son
  reales como actos conversacionales, pero sus consecuencias organizacionales son simuladas.
- **Anidamiento lengua/sitio.** Descrito en §4.5. Cualquier lectura de "efecto de lengua" en
  este corpus es indistinguible de un efecto de sitio de grabación.
- **Huecos en la capa de decisiones.** La capa `decisionlink` de AMI existe en el diseño
  pero no distribuye datos (documento 01, §4); y el análisis de casos del piloto encontró una
  relación real (IS1004b → IS1004c) que el bloqueador **no** seleccionó como candidata —un
  falso negativo confirmado, aunque proveniente de una revisión dirigida, no de la muestra de
  recall formal.
- **El material de origen contiene errores.** El resumen abstractivo de AMI para IS1004d
  afirma que se eliminó el botón turbo; la transcripción muestra que se mantuvo. La señal
  `evidencia = 0 actos` predijo este error antes de leer la transcripción — es el argumento a
  favor de exigir evidencia obligatoria en cada decisión (§5.2 del documento 06).

## 6. Plan de saneamiento

1. **Nunca decidir en la capa automática.** Todo lo que el bloqueo y la normalización
   automática producen son *sugerencias* en una columna `machine_flags`
   (`sin_evidencia`, `posible_compuesta`, `frase_corta`), nunca en la columna `status`. Sólo
   un humano decide si algo es una decisión y qué relación tiene con otra.
2. **Contrastar contra la transcripción, no contra el resumen.** El caso del botón turbo
   demuestra que el resumen abstractivo puede estar equivocado; el protocolo de anotación
   exige volver a los actos de diálogo, no aceptar el resumen como verdad.
3. **Doble anotación y kappa por tipo** (existencia / tipo de relación / dirección, nunca
   combinado) sobre el 36,4 % de la evaluación, con adjudicación documentada.
4. **Congelar antes de anotar.** El punto de operación del bloqueador, el criterio de
   selección de series y el split quedan fijados en
   [`../../config/corpus.toml`](../../config/corpus.toml) antes de que empiece la anotación
   humana, para que ningún ajuste posterior pueda leerse como sobreajuste a los resultados.

## Cambios respecto de la propuesta original

| Qué cambió | Evidencia que lo obligó |
|---|---|
| Marco muestral: de 6 series DDS (136 decisiones) a 33 series con resumen abstractivo (649), reduciéndose a 14 series seleccionadas | Medición directa sobre `ami_public_manual_1.6.2`; decisión D1 |
| El balanceo de la muestra es por **sitio**, no por lengua materna | La lengua está perfectamente anidada en el sitio (D7, D8); TS3005/bloque TS entero sin datos en `participants.xml` |
| El eje nativo/no-nativo baja de estratificación obligatoria a limitación declarada | 30,3 % de participantes desconocidos en las 33 series; ver documento 03 y 05 |
| El conteo de candidatos pasó de una extrapolación de ~170 a 92 medidos | El bloqueador con sólo coeficiente daba 712/3.071 (23,2 %); con `\|A∩B\|≥2` añadido, 92 (3,0 %) — D9 |
| El bloqueador usa coeficiente de solapamiento, no Jaccard | Jaccard = 0,118 pierde el par del botón turbo; solapamiento = 0,400 lo captura — D5 |
| La reversión del botón turbo, identificada a ojo en el piloto, resultó **falsa** al contrastar con la transcripción | Documentado en [`../anotacion/manual-anotacion-oe1.md`](../anotacion/manual-anotacion-oe1.md) §3 |

---

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| Licencia CC BY 4.0 (verificada en la página oficial el 20-09-2026), tamaño del paquete | [`../../config/corpus.toml`](../../config/corpus.toml) |
| Capas: 142/137/47/556/687/54 archivos | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Marco muestral 33/649 vs 6/136; D1, D2 | [`../decisions/README.md`](../decisions/README.md) |
| Selección de 14 series, criterio de balance por sitio | [`../decisions/0004-adr-oe1-series-selection.md`](../decisions/0004-adr-oe1-series-selection.md) |
| Split desarrollo/evaluación, control de doble anotación | [`../decisions/0005-adr-development-evaluation-split.md`](../decisions/0005-adr-development-evaluation-split.md) |
| Los cuatro N (56, 343, 3.071, 92) | [`../../config/corpus.toml`](../../config/corpus.toml), sección `[oe1]`; [`../README.md`](../README.md), sección "Los cuatro N" |
| 91/96/2 participantes; anidamiento lengua/sitio; TS sin `participants.xml` | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Autoría por rol (PM 47,0 % etc.) | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Anclaje a evidencia 317/343 (92,4 %) | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Proxy de tópico: 9,0 % / 16,5 % | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Bloqueador: 712/3.071 con sólo coeficiente, 92 con mínimo absoluto | [`../decisions/README.md`](../decisions/README.md), decisión D9 |
| Botón turbo: falso positivo del resumen abstractivo | [`../anotacion/manual-anotacion-oe1.md`](../anotacion/manual-anotacion-oe1.md) §3 |
| Caso IS1004b → IS1004c no seleccionado por el bloqueador | [`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb) |
