# Criterios de inclusión / exclusión

Estos criterios rigen qué entra a `refs.bib` y a `screening.csv`. Formalizan el estándar de
verificación ya aplicado en la sección 8 de la tesis
(`docs/propuesta.md`): "todas las entradas se verificaron contra una fuente
primaria".

## Criterios de inclusión

Una referencia se incluye si cumple **todas** las siguientes condiciones:

1. **Verificable contra una fuente primaria.** ACL Anthology, Crossref/DOI del editor,
   w3.org, nist.gov, o un registro autoritativo equivalente. Una cita copiada de una fuente
   secundaria (la bibliografía de otro artículo, una entrada de blog) sin verificación
   independiente no se puede incluir hasta que se verifique.
2. **Directamente relevante para al menos uno de:** el AMI Meeting Corpus y la detección de
   decisiones en reuniones; RAG y representaciones estructuradas/en grafo; extracción de
   información y construcción de bases de conocimiento basada en LLM; alucinación,
   atribución o evaluación con LLM como juez; conocimiento temporal y QA sensible al
   tiempo; memoria organizacional o racionalidad de diseño; procedencia y marcos de gestión
   de riesgo de IA.
3. **Asignable a exactamente una sección de la tesis (8.1-8.7) y al menos un eje temático**
   (ver `README.md`).

## Criterios de exclusión

Una referencia se excluye (o se marca `status = excluded` en `screening.csv` en vez de
eliminarse, para preservar el rastro de cribado) si:

- No puede verificarse de forma independiente contra una fuente primaria.
- Está fuera de tema respecto de los criterios de inclusión anteriores.
- Está reemplazada por una versión posterior y verificada del mismo trabajo ya presente en
  `refs.bib` (la entrada reemplazada se mantiene en `screening.csv` con un puntero en
  `notes`, no se elimina en silencio).

## Manejo de preprints

Los preprints **no se excluyen** — varios son fundamentales para la afirmación de novedad
de esta tesis (sección 9 de la tesis: Cai & O'Connor 2025, Zhang & Li 2026). Se incluyen
bajo una regla de divulgación más estricta:

- `peer_reviewed = false` en `screening.csv`.
- `keywords` en `refs.bib` incluye `preprint, not-peer-reviewed`.
- Cualquier afirmación proveniente de un preprint en texto escrito debe decirlo
  explícitamente en el punto de la cita, no solo en la bibliografía.

## Requisito de DOI

Cada entrada debería llevar un campo `doi` cuando la publicación lo asigne. Las entradas
sin DOI (artículos de taller anteriores a la asignación de DOI, recomendaciones del W3C,
informes del NIST con DOI pero a veces citados por número de informe, working papers) se
marcan en `screening.csv` (columna `doi` en blanco) en vez de asignárseles un identificador
fabricado. `src/afg/bibliography/audit.py` reporta las entradas sin DOI como un vacío de
cobertura, no como un error — algunas legítimamente no tienen DOI.
