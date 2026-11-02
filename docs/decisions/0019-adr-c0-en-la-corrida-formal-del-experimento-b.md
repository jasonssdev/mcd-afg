# 0019. C0 (respuesta sin recuperación) entra en la corrida formal del Experimento B como referencia descriptiva

## Estado

Aceptada (2026-11-02), por decisión del autor del proyecto. Resuelve el [issue #252](https://github.com/jasonssdev/mcd-afg/issues/252). Complementa, sin reemplazar, al [ADR 0014](0014-adr-c1-como-rag-convencional.md) (que define a C1 y lo que comparten las condiciones) y al [ADR 0005](0005-adr-development-evaluation-split.md) (partición de desarrollo y evaluación). Ninguna decisión anterior sobre las hipótesis cambia. Las reglas de lectura se fijan **antes de que exista cualquier resultado sobre series de evaluación**.

## Contexto

La propuesta (§5.3) define tres condiciones: C1, C2 y C3. Ningún ADR define a C0. Nació como diagnóstico de desarrollo: el mismo generador de C1 respondiendo sin ningún texto de apoyo, limitado a ES2015 y fuera de la corrida formal (`afg experiment b-closed-book`; `afg experiment b` lo rechazaba). Sirvió para dos cosas: tener la línea base más simple posible y observar cuánto del escenario AMI parece conocer el modelo (documento 09, §8.3).

El autor del proyecto decidió el 2026-11-02 que C0 entre en la corrida formal. La razón es de interpretación: la diferencia entre C1 y C2 dice cuánto vale el sistema compilado frente a un RAG convencional, pero no dice cuánto del rendimiento de ambos viene de recuperar algo y cuánto de lo que el modelo ya sabe. Una referencia sin recuperación, medida con el mismo banco, juez y semillas, deja esa lectura a la vista. El documento 09 (§8.2) ya lee así los resultados de desarrollo: sin contexto el modelo acierta 22,2 %, con la recuperación de C1 sube a 81,0 % y con la base compilada de C2 queda en 71,4 %.

## Decisión

1. **`afg experiment b --conditions` acepta `c0`** junto a `c1`, `c2` y `c3`, con el mismo banco de preguntas, generador (`qwen3:8b`), juez, semillas (`seed + r`), formato de registro, bloqueo de congelamiento y comprobación del entorno fijado (`[pinned_environment]`). Las series de evaluación siguen bloqueadas sin el registro de congelamiento. C0 no necesita `--c2-extraction`. La comprobación de modelos instalados pide el modelo de suficiencia solo si se pide `c2` o `c3`.
2. **`afg experiment b-closed-book` se conserva como atajo de desarrollo**, no como segunda vía formal. Corre solo sobre series de desarrollo (ADR 0005), sin pedir OpenKOS ni el modelo de suficiencia, y escribe el mismo formato. Se conserva porque es la corrida rápida que alimenta los notebooks y los avances (la carpeta `diagnostico-sin-contexto-es2015` es de ese comando) y porque su guarda de series es una protección adicional. Dos rutas hacia el mismo código no producen resultados distintos: ambas llaman al mismo `run_experiment_b` con la misma condición.
3. **C0 no es una cuarta condición de la comparación principal.** El criterio D16 (C2 frente a C1 en E3) y las reglas de H1 a H4 no cambian.
4. **Qué se informa de C0** (`b-report`, `final-tables`): corrección por estrato, abstención en E4 (corrección del rechazo) y las tasas de H4 (respuestas desactualizadas entre las respondidas, con la cota superior de incorrectas) en E3, cada una con su intervalo bootstrap por pregunta. **No se informan para C0** el soporte de evidencia, la citación correcta, su precisión ni la anchura de las citas: C0 no recupera ni cita, no hay evidencia recuperada que el juez pueda contrastar y el campo de citación del registro queda en falso o cero sin significado. Esas celdas salen como no disponibles, nunca como cero.
5. **Dos comparaciones descriptivas**, apareadas por pregunta, sobre la corrección y en cada estrato más el total, con el mismo bootstrap y el mismo intervalo del resto del análisis:
   - **C1 − C0**: el valor de recuperar texto (documento 09, §8.2: «recuperar texto aporta mucho»).
   - **C2 − C0**: el valor de la base compilada frente a no recuperar nada.

   Quedan marcadas como `descriptive` en `analisis.json`, en la tabla pareada de `final-tables` y en `b-report` («Secundaria descriptiva»). No deciden D16 ni H1 a H4. No se agrega C3 − C0 ni una comparación de H4 que involucre a C0: ningún documento las motiva (la distancia C1 → C3 y la C3 → C2 ya tienen su lectura en los ADR 0014 y 0018).
6. **Lectura de C0.** Que C0 acierte una pregunta no prueba conocimiento previo del corpus ni lo descarta (documento 09, §8.3). Además, el juez acepta como correcta una respuesta que admite no saber cuando la pregunta no tiene respuesta (E4): ahí C0 no mide abstención en sentido estricto, y la tasa de E4 de C0 se lee con esa advertencia.

## Alternativas descartadas

- **Mantener C0 solo como diagnóstico de desarrollo.** Deja sin medir, sobre las series de evaluación, cuánto aporta recuperar; la lectura quedaría apoyada en 21 preguntas de calibración.
- **Reemplazar `b-closed-book` por `b --conditions c0`.** Elimina un comando, pero también la guarda que impide correr C0 por error sobre evaluación y la corrida rápida sin OpenKOS ni modelo de suficiencia.
- **Incluir a C0 en el criterio principal o en H4 como pareja de C1.** Cambiaría hipótesis preregistradas sin que ningún documento lo pida; se descarta.
- **Informar métricas de citación de C0 como cero.** Un cero ahí no mide nada y se leería como una falla de citar.

## Consecuencias

- **Costo.** La corrida formal pasa de al menos unas 900 a unas 1.200 respuestas (100 preguntas × 4 condiciones × 3 corridas), todas juzgadas por el juez; C0 es la condición más barata de generar (una llamada, sin recuperación).
- **Los avances 06, 08 y 09 se actualizan** (versiones 10.0, 8.0 y 12.0): decían que C0 se usaba solo en desarrollo.
- **No cambia ninguna anotación, adjudicación, banco de preguntas ni calibración del juez.** El registro de congelamiento (#237) deberá cerrarse con este código; el bloqueo de las series de evaluación se mantiene.
- Cambian `src/afg/cli.py` (`b`, `b-report`), `src/afg/conditions/c0_closed_book.py`, `src/afg/experiments/analysis.py` y `src/afg/experiments/final_tables.py`. La propuesta (§5.3) sigue describiendo tres condiciones: C0 se declara aquí y en los avances como referencia, no como condición de la comparación principal.
