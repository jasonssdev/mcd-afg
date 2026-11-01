# 0002. Usar uv y una organización src/, reemplazando el entorno conda

## Estado

Aceptada (2026-09-20). Enmendada (2026-11-01): el intérprete pasa de Python 3.13 a 3.14; ver la sección Enmienda.

## Contexto

El repositorio antes usaba un `environment.yml` de conda (`ds-py313`) y una organización
plana, de nivel superior, `utils`/`models`/`data` con archivos `__init__.py` sueltos
dispersos en directorios que no contienen código importable. Eso no escala a un paquete con
estructura interna real (`domain`, `corpus`, `annotation`, `extraction`, `conditions`,
`evaluation`, `bibliography`) y mezcla directorios de datos/generados con código fuente en
el mismo espacio de nombres de importación.

## Decisión

- Reemplazar conda por **uv** (`pyproject.toml` + `uv.lock`), con Python fijado en
  **3.13** (`.python-version`).
- Mover todo el código importable bajo **`src/afg/`** (la organización `src`), instalado
  vía `[project.scripts] afg = "afg.cli:app"`.
- Separar las dependencias opcionales, pesadas o específicas de entorno en extras
  (`instrument`, `llm`, `retrieval`, `embeddings`) para que `uv sync` siga siendo rápido
  por defecto.
- Los nombres de los módulos bajo `src/afg/` nombran el *dominio de investigación* (p. ej.
  `annotation/`, `conditions/`), no capas técnicas genéricas (no `services/`,
  `handlers/`) — Screaming Architecture: el listado de directorios debe anunciar de qué
  trata este proyecto, no qué framework usa.

## Consecuencias

- `environment.yml` y `utils/paths.py` se eliminan; `src/afg/shared/paths.py` reemplaza a
  este último, extendido con rutas específicas del dominio (decisiones gold, relaciones
  gold, preguntas).
- Las personas contribuyentes necesitan tener `uv` instalado; no hay alternativa con conda.
- Los directorios de solo datos (`data/`, `reports/`, `docs/`, `notebooks/`) ya no llevan
  archivos `__init__.py` — nunca fueron paquetes de Python y no debían aparentar serlo.

## Enmienda (2026-11-01)

Esta sección corrige la parte de la decisión que fija Python en **3.13**. El texto anterior no
se reescribe: queda como registro de lo que se decidió con la información de entonces.

- **El intérprete pasa a Python 3.14** (`.python-version`, `requires-python = ">=3.14,<3.15"`,
  objetivo de `ruff` y versión de `mypy`). La causa es que OpenKOS, el instrumento del
  [ADR 0006](0006-adr-c1-rag-separado-con-respuesta-de-openkos.md), solo admite Python 3.14 a
  partir de la versión 0.6.0.
- **Alternativa considerada y descartada:** instalar OpenKOS como herramienta aparte, con su
  propio intérprete 3.14, y dejar el proyecto en 3.13. Se descarta para mantener **un solo
  intérprete y un solo `uv.lock`** en todo el proyecto. C2 sigue invocando `openkos` como
  subproceso, ahora desde el mismo entorno.
- **Evidencia (2026-11-01):** con 3.14 el *lock* se resuelve cambiando únicamente `openkos`; la
  suite completa pasa (2112 pruebas), `ruff` y `mypy` pasan, el notebook 18 se ejecuta y la
  verificación de capacidades del adaptador acepta la 0.7.0 (`ingest --auto`, fecha de evento y
  `query --json`).
- El resto de la decisión (uv, `pyproject.toml` + `uv.lock`, organización `src/afg/`, extras)
  no cambia.
