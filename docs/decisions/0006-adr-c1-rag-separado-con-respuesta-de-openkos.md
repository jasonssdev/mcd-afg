# 0006. C1 se construye en este proyecto, separado de OpenKOS, y responde con los prompts de respuesta de OpenKOS copiados byte a byte

## Estado

Aceptada (2026-10-07)

## Contexto

La sección 5.3 de la tesis exige que C1, C2 y C3 compartan el mismo modelo generativo, el
mismo modelo de *embeddings*, el mismo hardware y el mismo presupuesto de contexto, de modo que
lo único que varíe sea la representación consultada. También exige que C1 sea una línea base
**honesta**: parámetros de fragmentación y número de fragmentos recuperados ajustados sobre el
conjunto de desarrollo.

Un RAG tiene dos pasos: recuperar material y generar la respuesta con un *prompt* que contiene
la pregunta y ese material. C2 y C3 responden a través de `openkos query`, que hace dos
llamadas al modelo (verificado sobre el checkout local de OpenKOS, `v0.5.2-10-g4ac8b607`):

1. `src/openkos/prompts/answer/sufficiency.md` decide si el contexto alcanza para responder; si
   no, el sistema se abstiene.
2. `src/openkos/prompts/answer/system.md` redacta la respuesta solo desde el contexto numerado
   y cierra con una línea `USED:` que declara qué bloques usó.

Al responder, OpenKOS usa solo `qwen3:8b` (generación) y `bge-m3` (*embeddings*). Los demás
modelos que declara, como el juez `gemma4:26b-a4b`, intervienen solo al compilar y por lo tanto
solo afectan a C2, que es justo lo que la tesis mide. Por defecto deja `temperature` y `seed`
sin fijar.

Se consideraron tres caminos para C1:

- **C1 dentro de OpenKOS**, como un espacio de trabajo solo con las transcripciones. Igualaba
  todo por construcción, pero mezcla la línea base con el instrumento que se evalúa, y su
  tamaño de fragmento está fijo en el código, de modo que no se podía ajustar como exige §5.3.
- **Un responder común en este proyecto** para las tres condiciones, usando OpenKOS solo para
  recuperar. Igualaba la instrucción por construcción, pero dejaba de evaluar OpenKOS tal
  como responde.
- **C1 propio que copia los prompts de respuesta de OpenKOS.** Es la opción elegida.

## Decisión

1. **C1 vive completo en este proyecto** (`src/afg/conditions/c1_document_rag.py`):
   fragmentación de las transcripciones congeladas, recuperación híbrida léxica + densa con
   `bge-m3`, y ajuste de tamaño de fragmento y número de fragmentos sobre las series de
   desarrollo. No importa ni ejecuta OpenKOS.
2. **C2 y C3 responden con `openkos query`, sin modificar.** Se evalúa OpenKOS tal como
   responde.
3. **C1 genera la respuesta con una copia byte a byte de `sufficiency.md` y `system.md`**,
   con el mismo orden de llamadas, la misma numeración de bloques (`[n] `), el mismo marco
   `CONTEXT:` / `QUESTION:`, el mismo procesamiento de la línea `USED:`, el mismo modelo y
   los mismos límites de tokens. La copia se fija con el SHA-256 de cada archivo y una prueba
   lo verifica.
4. **El texto de los prompts no se adapta.** Habla de *concepts* y de *compiled bundle*, que
   no describe fragmentos de transcripción; se copia igual y se declara como limitación.
   Cualquier ajuste reabriría la duda de que la diferencia entre condiciones venga de la
   instrucción y no de la representación.
5. **OpenKOS se fija a una versión exacta publicada, `openkos==0.5.3`**, que incluye los
   cambios de recuperación posteriores a `v0.5.2`. No se usa un rango (`>=`).
6. **`openkos query --json`** se agrega en OpenKOS como prerrequisito: devuelve la respuesta,
   **todos** los bloques enviados al modelo con su texto exacto, lo recuperado antes de armar
   el contexto, las citas y los parámetros usados. OE4 lo necesita para distinguir un error
   de recuperación de uno de síntesis; hoy ni la CLI ni el servidor MCP exponen el conjunto
   completo. Este proyecto se comunica con OpenKOS solo por la CLI, nunca importando sus
   módulos internos, que no tienen API estable.
7. **Temperatura y semilla se fijan explícitamente** en las tres condiciones, en
   `config/experiments.toml` y en el `openkos.yaml` de cada espacio de trabajo.

## Consecuencias

- Las tres condiciones comparten modelos, prompts de respuesta, presupuesto de contexto,
  temperatura y semilla. Lo que varía es qué se recupera y de dónde, que es lo que §5.3 pide.
- C1 sigue siendo ajustable, como exige una línea base honesta, sin tocar el instrumento.
- El experimento depende de un cambio en OpenKOS (`query --json`) y de su publicación como
  0.5.3. Mientras no exista, C2 y C3 no pueden registrar lo recuperado y OE4 queda bloqueado.
- Si OpenKOS cambia sus prompts de respuesta en una versión posterior, la copia de C1 no se
  actualiza sola: el SHA-256 fijado lo detecta y la prueba falla.
- Los valores de `config/experiments.toml` que hoy difieren de los de OpenKOS
  (`context_window_tokens`, `top_k`) se alinean en la implementación; la fila **D13** del
  índice registra esta decisión.
- Complementa el [ADR 0003](0003-adr-openkos-as-instrument.md): OpenKOS sigue siendo el
  instrumento, y C1 queda explícitamente fuera de él.
