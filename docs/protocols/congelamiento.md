# Registro de congelamiento

| | |
|---|---|
| **Documento** | Registro de congelamiento y bloqueo de las series de evaluación |
| **Estado** | Vigente. Lo que se congela lo fija el [ADR 0022](../decisions/0022-adr-congelamiento-de-las-corridas-formales.md); el registro se escribe al fusionarse ese ADR (issue #237) y rige desde que `config/freeze.json` existe |

## Qué es

Un archivo, `config/freeze.json`, que repite en forma legible por máquina lo que fija el ADR de congelamiento. Contiene:

- el número del ADR y el commit exacto del código;
- la huella SHA-256 de `config/experiments.toml` y del banco de preguntas;
- por serie, la huella de la referencia de decisiones, la de relaciones (tal como se resuelven: adjudicada o de anotación individual) y la de `<SERIE>.reference-en.csv`;
- los valores de `[pinned_environment]` (versiones de Ollama y OpenKOS y huella de cada modelo).

Se escribe una sola vez con `afg freeze write --adr <número>` y no se sobrescribe: cambiar algo congelado exige un ADR nuevo.

## Qué bloquea

`afg experiment a`, `a-batch`, `a-relations`, `afg c3 build` y `afg experiment b` aplican la misma regla antes de llamar a un modelo:

| Serie | Resultado |
|---|---|
| De desarrollo (ES2015, IS1004, TS3009) | Corre sin registro. |
| De evaluación | Corre solo si el registro existe, la serie está en él y nada difiere: configuración, referencia, banco de preguntas (el archivo que recibe `--questions` debe ser el congelado) y código (`src`, `pyproject.toml` y `uv.lock` iguales al commit congelado). |
| Sin partición en `config/corpus.toml` | Nunca corre. |

Si algo difiere, el comando se detiene y lista cada diferencia con la huella actual y la congelada. El entorno de la máquina (huellas de modelos, versiones de Ollama y OpenKOS) lo verifica a continuación la comprobación de `[pinned_environment]`; como el bloqueo exige que esa sección sea la congelada, la máquina queda comparada con lo congelado. `afg experiment b-closed-book` es un diagnóstico de desarrollo y sigue limitado a esas series.
