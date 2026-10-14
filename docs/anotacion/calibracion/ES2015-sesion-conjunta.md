# ES2015: sesión conjunta de criterios

> **Qué es este documento.** El material de trabajo para la sesión de `jss`, `gv` y `gm` sobre
> los 16 desacuerdos de estado de ES2015. No define reglas: reúne los casos y las
> preguntas. El criterio que salió de estos mismos casos ya está en el manual
> ([`../manual-anotacion-oe1.md`](../manual-anotacion-oe1.md), «La regla de oro» y
> «Criterio de umbral», §2).

## Para qué es la sesión

La calibración sobre ES2015 dio un kappa de estado de 0,094: 13 de
29 filas coinciden. Casi todos los desacuerdos son de umbral y la guía no tenía un
criterio para ellos. La sesión busca que las tres personas lean el umbral de la misma manera
**antes** de recalibrar sobre TS3009 (ver [`../asignacion/README.md`](../asignacion/README.md),
Fase 1).

## Reglas de la sesión

1. **Se hace después de adjudicar.** ES2015 ya está adjudicada, así que se pueden comparar
   etiquetas de ES2015 sin romper la independencia de la Fase 1 (que rige para las series
   que aún se anotan).
2. **El objetivo es alinear criterios, no readjudicar.** Los veredictos de `jss` en
   `data/processed/decisions/ES2015.decisions.adjudicated.csv` no se reabren. Si alguien
   cree que un veredicto es un error, se anota para `jss` fuera de la sesión.
3. **Cada caso se discute para sacar la regla**, no para decidir quién tenía razón. Lo que
   se acuerde se escribe en el manual, en su propio PR.
4. **TS3009 queda fuera.** Nadie comenta casos de TS3009 ni lo anota antes de la sesión;
   la recalibración solo mide algo si las dos anotaciones son independientes.
5. **Solo se citan frases de ES2015**, que es serie de desarrollo (ADR
   [0005](../../decisions/0005-adr-development-evaluation-split.md)).

## Los 16 desacuerdos

Tabla generada con `afg.annotation.calibration.disagreement_groups("ES2015")` a partir del CSV
adjudicado. «Final» es el estado que fijó `jss`; «Con quién» indica con cuál de las dos
personas coincidió (`ninguno` si con ninguna). Resumen de a qué lado fue el veredicto:
gm: 13, gv: 2, ninguno: 1.


### `gm` dice `decision`, `gv` dice `no_decision` (6)

| Decisión | Frase | `gm` | `gv` | Final | Con quién | Razón de `jss` |
|---|---|---|---|---|---|---|
| `ES2015a.d01` | It will be a television remote control. | `decision` | `no_decision` | `decision` | gm | Me da a entender que se esta definiendo la creacion de un nuevo producto y en esta reunion se define que se quiere un nuevo control remoto, de hecho el PM dice `we want this to be a marketable product that can be trendy` |
| `ES2015a.d03` | The profit will be fifty million Euros. | `decision` | `no_decision` | `no_decision` | gv | No es una decision, es una meta financiera |
| `ES2015b.d02` | Teletext is outdated and will not be used. | `decision` | `no_decision` | `decision` | gm | es una decision, pues se da un input y se decide en las siguientes linas, creo que es importante que si la decision se toma en las lineas posteriores sigue siendo una decision, es parte del problema de como se formulan las decision |
| `ES2015b.d05` | Alarm locator will be implemented. | `decision` | `no_decision` | `decision` | gm | La primera frase suena como una sugerencia pero si se lee la transcripcion podemos ver que se reafirma que es como se suelen generar las decisiones |
| `ES2015d.d04` | Will use a regular chip. | `decision` | `no_decision` | `decision` | gm | el PM dice que estaran usando un chip estandar y luego se reafirma la decision por el siguiente hablante |
| `ES2015d.d06` | Will be made of plastic and rubber (rubber on remote for comfort). | `decision` | `no_decision` | `decision` | gm | Se usara plastico para el cuerpo y goma para los botones |

### `gm` dice `decision`, `gv` dice `sin_soporte` (8)

| Decisión | Frase | `gm` | `gv` | Final | Con quién | Razón de `jss` |
|---|---|---|---|---|---|---|
| `ES2015b.d06` | Glow in the dark buttons, self-timed lighting. | `decision` | `sin_soporte` | `decision` | gm | porque mas adelante se habla de los tipos de luz que podria tener |
| `ES2015b.d08` | Will research changable covers. | `decision` | `sin_soporte` | `decision` | gm | Es una decision de producto |
| `ES2015b.d09` | Will reserach environmental factor. | `decision` | `sin_soporte` | `no_decision` | ninguno | se pospone la decision del impacto ambiental no hay una solucion ecologica en la transcripcion |
| `ES2015c.d02` | Control will light up when you touch a button. | `decision` | `sin_soporte` | `decision` | gm | porque el PM lo reafirma |
| `ES2015c.d04` | The remote will run on kinetic energy. | `decision` | `sin_soporte` | `decision` | gm | Usa la palbra que nosotros hemos decidido |
| `ES2015c.d05` | Push buttons will be used. | `decision` | `sin_soporte` | `decision` | gm | Prefieron seguir con el diseno de tener botones que se pulsan en vez de una pantalla LCD |
| `ES2015d.d03` | Will be two colors, one for case and one for buttons. | `decision` | `sin_soporte` | `decision` | gm | Se habla de tener 2 colores distintos uno para los botones y otro para la carcasa |
| `ES2015d.d05` | The remote will be double-curved. | `decision` | `sin_soporte` | `decision` | gm | el PM expone y los demas reafirma, entonces es una decision de diseno |

### `gm` dice `compuesta`, `gv` dice `decision` (1)

| Decisión | Frase | `gm` | `gv` | Final | Con quién | Razón de `jss` |
|---|---|---|---|---|---|---|
| `ES2015b.d04` | No LCD, no voice recognition. | `compuesta` | `decision` | `compuesta` | gm | Son 3 exclusiones; el teletexto se descarta por duplicar ES2015b.d02 |

### `gm` dice `decision`, `gv` dice `compuesta` (1)

| Decisión | Frase | `gm` | `gv` | Final | Con quién | Razón de `jss` |
|---|---|---|---|---|---|---|
| `ES2015d.d02` | Casing will be interchangable and color schemes will be named and colored after fruits and vegetables. | `decision` | `compuesta` | `compuesta` | gv | La frase reúne dos decisiones separables: la carcasa intercambiable y los nombres y colores de frutas y verduras. Una podría cambiar en otra reunión sin la otra. |

## Preguntas para discutir

0. **Primero: evidencia frente a transcripción.** La guía anterior decía que, si
   `evidence_text` no dice lo que dice la frase, la fila es `sin_soporte`. Aplicada al pie de
   la letra, esa regla lleva a las 8 filas `sin_soporte` de `gv`: el error estuvo en la
   guía, no en quien anotó. La adjudicación juzgó con la transcripción de la reunión, y la
   regla de oro del manual (§2) ahora lo dice así: si `evidence_text` no alcanza, se lee la
   transcripción de esa misma reunión, y `sin_soporte` es solo cuando la transcripción la
   contradice o no la contiene. ¿Queda claro dónde está la transcripción y cómo buscar en
   ella?
1. **Propuesta aceptada.** ¿Basta con que otro participante la confirme o que las líneas
   siguientes la adopten para que sea `decision`, aunque la frase original sea tentativa?
   (`ES2015b.d02`, `ES2015b.d05`, `ES2015c.d02`, `ES2015d.d05`.)
2. **«Will research…».** `ES2015b.d08` y `ES2015b.d09` tienen la misma forma («Will
   research…») y terminaron en `decision` y `no_decision`. ¿Qué rasgo del diálogo las separa?
3. **Meta frente a diseño.** `ES2015a.d03` (meta de ganancia) quedó `no_decision` y
   `ES2015a.d01` (qué producto se hace) quedó `decision`. ¿Dónde pasa la línea entre una
   meta o aspiración y una decisión de producto?
4. **Pregunta de confirmación.** «We decided on kinetic, right?» (`ES2015c.d04`,
   `ES2015c.d05`): ¿es `decision` por la palabra «decided», `no_decision` por el tono, o
   `sin_soporte`?
5. **Evidencia parcial.** Cuando `evidence_text` cubre solo una parte de la frase
   (`ES2015d.d03`, `ES2015d.d05`) o el detalle aparece más adelante (`ES2015b.d06`), ¿cuánto
   hay que leer de la transcripción y desde cuándo la fila deja de ser `sin_soporte`?
6. **`sin_soporte` o `no_decision`.** Varias filas que `gv` marcó `sin_soporte` dicen en sus
   notas que la transcripción no es explícita o tiene otro tono. ¿Eso es falta de soporte
   (la evidencia no contiene lo que dice la frase) o es una propuesta no aceptada?
7. **Las `compuesta`.** `ES2015b.d04` y `ES2015d.d02` ya están cubiertas por la regla de
   separabilidad del manual (§2). ¿Alguna duda que esa regla no resuelva?
8. **Qué se ajusta.** El criterio de umbral ya está en el manual (§2). ¿Algún caso de esta
   sesión que no resuelva? Lo que se acuerde pasa al manual en su propio PR, antes de abrir
   TS3009.

## Después de la sesión

`jss` lleva al manual lo que se acuerde, si algo cambia. Luego
`gv` y `gm` anotan TS3009 por separado, siguiendo la secuencia de la Fase 1.
