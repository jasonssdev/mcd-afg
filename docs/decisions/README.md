# decisions/ — el registro de decisiones

Este directorio guarda **por qué** el proyecto es como es. Es lo único de la
documentación que no se recalcula ni se sincroniza con nada: se escribe una vez, cuando se
decide algo, y se deja quieto.

## Dos formatos, dos alcances

- **ADR** (*architecture decision record*) — una decisión con **consecuencia
  arquitectónica** sobre el arnés: cómo se organiza el código, qué herramienta se usa,
  dónde está el límite del instrumento, qué series entran en la muestra. Lleva **archivo
  propio**, numerado `NNNN-adr-{nombre}.md`, con contexto, decisión y consecuencias. La
  secuencia de cuatro dígitos hace que el directorio se ordene en el orden en que se
  tomaron.
- **Entrada D** — una decisión de **diseño o de método** que cambia una cifra, un criterio o
  un procedimiento. Es **una fila** de la tabla de abajo, con su evidencia al lado. No lleva
  archivo propio: su razonamiento largo, cuando existe, está en un notebook o en un ADR.

Los dos alcances no se excluyen. Una decisión que cambia una cifra **y además** tiene
consecuencia arquitectónica lleva las dos cosas: su ADR, donde vive el razonamiento completo,
y su fila D, que la deja en su sitio dentro de la secuencia. Cuando eso pasa, **el ADR es el
canónico** y la fila es su entrada de índice. Es el caso de **D10** y el
[ADR 0005](0005-adr-development-evaluation-split.md).

## La regla que impide que esto se pudra: es append-only

Se **añade** una fila cuando se decide algo. **No se editan las filas viejas.** Si una
decisión se revisa, no se corrige en su sitio: se añade otra que la **reemplaza** y lo dice,
como hizo el [ADR 0005](0005-adr-development-evaluation-split.md) con parte del
[ADR 0004](0004-adr-oe1-series-selection.md).

Un registro que solo crece nunca queda desactualizado: describe lo que se decidió en el
momento en que se decidió, que es un hecho y no cambia. Por eso este archivo no lleva
estados, ni casillas, ni cifras que un comando produzca. Lo que está pendiente vive en
**issues de GitHub**; lo que un comando calcula se lee corriendo el comando.

## Los ADR

| ADR | De qué trata |
|---|---|
| [0001](0001-adr-record-architecture-decisions.md) | Registrar decisiones de arquitectura en ADR livianos bajo `docs/decisions/`, un archivo por decisión, formato Nygard |
| [0002](0002-adr-uv-and-src-layout.md) | Reemplazar el entorno conda por **uv** (`pyproject.toml` + `uv.lock`, Python 3.13) y mover el código importable a `src/afg/` |
| [0003](0003-adr-openkos-as-instrument.md) | OpenKOS es el **instrumento** de extracción y persistencia, no un entregable del proyecto; el aporte es la referencia OE1, el diseño de tres condiciones y la medición de atribución |
| [0004](0004-adr-oe1-series-selection.md) | Selección de las **14 series** de OE1 sobre el marco de resúmenes abstractivos, balanceadas por sitio de grabación; TS3012 inelegible por `summlink` incompleto |
| [0005](0005-adr-development-evaluation-split.md) | División **desarrollo (3) / evaluación (11)** y revisión de las cuatro series de control. Reemplaza parte del 0004 |

> **El ADR 0005 es el registro canónico del split desarrollo / evaluación.** La fila **D10**
> dice lo mismo en una línea, y eso es deliberado: es su entrada de índice, no una segunda
> versión. Ante cualquier discrepancia entre las dos, manda el ADR, que es el que lleva el
> contexto, las alternativas rechazadas y las consecuencias.
>
> No se borra ni se reescribe D10, porque este registro es append-only y la tabla de abajo es
> donde se lee la secuencia completa de decisiones en el orden en que se tomaron: quitarle
> una fila dejaría un hueco justo donde está el hecho.

## Decisiones tomadas (no reabrir sin evidencia nueva)

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
| D12 | **El banco de preguntas arranca cuando las cuatro series de control de la Fase 2 están adjudicadas, y sus preguntas salen solo de series de evaluación.** Cierra por estrato, no por fecha: `E1_point_fact` y `E4_unanswerable` no consumen relaciones y se cierran con la Fase 2; `E2_current_state` y `E3_evolution` sí, y quedan abiertos hasta reunir 25 cada uno. Se escriben desde el arranque contra las relaciones ya adjudicadas, no al final. Si E3 no alcanza 25 con las once series de evaluación cerradas, se reporta el número real y no se rellena el cupo | E2 consume relaciones igual que E3: `src/afg/domain/question.py` lo define como *"requires knowing which of several versions of a decision prevails"*, así que son **50** preguntas atadas a la adjudicación y no 25. Contando los candidatos por serie y proyectando con la tasa provisional de 45,5 % (IC 95 % [21,3 – 72,0 %], ver D9 y `notebooks/01-jss-viabilidad-e3.ipynb`): la Fase 2 aporta 37 candidatos ≈ 17 relaciones; las 7 series de evaluación de la Fase 3, 44 ≈ 20; las 11 juntas, 81 ≈ 37. Una misma relación sostiene una E2 y una E3, así que el mínimo real son 25 relaciones distintas: el valor central deja holgura, la cota inferior no. Las series de desarrollo quedan excluidas por el [ADR 0005](0005-adr-development-evaluation-split.md), que prohíbe reportar sus cifras como resultados |

## Evidencia del piloto

Estas cifras no las produce ningún comando y no aparecen en ningún otro documento. Se
conservan aquí porque son la evidencia de **D4** (qué se puede automatizar y qué no) y el
contrapeso de **D9** (por qué la tasa del piloto no servía para dimensionar el trabajo).

**Piloto sobre ES2015 + IS1004, 53 decisiones.** 77,4 % normalizables al registro §5.2
(66,0 % limpias + 11,3 % compuestas) · 90,6 % ancladas a evidencia.

> ⚠️ **La tasa de adjudicación del piloto (~5,5 %) NO es generalizable y no debe citarse.**
> ES2015 e IS1004 resultaron ser las dos series de tasa más baja de las catorce. Sobre el
> conjunto real la tasa con solo coeficiente era 23,2 %. Ver D9. El rendimiento de
> normalización (77,4 % / 90,6 %) sí se mantiene como estimación, pero también sale de
> dos series y está sin replicar.

**Participantes de las seis series DDS.** 11 nativos / 9 no nativos / 4 desconocidos; TS3005
completa ausente de `participants.xml`. Es una cifra del marco muestral **anterior** a D1: el
conteo vigente, sobre el corpus completo, es 189 participantes (91 / 96 / 2) y está en
[`../avances/02-jss-fuente-de-datos.md`](../avances/02-jss-fuente-de-datos.md) §4.5.

El resto de los resultados del paso cero —capas verificadas, totales de las seis series DDS,
flags `external` y `recap`, enlaces candidatos— **no se transcribe en ninguna parte**: lo
produce `uv run afg corpus inventory` y queda en
[`../../reports/tables/paso_cero_inventory.csv`](../../reports/tables/paso_cero_inventory.csv).

---

## Procedencia

Las entradas D1–D11 y las cifras del piloto vienen de `docs/BACKLOG.md`, **retirado el
2026-09-21**. Aquel archivo mezclaba seis cosas bajo un nombre que invitaba a seguir
agregándole tareas, y por eso se desincronizaba: repetía cifras que un comando ya calcula y
listaba como pendiente trabajo que ya estaba cerrado. El trabajo pendiente vive ahora en
**issues de GitHub**; el plan por curso, en `README.md`; los cuatro N, en
[`../README.md`](../README.md).
