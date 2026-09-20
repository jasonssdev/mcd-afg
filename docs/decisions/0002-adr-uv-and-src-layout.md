# 0002. Usar uv y una organización src/, reemplazando el entorno conda

## Estado

Aceptada

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
