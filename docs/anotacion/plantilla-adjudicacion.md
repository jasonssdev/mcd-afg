# Plantilla del registro de adjudicación

> **Para qué.** Cada serie de doble anotación produce un archivo
> `data/processed/relations/<serie>.adjudication.md`. Esta plantilla existe para que los
> cinco salgan comparables entre sí.
>
> **Qué es esto hoy.** `uv run afg gold adjudicate --series <ID>` existe y escribe este
> archivo ya pre-llenado: calcula los tres kappas, encuentra los desacuerdos de la Tarea B
> y deja una fila por cada uno con las dos etiquetas puestas. Esta plantilla es, por lo
> tanto, en gran parte redundante con lo que el comando produce; se conserva como
> referencia del formato, no como instrucción para escribir el archivo a mano (ver
> [`asignacion/README.md`](asignacion/README.md) §5.3).
>
> **Qué sigue siendo manual.** Por cada fila de desacuerdo de la Tarea B, solo **etiqueta
> final** y **razón** (el comando ya puso las dos etiquetas de los anotadores). La tabla de
> desacuerdos de la Tarea A (`status`) el comando la deja completamente vacía: no hay
> función que calcule ese eje, así que se llena leyendo los dos archivos a mano, alineados
> por `decision_id` (ver [`asignacion/tareas-jss.md`](asignacion/tareas-jss.md) §2.4).
>
> **Quién lo escribe.** `jss`, que adjudica y no anota (`CONTRIBUTING.md` §1).
>
> **Cómo se usa.** Copia todo lo que está bajo la línea, reemplaza los `<marcadores>` y borra
> la fila de ejemplo.

---

# Adjudicación — `<SERIE>`

| | |
|---|---|
| **Serie** | `<SERIE>` |
| **Conjunto** | `<desarrollo / evaluación — control>` |
| **Fecha de la sesión** | `<AAAA-MM-DD>` |
| **Anotadores** | `gv` (Germán Vega), `gm` (Gustavo Martínez) |
| **Adjudicador** | `jss` (Jason Sepúlveda S.) |
| **Fase** | `<1 — calibración / 2 — serie de control>` |
| **¿Se reporta en la tesis?** | `<sí / no — la calibración es diagnóstica>` |

## Kappas

Salida de `uv run afg gold agreement --series <SERIE>`, tabla en
`reports/tables/<SERIE>.agreement.csv`. Los tres ejes van **por separado, nunca combinados**:
`existence` y `direction` pueden ser perfectos mientras `type` no lo es, y colapsarlos
escondería el modo de falla de H3 que la tesis mide.

| Eje | κ | Ítems | Desacuerdos |
|---|---:|---:|---:|
| Existencia del enlace | `<0,000>` | `<n>` | `<n>` |
| Tipo de relación | `<0,000 / n/a>` | `<n>` | `<n>` |
| Dirección | `<0,000>` | `<n>` | `<n>` |

- `type` puede salir `n/a` cuando ningún par fue marcado como enlace existente por las dos
  personas. No es un error: es el caso en que no hay nada cuyo tipo comparar.
- `type` se calcula **solo** sobre los pares que ambas marcaron como enlace existente.
- El kappa se reporta **tal como salga**. Un kappa bajo es el resultado que OE1 se propuso
  medir, no un fracaso a esconder (manual §6).

## Desacuerdos de la Tarea B — relaciones

Una fila por par de la lista que imprime el comando. La columna **Razón** es el contenido
real del registro: sin ella queda una lista de veredictos sin criterio, y el criterio es lo
que hay que poder aplicar igual en la serie siguiente.

| Par | Etiqueta de `gv` | Etiqueta de `gm` | Etiqueta final | Razón |
|---|---|---|---|---|
| `ES2015.p001` | `refina` | `reafirma` | `refina` | La posterior conserva el objeto (control de televisión) y **agrega** un límite que antes no estaba: función única, sin DVD ni VCR. `reafirma` exige que el contenido no cambie; aquí cambió por acotación, que es la definición de `refina`. |
| `<pair_id>` | `<etiqueta>` | `<etiqueta>` | `<etiqueta>` | `<por qué la final y no las otras dos>` |

> La fila de `ES2015.p001` es un **ejemplo ilustrativo**, sacado de ES2015, que es serie de
> desarrollo. Bórrala al usar la plantilla.

### Desacuerdos de dirección

Si `direction_ok` discrepó en algún par, va aquí aparte: una dirección invertida es una falla
distinta de una etiqueta equivocada, y la tesis las puntúa por separado (H3).

| Par | `direction_ok` de `gv` | `direction_ok` de `gm` | Final | Razón |
|---|---|---|---|---|
| `<pair_id>` | `<si / no>` | `<si / no>` | `<si / no>` | `<por qué>` |

## Desacuerdos de la Tarea A — `status` de las decisiones

**`afg gold agreement` no cubre esta tabla.** El comando busca
`f"{series}.candidates.*.csv"`, así que sus tres kappas son todos de la Tarea B; el acuerdo
sobre `status` se adjudica leyendo a mano los dos archivos, alineados por `decision_id`
(ver [`asignacion/tareas-jss.md`](asignacion/tareas-jss.md) §2.4).

| Decisión | `status` de `gv` | `status` de `gm` | `status` final | Razón |
|---|---|---|---|---|
| `<decision_id>` | `<status>` | `<status>` | `<status>` | `<por qué>` |

### Divisiones de filas `compuesta`

Cuando una persona dividió una frase en N hijas y la otra en M, los `decision_id` hijos no
coinciden y no hay nada que alinear. Se resuelve sobre la fila **madre** y se registra la
división final.

| Decisión madre | División de `gv` | División de `gm` | División final | Razón |
|---|---|---|---|---|
| `<decision_id>` | `<n hijas>` | `<m hijas>` | `<k hijas>` | `<por qué>` |

## Cierre — ¿revela esto un vacío de la guía?

Si dos personas competentes discreparon, la primera hipótesis es que **la guía no decidía el
caso**, no que una de las dos se equivocó. Es el punto de la sección 1.4 de la tesis: dos
equipos competentes obtuvieron kappa negativo sobre este mismo corpus, y no fue por
descuido.

Responde las tres, siempre, aunque la respuesta sea "no":

1. **¿Hay un patrón?** ¿Los desacuerdos se concentran en un par de etiquetas vecinas, en un
   tipo de frase, en una reunión concreta? Un desacuerdo aislado es ruido; tres en el mismo
   borde son un vacío.
   > `<respuesta>`

2. **¿Qué corrección concreta hace falta?** Cita el documento y la sección.
   > `<respuesta, o "ninguna">`

3. **¿Se corrigió antes de abrir la serie siguiente?** No se empieza la serie siguiente con
   la guía que produjo el desacuerdo.
   > `<sí / no aplica — enlace al PR de corrección>`

## Artefactos de esta sesión

- [ ] `data/processed/relations/<SERIE>.adjudication.md` (este archivo)
- [ ] `reports/tables/<SERIE>.agreement.csv`
- [ ] PR de corrección de la guía, si el cierre lo pidió: `<enlace o "no aplica">`
