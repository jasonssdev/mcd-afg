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
> implementados y con tests (`docs/BACKLOG.md`, P4).

| Comando | Para qué |
|---|---|
| `uv run afg corpus download` | Descarga el corpus (una sola vez por máquina) |
| `uv run afg corpus inventory` | Verifica que el corpus está completo |
| `uv run afg gold build --series <ID>` | Genera el CSV de decisiones de la Tarea A |
| `uv run afg gold candidates --series <ID>` | Genera el CSV de pares candidatos de la Tarea B |
| `uv run afg gold recall-sample --series <ID> --n 50 --seed 42` | Genera la muestra de la Tarea C |
| `uv run afg gold evidence --meeting <ID> --term <palabra>` | Busca evidencia en la transcripción cuando `evidence_da_count` es 0 |
| `uv run afg gold agreement --series <ID>` | Calcula el kappa de la Tarea D |

Para una serie, el flujo es:

```bash
uv run afg gold build      --series IS1004   # -> data/processed/decisions/IS1004.decisions.csv
uv run afg gold candidates --series IS1004   # -> data/processed/relations/IS1004.candidates.csv
```

El segundo comando **exige** que el primero esté adjudicado: los candidatos se generan sobre
las decisiones normalizadas, no sobre las frases crudas.

---

## 2. Tarea A — Normalizar decisiones

**Archivo que abres:** `data/processed/decisions/IS1004.decisions.csv`
**Herramienta:** cualquier editor de hojas de cálculo, o el editor de texto que prefieras.
**Ritmo esperado:** ~30 segundos por fila.

### Columnas

| Columna | Quién la llena | Qué es |
|---|---|---|
| `decision_id` | máquina | `IS1004c.d03`. No lo toques |
| `meeting_id` | máquina | `IS1004c` |
| `source_sentence_id` | máquina | `IS1004c.elana.s.29` — trazabilidad al XML |
| `sentence_text` | máquina | La frase del resumen abstractivo, literal |
| `evidence_da_count` | máquina | Cuántos actos de diálogo la respaldan |
| `evidence_text` | máquina | La transcripción de esos actos |
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
| `descartar` | Frase truncada, rota o ininteligible |

**`compuesta` no es un veredicto final, es una instrucción.** Marcas la fila original como
`compuesta` y creas N filas nuevas con `decision_id` sufijado `-1`, `-2`, … copiando
`source_sentence_id` y `evidence_text`. Cada fila nueva lleva su propio
`decision_object` / `decision_content` y su `status`.

### La regla de oro

> **Lee `evidence_text` antes de llenar nada. Si la evidencia no dice lo que dice
> `sentence_text`, el status es `sin_soporte` — aunque la frase suene perfectamente
> razonable.**

El resumen abstractivo de AMI es una anotación humana, y las anotaciones humanas tienen
errores. Todo el §1.3 de la tesis trata sobre el costo de persistir un error; eso aplica
también a los errores que vienen en el material de origen.

### ⚠️ Señal de triaje automática

**`evidence_da_count == 0` es sospecha inmediata, no un hueco menor.** Significa que los
propios anotadores de AMI no pudieron anclar esa frase a ningún acto de diálogo. En el
piloto, esa señal predijo exactamente la frase que resultó no tener soporte.

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

> **`words/IS1004d.B.words.xml`, cerca de `IS1004d.B.words1560`** (hablante B):
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
annotator        : JD
notes            : El resumen abstractivo afirma la eliminación. La transcripción
                   (IS1004d.B.words1560 y siguientes) muestra que se planteó como
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

**Archivo:** `data/processed/relations/IS1004.candidates.csv`
**Ritmo esperado:** ~1–2 minutos por par.
**Volumen esperado:** 92 pares en las 14 series (3,0 % de los 3.071 pares entre reuniones; ver
`docs/BACKLOG.md`, decisión D9). La cifra de 5,5 % del piloto no era generalizable.

### Columnas

| Columna | Quién | Qué es |
|---|---|---|
| `pair_id` | máquina | Identificador del par |
| `earlier_decision_id` / `later_decision_id` | máquina | Siempre en orden cronológico |
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

1. `uv run afg gold recall-sample --series IS1004 --n 50` extrae 50 pares **rechazados**
   por el blocker, al azar, con semilla fija.
2. Los adjudicas con las mismas reglas de la Tarea B.
3. Cualquier par que resulte distinto de `no_relacionada` es un **falso negativo del
   blocker**.

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
   `data/processed/relations/IS1004.adjudication.md`: par, etiqueta de cada anotador,
   etiqueta final, razón.

**El kappa se reporta tal como salga.** El §1.4 de la tesis existe porque dos equipos
competentes obtuvieron kappa negativo sobre este mismo corpus. Un kappa bajo no es un
fracaso a esconder: es el resultado que OE1 se propuso *medir* en vez de asumir.

---

## 7. Checklist de cierre por serie

Marca solo lo verificado. Cada ítem corresponde a algo revisable después.

### Tarea A — decisiones
- [ ] Toda fila de `<serie>.decisions.csv` tiene `status` no vacío
- [ ] Toda fila con `status = decision` tiene `decision_object` **y** `decision_content`
- [ ] Toda fila `compuesta` tiene sus filas hijas `-1`, `-2`, … creadas
- [ ] Ninguna fila hija quedó con `status = compuesta`
- [ ] **Toda fila con `evidence_da_count = 0` fue revisada contra la transcripción**
- [ ] Toda fila `sin_soporte` explica en `notes` qué dice la evidencia
- [ ] Las `no_decision` se conservaron (no se borró ninguna fila)
- [ ] `annotator` está en todas las filas

### Tarea B — relaciones
- [ ] Toda fila de `<serie>.candidates.csv` tiene `relation` del conjunto cerrado
- [ ] `direction_ok` está en todas las filas
- [ ] Ninguna relación distinta de `no_relacionada` apunta a una decisión
      `sin_soporte`, `descartar` o `no_decision`
- [ ] La anotación se hizo en orden cronológico (b, luego c, luego d)
- [ ] `confidence` está en todas las filas

### Tarea C — recall
- [ ] Muestra de rechazados extraída con semilla registrada
- [ ] Muestra adjudicada con las mismas reglas
- [ ] Falsos negativos contados y anotados

### Tarea D — acuerdo
- [ ] La serie está marcada como control, o se declaró que no lo es
- [ ] Si es control: segunda anotación independiente completa
- [ ] Kappa calculado por separado para existencia / tipo / dirección
- [ ] Desacuerdos resueltos y registrados en `<serie>.adjudication.md`

### Cierre
- [ ] `uv run afg gold agreement --series <ID>` corre sin error
- [ ] Los CSV están versionados en git (no están bajo `data/raw/`, que sí se ignora)
- [ ] Las cifras de la serie se agregaron al reporte acumulado

---

## 8. Resumen de una línea

> Abres dos CSV. En el primero decides **qué es una decisión**, leyendo siempre la evidencia
> antes que el resumen. En el segundo decides **qué relación hay entre dos decisiones**,
> respetando la convención de dirección. Todo lo demás lo hace la máquina.
