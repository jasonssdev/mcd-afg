# notebooks/

Los notebooks son el **registro académico paso a paso** del proyecto: lo que se hizo, lo que
se midió y, sobre todo, **por qué se decidió lo que se decidió**. Están escritos para que un
revisor de la universidad pueda seguir el razonamiento sin leer el código fuente.

> Idioma: estos notebooks van en **español**, porque sus lectores son el equipo y los
> revisores de una tesis en español. La regla completa de idioma por tipo de artefacto está en
> [`CONTRIBUTING.md` §7.4](../CONTRIBUTING.md#74-idioma): en resumen, todo lo que lee una
> persona (README, CONTRIBUTING, `docs/` completo, notebooks) va en español; solo el código,
> los identificadores y los comentarios de `config/` van en inglés.

## Convención de nombres

```
NN-{autor}-{nombre}.ipynb
```

- `NN` — dos dígitos, correlativo: cada notebook nuevo toma el siguiente número libre al
  crearse. No se reservan números para fases o experimentos futuros; los pendientes se listan
  sin número.
- `{autor}` — iniciales (ver [`CONTRIBUTING.md` §1](../CONTRIBUTING.md#1-quién-es-quién)). `jss` = Jason Sepúlveda S.; `gm` = Gustavo Martínez.
- `{nombre}` — tema, en minúsculas y con guiones.

Ejemplo: `00-jss-corpus-y-auditoria.ipynb`

Para crear uno nuevo, sigue la lista de pasos de [`CONTRIBUTING.md` §7.3](../CONTRIBUTING.md#73-notebooks).

## La serie

| | Notebook | Cubre | Estado |
|---|---|---|---|
| 00 | `00-jss-corpus-y-auditoria.ipynb` | Adquisición del corpus, verificación estructural (paso cero), auditoría de datos §5.1, y las decisiones de diseño que la auditoría obligó a tomar | ✅ |
| 01 | `01-jss-viabilidad-e3.ipynb` | Estimación **provisional** de la tasa de positivos del filtro y verificación de las relaciones identificadas a ojo. Decide si el estrato E3 se sostiene | ✅ |
| 02 | `02-jss-transcripciones.ipynb` | Del AMI Meeting Corpus (anotación *stand-off* NXT) a transcripciones legibles y congeladas: decisiones de render, los dos artefactos por reunión, cobertura del corpus y el manifiesto verificable | ✅ |
| 03 | `03-jss-eda.ipynb` | Análisis exploratorio de datos de AFG2 sobre las 14 series: proveniencia, calidad, faltantes, atípicos, relaciones, estructura multivariada y temporal, preguntas dirigidas e implicancias para el modelado; robustez con corrección por comparaciones múltiples (Benjamini-Hochberg) y bootstrap por serie. Solo estadísticas agregadas (ADR 0005) | ✅ |
| 04 | `04-jss-anotacion-f1-calibracion.ipynb` | Anotación **humana**, Fase 1: calibración sobre ES2015 y recalibración sobre TS3009 (doble anotación `gm`/`gv`, adjudicación de `jss`). Acuerdo **diagnóstico**, no reportable; vacíos de la guía que reveló. La sección de TS3009 muestra que el acuerdo crudo subió de 45 % a 83 % y por qué el kappa de estado quedó en 0,000 (un anotador usó una sola etiqueta), y registra la decisión de no recalibrar más y abrir la Fase 2 con ES2016 | ✅ |
| 05 | `05-jss-seleccion-juez.ipynb` | Selección del modelo juez de §5.7: criterios tomados de la literatura, umbrales prerregistrados y calibración de los candidatos contra etiquetas humanas sobre series de desarrollo | ✅ |
| 06 | `06-jss-ajuste-c1.ipynb` | Ajuste de la línea base C1 (§5.3) sobre ES2015: segmentación y número de fragmentos por recall de evidencia, con regla prerregistrada; presupuesto de texto compartido con C2 y C3 | ✅ |
| 07 | `07-jss-runner-experimento-b.ipynb` | Motor de corrida del Experimento B y corrida de humo con C1 sobre ES2015: tabla por pregunta, resumen por estrato, tiempos, el marcador `USED:` en línea y la citación bajo la regla del ADR 0009 (alguna cita acierta) con su precisión. Serie de desarrollo: sus cifras no entran en resultados (ADR 0005) | ✅ |
| 08 | `08-jss-fechas-de-reunion.ipynb` | Fechas de evento de las reuniones que se entregan a OpenKOS: qué trae `meetings.xml` en las 14 series (fecha común, hora real en 6 y ausente en 8), por qué el orden a→d es necesario, alternativas descartadas y la regla de hora sintética que solo preserva el orden ([ADR 0008](../docs/decisions/0008-adr-fechas-de-reunion-para-openkos.md)). Análisis estructural, admisible en todas las series | ✅ |
| 09 | `09-jss-regla-de-citacion.ipynb` | Análisis de la regla de citación correcta (§5.6, §6.2) sobre la corrida de humo con C1 en ES2015: tamaño de la evidencia de referencia y de las citas, cuatro variantes de la regla lado a lado (todos tocan, alguno toca, precisión, cobertura), cruce con el veredicto del juez y tres casos concretos. Describe y ofrece opciones; la decisión que tomó la dirección con este análisis (variante b como regla y c como cifra secundaria) está en el ADR 0009. Serie de desarrollo: sus cifras no entran en resultados (ADR 0005) | ✅ |
| 10 | `10-jss-potencia-criterio-d16.ipynb` | Potencia del criterio principal D16 por simulación Monte Carlo con datos **sintéticos** (no se corrió ningún experimento ni modelo): intervalos independientes sin solapar frente a diferencia pareada C2 − C1 por encima de 0, con 3 corridas por pregunta, dificultad compartida entre condiciones, tamaños de 25, 40 y 50 preguntas y falsos positivos. Respalda la enmienda de D16 del [ADR 0010](../docs/decisions/0010-adr-decisiones-del-analisis-del-experimento-b.md). Sus cifras describen el criterio de decisión, no a C1, C2 ni C3 | ✅ |
| 11 | `11-jss-figuras-video-eda.ipynb` | Selección de cinco figuras para el video de avance #1 (máximo 8 minutos): criterios tomados de la rúbrica, versión legible para grabación de pantalla, justificación de cada figura, su efecto en los siguientes pasos y exportación como PNG a `docs/entregables/figuras/`. Cuatro provienen del [notebook 03](03-jss-eda.ipynb) y el embudo del filtro léxico (3.071 → 92 pares) sale de `afg.audit.candidate_funnel`; no se calcula nada nuevo | ✅ |
| 12 | `12-jss-extraccion-openkos-es2015.ipynb` | Corrida **exploratoria** de extracción con OpenKOS 0.5.5 sobre ES2015: procedencia (versión, *digest* de modelos, semillas, commit, duración), decisiones extraídas por reunión junto a las 27 de la referencia adjudicada, solapamiento entre corridas (Jaccard de 0,70 a 0,82), reproducibilidad con la misma semilla y una observación cualitativa de elementos extraídos que no son decisiones. Solo describe las corridas: no calcula precisión ni cobertura. Serie de desarrollo y versión provisional: sus cifras no entran en resultados (ADR [0005](../docs/decisions/0005-adr-development-evaluation-split.md) y [0006](../docs/decisions/0006-adr-c1-rag-separado-con-respuesta-de-openkos.md)) | ✅ |
| 13 | `13-jss-anchura-de-citas.ipynb` | Insumo para #97: si la regla de citación (ADR [0009](../docs/decisions/0009-adr-regla-de-citacion-correcta.md)) favorece a una condición por la anchura de sus citas. Compara C1 y C2 (corridas de humo sobre ES2015) con la anchura en actos de diálogo (por respuesta y por unidad citada), la precisión y la cobertura por acto (`afg.evaluation.citation_width`) y una vista de control por anchura; recalcula `citation_correct` con la regla vigente para ambas. Solo describe: no decide ni modifica la regla. Serie de desarrollo y muestra de 11 a 13 respuestas: indica una dirección y sus cifras no entran en resultados (ADR [0005](../docs/decisions/0005-adr-development-evaluation-split.md)) | ✅ |
| 14 | `14-jss-alineacion-experimento-a.ipynb` | Insumo para #99: ámbito de la alineación del Experimento A (misma reunión frente a toda la serie), rol de una decisión con evidencia de varios hablantes (mayoritario frente a cada rol) e intervalos por decisión frente a un *bootstrap* por reuniones, sobre las tres corridas de `es2015-explora-r3x` a lo largo de la grilla de τ. Muestra cuántos emparejamientos cambian y tres cruces entre reuniones leídos. Ofrece los insumos de la decisión; esta quedó registrada después en el ADR [0011](../docs/decisions/0011-adr-alineacion-rol-e-intervalos-del-experimento-a.md). Calcula embeddings con el modelo de alineación (`bge-m3`) servido por Ollama local. Serie de desarrollo, OpenKOS 0.5.5 provisional y muestra pequeña: sus cifras no entran en resultados (ADR [0005](../docs/decisions/0005-adr-development-evaluation-split.md)) | ✅ |
| 15 | `15-jss-screen-de-modelos-openkos.ipynb` | Relectura con el puntaje de la tesis del *screen* prerregistrado de cuatro modelos generativos (`qwen3:8b`, `qwen3:14b`, `qwen3.6:27b`, `qwen3.6:35b-a3b`) para el pase de decisiones de OpenKOS 0.6.0 sobre ES2015 y TS3009 (corridas en `reports/experiment-a/model-screen-openkos/`): reproducción de la cifra de ES2015 (0,519 con τ = 0,60), concordancia exacta con la copia del puntaje de OpenKOS, tablas del *screen* (n = 5) y de la confirmatoria (n = 15) con la regla de selección, curvas de τ, control nulo entre equipos, dispersión entre corridas y techo entre idiomas. Deja preguntas abiertas (idioma, τ primario, modelo, §5.3); no decide. Calcula embeddings con `bge-m3` servido por Ollama local. Serie de desarrollo: sus cifras no entran en resultados (ADR [0005](../docs/decisions/0005-adr-development-evaluation-split.md)) | ✅ |
| 16 | `16-jss-c2-fuentes-e1.ipynb` | Insumo para #146: qué contexto recupera C2 al responder las preguntas de hecho puntual (E1) y cómo se relaciona con el acierto frente a C1, sobre las tres corridas de humo de ES2015 (`afg.experiments.c2_context`). Composición del contexto por tipo de bloque (transcripción en bruto, decisiones, resúmenes de tema), un caso completo, cruce con el veredicto y evidencia para clasificar los errores de C2 según OE4: la parte objetiva de la regla se calcula y las ocho fallas restantes llevan la etiqueta humana de jss (PR #177); reparto de las nueve fallas: recuperación 4, extracción 3, síntesis 2. Deja abierta la decisión de si C2 debe recuperar fuentes en bruto (a coordinar con openkos#1560); no decide. Serie de desarrollo: sus cifras no entran en resultados (ADR [0005](../docs/decisions/0005-adr-development-evaluation-split.md)) | ✅ |
| 17 | `17-jss-tau-referencia-en.ipynb` | Insumo para #142: dos evidencias para fijar τ con la referencia en inglés (protocolo de alineación v2.0), sin extracciones nuevas. Curvas reales con la referencia en español y en inglés sobre las 100 corridas del *screen* y la confirmatoria de OpenKOS (ES2015 y TS3009); control nulo entre equipos y `τ_nulo` (menor τ con cobertura nula media ≤ 0,05); muestra de 200 pares emparejados con similitud en [0,50; 0,90), estratificada en bins de 0,05, juzgada por `gpt-oss:20b` («¿misma decisión?», respuestas en `reports/experiment-a/tau-calibration/`) y `τ_juez`; propuesta `max(τ_nulo, τ_juez)`. Reglas fijadas antes de mirar los resultados; deja preguntas abiertas; el τ principal (0,70, con 0,75 y 0,80 como sensibilidad) se fijó después en el ADR [0012](../docs/decisions/0012-adr-umbral-tau-del-experimento-a.md). Calcula embeddings con `bge-m3` y llama al juez en Ollama local (la segunda ejecución reutiliza las respuestas guardadas). Serie de desarrollo: sus cifras no entran en resultados (ADR [0005](../docs/decisions/0005-adr-development-evaluation-split.md)) | ✅ |
| 18 | `18-jss-anotacion-f2-adjudicacion.ipynb` | Anotación **humana**, Fase 2: doble anotación (`gm`/`gv`) y adjudicación (`jss`) de las series de control. Hoy cubre **ES2016** (de 4 series): acuerdo en decisiones (17 de 24, 70,8 %; kappa de estado −0,077, **diagnóstico**) y por qué es negativo con un acuerdo alto, estados finales de la referencia, a quién dio la razón el veredicto, patrón de desacuerdos por pares de etiquetas, pares (kappa de tipo 1,0; existencia y dirección indefinidos) y comparación con ES2015 y TS3009. Estructurado para agregar IS1003, TS3005 y ES2008 y el resumen entre series. Serie de evaluación: solo estadísticas agregadas, sin contenido (ADR [0005](../docs/decisions/0005-adr-development-evaluation-split.md)) | en curso (ES2016) |
| 19 | `19-jss-modelos.ipynb` | Etapa de modelado (AFG2, semana 4): qué se pide en el curso y su equivalente en la tesis, restricciones del EDA, reparto desarrollo/evaluación en volúmenes y porcentajes, *pipeline* de cada condición, modelos por rol (extractor, juez), búsqueda de parámetros, línea base C0/C1/C2 en desarrollo, variabilidad, costo, dificultades y pendientes. Solo lee resultados guardados (sin Ollama); exporta seis figuras `modelos-*` a `docs/entregables/figuras/`. Incluye la comparación de F1 y tiempo del extractor, el gráfico de las etapas de las fallas de C2 en E1 y la lista de controles de comparabilidad (el [20](20-gm-mejoras-modelado.ipynb) los amplía). Necesita el corpus. **Descriptivo, sin resultados de la tesis.** | ✅ |
| 20 | `20-gm-mejoras-modelado.ipynb` | Complemento del 19 (AFG2, semana 4): extractor `qwen3:8b` frente a `qwen3.6:27b` en la confirmatoria (F1, *recall*, reuniones fallidas y tiempo por serie), etapa probable de las nueve fallas de C2 en E1 (recuperación, extracción, síntesis) y tabla de controles para comparar C1 y C2. Lee resultados guardados con funciones de `src/afg/` (sin Ollama ni corpus); no exporta figuras. **Descriptivo, sin resultados de la tesis.** | ✅ |
| 21 | `21-jss-extraccion-de-conceptos-openkos.ipynb` | Las decisiones de OpenKOS sobre la extracción de conceptos con que se construye C2, cada una con su prerregistro, releídas desde los archivos de puntaje agregados (`reports/experiment-a/extraccion-conceptos-openkos/`, `afg.experiments.concept_extraction`): el modelo (openkos #1557: `qwen3:8b` se queda, por qué cayó cada candidato, y la pérdida por etapa de #1559), el descarte determinista responsable de la pérdida L7 (#1572: la regla de *framing*, sana para el contenedor, con un falso positivo en #1575) y el tamaño de ventana (#1558: 4.000 caracteres se queda; los conceptos por reunión caen con la ventana). Explica la métrica (alza de cobertura contra el oro abstractivo de AMI con control de reunión ajena, IC *bootstrap*), reaplica cada regla registrada, coteja con los informes de OpenKOS y resume las decisiones vigentes; deja pendientes openkos #1571 y #1560. No llama a ningún modelo. Serie de desarrollo: sus cifras no entran en resultados (ADR [0005](../docs/decisions/0005-adr-development-evaluation-split.md)) | ✅ |
| — | `NN-jss-anotacion-f3-referencia.ipynb` | Anotación humana, Fase 3: reparto individual y conjunto de referencia final de las 14 series | pendiente |
| — | `NN-jss-experimento-a.ipynb` | OE2 — calidad de la extracción automática contra la referencia | pendiente |
| — | `NN-jss-experimento-b.ipynb` | OE3/OE4 — C1 vs C2 vs C3 y atribución del error a su etapa | pendiente |

> **Por qué el 01 y los notebooks de anotación están separados.** El 01 contiene etiquetas
> puestas por una máquina, con fines de planificación. Los de anotación (el 04 y los de las
> Fases 2 y 3) contienen la anotación real, hecha a mano, y el conjunto de
> referencia resultante. Mezclarlos invitaría a que alguien cite las provisionales como si
> fueran la referencia.
>
> **Por qué un notebook por fase de anotación.** Cada fase responde una pregunta distinta con
> un estatus distinto: la Fase 1 es diagnóstico (su kappa no se reporta), la Fase 2 produce el
> kappa reportable y la Fase 3 el conjunto de referencia. Un solo notebook mezclaría cifras
> que se citan con cifras que no.

## Regla de arquitectura: el notebook no calcula

**Toda cifra que un notebook muestre viene de una función testeada en `src/afg/`.**
El notebook importa, llama y grafica. No define lógica.

Esto no es purismo. En este proyecto una extrapolación hecha fuera del paquete produjo un
conteo de ~170 candidatos cuando la cifra real era 712 — un error de un factor de cuatro que
solo apareció al correr la función real sobre el conjunto real. Una celda de notebook es una
fuente de verdad paralela que nadie testea y que se desincroniza del CLI. Si "cuántas
decisiones hay" admite dos respuestas distintas, alguna acabará citada en la tesis.

La capa de cálculo de la auditoría vive en `src/afg/audit/`; la de cada tema, en el subpaquete
que le corresponde (`corpus`, `eda`, `experiments`, `extraction`). Las cifras que algunas celdas
calculaban en línea (el embudo del filtro y sus horas, la cobertura de la capa `disfluency`, el
resumen del manifiesto, las fechas de las reuniones, la potencia del criterio D16, las columnas
de citación y el rol de cada juez candidato) salen hoy de funciones con prueba, así que la regla
se cumple en los trece notebooks.

## Regla de alcance: qué se puede mirar

El proyecto tiene un split desarrollo / evaluación (ver
[`../docs/decisions/0005-adr-development-evaluation-split.md`](../docs/decisions/0005-adr-development-evaluation-split.md)).
Mirar el **contenido** del conjunto de evaluación es contaminarlo.

| Tipo de análisis | Qué incluye | Dónde es admisible |
|---|---|---|
| **Estructural** | conteos, coberturas, distribuciones, participantes, roles, longitudes, duraciones | Todas las series |
| **De contenido** | leer textos de decisiones, inspeccionar pares candidatos, leer transcripciones | **Solo desarrollo** (ES2015, IS1004, TS3009) |

## Reproducibilidad

- El corpus está en `.gitignore`. Un clon fresco necesita `uv run afg corpus download`
  antes de ejecutar un notebook que lee el corpus; esos notebooks empiezan con una guarda
  que falla con un mensaje claro si falta. Los notebooks que trabajan solo con los CSV y los
  reportes versionados (por ejemplo el 01, 04, 05, 06, 07, 09 y 10) no la llevan.
- **Estos notebooks se versionan CON sus outputs.** Es lo contrario de la práctica habitual
  en repositorios de código, y es deliberado: aquí el notebook es un entregable académico,
  y un revisor tiene que poder leer los resultados sin ejecutar nada ni tener los 228 MB del
  corpus. Los outputs *son* el registro.
- A cambio, la disciplina es más estricta: **todo notebook debe ser re-ejecutable de punta a
  punta, y hay que re-ejecutarlo antes de entregarlo**, para que lo que muestra corresponda
  al código actual del paquete. Un notebook con outputs obsoletos es peor que uno sin
  outputs, porque miente con autoridad.

```bash
uv run jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=900 notebooks/00-jss-corpus-y-auditoria.ipynb
```

```bash
uv sync --group notebooks
uv run jupyter lab
```
