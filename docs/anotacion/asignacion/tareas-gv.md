# Tareas de Germán Vega (`gv`)

> **Antes de la primera fila:** lee [`../annotation-guidelines.md`](../annotation-guidelines.md)
> (qué cuenta como decisión, qué significa cada relación) y ten
> [`../manual-anotacion-oe1.md`](../manual-anotacion-oe1.md) abierto al lado del CSV. Este
> documento dice **qué te toca y cómo lo entregas**; los criterios de etiquetado están allí y
> solo allí.

## Tu encargo en una frase

Anotar las Tareas A y B en diez series (260 decisiones y 61 pares candidatos), adjudicar la
muestra de recall de la Tarea C, y validar el banco de preguntas que escribe Gustavo.

## Tu día a día en tres comandos

```bash
uv run afg gold prepare  --annotator gv                    # crea tus archivos, ya nombrados
uv run afg gold validate --annotator gv --series <ID>       # antes de abrir el PR de esa serie
uv run afg gold status                                      # cómo va todo el equipo (lectura)
```

`prepare` genera cada `<serie>.decisions.gv.csv` y `<serie>.candidates.gv.csv` con las
columnas de máquina ya llenas y las tuyas vacías — nunca copies ni renombres un CSV a mano.
Correrlo de nuevo no borra tu trabajo: un archivo con anotación se respeta, salvo que pases
`--force`. `validate` es el filtro que tienes que pasar antes de cada PR: si hay un error
sale con código distinto de cero y te dice fila y columna exactas. `status` es solo lectura;
lo usas para ver tu propio avance sin abrir un CSV.

---

## 1. Tus series, en orden

Haz las fases en orden. No empieces la Fase 2 sin que ES2015 esté adjudicada.

### Fase 1 — Calibración (doble anotación con `gm`)

| Serie | Decisiones | Candidatos |
|---|---:|---:|
| ES2015 | 29 | 3 |

Serie de **desarrollo**, elegida a propósito: no se quema una serie de control aprendiendo
la guía. Este kappa es diagnóstico y no se reporta en la tesis
([`README.md`](README.md) §2).

### Fase 2 — Series de control (doble anotación con `gm`), en este orden

| Serie | Decisiones | Candidatos |
|---|---:|---:|
| ES2016 | 24 | 4 |
| IS1003 | 25 | 8 |
| TS3005 | 29 | 11 |
| ES2008 | 33 | 14 |
| **Total** | **111** | **37** |

De menor a mayor volumen de candidatos, para que el ritmo de la Tarea B se consolide antes
de la serie más pesada. **Una serie, adjudicación, la siguiente.** Nunca las cuatro seguidas.

### Fase 3 — Tus series individuales (solo tú las anotas), en este orden

| Serie | Decisiones | Candidatos | Conjunto |
|---|---:|---:|---|
| IS1004 | 24 | 4 | desarrollo |
| IS1006 | 17 | 1 | evaluación |
| IS1009 | 20 | 1 | evaluación |
| TS3003 | 31 | 6 | evaluación |
| ES2002 | 28 | 9 | evaluación |
| **Total** | **120** | **21** | |

IS1004 va primera porque es la serie del piloto: es la que el manual usa en su ejemplo
trabajado (§3), ya está contaminada, y equivocarse ahí no cuesta nada.

### Tu carga total

**260 decisiones y 61 pares candidatos** (29 + 111 + 120 y 3 + 37 + 21), más la Tarea C y la
validación del banco.

---

## 2. Qué archivo tocas y qué columnas llenas

### Tarea A — `data/processed/decisions/<serie>.decisions.gv.csv`

**Nunca edites `<serie>.decisions.csv`.** Es el insumo limpio que genera `afg gold build`. Tu
copia ya existe con el nombre correcto y las columnas de máquina llenas en cuanto corres:

```bash
uv run afg gold prepare --annotator gv
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
| **`annotator`** | **tú** | `gv`, ya puesto por `prepare` |
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

### Tarea B — `data/processed/relations/<serie>.candidates.gv.csv`

Misma regla: la crea `afg gold prepare --annotator gv`, no una copia manual.

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
| **`annotator`** | **tú** | `gv`, ya puesto por `prepare` |
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

> `no_relacionada` no es un valor vacío: significa *"el bloqueador se equivocó, aquí no hay
> relación"*, y el cálculo de acuerdo lo trata exactamente así
> (`agreement.py`, `_NO_RELATION_LABEL`). Una celda vacía y un `no_relacionada` no son lo
> mismo. Llena las 61 filas; `afg gold validate` marca como "a medio llenar" cualquier fila
> donde `relation`, `direction_ok` y `confidence` no estén las tres puestas.

---

## 3. Qué puedes mirar y qué no

**La transcripción de la reunión SÍ se puede y se debe leer.** Está en
`data/interim/transcripts/<reunion>.md` — por ejemplo `data/interim/transcripts/ES2015b.md`.

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
| Usar `afg gold evidence` para buscar un término | Leer series que no te tocan |
| Leer los insumos de tus series | Comentar contenido de evaluación fuera del flujo de anotación |
| Leer cualquier cosa de ES2015, IS1004 o TS3009 (desarrollo) | Abrir el XML del corpus (no hace falta nunca) |

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

**Durante la Fase 1 y la Fase 2, tú y Gustavo NO comparan etiquetas ni discuten casos
concretos hasta la sesión de adjudicación.**

Ni "oye, ¿la 14 te salió `refina`?", ni un mensaje con una captura del CSV. Si lo hacen, el
kappa deja de medir acuerdo entre dos lecturas independientes y pasa a medir su
conversación — y ese número es el que sostiene la confiabilidad de todo OE1.

Sí pueden, en cualquier momento: preguntarle a `jss` una duda de procedimiento, y proponer
una corrección de la guía **después** de una adjudicación.

En la Fase 3 no aplica: cada serie la anota una sola persona.

---

## 6. Un ejemplo resuelto

**Los dos ejemplos salen de ES2015, que es serie de desarrollo, a propósito**: reproducir
aquí una fila de una serie de evaluación sería publicar contenido de evaluación en un
documento que todo el equipo lee, es decir, contaminarla para siempre.

### 6.1 Tarea A — fila `ES2015b.d01`

**Antes** (lo que deja `uv run afg gold prepare --annotator gv` en tu
`ES2015.decisions.gv.csv`; `annotator` ya viene puesto, el resto de lo tuyo está vacío):

```
decision_id        : ES2015b.d01
meeting_id         : ES2015b
source_sentence_id : ES2015b.elana.s.11
evidence_da_count  : 3
sentence_text      : The remote will be a single function design- television only.
evidence_text      : D: because we're trying to do so much , that if we're trying to make
                     a unique , user-friendly , dadada , and it's also multi also
                     multifunctional , um , we're gonna go over budget for one thing . |
                     C: And with this we'll have more room in the budget probably to make
                     a more original design . | A: Um , for one thing , because
                     <disfmarker> Having controls with D_V_D_ , V_C_R_ , that sort of
                     thing , would really complicate the design of the remote control .
                     Um , we've decided not to include them and make it a specific , just
                     a specific television um function .
machine_flags      :
status             :
decision_object    :
decision_content   :
annotator          : gv
notes              :
```

**Después** (lo que escribes):

```
status           : decision
decision_object  : alcance funcional del control
decision_content : función única, solo televisión; se excluyen DVD y VCR
annotator        : gv
notes            :
```

**Por qué `decision` y no otra cosa.** Cumple las tres condiciones de §5.2: es *explícita*
(el acto de diálogo de A dice literalmente "we've decided not to include them"), es
*aceptada* (nadie la reabre en el segmento, y dos hablantes más la respaldan con el argumento
de presupuesto), y está *anclada* (hay objeto —el alcance funcional— y contenido —solo
televisión—). No es `compuesta` porque las tres frases de evidencia sostienen **una** sola
decisión desde tres ángulos, no tres decisiones distintas.

### 6.2 Tarea B — par `ES2015.p001`

**Antes** (lo que deja `prepare` en tu `ES2015.candidates.gv.csv`):

```
pair_id             : ES2015.p001
earlier_decision_id : ES2015a.d01
later_decision_id   : ES2015b.d01
earlier_sentence_id : ES2015a.elana.s.11
later_sentence_id   : ES2015b.elana.s.11
earlier_text        : It will be a television remote control.
later_text          : The remote will be a single function design- television only.
blocker_score       : 0.6666666666666666
relation            :
direction_ok        :
confidence          :
annotator           : gv
notes               :
```

**Después:**

```
relation      : refina
direction_ok  : si
confidence    : alta
annotator     : gv
notes         : La posterior conserva el objeto (es un control de televisión) y le agrega
                el limite explicito: funcion unica, sin DVD ni VCR.
```

**Por qué `refina` y no `reafirma` ni `introduce`.** No es `reafirma` porque la posterior no
repite la anterior sin cambiarla: le **agrega** una restricción que antes no estaba (la
exclusión explícita de la multifunción). No es `introduce` porque el objeto de decisión —el
alcance del producto— ya aparecía en `ES2015a`. `direction_ok = si` porque el archivo trae
la de la reunión `a` como `earlier` y la de la `b` como `later`, que es el orden que exige la
convención (la posterior actúa sobre la anterior).

---

## 7. Tarea C — Muestra de recall del bloqueador

**Archivo:** `data/processed/relations/IS1004.recall-sample.csv` — **ya está generado**, con
50 pares que el bloqueador **rechazó** (verificado: 50 filas, con la semilla ya registrada).
No lo regeneres: volver a correr `afg gold recall-sample` lo sobrescribe.

`uv run afg gold prepare --annotator gv` crea tu copia,
`IS1004.recall-sample.gv.csv`, junto con el resto de tus archivos. Mismas columnas y
**mismas reglas que la Tarea B**: mismo conjunto cerrado de `relation`, mismo `direction_ok`,
misma `confidence`. `afg gold validate --annotator gv --series IS1004` la revisa con las
mismas reglas de Tarea B.

**Qué mide.** Cada par que resulte **distinto de `no_relacionada`** es un **falso negativo
del bloqueador**: una relación real que el filtro tiró. Sin esta muestra el bloqueador es una
caja negra y la tesis no puede reportar qué se perdió (manual §5).

**Si crees que hace falta una segunda muestra, no la generes.** Esa decisión la toma `jss`
al ver los resultados de la primera. Escríbelo en el PR y para ahí.

---

## 8. Validación del banco de preguntas

Gustavo escribe el banco (mínimo 25 preguntas por estrato, ≥100 en total). **Tú lo validas, y
no escribes ninguna**: `docs/propuesta.md` §5.5 exige que quien valida no sea quien escribe.

Qué revisas en cada pregunta:

- Que el **estrato** sea el correcto (`E1_point_fact`, `E2_current_state`, `E3_evolution`,
  `E4_unanswerable`).
- Que la **respuesta de referencia** se derive de la evidencia citada, no del resumen.
- Que la **evidencia citada** exista y diga lo que la respuesta afirma.
- Que las de **E4 sean genuinamente incontestables** con el material. Este es el punto que
  más se rompe: una E4 que en realidad sí tiene respuesta arruina la medición de abstención,
  porque un sistema que la contesta bien queda penalizado por acertar.

Rellenas la columna `validated_by` con `gv`. Si una pregunta no pasa, no la corrijas tú:
devuélvela con el motivo, para que la autoría siga siendo de una sola persona.

---

## 9. Cómo entregas

Una serie, un PR (`CONTRIBUTING.md` §2 y §3):

```bash
git fetch upstream
git checkout -b data/anotacion-ES2015 upstream/main
uv run afg gold prepare --annotator gv
# ... anotas ...
uv run afg gold validate --annotator gv --series ES2015   # tiene que salir sin errores
git add data/processed/decisions/ES2015.decisions.gv.csv \
        data/processed/relations/ES2015.candidates.gv.csv
git commit -m "data(anotacion): tareas A y B de ES2015 (gv)"
git push -u origin data/anotacion-ES2015
# abres el PR desde tu fork contra main del repositorio original
```

- **Fork obligatorio.** Nadie clona ni escribe sobre el repositorio original.
- **Rama `data/anotacion-<serie>`**, con el prefijo `data/` de `CONTRIBUTING.md` §7.2.
- **Revisa el mantenedor** (`jss`), que es el CODEOWNER de `main`.
- **Una serie por PR, no todas juntas.** Un PR por serie permite detectar deriva de criterio
  temprano: si en la tercera serie empezaste a marcar `compuesta` con otro umbral, se ve en
  esa PR y no dentro de un bulto de diez series ya mezcladas.
- La Tarea C va en su propio PR, rama `data/anotacion-recall-IS1004`.

---

## 10. Checklist de cierre de serie

Marca solo lo verificado. Es el checklist del manual §7, con lo que este reparto agrega.
`uv run afg gold validate --annotator gv --series <ID>` ya cubre por ti los conjuntos
cerrados, las filas a medio llenar y que ninguna columna de máquina se haya tocado — no
hace falta revisarlos a ojo antes de correrlo, pero el checklist los deja explícitos porque
`validate` no juzga criterio (`sin_soporte` justificado, orden cronológico, `compuesta`
dividida con sentido).

### Tarea A
- [ ] El trabajo se hizo sobre `<serie>.decisions.gv.csv`; `<serie>.decisions.csv` quedó intacto
- [ ] Toda fila tiene `status` no vacío, del conjunto `decision | no_decision | compuesta | sin_soporte | descartar`
- [ ] Toda fila con `status = decision` tiene `decision_object` **y** `decision_content`
- [ ] Toda fila `compuesta` tiene sus filas hijas `-1`, `-2`, … creadas
- [ ] Ninguna fila hija quedó con `status = compuesta`
- [ ] Toda fila con `evidence_da_count = 0` fue revisada contra la transcripción
- [ ] Toda fila `sin_soporte` explica en `notes` qué dice la evidencia
- [ ] Las `no_decision` se conservaron: no se borró ninguna fila
- [ ] `annotator = gv` en todas las filas
- [ ] Ninguna columna de máquina quedó modificada, incluida `machine_flags`

### Tarea B
- [ ] El trabajo se hizo sobre `<serie>.candidates.gv.csv`; `<serie>.candidates.csv` quedó intacto
- [ ] Toda fila tiene `relation` del conjunto cerrado (ninguna vacía; `no_relacionada` es una etiqueta, no un vacío)
- [ ] `direction_ok` (`si` / `no`) está en todas las filas
- [ ] `confidence` (`alta` / `media` / `baja`) está en todas las filas
- [ ] Ninguna relación distinta de `no_relacionada` apunta a una decisión `sin_soporte`, `descartar` o `no_decision`
- [ ] La anotación se hizo en orden cronológico: primero los pares que terminan en `b`, luego `c`, luego `d`

### Independencia (solo Fases 1 y 2)
- [ ] No hubo comparación de etiquetas ni discusión de casos concretos con `gm` antes de la adjudicación

### Entrega
- [ ] Rama `data/anotacion-<serie>` desde `upstream/main` actualizado
- [ ] `uv run afg gold validate --annotator gv --series <ID>` sale sin errores
- [ ] Un PR con **esta serie sola**
- [ ] `uv run pytest -q` pasa
- [ ] Lo que no encajó quedó en `notes` y, si hace falta, en un issue "Hallazgo"
