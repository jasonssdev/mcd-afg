# 0026. Extensión del Experimento A: la extracción de C2 con seis modelos de pago

## Estado

Aceptada (2026-11-26), por decisión de `jss`. Prerregistra una **extensión descriptiva** del Experimento A. Se escribe antes de que exista cualquier corrida con estos modelos. No reemplaza ninguna decisión anterior y no toca la corrida formal `experimento-a-formal` ni el registro de congelamiento (`config/freeze.json`). Responde al trabajo futuro n.º 1 y al límite «diseño y modelo confundidos» del [avance 13](../avances/13-jss-conclusiones.md) (secciones 7 y 8).

## Contexto

La corrida formal del Experimento A dejó a la extracción automática como el eslabón débil de C2:

- Encuentra el 30,8 % de las decisiones de la referencia (*recall* 0,308 [0,247; 0,373] con τ = 0,70; [avance 11](../avances/11-jss-resultados-experimento-a.md)).
- Es la causa más frecuente de las respuestas incorrectas de C2 (21 de 43, 48,8 %; OE4, avance 13).

Esa corrida usa un solo modelo local pequeño, `qwen3:8b` ([ADR 0015](0015-adr-modelo-extractor-de-c2.md)). Por eso no se puede saber si la debilidad viene del diseño de la extracción de OpenKOS o de la capacidad del modelo.

OpenKOS 0.7.2 (2026-11-25) hace usable su *backend* `openai-compatible` con OpenAI, Anthropic y Google. Agrega reintentos ante fallas transitorias, `max_completion_tokens` y la clave `reasoning_effort`. Según su registro de cambios, nada cambia para un espacio de trabajo local. Eso permite repetir la extracción con modelos de pago y dejar fijo todo lo demás.

## Decisión

1. **Qué se mide.** Solo la extracción de decisiones de C2, con las métricas del Experimento A:
   - **Principal:** *recall* agrupado sobre `origin_meetings` con τ = 0,70.
   - **Secundarias:** *precision* y F1 con τ = 0,70, y las tres métricas con τ = 0,75 y 0,80 como sensibilidad.
   - **Lo que no se mide:** respuestas, juez ni Experimento B. La pregunta es si un modelo más capaz extrae más decisiones, no si C2 responde mejor.
2. **Línea base.** La corrida formal `experimento-a-formal` (`qwen3:8b`, OpenKOS 0.7.0) tal como está publicada. No se vuelve a correr.
3. **Modelos.** Dos por laboratorio, uno pequeño y uno grande, con los identificadores que sirve cada API:

   | Laboratorio | Pequeño | Grande |
   |---|---|---|
   | OpenAI | `gpt-5-mini` | `gpt-6-luna` |
   | Anthropic | `claude-haiku-5-5` | `claude-sonnet-5-5` |
   | Google | `gemini-3.8-flash` | `gemini-4-argon` |

   Se eligen porque OpenKOS 0.7.2 documenta que `gpt-5-mini`, `gpt-6-luna`, `claude-haiku-5-5` y `gemini-3.8-flash` completan un `ingest`. `claude-sonnet-5-5` y `gemini-4-argon` son los modelos grandes vigentes de esos laboratorios. La lista vive en `config/hosted_extraction.toml`. Si un identificador ya no existe al correr, se reemplaza por el sucesor del mismo nivel y se deja escrito en el manifiesto y en el notebook de resultados.
4. **Qué queda fijo.** Las once series de evaluación, tres repeticiones por modelo (`runs_per_config`), las mismas transcripciones y fechas de reunión, la pasada de decisiones activada (`transcript_decisions: true`), `max_generation_tokens = 8192` y `evidence_quote` apagado, como en la línea base. Los *embeddings* siguen siendo `bge-m3` en el Ollama local (`embedding_base_url`). La puntuación y la referencia son las de la corrida formal: la misma alineación, τ y el *bootstrap* por reunión (ADR 0011).
5. **Qué cambia, además del modelo.**
   - **Versión de OpenKOS.** Es 0.7.2, instalada aparte de la 0.7.0 del entorno congelado.
   - **`reasoning_effort = "low"`.** Se usa en los seis modelos por igual, porque Gemini no termina un `ingest` sin él. El ajuste se aplica a todos para no tratar distinto a un laboratorio.
   - **`temperature` y `seed`.** No se envían a los modelos de pago, porque los proveedores los rechazan o los ignoran. Las tres repeticiones miden esa variabilidad.
6. **Puente de continuidad.** Antes de comparar se corre `qwen3:8b` con OpenKOS 0.7.2 en el Ollama local (*backend* `ollama`, la misma configuración de la línea base). Se corre una serie de evaluación (ES2002) con una repetición. Si sus cifras quedan dentro del rango de las tres repeticiones formales de esa serie, se acepta que el cambio de versión no explica las diferencias. Si quedan fuera, el notebook lo declara y la comparación pierde fuerza.
7. **Regla de mejora, fijada antes de ver datos.** Para cada modelo se calcula la diferencia frente a la línea base (modelo − `qwen3:8b`):
   - **Cómo se calcula:** con un *bootstrap* pareado por reunión. En cada remuestreo se toman las mismas reuniones para los dos sistemas. Cada reunión aporta sus conteos promediados sobre las tres repeticiones. Se usan 10.000 remuestreos con semilla 42.
   - **Corrección por multiplicidad:** los intervalos se corrigen con Bonferroni por los seis modelos (nivel 1 − 0,05/6).
   - **Cuándo se dice que un modelo mejora la extracción:** el intervalo de la diferencia de *recall* queda entero sobre 0 y el límite inferior de la diferencia de *precision* no baja de −0,05.
   - **Empate y empeora:** si el intervalo de *recall* contiene el 0, se informa como «sin diferencia demostrada». Si queda entero bajo 0, se informa como «empeora».
8. **Indicadores secundarios de operación, también fijados antes de ver datos.** Responden a si los modelos de pago son más rápidos o más confiables, además de si extraen mejor.
   - **Tiempo de extracción por reunión:** la suma de `duration_s` de los `ingest` de cada reunión, registrada en el manifiesto de cada corrida (la línea base ya la tiene). Se informa la mediana por modelo y la razón de tiempos frente a `qwen3:8b`, con un intervalo *bootstrap* pareado por reunión sobre el logaritmo de la razón (mismo nivel Bonferroni). Un modelo es «más rápido» si el intervalo de la razón queda entero bajo 1, y «más lento» si queda entero sobre 1.
   - **Extracciones completas:** la proporción de reuniones cuyo `ingest` terminó con extracción, es decir, sin quedarse solo con la fuente.
   - **Decisiones extraídas por reunión:** se informan de forma descriptiva y ayudan a leer la *precision*.
   - **Costo en dólares por modelo:** se toma del panel de cada proveedor después de la corrida y se registra en el manifiesto de la comparación. Es descriptivo.
   - **Lectura del tiempo:** la línea base corre en un equipo local (Apple M4 Pro, 48 GB) y los modelos de pago en la infraestructura del proveedor. La razón de tiempos mide la experiencia de uso de cada opción, no la eficiencia del modelo.
9. **Carácter descriptivo.** Las series de evaluación ya se usaron en la corrida formal y quien mantiene el repositorio ya vio sus cifras. Por eso la extensión es descriptiva y no confirma hipótesis de la tesis. Sus informes se escriben con `--descriptive` (`informe-descriptivo.json`) y nunca reemplazan a `informe.json` de la corrida formal.

## Enmienda (2026-11-26, después del puente y antes de cualquier corrida con modelos de pago)

### Resultado del puente

El puente (decisión 6) quedó **fuera** del rango de las tres corridas formales de ES2002, del lado favorable. Se midió con τ = 0,70 y una sola corrida:

| Métrica | Puente | Rango formal |
|---|---|---|
| *precision* | 0,212 | 0,185–0,200 |
| *recall* | 0,355 | 0,323–0,355 |
| F1 | 0,265 | 0,235–0,256 |

La diferencia equivale a pocas decisiones, y el rango de solo tres corridas es estrecho. Aun así, con la regla fijada no se puede descartar un efecto de la versión de OpenKOS.

El tiempo del puente no es comparable. Mientras corría, el mismo equipo ejecutaba las pruebas del proyecto.

### Decisión

Se agrega una **segunda línea base**: `qwen3:8b` con OpenKOS 0.7.2, con la misma configuración del puente. Cubre las once series de evaluación con tres repeticiones (`experimento-a-base-0-7-2`). Tiene tres usos:

- Cada modelo de pago se compara contra las dos líneas base, con la misma regla de la decisión 7 y los mismos indicadores de la decisión 8.
- La línea base formal sigue siendo la principal. Si las dos comparaciones dan veredictos distintos, se informan ambos y la conclusión se apoya en la de la misma versión (0.7.2), porque solo esa aísla el modelo.
- La comparación de la segunda línea base contra la formal se informa como «efecto de versión». No cuenta en el Bonferroni de los seis modelos.

Esta enmienda se decide después de ver el puente (una serie, una repetición) y se declara como tal. No se vio ninguna cifra de modelos de pago.

## Segunda enmienda (2026-11-26, antes de cualquier corrida con modelos de pago)

### Contexto

OpenKOS 0.7.3 (2026-11-26) agrega dos cosas que esta extensión necesita:

- **Tokens por reunión.** Cada `ingest` imprime una línea `tokens:` con el número de llamadas al modelo y los tokens de entrada (*prompt*), de salida (*completion*) y el total. El total es el que informa el proveedor, así que incluye el razonamiento oculto que algunos modelos cobran y que no aparece en la salida. La línea cuenta también las llamadas de un `ingest` que falló o que se cortó por el límite de salida, porque esas llamadas se cobran igual.
- **Estado de la extracción.** Cuando un `ingest` no produce ningún objeto derivado, la fuente lleva en su encabezado la clave `extraction_status`. Puede tomar uno de cuatro valores: `failed`, `no-concepts-found`, `no-extractable-text` o `blocked-by-sensitivity`. El código de OpenKOS 0.7.3 muestra que un `ingest` cuya extracción falla termina con código de salida 0 y deja escrita la fuente. Por eso el código de salida no basta para saber si una reunión tiene extracción.

En el momento de esta enmienda, la segunda línea base `experimento-a-base-0-7-2` está incompleta: tiene 16 de los 33 pares serie × repetición. Ninguna fuente de la corrida formal, del puente ni de esos 16 pares tiene `extraction_status`, así que sus cifras de completitud no cambian con la nueva definición.

### Decisión

1. **Versión.** Los seis modelos de pago se corren con OpenKOS 0.7.3, instalado aparte del entorno congelado igual que antes. El pin 0.7.0 del entorno congelado y la corrida formal no cambian.
2. **Línea base de la misma versión.** La segunda línea base pasa a ser `experimento-a-base-0-7-3`: `qwen3:8b` con OpenKOS 0.7.3 en el Ollama local, con la configuración del puente y las once series de evaluación con tres repeticiones. Cumple los tres usos de la primera enmienda, incluido el de decidir cuando las dos comparaciones dan veredictos distintos. La comparación de esta línea base contra la formal se informa como «efecto de versión» y no cuenta en el Bonferroni.
3. **Lo que queda de 0.7.2.** El puente y los 16 pares de `experimento-a-base-0-7-2` se conservan como evidencia y se mencionan en el notebook. No entran en ningún veredicto. La corrida 0.7.2 no se completa.
4. **Reunión con extracción (decisión 8).** Una reunión cuenta como extraída si su `ingest` terminó con código 0 y su fuente en `bundle/sources/` no tiene la clave `extraction_status`. Se informa por separado cuántas reuniones quedaron con cada uno de los cuatro valores. Para *precision* y *recall*, una reunión sin extracción aporta cero decisiones, como ya se hacía con las corridas fallidas. No se reintenta ninguna reunión fuera de los reintentos que OpenKOS hace por su cuenta.
5. **Costo (decisión 8).** El costo se calcula con los tokens en vez de leerse en el panel de cada proveedor:
   - **Qué se registra:** por reunión, las llamadas, las llamadas que informaron tokens y los tokens de entrada, salida y total.
   - **Fórmula:** costo = entrada × precio de entrada + (total − entrada) × precio de salida. Así se cobra como salida el razonamiento oculto que el total incluye y la salida no.
   - **Precios:** se fijan en `config/hosted_extraction.toml` por modelo, en dólares por millón de tokens, con la fecha y la página de precios de cada proveedor. Se fijan antes del piloto.
   - **Carácter:** sigue siendo un indicador descriptivo. Si alguna llamada no informó tokens, el costo de esa reunión se informa como cota inferior. El panel del proveedor puede usarse como control, pero no reemplaza al cálculo.
6. **Lo que no cambia.** `evidence_quote` sigue apagado en los seis modelos, aunque OpenKOS lo recomiende para algunos, por la razón de la alternativa descartada. `reasoning_effort = "low"`, las métricas, la regla de mejora, los indicadores de tiempo y el carácter descriptivo de la extensión siguen igual.

Esta enmienda se decide antes de cualquier corrida con modelos de pago. No se vio ninguna cifra de esos modelos.

## Tercera enmienda (2026-11-26, antes de cualquier corrida con modelos de pago)

### Contexto

Con la extracción sola, la extensión responde si un modelo más capaz encuentra más decisiones que `qwen3:8b`. No responde la pregunta que importa para la tesis: si C2, con un extractor mejor, responde tan bien como C1 o mejor. Esa es la comparación del criterio D16 (diferencia pareada C2 − C1 en E3, [ADR 0010](0010-adr-decisiones-del-analisis-del-experimento-b.md)). Además, `qwen3:8b` no sirve de referencia para las respuestas: C2 formal ya quedó por debajo de C1, así que superarlo no basta para decir que el sistema funciona.

La alternativa «Medir C2 completo (respuestas + juez)» se había descartado por costo. Esa razón no se sostiene: el costo de proveedor está solo en la extracción. Las respuestas y el juez corren en el equipo local, con los modelos de la corrida formal.

### Decisión

1. **Se agrega la medición de respuestas.** Para cada modelo de pago se corre el Experimento B solo con C2 sobre los workspaces de su corrida completa (11 series × 3 repeticiones). Todo lo demás queda igual que en la corrida formal:
   - el banco congelado de 99 preguntas;
   - las semillas 42, 43 y 44;
   - el generador `qwen3:8b` y el modelo de suficiencia `gemma4:26b-a4b`, ambos locales;
   - el juez `gpt-oss:20b`.

   Cada workspace se **deriva** sin tocar el original: se cambia solo la configuración de consulta, para que la respuesta salga del Ollama local y no del modelo de pago. Los objetos extraídos no cambian. Así, lo único que varía frente a C2 formal es el extractor.
2. **Comparación principal: frente a C1, el control.** Para cada modelo se calcula la diferencia pareada «C2 con ese extractor − C1 formal» en la corrección de E3, con el mismo *bootstrap* del criterio D16 y Bonferroni por los seis modelos (nivel 1 − 0,05/6). Se informa así:
   - **«Supera a C1»:** el intervalo queda entero sobre 0.
   - **«No se distingue de C1»:** el intervalo contiene el 0.
   - **«Queda bajo C1»:** el intervalo queda entero bajo 0.

   C1 no se vuelve a correr, porque no depende del extractor: se usa la corrida formal.
3. **Comparaciones secundarias.**
   - **Por estrato y en total:** corrección, abstención, `evidence_supported`, `citation_correct`, `outdated_among_answered` (H4) y `answer_seconds`.
   - **Frente a C2 formal:** la misma diferencia pareada, para saber cuánto mejora la respuesta con el extractor.
   - **Frente a la línea base de la misma versión:** también se corre el Experimento B de C2 sobre `experimento-a-base-0-7-3`. Así, una mejora puede atribuirse al modelo y no a la versión de OpenKOS.
4. **El chequeo de suficiencia sigue activo,** como en la corrida formal. Su variante relajada es un análisis aparte, con su propia decisión (#336).
5. **La extracción sigue midiéndose,** con las métricas y las reglas de las decisiones 1 a 8, ahora como resultado secundario. La decisión 1 se modifica solo en su punto «Lo que no se mide»: las respuestas y el juez pasan a medirse. El Experimento B completo, con C0 y C3, sigue fuera.
6. **Carácter descriptivo.** Las cifras de C1 y C2 formales ya se vieron en el preinforme. Por eso la comparación frente a C1 es descriptiva y no reemplaza al criterio D16 de la corrida formal.
7. **Costo y calendario.** Esta medición no tiene costo de proveedor. Corre en el equipo local después de las extracciones, sin superponerse con otra corrida local.

Esta enmienda se decide antes de cualquier corrida con modelos de pago. No se vio ninguna cifra de esos modelos.

## Alternativas descartadas

- **Medir C2 completo (respuestas + juez).** Multiplica el costo y mezcla la extracción con la recuperación y la síntesis. La pregunta del avance 13 es sobre la extracción. *(Revertida por la tercera enmienda: el costo de proveedor está solo en la extracción, y la mezcla se controla dejando fijos la recuperación, el generador y el juez.)*
- **Usar las series de desarrollo.** Son solo tres, y la línea base formal no las cubre. La comparación con la corrida publicada se perdería.
- **Subir el pin del entorno congelado a 0.7.2.** Rompería la verificación de la corrida formal contra `config/freeze.json`. Instalar 0.7.2 aparte deja intacta la corrida formal.
- **Activar `evidence_quote` en los modelos donde OpenKOS lo midió como beneficioso.** Afecta la evidencia de los conceptos, no la pasada de decisiones. Activarlo según el modelo agregaría una segunda variable.
- **Una sola repetición por modelo.** Sin `seed` y `temperature` fijos, una repetición no permite separar el modelo del azar.

## Consecuencias

- **Datos a terceros.** Las transcripciones de AMI (CC BY 4.0, sin datos personales sensibles) se envían a OpenAI, Anthropic y Google. Es la primera vez que el proyecto lo hace. Debe mencionarse en el avance de resultados de esta extensión y en el [avance 05](../avances/05-jss-aspectos-eticos.md) cuando se actualice.
- **Costo.** Son 6 modelos × 11 series × 3 repeticiones = 198 extracciones de cuatro reuniones cada una. Antes de la corrida completa se hace una corrida piloto de una serie y una repetición por modelo. El piloto mide el tiempo y el costo y detecta identificadores o parámetros rechazados.
- **Claves.** Cada proveedor se corre con su propia clave en `OPENKOS_OPENAI_API_KEY`, nunca en un archivo del repositorio. El código verifica que la clave exista antes de cualquier llamada.
- **Instrumento y entregables.** El código vive en `src/afg/` con tests: la configuración del proveedor, el comando de la corrida y la comparación pareada. Las cifras se muestran en un notebook de resultados. El avance que informe la extensión se escribe después del notebook.
- **Límites que se declaran desde ya.** Hay tres:
  - El resultado vale para estos seis modelos, en esta fecha y con `reasoning_effort = "low"`.
  - Los modelos de pago cambian sin aviso detrás del mismo identificador.
  - La extensión es descriptiva sobre series ya vistas.
