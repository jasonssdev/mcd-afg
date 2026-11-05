# Registro de congelamiento

| | |
|---|---|
| **Documento** | Registro de congelamiento y bloqueo de las series de evaluación |
| **Estado** | Vigente. Lo que se congela lo fija el [ADR 0023](../decisions/0023-adr-recongelamiento-tras-la-auditoria.md), que reemplaza al ADR 0022; el registro se escribe tras la fusión del PR de ese ADR (issue #237) y rige desde que `config/freeze.json` existe |

## Qué es

Un archivo, `config/freeze.json`, que repite en forma legible por máquina lo que fija el ADR de congelamiento. Contiene:

- el número del ADR y el commit exacto del código;
- la huella SHA-256 de `config/experiments.toml`, `config/corpus.toml`, `config/annotation.toml` y del banco de preguntas;
- las transcripciones congeladas (`data/interim/transcripts`, fuera de git): número de archivos y una huella única calculada sobre las rutas ordenadas y la huella de cada archivo; se regeneran con `afg corpus transcripts --force`;
- por serie, la huella de la referencia de decisiones, la de relaciones (tal como se resuelven: adjudicada o de anotación individual) y la de `<SERIE>.reference-en.csv`;
- los valores de `[pinned_environment]` (versiones de Ollama y OpenKOS y huella de cada modelo).

Se escribe una sola vez con `afg freeze write --adr <número>` y no se sobrescribe: cambiar algo congelado exige un ADR nuevo.

## Qué bloquea

`afg experiment a`, `a-batch`, `a-relations`, `afg c3 build` y `afg experiment b` aplican la misma regla antes de llamar a un modelo:

| Serie | Resultado |
|---|---|
| De desarrollo (ES2015, IS1004, TS3009) | Corre sin registro. |
| De evaluación | Corre solo si el registro existe, la serie está en él y nada difiere: configuración (`experiments.toml`, `corpus.toml`, `annotation.toml`), transcripciones, referencia, banco de preguntas (el archivo que recibe `--questions` debe ser el congelado) y código (`src`, `pyproject.toml`, `uv.lock` y `.python-version` iguales al commit congelado). Además, no admite variables `AFG_GENERATIVE_MODEL`, `AFG_JUDGE_MODEL`, `AFG_EMBEDDING_MODEL`, `AFG_SEED` ni `AFG_OPENKOS_EXECUTABLE` (ni en el entorno ni en `.env`), y `--runs` solo puede valer lo configurado en `runs_per_config`. |
| Sin partición en `config/corpus.toml` | Nunca corre. |

Si algo difiere, el comando se detiene y lista cada diferencia con la huella actual y la congelada. El entorno de la máquina (huellas de modelos, versiones de Ollama y OpenKOS) lo verifica a continuación la comprobación de `[pinned_environment]`; como el bloqueo exige que esa sección sea la congelada, la máquina queda comparada con lo congelado. `afg experiment b-closed-book` es un diagnóstico de desarrollo y sigue limitado a esas series.

## Fallas y repeticiones

Una corrida formal dura horas y puede interrumpirse. Reanudarla no viola el protocolo: lo
congelado (configuración, referencia, banco, código, modelos) sigue siendo el mismo, y el
bloqueo lo vuelve a comprobar en cada comando.

- **Reanudar es repetir el comando con el mismo `--run-name`.**
  - `afg experiment a-batch` omite los pares (serie, corrida) ya terminados y rehace desde un
    espacio limpio los que quedaron a medias o fallaron.
  - `afg experiment b` conserva los registros completos de `respuestas.jsonl`, que solo se
    agrega al final: para cada (pregunta, condición, corrida) vale el último registro. Los
    registros con error se reintentan. Al reanudar se compara el manifiesto: si cambió el banco,
    las condiciones, las series o la extracción de C2, el comando se niega.
- **Diez errores seguidos abortan** el Experimento B (`RunAbortedError`): señal de una causa
  sistémica (típicamente Ollama caído). Se corrige la causa y se repite el comando.
- **El historial de errores queda registrado.** En B cada intento con error es una línea de
  `respuestas.jsonl` y el manifiesto cuenta `records` (todas las líneas), `complete` y `errors`
  (último estado de cada clave). En A el manifiesto guarda el estado, el último error y las
  horas de cada par. Una corrida reanudada se informa como tal.
- **Las respuestas con `judge_failure` no se reintentan.** Son un resultado medido (el juez
  contestó algo que no se pudo leer) y repetirlas no lo cambiaría. Se cuentan y se informan en
  la tasa de JSON válido del juez.
- **Si Ollama se cae:** se reinicia el servicio, se comprueba el entorno (`afg` compara las
  versiones y huellas de los modelos con las congeladas) y se repite el comando con el mismo
  `--run-name`. Reiniciar Ollama no cambia lo congelado mientras las versiones y las huellas
  sigan siendo las del registro.
- **Una corrida abandonada y reiniciada con un nombre nuevo** (porque el directorio se corrompió
  o se prefirió empezar de cero) se declara en el notebook de resultados: nombre abandonado,
  nombre nuevo y motivo. La corrida abandonada no se borra ni se usa para elegir resultados.
- **Un congelamiento nuevo se necesita solo si algo congelado cambia** (un modelo, un parámetro,
  una etiqueta de la referencia, una pregunta, el código). Eso exige un ADR nuevo, como dice la
  regla del ADR de congelamiento. Una falla, una reanudación o un reinicio de la máquina no lo
  exigen.
