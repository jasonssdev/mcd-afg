# Screen de modelos generativos del pase de decisiones de OpenKOS: procedencia

Copia de solo lectura de las corridas del *screen* de modelos que OpenKOS hizo sobre su pase
de decisiones de transcripciones. Las lee el
[notebook 15](../../../notebooks/15-jss-screen-de-modelos-openkos.ipynb) con el puntaje de la
tesis (`src/afg/experiments/model_screen.py`).

| Campo | Valor |
|---|---|
| Origen | `~/Dev/Projects/openkos-eval-runs/model-screen/` (fuera de ambos repositorios) |
| Copiado | 2026-10-18, sin modificar los JSON |
| Prerregistro | `evals/transcript_decisions/PREREGISTRATION-model-screen.md` en OpenKOS (PR #1554), registrado antes de la primera corrida |
| Código del arnés | OpenKOS 0.6.0, commit `28ed7bed` (árbol limpio) para `screen/` y `confirm/`; `37169cb2` con árbol modificado para `probes/` |
| Prompt del pase | `extraction/decision_pass`, hash `6d3962b0dd75650c`, igual en todas las corridas |
| Configuración fija | techo de generación 8192, ventana de contexto 12288, un reintento por ventana fallida, a lo más 25 decisiones por reunión |
| Series | ES2015 y TS3009, **solo desarrollo** ([ADR 0005](../../../docs/decisions/0005-adr-development-evaluation-split.md)); ninguna serie de evaluación |
| Fecha de las corridas | 2026-10-18 |

## Contenido

| Carpeta | Modelos | n por modelo y serie | Uso |
|---|---|---|---|
| `probes/` | `qwen3:8b`, `qwen3:14b`, `qwen3.6:27b`, `qwen3.6:35b-a3b` | 1 corrida, solo TS3009 | Sondeo de tiempos antes del prerregistro. **No se puntúa** (lo excluye el prerregistro) |
| `screen/` | los mismos cuatro | 5 | El *screen* con la regla de selección |
| `confirm/` | `qwen3.6:27b` y `qwen3:8b` | 15, corridas nuevas | La corrida confirmatoria del modelo que avanzó |
| `validation/` | — | — | La reproducción, con la copia de OpenKOS del puntaje, de la cifra de ES2015 de la tesis (`es2015-explora-r3x`) |

Digest de los modelos en Ollama (12 primeros caracteres): `qwen3:8b` `500a1f067a9f`,
`qwen3:14b` `bdbd181c33f2`, `qwen3.6:27b` `bcbdbd4bcf86`, `qwen3.6:35b-a3b` `a7eb95c53bcf`.

Además de los `runs-pass-*.json`, cada carpeta trae lo que escribió el lado de OpenKOS:
`scored.json` y `scored.txt` (su puntaje: la copia de la métrica de la tesis y el *recall*
por solapamiento de evidencia del arnés), `diagnostics.txt` (techo entre idiomas y control
nulo) y los resúmenes de tiempos (`summary.txt`, `probe-summary.txt`). No se copiaron los
registros de ejecución (`*.log`) ni los scripts, que llevan rutas locales.

## Política de datos

Los JSON son salidas de extracción sobre series de desarrollo, como
`reports/experiment-a/es2015-explora-r*/extracciones.jsonl`, y se versionan igual que ellas
para que el notebook se pueda releer sin rehacer las corridas (unos 3,7 MB). No contienen
datos de las series de evaluación ni copias de la referencia adjudicada.
