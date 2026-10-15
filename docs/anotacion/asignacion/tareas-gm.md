# Tareas de Gustavo Martínez (`gm`)

> **Antes de la primera fila:** lee [`../annotation-guidelines.md`](../annotation-guidelines.md)
> (qué cuenta como decisión, qué significa cada relación) y ten
> [`../manual-anotacion-oe1.md`](../manual-anotacion-oe1.md) abierto al lado del CSV. Este
> documento dice **qué te toca y cómo lo entregas**; los criterios de etiquetado están allí y
> solo allí.

## Próximos pasos (estado al 2026-10-13)

ES2015 ya está adjudicada. Lo que sigue, en este orden:

1. **Sesión conjunta sobre ES2015** con `jss` y gv
   ([`../calibracion/ES2015-sesion-conjunta.md`](../calibracion/ES2015-sesion-conjunta.md)).
   Se habla **solo de ES2015**: no leas ni anotes TS3009 antes.
2. **`jss` ya abrió TS3009**: la anotas ahora (recalibración):
   ```bash
   git switch main && git pull
   git switch -c data/anotacion-TS3009-gm
   uv run afg gold prepare --annotator gm
   ```
   Abre `data/processed/decisions/TS3009.decisions.gm.csv` (Tarea A) y luego
   `data/processed/relations/TS3009.candidates.gm.csv` (Tarea B), en orden de reunión
   `a → b → c → d`. Aplica la regla de oro nueva (manual §2): si `evidence_text` no alcanza,
   lee la transcripción de **la misma reunión**. Al terminar:
   ```bash
   uv run afg gold validate --annotator gm --series TS3009
   ```
   y entrega con la convención de §9 (rama `data/anotacion-TS3009-gm`, commit
   `data(anotacion): tareas A y B de TS3009 (gm)`, un PR). El issue de recalibración de
   TS3009 asignado a ti (#79) sigue ese avance.
3. **Independencia:** no abras el PR, la rama ni el CSV de Germán, ni comenten casos de
   TS3009, hasta que `jss` anuncie la adjudicación de TS3009.
4. **Espera la adjudicación de TS3009.** Después sigue ES2016 con la misma receta (§9).

---

## Tu encargo en una frase

Anotar las Tareas A y B en nueve series (223 decisiones y 71 pares candidatos) y escribir el
banco de preguntas de OE4: mínimo 25 preguntas por cada uno de los cuatro estratos.

## Tu día a día en tres comandos

```bash
uv run afg gold setup    --annotator gm                    # una vez: deja todo listo
uv run afg gold validate --annotator gm --series <ID>       # al cerrar cada serie
uv run afg gold status   --annotator gm                     # tu propio avance (lectura)
```

`setup` se corre **una sola vez** (y otra vez cuando `jss` abre una serie nueva): descarga el
corpus (con confirmación de la licencia; la descarga pesa unos 22 MB y ocupa 228 MB),
genera las transcripciones y crea, solo para las series ya abiertas, cada `<serie>.decisions.gm.csv` y
`<serie>.candidates.gm.csv` con las columnas de máquina ya llenas y las tuyas vacías —
nunca copies ni renombres un CSV a mano. Termina diciéndote lo único que toca hacer
ahora según el estado real (qué serie, qué archivo, o a quién esperas). Si vuelves a correrlo, salta lo que ya esté hecho y nunca borra tu trabajo: un
archivo con anotación se respeta. Si alguna vez necesitas recrear un archivo puntual
(por ejemplo porque su base cambió), sigue disponible `afg gold prepare --annotator gm`.
`validate` con `--series <ID>` revisa solo la serie cuyo PR vas a abrir; sin `--series`
recorre todas tus series asignadas. Si hay un error sale con código distinto de cero y te
dice fila y columna exactas. `status --annotator gm` es solo lectura; te muestra tu propio
avance, serie por serie, sin abrir un CSV. Cada serie está `pendiente (aún no)` (`jss`
todavía no la abre; no hay archivos), `sin preparar`, `por empezar`, `en curso`, `con errores`,
`lista para entregar` o `adjudicada`. Las filas de una serie cuentan también las partes de
las decisiones `compuesta` (p. ej. «32 filas = 29 originales + 3 partes»). Termina siempre
con una línea `Siguiente: …`.
También muestra cuántas preguntas del banco llevas por estrato frente al mínimo.

---

## 1. Tus series, en orden

Haz las fases en orden. No empieces la Fase 2 sin que ES2015 y TS3009 estén adjudicadas.

### Fase 1 — Calibración y recalibración (doble anotación con `gv`)

| Serie | Decisiones | Candidatos | Para qué |
|---|---:|---:|---|
| ES2015 | 29 | 3 | calibración |
| TS3009 | 24 | 4 | recalibración |
| **Total** | **53** | **7** | |

Series de **desarrollo**, elegidas a propósito: no se quema una serie de control aprendiendo
la guía. Los kappas son diagnósticos y no se reportan en la tesis
([`README.md`](README.md) §2). ES2015 va primero. El acuerdo en ES2015 salió bajo, así que
tras la sesión conjunta de criterios se vuelve a calibrar sobre TS3009 antes de tocar
ninguna serie de control. **TS3009 no se empieza hasta que Jason lo indique** (después de la
sesión conjunta y de la actualización del manual).

### Fase 2 — Series de control (doble anotación con `gv`), en este orden

| Serie | Decisiones | Candidatos |
|---|---:|---:|
| ES2016 | 24 | 4 |
| IS1003 | 25 | 8 |
| TS3005 | 29 | 11 |
| ES2008 | 33 | 14 |
| **Total** | **111** | **37** |

El mismo orden que `gv`, de menor a mayor volumen de candidatos. **Una serie, adjudicación,
la siguiente.** Nunca las cuatro seguidas.

### Fase 3 — Tus series individuales (solo tú las anotas), en este orden

| Serie | Decisiones | Candidatos | Conjunto |
|---|---:|---:|---|
| TS3011 | 23 | 5 | evaluación |
| IS1008 | 13 | 8 | evaluación |
| ES2014 | 23 | 14 | evaluación |
| **Total** | **59** | **27** | |

TS3009, que antes abría esta fase, pasó a la Fase 1: ahora la anotan las dos personas como
recalibración.

### Tu carga total

**223 decisiones y 71 pares candidatos** (53 + 111 + 59 y 7 + 37 + 27), más el banco de
preguntas.

**Por qué llevas 61 decisiones menos que Germán.** Porque además escribes el banco: ≥100
preguntas a ~5 minutos cada una son unas 8 horas que él no tiene. El reparto equilibra horas
totales, no filas. A cambio llevas 6 pares candidatos más que él, que es donde está el
trabajo fino.

---

## 2. Qué archivo tocas y qué columnas llenas

### Tarea A — `data/processed/decisions/<serie>.decisions.gm.csv`

**Nunca edites `<serie>.decisions.csv`.** Es el insumo limpio que genera `afg gold build`. Tu
copia ya existe con el nombre correcto y las columnas de máquina llenas en cuanto corres:

```bash
uv run afg gold prepare --annotator gm
```

El patrón `<serie>.decisions.<iniciales>.csv` es el que fija [`README.md`](README.md) §5.1,
espejo del `<serie>.candidates.<iniciales>.csv` que el manual ya definía para la Tarea B.
`prepare` lo aplica también en Fase 3, aunque anotes solo tú.

| Columna | Quién | Regla |
|---|---|---|
| `decision_id` | máquina | **No tocar** |
| `meeting_id` | máquina | **No tocar** |
| `source_sentence_id` | máquina | **No tocar** |
| `sentence_text` | máquina | **No tocar** |
| `evidence_da_count` | máquina | **No tocar** |
| `evidence_text` | máquina | **No tocar** |
| `machine_flags` | máquina | **No tocar.** Es una sugerencia de triaje, no una etiqueta |
| **`status`** | **tú** | Valor del conjunto cerrado, ver abajo |
| **`decision_object`** | **tú** | Qué se decide |
| **`decision_content`** | **tú** | Qué se decidió al respecto |
| **`annotator`** | **tú** | `gm`, ya puesto por `prepare` |
| **`notes`** | **tú** | Solo si algo no es obvio; obligatorio en `sin_soporte` |

**Valores permitidos de `status`:**

```
decision | no_decision | compuesta | sin_soporte | descartar
```

> Verificado: este conjunto lo define el manual §2 y hoy también lo valida el código —
> `src/afg/domain/decision.py::AnnotationStatus` es el `enum` que usa `afg gold validate`
> para rechazar un valor fuera de estos cinco. No es lo mismo que
> `DecisionStatus` (`accepted`, `open_proposal`, `open_question`, `opinion`), que es el
> vocabulario del modelo de dominio, no el de esta columna. Aun así, cópialos literalmente:
> `validate` te avisa si te equivocas, pero solo al correrlo.
>
> Los valores de `machine_flags` que sí produce el código son `sin_evidencia`,
> `posible_compuesta` y `frase_corta` (`src/afg/annotation/goldset.py::machine_flags_for`).
> `posible_compuesta` **no** es un `status`: es una sugerencia de que mires la fila.

### Tarea B — `data/processed/relations/<serie>.candidates.gm.csv`

Misma regla: la crea `afg gold prepare --annotator gm`, no una copia manual.

| Columna | Quién | Regla |
|---|---|---|
| `pair_id` | máquina | **No tocar** |
| `earlier_decision_id` / `later_decision_id` | máquina | **No tocar.** El id de la decisión, siempre en orden cronológico |
| `earlier_sentence_id` / `later_sentence_id` | máquina | **No tocar.** El id de la frase de origen en el corpus AMI |
| `earlier_text` / `later_text` | máquina | **No tocar** |
| `blocker_score` | máquina | **No tocar** |
| **`relation`** | **tú** | Valor del conjunto cerrado, ver abajo |
| **`direction_ok`** | **tú** | `si` / `no` |
| **`confidence`** | **tú** | `alta` / `media` / `baja` |
| **`annotator`** | **tú** | `gm`, ya puesto por `prepare` |
| **`notes`** | **tú** | Obligatorio si `direction_ok = no` |

**Valores permitidos:**

```
relation      : introduce | reafirma | refina | revierte | reemplaza | no_relacionada
direction_ok  : si | no
confidence    : alta | media | baja
```

> Verificado: los seis valores de `relation` son literalmente los de
> `src/afg/domain/relation.py::RelationType`, y los tres conjuntos (`relation`,
> `direction_ok`, `confidence`) son `enum`s que `afg gold validate` compara celda a celda
> (`src/afg/annotation/workspace.py`). `direction_ok` se compara en minúsculas
> (`agreement.py`), así que escribe `si`, sin tilde y sin mayúscula.
>
> `no_relacionada` no es un valor vacío: significa *"el bloqueador se equivocó, aquí no hay
> relación"*, y el cálculo de acuerdo lo trata exactamente así
> (`agreement.py`, `_NO_RELATION_LABEL`). Una celda vacía y un `no_relacionada` no son lo
> mismo. Llena las 71 filas; `afg gold validate` marca como "a medio llenar" cualquier fila
> donde `relation`, `direction_ok` y `confidence` no estén las tres puestas.

---

## 3. Qué puedes mirar y qué no

**La transcripción de la reunión SÍ se puede y se debe leer.** Está en
`data/interim/transcripts/<reunion>.md` — por ejemplo `data/interim/transcripts/ES2015c.md`.

Esto no contradice la regla de alcance de
[`../../../notebooks/README.md`](../../../notebooks/README.md), que restringe el **análisis
exploratorio** a las series de desarrollo. **La anotación no es análisis exploratorio**:
construir el conjunto de referencia *exige* leer la evidencia, incluida la de las series de
evaluación. Lo prohibido es leer contenido de evaluación **fuera** del flujo de anotación
(para hacerse una idea, para preparar un gráfico, para contarlo en una reunión).

Se dice así de claro porque un anotador que crea que no puede abrir la transcripción anotará
a ciegas desde el resumen abstractivo — y **el caso del botón turbo, documentado en el
notebook 00 y en el manual §3, demuestra que el resumen abstractivo a veces contradice la
transcripción**. Ese error entraría al conjunto de referencia y se volvería la vara con la
que se mide todo lo demás.

| Puedes | No puedes |
|---|---|
| Leer la transcripción de la reunión que estás anotando | Leer reuniones posteriores a la que anotas (§4) |
| Usar `afg gold evidencia` para buscar un término | Leer series que no te tocan |
| Leer los insumos de tus series | Comentar contenido de evaluación fuera del flujo de anotación |
| Leer cualquier cosa de ES2015 o IS1004 (desarrollo) | Abrir el XML del corpus (no hace falta nunca) |

**TS3009 es una serie que anotas tú**, aunque sea de desarrollo: no la leas antes de anotarla, más allá de lo que la propia anotación exige, ni la comentes con la otra persona hasta que `jss` anuncie su adjudicación.

---

## 4. La regla anti-fuga (§5.1 de la tesis)

**Dentro de una serie se anota en orden cronológico: `a → b → c → d`.** Al juzgar una
decisión de la reunión `b` no debes haber leído aún `c` ni `d`.

En la Tarea B eso significa: primero todos los pares cuyo extremo posterior está en `b`,
luego los de `c`, luego los de `d`.

No es una preferencia de estilo. La tesis impone esta restricción a la extracción
automática; si la anotación humana no la cumple, la comparación entre ambas no es limpia —
la persona habría tenido información que el sistema no tenía. `src/afg/annotation/linking.py`
la impone estructuralmente del lado de la máquina (`meetings_visible_when_annotating`,
`validate_no_leakage`); del lado humano la impones tú.

---

## 5. La regla de independencia

**Durante la Fase 1 y la Fase 2, tú y Germán NO comparan etiquetas ni discuten casos
concretos hasta la sesión de adjudicación.**

Ni "oye, ¿la 14 te salió `refina`?", ni un mensaje con una captura del CSV. Si lo hacen, el
kappa deja de medir acuerdo entre dos lecturas independientes y pasa a medir su
conversación — y ese número es el que sostiene la confiabilidad de todo OE1.

Sí pueden, en cualquier momento: preguntarle a `jss` una duda de procedimiento, y proponer
una corrección de la guía **después** de una adjudicación.

En la Fase 3 no aplica: cada serie la anota una sola persona.

### Sesión conjunta

La excepción es la **sesión conjunta** con `jss` y Germán: solo vale para series **ya
adjudicadas** (hoy, ES2015), porque allí las etiquetas ya no son independientes y comparar no
daña ninguna medición. Nunca se usa para una serie que aún se anota: TS3009 queda fuera hasta
que `jss` anuncie su adjudicación. Lo mismo vale para cada serie siguiente.

---

## 6. Un ejemplo resuelto

**Los dos ejemplos salen de ES2015, que es serie de desarrollo, a propósito**: reproducir
aquí una fila de una serie de evaluación sería publicar contenido de evaluación en un
documento que todo el equipo lee, es decir, contaminarla para siempre.

### 6.1 Tarea A — fila `ES2015c.d08`, una `compuesta`

**Antes** (lo que deja `uv run afg gold prepare --annotator gm` en tu
`ES2015.decisions.gm.csv`; `annotator` ya viene puesto, el resto de lo tuyo está vacío):

```
decision_id        : ES2015c.d08
meeting_id         : ES2015c
source_sentence_id : ES2015c.elana.s.21
evidence_da_count  : 3
sentence_text      : Functions will be basic, including power, channels, volume.
evidence_text      : C: just just the basic button functions . | B: So we're just going
                     for power , channels , volume , | B: We can just go for , make it a
                     selling point that it is just the basic .
machine_flags      : posible_compuesta
status             :
decision_object    :
decision_content   :
annotator          : gm
notes              :
```

**Después** — la fila original queda marcada, y se crean las filas hijas:

```
decision_id      : ES2015c.d08
status           : compuesta
decision_object  : conjunto de funciones del control
decision_content : (vacio - se divide en las filas hijas)
annotator        : gm
notes            : La frase enumera el criterio general y tres funciones concretas.
```

| `decision_id` | `decision_object` | `decision_content` | `status` |
|---|---|---|---|
| `ES2015c.d08-1` | alcance de funciones | solo funciones básicas, como argumento de venta | `decision` |
| `ES2015c.d08-2` | encendido | el control incluye encendido | `decision` |
| `ES2015c.d08-3` | canales | el control incluye selección de canales | `decision` |
| `ES2015c.d08-4` | volumen | el control incluye control de volumen | `decision` |

Las cuatro hijas copian `source_sentence_id` y `evidence_text` de la original, llevan
`annotator = gm`, y **ninguna queda con `status = compuesta`**.

**Por qué `compuesta` y no `decision`.** La frase nombra **cuatro** objetos de decisión
distintos —el criterio de alcance, y tres funciones concretas— y §5.2 exige que una decisión
nombre *un* objeto y *un* contenido. Una sola fila obligaría a un sistema a acertar las
cuatro a la vez o fallar entero, que no es lo que OE2 quiere medir.

**Ojo con `machine_flags`.** Aquí la máquina había puesto `posible_compuesta` y resultó
tener razón, pero eso es una coincidencia útil, no una autorización: la etiqueta la pones tú
después de leer la evidencia (`CONTRIBUTING.md` §7.6). Hay filas con `posible_compuesta` que
son una sola decisión, y filas sin bandera que son tres.

### 6.2 Tarea B — par `ES2015.p002`

**Antes** (lo que deja `prepare` en tu `ES2015.candidates.gm.csv`):

```
pair_id             : ES2015.p002
earlier_decision_id : ES2015c.d06
later_decision_id   : ES2015d.d04
earlier_sentence_id : ES2015c.elana.s.19
later_sentence_id   : ES2015d.elana.s.15
earlier_text        : Regular chip will be used.
later_text          : Will use a regular chip.
blocker_score       : 1.0
relation            :
direction_ok        :
confidence          :
annotator           : gm
notes               :
```

**Después:**

```
relation      : reafirma
direction_ok  : si
confidence    : alta
annotator     : gm
notes         : Mismo objeto (tipo de chip) y mismo contenido (chip regular), sin detalle
                nuevo. La evidencia de ES2015d ("we're using a regular chip") es un
                recuento de lo ya decidido en ES2015c.
```

**Por qué `reafirma` y no `refina` ni `reemplaza`.** No es `refina` porque la posterior no
agrega nada: dice exactamente lo mismo con otras palabras, y por eso el `blocker_score` es
1.0. No es `reemplaza` porque no hay contenido distinto que sustituya al anterior. Y no es
`introduce` porque el objeto ya existía en `ES2015c`. `direction_ok = si`: la de `c` viene
como `earlier` y la de `d` como `later`, que es el orden de la convención.

> **Cuidado con el `blocker_score` alto.** Un 1.0 hace que `reafirma` parezca automático.
> No lo es: el coeficiente mide solapamiento de palabras, y dos frases casi idénticas pueden
> ser `revierte` si una lleva un "no" (*"will use a regular chip"* / *"will not use a
> regular chip"*). Lee las dos frases completas antes de etiquetar.

---

## 7. El banco de preguntas — tú escribes, Germán valida

**Cuándo empieza.** Cuando las cuatro series de control de la Fase 2 (ES2016, IS1003, TS3005,
ES2008) estén adjudicadas; hasta entonces `afg gold status` muestra «Banco de preguntas: aún
no» y no lo propone como siguiente paso. Las preguntas salen solo de series de evaluación
(ES2015, IS1004 y TS3009 quedan fuera, ADR 0005). E3 depende de relaciones ya adjudicadas, así
que la mayoría llegará con la Fase 3.

Mínimo **25 preguntas por estrato**, cuatro estratos, **≥100 en total**
(`docs/propuesta.md` §5.5); para E3 la meta es **hasta 40** (ver más abajo). **El autor no valida y el validador no escribe**: tú no tocas
`validated_by`, y Germán no escribe preguntas. Es la misma regla de separación que hace que
`jss` adjudique y no anote (`CONTRIBUTING.md` §1).

### Los cuatro estratos

Los valores de `stratum` son literalmente los de
`src/afg/domain/question.py::QuestionStratum`:

| Valor | Estrato | Forma | Qué mide |
|---|---|---|---|
| `E1_point_fact` | E1 — hecho puntual | *¿Qué se decidió sobre X?* | Caso donde se espera **paridad** entre condiciones; si C2 pierde aquí, hay una regresión que explicar |
| `E2_current_state` | E2 — estado vigente | *¿Cuál es la decisión vigente sobre X?* | Exige saber **cuál de varias versiones prevalece** |
| `E3_evolution` | E3 — evolución | *¿Cambió X? ¿En qué reunión y por qué?* | **El estrato que prueba la tesis** |
| `E4_unanswerable` | E4 — incontestable | Pregunta adyacente al dominio, sin respuesta en el material | Mide si el sistema **se abstiene o fabrica** |

### Cuántas preguntas de E3: hasta 40, nunca inventadas

El mínimo de cada estrato sigue siendo **25**. Para E3 el banco tiene además espacio para
**hasta 40 preguntas**: escribe tantas como el material permita, hasta ese tope. La razón es
estadística: E3 es el estrato donde se compara C2 con C1, y con más preguntas aumenta la
probabilidad de detectar una mejora real pequeña. En la simulación de potencia del notebook 10,
con 25 preguntas una mejora verdadera de 15 puntos se detecta en alrededor de 57 % de los
experimentos; con 40, en alrededor de 76 %. El límite lo pone el material, no el esfuerzo: el
notebook 01 proyecta unas 37 relaciones de evolución en las series de evaluación, así que no
siempre habrá 40 casos genuinos.

**Regla: nunca se inventa un caso E3.** Solo entra una pregunta sobre una decisión que de
verdad cambia entre reuniones y que está anotada como `revierte`, `reemplaza` o `refina`. Si
el material se agota antes de 40, las filas sobrantes de E3 se **dejan vacías**: no pasa nada,
`questions-check --complete` las trata como opcionales y no se usan. Quedarse corto de 40 se
declara como una limitación de potencia, no como un incumplimiento; lo que sí es obligatorio
es llegar a 25.

### El archivo

`data/processed/questions/banco-preguntas.csv` ya está creado — el mantenedor corrió:

```bash
uv run afg gold questions-init
```

115 filas numeradas `q001`..`q115`: 25 para E1 (`q001`–`q025`), 25 para E2 (`q026`–`q050`),
**40 para E3** (`q051`–`q090`) y 25 para E4 (`q091`–`q115`), en el orden de la tabla de arriba,
con `stratum` y `author = gm` ya puestos. Tú **nunca inventas un `id` ni
escribes un `stratum`**: escribes texto dentro de una fila que ya existe. Si el banco llegara
a necesitar regenerarse, `questions-init` se niega a hacerlo mientras haya preguntas escritas,
salvo `--force` — que destruye el banco, igual que `prepare --force` en las Tareas A y B.

Antes de abrir el PR del banco (o de un estrato) se corre la revisión del banco, que no
ejecuta nada y revisa fila por fila sin detenerse en el primer error:

```bash
uv run afg gold questions-check              # tolera un banco a medias
uv run afg gold questions-check --complete   # solo al cierre: exige el mínimo validado por estrato
```

Comprueba, en cada fila ya validada, que la serie sea una **serie de evaluación** (las de
desarrollo —ES2015, IS1004 y TS3009— no aportan preguntas al banco: ADR 0005), que la evidencia
esté bien formada y pertenezca a esa serie, que cada acto de diálogo citado **exista** en la
transcripción de la reunión, que la respuesta y la evidencia estén presentes (y que una E4 no
lleve ninguna de las dos), y que `validated_by` sean las iniciales de quien valida (`gm` o `gv`),
distintas del autor. En la evidencia los actos de una misma reunión se separan con `;` y las
reuniones con `|`; una coma entre ids se rechaza con un ejemplo del formato correcto. Si faltan
las transcripciones, avisa una sola vez y se corre `uv run afg gold setup`. Las filas aún sin
validar quedan como pendientes y el mínimo por estrato es un aviso; con `--complete` ambos
pasan a ser errores, y los errores repetidos se agrupan en una línea con su cuenta (por
ejemplo, «115 filas (q001, q002, q003 y 112 más): sin escribir»). Las filas de más sobre el mínimo que siguen **completamente vacías** (sin
texto, respuesta, evidencia, serie ni validador) se informan como *opcionales sin usar*: no
son pendientes ni errores, y el Experimento B las ignora. Sale con código 1 si hay errores: se corrigen antes del PR.

Hay además un ejemplo de referencia, uno por estrato, en
[`../../../data/processed/questions/_plantilla-banco-preguntas.csv`](../../../data/processed/questions/_plantilla-banco-preguntas.csv).
**Su `id` lleva prefijo de serie** (`ES2015.q001`); el banco real que genera `questions-init`
no lo lleva (`q001`..`q115`, sin serie) porque la serie es tu elección por pregunta, no algo
que se sepa de antemano. Úsala solo para ver el estilo de una pregunta bien construida, no
como plantilla de formato de `id`.

Las columnas salen del modelo `src/afg/domain/question.py::Question`, una por campo:

| Columna | Qué es |
|---|---|
| `id` | `q001`..`q115`, ya puesto por `questions-init`. **No tocar** |
| `series_id` | La serie de la que sale la pregunta. **La llenas tú**, es tu elección por pregunta |
| `stratum` | Uno de los cuatro valores de arriba, ya puesto por `questions-init`. **No tocar** |
| `text` | La pregunta, en español. **La llenas tú** |
| `reference_answer` | La respuesta derivada de la evidencia. **La llenas tú**, y queda **vacía en E4**: el modelo la declara `None` para ese estrato, porque ahí la referencia *es la ausencia de respuesta* |
| `reference_evidence` | Los actos de diálogo que la respaldan. **La llenas tú**. Formato `reunion:da_id;da_id`, y `\|` entre reuniones cuando la evidencia abarca más de una. **Vacía en E4**. Los ids se obtienen con `uv run afg gold evidencia` (ver «Cómo llenar `reference_evidence`» más abajo) |
| `author` | `gm`, ya puesto por `questions-init` |
| `validated_by` | **Lo llena Germán.** Tú lo dejas vacío |
| `validation_notes` | **Lo llena Germán** cuando devuelve una pregunta que no pasó, con el motivo. **Tú lo borras** al reentregar la pregunta corregida — la tabla completa de los cuatro estados está en `tareas-gv.md` §8 |

### Cómo llenar `reference_evidence`

Los ids de acto de diálogo no aparecen en los `.md` de las transcripciones ni en los CSV de
anotación. El comando `uv run afg gold evidencia` los muestra y entrega la celda lista para
pegar. Hay dos formas de usarlo.

**A. Partir de una decisión ya adjudicada** (lo habitual, porque las preguntas salen de la
anotación adjudicada). El id de la decisión está en la primera columna de
`data/processed/decisions/<SERIE>.decisions.adjudicated.csv`:

```bash
uv run afg gold evidencia --decision ES2015a.d02
```

```text
ES2015a.d02: precio de venta — fijar el precio de venta en 25 euros
Evidencia en 1 turno(s) de ES2015a:

turno 114 (PM)
  So, now that we know how to use the whiteboard, um, the next, um, thing we need to
  address is our financial department, [...] selling price of twenty five Euros. [...]
  actos: ES2015a.A.dialog-act.dharshi.120

Para pegar en `reference_evidence`:
  ES2015a:ES2015a.A.dialog-act.dharshi.120
```

El texto de la última sección (la línea bajo «Para pegar en `reference_evidence`») se copia tal
cual en la celda. Si la evidencia abarca varios turnos o varias decisiones, los valores de la
misma reunión se unen con `;` dentro de un solo `reunion:` y los de reuniones distintas se
separan con `|`, por ejemplo `ES2015a:ES2015a.A.dialog-act.dharshi.120|ES2015b:ES2015b.A.dialog-act.dharshi.45`.

**B. Buscar en la transcripción** (cuando la evidencia no coincide con una decisión, por ejemplo
en una E1 sobre un detalle, o para confirmar una E4):

```bash
uv run afg gold evidencia --meeting ES2015a --term "twenty five"   # por palabra o frase
uv run afg gold evidencia --meeting ES2015a --turnos 113-115       # por turnos
```

Cada turno que coincide se muestra con su número, quién habló (`PM`, `UI`, `ID`, `ME`), el texto,
sus ids (`actos:`) y su línea «para pegar». Con varios turnos, la última sección junta todos los
ids. Los turnos largos traen varios actos de diálogo: si solo uno respalda la respuesta, basta
con dejar ese id en la celda.

Antes de pegar, conviene leer el turno y confirmar que dice lo que afirma `reference_answer`
(regla 1 de arriba: la respuesta sale de la evidencia). Después, `uv run afg gold questions-check`
verifica el formato de la celda.

Si el comando indica que faltan las transcripciones, se corre `uv run afg gold setup`. Si el
archivo del banco se guardó con Excel, debe quedar como «CSV UTF-8 (delimitado por comas)»;
con otra codificación o con `;` como separador, `questions-check` indica qué cambiar.

### Las tres reglas que más se rompen

1. **La respuesta sale de la evidencia, no del resumen abstractivo.** Es la misma regla de la
   Tarea A: el resumen de AMI tiene al menos un error demostrado (el botón turbo). Si la
   respuesta de referencia sale del resumen, el banco hereda ese error.
2. **Una E4 tiene que ser genuinamente incontestable.** Es el punto que más se rompe y el más
   caro: **ese estrato existe para medir abstención**, así que una E4 que sí tiene respuesta
   en el material invierte el resultado — un sistema que la contesta correctamente queda
   penalizado por acertar, y uno que se abstiene queda premiado por fallar. Antes de dar una
   E4 por buena, búscala en la transcripción de las cuatro reuniones de la serie y confirma
   que no aparece. Ejemplo verificado: en las cuatro transcripciones de ES2015 no hay
   ninguna ocurrencia de *warranty* ni de *guarantee*, así que preguntar por los años de
   garantía es incontestable con ese material.
3. **Una E4 sigue siendo del dominio.** "¿Cuál es la capital de Francia?" no mide nada:
   cualquier sistema la contesta desde su entrenamiento. La E4 tiene que ser *adyacente* —
   sonar como una pregunta legítima sobre este control remoto— para que la tentación de
   fabricar exista.

### Las preguntas salen del conjunto de referencia

Cada pregunta se construye **desde la anotación de OE1 ya adjudicada**, no al revés: una E3
sobre una decisión que cambió necesita que ese cambio esté anotado como `revierte`,
`reemplaza` o `refina` en algún `<serie>.candidates.*.csv`. Por eso el banco se escribe
**después** de que haya series cerradas, no en paralelo a la Fase 1.

---

## 8. Cómo entregas

Una serie, un PR (`CONTRIBUTING.md` §2 y §3). El trabajo se hace en una **rama**: una copia
paralela del historial donde se puede anotar sin tocar `main` todavía. Trabajar en rama evita
mezclar una serie a medio anotar con el trabajo de Germán o de `jss`, y permite que el
mantenedor revise exactamente esa serie antes de que entre.

```bash
git checkout main                                          # vuelve a main
git pull                                                    # trae lo que el equipo ya fusionó
git checkout -b data/anotacion-ES2015-gm                    # crea la rama de esta serie
uv run afg gold prepare --annotator gm
# ... anotas ...
uv run afg gold validate --annotator gm --series ES2015     # tiene que salir sin errores
git add data/processed/decisions/ES2015.decisions.gm.csv \
        data/processed/relations/ES2015.candidates.gm.csv
git commit -m "data(anotacion): tareas A y B de ES2015 (gm)"
git push -u origin data/anotacion-ES2015-gm                 # sube la rama al repositorio del equipo
```

Para TS3009 (y cada serie siguiente) es el mismo patrón con otra serie: rama
`data/anotacion-TS3009-gm`, `validate --series TS3009`, `git add` de
`TS3009.decisions.gm.csv` y `TS3009.candidates.gm.csv`, y mensaje de commit
`data(anotacion): tareas A y B de TS3009 (gm)`.

`origin` es el repositorio del equipo (`jasonssdev/mcd-afg`), el único remoto que hace falta.
Esto es seguro porque `main` está protegida (`CONTRIBUTING.md` §3): con permiso de escritura
se puede subir una rama, pero no `main` — GitHub rechaza cualquier intento de subir
directamente ahí.

**Si `git push` es rechazado**, la causa casi siempre es que la rama activa es `main` en vez
de la rama de la serie: revisa con `git branch --show-current` y corrige antes de reintentar.
Si el rechazo es por otra razón y no queda claro, se consulta a `jss`.

**Abrir el PR desde GitHub.** Después del `git push -u origin ...`, la página del repositorio
en GitHub muestra un botón **"Compare & pull request"**. Se pulsa, se confirma `main` como
destino, se completa la plantilla y se abre. Si el botón no aparece, se va a la pestaña
**Pull requests** y se pulsa **New pull request**, eligiendo la rama de la serie como origen y
`main` como destino.

**Si `git pull` trae conflictos** al actualizar `main` antes de empezar una serie nueva, no se
resuelven a ciegas: son dos cambios sobre las mismas líneas. Se consulta a `jss` antes de
forzar una resolución, sobre todo si el conflicto está en un CSV de anotación.

Después de que se fusione el PR, se limpia la rama local ya mergeada:

```bash
git checkout main
git pull
git branch -d data/anotacion-ES2015-gm
```

- **Rama `data/anotacion-<serie>-gm`**, con el prefijo `data/` de `CONTRIBUTING.md` §7.2. Las
  iniciales al final son obligatorias: en las Fases 1 y 2 las dos personas anotan la misma
  serie, y sin ellas las dos ramas tendrían el mismo nombre y el segundo `git push` chocaría.
- **Revisa el mantenedor** (`jss`), que es el CODEOWNER de `main`.
- **Una serie por PR, no todas juntas.** Un PR por serie permite detectar deriva de criterio
  temprano: si en la tercera serie empezaste a marcar `compuesta` con otro umbral, se ve en
  esa PR y no dentro de un bulto de diez series ya mezcladas.
- El banco de preguntas va aparte, rama `data/banco-preguntas`, y puede entregarse por
  estratos si prefieres PRs pequeños.

---

## 9. Checklist de cierre de serie

Marca solo lo verificado. Es el checklist del manual §7, con lo que este reparto agrega.
`uv run afg gold validate --annotator gm --series <ID>` ya cubre por ti los conjuntos
cerrados, las filas a medio llenar y que ninguna columna de máquina se haya tocado — no
hace falta revisarlos a ojo antes de correrlo, pero el checklist los deja explícitos porque
`validate` no juzga criterio (`sin_soporte` justificado, orden cronológico, `compuesta`
dividida con sentido).

### Tarea A
- [ ] El trabajo se hizo sobre `<serie>.decisions.gm.csv`; `<serie>.decisions.csv` quedó intacto
- [ ] Toda fila tiene `status` no vacío, del conjunto `decision | no_decision | compuesta | sin_soporte | descartar`
- [ ] Toda fila con `status = decision` tiene `decision_object` **y** `decision_content`
- [ ] Toda fila `compuesta` tiene sus filas hijas `-1`, `-2`, … creadas
- [ ] Ninguna fila hija quedó con `status = compuesta`
- [ ] Toda fila con `evidence_da_count = 0` fue revisada contra la transcripción
- [ ] Toda fila `sin_soporte` explica en `notes` qué dice la evidencia
- [ ] Las `no_decision` se conservaron: no se borró ninguna fila
- [ ] `annotator = gm` en todas las filas
- [ ] Ninguna columna de máquina quedó modificada, incluida `machine_flags`

### Tarea B
- [ ] El trabajo se hizo sobre `<serie>.candidates.gm.csv`; `<serie>.candidates.csv` quedó intacto
- [ ] Toda fila tiene `relation` del conjunto cerrado (ninguna vacía; `no_relacionada` es una etiqueta, no un vacío)
- [ ] `direction_ok` (`si` / `no`) está en todas las filas
- [ ] `confidence` (`alta` / `media` / `baja`) está en todas las filas
- [ ] Ninguna relación distinta de `no_relacionada` apunta a una decisión `sin_soporte`, `descartar` o `no_decision`
- [ ] La anotación se hizo en orden cronológico: primero los pares que terminan en `b`, luego `c`, luego `d`

### Independencia (solo Fases 1 y 2)
- [ ] No hubo comparación de etiquetas ni discusión de casos concretos con `gv` antes de la adjudicación

### Banco de preguntas (al cerrarlo)
- [ ] ≥25 preguntas por cada uno de los cuatro estratos, ≥100 en total (en E3, hasta 40 si el material lo permite; las filas E3 sobrantes quedan vacías)
- [ ] `stratum` usa los valores literales de `QuestionStratum`
- [ ] Cada respuesta de referencia se deriva de la evidencia citada, no del resumen
- [ ] Toda E4 se buscó en las cuatro transcripciones de su serie y no aparece
- [ ] `author = gm` en todas las filas; `validated_by` vacío (lo llena `gv`)

### Entrega
- [ ] Rama `data/anotacion-<serie>-gm` creada desde `main` actualizado (`git pull` antes de crear la rama)
- [ ] `uv run afg gold validate --annotator gm --series <ID>` sale sin errores
- [ ] Un PR con **esta serie sola**
- [ ] `uv run pytest -q` pasa
- [ ] Lo que no encajó quedó en `notes` y, si hace falta, en un issue "Hallazgo"
