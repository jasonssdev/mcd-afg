# Bibliografía

La revisión de literatura vive aquí, organizada bajo dos esquemas ortogonales:

## 1. Las siete secciones bibliográficas de la sección 8 de la tesis

`refs.bib` agrupa cada referencia bajo las mismas siete secciones usadas en la tesis
(`docs/propuesta.md`, sección 8):

| Sección | Tema |
|---|---|
| 8.1 | Corpus y detección de decisiones en reuniones |
| 8.2 | Recuperación aumentada (RAG) y estructuración |
| 8.3 | Extracción de información y construcción de bases de conocimiento con LLM |
| 8.4 | Alucinación, atribución y evaluación |
| 8.5 | Temporalidad del conocimiento |
| 8.6 | Memoria organizacional y racionalidad de diseño |
| 8.7 | Procedencia y marcos de riesgo |

Cada entrada BibTeX lleva un campo `keywords` con su sección, p. ej. `section-8-3`, para
que `src/afg/bibliography/audit.py` pueda reportar cobertura por sección sin volver a
parsear texto libre.

## 2. Los tres ejes temáticos

Independientemente de la sección bibliográfica, cada referencia también se ubica en uno de
tres ejes propuestos por el equipo al mapear la literatura en la semana 3 del curso:

1. **PLN clásico vs. modelos de lenguaje** — detección de decisiones basada en reglas o
   estadística (p. ej. Hsueh & Moore, Fernández et al.) frente a extracción y generación
   basadas en LLM.
2. **RAG vs. bases compiladas/estructuradas** — recuperación sobre documentos crudos frente
   a construir una representación tipada persistente antes de consultar.
3. **Procesamiento local-first y privacidad** — si el enfoque es desplegable sin enviar
   datos organizacionales a un servicio de terceros.

El eje se registra por referencia en `screening.csv` (columna `axis`), no en `refs.bib`,
porque la asignación de eje de una referencia es un juicio editorial hecho durante el
cribado, no un hecho bibliográfico.

## Cómo entra una referencia nueva a esta bibliografía

1. **Agregar la entrada BibTeX a `refs.bib`**, en la sección a la que pertenece, con una
   clave de cita estable (`autor+año+tituloCorto`, en minúsculas). Verificarla contra una
   fuente primaria (ACL Anthology, Crossref, DOI del editor) antes de agregarla — este
   archivo hereda el estándar de verificación de la tesis, no lo relaja.
2. **Agregar una fila a `screening.csv`** que registre la decisión de inclusión/exclusión,
   la sección de la tesis y el eje que respalda, si está revisada por pares, y si la
   cita/DOI se verificó de forma independiente.
3. **Escribir una nota a partir de `notes/TEMPLATE.md`**, guardada como
   `notes/<clave-de-cita>.md`, que capture qué afirma el trabajo, qué mide y —lo más
   importante— qué **no** cierra, para que los borradores posteriores no tengan que
   releer la fuente para recordar por qué se citó.

## Preprints

Cualquier entrada que la tesis marque como **preprint sin revisión por pares** lleva
`keywords = {..., preprint, not-peer-reviewed}` y una `note = {Preprint, not peer
reviewed}` en `refs.bib`. `src/afg/bibliography/audit.py` las reporta por separado para que
nunca se citen en silencio como si fueran revisadas por pares.
