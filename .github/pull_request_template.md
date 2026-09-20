<!--
Completa cada sección. Un PR incompleto no se revisa.
Ver CONTRIBUTING.md para las convenciones del proyecto.
-->

## Qué cambia y por qué

<!-- Descripción breve del cambio y la motivación. -->

## Issue que cierra

Closes #

## Respaldo en notebook

<!--
CONTRIBUTING.md §7.1: "Código sin notebook no es un registro." Si este cambio
produce un número, una decisión o un entregable, tiene que poder leerse desde
un notebook en notebooks/.
-->

- [ ] Notebook que cubre este cambio: `notebooks/NN-jss-....ipynb`
- [ ] No aplica ningún notebook — justificación explícita:

## Verificación

Ejecuta cada comando y pega el resultado observado (no basta con marcar la casilla).

- [ ] `uv run pytest -q`
- [ ] `uv run ruff check .`
- [ ] `uv run mypy src/afg`
- [ ] Si se tocó un notebook, se re-ejecutó de punta a punta:
      ```bash
      uv run jupyter nbconvert --to notebook --execute --inplace \
        --ExecutePreprocessor.timeout=900 notebooks/<archivo>.ipynb
      ```

## Si cambiaron cifras

<!--
CONTRIBUTING.md §7.5: una cifra corregida se corrige en TODOS los lugares
donde aparece. Lista cada archivo actualizado; si ninguna cifra cambió, dilo.
-->

- [ ] No cambió ninguna cifra.
- [ ] Cambió una o más cifras. Dónde más aparecía cada una, y dónde se actualizó:

## Alcance desarrollo/evaluación

<!-- ADR 0005 — docs/decisions/0005-adr-development-evaluation-split.md -->

- [ ] Confirmo que no se leyó ni citó **contenido** del conjunto de evaluación
      (textos de decisiones, pares candidatos, transcripciones fuera de
      desarrollo: ES2015, IS1004, TS3009).

## Etiquetas del conjunto de referencia

<!-- CONTRIBUTING.md §7.6: las etiquetas del gold set las pone un humano, nunca un modelo. -->

- [ ] Confirmo que ninguna etiqueta producida por una máquina entró al camino
      de la referencia (columna `status`, nunca `machine_flags`).

## Checklist final

- [ ] El PR no incluye notas de herramientas ni coautores automáticos; la autoría es la de quien firma (CONTRIBUTING.md, Autoría).
- [ ] Los nombres de archivo siguen la convención del directorio correspondiente (`notebooks/`, `docs/avances/`, `docs/decisions/`).
- [ ] El idioma de cada artefacto sigue CONTRIBUTING.md §7.4.
