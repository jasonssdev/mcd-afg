# Etapa de la falla (OE4): hoja de etiquetado de C2

**Para qué sirve.** El objetivo OE4 pregunta **en qué etapa falla** el sistema compilado (C2)
cuando contesta mal una pregunta de hecho puntual (estrato E1). La respuesta es una de tres
etapas. La regla automática ya atribuye a síntesis las fallas cuyo dato completo estaba en lo
recuperado; las demás no se pueden atribuir con la traza guardada, porque hace falta mirar la
base compilada. Esas son las filas de esta hoja, y las etiqueta una persona
([`CONTRIBUTING.md`](../../CONTRIBUTING.md) §7.6: la máquina nunca pone la etiqueta).

**Quién.** `gm`. **Cuándo.** Después de la corrida formal del Experimento B que incluye C2.
**Cuánto toma.** El tiempo no está documentado; como estimación, de 1 a 3 minutos por fila.

## Qué filas llegan a la hoja

Una fila por cada respuesta de C2 en E1 que el juez marcó incorrecta y que la regla automática
no pudo atribuir, **por pregunta y por corrida** (la misma pregunta puede aparecer hasta tres
veces, una por corrida). Como máximo son 25 preguntas × 3 corridas = **75 filas**; en la
práctica son menos, porque solo entran las que fallaron.

## Cómo se genera la hoja

La genera quien mantiene el repositorio:

```bash
uv run afg experiment b-oe4-sheet --run-name <corrida-B> --questions data/processed/questions/banco-preguntas.csv
```

Escribe `reports/experiment-b/<corrida-B>/oe4-etapa-e1.csv`. `--questions` es obligatorio y debe
ser el banco con el que se corrió. La hoja usa la base compilada que C2 consultó
(`data/interim/openkos/`, fuera de git). El comando se niega a pisar una hoja que ya tiene
etiquetas (salvo `--force`). Con `--all-failures` la hoja incluye también las fallas que la regla
ya atribuyó a síntesis, para que la persona pueda contradecirlas.

## Qué trae cada fila

| Columna | Qué es |
|---|---|
| `pregunta_id`, `corrida` | Qué pregunta y qué repetición (0, 1 o 2) |
| `pregunta`, `respuesta_referencia` | Lo que se preguntó y la respuesta correcta |
| `respuesta_c2` | Lo que contestó el sistema |
| `mejor_objeto`, `mejor_objeto_recuperado` | El objeto de la base compilada que contiene más palabras de la referencia, y si el sistema lo recuperó (`sí`/`no`) |
| `objetos_de_la_base` | Los tres objetos con más cobertura, con su cobertura (0 a 1) y si se recuperaron |
| `mejor_fuente` | La transcripción en bruto de esa reunión con más cobertura |
| `pista_automatica` | Una pista de triaje de la máquina (ver abajo) |
| **`etapa_humana`** | **La que se llena** |
| **`nota`** | Opcional: el motivo, sobre todo en los casos dudosos |

La cobertura cuenta palabras, no significado: «25» y «veinticinco» no coinciden. Una cobertura
baja es una razón para leer el objeto, no una prueba de que el dato falta.

## Las tres etapas

En `etapa_humana` se escribe exactamente una de estas palabras, en minúscula y sin tilde:

- **`extraccion`**: el dato **no está en la base compilada**, o está mal (otra cifra, otra
  persona, la decisión contraria). La falla ocurrió antes de que existiera la base. La
  transcripción en bruto (`sources/`) no cuenta como haberlo extraído: está en la base tal cual
  se importó, y que el dato aparezca solo ahí significa que ninguna decisión ni concepto lo
  capturó.
- **`recuperacion`**: el dato **está bien** en un objeto de la base, pero el sistema **no lo
  recuperó** (`mejor_objeto_recuperado` = `no` y ningún objeto recuperado lo dice).
- **`sintesis`**: el dato está en la base y el sistema **sí lo recuperó**, y aun así la respuesta
  salió mal: la redactó mal, la mezcló con otro dato o no usó lo que tenía delante.

Se decide en ese orden: ¿está en la base? Si no, `extraccion`. ¿Se recuperó? Si no,
`recuperacion`. Si sí, `sintesis`.

### Ejemplos inventados

Los ejemplos no vienen de ninguna reunión de evaluación.

1. Referencia: «El equipo eligió el color azul para la carcasa». `objetos_de_la_base` lista
   `decisions/d12 (1.00, recuperado)` con el texto «Se elige el azul para la carcasa», y la
   respuesta de C2 dice «verde». El dato está y se recuperó: **`sintesis`**.
2. Referencia: «El presupuesto quedó en 12 euros por unidad». El mejor objeto,
   `decisions/d07 (1.00, no recuperado)`, lo dice con claridad, pero ninguno de los objetos que
   C2 trajo lo menciona: **`recuperacion`**.
3. Referencia: «Se aprobó el uso de baterías recargables». Ningún objeto de la base lo dice; el
   más cercano habla de baterías sin la aprobación, y solo la transcripción en bruto lo
   contiene: **`extraccion`**.
4. Referencia: «La reunión fijó el jueves como fecha de entrega». El objeto de la base dice
   «viernes»: la base tiene el dato mal. **`extraccion`**, aunque se haya recuperado.

## La pista automática: ignórala al decidir

`pista_automatica` es una sugerencia de triaje, **no una etiqueta ni una respuesta correcta**. Dice, por ejemplo, que un
objeto tiene todas las palabras de la referencia y se recuperó (apunta a síntesis), que lo
tiene y no se recuperó (recuperación), o que solo la transcripción en bruto lo tiene
(extracción). Puede equivocarse en ambos sentidos: una paráfrasis la despista y un objeto con
todas las palabras puede decir otra cosa. Conviene leer el objeto y decidir sin apoyarse en la
pista; si la persona discrepa, se escribe la etapa que cree correcta, sin ajustarla a la pista.
Los desacuerdos con la pista se cuentan y se informan, y no son un error de quien etiqueta.

## Cómo se llena

- Se abre la hoja en una hoja de cálculo y se escriben `etapa_humana` y, si hace falta, `nota`.
  Nada más se edita.
- Guardar como **CSV UTF-8 (delimitado por comas)**, con las mismas columnas y sin agregar ni
  reordenar filas ([`EMPIEZA-AQUI.md`](asignacion/EMPIEZA-AQUI.md) §4).
- No se deja ninguna fila vacía ni con otro valor: la hoja a medio etiquetar se rechaza.
- Para leer un objeto completo de la base se abre en `data/interim/openkos/` (la ruta de la
  hoja indica la corrida y la serie). Para el contexto de la reunión, la transcripción del
  mismo archivo.

## Después

```bash
uv run afg experiment b-oe4-summary --run-name <corrida-B>
```

Valida las etiquetas, cuenta las fallas por etapa (recuperación, extracción, síntesis) y su
parte del total, y cuántas veces la persona discrepó de la pista automática. Guarda
`oe4-resumen.json` en la carpeta de la corrida. El comando acepta varias corridas repitiendo
`--run-name`.
