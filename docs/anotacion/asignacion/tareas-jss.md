# Tareas de Jason Sepúlveda (`jss`)

> **Tu papel es distinto.** No anotas ninguna fila. Generas los insumos, adjudicas los
> desacuerdos de la doble anotación en los CSV de adjudicación, verificas que
> ninguna etiqueta de máquina se coló en el conjunto de referencia, y cierras OE1 con el
> notebook 03. Que quien adjudica no anote es una regla del diseño
> (`CONTRIBUTING.md` §1): si adjudicaras tus propias etiquetas, las finales quedarían
> sesgadas hacia uno de los tres.

## Tu encargo en una frase

Cerrar el bucle de calidad de OE1: adjudicar las cinco series de doble anotación una por
una, dejar cada veredicto registrado en un CSV con su razón, y garantizar que ninguna etiqueta del
conjunto de referencia la haya puesto una máquina.

## Tu día a día en tres comandos

```bash
uv run afg gold status                                 # avance de todo el equipo, sin abrir un CSV
uv run afg gold adjudicate --series <ID>                # tras cada serie doble: escribe los dos CSV de adjudicación
uv run afg gold validate --annotator <iniciales>        # en cada PR, antes de aprobarlo
uv run afg gold validate-adjudication --series <ID>     # al terminar de adjudicar: ¿quedó todo con veredicto y razón?
```

`status` es tu panel: una fila por persona y serie, con fase, avance de las dos tareas y si
pasa la validación — así sabes cuándo una serie doble ya tiene los cuatro archivos listos
para adjudicar, sin entrar a `data/processed/`. `adjudicate` escribe los dos CSV de
adjudicación (§3) con las respuestas de las dos personas lado a lado, ya prellenados donde
coinciden: tú completas el veredicto final y la razón donde discrepan. `validate --annotator <iniciales>` (sin
`--series`, para revisar el PR entero) es la mitad mecánica de la verificación de §4: confirma
que las columnas de máquina llegaron intactas y que los valores son legales, antes de que tú
revises a ojo lo que ningún comando puede juzgar.

---

## 1. Fase 0 — Generación de insumos (hecha)

Las 14 series de `config/corpus.toml` `[oe1]` ya tienen sus dos archivos de entrada,
generados con:

```bash
uv run afg gold build      --series <ID>   # -> data/processed/decisions/<ID>.decisions.csv
uv run afg gold candidates --series <ID>   # -> data/processed/relations/<ID>.candidates.csv
```

Total medido: **343 decisiones y 92 pares candidatos**, coincidente con
`config/corpus.toml` (`total_decisions = 343`). El desglose por serie está en
[`README.md`](README.md) §1.

**Nada que hacer aquí, y una prohibición:** no se vuelve a correr `gold build` ni
`gold candidates` sobre una serie ya anotada. Regenerarla sobrescribe el insumo y, si
alguien estaba trabajando sobre una copia derivada, deja dos archivos que ya no se pueden
alinear por `pair_id`.

---

## 2. Adjudicación, serie por serie

**Se adjudica después de cada serie de doble anotación, no al final** ([`README.md`](README.md)
§3). Son cinco sesiones: ES2015 (calibración), y luego ES2016, IS1003, TS3005, ES2008.

### 2.1 Requisitos para abrir una sesión

- Los dos PRs de esa serie están mergeados: `<serie>.decisions.gv.csv`,
  `<serie>.candidates.gv.csv`, `<serie>.decisions.gm.csv`, `<serie>.candidates.gm.csv`.
- Los cuatro archivos están completos: ninguna celda humana vacía. `uv run afg gold status`
  te lo confirma de un vistazo: la serie tiene que aparecer como **completa** para `gv` y
  para `gm`; "en curso" o "sin preparar" significa que todavía falta trabajo.
- Ninguna de las dos personas ha visto el archivo de la otra.

### 2.2 El comando

```bash
uv run afg gold agreement --series ES2015
```

Lee todos los `data/processed/relations/ES2015.candidates.*.csv` y escribe
`reports/tables/ES2015.agreement.csv`.

**Qué imprime y qué hacer con cada cosa:**

| Salida | Qué es | Qué haces |
|---|---|---|
| `existence kappa` | ¿Hay relación, sí o no? Derivado de `relation`: todo lo distinto de `no_relacionada` cuenta como enlace existente | Lo anotas para el reporte de la serie |
| `type kappa` | La etiqueta concreta, **solo sobre los pares que ambas personas marcaron como enlace existente** | Lo anotas. Puede salir `n/a` si ningún par fue marcado como enlace por los dos: no es un error |
| `direction kappa` | El valor de `direction_ok`, sobre todos los pares emparejados | Lo anotas |
| `... disagreements (adjudicate): <pair_ids>` | La lista exacta de pares a resolver | **Es tu orden del día**; los mismos pares aparecen con `acuerdo = no` en el CSV de candidatos |
| `Wrote reports/tables/<serie>.agreement.csv` | La tabla con los tres ejes | Entra al PR de adjudicación junto con los dos CSV |

Los tres kappas se reportan **por separado, nunca combinados en uno**: `existence` y
`direction` pueden ser perfectos mientras `type` no lo es, y colapsarlos escondería
exactamente el modo de falla de H3 que la tesis mide (`agreement.py`,
`SeriesAgreementResult`).

**Los kappas viven solo aquí**: `afg gold adjudicate --series <ID>` (§3) no los calcula ni los
escribe. `agreement` deja `reports/tables/<serie>.agreement.csv` como artefacto versionado, y
los CSV de adjudicación quedan sin kappas a propósito: son el conjunto de referencia, no un
reporte.

**Errores que puede devolver el comando** (`AgreementInputError`, y el chequeo previo del
CLI):

- *"Need at least 2 annotator files…"* — falta un archivo, o su nombre no sigue
  `<serie>.candidates.<iniciales>.csv`. Es de nombre, no de contenido.
- *"share no pair_id in common"* — alguien editó la columna `pair_id`, o trabajó sobre un
  insumo regenerado. Hay que volver al insumo original.
- Si aparecen **más de dos** archivos de anotador, el comando avisa y usa los dos primeros por
  orden alfabético, porque el kappa de Cohen es por pares. Con `gv` y `gm` no debería ocurrir.
  Los archivos `*.adjudicated.csv` nunca cuentan como anotador: `agreement` los excluye
  explícitamente, así que puede correrse antes o después de `adjudicate`.

### 2.3 Los kappas de calibración no se reportan

El de ES2015 es **diagnóstico**: responde "¿entendimos los dos lo mismo?" y no entra en la
tesis. Si sale bajo, se corrige `annotation-guidelines.md` o el manual —en su propio PR—
**antes** de tocar ES2016, y se recalibra. Los cuatro kappas de las series de control sí se
reportan, tal como salgan: son el 36,4 % del conjunto de evaluación que exige el
ADR [0005](../../decisions/0005-adr-development-evaluation-split.md).

### 2.4 La Tarea A se adjudica sobre el CSV

`compute_series_agreement` deriva sus tres ejes solo de `relation` y `direction_ok`
(`src/afg/annotation/agreement.py`; [`README.md`](README.md) §5.2): no existe un kappa para
`status`. Eso ya no obliga a leer los dos archivos de decisiones en paralelo. El CSV de
decisiones de §3 trae, por cada decisión base, el `status`, el objeto, el contenido y las
notas de cada persona **en la misma fila**, y la columna `acuerdo` ya dice dónde coinciden.
La lista de desacuerdos de la Tarea A es simplemente filtrar `acuerdo = no`.

Las filas `compuesta` se alinean por la fila **madre**. Si una persona dividió una frase en
tres hijas y la otra en cuatro, los `decision_id` hijos no coinciden; por eso cada persona
trae una columna `<iniciales>_split` con un resumen de sus hijas y la fila cuenta como
desacuerdo (§3).

---

## 3. Los CSV de adjudicación

**Ya no se escribe a mano ni en Markdown.** La adjudicación son dos CSV con las respuestas de
las dos personas lado a lado y tu veredicto al final. Son el **conjunto de referencia legible
por código**: C3, el banco de preguntas y la medición de C2 leen `final_*`, no un documento.

```bash
uv run afg gold adjudicate --series ES2015
```

Escribe, sin tocar nada más:

- `data/processed/decisions/ES2015.decisions.adjudicated.csv` — una fila por decisión
  **base** de `ES2015.decisions.csv`.
- `data/processed/relations/ES2015.candidates.adjudicated.csv` — una fila por `pair_id`.

El sufijo es siempre `adjudicated`, nunca unas iniciales: quién adjudicó va en la columna
`adjudicator`. Por eso `agreement`, `status`, `validate` y `prepare` los excluyen de toda
búsqueda de archivos de anotador.

**Columnas de decisiones**, en este orden: `decision_id`, `meeting_id`, `source_sentence_id`,
`sentence_text`, `evidence_text`; luego, por cada persona (orden alfabético de iniciales),
`<ini>_status`, `<ini>_object`, `<ini>_content`, `<ini>_notes`, `<ini>_split`; y al final
`acuerdo`, `final_status`, `final_object`, `final_content`, `razon`, `adjudicator`.

**Columnas de candidatos**: `pair_id`, `earlier_decision_id`, `later_decision_id`,
`earlier_text`, `later_text`, `blocker_score`; por persona, `<ini>_relation`,
`<ini>_direction_ok`, `<ini>_confidence`, `<ini>_notes`; y `acuerdo`, `final_relation`,
`final_direction_ok`, `razon`, `adjudicator`.

**`acuerdo`.** En decisiones es `si` cuando los dos `status` son iguales y ninguno es
`compuesta`, o cuando los dos son `compuesta` con **los mismos `status` en las filas hijas, en
el mismo orden**; en cualquier otro caso es `no`. En candidatos es `si` solo si `relation` y
`direction_ok` coinciden en ambos. Una fila que nadie respondió no es acuerdo.

**Qué viene prellenado.** Solo donde `acuerdo = si`: `final_status` (o `final_relation` y
`final_direction_ok`) con el valor en que las dos personas coinciden, `final_object` y
`final_content` copiados de la primera persona en orden alfabético, y `adjudicator` con el
adjudicador de `config/annotation.toml`. `razon` queda vacía. Donde `acuerdo = no`, **todo
`final_*`, `razon` y `adjudicator` quedan vacíos**: la máquina copia una etiqueta en la que
dos humanos ya coinciden, nunca elige entre dos que discrepan.

**Qué llenas tú.**

1. En cada fila con `acuerdo = no`: el veredicto `final_*`, la `razon` y tus iniciales en
   `adjudicator`. La razón es el contenido real del archivo: sin ella, es una lista de
   veredictos sin criterio, y el criterio es lo que hay que poder aplicar igual en la serie
   siguiente.
2. En las filas con acuerdo, revisa el prellenado y cámbialo si hace falta; si dejas un
   `sin_soporte` la razón sigue siendo obligatoria.
3. Si dictaminas una fila `compuesta` (haya acuerdo o no), agrega **debajo de la fila madre**
   las filas hijas con ids `<id_base>-1`, `<id_base>-2`, ..., y llena `final_*` en cada una
   (`decision_id`, `acuerdo` y las columnas de anotador de las hijas pueden quedar vacías).
   Una `compuesta` final exige al menos dos hijas consecutivas.

```bash
uv run afg gold validate-adjudication --series ES2015
```

Falla con código distinto de cero y dice fila y columna de cada pendiente: veredicto ausente
o fuera del conjunto cerrado, `decision` sin `final_object`/`final_content`, `razon` ausente
donde hubo desacuerdo o el veredicto es `sin_soporte`, `adjudicator` vacío, o una `compuesta`
sin hijas.

`adjudicate` se niega a regenerar cualquiera de los dos archivos si alguna fila tiene una
`razon` escrita o un `final_*` distinto del prellenado, salvo `--force`, que descarta el
criterio ya registrado igual que `prepare --force` descarta anotación. Necesita que los dos
PRs de esa serie estén mergeados (§2.1): busca `<serie>.candidates.<iniciales>.csv` y
`<serie>.decisions.<iniciales>.csv` de dos personas.

**Los vacíos de la guía** no van en un archivo de la serie. Si dos personas competentes
discreparon, la primera hipótesis es que la guía no decidía el caso, no que una de las dos se
equivocó; la corrección va como PR a
[`annotation-guidelines.md`](../annotation-guidelines.md) (o al manual), antes de abrir la
serie siguiente.

---

## 4. Verificación: ninguna etiqueta de máquina en el conjunto de referencia

Es la verificación que sostiene OE4. `CONTRIBUTING.md` §7.6 y el manual §0 lo dicen igual:
la máquina puede extraer candidatos, resolver evidencia, proponer qué pares mirar y marcar
señales de revisión; **no puede decidir si algo es una decisión ni qué relación hay entre
dos**. `machine_flags` es una sugerencia; `status` y `relation` los llena una persona.

Si un modelo hubiera puesto esas etiquetas, C3 —*"la misma representación sin errores de
extracción"*— tendría errores de extracción por construcción, y la brecha C2 − C3, que es
todo OE4, dejaría de medir nada.

**Primer paso, siempre:** `uv run afg gold validate --annotator <iniciales>` sobre el PR.
Cubre, mecánicamente, que las columnas de máquina lleguen **byte a byte iguales** al insumo —
`decision_id`, `meeting_id`, `source_sentence_id`, `sentence_text`, `evidence_da_count`,
`evidence_text`, `machine_flags` en decisiones; `pair_id`, `earlier_decision_id`,
`later_decision_id`, `earlier_sentence_id`, `later_sentence_id`, `earlier_text`,
`later_text`, `blocker_score` en candidatos— y que `status`, `relation`, `direction_ok` y
`confidence` sean valores del conjunto cerrado: son `enum`s
(`src/afg/domain/decision.py::AnnotationStatus`, `src/afg/domain/relation.py::RelationType`,
`DirectionOk`, `Confidence`) que `afg gold validate` compara celda a celda. Sale con código
distinto de cero si algo falla; si el PR no lo pasa, se devuelve antes de mirar nada más.

Lo que `validate` no puede juzgar, y sigue siendo tuyo revisar a ojo en cada PR, antes de
mergear:

- [ ] `annotator` está lleno en todas las filas, con `gv` o `gm`, nunca vacío ni con otro
      valor (`validate` exige que no esté vacío, pero no que sea el correcto).
- [ ] `status` **no** es una copia de `machine_flags`. Si una serie tiene `compuesta`
      exactamente en las filas con `posible_compuesta` y en ninguna otra, revísalo: puede ser
      coincidencia, pero también puede ser que alguien haya transcrito la bandera.
- [ ] El insumo sin iniciales (`<serie>.decisions.csv`, `<serie>.candidates.csv`) no aparece
      modificado en el PR.

---

## 5. Decisión sobre la segunda muestra de recall

La Tarea C la ejecuta `gv` sobre `data/processed/relations/IS1004.recall-sample.csv` — 50
pares rechazados por el bloqueador, ya generados con semilla fija. Cada par que resulte
distinto de `no_relacionada` es un **falso negativo**.

**La decisión sobre una segunda muestra es tuya, y se toma después de ver la primera.**
Nadie genera otra por su cuenta: una segunda muestra elegida después de ver un resultado que
no gustó es selección de muestra por conveniencia, y eso sí invalidaría la cifra.

Qué mirar para decidir:

- **Cuántos falsos negativos aparecieron.** Si son cero o uno en 50, el intervalo de
  confianza por bootstrap va a ser ancho por abajo pero la conclusión —"el bloqueador pierde
  poco"— se sostiene. Si son muchos, el punto de operación del bloqueador es el problema, no
  el tamaño de la muestra, y lo que toca es revisarlo, no muestrear más.
- **Si la segunda muestra fuera de otra serie**, deja de estimar lo mismo: IS1004 es
  desarrollo, y muestrear una serie de evaluación para esto significa leer contenido de
  evaluación. Tendría que justificarse y registrarse.
- Cualquiera que sea la decisión, se escribe: como entrada nueva en
  `docs/decisions/README.md` si cambia una cifra publicada, o como ADR si cambia el
  procedimiento.

---

## 6. Un ejemplo resuelto — una sesión de adjudicación

**El ejemplo sale de ES2015 (serie de desarrollo) a propósito**: un registro de adjudicación
real de una serie de control contiene contenido de evaluación, y este documento lo lee todo
el equipo.

Supongamos que en la calibración `gv` puso `refina` y `gm` puso `reafirma` en `ES2015.p001`.
El par, verbatim del insumo:

```
pair_id             : ES2015.p001
earlier_decision_id : ES2015a.d01
later_decision_id   : ES2015b.d01
earlier_sentence_id : ES2015a.elana.s.11
later_sentence_id   : ES2015b.elana.s.11
earlier_text        : It will be a television remote control.
later_text          : The remote will be a single function design- television only.
blocker_score       : 0.6666666666666666
```

`uv run afg gold adjudicate --series ES2015` ya deja en `ES2015.candidates.adjudicated.csv` la
fila con las dos etiquetas puestas, `acuerdo = no` y `final_*`, `razon` y `adjudicator` vacíos.
Tú completas el veredicto, la razón y tus iniciales; el resultado, leído por columnas, es:

| `pair_id` | `gm_relation` | `gv_relation` | `final_relation` | `razon` |
|---|---|---|---|---|
| `ES2015.p001` | `reafirma` | `refina` | `refina` | La posterior conserva el objeto (control de televisión) y **agrega** un límite que antes no estaba: función única, sin DVD ni VCR. `reafirma` exige que el contenido no cambie; aquí cambió por acotación, que es la definición de `refina`. |

(El orden de las columnas de anotador en el archivo generado es alfabético por iniciales —
`gm` antes que `gv` — no el orden en que se anotó.)

Y, aparte del CSV, el vacío de la guía que el desacuerdo revela:

> Este desacuerdo revela un vacío: la guía no dice si **excluir** alternativas cuenta como
> agregar detalle. Propuesta de corrección de `annotation-guidelines.md`: en `refina`,
> precisar que acotar incluye excluir explícitamente opciones que la decisión anterior dejaba
> abiertas. Va como PR a `annotation-guidelines.md`, no a un archivo de la serie.

**Por qué el veredicto es `refina` y no `reafirma`.** Las dos etiquetas se distinguen por una
sola cosa —si el contenido cambió— y aquí cambió: `ES2015a` no excluía la multifunción y
`ES2015b` sí. Que el desacuerdo caiga justo en el borde entre dos etiquetas vecinas es la
señal típica de un vacío de la guía, no de un descuido de una de las dos personas; por eso
la fila lleva razón **y** la guía recibe un PR de corrección.

---

## 7. Notebook 03 — el cierre de OE1

`notebooks/03-jss-anotacion-oe1.ipynb` está pendiente (`notebooks/README.md`). Es el registro
académico de la anotación humana: acuerdo, kappa, adjudicación y el conjunto de referencia
resultante.

- **El notebook no calcula** (`CONTRIBUTING.md` §7.1, `notebooks/README.md`). Toda cifra
  viene de una función testeada de `src/afg/`; el notebook importa, llama y explica. Si al
  escribirlo aparece una cifra que no tiene función detrás, la función se escribe primero,
  con su prueba.
- **Va separado del 01** a propósito: el 01 contiene etiquetas puestas por una máquina con
  fines de planificación, y el 03 contendrá el conjunto de referencia real, hecho a mano.
  Mezclarlos invitaría a citar las provisionales como si fueran la referencia.
- **Se versiona con sus outputs y se re-ejecuta antes de entregarlo.** Un notebook con
  outputs obsoletos miente con autoridad.

```bash
uv run jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=900 notebooks/03-jss-anotacion-oe1.ipynb
```

Si al escribirlo una cifra cambia respecto de lo ya publicado, hay que decir **dónde más
aparece esa cifra** y actualizar cada lugar (`CONTRIBUTING.md` §7.5 y §7.9).

---

## 8. Qué haces cumplir (aunque no anotes)

- **La regla anti-fuga (§5.1).** En la revisión de cada PR: la anotación va en orden
  cronológico `a → b → c → d`, y al juzgar una decisión no se miran reuniones posteriores.
  Un `notes` que cite una reunión posterior a la de la fila es una fuga y se devuelve.
- **La regla de independencia.** Durante las Fases 1 y 2, `gv` y `gm` no comparan etiquetas
  ni discuten casos concretos antes de la sesión. Si lo hacen, el kappa deja de medir acuerdo
  y pasa a medir conversación. Las dudas de procedimiento vienen a ti, no de uno al otro.
- **La lectura de transcripciones es legítima.** `data/interim/transcripts/<reunion>.md` se
  lee y se debe leer: la regla de alcance de `notebooks/README.md` restringe el análisis
  exploratorio, no la anotación. Si alguien pregunta, la respuesta es sí.
- **Una serie por PR.** No se aceptan PRs con varias series: un PR por serie es lo que
  permite detectar deriva de criterio temprano.

---

## 9. Cómo entregas

Cada adjudicación es su propio PR, contra `main`, revisado por ti mismo — es deliberado
(`CONTRIBUTING.md` §3): la responsabilidad de lo que entra a `main` es tuya de todos modos.

```bash
git checkout main
git pull
git checkout -b data/adjudicacion-ES2015
uv run afg gold adjudicate --series ES2015    # escribe los dos *.adjudicated.csv prellenados
uv run afg gold agreement  --series ES2015    # escribe reports/tables/ES2015.agreement.csv
# completas final_*, razon y adjudicator en las filas con acuerdo = no
uv run afg gold validate-adjudication --series ES2015
git add data/processed/decisions/ES2015.decisions.adjudicated.csv \
        data/processed/relations/ES2015.candidates.adjudicated.csv \
        reports/tables/ES2015.agreement.csv
git commit -m "data(adjudicacion): resolver desacuerdos de ES2015 y registrar kappas"
```

Nunca push directo a `main`, ni para cambios triviales.

---

## 10. Checklist de cierre de adjudicación

### Antes de la sesión
- [ ] `uv run afg gold status` muestra la serie como **completa** para `gv` y para `gm`
- [ ] Los cuatro archivos de la serie están mergeados (§2.1)
- [ ] `uv run afg gold validate --annotator gv` y `--annotator gm` corrieron sin error en sus
      PRs respectivos (§4) — columnas de máquina intactas y valores legales ya verificados

### Durante
- [ ] `uv run afg gold adjudicate --series <ID>` corrió sin error y escribió los dos `*.adjudicated.csv`
- [ ] Cada fila con `acuerdo = no` (Tarea A y Tarea B) tiene `final_*` **y `razon` escrita**
- [ ] Las filas `compuesta` tienen sus hijas `<id>-1`, `<id>-2`, ... con `final_*`
- [ ] `uv run afg gold validate-adjudication --series <ID>` sale sin errores
- [ ] Se evaluó si el desacuerdo revela un vacío de la guía

### Después
- [ ] `uv run afg gold agreement --series <ID>` corrió y `reports/tables/<serie>.agreement.csv`
      quedó versionado
- [ ] Los dos `*.adjudicated.csv` y el `.agreement.csv` van en el mismo PR (§9)
- [ ] Si hay vacío de guía: PR a `annotation-guidelines.md` o al manual,
      **antes** de abrir la serie siguiente
- [ ] Si la serie es de calibración: queda escrito que ese kappa **no se reporta**
- [ ] `uv run pytest -q`, `uv run ruff check .` y `uv run mypy src/afg` pasan
