# 0020. Se mantiene el filtro léxico (blocking) de la Tarea B y su pérdida de relaciones se declara como limitación de la referencia

## Estado

Aceptada (2026-11-03), por decisión de `jss`. Resuelve el [issue #205](https://github.com/jasonssdev/mcd-afg/issues/205) (recall del filtro léxico). Se aparta, con la razón explícita, de la guía fijada de antemano en `docs/anotacion/asignacion/tareas-jss.md` (§5). Complementa al [ADR 0013](0013-adr-composicion-de-la-base-c3.md) y al [ADR 0016](0016-adr-relaciones-temporales-de-openkos.md), cuyos resultados dependen de las relaciones anotadas. La decisión se toma **antes de que exista cualquier resultado sobre series de evaluación**.

## Contexto

La Tarea B anota relaciones entre decisiones de reuniones distintas, pero solo sobre los pares que pasan un filtro léxico (*blocking*): coeficiente de solapamiento (*overlap coefficient*) de al menos 0,30 y al menos 2 tokens compartidos. De 3.071 pares entre reuniones distintas, 92 son candidatos. Lo que el filtro rechaza no se anota, de modo que toda relación real entre pares rechazados queda fuera de la referencia.

Para medir esa pérdida se anotaron cuatro muestras de 50 pares rechazados, una por serie (IS1004, ES2016, IS1003 y TS3005), la Tarea C. El resultado ([notebook 18](../../notebooks/18-jss-anotacion-f2-adjudicacion.ipynb), §8) es un *recall* total de **0,407** (intervalo de Wilson al 95 % de 0,245 a 0,596): 6 falsos negativos en 200 pares, unas 26,3 relaciones perdidas estimadas [12,2; 55,4] frente a 18 conservadas. Por sitio, ES 1,000 [0,236; 1,000] (cero falsos negativos, pero con 50 pares no se descarta una pérdida de hasta unas 13 relaciones), IS 0,352 y TS 0,344. La pérdida es sustancial. El 2026-11-03 se decidió no pedir una muestra adicional: una muestra mayor solo estrecharía los intervalos.

La guía de `tareas-jss.md` (§5) fijó de antemano que, si los falsos negativos son muchos en un sitio, «lo que toca es revisar el punto de operación, no muestrear más», y que toda decisión se escribe. Para que esa revisión se pudiera juzgar con datos, el [notebook 25](../../notebooks/25-jss-canal-semantico-del-bloqueador.ipynb) (`src/afg/annotation/semantic_channel.py`) midió qué aportaría un canal semántico (similitud coseno de embeddings `bge-m3`) añadido al filtro léxico:

- 3 de los 6 falsos negativos no comparten ningún token de contenido con su pareja, y los otros 3 comparten uno solo. Ningún ajuste del umbral léxico puede recuperar los primeros.
- Con un umbral coseno t = 0,75, el canal agrega 149 pares (75 de ellos en series que se anotan por dos personas; unas 3,7 horas adicionales por pasada de anotación, a 1,5 minutos por par), recupera 2 de los 6 falsos negativos (ambos de TS3005) y marca 2,6 % de falsas alarmas. El *recall* estimado de la unión sería 0,636 [0,404; 0,821], cifra optimista porque el umbral se exploró sobre esos mismos 6 falsos negativos.
- Con t = 0,50 recupera los 6, pero agrega 2.087 pares.

La razón de `jss` para mantener el filtro es una sola: no sumar carga de anotación al equipo (`gm` y `gv`) mientras se termina el banco de preguntas (#32 y #33). No es una conclusión de que la pérdida sea pequeña: la medición dice lo contrario.

## Decisión

1. **El filtro léxico de la Tarea B se mantiene sin cambios**: coeficiente de solapamiento de al menos 0,30 y al menos 2 tokens compartidos; `BLOCKER_VERSION` no cambia. No se agrega el canal semántico ni se generan ni anotan pares candidatos nuevos.
2. **La pérdida se declara como limitación de la ground truth de relaciones.** El *recall* del filtro, 0,407 [0,245; 0,596] (Wilson 95 %), se informa con su intervalo en todo lugar donde aparezcan resultados de relaciones: Experimento A (relaciones), lectura de H4 y de E3, y la tesis. No se presenta la referencia de relaciones como completa.
3. **Esta decisión se aparta de la guía fijada de antemano** (`tareas-jss.md`, §5), que ante una pérdida grande indicaba revisar el punto de operación. El motivo es la carga de anotación del equipo (ver Contexto). La partida es informada, no ciega: la alternativa está medida y versionada (notebook 25), con su costo y su beneficio.
4. **Experimento A informa la precision de existencia de enlaces también sin los falsos positivos sin par candidato** (`fp_breakdown["not_candidate"]`), junto a la precision estándar. La *existencia* se lee así: la precision estándar es un piso (un enlace de la máquina sobre un par que el filtro nunca ofreció cuenta como falso positivo, aunque pueda ser una relación real); la precision sin esos casos es el extremo optimista; y el *recall* de existencia es una cota superior, porque las relaciones perdidas por el filtro no están en el denominador. La exactitud de tipo y de dirección se calcula solo sobre enlaces de la referencia y no cambia. El puntaje (`src/afg/evaluation/relations.py`) no cambia; se agrega una columna a la tabla de `src/afg/experiments/relations_summary.py`.
5. **Las preguntas E3 del banco (#32) se redactan a partir de las transcripciones, no solo de las relaciones anotadas**, para que el banco no herede el punto ciego del filtro. Se solicita a `gm` en el issue #32.
6. **La medición del canal semántico queda versionada** (notebook 25 y `semantic_channel.py`) como base para reabrir la decisión en trabajo futuro. Reabrirla exige un ADR nuevo y fijar el umbral **antes** de anotar.
7. **El registro de congelamiento (#237) congela la referencia tal como está**, sin cambio del filtro.

## Alternativas descartadas

- **Canal semántico con t = 0,75.** Es la opción que más recupera por costo: +149 pares (unas 3,7 horas por pasada, 75 en series con doble anotación), 2 de 6 falsos negativos, 2,6 % de falsas alarmas, *recall* estimado de la unión de 0,636 [0,404; 0,821], optimista por haber explorado el umbral sobre los mismos 6 casos. Se descarta por la carga de anotación que suma al equipo mientras se termina el banco de preguntas. Es la alternativa más razonable si la decisión se reabre.
- **Canal semántico con t = 0,50.** Recupera los 6 falsos negativos, pero agrega 2.087 pares (total 2.179, unas 23,7 veces los 92 actuales) y marca 71,6 % de los pares sin relación muestreados: apenas filtra. Inviable en horas de anotación.
- **Aflojar el filtro léxico** (coeficiente 0,25 o 0,20, o mínimo de 1 token). Bajar solo el coeficiente agrega 35 y 44 pares y recupera 0 de los 6 falsos negativos, porque todos tienen a lo sumo un token compartido. Bajar el mínimo a 1 token recupera 1, agrega 620 pares y marca 64 de 194 pares sin relación. Ninguno toca los 3 falsos negativos sin tokens en común.
- **Una muestra de recall adicional.** Solo estrecharía los intervalos, sobre todo el de ES, sin cambiar la conclusión (`jss`, 2026-11-03), y la guía de `tareas-jss.md` (§5) advierte que muestrear más no corrige un punto de operación con pérdida grande.

## Consecuencias

- **La ground truth de relaciones es incompleta.** Se estima que el filtro dejó fuera más relaciones de las que conservó (26,3 [12,2; 55,4] frente a 18), y no se puede afirmar que la pérdida sea pareja entre sitios ni acotarla en ES. El *recall* de 0,407 con su intervalo se cita donde aparezcan resultados de relaciones.
- **Experimento A (ADR 0016).** Un enlace de la máquina sobre un par fuera de los candidatos cuenta como falso positivo, así que la precision de existencia se subestima, y las relaciones de la referencia perdidas por el filtro no están en el denominador, así que el *recall* de existencia se sobrestima. Por eso se informa la precision también sin los falsos positivos sin par candidato (decisión 4) y el *recall* de existencia se lee como cota superior. Esto afecta también la lectura de H3 solo en la medida en que depende de enlaces detectados; las exactitudes de tipo y dirección no cambian.
- **C3 y el banco (ADR 0013).** C3 solo puede aportar los enlaces `Related` que existen en la referencia; ningún código marca una decisión como vigente. C3 y un banco redactado solo desde las relaciones anotadas comparten el mismo punto ciego. Para E3/H4, `superseded_answer` lo escribe una persona y no depende mecánicamente de la referencia, pero un E3 redactado solo desde relaciones anotadas heredaría la pérdida (decisión 5).
- **No cambia ninguna anotación ya hecha, adjudicación, umbral ni criterio de éxito.** No se generan pares nuevos ni se agrega trabajo para `gm` o `gv` por esta decisión.
- **Se actualizan** el avance 08 (§4.2 y decisión abierta D, que queda resuelta; versión 8.3), el avance 09 (fila 11 de la sección 11; versión 12.2) y la prosa de cierre de los notebooks 18 y 25. Cambian además `src/afg/experiments/relations_summary.py` y `tests/test_relations_summary.py`.
