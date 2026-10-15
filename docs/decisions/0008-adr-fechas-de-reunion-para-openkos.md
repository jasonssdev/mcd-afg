# 0008. Las reuniones se ingestan con fecha de evento real y hora real cuando existe, y con hora sintética que solo preserva el orden cuando no

## Estado

Aceptada (2026-10-15)

## Contexto

OpenKOS ordena las decisiones de un espacio de trabajo por la fecha de evento (`event_date`) de
su fuente, que se entrega con `openkos ingest --event-date YYYY-MM-DDTHH:MM`. C2 ingesta las
cuatro reuniones de una serie, en orden, en un mismo espacio de trabajo (D15), y de ese orden
depende qué decisión se considera posterior a cuál. Por eso las cuatro reuniones necesitan
fechas estrictamente crecientes.

Las transcripciones congeladas no traen la fecha; vive en `corpusResources/meetings.xml` de AMI
(atributos `dateOnly` y `startTime`). Lo medido sobre ese archivo para las 14 series de OE1 (análisis completo y reproducible en el
[notebook 08](../../notebooks/08-jss-fechas-de-reunion.ipynb), calculado con
`meeting_date_table` y `series_date_summary`):

- Las cuatro reuniones de una serie comparten un mismo `dateOnly`. La fecha sola no ordena.
- El formato de `dateOnly` es día-mes-año, con año de dos cifras en las series ES
  (`09-03-05`) y de cuatro en IS y TS (`23-11-2004`). El orden día-mes es el que ya aplica
  `src/afg/eda/tables.py`, que se reutiliza.
- `startTime` (por ejemplo `11h03`) existe en 6 series: ES2008, IS1003, IS1004, IS1006,
  IS1008 e IS1009. En **8 de las 14** no existe: está vacío en ES2002, ES2014, ES2015 y
  ES2016, y el atributo está ausente en TS3003, TS3005, TS3009 y TS3011.

## Decisión

1. **Fecha real siempre.** Se usa `dateOnly` de AMI, interpretada como día-mes-año.
2. **Hora real cuando existe.** Con `startTime` presente, el `event_date` es la fecha más esa
   hora (`time_source = "ami"`).
3. **Hora sintética cuando falta.** El escenario de AMI define las cuatro reuniones en
   secuencia (a, b, c, d); se les asigna la fecha real con las 09:00, 10:00, 11:00 y 12:00
   respectivamente (`time_source = "synthetic"`). La asignación es por reunión, no por serie.
4. **Validación.** Dentro de una serie, las fechas resultantes deben ser estrictamente
   crecientes de a a d. Si no lo son, el procesamiento se detiene con un error que nombra la
   serie; no se reordena ni se corrige en silencio.
5. **Trazabilidad.** El manifiesto de cada corrida registra, por reunión, la fecha pasada y su
   `time_source`.

Implementación: `src/afg/extraction/openkos/event_dates.py` (`read_series_event_dates`,
`attach_event_dates`) y `MeetingSource.event_date` / `MeetingSource.time_source` en
`workspace.py`.

## Consecuencias

- **Las horas sintéticas son una desviación declarada.** En 8 de las 14 series el `event_date`
  que recibe OpenKOS contiene una hora que no ocurrió. Debe indicarse como tal en la
  metodología y en el informe de resultados.
- **Solo codifican el orden.** No representan la duración real de las reuniones ni los
  intervalos entre ellas: una separación de una hora entre reuniones sintéticas no es un dato.
  Ningún análisis puede usar la diferencia entre fechas de evento como medida de tiempo.
- **Afectan lo que depende del orden.** La dirección de las relaciones entre decisiones
  (cuál reemplaza a cuál) se decide con ese orden en OpenKOS, y con ella la respuesta del
  estrato E3 (evolución de una decisión). El orden a→d es el del escenario de AMI, de modo que
  el sesgo esperado es nulo, pero la fecha no es evidencia independiente del orden.
- **Conviven dos calidades de fecha.** Las 6 series con hora real y las 8 con hora sintética
  pueden compararse en los resultados por `time_source`, para comprobar que la diferencia no
  mueve las cifras.
- **La validación puede detener una serie.** Si una hora real no respeta el orden a→d, la
  corrida falla con un mensaje claro; la decisión de qué hacer entonces queda a la dirección
  del proyecto.

## Trazabilidad

- Fuente: `data/raw/ami/corpusResources/meetings.xml`.
- Evidencia: [notebook 08](../../notebooks/08-jss-fechas-de-reunion.ipynb), con la tabla por
  reunión, el resumen por serie (fechas distintas, horas reales, orden y separaciones) y las
  alternativas descartadas; sus cifras salen de `meeting_date_table` y `series_date_summary`.
- Código: `src/afg/extraction/openkos/event_dates.py`; pruebas en
  `tests/test_openkos_event_dates.py`.
- Se apoya en D15 (orden cronológico dentro de la serie) y en el
  [ADR 0006](0006-adr-c1-rag-separado-con-respuesta-de-openkos.md) (OpenKOS solo por CLI).
