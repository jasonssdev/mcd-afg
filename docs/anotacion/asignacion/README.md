# Asignación del trabajo de anotación — OE1

> **Qué es este documento.** El plan maestro del reparto: quién anota qué serie, en qué
> orden, cuándo se adjudica y qué limitaciones conocidas tiene hoy la herramienta.
>
> **Qué NO es.** No define qué cuenta como decisión ni qué significa cada relación. Eso vive
> en [`../annotation-guidelines.md`](../annotation-guidelines.md) y en
> [`../manual-anotacion-oe1.md`](../manual-anotacion-oe1.md), y esos documentos son la única
> fuente de verdad conceptual. Si algo de aquí parece contradecirlos, mandan ellos.
>
> **Idioma.** Español, como el resto de `docs/anotacion/` y por la misma razón declarada en
> [`../../../notebooks/README.md`](../../../notebooks/README.md): los lectores son el equipo
> y quienes revisan la tesis.

## Documentos personales

| Persona | Rol | Documento |
|---|---|---|
| Germán Vega (`gv`) | Anotador; valida el banco de preguntas; Tarea C | [`tareas-gv.md`](tareas-gv.md) |
| Gustavo Martínez (`gm`) | Anotador; escribe el banco de preguntas | [`tareas-gm.md`](tareas-gm.md) |
| Jason Sepúlveda (`jss`) | Mantenedor; adjudica; no anota | [`tareas-jss.md`](tareas-jss.md) |

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

No hay nada que hacer en esta fase. Nadie vuelve a correr estos comandos sobre una serie ya
anotada: regenerarla borra el trabajo humano.

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

Las cuatro de `control_series`: **ES2008, ES2016, IS1003, TS3005** (111 decisiones y 37
pares candidatos entre las cuatro). Ambas personas anotan las cuatro, por separado.

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

Es decir: se cierra ES2015, se adjudica ES2015, y solo entonces empieza ES2008. Se cierra
ES2008, se adjudica ES2008, y solo entonces empieza ES2016. Y así con las cinco series de
doble anotación (ES2015 + las cuatro de control).

**La razón.** Un malentendido sistemático de la guía —dos personas que interpretan `refina`
de forma distinta, o que discrepan sobre cuándo una frase es `compuesta`— no se manifiesta
en una fila: se manifiesta en un patrón. Adjudicar al final significa descubrir ese patrón
**después** de haber anotado dos veces las 140 decisiones de las cinco series dobles, y
tener que rehacerlas. Adjudicar por serie lo descubre después de la primera, cuando corregir
cuesta 29 filas.

Es el mismo argumento de §1.3 de la tesis sobre el costo de persistir un error, aplicado al
propio procedimiento de anotación: cuanto más tarde se detecta, más caro sale.

**Qué produce cada sesión de adjudicación:**

1. La salida de `uv run afg gold agreement --series <ID>` (los tres kappas).
2. Un archivo `data/processed/relations/<serie>.adjudication.md`, escrito por `jss` a partir
   de [`../plantilla-adjudicacion.md`](../plantilla-adjudicacion.md).
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

## 5. Tres limitaciones conocidas de la herramienta

No están escondidas porque afectan al procedimiento, y el procedimiento tiene que
compensarlas a mano.

### 5.1 La Tarea A de doble anotación no tenía convención de nombre — se fija aquí

El manual (§6) solo define el patrón de la Tarea B:
`<serie>.candidates.<iniciales>.csv`. Para la Tarea A no existía nombre.

**Convención nueva, a partir de este documento:**

```
data/processed/decisions/<serie>.decisions.<iniciales>.csv
```

Patrón espejo del de la Tarea B, mismas iniciales de `CONTRIBUTING.md` §1 (`gv`, `gm`). El
archivo sin iniciales (`<serie>.decisions.csv`) queda como el insumo limpio generado por
`afg gold build` y **no se edita nunca**: cada persona parte de una copia con su sufijo.

En Fase 3, donde solo anota una persona, se usa igualmente el sufijo
(`IS1006.decisions.gv.csv`), para que el nombre diga siempre quién puso las etiquetas.

### 5.2 `afg gold agreement` no calcula el kappa de la Tarea A

El comando busca únicamente pares candidatos:

```python
pattern = f"{series}.candidates.*.csv"
paths = sorted(GOLD_RELATIONS_DIR.glob(pattern))
```

(`src/afg/cli.py`, comando `gold agreement`). Es decir: los tres kappas que calcula
—existencia, tipo y dirección— son **todos de la Tarea B**. **El acuerdo sobre `status` de
la Tarea A no lo calcula el CLI hoy.**

**Consecuencia operativa:** en las series de doble anotación, la Tarea A se adjudica
**leyendo los dos archivos a mano**, fila por fila, comparando la columna `status`. `jss`
registra los desacuerdos en el mismo `.adjudication.md`, en su propia tabla. Cuando exista el
comando, se recalculará sobre los archivos ya guardados —por eso la convención de §5.1
importa: los archivos tienen que estar ahí y con el nombre correcto.

### 5.3 No existe comando que escriba `<serie>.adjudication.md`

La función `build_adjudication_log()` existe en `src/afg/annotation/agreement.py` y tiene
tests (`tests/test_annotation.py`), pero **nadie la invoca desde el CLI**: no hay
`afg gold adjudicate`. El archivo de adjudicación se escribe hoy **a mano**.

Para que los cinco archivos salgan comparables entre sí, se escriben desde la plantilla:
[`../plantilla-adjudicacion.md`](../plantilla-adjudicacion.md).

---

## 6. Artefactos que produce este plan

| Archivo | Quién | Cuándo |
|---|---|---|
| `data/processed/decisions/<serie>.decisions.<iniciales>.csv` | `gv`, `gm` | Tarea A de cada serie |
| `data/processed/relations/<serie>.candidates.<iniciales>.csv` | `gv`, `gm` | Tarea B de cada serie |
| `data/processed/relations/IS1004.recall-sample.csv` (adjudicado) | `gv` | Tarea C |
| `data/processed/relations/<serie>.adjudication.md` | `jss` | Tras cada serie doble |
| `reports/tables/<serie>.agreement.csv` | `afg gold agreement` | Tras cada serie doble |
| `data/processed/questions/banco-preguntas.csv` | `gm` escribe, `gv` valida | Banco de preguntas |
| `notebooks/03-jss-anotacion-oe1.ipynb` | `jss` | Al cerrar OE1 |
