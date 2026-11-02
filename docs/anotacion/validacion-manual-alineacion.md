# Validación manual de la alineación (paso 3 del protocolo)

**Para qué sirve.** El protocolo de alineación (`docs/protocols/alignment.md`, paso 3) exige
contrastar la alineación automática con un emparejamiento hecho a mano sobre al menos 100 pares.
Esta hoja reúne esos pares; quien etiqueta contesta si/no y el repositorio calcula la
concordancia entre ambas alineaciones. El juez automático no sustituye este paso.

**Quién.** Una persona del equipo que no haya mirado las cifras de la alineación. **Cuánto toma.**
Entre 30 y 60 segundos por par, de 50 a 100 minutos en total.

## La pregunta

Cada fila trae dos frases de la misma reunión (`meeting_id`): `extracted_decision` (lo que extrajo
el sistema) y `reference_decision` (la decisión de referencia, traducida al inglés). En `same`:

- **`si`**: ambas frases describen la misma decisión, aunque estén redactadas distinto o una sea
  más detallada que la otra.
- **`no`**: describen decisiones distintas, o una trata un aspecto que la otra no menciona.

No hay tercera opción: si hay duda, se elige la respuesta más probable y se anota el motivo en
`notes` (opcional). No se deja ninguna fila vacía. Cada par se juzga solo: no hace falta cuidar
que una decisión quede emparejada una única vez.

## Cómo se llena

El archivo es `data/processed/alignment-validation/<corrida>.<serie>.manual.csv`. Se abre en una
hoja de cálculo y solo se escriben `same` y, si hace falta, `notes`.

- Guardar como **CSV UTF-8 (delimitado por comas)**, con las mismas seis columnas, sin agregar
  ni reordenar filas. Detalles en [`EMPIEZA-AQUI.md`](asignacion/EMPIEZA-AQUI.md) §4.
- **No abrir** `reports/experiment-a/<corrida>/validacion-manual-<serie>-clave.json`. Guarda la
  similitud y lo que decidió la alineación automática; verlos sesgaría las respuestas. El orden de
  las filas ya está barajado.
- Las etiquetas son solo de la persona que las pone: nadie las prellena.

## Cómo se arma la muestra

`uv run afg experiment a-validacion-hoja --run-name <corrida>` toma una corrida guardada y la
referencia de la serie (solo series de desarrollo), alinea con τ = 0,70 y sortea 100 pares
(`manual_validation_sample_size`): la mitad entre los que la alineación automática empareja y la
otra mitad entre pares de la misma reunión que descarta pero tienen similitud de al menos 0,50.
Si faltan pares emparejados, se completa con descartados. Semilla, reparto y piso están en
`[alignment.manual_validation]` de `config/experiments.toml`, fijados antes de etiquetar. El
comando se niega a pisar una hoja con etiquetas (salvo `--force`).

## Después

```bash
uv run afg experiment a-validacion-puntaje --run-name <corrida>
```

Exige todas las etiquetas y reporta la **concordancia** del protocolo
(`alignment.concordance`: pares que ambas alineaciones emparejan, sobre los que empareja al menos
una), el acuerdo observado, la matriz de confusión, cuántos pares emparejados por la alineación
confirmó la persona y cuántos de los descartados emparejaría. No hay umbral de aprobación. Como
la muestra está estratificada, las proporciones por grupo describen cada grupo, no toda la serie.
