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

## Alternativas descartadas

- **Medir C2 completo (respuestas + juez).** Multiplica el costo y mezcla la extracción con la recuperación y la síntesis. La pregunta del avance 13 es sobre la extracción.
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
