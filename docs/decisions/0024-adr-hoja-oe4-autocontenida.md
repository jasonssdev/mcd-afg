# 0024. La hoja de OE4 trae los textos de los objetos y pasa a ser autocontenida

## Estado

Aceptada (2026-11-05), por decisión de `jss`. **Reemplaza al [ADR 0023](0023-adr-recongelamiento-tras-la-auditoria.md)** y resuelve de nuevo el [issue #237](https://github.com/jasonssdev/mcd-afg/issues/237), que ya estaba cerrado: el registro del congelamiento se reescribe y el issue sigue cerrado. Mantiene la regla del [ADR 0005](0005-adr-development-evaluation-split.md): nada se ajusta ya con las series de evaluación. La decisión se toma **antes de que exista cualquier corrida formal**.

## Contexto

Al revisar las guías para las personas que etiquetan se encontró que la hoja de OE4 no era autocontenida. Las columnas `mejor_objeto` y `objetos_de_la_base` listaban identificadores de objetos y su cobertura, pero el texto de esos objetos vive en la base compilada de C2 (`data/interim/openkos/`), que está fuera de git y solo existe en la máquina de quien mantiene el repositorio. `gm`, que debe decidir si el dato «está en la base», no podía leerlo con lo que recibe.

**No existe ninguna corrida formal, de modo que ningún resultado se invalida.** El defecto es de la hoja, no de ninguna cifra.

## Decisión

La hoja de OE4 (`afg experiment b-oe4-sheet`) agrega tres columnas, sin cambiar el orden de las filas ni las demás columnas:

- **`mejor_objeto_texto`**: el texto completo del objeto de `mejor_objeto`, sin el encabezado de metadatos ni los enlaces `## Related`.
- **`objetos_de_la_base_texto`**: los textos de los mismos tres objetos de `objetos_de_la_base`, cada uno precedido por su identificador (`id: texto`) y separados por ` || `.
- **`mejor_fuente_fragmento`**: el pasaje de la transcripción en bruto de `mejor_fuente` con más cobertura de la referencia (hasta tres líneas seguidas, máximo 600 caracteres), para poder decidir `extraccion` sin abrir el espacio de trabajo.

Todo lo demás del ADR 0023 **sigue vigente tal como está** (qué se congela, análisis y hojas, verificación contra el registro, validación manual de la alineación, roles y ciegos, fallas y repeticiones, regla de no cambiar lo congelado). El ADR 0023 deja de regir solo como fuente del registro: el congelamiento se escribe con este ADR.

El commit congelado es **el commit de fusión del PR de este ADR en `main`**. Se registra con `uv run afg freeze write --adr 0024`, ejecutado sobre `main` justo después de esa fusión, en un PR posterior que agrega solo `config/freeze.json`. El `config/freeze.json` del ADR 0023 se elimina en el PR de este ADR (ya no corresponde al código): mientras no exista el nuevo, el bloqueo impide cualquier corrida sobre evaluación.

## Consecuencias

- **Ninguna cifra cambia.** La hoja trae más columnas, pero la regla de atribución, el banco y la configuración son los mismos.
- **`gm` etiqueta solo con la hoja.** La guía deja de pedir que se abra `data/interim/openkos/`.
- **La hoja pesa más** (tres columnas de texto por fila, hasta 75 filas); es lo que cuesta no depender de la máquina del mantenedor.
- **Un congelamiento más**, el tercero, antes de la primera corrida; no hay nada que rehacer porque no se corrió nada.

## Respaldo

- Código: `oe4_worksheet_rows` y `WORKSHEET_COLUMNS` en `src/afg/experiments/c2_base_evidence.py`.
- Tests: `tests/test_c2_base_evidence.py` (`test_worksheet_carries_the_object_texts_so_it_is_self_contained`, `test_worksheet_texts_are_empty_without_objects_and_sources`, `test_source_fragment_is_the_passage_with_most_coverage_and_is_capped`).
- Guía para la persona que etiqueta: [`etapa-oe4.md`](../anotacion/etapa-oe4.md).
- Protocolo: [`docs/protocols/congelamiento.md`](../protocols/congelamiento.md).
- Registro: `config/freeze.json`, que se agrega en el PR posterior a la fusión de este ADR.
