# Anotación humana: empieza aquí

Esta carpeta reúne todo lo que hace una **persona**, no la máquina, para construir el
conjunto de referencia de OE1. Si vas a anotar, este es tu punto de entrada; no necesitas
leer el código.

| Documento | Qué es | Cuándo leerlo |
|---|---|---|
| [`asignacion/EMPIEZA-AQUI.md`](asignacion/EMPIEZA-AQUI.md) | Una página: clona, instala, `prepare`, llena, `validate`, PR | Si nunca has abierto este repositorio |
| Este README | Quién hace qué, en qué orden, con qué archivos y cuánto toma | Primero |
| [`annotation-guidelines.md`](annotation-guidelines.md) | Qué cuenta como decisión y qué significa cada una de las seis relaciones | Antes de anotar la primera fila |
| [`manual-anotacion-oe1.md`](manual-anotacion-oe1.md) | El manual operativo: qué archivo abres, qué columna llenas, qué escribes, con un ejemplo real resuelto de punta a punta | Con el CSV abierto al lado |
| [`asignacion/`](asignacion/) | El reparto concreto: qué serie le toca a cada persona, en qué orden, cuándo se adjudica. `config/annotation.toml` es la fuente de verdad; `afg gold status` muestra el avance en vivo | Antes de abrir tu primera serie |
| [`plantilla-adjudicacion.md`](plantilla-adjudicacion.md) | La plantilla original de `<serie>.adjudication.md`, de cuando se escribía a mano. `uv run afg gold adjudicate --series <ID>` lo escribe hoy por ti | Referencia, si quieres ver el formato sin correr el comando |

## Quién hace qué

| Persona | Rol | Tareas |
|---|---|---|
| Germán Vega (`gv`) | Anotador | Tareas A, B, C y D |
| Gustavo Martínez (`gm`) | Anotador | Tareas A, B, C y D |
| Jason Sepúlveda (`jss`) | Adjudicador | Resuelve los desacuerdos de la Tarea D; no anota |

Las dos personas que anotan lo hacen **de forma independiente**: nadie ve las etiquetas de
la otra antes de la sesión de adjudicación. Quien adjudica no anota, para que las etiquetas
finales no queden sesgadas hacia uno de los dos anotadores.

El reparto serie por serie, con las cifras de cada una y el orden de ejecución, está en
[`asignacion/README.md`](asignacion/README.md), y cada persona tiene su propio documento:
[`asignacion/tareas-gv.md`](asignacion/tareas-gv.md),
[`asignacion/tareas-gm.md`](asignacion/tareas-gm.md) y
[`asignacion/tareas-jss.md`](asignacion/tareas-jss.md).

## La regla que no se negocia

La máquina extrae las decisiones, resuelve la evidencia, propone qué pares mirar y calcula
el acuerdo. **La máquina nunca decide si algo es una decisión ni qué relación hay entre
dos decisiones.** Sus sugerencias van en la columna `machine_flags`; la columna `status` y la
columna `relation` las llena una persona. Si un modelo pusiera esas etiquetas, la condición
C3 tendría errores de extracción por construcción y el objetivo OE4 dejaría de medir nada.

## Qué series puedes mirar

| Series | Qué son | Qué puedes hacer |
|---|---|---|
| ES2015, IS1004, TS3009 | Desarrollo | Leer todo; aquí se practica y se ajustan criterios |
| ES2008, ES2016, IS1003, TS3005 | Control (doble anotación) | Anotar ambas personas, por separado |
| ES2002, ES2014, IS1006, IS1008, IS1009, TS3003, TS3011 | Evaluación | Anotar; **no** leer su contenido fuera de la anotación |

Leer decisiones o transcripciones de evaluación fuera del flujo de anotación contamina los
resultados (ver [`../decisions/0005-adr-development-evaluation-split.md`](../decisions/0005-adr-development-evaluation-split.md)).

## El flujo, en orden

Todo ocurre dentro de dos archivos CSV por serie, que genera el CLI. Nunca abres un XML.

```bash
uv run afg gold build --series IS1004        # -> data/processed/decisions/IS1004.decisions.csv
# Tarea A: llenas status, decision_object, decision_content, annotator, notes
uv run afg gold candidates --series IS1004   # -> data/processed/relations/IS1004.candidates.csv
# Tarea B: llenas relation, direction_ok, confidence, annotator, notes
uv run afg gold recall-sample --series IS1004 --n 50 --seed 42   # Tarea C
uv run afg gold agreement --series IS1004    # Tarea D: kappa por existencia, tipo y dirección
```

| Tarea | Qué haces | Archivo | Ritmo | Horas (14 series) |
|---|---|---|---|---|
| **A** Normalizar decisiones | Lees la evidencia, decides `status`, escribes objeto y contenido | `data/processed/decisions/<serie>.decisions.csv` | ~30 s por fila | ≈ 3 h (343 filas) |
| **B** Adjudicar pares | Eliges la relación entre dos decisiones de reuniones distintas | `data/processed/relations/<serie>.candidates.csv` | 1–2 min por par | ≈ 2–3 h (92 pares) |
| **C** Muestra de recall | Anotas 50 pares que el filtro rechazó, para medir qué se perdió | `data/processed/relations/<serie>.recall-sample.csv` | 1–2 min por par | ≈ 1–2 h |
| **D** Doble anotación | La segunda persona repite A y B sobre copia limpia; se calcula kappa y se adjudica | `<serie>.candidates.<iniciales>.csv` y `<serie>.adjudication.md` | como A y B | ≈ 3 h por persona |

El orden dentro de cada serie es **cronológico**: primero la reunión a, luego b, c, d. No se
mira una reunión posterior para etiquetar una anterior.

## Tres reglas que evitan los errores más comunes

1. **Lee `evidence_text` antes de llenar nada.** Si la evidencia no dice lo que dice la frase
   del resumen, el `status` es `sin_soporte`, aunque la frase suene razonable. El resumen
   oficial de AMI ya tiene al menos un error demostrado (el botón turbo, manual §3).
2. **`evidence_da_count = 0` es sospecha inmediata.** Busca la evidencia con
   `uv run afg gold evidence --meeting <ID> --term <palabra>` antes de decidir.
3. **La dirección importa.** En un par, la decisión posterior actúa sobre la anterior: "la de
   diciembre revierte la de octubre", nunca al revés. La hipótesis H3 depende de esto.

## Dónde queda el resultado y cómo se entrega

- Los CSV anotados se suben por pull request, como cualquier otro cambio
  ([`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) §2). La revisión la hace otra persona.
- El checklist de cierre por serie está en el manual, §7, y ampliado en el documento
  personal de cada quien dentro de [`asignacion/`](asignacion/). Una serie no está terminada
  hasta que todo el checklist está marcado.
- El acuerdo entre anotadores se reporta **tal como salga**. Un kappa bajo no es un fracaso:
  es lo que OE1 se propuso medir.

## Qué hacer si algo no encaja

Si una fila no cabe en ninguna etiqueta, si la cronología del archivo parece incorrecta, o si
encuentras una relación real cuyo extremo anterior no aparece como decisión, **no lo
descartes en silencio**: escríbelo en `notes` y abre un issue con la plantilla "Hallazgo".
Esos casos son parte del resultado.
