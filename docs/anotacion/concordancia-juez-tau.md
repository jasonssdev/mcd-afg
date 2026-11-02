# Concordancia juez-persona sobre 50 pares (ADR 0012)

**Para qué sirve.** Para fijar el umbral τ del Experimento A se usó un juez automático que
responde «¿los dos textos describen la misma decisión?». Falta comprobar que, sobre una muestra,
una persona responde lo mismo. Esta hoja reúne 50 pares; quien etiqueta contesta si/no y el
repositorio calcula el acuerdo con el juez.

**Quién.** `jss` (una sola persona etiqueta). **Cuánto toma.** Entre 30 y 60 segundos por par, unos
25 a 50 minutos en total.

## La pregunta

Cada fila trae dos frases: `extracted_decision` (lo que extrajo el sistema) y
`reference_decision` (la decisión de referencia, traducida al inglés). Se responde en la columna
`same`:

- **`si`**: ambas frases describen la misma decisión tomada en esa reunión (`meeting_id`), aunque
  estén redactadas distinto o una sea más detallada que la otra.
- **`no`**: describen decisiones distintas, o una trata un aspecto que la otra no menciona.

No hay tercera opción: si hay duda, se elige la respuesta más probable y se anota el motivo en
`notes` (columna libre y opcional). No se deja ninguna fila vacía.

## Cómo se llena

El archivo es `data/processed/judge-calibration/tau-concordancia.jss.csv`. Se abre en una hoja de
cálculo y solo se escriben `same` y, si hace falta, `notes`; el resto no se toca.

- Guardar como **CSV UTF-8 (delimitado por comas)**, con las mismas seis columnas
  (`pair_id`, `meeting_id`, `extracted_decision`, `reference_decision`, `same`, `notes`), sin
  agregar ni reordenar filas. Detalles en [`EMPIEZA-AQUI.md`](asignacion/EMPIEZA-AQUI.md) §4.
- **No abrir** `reports/experiment-a/tau-calibration/concordancia-key.json`. Guarda la similitud,
  el tramo y el veredicto del juez; verlos sesgaría las respuestas. El orden de las filas ya está
  barajado a propósito.
- Las etiquetas son solo de la persona que las pone: nadie las prellena.

## Después

```bash
uv run afg judge tau-concordance-score
```

El comando exige las 50 etiquetas, calcula el acuerdo observado, el kappa de Cohen con intervalo
de confianza del 95 %, la matriz de confusión, el acuerdo por tramo de similitud y la proporción
de «sí» del juez frente a la de la persona por debajo y por encima de τ = 0,70, y guarda todo en
`reports/experiment-a/tau-calibration/concordancia.json`. No hay umbral de aprobación: un acuerdo
bajo reabre el ADR 0012 («Pendiente»).

La hoja se generó con `uv run afg judge tau-concordance-sheet` (muestra de 6 pares por tramo más 2
al azar, semilla 42, definidas en `[alignment.concordance]` de `config/experiments.toml`). El
comando se niega a pisar una hoja que ya tenga etiquetas.
