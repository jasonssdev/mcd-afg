# 0013. La base de C3 es la de una corrida de C2 con sus decisiones sustituidas por las de la anotación de oro

## Estado

Aceptada (2026-10-28). Decide cómo se compone la base que consulta la condición C3 (tesis, sección 5.3), pendiente desde que el arnés dejó C3 como la única condición sin implementar ([issue #23](https://github.com/jasonssdev/mcd-afg/issues/23)).

## Contexto

C3 responde igual que C2 (`openkos query --json --limit K`), pero sobre una base compilada a partir de la anotación humana adjudicada en lugar de la extracción automática. Su función en el Experimento B es **atribuir**: si C2 responde mal, la comparación C2 → C3 debe poder decir si la causa es la idea de la base (objetos con procedencia) o el relleno que hizo el modelo.

Una base de OpenKOS no contiene solo decisiones. Una corrida del Experimento A deja, además de `decisions/`, conceptos, eventos, personas, proyectos, las fuentes (`sources/`) y los textos crudos (`raw/`); una consulta recupera y cita cualquiera de ellos, no solo decisiones. Si C3 se construyera con las decisiones de oro y nada más, C2 y C3 diferirían en **dos** cosas a la vez (las decisiones y el resto del contenido recuperable), y la diferencia entre sus respuestas no se podría atribuir a ninguna de las dos.

Los insumos existen para las series de desarrollo con referencia adjudicada (hoy ES2015 y TS3009; ES2016, IS1003 y TS3005 están adjudicadas pero son de evaluación y el Experimento A las rechaza, [ADR 0005](0005-adr-development-evaluation-split.md)): `load_series_reference` entrega las decisiones con su evidencia en actos de diálogo, `<SERIE>.reference-en.csv` su texto en inglés y `<SERIE>.candidates.adjudicated.csv` las relaciones adjudicadas entre decisiones de reuniones distintas.

## Decisión

1. **Una base de C3 por cada corrida de C2.** El espacio de trabajo de C3 de la serie `S` y la corrida `r` se construye a partir del de C2 (`data/interim/openkos/<corrida>/S/run-r/`) y vive en `data/interim/openkos-c3/<corrida>/S/run-r/`. `afg c3 build` lo escribe.
2. **Solo cambian las decisiones.** Se copian sin tocar `openkos.yaml` (la semilla y la temperatura son lo que `require_reproducible` comprueba al consultar), `raw/`, y de `bundle/` todo menos `decisions/`: conceptos, eventos, personas, proyectos, fuentes y el resto. No se copian los índices (`.openkos/`): se reconstruyen con `openkos reindex --force` sobre el paquete resultante. La sección «Decisions» de `bundle/index.md` se regenera con las decisiones de oro (dejarla apuntaría a archivos que ya no existen); el registro de OpenKOS (`log.md`) se deja como está: es la historia de la extracción y no se consulta.
3. **`bundle/decisions/` se escribe desde la referencia adjudicada**: las filas con estado final `decision`, incluidos los hijos de una fila `compuesta`, en **inglés** (la base y las preguntas de C2 están en inglés; se usa la misma traducción que el Experimento A usa como referencia). Una decisión por archivo, con el formato que C2 produce, de modo que el lector de paquetes que mapea las citas a actos de diálogo funciona igual en las dos condiciones. La cita de evidencia es el texto de los turnos que contienen los actos de oro. El sello `generated.by` es `afg/c3-gold`, para que ningún archivo de C3 pase por uno de OpenKOS.
4. **Las relaciones adjudicadas son enlaces.** Una relación aceptada (`final_relation` distinta de `no_relacionada` y con la dirección confirmada) se escribe como enlace bajo `## Related` en las dos decisiones, con el tipo de la relación como descripción (por ejemplo «reaffirms» en la posterior y «reaffirmed by» en la anterior). No se inventa ningún otro objeto ni arista.
5. **Lo que no se puede escribir se descarta y se informa.** Una decisión de oro sin evidencia localizable en la transcripción no puede ser un concepto citable: se descarta y queda en `c3-manifest.json` con su motivo, junto con las relaciones que quedaron sin uno de sus extremos y las decisiones cuya evidencia vuelve incompleta. Nada se descarta en silencio.
6. **Solo series de desarrollo**, con la misma compuerta que `afg experiment a`: mientras la versión de OpenKOS no esté fijada, C3 no se construye para series de evaluación.

## Alternativas descartadas

- **Solo decisiones y fuentes.** Una base más fiel a la idea de «solo la anotación», pero C2 y C3 diferirían también en los conceptos y eventos que C2 recupera. La diferencia de respuestas mezclaría el error de extracción de decisiones con la presencia o ausencia de todo lo demás. Se descarta porque rompe la finalidad de C3.
- **Solo decisiones.** La misma objeción, agravada: sin `sources/` la consulta cambia además de forma (el recuperador deja de ver las transcripciones completas que C2 sí ve).
- **Una sola base de C3 por serie, compartida entre corridas.** Más barata, pero el espacio de C2 de cada corrida tiene su propia semilla y sus propios conceptos; compartirla haría que C3 comparara contra una corrida de C2 distinta de la que responde la pregunta, y la comprobación de semilla de `require_reproducible` no podría hacerse.

## Consecuencias

- **C3 queda atada a una corrida de C2.** Cambiar de corrida de C2 obliga a reconstruir C3. A cambio, el par (C2, C3) de la corrida `r` comparte semilla y contenido no decisorio, y su diferencia aísla el **error de extracción de decisiones**.
- **Los conceptos de máquina permanecen en C3.** C3 no es «solo anotación humana»: contiene los conceptos, eventos y demás que generó el modelo en esa corrida. Esto es parte de lo decidido y debe decirse en toda lectura de C3 (en consonancia con la tesis, sección 3, que no la llama techo teórico).
- **La evidencia de una cita es el turno completo.** Los actos de oro son más finos que un turno; el lector de paquetes de C2 asigna a una cita todos los actos de los turnos que toca, y C3 hereda ese criterio. Es el mismo grano que C2, lo que mantiene la comparación pareja, pero C3 no puede citar un acto suelto.
- **Evidencia repartida en turnos no contiguos.** El lector usa la primera cita que se mapea: una decisión de oro cuya evidencia abarca turnos no consecutivos conserva solo el primer tramo. El constructor lo detecta y lo lista en `evidence_partial` del manifiesto. Sobre ES2015 (corrida 0 de `humo-lote-dev`) el constructor escribió las 27 decisiones de oro, descartó 0 y marcó 10 con evidencia parcial; esa proporción debe leerse en cada manifiesto antes de interpretar resultados de C3.
- **Dependencia de la traducción.** Si la traducción al inglés cambia, hay que reconstruir C3 (`--overwrite`).
- **Lo verificado.** Los formatos y el recorrido de la evidencia están comprobados con pruebas con un ejecutor simulado. En la primera corrida real (ES2015, corrida 0 de `humo-lote-dev`, 21 preguntas de calibración, `reports/experiment-b/humo-c3-es2015/`), `openkos reindex` indexó la base en unos 14 s, y `openkos query` respondió las 21 preguntas sin errores y llevó decisiones de oro al contexto (23 bloques de `decisions/`, junto con conceptos, fuentes y eventos copiados de C2). Es una prueba de funcionamiento, no un resultado (ADR 0005).
- **C3 es optimista por construcción.** Las preguntas y sus respuestas de referencia se redactan desde la misma anotación que llena la base de C3, de modo que la respuesta suele estar escrita casi literalmente en una decisión de oro. Es lo que C3 debe medir (la base sin errores de extracción), pero toda lectura de la distancia C3 → C2 debe tenerlo presente.
- **Sin cambios.** La regla de citación ([ADR 0009](0009-adr-regla-de-citacion-correcta.md)), el criterio D16 ([ADR 0010](0010-adr-decisiones-del-analisis-del-experimento-b.md)) y el uso de OpenKOS sin modificar ([ADR 0006](0006-adr-c1-rag-separado-con-respuesta-de-openkos.md)).
