# Backlog — mcd-afg

Trabajo pendiente, en orden de dependencia. Última actualización: 2026-09-21.

> Las decisiones ya tomadas y la evidencia que las respalda están en
> [`decisions/`](decisions/) (ADRs) y en los resultados del paso cero más abajo.
> Este archivo solo lista lo que falta.

---

## Plan por curso

| Curso | Qué se entrega | Objetivos |
|> Sincronizado con `README.md` y `docs/avances/03-jss-objetivos.md`; si cambia, se actualiza en
> los tres lugares. El punto de decisión de AFG2 (semana 3: adaptador de OpenKOS de punta a
> punta, o OE3 se reduce a C1 contra C3) está en el documento 03.

---|---|---|
| **AFG1** | Problema, estado del arte, metodología, ética, conjunto de referencia listo para anotar (herramientas de OE1) y anotación iniciada en desarrollo | OE1 (herramientas) |
| **AFG2** | OE1 cerrado (anotación + kappa); OE2 sobre las 14 series con una escala de modelo (3 corridas); OE3 con banco de preguntas ≥100 y las tres condiciones, versión mínima | OE1, OE2, OE3 (mínimo) |
| **AFG3** | OE4, análisis de errores, intervalos bootstrap, conclusiones | OE4 |

---

## Decisiones ya tomadas (no reabrir sin evidencia nueva)

| # | Decisión | Evidencia |
|---|---|---|
| D1 | **Marco muestral: resumen abstractivo, no capa DDS.** 33 series completas / 649 decisiones, contra 6 / 136 | Medido sobre `ami_public_manual_1.6.2` |
| D2 | **DDS pasa a subconjunto de validación** en las 6 series que tienen ambas capas | 29 de las 47 reuniones con DDS caen dentro de las 56 de OE1 y 18 quedan fuera. Cobertura dentro de OE1: **4/4** en ES2015, ES2016, IS1004, IS1006, IS1008 y TS3005; **3/4** en IS1003; **2/4** en ES2002. Medido sobre `data/raw/ami/decision/manual/*.decision.xml` contra `config/corpus.toml` `[oe1]` |
| D3 | **Las etiquetas del conjunto de referencia las pone un humano.** Innegociable | Si un LLM construye OE1, C3 tiene errores de extracción por construcción y la brecha C2−C3 (todo OE4) se vuelve ruido |
| D4 | **Se automatiza todo menos la etiqueta**: normalización, evidencia, bloqueo de candidatos, kappa, banco de preguntas | Anotar los 3.071 pares de las 14 series exhaustivamente es inviable; con bloqueo son **92** (ver D9) |
| D5 | **El blocker usa coeficiente de solapamiento, no Jaccard** | Jaccard = 0,118 vs solapamiento = 0,400 en el par del botón turbo; Jaccard lo pierde |
| D6 | **El blocker no puede ser el LLM extractor.** Léxico o embeddings, canal independiente | Evita sesgar la referencia hacia lo que los LLM encuentran |
| D7 | **Eje nativo/no-nativo baja a limitación reportada.** El eje de rol pasa a análisis primario de §6.3 | 30,3 % de desconocidos en 33 series; solo 9/33 series lingüísticamente mixtas; roles balanceados 6/6/6/6 |
| D8 | **La muestra se balancea por sitio de grabación (ES/IS/TS), no por lengua** | La lengua está perfectamente anidada en el sitio; balancear por lengua es imposible y cualquier desbalance de sitio haría que un resultado sea un artefacto de sitio |
| D9 | **El blocker exige coeficiente ≥ 0,30 **y** `\|A∩B\| ≥ 2`** | Solo con el coeficiente selecciona 712/3.071 (23,2 %) ≈ 18 h; con el mínimo absoluto, 92 (3,0 %) ≈ 2,3 h, y el par del turbo sobrevive |
| D10 | **Split desarrollo (3) / evaluación (11).** No es train/test: nada se entrena | Se ajustan tres cosas (C1, τ, blocker) y ninguna puede ajustarse sobre los datos cuyos resultados se reportan. ES2015 e IS1004 ya están contaminadas por el piloto |
| D11 | **El corpus se congela en transcripciones legibles antes de anotar, en dos artefactos versionados por reunión**: `.md` para lectura e indexación, `.jsonl` con tiempos, offsets de caracteres e ids de acto de diálogo que enlazan de vuelta a `summlink` | 171 reuniones renderizadas por `afg corpus transcripts` a `data/interim/transcripts/` (ignorado por git); manifiesto de congelamiento de 171 filas con SHA-256 por artefacto en `reports/tables/transcripts_manifest.csv`; registro académico en `notebooks/02-jss-transcripciones.ipynb` (✅ en `notebooks/README.md`). La serie de notebooks se renumeró: anotación pasa a ser el notebook 03 |

---

## Resultados del paso cero y del piloto (referencia)

**Corpus.** `ami_public_manual_1.6.2`, CC BY 4.0, 228 MB en `data/raw/ami/` (ignorado por git).

**Capas verificadas.** `abstractive/<m>.abssumm.xml` (142) · `decision/manual/<m>.decision.xml`
(47) · `extractive/<m>.summlink.xml` (137) · `dialogueActs/<m>.<spk>.dialog-act.xml` (556) ·
`words/<m>.<spk>.words.xml` (687).

**Seis series DDS completas.** 136 decisiones abstractivas · 157 segmentos DDS · 22 flags
`external` (11 en reuniones kick-off, inservibles) · 11 `recap` → 22 enlaces candidatos.
**Ese 22 es un piso derivado de flags, no el conteo de enlaces** — el piloto encontró una
reversión explícita sin ningún flag.

**Piloto (ES2015 + IS1004, 53 decisiones).** 77,4 % normalizables a registro §5.2
(66,0 % limpias + 11,3 % compuestas) · 90,6 % ancladas a evidencia.

> ⚠️ **La tasa de adjudicación del piloto (~5,5 %) NO es generalizable y no debe citarse.**
> ES2015 e IS1004 resultaron ser las dos series de tasa más baja de las catorce. Sobre el
> conjunto real la tasa con solo coeficiente era 23,2 %. Ver D9. El rendimiento de
> normalización (77,4 % / 90,6 %) sí se mantiene como estimación, pero también sale de
> dos series y está sin replicar.

**Participantes.** 189 en total: 91 nativos / 96 no nativos / 2 desconocidos.
Las 6 series: 11 / 9 / 4. TS3005 completa ausente de `participants.xml`.

---

## Los cuatro N (no confundirlos)

| Nivel | N | Estado |
|---|---|---|
| Reuniones | **56** (14 series × 4) | medido, fijo |
| Frases `DECISIONS` | **343** | medido, fijo |
| Registros §5.2 tras la Tarea A | **~330** | **estimado**; el piloto dio ~96 % de rendimiento porque las compuestas se desdoblan |
| Pares entre reuniones | **3.071** | medido, fijo |
| Pares candidatos | **92** (0,30 + ≥2) | medido |
| **Relaciones reales** | **DESCONOCIDO** | **el número que decide si E3 vive** |
| Preguntas del banco | **≥100** (25 × 4) | **no existe** |

Reparto por el split: desarrollo 77 decisiones / 11 candidatos · evaluación 266 / 81.

> **Dos series aportan casi nada a E3:** IS1006 e IS1009 dan 1 candidato cada una.
> Siguen aportando decisiones a OE2.

---

## Pendiente

### P1 — Elegir las series de OE1 ✅ **hecho** (2026-09-20)
- [x] **14 series elegidas**, balanceadas por sitio de grabación: 5 ES / 5 IS / 4 TS.
      343 decisiones, 3.071 pares entre reuniones, **92** pares a adjudicar
      (la cifra ≈170 que figuró aquí era una extrapolación desde las dos series de tasa
      más baja del conjunto; ver D9)
- [x] TS3012 declarada **inelegible** — `summlink` en solo 3 de 4 reuniones
- [x] ~~Series de control: ES2015, ES2008, IS1004, TS3005~~ → **revisado por el ADR 0005**:
      **ES2008, ES2016, IS1003, TS3005** (4/11 series de evaluación = 36,4 %). Dos de las
      anteriores quedaron en desarrollo, y el kappa se mide sobre lo que se reporta
- [x] 18 series **held-out**, no inspeccionar durante la anotación
- [x] ADR: [`decisions/0004-adr-oe1-series-selection.md`](decisions/0004-adr-oe1-series-selection.md)
- [x] Registrado en `config/corpus.toml`, sección `[oe1]`

> **Hallazgo estructural que cambió el criterio.** La lengua materna no está dispersa por el
> corpus: está **perfectamente anidada en el sitio de grabación**. ES (Edinburgh) es casi
> todo nativo; IS (Idiap) es casi todo no nativo; **TS (TNO) no tiene ningún participante en
> `participants.xml`** — los 40 desconocidos son el bloque TS completo. En AMI no se puede
> separar "hablante no nativo" de "grabado en Idiap". Esto refuerza D7 por razones
> estructurales, no de tamaño muestral, y hace del **sitio** la variable a balancear.

### P2 — `annotation/blocking.py` ✅ **hecho** (2026-09-20)
- [x] Coeficiente de solapamiento, umbral configurable, por defecto 0,30
- [x] Caso de regresión en verde: `test_turbo_button_pair_survives_overlap_but_not_jaccard`
      fija |A|=14, |B|=5, intersección `{button, turbo}`, Jaccard 0,118 (se pierde),
      solapamiento 0,400 (se captura), y que el par **está** entre los candidatos
- [x] `STOPWORDS` + `BLOCKER_VERSION` versionados; cambiarlos invalida los candidatos ya
      generados, y la versión queda escrita en cada fila del CSV
- [x] `jaccard()` conservada **solo** para que el test pueda demostrar el fallo
- [x] `afg gold recall-sample` con semilla fija y muestreo determinista
- [x] Reproduce lo medido a mano

> **Corregido después (D9).** Solo con el coeficiente, sobre las 14 series reales, el
> blocker seleccionaba **712/3.071 = 23,2 %** (~18 h), no el 5,5 % del piloto: **las dos
> series piloto resultaron ser las dos de tasa más baja de las catorce**. Causa: el
> coeficiente divide por `min(|A|,|B|)`, así que las frases cortas se vuelven promiscuas
> (ES2002 tiene mediana de 3,5 tokens). Arreglo: exigir además `|A∩B| ≥ 2` → **92 (3,0 %)**.
> El punto de operación está acotado por ambos lados: umbral ≤ 0,40 **y** mínimo ≤ 2, o se
> pierde el par del turbo.
>
> **La muestra de recall no es un trámite: es lo que fija el umbral.**
>
> **Arreglo aplicado (2026-09-20).** `min_overlap_tokens=2` por defecto,
> `BLOCKER_VERSION` 1.0 → **1.1** (cambiar el punto de operación invalida los candidatos ya
> generados: para eso existe la versión). `--min-overlap` expuesto en el CLI, y cada línea
> de resumen imprime `threshold`, `min_overlap` y `blocker_version`, así que todo CSV se
> puede trazar a la configuración que lo produjo. Test de frontera en verde:
> `test_turbo_button_pair_survives_at_default_but_is_lost_past_either_bound` — sobrevive en
> (0,30 · 2) y **muere** en (0,30 · 3) y en (0,50 · 2). Ese test es el que impide que
> alguien apriete el blocker hasta dejarlo inútil. Total 92 fijado como regresión, leyendo
> las series desde `config/corpus.toml`, no hardcodeado.

### P3 — Completar `annotation/goldset.py` ✅ **hecho** (2026-09-20)
- [x] `build_gold_decisions` implementado; ya no queda ningún `NotImplementedError`
- [x] Emite `data/processed/decisions/<serie>.decisions.csv` con el esquema del
      [manual](anotacion/manual-anotacion-oe1.md) §2 + columna `machine_flags`
- [x] `evidence_da_count` y `evidence_text` resueltos por la cadena completa
      `summlink` → `dact` (filtrando el href a `da-types.xml`) → rango de `words`
- [x] Sugerencias en `machine_flags`, **nunca en `status`**:
      `sin_evidencia` · `posible_compuesta` · `frase_corta`
- [x] Las cinco columnas humanas salen vacías, verificado en todas las filas
- [x] Regresiones fijadas: IS1004 = 24 (a4/b6/c2/d12), ES2015 = 29,
      `IS1004c.elana.s.29` → 6 actos, `IS1004d.elana.s.22` → 0 + `sin_evidencia`

### P4 — Comandos CLI que el manual asume ✅ **hecho** (2026-09-20)
- [x] `afg gold build --series <ID>`
- [x] `afg gold candidates --series <ID>` (P2)
- [x] `afg gold agreement --series <ID>` — kappa **separado** para existencia / tipo /
      dirección; nunca un kappa combinado
- [x] `afg gold recall-sample --series <ID> --n <N> --seed <S>` (P2)
- [x] `afg gold evidence --meeting <ID> --term <palabra>` — el buscador que el manual §3.3
      asume para las filas con `evidence_da_count = 0`

> **El manual de anotación ya es ejecutable de punta a punta.**

### P9 — Estimar la tasa de positivos ✅ **hecho, provisional** (2026-09-20)
- [x] Adjudicados los **11 candidatos de desarrollo** (ES2015, IS1004, TS3009), cada uno
      contrastado contra transcripción
- [x] **Tasa de positivos = 45,5 % (5/11), IC 95 % Wilson [21,3 % – 72,0 %]**
- [x] Extrapolación a evaluación (81 candidatos): **~37 relaciones, IC [17 – 58]**
- [x] **Primera relación entre reuniones verificada del proyecto**: TS3009c → TS3009d,
      titanio reemplazado por plástico por costo (`reemplaza`), con la resistencia registrada
      en la transcripción: *"we'll hate the managers for that"*
- [ ] **Estrechar el intervalo**: adjudicar una serie de **evaluación** (trabajo humano).
      Con n = 11 no se puede afirmar que E3 sea viable, solo que es plausible

> ⚠️ **Estas etiquetas las puso una máquina y NO son el conjunto de referencia.** Sirven solo
> para decidir si vale la pena invertir las horas de anotación. No se escribieron en ningún
> `*.candidates.csv` y no deben mostrarse a un anotador antes de que anote. Solo se adjudicó
> desarrollo: leer el contenido de evaluación lo contamina.
>
> **Lectura para E3.** El estrato necesita ≥ 25 preguntas. El valor central (37) da holgura;
> **la cota inferior (17) no alcanza.**

### P5 — Anotación humana 🟡 depende de P1–P4
Anotan Germán Vega y Gustavo Martínez; adjudica Jason Sepúlveda (ver `CONTRIBUTING.md` §1).

| Tarea | Volumen | Ritmo (manual) | Horas estimadas |
|---|---|---|---|
| A — Normalizar decisiones | 343 filas | ~30 s por fila | ≈ 3 h |
| B — Adjudicar pares candidatos | 92 pares | 1–2 min por par | ≈ 2–3 h |
| C — Muestra de recall del bloqueador | 50 pares rechazados por serie muestreada (`--n 50`) | 1–2 min por par | ≈ 1–2 h |
| D — Doble anotación (4 series de control: ES2008, ES2016, IS1003, TS3005) + kappa + adjudicación | Las decisiones y pares candidatos de esas 4 series, anotados por ambos | como A y B | ≈ 3 h por anotador + sesión de adjudicación |
| Banco de preguntas (OE3) | ≥ 100 preguntas con respuesta y evidencia, 4 estratos | ~5 min por pregunta (autor) + ~3 min (validador) | ≈ 8 h autor + ≈ 5 h validador |
| **Total OE1** | | | **≈ 10–12 h de trabajo humano**, repartidas entre dos anotadores |

- [ ] Tarea A sobre las series elegidas
- [ ] Tarea B, en orden cronológico estricto (§5.1, sin fuga de información)
- [ ] Tarea C, muestra de recall
- [ ] Tarea D, doble anotación + kappa + adjudicación

### P6 — Deuda técnica ✅ **casi cerrada** (2026-09-20)
- [x] `src/afg/corpus/nxt.py`: los tres supuestos obsoletos resueltos con lo verificado
      (layout real, incluida la anidación `decision/manual/`; las dos formas de `href`;
      la trampa del doble `href` en `dact`; el formato de los ids NXT)
- [x] `config/corpus.toml` `[corpus.phases]`: afinado. **La cronología SÍ está verificada**
      vía `startTime` en `meetings.xml` (IS1004: 11h03 → 12h03 → 14h13 → 15h34 el mismo día);
      **los nombres de fase NO** — no existen en el corpus, solo en los papers del escenario
- [x] `.env.example` está vacío a propósito: ninguna parte del harness necesita
      credenciales todavía. Se completa cuando una condición lo requiera

### P8 — Verificar contra transcripción los candidatos identificados a ojo ✅ **hecho** (2026-09-20)
Durante el piloto se listaron 6 posibles relaciones entre reuniones **identificadas a ojo,
sin trazar la transcripción**. El único que sí se trazó —la supuesta reversión del botón
turbo, `IS1004c` → `IS1004d`— **resultó falso**: el resumen abstractivo de AMI afirma una
eliminación que la transcripción contradice (ver el ejemplo trabajado del
[manual](anotacion/manual-anotacion-oe1.md) §3). Los cinco restantes están sin verificar y
deben tratarse como hipótesis, no como hallazgo.

- [ ] `ES2015c` → `ES2015d`, chip regular (¿`reafirma`?)
- [ ] `ES2015c` → `ES2015d`, plástico + goma (¿`reafirma` / `refina`?)
- [ ] `ES2015b` → `ES2015d`, color corporativo (¿`refina`?)
- [ ] `IS1004b` → `IS1004c`, LCD / ASR descartados (¿`reafirma`? marcado `recap`)
- [ ] `IS1004d`, "single, not double curve" — ¿existe la decisión anterior de doble
      curvatura dentro de la serie, o la frase refiere algo fuera de ella?
- [x] **Resultado: 3 de 6 confirmadas. El 50 % de los juicios a ojo estaban equivocados.**
      Confirmadas: chip regular (`reafirma`), plástico+goma (`reafirma`), LCD/ASR (`reafirma`).
      Falsas: color corporativo (objetos distintos), "single not double curve" (**la decisión
      anterior no existe en IS1004** — la única de doble curvatura está en ES2015, otra serie),
      y el botón turbo (ya sabido).
- [x] Detalle en
      [`../notebooks/01-jss-viabilidad-e3.ipynb`](../notebooks/01-jss-viabilidad-e3.ipynb)

> **Dos consecuencias.** (1) La afirmación "los flags DDS subcuentan las relaciones reales"
> **queda con apoyo parcial**: IS1004b → c es una relación real que el blocker **no**
> seleccionó, o sea un falso negativo confirmado — pero viene de una sonda no aleatoria y no
> reemplaza la muestra de recall de la Tarea C. (2) **La capa de decisiones abstractivas tiene
> huecos**: hay relaciones reales cuyo extremo anterior nunca se registró como decisión. La
> Tarea A debe anotarlas en `notes`, no descartarlas en silencio.

> **Consecuencia sobre una conclusión previa.** La afirmación "los flags DDS subcuentan las
> relaciones reales" se apoyaba en el caso del turbo. Al caerse ese caso, la afirmación
> **queda sin prueba**. Puede seguir siendo cierta; hoy no está demostrada.

### P7 — Revisión de la tesis 🟡
- [ ] **§1.6: fortalecer la afirmación de novedad con evidencia directa.** AMI **declara**
      una capa `decisionlink` (`corpusdoc/annot_decisionlink.html`, `AMI-metadata.xml`,
      `resource.xml`: *"decision points manual coding"*, anotador MK, responsable Hsueh,
      ruta `decision/manual`). No la debilita — la refuerza, y ahora se puede decir con
      precisión: (a) enlaza un segmento `decision` con una **`sentence` del resumen**, no
      con otra decisión; (b) es *"one file per observation"*, o sea estructuralmente
      **intra-reunión**; (c) **no se distribuye ningún dato** — `decision/manual/` contiene
      solo los 47 `.decision.xml`, con 288 elementos `<decision>` y **cero** punteros a
      `abssumm`. Verificado 2026-09-20 sobre `ami_public_manual_1.6.2`
- [ ] §5.0: reescribir el párrafo de muestreo (DDS → resumen abstractivo)
- [x] §5.1: publicar 91/96/2 y declarar que `native_language` es la fuente, no la heurística
      (2026-09-21, aplicado en `propuesta.md`)
- [x] §6.3: bajar el eje de lengua a limitación; rol pasa a primario
      (2026-09-21, aplicado en `propuesta.md` §3 OE2, §5.1, §5.6 y §6.3)
- [ ] §5.4: documentar coeficiente de solapamiento y la evidencia contra Jaccard
- [x] §7: actualizar el riesgo principal — el cuello de botella eran los flags, no el corpus
      (2026-09-21, reescrito: E3 plausible pero no demostrado, cota inferior 17 contra el
      mínimo de 25 preguntas)
- [ ] §9: leer Zhang & Li, *ConsistencyGate* antes de fijar la afirmación de novedad
- [x] §5.0: quitar "desde abril de 2017" de la licencia (la página no declara fecha)
      (2026-09-21, aplicado en `propuesta.md` §5.0)
- [ ] §8: aplicar las correcciones bibliográficas ya hechas en refs.bib y en el avance 04.
      **Parcial** (2026-09-21): hechos Hsueh & Moore 2007a/b —el conteo 554/37.400 es de
      2007a, verificado contra <https://aclanthology.org/N07-1004.pdf>— y el título completo
      de Cai & O'Connor 2025. Quedan: autores de Zhang & Li 2026, listas de autores de Huang
      et al. y Bohnet et al., entrada de la página de licencia, y el sufijo de la cita de
      §5.1 sobre límites de tópico (no está en 2007a; falta alcanzar el texto de 2007b)

### P10 — Reparto de roles del equipo ✅ **hecho** (2026-09-20)
- [x] Completar la tabla de [`CONTRIBUTING.md`](../CONTRIBUTING.md) §1 con los tres
      integrantes (2026-09-20)
- [x] Anotadores independientes de OE1: Germán Vega y Gustavo Martínez (2026-09-20)
- [x] Adjudica los desacuerdos de la doble anotación: Jason Sepúlveda, que no anota (2026-09-20)
- [x] Autor del banco de preguntas: Gustavo Martínez (2026-09-20)
- [x] Valida el banco de preguntas: Germán Vega (2026-09-20)

### P11 — Entregables de AFG1 🟡
- [x] Presentación formal del problema (semana 4): ya enviada; archivada congelada en
      `docs/entregables/02-jss-informe-semana4.md` (2026-09-20)
- [x] Guiones de los videos de avance #1 y #2 archivados congelados (`00-` y `01-`)
- [x] Guion del video de avance #3 (semana 7): `docs/entregables/03-jss-guion-video-semana7.md`
- [ ] Registrar en cada entregable ya enviado la fecha exacta de envío (consultar Coursera)
- [ ] Grabar y subir el video de avance #3; registrar la fecha de envío en el guion
- [ ] Foro de alcances éticos: publicar la idea inicial (no evaluado, pero recomendado por el curso)

### P12 — Presentación final (semana 8) 🟡
- [ ] Guion con las cuatro secciones de la rúbrica: contextualización y problema; al menos dos
      trabajos relacionados y cómo se vinculan; propuesta metodológica por fases y aporte de
      cada fase; alcances éticos con riesgos y partes involucradas
- [ ] Material de apoyo (presentación) y video sin restricciones de acceso; lo sube una sola persona
- [ ] Revisión entre equipos: comentarios cualitativos en el foro del equipo asignado y
      formulario cuantitativo (obligatorio)

---

## Aún sin implementar en el harness (bloqueado por datos o por modelo)

`extraction/openkos_adapter.py` · `conditions/c1_document_rag.py` ·
`conditions/c2_compiled_auto.py` · `conditions/c3_compiled_gold.py` ·
`evaluation/judge.py::judge_answer`

Cada uno lanza `NotImplementedError` citando la sección de la tesis que lo especifica.
