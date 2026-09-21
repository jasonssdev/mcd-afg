# Tareas de Gustavo Martínez (`gm`)

> **Antes de la primera fila:** lee [`../annotation-guidelines.md`](../annotation-guidelines.md)
> (qué cuenta como decisión, qué significa cada relación) y ten
> [`../manual-anotacion-oe1.md`](../manual-anotacion-oe1.md) abierto al lado del CSV. Este
> documento dice **qué te toca y cómo lo entregas**; los criterios de etiquetado están allí y
> solo allí.

## Tu encargo en una frase

Anotar las Tareas A y B en nueve series (223 decisiones y 71 pares candidatos) y escribir el
banco de preguntas de OE4: mínimo 25 preguntas por cada uno de los cuatro estratos.

---

## 1. Tus series, en orden

Haz las fases en orden. No empieces la Fase 2 sin que ES2015 esté adjudicada.

### Fase 1 — Calibración (doble anotación con `gv`)

| Serie | Decisiones | Candidatos |
|---|---:|---:|
| ES2015 | 29 | 3 |

Serie de **desarrollo**, elegida a propósito: no se quema una serie de control aprendiendo
la guía. Este kappa es diagnóstico y no se reporta en la tesis
([`README.md`](README.md) §2).

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
| TS3009 | 24 | 4 | desarrollo |
| TS3011 | 23 | 5 | evaluación |
| IS1008 | 13 | 8 | evaluación |
| ES2014 | 23 | 14 | evaluación |
| **Total** | **83** | **31** | |

TS3009 va primera porque es serie de desarrollo: si algo del procedimiento individual falla,
falla sobre datos que ya estaban gastados.

### Tu carga total

**223 decisiones y 71 pares candidatos** (29 + 111 + 83 y 3 + 37 + 31), más el banco de
preguntas.

**Por qué llevas 37 decisiones menos que Germán.** Porque además escribes el banco: ≥100
preguntas a ~5 minutos cada una son unas 8 horas que él no tiene. El reparto equilibra horas
totales, no filas. A cambio llevas 10 pares candidatos más que él, que es donde está el
trabajo fino.

---

## 2. Qué archivo tocas y qué columnas llenas

### Tarea A — `data/processed/decisions/<serie>.decisions.csv`

**Nunca edites ese archivo.** Es el insumo limpio. Haz una copia con tus iniciales y trabaja
sobre ella:

```bash
cp data/processed/decisions/ES2015.decisions.csv \
   data/processed/decisions/ES2015.decisions.gm.csv
```

El patrón `<serie>.decisions.<iniciales>.csv` es una **convención nueva**, fijada en
[`README.md`](README.md) §5.1 como espejo del `<serie>.candidates.<iniciales>.csv` que el
manual ya definía para la Tarea B. Úsalo también en Fase 3, aunque anotes solo tú.

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
| **`annotator`** | **tú** | `gm` |
| **`notes`** | **tú** | Solo si algo no es obvio; obligatorio en `sin_soporte` |

**Valores permitidos de `status`:**

```
decision | no_decision | compuesta | sin_soporte | descartar
```

> Verificado: este conjunto está definido **solo en el manual §2**. No existe hoy en el
> código ningún `enum` que lo valide — `src/afg/domain/decision.py::DecisionStatus`
> (`accepted`, `open_proposal`, `open_question`, `opinion`) es el vocabulario del modelo de
> dominio, no el de esta columna. Nada te va a avisar si escribes mal un valor: cópialos
> literalmente de aquí.
>
> Los valores de `machine_flags` que sí produce el código son `sin_evidencia`,
> `posible_compuesta` y `frase_corta` (`src/afg/annotation/goldset.py::machine_flags_for`).
> `posible_compuesta` **no** es un `status`: es una sugerencia de que mires la fila.

### Tarea B — `data/processed/relations/<serie>.candidates.csv`

Misma regla: copia con tus iniciales,
`data/processed/relations/ES2015.candidates.gm.csv`.

| Columna | Quién | Regla |
|---|---|---|
| `pair_id` | máquina | **No tocar** |
| `earlier_decision_id` / `later_decision_id` | máquina | **No tocar** |
| `earlier_text` / `later_text` | máquina | **No tocar** |
| `blocker_score` | máquina | **No tocar** |
| **`relation`** | **tú** | Valor del conjunto cerrado, ver abajo |
| **`direction_ok`** | **tú** | `si` / `no` |
| **`confidence`** | **tú** | `alta` / `media` / `baja` |
| **`annotator`** | **tú** | `gm` |
| **`notes`** | **tú** | Obligatorio si `direction_ok = no` |

**Valores permitidos:**

```
relation      : introduce | reafirma | refina | revierte | reemplaza | no_relacionada
direction_ok  : si | no
confidence    : alta | media | baja
```

> Verificado: los seis valores de `relation` son literalmente los de
> `src/afg/domain/relation.py::RelationType`. `direction_ok` y `confidence` vienen del
> manual §4 y son los valores que usan las pruebas de acuerdo
> (`tests/test_agreement.py`). `direction_ok` se compara en minúsculas
> (`agreement.py`), así que escribe `si`, sin tilde y sin mayúscula.
>
> `no_relacionada` no es un valor vacío: significa *"el bloqueador se equivocó, aquí no hay
> relación"*, y el cálculo de acuerdo lo trata exactamente así
> (`agreement.py`, `_NO_RELATION_LABEL`). Una celda vacía y un `no_relacionada` no son lo
> mismo. Llena las 71 filas.

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

**Durante la Fase 1 y la Fase 2, tú y Germán NO comparan etiquetas ni discuten casos
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

### 6.1 Tarea A — fila `ES2015c.d08`, una `compuesta`

**Antes** (lo que te entrega la máquina, verbatim de `ES2015.decisions.csv`):

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
annotator          :
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

**Antes** (verbatim de `ES2015.candidates.csv`):

```
pair_id             : ES2015.p002
earlier_decision_id : ES2015c.elana.s.19
later_decision_id   : ES2015d.elana.s.15
earlier_text        : Regular chip will be used.
later_text          : Will use a regular chip.
blocker_score       : 1.0
relation            :
direction_ok        :
confidence          :
annotator           :
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

Mínimo **25 preguntas por estrato**, cuatro estratos, **≥100 en total**
(`docs/propuesta.md` §5.5). **El autor no valida y el validador no escribe**: tú no tocas
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

### El archivo

Plantilla con la cabecera y un ejemplo por estrato:
[`../../../data/processed/questions/_plantilla-banco-preguntas.csv`](../../../data/processed/questions/_plantilla-banco-preguntas.csv).
El banco real va en `data/processed/questions/banco-preguntas.csv`.

Las columnas salen del modelo `src/afg/domain/question.py::Question`, una por campo:

| Columna | Qué es |
|---|---|
| `id` | Identificador estable, `<serie>.q001` |
| `series_id` | Serie de la que sale la pregunta |
| `stratum` | Uno de los cuatro valores de arriba, literal |
| `text` | La pregunta, en español |
| `reference_answer` | La respuesta derivada de la evidencia. **Vacía en E4**: el modelo la declara `None` para ese estrato, porque ahí la referencia *es la ausencia de respuesta* |
| `reference_evidence` | Los actos de diálogo que la respaldan. Formato `reunion:da_id;da_id`, y `\|` entre reuniones cuando la evidencia abarca más de una. **Vacía en E4** |
| `author` | `gm` |
| `validated_by` | **Lo llena Germán.** Tú lo dejas vacío |

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

Una serie, un PR (`CONTRIBUTING.md` §2 y §3):

```bash
git fetch upstream
git checkout -b data/anotacion-ES2015 upstream/main
# ... anotas ...
git add data/processed/decisions/ES2015.decisions.gm.csv \
        data/processed/relations/ES2015.candidates.gm.csv
git commit -m "data(anotacion): tareas A y B de ES2015 (gm)"
git push -u origin data/anotacion-ES2015
# abres el PR desde tu fork contra main del repositorio original
```

- **Fork obligatorio.** Nadie clona ni escribe sobre el repositorio original.
- **Rama `data/anotacion-<serie>`**, con el prefijo `data/` de `CONTRIBUTING.md` §7.2.
- **Revisa el mantenedor** (`jss`), que es el CODEOWNER de `main`.
- **Una serie por PR, no todas juntas.** Un PR por serie permite detectar deriva de criterio
  temprano: si en la tercera serie empezaste a marcar `compuesta` con otro umbral, se ve en
  esa PR y no dentro de un bulto de diez series ya mezcladas.
- El banco de preguntas va aparte, rama `data/banco-preguntas`, y puede entregarse por
  estratos si prefieres PRs pequeños.

---

## 9. Checklist de cierre de serie

Marca solo lo verificado. Es el checklist del manual §7, con lo que este reparto agrega.

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
- [ ] ≥25 preguntas por cada uno de los cuatro estratos, ≥100 en total
- [ ] `stratum` usa los valores literales de `QuestionStratum`
- [ ] Cada respuesta de referencia se deriva de la evidencia citada, no del resumen
- [ ] Toda E4 se buscó en las cuatro transcripciones de su serie y no aparece
- [ ] `author = gm` en todas las filas; `validated_by` vacío (lo llena `gv`)

### Entrega
- [ ] Rama `data/anotacion-<serie>` desde `upstream/main` actualizado
- [ ] Un PR con **esta serie sola**
- [ ] `uv run pytest -q` pasa
- [ ] Lo que no encajó quedó en `notes` y, si hace falta, en un issue "Hallazgo"
