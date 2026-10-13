"""Variable registry: description, unit and valid domain of every column of the five levels.

The notebook's data dictionary is built from this single registry
(:func:`table_dictionary`), so a column added to a table without documentation is caught by
``tests/test_eda_tables.py`` instead of silently appearing undocumented. Descriptions are in
Spanish because they are read by the project's reviewers.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from afg.eda.quality import data_dictionary


@dataclass(frozen=True, slots=True)
class VariableSpec:
    """Metadata of one variable."""

    description: str
    unit: str = ""
    domain: str = ""


_POSITIVE_COUNT = ">= 0"
_SHARE = "[0, 1]"

VARIABLES: dict[str, VariableSpec] = {
    # keys and descriptors
    "series_id": VariableSpec("Identificador de la serie AMI (cuatro reuniones a-d)"),
    "meeting_id": VariableSpec("Identificador de la reunión: serie más letra de posición"),
    "decision_id": VariableSpec("Identificador de la decisión: reunión más número de orden"),
    "sentence_id": VariableSpec("Identificador de la oración abstractiva de origen en AMI"),
    "pair_id": VariableSpec("Identificador del par de decisiones dentro de la serie"),
    "speaker": VariableSpec("Letra del hablante en los archivos NXT", domain="A-E"),
    "participant_id": VariableSpec("Identificador público (seudónimo) del participante en AMI"),
    "site": VariableSpec("Sitio de grabación", domain="ES, IS, TS"),
    "split": VariableSpec(
        "Partición congelada de las series (ADR 0005)", domain="development, evaluation"
    ),
    "position": VariableSpec("Letra de la reunión dentro de la serie", domain="a, b, c, d"),
    "position_index": VariableSpec("Orden cronológico de la reunión en la serie", domain="1-4"),
    "role": VariableSpec("Rol de escenario del hablante", domain="PM, ID, ME, UI"),
    "native_language": VariableSpec("Lengua nativa declarada (vacía si se desconoce)"),
    "native_status": VariableSpec(
        "Nativo o no nativo de inglés derivado de la lengua nativa",
        domain="native, non_native, unknown",
    ),
    "recording_date": VariableSpec("Fecha de grabación según meetings.xml"),
    "start": VariableSpec(
        "Inicio real de la reunión (fecha y hora); vacío si meetings.xml no trae la hora"
    ),
    # series level
    "n_meetings": VariableSpec("Reuniones de la serie", "reuniones", "4"),
    "n_decisions": VariableSpec(
        "Decisiones (oraciones DECISIONS del resumen abstractivo)", "decisiones", _POSITIVE_COUNT
    ),
    "n_cross_meeting_pairs": VariableSpec(
        "Pares de decisiones de reuniones distintas de la serie", "pares", _POSITIVE_COUNT
    ),
    "n_candidates": VariableSpec(
        "Pares candidatos con el punto de operación por defecto del bloqueador",
        "pares",
        _POSITIVE_COUNT,
    ),
    "candidate_rate": VariableSpec("Candidatos entre pares posibles", "proporción", _SHARE),
    "anchoring_rate": VariableSpec(
        "Proporción de decisiones con al menos un acto de diálogo de evidencia",
        "proporción",
        _SHARE,
    ),
    "median_decision_tokens": VariableSpec(
        "Mediana de tokens de contenido por decisión", "tokens", _POSITIVE_COUNT
    ),
    "total_turns": VariableSpec("Turnos de habla de la serie", "turnos", _POSITIVE_COUNT),
    "total_characters": VariableSpec(
        "Caracteres hablados de la serie", "caracteres", _POSITIVE_COUNT
    ),
    "total_words": VariableSpec("Palabras habladas de la serie", "palabras", _POSITIVE_COUNT),
    "total_duration_seconds": VariableSpec("Duración total de la serie", "s", "> 0"),
    # meeting level
    "duration_seconds": VariableSpec("Duración de la reunión según meetings.xml", "s", "> 0"),
    "n_speakers": VariableSpec("Hablantes que intervinieron", "personas", "0-5"),
    "n_turns": VariableSpec("Turnos de habla", "turnos", _POSITIVE_COUNT),
    "n_dialogue_acts": VariableSpec("Actos de diálogo distintos", "actos", _POSITIVE_COUNT),
    "n_characters": VariableSpec("Caracteres hablados", "caracteres", _POSITIVE_COUNT),
    "n_words": VariableSpec(
        "Palabras habladas (separadas por espacio)", "palabras", _POSITIVE_COUNT
    ),
    "n_anchored_decisions": VariableSpec(
        "Decisiones de la reunión con evidencia", "decisiones", _POSITIVE_COUNT
    ),
    "approx_tokens": VariableSpec(
        "Tokens estimados: techo de 1,3 por palabra (aproximación, no medición)",
        "tokens",
        _POSITIVE_COUNT,
    ),
    "approx_tokens_chars": VariableSpec(
        "Tokens estimados: caracteres divididos entre 4 (contraste de la anterior)",
        "tokens",
        _POSITIVE_COUNT,
    ),
    "context_ratio": VariableSpec(
        "Tokens estimados entre la ventana de contexto", "proporción", _POSITIVE_COUNT
    ),
    "fits_context": VariableSpec(
        "La transcripción cabe en la ventana de contexto", domain="True, False"
    ),
    # speaker level
    "n_chars": VariableSpec(
        "Caracteres (hablados o de la oración, según el nivel)", "caracteres", _POSITIVE_COUNT
    ),
    "talk_seconds": VariableSpec("Segundos de habla del hablante", "s", _POSITIVE_COUNT),
    "talk_share": VariableSpec("Parte de las palabras de la reunión", "proporción", _SHARE),
    "n_decision_acts": VariableSpec(
        "Actos del hablante citados como evidencia de decisiones", "actos", _POSITIVE_COUNT
    ),
    # decision level
    "n_tokens": VariableSpec(
        "Tokens de contenido de la decisión (tokenización del bloqueador)",
        "tokens",
        _POSITIVE_COUNT,
    ),
    "n_evidence_acts": VariableSpec(
        "Actos de diálogo vinculados a la decisión", "actos", _POSITIVE_COUNT
    ),
    "anchored": VariableSpec(
        "La decisión tiene al menos un acto de evidencia", domain="True, False"
    ),
    "has_non_decision_marker": VariableSpec(
        "Contiene una frase de propuesta abierta o duda (indicio, precisión sin medir)",
        domain="True, False",
    ),
    "n_evidence_roles": VariableSpec(
        "Roles distintos entre los actos de evidencia", "roles", "0-4"
    ),
    "evidence_role": VariableSpec(
        "Rol más frecuente en la evidencia (mixed si hay empate)", domain="PM, ID, ME, UI, mixed"
    ),
    "exact_duplicate": VariableSpec(
        "Texto idéntico a otra decisión de la serie (minúsculas, espacios colapsados)",
        domain="True, False",
    ),
    "near_duplicate": VariableSpec(
        "Mismo conjunto de tokens de contenido que otra decisión de la serie",
        domain="True, False",
    ),
    # pair level
    "earlier_decision_id": VariableSpec("Decisión de la reunión anterior"),
    "later_decision_id": VariableSpec("Decisión de la reunión posterior"),
    "earlier_meeting_id": VariableSpec("Reunión de la decisión anterior"),
    "later_meeting_id": VariableSpec("Reunión de la decisión posterior"),
    "meeting_distance": VariableSpec("Reuniones que separan al par", "reuniones", "{1, 2, 3}"),
    "n_tokens_earlier": VariableSpec(
        "Tokens de contenido de la decisión anterior", "tokens", _POSITIVE_COUNT
    ),
    "n_tokens_later": VariableSpec(
        "Tokens de contenido de la decisión posterior", "tokens", _POSITIVE_COUNT
    ),
    "shared_tokens": VariableSpec(
        "Tokens compartidos por las dos decisiones", "tokens", _POSITIVE_COUNT
    ),
    "overlap": VariableSpec(
        "Coeficiente de solapamiento: compartidos entre el menor de los dos conjuntos",
        "proporción",
        _SHARE,
    ),
    "is_candidate": VariableSpec(
        "Supera el punto de operación (solapamiento >= 0,30 y al menos 2 tokens compartidos)",
        domain="True, False",
    ),
    # turn level (turn_length_distribution input)
    "turn_index": VariableSpec("Orden del turno dentro de la reunión", domain=_POSITIVE_COUNT),
    "end": VariableSpec("Fin del turno", "s"),
    "duration": VariableSpec("Duración del turno", "s", _POSITIVE_COUNT),
}


def table_dictionary(table: pd.DataFrame) -> pd.DataFrame:
    """:func:`afg.eda.quality.data_dictionary` filled from :data:`VARIABLES`. Columns the
    registry does not know stay blank so that gaps are visible, not invented."""
    return data_dictionary(
        table,
        descriptions={k: v.description for k, v in VARIABLES.items()},
        units={k: v.unit for k, v in VARIABLES.items()},
        domains={k: v.domain for k, v in VARIABLES.items()},
    )
