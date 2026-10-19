# Calibración de τ con un juez: procedencia

Respuestas crudas del juez sobre una muestra de pares emparejados de las corridas del
*screen* de modelos de OpenKOS. Las produce y lee el
[notebook 17](../../../notebooks/17-jss-tau-referencia-en.ipynb) con
`src/afg/experiments/tau_calibration.py`.

| Campo | Valor |
|---|---|
| Entrada | `reports/experiment-a/model-screen-openkos/screen/` y `confirm/` (100 corridas), series ES2015 y TS3009, **solo desarrollo** ([ADR 0005](../../../docs/decisions/0005-adr-development-evaluation-split.md)) |
| Referencia | traducción al inglés (`data/processed/decisions/<SERIE>.reference-en.csv`, protocolo de alineación v2.0) |
| Pares | emparejamiento húngaro del puntaje (ámbito de la misma reunión) con τ = 0,50; similitud `bge-m3` en [0,50; 0,90); bins de 0,05; hasta 25 por bin; textos (extraído, referencia) distintos |
| Semilla del muestreo | 42 (`[shared_budget].seed`); también fija el orden en que el juez ve los dos textos |
| Muestra | 200 pares (25 por bin, 8 bins) de 1.848 pares de textos distintos |
| Juez | `gpt-oss:20b`, digest `f38aa0c53da5f8c49d08c43a99df24ff53167fe68e24664a7777288e7656fdfe` |
| Parámetros del juez | temperatura 0,0, semilla 42, razonamiento `low` (`[judge.calibration.think]`) |
| Prompt | `src/afg/evaluation/prompts/same_decision_v1.md`, versión `same-decision-v1`, SHA-256 `c34d5fc3eb80dc9c90f39ed996d646df7ff1cc3d172745a9655e3a982ce0a758` |
| Ejecución | 2026-10-18, Ollama local; 200 llamadas, 1.080 s en total, 0 respuestas ilegibles |

## Contenido

- `judgments.jsonl`: una línea por par con el par completo (textos, similitud, bin, modelos
  extractores), el orden de presentación, la salida cruda del juez, el veredicto, la razón y los
  segundos. Cada línea lleva una clave (hash de texto, orden, *prompt*, modelo, digest, semilla,
  temperatura y razonamiento): una ejecución con otra clave vuelve a llamar al juez y agrega una línea
  nueva; para un mismo par vale la última.
- `run.json`: descripción de la última ejecución (modelo, digest, versión y hash del *prompt*,
  parámetros, semilla del muestreo, pares y fallas).

## Política de datos

Son textos de decisiones de series de desarrollo, como las extracciones de
`reports/experiment-a/model-screen-openkos/`; ninguna cifra de aquí entra en una tabla de
resultados (ADR 0005).
