# 0001. Registrar decisiones de arquitectura

## Estado

Aceptada

## Contexto

Este repositorio es un arnés de evaluación de investigación con un horizonte de
implementación largo (paso cero, anotación gold de OE1, experimentos OE2/OE3, atribución
OE4). Las decisiones sobre *cómo se construye el arnés* (organización, herramientas, límite
del instrumento) necesitan un registro duradero independiente de la propuesta
(`docs/propuesta.md`), que documenta las decisiones de investigación de la tesis, no las decisiones de ingeniería de
este código.

## Decisión

Usar registros de decisiones de arquitectura (ADR) livianos bajo `docs/decisions/`, un
archivo por decisión, numerados secuencialmente, siguiendo el formato popularizado por
Michael Nygard.

## Consecuencias

Futuros contribuyentes (incluido el propio equipo en el futuro) pueden ver por
qué el proyecto está organizado como está sin necesidad de arqueología en el historial de
commits.
