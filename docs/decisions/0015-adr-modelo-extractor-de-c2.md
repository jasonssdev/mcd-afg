# 0015. El modelo de extracción de C2 y C3 es `qwen3:8b`, el de OpenKOS, con la pasada de decisiones activada

## Estado

Aceptada (2026-11-01). Resuelve los cuatro puntos abiertos del [issue #143](https://github.com/jasonssdev/mcd-afg/issues/143): el alcance de la regla del «mismo modelo generativo» (tesis, sección 5.3), el modelo de extracción de C2 y C3, el modelo de respuesta común y la independencia del juez. No reemplaza ninguna decisión anterior; completa el [ADR 0014](0014-adr-c1-como-rag-convencional.md) («OpenKOS tal como se distribuye») y el [ADR 0006](0006-adr-c1-rag-separado-con-respuesta-de-openkos.md) (enmienda del 2026-11-01 sobre la suficiencia).

## Contexto

La tesis necesita fijar, antes de cualquier evaluación, qué modelo construye la base compilada de C2 (y la parte de C3 que no viene de la anotación humana). El issue #143 dejó cuatro puntos abiertos, que dependían de las mediciones que OpenKOS hacía en su épica jasonssdev/openkos#1556:

1. Si la regla del «mismo modelo generativo» se aplica solo al modelo que responde o también al que extrae.
2. Qué modelo extrae en C2 y C3.
3. Qué modelo responde en común a C1, C2 y C3.
4. Que el juez siga siendo de una familia distinta de la del modelo generativo.

La evidencia ya está completa. El *screen* prerregistrado de cuatro modelos sobre el pase de decisiones ([notebook 15](../../notebooks/15-jss-screen-de-modelos-openkos.ipynb)) mostró que `qwen3.6:27b` supera a `qwen3:8b` en F1 con 15 corridas nuevas por modelo (+0,181 en ES2015 y +0,172 en TS3009), a cambio de 1,8 a 3,6 veces el tiempo; `qwen3.6:35b-a3b`, más rápido, no pasó la regla registrada con 15 corridas (jasonssdev/openkos#1561). Del lado de OpenKOS, la épica #1556 se cerró dejando **todas las tareas en `qwen3:8b`**, salvo los jueces internos y la verificación de suficiencia (`gemma4:26b-a4b`): el modelo de extracción de conceptos no tuvo ganador (#1557; `qwen3.6:27b` no mejoró la cobertura de conceptos de forma separable de cero y no alcanzó el piso de precisión G1, [notebook 21](../../notebooks/21-jss-extraccion-de-conceptos-openkos.ipynb), sección 2.3), tampoco el tamaño de ventana (#1558) ni el modelo de respuesta (#1560).

Todas las cifras son de series de desarrollo ([ADR 0005](0005-adr-development-evaluation-split.md)).

## Decisión

1. **El modelo de extracción de C2 y C3 es `qwen3:8b`**, el modelo por defecto de OpenKOS 0.7.0 (clave `model:` de su `openkos.yaml`), sin cambiarlo. Es coherente con el ADR 0014: C2 y C3 usan OpenKOS tal como se distribuye, sin cambios en su código, sus *prompts* ni sus modelos.
2. **La pasada de decisiones queda activada (`transcript_decisions: true`).** Es una opción documentada de OpenKOS, pensada para transcripciones de reuniones; su propia plantilla de configuración la describe así: «Measured on meeting transcripts: about 3x the decisions recalled at high precision, yet short of the bar for turning it on by default». Es la **única opción de C2 que no está en su valor por defecto**, y se declara como tal. «Tal como se distribuye» significa que no se modifican el código, los *prompts* ni los modelos de OpenKOS; elegir una opción documentada que corresponde al dominio de la tesis (reuniones, cuya unidad de interés es la decisión) forma parte de usar el producto.
3. **Puntos ya resueltos, que se registran aquí para cerrar el issue.** La regla del «mismo modelo generativo» (sección 5.3) se aplica al **modelo que responde**: `qwen3:8b` en C1, C2 y C3 (ADR 0014); el modelo de extracción es una pieza distinta que, por esta decisión, resulta ser el mismo. El juez `gpt-oss:20b` sigue siendo de otra familia que el modelo generativo (`must_differ_from_generative_model`). La verificación de suficiencia de C2 y C3 usa `gemma4:26b-a4b`, el modelo que empaqueta OpenKOS (enmienda del ADR 0006).

## Alternativas descartadas

- **`qwen3.6:27b` como extractor.** Gana en F1 del pase de decisiones (+0,181 en ES2015 y +0,172 en TS3009 con n = 15, notebook 15), pero no alcanzó el piso de precisión de la extracción de conceptos (#1557), tarda de 1,8 a 3,6 veces más por corrida y no es el modelo por defecto de OpenKOS: usarlo sería una modificación del producto evaluado, contraria al ADR 0014. La ganancia, además, sale de dos series de desarrollo y de un puntaje con parecido temático.
- **`qwen3.6:35b-a3b` como extractor.** Es más rápido que el 27b, pero no pasó la regla registrada con 15 corridas (jasonssdev/openkos#1561: margen de F1 de +0,164 frente a 0,192 exigido en ES2015, y +0,070 frente a 0,165 en TS3009).
- **Desactivar la pasada de decisiones.** Deja a C2 en el valor por defecto, pero debilita a propósito la extracción de las decisiones, que es lo que mide OE2 y de lo que depende C2 en E3, y obligaría a rehacer las corridas de desarrollo ya hechas. Se descarta.

## Consecuencias

- **La escala del modelo queda como extensión opcional (H3):** `generative_model_large = "qwen3:32b"` en `config/experiments.toml` sigue siendo el segundo punto de escala, sin corrida comprometida.
- **No hay nada que rehacer.** Las corridas de desarrollo actuales de C2 ya usan esta configuración (`qwen3:8b` con la pasada de decisiones activada).
- **`config/experiments.toml` no cambia de valores.** Solo se actualiza el comentario de `generative_model`, que ahora dice que es el modelo de respuesta y de extracción.
- **Limitación declarada.** La pasada de decisiones es una desviación del valor por defecto de OpenKOS y debe mencionarse en toda descripción de C2. La elección del extractor se apoya en el *screen* de dos series de desarrollo; no se probó en las series de evaluación y no se vuelve a ajustar con ellas.
- **Lo que queda antes de evaluar** es congelar modelos, versiones y código en un registro de congelamiento y evaluar una sola vez ([ADR 0005](0005-adr-development-evaluation-split.md)).
