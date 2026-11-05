# Verificación del juez automático por una persona (Experimento B)

**Para qué sirve.** En el Experimento B un modelo juez decide si cada respuesta es correcta.
La metodología prerregistrada (`docs/avances/06-jss-metodologia.md`, §5.7) exige que una
persona vuelva a juzgar el 20 % de esas respuestas y que el acuerdo con el juez alcance un
kappa de Cohen de al menos 0,70. Esta hoja reúne esas respuestas; quien etiqueta contesta
si/no en tres columnas y el repositorio calcula el acuerdo.

**Quién.** `gv`, que no escribió ninguna respuesta de referencia ni vio los veredictos del juez.
**Cuándo.** Después de la corrida formal del Experimento B con las cuatro condiciones (C0 a C3),
una vez que el juez terminó de calificar. **Cuánto toma.** El tiempo no está documentado; como
estimación, un minuto por fila, unas 4 horas en total.

## Qué se revisa

De cada celda (condición × estrato; 4 × 4 = 16 celdas) se toma el 20 % de las respuestas
calificadas por el juez, con una sola corrida sorteada por cada par (pregunta, condición): las
corridas de una pregunta son repeticiones de un mismo caso y no se juzgan dos veces. Con 25
preguntas por estrato (24 en E3, [ADR 0021](../decisions/0021-adr-minimo-de-e3-segun-relaciones-disponibles.md)) y 3 corridas, cada celda aporta 15 filas y la hoja tiene unas
**240 filas** (16 × 15). La regla está en `src/afg/evaluation/judge_human_check.py`
(`select_human_sample`) y el sorteo usa la semilla fijada en `config/experiments.toml`.
Una respuesta que el juez no pudo calificar (falla del juez o error) no entra al sorteo.

## Cómo se genera la hoja

La genera quien mantiene el repositorio, no quien etiqueta:

```bash
uv run afg experiment b-sample --run-name <corrida-B> --questions data/processed/questions/banco-preguntas.csv
```

Escribe dos archivos en `reports/experiment-b/<corrida-B>/`:

| Archivo | Quién lo abre |
|---|---|
| `muestra-juez.csv` | La persona que etiqueta. Es la hoja ciega: sin condición, sin corrida y sin el veredicto del juez |
| `muestra-juez.clave.csv` | **Nadie que etiquete.** Guarda la condición, la corrida y lo que respondió el juez en cada fila; verlo sesga las respuestas |

El orden de las filas está barajado y los identificadores (`h001`, `h002`…) no revelan la
condición. El comando se niega a pisar una hoja que ya tiene etiquetas (salvo `--force`).

## Qué columnas se llenan

Cada fila trae la pregunta (`question`), la respuesta de referencia (`reference_answer`), la
respuesta del sistema (`answer_text`) y el pasaje de la transcripción que vio el juez
(`pasaje_transcripcion`, con los archivos en `archivos_transcripcion`). Se escriben tres
columnas, con `si` o `no`:

- **`correct`**: la respuesta del sistema coincide con la de referencia. Se juzga el contenido,
  no el largo ni el tono. Un dato clave que falta, un valor equivocado, un cambio en sentido
  contrario o una afirmación añadida que contradice la referencia la vuelven `no`. Un detalle
  extra que no contradice nada no la vuelve `no`.
- **`evidence_supported`**: **cada** afirmación de la respuesta aparece en el pasaje de la
  transcripción. Una afirmación que el pasaje no dice, o que contradice, la vuelve `no`, aunque
  sea verdadera en otra parte. Se compara con el pasaje, nunca con las fuentes que la respuesta
  cita ni con lo que la persona sepa de la reunión.
- **`outdated`**: solo en filas E3 (evolución). La columna `respuesta_superada` trae el estado
  anterior de la decisión, el que la referencia reemplaza. Se escribe `si` solo si la respuesta
  presenta ese estado anterior como el estado vigente; si menciona el estado anterior y dice que
  fue reemplazado, es `no`. En E1, E2 y E4 la columna se deja vacía.

No se deja ninguna fila vacía en `correct` ni en `evidence_supported`, y ninguna fila E3 sin
`outdated`: el comando de puntaje se detiene y nombra la fila que falta.

## Casos que se prestan a duda

- **E4 (sin respuesta en el material).** La referencia dice que el material no contiene la
  respuesta. Si el sistema se abstiene o dice que no lo sabe: `correct` = `si` y
  `evidence_supported` = `si` (una abstención no afirma nada, así que no hay afirmación sin
  respaldo). Si inventa una respuesta: ambos `no`. `outdated` queda vacía.
- **Respuesta sin fuentes (C0).** C0 contesta sin acceso a las reuniones y no cita. Eso no la
  vuelve `no` por sí solo: `evidence_supported` mira si lo que afirma está en el pasaje. Si
  acierta pero con datos que el pasaje no menciona, `correct` puede ser `si` y
  `evidence_supported` `no`.
- **Abstención en E1, E2 o E3.** La referencia sí tiene respuesta, de modo que la abstención es
  `correct` = `no`. Como no afirma nada, `evidence_supported` = `si`. En E3, `outdated` = `no`.
- **Respuesta que da dos versiones.** Si presenta ambos estados como posibles sin decir cuál es el vigente, `correct` = `no`; `outdated` = `no`,
  porque no presenta el anterior como el actual.
- **Duda genuina.** Se elige la respuesta más probable. No hay tercera opción.

## Ciegos, de verdad

No intentar adivinar de qué condición viene la respuesta, no abrir la clave, no consultar las
cifras ni el informe del Experimento B y no pedir a otra persona que mire el veredicto del
juez. Las etiquetas son solo de quien las pone y nadie las prellena. Guardar como **CSV UTF-8
(delimitado por comas)**, con las mismas columnas y sin agregar ni reordenar filas (detalles en
[`EMPIEZA-AQUI.md`](asignacion/EMPIEZA-AQUI.md) §4).

## Cómo se puntúa

```bash
uv run afg experiment b-human-check --run-name <corrida-B>
```

Calcula, por etiqueta, el acuerdo observado, la prevalencia de «sí» del juez y de la persona, y
el kappa de Cohen, con umbral 0,70 (`[judge.calibration].min_kappa_correct`). El resultado
queda en `juez-humano.json`. Un kappa **indefinido** (juez y persona usan una sola clase) cuenta
como «no cumple»; se informa igualmente el acuerdo observado.

Qué pasa si una etiqueta no cumple (ADR 0010):

- **`correct`**: se descarta el juicio automático de la métrica principal y la corrección se
  reporta solo con la evaluación humana.
- **`evidence_supported`**: esa métrica se reporta solo con la evaluación humana o marcada como
  no confiable. No afecta la métrica principal.
- **`outdated`**: H4 se reporta con las etiquetas humanas o como no confiable. Su kappa se
  calcula sobre las filas E3 que el juez marcó con respuesta.

Un resultado que no cumple no es un fracaso: se reporta como limitación, tal como salga.
