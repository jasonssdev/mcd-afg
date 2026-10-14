# Calibración del juez: qué haces y cómo

**Para qué sirve.** El Experimento B produce unas 900 respuestas (100 preguntas × 3
condiciones × 3 corridas) y un juez automático las califica. Antes de usarlo hay que elegir
cuál de los tres modelos candidatos es el juez y comprobar que califica como lo haría una
persona. Para eso se arma un conjunto pequeño, con etiquetas puestas **por una persona**, y se
mide cuánto coincide cada candidato con ellas. Tu trabajo es escribir unas 20 preguntas (16 como mínimo) y
después etiquetar unas 40 respuestas; todo lo demás lo hace el repositorio.

**Por qué solo ES2015.** Es una serie de desarrollo ya anotada y adjudicada, así que leerla no
compromete ninguna anotación pendiente. IS1004 y TS3009 son de desarrollo, pero su anotación
sigue abierta: leer su contenido para esto rompería la independencia de quienes las anotan.

**Cuánto toma.** Preguntas: 1 a 1,5 h. Etiquetas: unos 40 min. Los pasos 4, 6 y 7 los hace la
máquina y no necesitan atención; tardan, así que se dejan corriendo.

## Los pasos

```bash
uv run afg judge calibration-init        # 1. crea la hoja de preguntas, ya prellenada
# 2. abres data/processed/judge-calibration/ES2015.preguntas.csv y llenas 4 columnas
uv run afg judge calibration-validate    # 3. revisa tu selección
uv run afg judge calibration-answers     # 4. la máquina genera 2 respuestas por pregunta
# 5. abres data/processed/judge-calibration/calibracion-juez.csv y etiquetas
uv run afg judge calibration-run         # 6. corre los tres candidatos (tarda)
uv run jupyter nbconvert --to notebook --execute --inplace \
  notebooks/05-jss-seleccion-juez.ipynb  # 7. el notebook muestra el resultado
```

El paso 1 ya está hecho en el repositorio: `ES2015.preguntas.csv` existe. Solo lo repites si
la hoja se perdió (el comando se niega a pisarla si ya tiene algo escrito por una persona).

### Paso 2. Llena la hoja de preguntas

Ábrela en una hoja de cálculo (VS Code, LibreOffice Calc; Excel solo si guardas como
**CSV UTF-8**, igual que en [`EMPIEZA-AQUI.md`](asignacion/EMPIEZA-AQUI.md) §4). Las **cuatro
primeras columnas** son las tuyas; el resto viene hecho y no se toca:

| Columna | Qué escribes |
|---|---|
| `usar` | `si` en las ~20 filas que eliges; las demás, vacías |
| `stratum` | `E1`, `E2`, `E3` o `E4` |
| `pregunta` | La pregunta, **en inglés**, como las del banco |
| `respuesta_referencia` | La respuesta correcta, en inglés y corta. **Vacía en E4** |

Cada fila trae la decisión, el contenido acordado, la evidencia como texto
(`evidencia_texto`) y la evidencia ya resuelta a actos de diálogo (`reference_evidence`). Las
filas con `ES2015.pNNN` son pares de decisiones con una relación entre ellas (`relacion`): sirven
para E2 y E3. Las seis filas `E4` están en blanco a propósito. Si una fila dice algo en
`aviso_evidencia`, la evidencia no pudo resolverse completa: elige otra. Apunta a unas 20 filas
(con 16 a 19 la validación avisa pero deja seguir; con menos de 16 no) con los cuatro estratos presentes; E3 tendrá pocas, porque ES2015 tiene pocas relaciones de
evolución, y no pasa nada.

### Un ejemplo por estrato (ES2015, filas reales)

**E1, dato puntual** (fila `ES2015a.d02`). La decisión dice *"The selling price will be twenty
five Euros."* y la evidencia es una sola intervención del PM.

| `usar` | `stratum` | `pregunta` | `respuesta_referencia` |
|---|---|---|---|
| si | E1 | What selling price was set for the remote control? | Twenty five Euros. |

**E2, estado vigente** (fila `ES2015.p002`, relación `reafirma`: la reunión `c` y la `d`
dicen lo mismo). Se pregunta por lo que rige al final, no por una reunión concreta.

| `usar` | `stratum` | `pregunta` | `respuesta_referencia` |
|---|---|---|---|
| si | E2 | What type of chip does the remote control use? | A regular chip. |

**E3, evolución** (fila `ES2015.p001`, relación `refina`). Se pregunta cómo cambió una
decisión entre reuniones; la evidencia de la fila une las dos.

| `usar` | `stratum` | `pregunta` | `respuesta_referencia` |
|---|---|---|---|
| si | E3 | How did the scope of the remote control change between the first and second meetings? | It started as a television remote control and was narrowed to a single-function, television-only design, to keep the design simple and within budget. |

**E4, sin respuesta** (una de las seis filas `E4`). Una pregunta de un dominio vecino sobre
algo que el material **no** dice; en ES2015 no se menciona ninguna garantía. Sin respuesta de
referencia.

| `usar` | `stratum` | `pregunta` | `respuesta_referencia` |
|---|---|---|---|
| si | E4 | What warranty period does the remote control carry? | *(vacía)* |

### Paso 3. Valida

`calibration-validate` dice, fila por fila, qué falta: sin `stratum`, E4 con respuesta de
referencia, pregunta sin respuesta o sin evidencia, menos de 16 filas, ningún E4. Con 16 a 19 filas solo avisa que lo
recomendado es 20 y sigue. Termina con cuántas preguntas hay por estrato. Corrige y repite hasta que diga que la hoja está lista.

### Paso 5. Etiqueta las respuestas

`calibracion-juez.csv` tiene dos respuestas por pregunta. Se etiqueta con el **mismo método que
el juez automático y que la anotación** (ver [`manual-anotacion-oe1.md`](manual-anotacion-oe1.md)):
se lee la evidencia y, si no basta, la transcripción. Por cada fila lee:

- `question`, `reference_answer` y `answer_text`;
- `pasaje_transcripcion`: el fragmento de la transcripción alrededor de la evidencia, el mismo
  que lee el juez. Si no alcanza para decidir, abre la transcripción completa de la reunión
  (ruta en `archivos_transcripcion`, archivo `.md` legible) y busca ahí.

Después llena **solo dos columnas** con `si` o `no`:

- `correct`: la respuesta del sistema coincide con la de referencia. Una abstención
  ("The material does not contain enough information…") es correcta solo en una pregunta E4.
- `evidence_supported`: **cada afirmación** de la respuesta está respaldada por la transcripción
  (el pasaje o, si hizo falta, la reunión). Una afirmación que la transcripción no dice, o que
  contradice, la deja en `no` aunque sea verdad fuera de la reunión. Una abstención no afirma
  nada, así que se respalda sola; en E4 ambas etiquetas son `si` solo si la respuesta se abstiene
  (esas filas no traen pasaje: el material no tiene la respuesta).

Se aceptan `si`, `sí`, `no`, `true`, `false`, `1` y `0`. Nada más se edita. Las etiquetas las
pones tú, a ojo, sin preguntarle a ningún modelo; por eso el conjunto sirve de patrón. Las
filas están **barajadas a propósito**: las dos respuestas de una pregunta no quedan juntas y su
orden no delata cuál es la buena. Con una salvedad: el `id` termina en `.grounded` o
`.ungrounded`, de modo que sí revela cómo se generó la respuesta (el archivo auxiliar con la
variante no se muestra, pero el sufijo la delata). **Ignora el sufijo del `id`** y etiqueta
cada fila por lo que dice, sin intentar adivinar de dónde viene. Esta fuga afectó a las dos
personas que etiquetaron y se declara como limitación en el notebook 05.

Si agregas preguntas después, `calibration-answers` solo genera las nuevas y no toca las
etiquetas que ya pusiste (las filas se vuelven a barajar, pero cada una conserva su `id`).

## Segunda etiqueta

Una segunda persona (`gm` o `gv`) etiqueta 15 ítems por separado para comprobar que la etiqueta
humana es confiable:

1. `uv run afg judge calibration-second-sheet` crea la hoja sin etiquetas
   (`calibracion-juez.segunda-etiqueta.csv`, muestra determinista con semilla 42). No
   sobrescribe una hoja que ya tenga etiquetas.
2. La segunda persona llena `correct` y `evidence_supported` sin ver las etiquetas de la primera.
3. `uv run afg judge calibration-agreement` calcula el kappa por columna, lo compara con el
   umbral de `[judge.calibration]` y guarda `reports/judge-calibration/acuerdo-humano.json`,
   que lee el notebook 05.

## Lo que no se hace

- **No leas IS1004 ni TS3009** para escribir preguntas. Solo ES2015.
- **No escribas las etiquetas con ayuda de ningún modelo.** Son siempre humanas.
- **No edites** `banco-preguntas.csv` ni los CSV de anotación; esto es un conjunto aparte.
- **No escribas las preguntas en español.** Van en inglés, como las del banco.
- **No toques las columnas automáticas** de la hoja ni el orden de las filas: el identificador
  de cada pregunta sale del número de `fila`.

Si algo falla, el mensaje de cada comando dice qué paso falta; las dudas van al issue #82.
