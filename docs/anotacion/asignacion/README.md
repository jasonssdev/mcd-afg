# Asignación del trabajo de anotación — OE1

> **Qué es este documento.** La explicación en prosa del reparto: por qué las fases van en
> ese orden, por qué la calibración cae en ES2015, por qué se adjudica serie por serie y no
> al final. Es el razonamiento; no es donde se lee el estado.
>
> **Quién manda en el reparto concreto.** [`config/annotation.toml`](../../../config/annotation.toml)
> es la **única fuente de verdad** de quién anota qué serie, en qué fase, quién adjudica,
> quién escribe y valida el banco de preguntas, y quién hace la Tarea C. Es lo que leen
> `afg gold prepare`, `afg gold validate` y `afg gold status`. Si algo de este documento
> parece contradecir el archivo, gana el archivo y este documento tiene un error.
>
> **Dónde se ve el estado en vivo.** `uv run afg gold status` — no este documento, que es
> prosa y no se actualiza sola. Las cifras de §1 y §2 son una fotografía verificada contra
> `config/corpus.toml` y `config/annotation.toml`, útil para leer, no para programar contra
> ella.
>
> **Qué NO es.** No define qué cuenta como decisión ni qué significa cada relación. Eso vive
> en [`../annotation-guidelines.md`](../annotation-guidelines.md) y en
> [`../manual-anotacion-oe1.md`](../manual-anotacion-oe1.md), y esos documentos son la única
> fuente de verdad conceptual. Si algo de aquí parece contradecirlos, mandan ellos.
>
> **Idioma.** Español, como el resto de `docs/anotacion/` y por la misma razón declarada en
> [`../../../notebooks/README.md`](../../../notebooks/README.md): los lectores son el equipo
> y quienes revisan la tesis.
>
> **Si nunca has abierto este repositorio:** empieza por
> [`EMPIEZA-AQUI.md`](EMPIEZA-AQUI.md), no por aquí.

## Documentos personales

| Persona | Rol | GitHub | Documento |
|---|---|---|---|
| Germán Vega (`gv`) | Anotador; valida el banco de preguntas; Tarea C | [`Vega-German`](https://github.com/Vega-German) | [`tareas-gv.md`](tareas-gv.md) |
| Gustavo Martínez (`gm`) | Anotador; escribe el banco de preguntas | [`gmartinezbMCD`](https://github.com/gmartinezbMCD) | [`tareas-gm.md`](tareas-gm.md) |
| Jason Sepúlveda (`jss`) | Mantenedor; adjudica; no anota | [`jasonssdev`](https://github.com/jasonssdev) | [`tareas-jss.md`](tareas-jss.md) |

El reparto respeta las dos reglas del diseño (`CONTRIBUTING.md` §1): quien adjudica no
anota, y quien escribe el banco de preguntas no lo valida.

---

## 1. El volumen total, medido

Las 14 series de OE1 (`config/corpus.toml` `[oe1]`) tienen hoy sus dos insumos generados:
**343 decisiones** y **92 pares candidatos**, que es exactamente lo que declara
`config/corpus.toml` (`total_decisions = 343`, y los 92 candidatos del punto de operación
actual del bloqueador).

| Serie | Decisiones | Candidatos | Conjunto | Fase |
|---|---:|---:|---|---|
| ES2015 | 29 | 3 | desarrollo | 1 — calibración |
| ES2008 | 33 | 14 | evaluación / control | 2 |
| ES2016 | 24 | 4 | evaluación / control | 2 |
| IS1003 | 25 | 8 | evaluación / control | 2 |
| TS3005 | 29 | 11 | evaluación / control | 2 |
| IS1004 | 24 | 4 | desarrollo | 3 — `gv` |
| IS1006 | 17 | 1 | evaluación | 3 — `gv` |
| IS1009 | 20 | 1 | evaluación | 3 — `gv` |
| TS3003 | 31 | 6 | evaluación | 3 — `gv` |
| ES2002 | 28 | 9 | evaluación | 3 — `gv` |
| TS3009 | 24 | 4 | desarrollo | 3 — `gm` |
| TS3011 | 23 | 5 | evaluación | 3 — `gm` |
| IS1008 | 13 | 8 | evaluación | 3 — `gm` |
| ES2014 | 23 | 14 | evaluación | 3 — `gm` |
| **Total** | **343** | **92** | | |

---

## 2. Las cuatro fases, en orden temporal

Las fases son estrictamente secuenciales. No se empieza la 2 sin cerrar la 1.

### Fase 0 — Generación de insumos (hecha, `jss`)

Las 14 series ya tienen sus dos archivos de entrada, generados con:

```bash
uv run afg gold build      --series <ID>   # -> data/processed/decisions/<ID>.decisions.csv
uv run afg gold candidates --series <ID>   # -> data/processed/relations/<ID>.candidates.csv
```

No hay nada que hacer en esta fase. Si alguien vuelve a correr estos comandos sobre una
serie que ya tiene archivos de anotador con trabajo cargado, `afg gold build` y `afg gold
candidates` se niegan a regenerar la base: perder la división de una fila `compuesta` o
desalinear las columnas de máquina que `afg gold validate` compara contra la base rompería
la anotación de todo el mundo, no solo la de quien la cargó. Solo `--force` regenera, y
avisa qué archivos quedan desalineados.

### Fase 1 — Calibración sobre ES2015 (ambos anotadores)

`gv` y `gm` hacen **Tarea A y Tarea B sobre ES2015** (29 decisiones, 3 candidatos), por
separado y sin hablar entre ellos. Después se calcula el acuerdo y se adjudica en sesión
conjunta con `jss`.

**Por qué ES2015 y no una serie de control.** Porque **no se quema una serie de control
aprendiendo la guía.** ES2015 es serie de desarrollo y ya está contaminada por el piloto
(ADR [0005](../../decisions/0005-adr-development-evaluation-split.md): sus frases de
decisión se leyeron completas), así que gastarla en calibrar cuesta cero. Si en cambio se
calibrara sobre ES2008, el primer kappa —el peor, el que mide *"todavía no entendemos la
guía"*— sería un kappa reportable, y habría que reportarlo.

**Este kappa es diagnóstico y no se reporta en la tesis.** Su única función es responder:
¿entendimos los dos lo mismo? Si sale bajo, se corrige la guía **antes** de tocar una sola
serie de evaluación, y se vuelve a calibrar.

### Fase 2 — Series de control (ambos anotadores)

Las cuatro de `control_series`, **en este orden: ES2016 → IS1003 → TS3005 → ES2008**
(111 decisiones y 37 pares candidatos entre las cuatro). Ambas personas anotan las cuatro,
por separado.

El orden no es alfabético ni arbitrario: sube de menor a mayor volumen de candidatos
(4 → 8 → 11 → 14), para que la primera serie de control sea la más barata y la más cara
quede para cuando la guía ya se domina. `config/annotation.toml` guarda `phase2_series` en
ese mismo orden, y `afg gold setup` lo imprime así.

**Una serie a la vez, con adjudicación después de cada una** — ver §3.

**Estos kappas sí se reportan.** Son el 36,4 % del conjunto de evaluación que exige el ADR
0005 (4 de 11 series), y son la evidencia de confiabilidad de todo OE1. Se reportan tal como
salgan: un kappa bajo es el resultado que OE1 se propuso medir, no un fracaso a esconder
(manual §6).

### Fase 3 — Reparto individual (una sola anotación por serie)

Las nueve series restantes se reparten. Cada una la anota **una sola persona**; no hay
segunda anotación ni kappa.

| | Series (en orden de ejecución) | Decisiones | Candidatos |
|---|---|---:|---:|
| **Germán (`gv`)** | IS1004, IS1006, IS1009, TS3003, ES2002 | 120 | 21 |
| **Gustavo (`gm`)** | TS3009, TS3011, IS1008, ES2014 | 83 | 31 |

**Por qué Gustavo lleva menos decisiones.** Porque además escribe el **banco de preguntas**:
mínimo 100 preguntas (25 por estrato, `docs/propuesta.md` §5.5) a un ritmo estimado de ~5
minutos cada una. Germán las valida (~3 min cada una) y además hace la **Tarea C**. El
reparto equilibra horas totales, no filas.

### Carga total por persona

| | Decisiones | Candidatos | Además |
|---|---:|---:|---|
| **`gv`** | 260 | 61 | Tarea C (50 pares) + validación del banco (≥100 preguntas) |
| **`gm`** | 223 | 71 | Escritura del banco (≥100 preguntas) |
| **`jss`** | 0 | 0 | Adjudicación de las 5 series dobles, los `.adjudication.md`, notebook 03 |

(260 = 29 de Fase 1 + 111 de Fase 2 + 120 de Fase 3. 223 = 29 + 111 + 83.)

---

## 3. ¿Cuándo se adjudica?

> **Después de cada serie de doble anotación, no al final.**

Es decir: se cierra ES2015, se adjudica ES2015, y solo entonces empieza ES2016. Se cierra
ES2016, se adjudica ES2016, y solo entonces empieza IS1003. Y así con las cinco series de
doble anotación, en orden: **ES2015 → ES2016 → IS1003 → TS3005 → ES2008**.

**La razón.** Un malentendido sistemático de la guía —dos personas que interpretan `refina`
de forma distinta, o que discrepan sobre cuándo una frase es `compuesta`— no se manifiesta
en una fila: se manifiesta en un patrón. Adjudicar al final significa descubrir ese patrón
**después** de haber anotado dos veces las 140 decisiones de las cinco series dobles, y
tener que rehacerlas. Adjudicar por serie lo descubre después de la primera, cuando corregir
cuesta 29 filas.

Es el mismo argumento de §1.3 de la tesis sobre el costo de persistir un error, aplicado al
propio procedimiento de anotación: cuanto más tarde se detecta, más caro sale.

**Qué produce cada sesión de adjudicación:**

1. `uv run afg gold adjudicate --series <ID>` escribe
   `data/processed/relations/<serie>.adjudication.md`, ya con los tres kappas, la fecha, los
   dos anotadores y una fila por cada desacuerdo de la Tarea B con ambas etiquetas puestas.
   `jss` solo llena **etiqueta final** y **razón** de cada fila, más la tabla de la Tarea A
   (ver §5.3).
2. `uv run afg gold agreement --series <ID>` escribe además
   `reports/tables/<serie>.agreement.csv`, la tabla de los tres kappas como artefacto aparte
   — `adjudicate` calcula los mismos números para el `.md`, pero no escribe este CSV.
3. Si el desacuerdo revela un vacío de la guía: una corrección explícita de
   `annotation-guidelines.md` o del manual, en su propio PR, **antes** de seguir.

---

## 4. Reglas comunes a todas las personas

Estas valen para `gv` y `gm` por igual, en las tres fases.

1. **La evidencia antes que el resumen.** Se lee `evidence_text` antes de llenar nada. Si la
   evidencia no dice lo que dice `sentence_text`, el `status` es `sin_soporte` (manual §2).
2. **`evidence_da_count = 0` es sospecha inmediata**, no un hueco menor. Se busca la
   evidencia con `uv run afg gold evidence --meeting <ID> --term <palabra>` antes de decidir.
3. **Orden cronológico dentro de la serie: `a → b → c → d`.** Al juzgar una decisión no se
   miran reuniones posteriores (regla anti-fuga, §5.1 de la tesis).
4. **Independencia durante las Fases 1 y 2.** Las dos personas no comparan etiquetas ni
   discuten casos concretos hasta la sesión de adjudicación. Si lo hacen, el kappa deja de
   medir acuerdo y pasa a medir conversación.
5. **La transcripción sí se puede leer.** Está en `data/interim/transcripts/<reunion>.md` y
   el anotador debe consultarla: anotar el conjunto de referencia exige leer la evidencia.
   La regla de alcance de `notebooks/README.md` restringe el **análisis exploratorio**, no la
   anotación. Ver el detalle en cada documento personal.
6. **Las etiquetas las pone una persona** (`CONTRIBUTING.md` §7.6). `machine_flags` es una
   sugerencia de triaje; `status` y `relation` no se copian de ahí nunca.
7. **Una serie por PR.** Fork → rama `data/anotacion-<serie>` → PR contra `main`, revisado
   por el mantenedor (`CONTRIBUTING.md` §2 y §3). No se juntan varias series en un PR: un PR
   por serie permite detectar deriva de criterio temprano, cuando corregirla es barata.
8. **Lo que no encaja se escribe, no se descarta en silencio.** Va a `notes` y a un issue con
   la plantilla "Hallazgo".

---

## 5. Qué automatiza la herramienta hoy, y qué sigue siendo manual

Dos limitaciones que este mismo documento documentaba ya están resueltas en el código; se
dejan registradas igual, para que quede claro qué cambió y cuándo. La tercera sigue en pie,
verificada de nuevo al escribir esto.

### 5.1 Resuelto: nombrar los archivos ya no es trabajo manual

Antes no existía convención de nombre para la Tarea A y cada quien copiaba y renombraba a
mano — tres oportunidades de escribirlo mal por archivo. Hoy `uv run afg gold prepare
--annotator <iniciales>` crea directamente:

```
data/processed/decisions/<serie>.decisions.<iniciales>.csv
data/processed/relations/<serie>.candidates.<iniciales>.csv
```

con las iniciales de `CONTRIBUTING.md` §1 (`gv`, `gm`), en Fase 3 también aunque solo anote
una persona. Nadie copia ni renombra un CSV a mano; el archivo sin iniciales
(`<serie>.decisions.csv`, `<serie>.candidates.csv`) es el insumo limpio que generan
`afg gold build` y `afg gold candidates`, y **no se edita nunca** — `afg gold validate` lo
verifica columna por columna.

### 5.2 Sigue siendo manual: el acuerdo de la Tarea A

Verificado de nuevo en `src/afg/annotation/agreement.py`: `compute_series_agreement` deriva
sus tres ejes —existencia, tipo, dirección— exclusivamente de las columnas `relation` y
`direction_ok` de `<serie>.candidates.*.csv`. No hay ninguna función equivalente para la
columna `status` de la Tarea A, y `afg gold adjudicate` (§5.3) llama a la misma función:
tampoco calcula ese eje.

**Consecuencia operativa, sin cambios:** en las series de doble anotación, la Tarea A se
adjudica **leyendo los dos archivos a mano**, fila por fila, comparando `status` alineado por
`decision_id` (detalle del procedimiento en
[`tareas-jss.md`](tareas-jss.md) §2.4). `afg gold adjudicate` deja la tabla de la Tarea A
dentro del `.adjudication.md` generado, vacía y con esta misma explicación escrita adentro —
no por descuido, porque no hay nada que calcular todavía.

### 5.3 Resuelto: el registro de adjudicación ya no se escribe a mano

`build_adjudication_log()` existía en `src/afg/annotation/agreement.py`, con tests, pero
nadie la invocaba desde el CLI. Hoy sí:

```bash
uv run afg gold adjudicate --series <ID>
```

Escribe `data/processed/relations/<serie>.adjudication.md` con la fecha, los dos anotadores,
el adjudicador, los tres kappas y una fila por cada desacuerdo de la Tarea B —relación y
dirección— con las dos etiquetas ya puestas. El humano llena exactamente dos celdas por fila,
**etiqueta final** y **razón**, más la tabla de la Tarea A que §5.2 explica por qué queda
vacía. Se niega a regenerar un archivo que ya tenga resoluciones escritas a mano, salvo
`--force`.

---

## 6. Artefactos que produce este plan

Las tres primeras filas las crea `afg gold prepare` (columnas humanas vacías); las llena la
persona; `afg gold validate` verifica el resultado.

| Archivo | Quién | Cuándo |
|---|---|---|
| `data/processed/decisions/<serie>.decisions.<iniciales>.csv` | `gv`, `gm` | Tarea A de cada serie |
| `data/processed/relations/<serie>.candidates.<iniciales>.csv` | `gv`, `gm` | Tarea B de cada serie |
| `data/processed/relations/IS1004.recall-sample.<iniciales>.csv` (adjudicado) | `gv` | Tarea C |
| `data/processed/relations/<serie>.adjudication.md` | `afg gold adjudicate` escribe, `jss` completa | Tras cada serie doble |
| `reports/tables/<serie>.agreement.csv` | `afg gold agreement` | Tras cada serie doble |
| `data/processed/questions/banco-preguntas.csv` | `afg gold questions-init` crea, `gm` escribe, `gv` valida | Banco de preguntas |
| `notebooks/03-jss-anotacion-oe1.ipynb` | `jss` | Al cerrar OE1 |
