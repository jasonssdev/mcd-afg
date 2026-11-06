# 0025. Una relación de oro no puede tener como extremo una decisión compuesta

## Estado

Aceptada (2026-11-06), por decisión de `jss`. Resuelve el [issue #298](https://github.com/jasonssdev/mcd-afg/issues/298), dentro de la [épica #288](https://github.com/jasonssdev/mcd-afg/issues/288). Corrige datos de la anotación de oro sin tocar el código congelado; **reemplaza el registro** de `config/freeze.json` por uno nuevo con este ADR (ver «Consecuencias»). Mantiene la regla del [ADR 0005](0005-adr-development-evaluation-split.md): la corrección se decide por el contenido de las decisiones, no por resultados.

## Contexto

La referencia de decisiones de cada serie solo contiene las decisiones hijas de una decisión `compuesta`: `load_reference` excluye al padre y lo reemplaza por sus filas `-1`, `-2`, ... (`src/afg/evaluation/reference.py`). En la Tarea B, sin embargo, **nueve relaciones aceptadas de las series de evaluación apuntaban al identificador del padre** y no al de una hija:

- ES2008: p009 y p013.
- ES2014: p010, p011, p012 (con dos extremos) y p014.
- ES2016: p001 y p002.
- IS1008: p007 (con dos extremos).

Son 9 relaciones y 11 extremos. Efectos:

- **C3.** `build_gold_workspace` ([ADR 0013](0013-adr-composicion-de-la-base-c3.md), regla 5) no encontraba el extremo y descartaba el enlace, informándolo en `c3-manifest.json`. Pero el ADR 0013 solo previó descartes por **evidencia ausente**, no por un extremo que nunca puede existir en la referencia. El límite superior de C3 quedaba sesgado a la baja.
- **Experimento A (relaciones).** `load_gold_pairs` y `_tally_case` (`src/afg/evaluation/relations.py`) conservaban esos enlaces como pares de oro. Ninguna decisión extraída se alinea con un padre ausente de la referencia, de modo que esos enlaces **no se podían alinear nunca** y el *recall* de relaciones quedaba sesgado a la baja.

El [notebook 27](../../notebooks/27-jss-relaciones-con-extremo-compuesto.ipynb) cuenta las relaciones aceptadas por serie (37 en total, sobre las once series de evaluación), muestra que tras la corrección ninguna tiene un extremo compuesto y lista las nueve reasignaciones. El test `tests/test_gold_relations_endpoints.py` fija el requisito: antes de la corrección falló en ES2008, ES2014, ES2016 e IS1008, y ahora pasa en las once series.

## Decisión

**Principio P1, «una relación, un enlace».** Cada relación se mantiene como un único enlace, y su extremo pasa a la hija que sostiene el contenido de las decisiones. Cuando las notas de la persona que anotó nombran la hija, la elección se ancla en ellas. Se conservan el `pair_id`, el tipo de relación y la dirección; los candidatos no se regeneran. En cada fila editada, la columna `razon` (archivo adjudicado) o `notes` (archivo de un anotador) lleva la marca «Extremo compuesto reasignado a la hija (X -> Y) por jss, issue #298, ADR 0025.».

| Par | Antes -> después | Criterio |
|---|---|---|
| ES2014.p010 | b.d04 -> b.d04-3 | la nota de `gm` nombra b.d04-3 |
| ES2014.p011 | b.d04 -> b.d04-9 | d.d07 nombra el botón de confirmación; la nota lista -6 a -9 y P1 conserva una |
| ES2014.p012 | c.d07 -> c.d07-1; d.d01 -> d.d01-1 | la nota de `gm` nombra ambas |
| ES2014.p014 | c.d02 -> c.d02-2 | la nota de `gm` nombra c.d02-2 |
| IS1008.p007 | b.d02 -> b.d02-2; c.d02 -> c.d02-5 | la nota de `gm` nombra ambas |
| ES2016.p001 | c.d03 -> c.d03-1 | mismo objeto, el desplazamiento; las notas mencionan también el chip, que es otro objeto |
| ES2016.p002 | c.d03 -> c.d03-2 | mismo objeto, el chip-on-print |
| ES2008.p013 | c.d07 -> c.d07-1 | d.d05 nombra el botón de encendido |
| ES2008.p009 | c.d07 -> c.d07-1 | **débil**: sin ancla textual; se elige la misma hija que en p013 por consistencia |

**ES2008.p009 se declara débil.** Su elección descansa en la consistencia con p013 y no en un texto; si en una revisión posterior se prefiere otra hija, el cambio exigiría un ADR nuevo.

Para que no vuelva a ocurrir, `tests/test_gold_relations_endpoints.py` falla si una relación aceptada de una serie de evaluación apunta a una decisión `compuesta`.

### Declaración sobre el momento

El Experimento A **ya se había corrido** cuando se encontró este defecto (corrida `experimento-a-formal`, congelamiento del [ADR 0024](0024-adr-hoja-oe4-autocontenida.md)): `a-relations`, `a-report` y C3 ya se habían calculado, y quien mantiene el repositorio **había visto algunas cifras agregadas**. La corrección **se motiva en el defecto de enlace** (un extremo que no puede existir en la referencia) y **el criterio de elección de cada hija es el contenido de las decisiones**, no el efecto sobre ninguna cifra. Este ADR no cita ni usa cifras de los experimentos.

## Alternativas descartadas

- **P2: enlazar todas las hijas que respaldan las notas.** Daría 19 enlaces en lugar de 9 y llevaría la referencia de 37 a 47 enlaces. Contradice el [ADR 0021](0021-adr-minimo-de-e3-segun-relaciones-disponibles.md), donde las hijas de una compuesta cuentan como una sola relación, y cambiaría el número de relaciones de evolución disponibles que fija el mínimo de E3.
- **Expandir el padre a sus hijas en el código.** Cambia `src/`, rompe el congelamiento ([ADR 0024](0024-adr-hoja-oe4-autocontenida.md), [ADR 0023](0023-adr-recongelamiento-tras-la-auditoria.md)), obligaría a repetir la extracción de unas 12 horas e inflaría los enlaces como P2.
- **Declararlo como limitación.** Dejaría el *recall* de relaciones del Experimento A y el límite superior de C3 sesgados a la baja por un defecto conocido y corregible con datos.

## Consecuencias

- **Nuevo registro de congelamiento.** Las huellas de la referencia de relaciones de ES2008, ES2014, ES2016 e IS1008 cambian, así que el registro anterior deja de corresponder a los archivos. El registro se vuelve a escribir con `afg freeze write --adr 0025`, ejecutado sobre `main` justo después de la fusión del PR de este ADR, en un PR posterior que agrega solo `config/freeze.json`; el commit congelado es esa fusión. El `config/freeze.json` del ADR 0024 se elimina en el PR de este ADR, como se hizo con el ADR 0024: mientras no exista el nuevo, el bloqueo impide cualquier corrida sobre evaluación.
- **La extracción `experimento-a-formal` sigue vigente.** No cambia nada de `src/`, `pyproject.toml`, `uv.lock` ni `.python-version`: `code_changes_since` sobre el commit congelado (`e346a4e`) devuelve una lista vacía, y la regla de los informes («mismo commit o sin diferencias de código») se cumple bajo el nuevo registro. No hay que repetir la extracción.
- **Se rehacen `a-relations` y `a-report`** sobre `experimento-a-formal`, y **se reconstruye C3** (`c3 build --overwrite`), porque ambos leen la anotación corregida. `a-relations` y `a-report` sobrescriben `relaciones.json` e `informe.json` en la carpeta de la corrida; los anteriores quedan en el historial de git (PR #297) y se declaran en el notebook del Experimento A (28).
- **El Experimento B espera** a esta corrección, porque C3 forma parte de su comparación.
- **El conteo de relaciones no cambia** (una relación, un enlace), de modo que el mínimo de E3 del ADR 0021 no se altera.
- **Regla de evidencia.** Este ADR se respalda en el notebook 27 y en el test de `tests/`, y no en una función nueva de `src/`: agregar código a `src/` cambiaría el código congelado y obligaría a repetir la extracción. El análisis usa solo funciones que ya existían.

## Respaldo

- Análisis: [`notebooks/27-jss-relaciones-con-extremo-compuesto.ipynb`](../../notebooks/27-jss-relaciones-con-extremo-compuesto.ipynb).
- Test: `tests/test_gold_relations_endpoints.py`.
- Datos: `data/processed/relations/ES2008.candidates.adjudicated.csv`, `ES2016.candidates.adjudicated.csv`, `ES2014.candidates.gm.csv` e `IS1008.candidates.gm.csv`.
- Issue: [#298](https://github.com/jasonssdev/mcd-afg/issues/298).
- Decisiones relacionadas: [ADR 0013](0013-adr-composicion-de-la-base-c3.md), [ADR 0021](0021-adr-minimo-de-e3-segun-relaciones-disponibles.md), [ADR 0023](0023-adr-recongelamiento-tras-la-auditoria.md), [ADR 0024](0024-adr-hoja-oe4-autocontenida.md).
