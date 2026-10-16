# Manual operativo de anotación — OE1

> **Qué es este documento.** El paso a paso físico: qué archivo abrir, qué columna llenar,
> qué escribir. La definición conceptual de "decisión" y del conjunto de relaciones vive en
> [`annotation-guidelines.md`](annotation-guidelines.md); este documento asume que ya la
> leíste y te dice cómo ejecutarla.
>
> **Idioma.** Este documento y las etiquetas de anotación van en español porque sus lectores
> son anotadores humanos y porque el protocolo se cita en la tesis. El código, la
> configuración y el README del repositorio siguen en inglés.

---

## 0. Lo primero: qué NO es el trabajo manual

Hay que sacarse esta idea de encima antes de empezar.

**Nunca vas a abrir un archivo XML.** El corpus AMI son 228 MB de NXT con punteros cruzados
entre capas. Leer eso a mano es imposible y además innecesario: las herramientas resuelven
la cadena `resumen → acto de diálogo → palabras` y te entregan **dos archivos CSV** con el
texto ya resuelto. Tu trabajo ocurre íntegramente dentro de esos dos CSV.

Reparto real del trabajo:

| Tarea | Quién |
|---|---|
| Extraer las decisiones de las capas de AMI | Máquina |
| Resolver la evidencia (frase → actos → transcripción) | Máquina |
| Proponer qué pares de decisiones mirar | Máquina |
| **Decidir si algo es una decisión** | **Humano** |
| **Decidir qué relación hay entre dos decisiones** | **Humano** |
| Calcular kappa, generar reportes y el banco de preguntas | Máquina |

**La regla que no se negocia:** cada *etiqueta* la pone un humano. Si un modelo construye el
conjunto de referencia, OE2 mide un modelo contra un modelo, y C3 —definida como *"la misma
representación sin errores de extracción"*— tiene errores de extracción por construcción.
La brecha C2−C3, que es todo OE4, se vuelve ruido. La máquina decide **qué mirar**; tú
decides **qué dice**.

---

## 1. Preparación (comandos, no trabajo manual)

> **Estado de implementación (2026-09-20).** Todos los comandos que usa este manual están
> implementados y con tests (ver `README.md`, sección "Comandos del proyecto").

**Quien anota corre solo `setup`, `prepare`, `validate` y `evidence`** (y `status`, de solo
lectura). `build` y `candidates` los corre quien mantiene el repositorio, ya los corrió, y
volver a correrlos sobrescribe el insumo. La tabla de abajo los lista como referencia.

| Comando | Para qué |
|---|---|
| `uv run afg corpus download` | Descarga el corpus (una sola vez por máquina) |
| `uv run afg corpus inventory` | Verifica que el corpus está completo |
| `uv run afg gold build --series <ID>` | (mantenedor) Genera el CSV de decisiones de la Tarea A |
| `uv run afg gold candidates --series <ID>` | (mantenedor) Genera el CSV de pares candidatos de la Tarea B |
| `uv run afg gold recall-sample --series <ID> --n 50 --seed 42` | (mantenedor) Genera la muestra de la Tarea C |
| `uv run afg gold evidencia --meeting <ID> --term <palabra>` | Busca en la transcripción: evidencia de la Tarea A cuando `evidence_da_count` es 0, o ids de acto para el banco de preguntas |
| `uv run afg gold agreement --series <ID>` | (adjudicador) Calcula el kappa de la Tarea D |

Para una serie, el flujo del mantenedor (no el tuyo) fue:

```bash
uv run afg gold build      --series IS1004   # -> data/processed/decisions/IS1004.decisions.csv
uv run afg gold candidates --series IS1004   # -> data/processed/relations/IS1004.candidates.csv
```

El segundo comando **no depende** de que el primero esté adjudicado: hoy los candidatos se
generan sobre las frases crudas del resumen abstractivo
(`afg.annotation.blocking.decisions_from_abstractive`), no sobre las decisiones ya
normalizadas de la Tarea A. Es un comportamiento provisional —lo dice también
`uv run afg gold candidates --help`— hasta que exista la normalización real de la Tarea A
como fuente. Por eso el ejemplo trabajado de la sección 4 usa como extremo posterior
`IS1004d.d12`, una fila que la Tarea A termina marcando `sin_soporte`: el par se genera
igual, y descartarlo es trabajo de la adjudicación humana, no del comando.

---

## 2. Tarea A — Normalizar decisiones

**Archivo que abres:** `data/processed/decisions/IS1004.decisions.gv.csv` — tu copia, con
tus iniciales (ejemplo ilustrativo; IS1004 se abre en la Fase 3). **Nunca edites `IS1004.decisions.csv`** (el archivo sin iniciales): es el
insumo limpio que genera `afg gold build`. Si anotas ahí, `afg gold prepare` no lo detecta
—solo mira si tu propio `<serie>.decisions.<iniciales>.csv` ya tiene anotación— y genera tu
copia con las columnas humanas vacías: el trabajo desaparece sin ningún error en pantalla.
**Herramienta:** un editor de texto o de hojas de cálculo (ver el recuadro de abajo).
**Ritmo esperado:** ~30 segundos por fila.

> **Editar el CSV.** Editores recomendados: VS Code o LibreOffice Calc. Excel sirve solo si
> guardas con **«CSV UTF-8 (delimitado por comas)»**; nunca con «CSV» a secas, que rompe las
> tildes. El separador debe ser la **coma**. Si `afg gold validate` falla en la primera
> columna, casi siempre es la codificación o el separador (por ejemplo, el archivo quedó con
> `;`): vuelve a guardarlo con comas y UTF-8. Un BOM al inicio del archivo (lo que escribe
> Excel con «CSV UTF-8») se acepta.

### Columnas

| Columna | Quién la llena | Qué es |
|---|---|---|
| `decision_id` | máquina | `IS1004c.d03`. No lo toques |
| `meeting_id` | máquina | `IS1004c` |
| `source_sentence_id` | máquina | `IS1004c.elana.s.29` — trazabilidad al XML |
| `sentence_text` | máquina | La frase del resumen abstractivo, literal |
| `evidence_da_count` | máquina | Cuántos actos de diálogo la respaldan |
| `evidence_text` | máquina | La transcripción de esos actos |
| `machine_flags` | máquina | Sugerencia de triaje (no un veredicto): `sin_evidencia`, `posible_compuesta`, `frase_corta`, separadas por `;` |
| **`status`** | **tú** | Ver tabla abajo |
| **`decision_object`** | **tú** | Qué se decide |
| **`decision_content`** | **tú** | Qué se decidió al respecto |
| **`annotator`** | **tú** | Tus iniciales |
| **`notes`** | **tú** | Solo si algo no es obvio |

### Valores permitidos de `status`

| Valor | Cuándo |
|---|---|
| `decision` | Cumple las tres condiciones de §5.2: explícita, aceptada, anclada |
| `no_decision` | Propuesta abierta, pregunta u opinión. **Se conserva**: mide falsos positivos |
| `compuesta` | La frase contiene N decisiones. Se divide (ver abajo) |
| `sin_soporte` | La evidencia no respalda lo que la frase afirma |
| `descartar` | Frase truncada, rota o ininteligible, o que repite una decisión ya anotada en la misma reunión (ver abajo) |

**`compuesta` no es un veredicto final, es una instrucción.** Marcas la fila original como
`compuesta` y creas N filas nuevas con `decision_id` sufijado `-1`, `-2`, … copiando
`source_sentence_id` y `evidence_text`. Cada fila nueva lleva su propio
`decision_object` / `decision_content` y su `status`.

**Cuándo una frase es `compuesta`.** Cuando reúne **decisiones separables sobre objetos
distintos**. La prueba: *¿podría una reunión posterior cambiar o revertir una parte sin tocar
la otra?* Si sí, se divide, porque cada parte puede tener su propia relación con otras
reuniones (el caso del turbo en §3: en `d` se elimina solo el botón turbo). Si no, es una
sola decisión. No se dividen:

- los **atributos** de un mismo objeto ("botón turbo, posiblemente en la cara inferior" es
  una decisión: la existencia del botón; la ubicación va a `notes`);
- la **razón** de una decisión ("goma, por comodidad" es una decisión);
- una frase larga con un solo objeto: el criterio es la separabilidad, no la longitud.

Ejemplo de calibración (ES2015): *"Casing will be interchangeable and color schemes will be
named and colored after fruits and vegetables"* se divide en dos —carcasa intercambiable y
nombres y colores de los esquemas— porque una puede cambiar sin la otra.

**Una decisión repetida dentro de la misma reunión se anota una sola vez.** Si dos filas de
la misma reunión describen la misma decisión (por ejemplo, una frase propia y la hija de una
`compuesta`), conservas la fila cuya frase la enuncia de forma explícita y marcas la otra
`descartar`, con `notes` (o `razon`, al adjudicar) indicando qué fila duplica: *"duplica
ES2015b.d02"*. Así la reunión no suma una decisión de más ni aparece un par de la decisión
consigo misma.

### La regla de oro

> **Lee `evidence_text` antes de llenar nada. Si no alcanza para juzgar la frase, lee la
> transcripción de esa misma reunión. El status es `sin_soporte` solo si la transcripción
> de la reunión contradice lo que dice `sentence_text` o no lo contiene — aunque la frase
> suene perfectamente razonable.**

`evidence_text` son solo los actos de diálogo que AMI enlazó a la frase, y a menudo es un
fragmento corto que no dice mucho. Que la evidencia sea pobre **no** es, por sí solo, falta
de soporte: antes de marcar `sin_soporte`, busca el pasaje completo.

- **Dónde está la transcripción:** `data/interim/transcripts/<reunión>.md` (por ejemplo,
  `ES2015d.md`). Para buscar un término dentro de ella:
  `uv run afg gold evidencia --meeting <ID> --term <palabra>`.
- **Qué puedes leer:** lo que se dice antes y después en **la misma reunión**. Nunca
  reuniones posteriores de la serie (regla anti-fuga, §4).
- **Qué escribes:** en `notes`, qué encontraste en la transcripción y dónde, sobre todo si
  marcas `sin_soporte`.

El resumen abstractivo de AMI es una anotación humana, y las anotaciones humanas tienen
errores. Todo el §1.3 de la tesis trata sobre el costo de persistir un error; eso aplica
también a los errores que vienen en el material de origen.

### ⚠️ Señal de triaje automática

**`evidence_da_count == 0` es sospecha inmediata, no un hueco menor.** Significa que los
propios anotadores de AMI no pudieron anclar esa frase a ningún acto de diálogo. En el
piloto, esa señal predijo exactamente la frase que resultó no tener soporte.

### Criterio de umbral: ¿`decision`, `no_decision` o `sin_soporte`?

> **De dónde sale este criterio.** De la calibración sobre ES2015: 14 de los 16 desacuerdos
> entre `gm` y `gv` fueron de umbral (`gm` puso `decision` donde `gv` puso `no_decision` o
> `sin_soporte`). El criterio concreta la guía conceptual a partir de cómo `jss` resolvió
> esos casos al adjudicar; no la amplía. Los casos se revisan en la sesión conjunta
> ([`calibracion/ES2015-sesion-conjunta.md`](calibracion/ES2015-sesion-conjunta.md)). Los
> ejemplos son de ES2015, serie de desarrollo, y por eso pueden citarse.

**Primero, el método.** Todo lo que sigue se juzga con la transcripción de la reunión, no
solo con `evidence_text` (regla de oro, arriba): se lee lo que se dice **antes y después en la
misma reunión**, nunca en reuniones posteriores. Es lo mismo que hace el ejemplo de §3 con el
botón turbo.

**(a) ¿Cuándo una propuesta cuenta como aceptada (`decision`)?** Es `decision` cuando, en la
misma reunión, el equipo la adopta o la usa como ya resuelta, aunque la frase original sea
tentativa:

- Otro participante la **confirma o reafirma** ("el PM expone y los demás reafirman"):
  `ES2015c.d02`, `ES2015d.d04`, `ES2015d.d05`.
- El diálogo **posterior la cierra**: una frase que suena a sugerencia es decisión si las
  líneas siguientes la adoptan (`ES2015b.d02`, `ES2015b.d05`).
- Se **recuerda como ya decidida**, incluso con tono de pregunta de confirmación ("we decided
  on kinetic, right?"): `ES2015c.d04`, `ES2015c.d05`.
- Se enuncia **como un hecho** del producto ("we're using plastic and rubber"):
  `ES2015d.d04`, `ES2015d.d06`. También cuando define qué producto se hace (`ES2015a.d01`).

Es `no_decision` cuando lo que hay es:

- Un **compromiso de investigar o una decisión que se pospone**: `ES2015b.d09` ("se pospone
  la decisión del impacto ambiental"; la evidencia dice *"we'll have to do more research"*).
- Una **meta o aspiración** y no una elección de diseño: `ES2015a.d03` (la meta de ganancia
  de cincuenta millones, "es una meta financiera").

**(b) ¿Cuándo la evidencia basta y la fila NO es `sin_soporte`?** `sin_soporte` es para cuando
el pasaje **contradice** la frase o **no contiene** lo que afirma. No lo es por que la
evidencia use otras palabras o cubra solo una parte de la frase:

- La evidencia expresa lo central con otras palabras o sin nombrar todos los elementos: la
  doble curvatura sin nombrar el control (`ES2015d.d05`), "tendremos dos colores" cuando la
  frase añade carcasa y botones, que se tratan en la reunión (`ES2015d.d03`).
- El detalle que falta en `evidence_text` aparece **más adelante en la reunión**
  (`ES2015b.d06`, "más adelante se habla de los tipos de luz que podría tener").
- La evidencia está en forma de pregunta de confirmación (`ES2015c.d04`, `ES2015c.d05`): eso
  no es falta de soporte; el criterio de (a) decide si es decisión.

`sin_soporte` se mantiene cuando el contenido de la frase **choca** con lo dicho. El caso de
referencia es `ES2015d.d07`: la frase dice 1,20 euros y la transcripción, *"twelve twenty"*
(12,20); ambas personas la marcaron `sin_soporte`. Mismo criterio que la regla de oro y que
el botón turbo de §3.

**Cuando dudes entre `decision` y `no_decision`, la prueba práctica:** ¿alguien en esa reunión
trata el asunto como ya resuelto (lo confirma, lo usa, lo da por hecho)? Si sí, `decision`;
si lo único que hay es "habrá que investigar", "se verá" o un deseo, `no_decision`.

---

## 3. Ejemplo trabajado real — el botón turbo

Este caso es real, verificado sobre `ami_public_manual_1.6.2`, y se eligió porque **el
resultado correcto es contraintuitivo**. Si entiendes este, entiendes la tarea.

### 3.1 Lo que te entrega la máquina

Dos filas, de dos reuniones distintas de la misma serie:

```
decision_id : IS1004c.d02
meeting_id  : IS1004c
source_sentence_id : IS1004c.elana.s.29
evidence_da_count  : 6
sentence_text : "The remote will have a base station, a button on the base station
                 to press, 2 scroll wheels for the channels and volume, a turbo
                 button (possibly underneath the device), and an on/off button for
                 the TV."
```

```
decision_id : IS1004d.d12
meeting_id  : IS1004d
source_sentence_id : IS1004d.elana.s.22
evidence_da_count  : 0        <-- ⚠️ señal de triaje
sentence_text : "For pricing reasons they eliminate the turbo button."
```

### 3.2 Qué haces con la primera fila

`IS1004c.d02` enumera **cinco** decisiones de producto en una sola frase. No es una.

Marcas la original `compuesta` y creas cinco filas:

| `decision_id` | `decision_object` | `decision_content` | `status` |
|---|---|---|---|
| `IS1004c.d02-1` | estación base | el control tendrá estación base | `decision` |
| `IS1004c.d02-2` | botón en la estación base | habrá un botón para localizar el control | `decision` |
| `IS1004c.d02-3` | ruedas de desplazamiento | dos ruedas: canales y volumen | `decision` |
| `IS1004c.d02-4` | botón turbo | se incluye, posiblemente en la cara inferior | `decision` |
| `IS1004c.d02-5` | botón de encendido | habrá botón de encendido/apagado del televisor | `decision` |

> **Sobre `IS1004c.d02-4`:** la frase dice *"possibly underneath the device"*. El
> *posicionamiento* es tentativo, pero la *existencia* del botón no lo es. El objeto de
> decisión es la existencia; la ubicación es contenido incierto y va a `notes`. No lo
> marques `no_decision` por el "possibly".

### 3.3 Qué haces con la segunda fila — aquí está la lección

`evidence_da_count == 0`, así que la máquina no te da evidencia. Tienes que buscarla.

La herramienta te ofrece las ocurrencias de los términos del objeto en la transcripción de
esa reunión. Para "turbo" en `IS1004d` hay ocho. La relevante es esta:

> **Transcripción `data/interim/transcripts/IS1004d.md`** (hablante B; la encuentras con
> `uv run afg gold evidencia --meeting IS1004d --term turbo`):
>
> *"…instead of a turbo button but you know the turbo button does add that extra class.
> You know. So I mean if we're **if we're over budget then maybe we could we could rethink
> that**. Yeah. **No we're not** — we don't need anything special for the buttons.
> **Make it plastic instead of rubber.** And then we're basically on budget except for
> you know ten cents."*

Léelo despacio. Lo que ocurrió fue:

1. Alguien propone eliminar el botón turbo **si** están sobre presupuesto.
2. Verifican: **no** están sobre presupuesto.
3. Resuelven el desajuste **cambiando goma por plástico**, no tocando el turbo.
4. **El botón turbo se queda.**

Y el resumen abstractivo de AMI afirma: *"For pricing reasons they eliminate the turbo
button."*

**El resumen está equivocado.** No hay pasaje posterior que lo elimine; esta es la última
mención en toda la reunión.

### 3.4 Qué escribes

```
decision_id      : IS1004d.d12
status           : sin_soporte
decision_object  : botón turbo
decision_content : (vacío — la frase afirma una eliminación que la evidencia contradice)
annotator        : gv
notes            : El resumen abstractivo afirma la eliminación. La transcripción
                   (IS1004d, intervención del hablante B) muestra que se planteó como
                   condicional a estar sobre presupuesto, se verificó que NO lo estaban,
                   y el ajuste se hizo cambiando goma por plástico. El botón se mantiene.
                   Última mención de "turbo" en la reunión. Error del resumen de origen.
```

### 3.5 Por qué este ejemplo importa

Si hubieras confiado en el resumen, habrías escrito una relación `revierte` entre
`IS1004c.d02-4` y `IS1004d.d12`. Sería un enlace temporal **falso** en el conjunto de
referencia — es decir, en el material que según §5.3 define C3, *"la misma representación
sin errores de extracción"*.

Un error ahí no se mide: se convierte en la vara con la que mides todo lo demás.

---

## 4. Tarea B — Adjudicar pares candidatos

**Archivo:** `data/processed/relations/IS1004.candidates.gv.csv` — tu copia, con tus
iniciales (ejemplo ilustrativo; IS1004 se abre en la Fase 3). **Nunca edites `IS1004.candidates.csv`** (el archivo sin iniciales): es el
insumo limpio que genera `afg gold candidates`, igual que en la Tarea A.
**Ritmo esperado:** ~1–2 minutos por par.
**Volumen esperado:** 92 pares en las 14 series (3,0 % de los 3.071 pares entre reuniones; ver
`docs/decisions/README.md`, decisión D9). La cifra de 5,5 % del piloto no era generalizable.

### Columnas

| Columna | Quién | Qué es |
|---|---|---|
| `pair_id` | máquina | Identificador del par |
| `earlier_decision_id` / `later_decision_id` | máquina | Siempre en orden cronológico |
| `earlier_sentence_id` / `later_sentence_id` | máquina | El id de la frase de origen en el corpus AMI |
| `earlier_text` / `later_text` | máquina | Objeto y contenido de cada una |
| `blocker_score` | máquina | Coeficiente de solapamiento que lo seleccionó |
| **`relation`** | **tú** | Del conjunto cerrado |
| **`direction_ok`** | **tú** | `si` / `no` (ver abajo) |
| **`confidence`** | **tú** | `alta` / `media` / `baja` |
| **`annotator`**, **`notes`** | **tú** | |

### Conjunto cerrado de relaciones

| Etiqueta | Significado |
|---|---|
| `introduce` | La posterior plantea un objeto de decisión nuevo, no tratado antes |
| `reafirma` | La posterior repite la anterior sin cambiarla |
| `refina` | La posterior conserva la anterior y le agrega detalle |
| `revierte` | La posterior deja sin efecto la anterior |
| `reemplaza` | La posterior sustituye la anterior por una alternativa distinta |
| `no_relacionada` | El blocker se equivocó: no hay relación |

**`reafirma` o `refina`: la pregunta es si cambió el contenido.** `refina` exige que la
posterior cambie lo decidido: lo acota, lo precisa, le agrega un elemento o excluye opciones
que la anterior dejaba abiertas. Si la posterior solo repite lo decidido y agrega una
**razón** o un motivo ("plástico y goma, la goma por comodidad"), el contenido no cambió y es
`reafirma`. Una posterior menos específica que la anterior ("plástico y goma" frente a
"plástico recubierto de goma") también es `reafirma`.

### ⚠️ La convención de dirección — léela dos veces

**`source` = la decisión POSTERIOR. `target` = la ANTERIOR sobre la que actúa.**

Se lee: *"la decisión de diciembre **revierte** la de octubre."* Nunca al revés.

Esto no es un detalle de formato. La H3 de la tesis predice que **la dirección invertida
será un modo de falla dominante** y que no mejorará con el tamaño del modelo. Si la
referencia tiene direcciones inconsistentes, H3 no se puede evaluar.

La columna `direction_ok` es tu confirmación explícita de que el par, tal como viene
ordenado en el CSV, respeta la convención. Si el orden cronológico del archivo estuviera
mal, pones `no` y lo explicas en `notes`.

### Regla de aislamiento temporal (§5.1)

**Anota cada serie en orden cronológico: primero todos los pares que terminan en la reunión
`b`, luego los de `c`, luego los de `d`.** Al etiquetar un par no debes haber leído aún las
reuniones posteriores. La tesis exige esto para la extracción automática; la anotación
humana tiene que cumplir la misma restricción o la comparación no es limpia.

### Ejemplo trabajado, continuando el caso

```
pair_id             : IS1004.p041
earlier_decision_id : IS1004c.d02-4      (botón turbo: se incluye)
later_decision_id   : IS1004d.d12        (botón turbo: "eliminado")
blocker_score       : 0.400
```

Tentador: `revierte`. **Incorrecto.**

`IS1004d.d12` quedó como `sin_soporte` en la Tarea A. Una decisión sin soporte no puede ser
el origen de una relación: no es una decisión.

```
relation      : no_relacionada
direction_ok  : si
confidence    : alta
notes         : El extremo posterior (IS1004d.d12) es sin_soporte — ver su fila en
                decisions.csv. La eliminación que afirma nunca ocurrió. Sin relación
                que anotar. El botón turbo permanece decidido desde IS1004c.
```

**Este par es oro para el banco de preguntas de §5.5.** Una pregunta del estrato E3
—*"¿se eliminó el botón turbo y en qué reunión?"*— tiene como respuesta de referencia
**"no, sigue vigente"**. Un sistema que lea el resumen abstractivo y conteste "sí, en la
reunión d" está exhibiendo exactamente el modo de falla de H4: respuesta confiada,
desactualizada y con cita que no la sustenta.

---

## 5. Tarea C — Muestra de recall del blocker

Sin esto, el blocker es una caja negra y no puedes reportar qué se perdió.

La muestra tiene **una parte por serie**: IS1004 (desarrollo) más una serie de evaluación
por sitio de grabación (ES2016, IS1003 y TS3005). Para cada serie:

1. `uv run afg gold recall-sample --series <SERIE> --n 50 --seed 42` extrae 50 pares
   **rechazados** por el blocker, al azar, con semilla fija (la misma en las cuatro series).
2. Los adjudicas con las mismas reglas de la Tarea B.
3. Cualquier par que resulte distinto de `no_relacionada` es un **falso negativo del
   blocker**.

El recall se reporta **por sitio** (una cifra para ES, IS y TS, cada una con su intervalo
bootstrap) y **en conjunto**. Así se puede ver si la pérdida es pareja entre sitios o si el
filtro pierde más en uno; IS1004 aporta la cifra del sitio IS junto con IS1003.

La cifra a reportar en la tesis es: *"el blocker con coeficiente de solapamiento ≥ 0,30
recuperó N de M relaciones en una muestra aleatoria de pares rechazados (IC 95 % por
bootstrap)."*

> **Por qué coeficiente de solapamiento y no Jaccard.** Medido en el piloto sobre el par del
> botón turbo (|A|=14, |B|=5, intersección `{button, turbo}`): Jaccard = 0,118, bajo
> cualquier umbral razonable → **se pierde**. Coeficiente de solapamiento = 0,400 → se
> captura. La razón es estructural: una reversión es casi siempre una frase **corta**
> apuntando a una **larga**, y Jaccard divide por la unión, castigando esa asimetría.
> Un blocker con Jaccard queda sistemáticamente ciego a las reversiones — es decir, ciego
> al estrato E3 completo.

---

## 6. Tarea D — Doble anotación y kappa

Exigido por OE1: **mínimo 25 % de las series, anotadas de forma independiente.**

1. Elige las series de control **antes** de empezar, no después.
2. La segunda persona trabaja sobre una copia limpia, sin ver tus etiquetas.
   Nomenclatura: `IS1004.candidates.<iniciales>.csv`.
3. `uv run afg gold agreement --series IS1004` calcula el kappa de Cohen por separado para:
   - **existencia** del enlace (¿hay relación, sí o no?)
   - **tipo** de relación
   - **dirección**
4. Los desacuerdos se resuelven en sesión de adjudicación y se registran en
   `data/processed/relations/IS1004.candidates.adjudicated.csv` (y, para la Tarea A,
   `data/processed/decisions/IS1004.decisions.adjudicated.csv`; nombres de ejemplo
   ilustrativo, IS1004 se abre en la Fase 3): par, etiqueta de cada
   anotador, etiqueta final, razón.

### Qué es el kappa de Cohen y cómo leerlo

**Qué mide.** El kappa de Cohen (κ) mide cuánto coinciden dos personas que etiquetan los
mismos ítems **descontando la coincidencia que se esperaría por azar**. Dos personas que
etiquetan casi todo igual, con una categoría dominante, coinciden mucho aunque no entiendan
la guía; el kappa corrige eso.

**Fórmula.**

> κ = (p_o − p_e) / (1 − p_e)

- **p_o** (acuerdo observado): la fracción de ítems en que las dos personas pusieron la misma
  etiqueta.
- **p_e** (acuerdo esperado por azar): para cada categoría, se multiplica la fracción de
  ítems que le dio una persona por la que le dio la otra, y se suman esos productos.

**Ejemplo con números chicos.** Diez pares, eje de existencia. Las dos personas ven un
enlace en 7 pares y ninguno en 1; en otro par `gv` ve enlace y `gm` no, y en otro `gm` ve
enlace y `gv` no.

- p_o = (7 + 1) / 10 = 0,80.
- Cada persona vio enlace en 8 de 10 pares (0,8) y ninguno en 2 de 10 (0,2), así que
  p_e = 0,8 × 0,8 + 0,2 × 0,2 = 0,68.
- κ = (0,80 − 0,68) / (1 − 0,68) = 0,375.

Un 80 % de coincidencia suena alto, pero con una categoría que domina el azar ya explica
casi todo: el kappa lo dice con 0,375.

**Cómo leer el valor.** κ = 1 es acuerdo perfecto, κ = 0 es lo que daría el azar y κ < 0
es peor que el azar. Como ayuda de lectura, y solo como eso, se suelen citar las bandas de
Landis y Koch (1977): menos de 0 pobre; 0,00–0,20 leve; 0,21–0,40 regular; 0,41–0,60
moderado; 0,61–0,80 sustancial; 0,81–1,00 casi perfecto. **El proyecto no fija ningún
umbral de aceptación del kappa**: se reporta tal como salga, y un kappa bajo es un hallazgo
y no un fracaso a esconder (avance 06, tabla de umbrales operativos, fila del kappa de la
anotación). Las bandas no sustituyen esa regla.

**Cuándo no existe (`NaN`).** Si las dos personas usan **la misma categoría única** en todos
los ítems, p_e = 1 y el denominador se anula: el kappa queda indefinido aunque el acuerdo
crudo sea del 100 %. No es un error de cálculo y no se reemplaza por 1 ni por 0; se reporta
como indefinido (notebook 04, §3.4). Con pocos ítems, además, el valor es muy inestable: un
solo par que cambie lo mueve mucho.

**Sobre qué filas se calcula cada eje** (`src/afg/annotation/agreement.py`, función
`compute_series_agreement`). Los tres se calculan sobre los pares cuyo `pair_id` está en los
dos archivos de anotador:

| Eje | Etiqueta que se compara | Filas que entran |
|---|---|---|
| **Existencia** | `exists` si `relation` tiene valor y no es `no_relacionada`; si no, `no_relation` | Todos los pares emparejados |
| **Tipo** | El valor de `relation` | Solo los pares donde **las dos** personas marcaron que existe un enlace. Si no hay ninguno, el kappa de tipo no se calcula |
| **Dirección** | El valor de `direction_ok` (sin espacios, en minúsculas) | Todos los pares emparejados, también los `no_relacionada`, porque el manual pide llenar esa columna en cada fila. Una celda vacía cuenta como un valor más |

**El kappa de estado de la Tarea A (solo diagnóstico).** Los tres kappas anteriores salen de
los CSV de pares. Para la calibración de la Fase 1 existe además un kappa sobre el `status`
de la Tarea A (`decision_agreement`, en `src/afg/annotation/calibration.py`): compara el
`status` de cada persona en las **filas base** del CSV de adjudicación (las filas hijas de
una `compuesta` no entran, porque cada persona puede dividir la frase de forma distinta),
con las cinco categorías de `status` como etiquetas y la misma función de kappa. Junto con
él se informa el acuerdo crudo y el número de filas con `acuerdo = si`, que es más estricto
porque en las `compuesta` exige además la misma división. Es solo diagnóstico de
calibración y no se reporta en la tesis. Un ejemplo calculado está en el notebook 04, §2.

**El kappa se reporta tal como salga.** El §1.4 de la tesis existe porque dos equipos
competentes obtuvieron kappa negativo sobre este mismo corpus. Un kappa bajo no es un
fracaso a esconder: es el resultado que OE1 se propuso *medir* en vez de asumir.

---

## 7. Checklist de cierre por serie

Marca solo lo verificado. Cada ítem corresponde a algo revisable después.

### Tarea A — decisiones
- [ ] Toda fila de `<serie>.decisions.<ini>.csv` (tu copia, no el archivo base) tiene `status` no vacío
- [ ] Toda fila con `status = decision` tiene `decision_object` **y** `decision_content`
- [ ] Toda fila `compuesta` tiene sus filas hijas `-1`, `-2`, … creadas
- [ ] Cada `compuesta` es realmente separable (una parte podría cambiar sin la otra); atributos y razones no se dividen
- [ ] Todo duplicado dentro de la reunión está marcado `descartar`, con `notes` indicando qué fila duplica
- [ ] Ninguna fila hija quedó con `status = compuesta`
- [ ] **Toda fila con `evidence_da_count = 0` fue revisada contra la transcripción**
- [ ] **Toda fila `sin_soporte` fue revisada contra la transcripción de su reunión**, no solo
      contra `evidence_text`
- [ ] Toda fila `sin_soporte` explica en `notes` qué dice la transcripción y dónde
- [ ] Las `no_decision` se conservaron (no se borró ninguna fila)
- [ ] `annotator` está en todas las filas

### Tarea B — relaciones
- [ ] Toda fila de `<serie>.candidates.<ini>.csv` (tu copia, no el archivo base) tiene `relation` del conjunto cerrado
- [ ] `direction_ok` está en todas las filas
- [ ] Ninguna relación distinta de `no_relacionada` apunta a una decisión
      `sin_soporte`, `descartar` o `no_decision`
- [ ] La anotación se hizo en orden cronológico (b, luego c, luego d)
- [ ] `confidence` está en todas las filas

### Tarea C — recall
- [ ] Muestra de rechazados extraída con semilla registrada, una por serie (IS1004, ES2016, IS1003, TS3005)
- [ ] Las cuatro muestras adjudicadas con las mismas reglas
- [ ] Falsos negativos contados y anotados

### Tarea D — acuerdo
- [ ] La serie está marcada como control, o se declaró que no lo es
- [ ] Si es control: segunda anotación independiente completa
- [ ] Kappa calculado por separado para existencia / tipo / dirección
- [ ] Desacuerdos resueltos y registrados en los `<serie>.*.adjudicated.csv`

### Cierre
- [ ] `uv run afg gold agreement --series <ID>` corre sin error
- [ ] Los CSV están versionados en git (no están bajo `data/raw/`, que sí se ignora)
- [ ] Las cifras de la serie se agregaron al reporte acumulado

---

## 8. Resumen de una línea

> Abres dos CSV. En el primero decides **qué es una decisión**, leyendo siempre la evidencia
> antes que el resumen. En el segundo decides **qué relación hay entre dos decisiones**,
> respetando la convención de dirección. Todo lo demás lo hace la máquina.
