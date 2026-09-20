# Pautas de anotación de OE1: decisiones y relaciones entre reuniones

Congeladas antes de empezar la anotación. Implementan la sección 5.2 de la tesis
(definición de decisión) y la sección 3 / OE1 de la tesis (conjunto de etiquetas de
relación).

## Qué cuenta como decisión

Dada la evidencia de inestabilidad de anotación de la sección 1.4 de la tesis (dos equipos
competentes, el mismo corpus, el mismo constructo nominal, acuerdo peor que el azar),
"decisión" se define de forma restrictiva y verificable. Un candidato es una decisión
(`DecisionStatus.ACCEPTED` en `src/afg/domain/decision.py`) solo si se cumplen **las tres**
condiciones:

1. **Explícita** — al menos un acto de diálogo la formula o la ratifica.
2. **Aceptada** — no queda como una propuesta abierta al cierre del segmento de discusión.
3. **Anclada** — nombra tanto un objeto de decisión (qué se está decidiendo) como un
   contenido (qué se decidió al respecto).

Los candidatos que fallan cualquier condición se registran como no-decisiones
(`OPEN_PROPOSAL` / `OPEN_QUESTION` / `OPINION`), no se descartan: se necesitan para medir
falsos positivos.

## Etiquetas de relación entre reuniones

Para cada par elegible de decisiones dentro de una serie (ver
`src/afg/annotation/linking.py::chronological_candidate_pairs`), asignar exactamente una
etiqueta del conjunto cerrado definido en `src/afg/domain/relation.py::RelationType`:

| Etiqueta | Español (canónico) | Significado |
|---|---|---|
| `introduce` | introduce | Primera aparición de este objeto de decisión en la serie. |
| `reafirma` | reafirma | Reitera una decisión previa sin cambiar su contenido. |
| `refina` | refina | Acota o elabora el contenido de una decisión previa. |
| `revierte` | revierte | Revierte explícitamente una decisión previa. |
| `reemplaza` | reemplaza | Sustituye una decisión previa con contenido distinto. |
| `no_relacionada` | no_relacionada | Evaluada como candidata; no existe relación temporal. |

Las etiquetas se mantienen en español porque son el vocabulario de anotación propio de la
tesis, no un detalle de implementación para traducir.

**La dirección importa.** `source_decision_id` es siempre la decisión más tardía;
`target_decision_id` es siempre la decisión anterior con la que se relaciona. Una relación
con la etiqueta correcta pero con origen/destino invertidos es una falla de dirección
(hipótesis H3 de la tesis), que se puntúa por separado de una etiqueta incorrecta
(`src/afg/evaluation/metrics.py::relation_direction_accuracy`).

**La evidencia es obligatoria.** Cada relación lleva el id de reunión y el segmento de
acto de diálogo que la respalda (`TemporalRelation.evidence`).

## Regla anti-fuga (sección 5.1 de la tesis)

Anotar estrictamente en orden cronológico dentro de cada serie, sin consultar reuniones
posteriores a la que se está anotando. `src/afg/annotation/linking.py` impone esto de
forma estructural:

- `chronological_candidate_pairs` solo propone un par con el origen en la misma reunión o
  en una posterior a la del destino.
- `meetings_visible_when_annotating` devuelve exactamente las reuniones que una persona
  anotadora puede consultar para una decisión dada.
- `validate_no_leakage` verifica a posteriori una relación propuesta contra esta regla.

## Confiabilidad

Doble anotación en al menos el 25 % de las series, con kappa de Cohen reportado
(`src/afg/annotation/agreement.py::compute_agreement`), y un registro de adjudicación
documentado para cada desacuerdo (`build_adjudication_log`). Dado el precedente de la
sección 1.4 de la tesis, no se asume que el acuerdo sea alto — se mide y se reporta
independientemente del resultado.
