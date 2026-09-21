# Tareas de Jason Sepúlveda (`jss`)

> **Tu papel es distinto.** No anotas ninguna fila. Generas los insumos, adjudicas los
> desacuerdos de la doble anotación, escribes los registros de adjudicación, verificas que
> ninguna etiqueta de máquina se coló en el conjunto de referencia, y cierras OE1 con el
> notebook 03. Que quien adjudica no anote es una regla del diseño
> (`CONTRIBUTING.md` §1): si adjudicaras tus propias etiquetas, las finales quedarían
> sesgadas hacia uno de los tres.

## Tu encargo en una frase

Cerrar el bucle de calidad de OE1: adjudicar las cinco series de doble anotación una por
una, dejar cada decisión registrada por escrito, y garantizar que ninguna etiqueta del
conjunto de referencia la haya puesto una máquina.

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
- Los cuatro archivos están completos: ninguna celda humana vacía.
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
| `existence kappa` | ¿Hay relación, sí o no? Derivado de `relation`: todo lo distinto de `no_relacionada` cuenta como enlace existente | Lo anotas en la cabecera del registro |
| `type kappa` | La etiqueta concreta, **solo sobre los pares que ambas personas marcaron como enlace existente** | Lo anotas. Puede salir `n/a` si ningún par fue marcado como enlace por los dos: no es un error |
| `direction kappa` | El valor de `direction_ok`, sobre todos los pares emparejados | Lo anotas |
| `... disagreements (adjudicate): <pair_ids>` | La lista exacta de pares a resolver | **Es tu orden del día.** Una fila del registro por cada uno |
| `Wrote reports/tables/<serie>.agreement.csv` | La tabla con los tres ejes | Entra al PR de adjudicación |

Los tres kappas se reportan **por separado, nunca combinados en uno**: `existence` y
`direction` pueden ser perfectos mientras `type` no lo es, y colapsarlos escondería
exactamente el modo de falla de H3 que la tesis mide (`agreement.py`,
`SeriesAgreementResult`).

**Errores que puede devolver el comando** (`AgreementInputError`, y el chequeo previo del
CLI):

- *"Need at least 2 annotator files…"* — falta un archivo, o su nombre no sigue
  `<serie>.candidates.<iniciales>.csv`. Es de nombre, no de contenido.
- *"share no pair_id in common"* — alguien editó la columna `pair_id`, o trabajó sobre un
  insumo regenerado. Hay que volver al insumo original.
- Si aparecen **más de dos** archivos, el comando avisa y usa los dos primeros por orden
  alfabético, porque el kappa de Cohen es por pares. Con `gv` y `gm` no debería ocurrir.

### 2.3 Los kappas de calibración no se reportan

El de ES2015 es **diagnóstico**: responde "¿entendimos los dos lo mismo?" y no entra en la
tesis. Si sale bajo, se corrige `annotation-guidelines.md` o el manual —en su propio PR—
**antes** de tocar ES2016, y se recalibra. Los cuatro kappas de las series de control sí se
reportan, tal como salgan: son el 36,4 % del conjunto de evaluación que exige el
ADR [0005](../../decisions/0005-adr-development-evaluation-split.md).

### 2.4 La Tarea A se adjudica a mano

**Limitación conocida** ([`README.md`](README.md) §5.2): `afg gold agreement` busca
`f"{series}.candidates.*.csv"` (`src/afg/cli.py`), así que **sus tres kappas son todos de la
Tarea B**. El acuerdo sobre la columna `status` no lo calcula el CLI hoy.

Mientras no exista el comando, la Tarea A se adjudica **leyendo los dos archivos en
paralelo**, alineados por `decision_id`, y comparando `status`. Una forma rápida de sacar la
lista de desacuerdos, solo para preparar la sesión —el veredicto lo pones tú:

```bash
python3 - <<'PY'
import csv
a = {r["decision_id"]: r for r in csv.DictReader(open("data/processed/decisions/ES2015.decisions.gv.csv"))}
b = {r["decision_id"]: r for r in csv.DictReader(open("data/processed/decisions/ES2015.decisions.gm.csv"))}
for k in sorted(set(a) & set(b)):
    if a[k]["status"].strip() != b[k]["status"].strip():
        print(k, a[k]["status"], "|", b[k]["status"])
PY
```

Las filas `compuesta` necesitan atención aparte: si una persona dividió una frase en tres
hijas y la otra en cuatro, los `decision_id` hijos no coinciden y no hay nada que alinear. Se
resuelve sobre la fila **madre**, y la división final se decide en la sesión.

---

## 3. El registro de adjudicación

**Limitación conocida** ([`README.md`](README.md) §5.3): `build_adjudication_log()` existe en
`src/afg/annotation/agreement.py` y tiene pruebas en `tests/test_annotation.py`, pero **nadie
la invoca desde el CLI** — no hay `afg gold adjudicate`. El archivo se escribe **a mano**.

Uno por serie, en `data/processed/relations/<serie>.adjudication.md`, desde la plantilla
[`../plantilla-adjudicacion.md`](../plantilla-adjudicacion.md), para que los cinco salgan
comparables entre sí.

Lo que no puede faltar en ninguno:

1. Los **tres kappas** en la cabecera, con la fecha y quién anotó.
2. **Una fila por desacuerdo**, con la etiqueta de cada persona, la final y la **razón**. La
   razón es el contenido real del documento: sin ella, el registro es una lista de veredictos
   sin criterio, y el criterio es lo que hay que poder aplicar igual en la serie siguiente.
3. Una sección de cierre que diga **si el desacuerdo revela un vacío de la guía**. Si dos
   personas competentes discreparon, la primera hipótesis es que la guía no decidía el caso,
   no que una de las dos se equivocó.

Cuando exista `afg gold adjudicate`, se recalculará sobre los archivos ya guardados. Por eso
la convención de nombres de [`README.md`](README.md) §5.1 importa aunque hoy nadie la lea de
forma automática.

---

## 4. Verificación: ninguna etiqueta de máquina en el conjunto de referencia

Es la verificación que sostiene OE4. `CONTRIBUTING.md` §7.6 y el manual §0 lo dicen igual:
la máquina puede extraer candidatos, resolver evidencia, proponer qué pares mirar y marcar
señales de revisión; **no puede decidir si algo es una decisión ni qué relación hay entre
dos**. `machine_flags` es una sugerencia; `status` y `relation` los llena una persona.

Si un modelo hubiera puesto esas etiquetas, C3 —*"la misma representación sin errores de
extracción"*— tendría errores de extracción por construcción, y la brecha C2 − C3, que es
todo OE4, dejaría de medir nada.

Qué revisas en cada PR de anotación, antes de mergear:

- [ ] Las columnas de máquina llegan **byte a byte iguales** al insumo:
      `decision_id`, `meeting_id`, `source_sentence_id`, `sentence_text`,
      `evidence_da_count`, `evidence_text`, `machine_flags` en decisiones;
      `pair_id`, `earlier_decision_id`, `later_decision_id`, `earlier_text`, `later_text`,
      `blocker_score` en candidatos. Un `git diff` que las toque es motivo de devolución.
- [ ] `annotator` está lleno en todas las filas, con `gv` o `gm`, nunca vacío ni con otro
      valor.
- [ ] `status` **no** es una copia de `machine_flags`. Si una serie tiene `compuesta`
      exactamente en las filas con `posible_compuesta` y en ninguna otra, revísalo: puede ser
      coincidencia, pero también puede ser que alguien haya transcrito la bandera.
- [ ] Los valores están dentro de los conjuntos cerrados. No hay `enum` que los valide en el
      código, así que la validación es esta revisión.
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
- Cualquiera que sea la decisión, se escribe: en `docs/BACKLOG.md` si cambia una cifra
  publicada, o en un ADR si cambia el procedimiento.

---

## 6. Un ejemplo resuelto — una sesión de adjudicación

**El ejemplo sale de ES2015 (serie de desarrollo) a propósito**: un registro de adjudicación
real de una serie de control contiene contenido de evaluación, y este documento lo lee todo
el equipo.

Supongamos que en la calibración `afg gold agreement --series ES2015` imprime un desacuerdo
de tipo en `ES2015.p001`. El par, verbatim del insumo:

```
pair_id             : ES2015.p001
earlier_decision_id : ES2015a.elana.s.11
later_decision_id   : ES2015b.elana.s.11
earlier_text        : It will be a television remote control.
later_text          : The remote will be a single function design- television only.
blocker_score       : 0.6666666666666666
```

`gv` puso `refina`; `gm` puso `reafirma`. La fila que escribes en el registro:

| `pair_id` | `gv` | `gm` | Final | Razón |
|---|---|---|---|---|
| `ES2015.p001` | `refina` | `reafirma` | `refina` | La posterior conserva el objeto (control de televisión) y **agrega** un límite que antes no estaba: función única, sin DVD ni VCR. `reafirma` exige que el contenido no cambie; aquí cambió por acotación, que es la definición de `refina`. |

Y en la sección de cierre:

> Este desacuerdo revela un vacío: la guía no dice si **excluir** alternativas cuenta como
> agregar detalle. Propuesta de corrección de `annotation-guidelines.md`: en `refina`,
> precisar que acotar incluye excluir explícitamente opciones que la decisión anterior dejaba
> abiertas.

**Por qué el veredicto es `refina` y no `reafirma`.** Las dos etiquetas se distinguen por una
sola cosa —si el contenido cambió— y aquí cambió: `ES2015a` no excluía la multifunción y
`ES2015b` sí. Que el desacuerdo caiga justo en el borde entre dos etiquetas vecinas es la
señal típica de un vacío de la guía, no de un descuido de una de las dos personas; por eso
la fila lleva razón **y** el cierre lleva propuesta de corrección.

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
git checkout -b data/adjudicacion-ES2015 upstream/main
uv run afg gold agreement --series ES2015
# escribes data/processed/relations/ES2015.adjudication.md desde la plantilla
git add data/processed/relations/ES2015.adjudication.md reports/tables/ES2015.agreement.csv
git commit -m "data(adjudicacion): resolver desacuerdos de ES2015 y registrar kappas"
```

Nunca push directo a `main`, ni para cambios triviales.

---

## 10. Checklist de cierre de adjudicación

### Antes de la sesión
- [ ] Los cuatro archivos de la serie están mergeados y completos
- [ ] Ninguna celda humana quedó vacía en ninguno de los cuatro
- [ ] Las columnas de máquina llegaron intactas en los cuatro (§4)
- [ ] `uv run afg gold agreement --series <ID>` corre sin error
- [ ] La lista de desacuerdos de la Tarea B está impresa
- [ ] La lista de desacuerdos de `status` de la Tarea A está sacada a mano (§2.4)

### Durante
- [ ] Cada desacuerdo tiene etiqueta final **y razón escrita**
- [ ] Las filas `compuesta` con divisiones distintas se resolvieron sobre la fila madre
- [ ] Se anotó si el desacuerdo revela un vacío de la guía

### Después
- [ ] `data/processed/relations/<serie>.adjudication.md` escrito desde la plantilla
- [ ] `reports/tables/<serie>.agreement.csv` versionado
- [ ] Los tres kappas están en la cabecera del registro, por separado
- [ ] Si hay vacío de guía: PR de corrección de `annotation-guidelines.md` o del manual,
      **antes** de abrir la serie siguiente
- [ ] Si la serie es de calibración: queda escrito que ese kappa **no se reporta**
- [ ] `uv run pytest -q`, `uv run ruff check .` y `uv run mypy src/afg` pasan
