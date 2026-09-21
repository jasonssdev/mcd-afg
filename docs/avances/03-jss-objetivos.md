# Objetivos

| | |
|---|---|
| **Documento** | 03 — Objetivos |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 2.1 |
| **Fecha** | 2026-09-20 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial. Objetivos e hipótesis para AFG1. | Primera entrega del curso. |
| 2.0 | 2026-09-20 | Alcance por curso y cambios de H3 | Plan realista para tres cursos y reconciliación de la escala de modelo configurada |
| 2.1 | 2026-09-20 | Aporte propositivo explícito; origen de la observación de H3; punto de decisión de AFG2; nota de sincronización del plan | Revisión final de AFG1 |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## Objetivo general

Diseñar, implementar y evaluar experimentalmente un método de extracción automática y
representación persistente de decisiones organizacionales —incluyendo su evolución a través
de reuniones sucesivas— utilizando modelos de lenguaje de ejecución local, con el fin de
**cuantificar por separado** el valor aportado por la representación, el costo introducido
por los errores de su extracción automática, y las condiciones bajo las cuales el resultado
neto supera a un sistema RAG aplicado directamente sobre las transcripciones originales.

### Qué propone este proyecto, además de medir

El aporte no es solo una medición. El proyecto propone cuatro cosas que no existen en el estado
del arte revisado: (1) un **conjunto de referencia con enlaces tipados entre decisiones de
reuniones sucesivas** sobre un corpus real, que ninguna capa de anotación publicada ofrece;
(2) un **diseño de tres condiciones** que separa el valor de la representación del costo de
su extracción, en lugar de comparar sistemas completos; (3) una **taxonomía determinista de
atribución de error** (extracción, recuperación, síntesis) aplicable a cualquier sistema que
persista conocimiento extraído; y (4) el **punto de equilibrio amortizado** como métrica
operativa de decisión, en lugar de la latencia aislada. La medición es lo que permite
evaluar esas propuestas; las propuestas son el aporte.

## Objetivos específicos

### OE1 — Construir un conjunto de referencia de decisiones con evolución entre reuniones

Se deriva un conjunto de referencia a partir de las capas de anotación ya existentes en AMI
(resumen abstractivo, `summlink`, capa DDS como validación), extendiéndolas con la única
anotación que el corpus no posee: el enlace temporal entre reuniones, del conjunto cerrado
`{ introduce, reafirma, refina, revierte, reemplaza, no-relacionada }`, con evidencia
obligatoria (reunión y rango de actos de diálogo).

**Las etiquetas las pone un humano, nunca un modelo.** Si un LLM construyera OE1, la
condición C3 tendría errores de extracción por construcción y la brecha C2 − C3 —que es todo
OE4— dejaría de medir nada. Los modelos sólo pueden proponer candidatos, resolver evidencia y
calcular acuerdo; nunca decidir si algo es una decisión.

**Confiabilidad declarada, no asumida.** Doble anotación independiente sobre el 36,4 % de la
evaluación (≥25 % exigido), kappa de Cohen reportado por separado para existencia, tipo y
dirección de la relación, y protocolo de adjudicación documentado.

**Criterio de cumplimiento:** el conjunto de referencia existe para las 14 series (343
decisiones, 92 pares candidatos adjudicados), con kappa reportado en los tres niveles y
adjudicación documentada para todo desacuerdo.

### OE2 — Medir la calidad de la extracción automática (Experimento A)

Se cuantifica la capacidad de modelos de lenguaje de ejecución local para extraer decisiones
y sus relaciones temporales, contra el conjunto de referencia de OE1.

- **Nivel decisión:** precisión, cobertura y F1, bajo el protocolo de alineamiento del
  documento 06 (asignación húngara, curva sobre τ).
- **Nivel relación temporal:** exactitud de la etiqueta y, reportada por separado, exactitud
  de la **dirección** — si el sistema identifica correctamente cuál decisión revisa a cuál.
- **Estratificación obligatoria por rol del hablante.** El eje nativo/no-nativo de inglés
  **ya no es estratificación obligatoria**: pasa a limitación declarada (ver "Cambios"
  abajo y el documento 05, §2).

**Criterio de cumplimiento:** P/R/F1 a nivel decisión reportados como curva sobre τ; exactitud
de tipo y de dirección reportadas por separado; desglose por rol publicado aunque no se
detecte diferencia.

### OE3 — Medir la utilidad funcional en tres condiciones (Experimento B)

Se compara el desempeño frente a un mismo banco de preguntas estratificado, bajo tres
condiciones que comparten modelo generativo, modelo de *embeddings*, hardware y presupuesto
de contexto:

| | Condición | Rol |
|---|---|---|
| **C1** | RAG documental sobre las transcripciones originales | Piso — la práctica actual |
| **C2** | Base estructurada construida automáticamente | La propuesta bajo evaluación |
| **C3** | Base estructurada construida desde la anotación de OE1 | Referencia superior, no "techo teórico" |

Métricas de calidad: corrección de la respuesta, tasa de soporte de evidencia, tasa de
citación correcta, y corrección del rechazo ante preguntas incontestables (estrato E4).
Métricas operativas: memoria residente, y **costo amortizado** — el punto de equilibrio en
número de consultas a partir del cual compilar y consultar es más barato que consultar
siempre por RAG.

**Criterio de cumplimiento:** las tres condiciones evaluadas sobre el mismo banco de
preguntas estratificado (E1–E4, ≥25 por estrato), con intervalos de confianza por *bootstrap*
reportados para cada métrica.

### OE4 — Atribuir el error final a su etapa de origen

Para cada respuesta incorrecta o sin soporte de C2, se determina si el error se originó en la
**extracción** (el hecho quedó mal escrito en la base), la **recuperación** (el hecho
correcto existía pero no fue recuperado) o la **síntesis** (el material correcto fue
recuperado y la respuesta lo contradice), mediante el procedimiento determinista del
documento 06 §7.

**Criterio de cumplimiento:** toda respuesta fallida de C2 queda clasificada en una y sólo
una de las tres categorías, con la proporción atribuible a extracción reportada como cifra
principal (documento 05, principio de responsabilidad).

## Alcance por curso

| Curso | Qué se entrega | Objetivos |
|---|---|---|
| **AFG1** | Problema, estado del arte, metodología, ética, conjunto de referencia listo para anotar (herramientas de OE1) y anotación iniciada en desarrollo | OE1 (herramientas) |
| **AFG2** | OE1 cerrado (anotación + kappa); OE2 sobre las 14 series con una escala de modelo (3 corridas); OE3 con banco de preguntas ≥100 y las tres condiciones, versión mínima | OE1, OE2, OE3 (mínimo) |
| **AFG3** | OE4, análisis de errores, intervalos bootstrap, conclusiones | OE4 |

Extensiones si hay tiempo: segunda escala de modelo (H3), validación humana ampliada.

> La versión canónica de esta tabla está en `README.md` (sección "Plan por curso"). Si
> cambia, se actualiza en ambos lugares.

**Punto de decisión en AFG2.** Al cierre de la semana 3 de AFG2, el adaptador de OpenKOS
debe correr de punta a punta sobre las tres series de desarrollo (extracción, persistencia y
consulta). Si no lo hace, OE3 se reduce a comparar **C1 contra C3** (el valor de la
representación sin errores de extracción) y OE4 se pospone a AFG3 o se declara fuera de
alcance. La decisión se toma en esa fecha y se registra en `docs/decisions/`, no se descubre en la
semana 7.

| Objetivo | Mínimo comprometido | Extensión |
|---|---|---|
| **OE1** | 14 series anotadas, kappa en 3 niveles, adjudicación | — |
| **OE2** | Una escala (qwen3:8b o equivalente), 3 corridas, curva sobre τ, desglose por rol | Segunda escala |
| **OE3** | Banco ≥100 preguntas (25 × 4 estratos), tres condiciones, juez automático con validación humana del 20 % | Validación humana ampliada |
| **OE4** | Clasificación determinista de todas las respuestas fallidas de C2 | — |

## Hipótesis

Declaradas antes de la ejecución para evitar reinterpretación posterior.

| | Hipótesis | Fundamento |
|---|---|---|
| **H1** | C2 y C3 superarán a C1 en preguntas de evolución (E3), con diferencia pequeña o nula en hecho puntual (E1) | La ventaja de la representación es relacional |
| **H2** | La brecha C3 − C2 será mayor en relaciones temporales que en identificación de decisiones | Extraer que algo se decidió es más fácil que extraer correctamente que una decisión reemplaza a otra |
| **H3** | La dirección de las relaciones temporales será un modo de falla dominante, sin mejora proporcional al tamaño del modelo | Observación informal en el instrumento a dos escalas (≈8B y ≈30B): alrededor de un 25 % de direcciones invertidas, sin mejora clara con la escala. Es una observación previa, no una medición del proyecto; la segunda escala es una extensión. |
| **H4** | C1 mostrará mayor tasa de respuestas confiadas pero desactualizadas en preguntas de evolución | Consistente con lo reportado en la literatura de recuperación insuficiente |

**Origen de la observación de H3.** Proviene de corridas informales previas de OpenKOS
realizadas por Jason Sepúlveda antes de este proyecto, sin registro en este repositorio. Por
eso no se cita como cifra del proyecto ni entra en ningún notebook: es la motivación de la
hipótesis, no evidencia. La medición formal es OE2.

**Plan ante resultado negativo.** Si H1 no se sostiene —si RAG documental iguala a la
representación estructurada incluso en preguntas de evolución—, el resultado es igualmente
publicable: sería la primera medición controlada que acota el valor de compilar en este
dominio. Ninguna conclusión del proyecto depende de que la representación estructurada gane;
el aporte es la medición, no el sistema.

**Nota provisional sobre E3.** El estrato E3 necesita ≥25 preguntas. La evidencia disponible
—11 candidatos de desarrollo adjudicados por máquina, tasa de positivos 45,5 % (5/11), IC 95 %
Wilson [21,3 % – 72,0 %], proyectado a evaluación ~37 relaciones, IC [17 – 58]— hace a E3
**plausible, no demostrado**: el valor central alcanza el mínimo, la cota inferior del
intervalo no. Estas etiquetas fueron puestas por una máquina, sirven sólo para decidir si
vale la pena anotar, y no son el conjunto de referencia de OE1.

## Cambios respecto de la propuesta original

| Qué cambió | Evidencia que lo obligó |
|---|---|
| OE2 ya no exige estratificación obligatoria por condición nativo/no-nativo de inglés | La lengua materna está anidada en el sitio de grabación y el bloque TS carece de dato de lengua (documento 02, §4.5; documento 05, §2) — decisión D7 |
| La base de OE1 pasó de 6 series / 136 decisiones a 14 series / 343 decisiones | Marco muestral revisado (documento 02, §4.1) — decisión D1 |
| La viabilidad de E3 se declara explícitamente provisional, con intervalo de confianza | Adjudicación de desarrollo (11 candidatos), no de evaluación — `notebooks/01-jss-viabilidad-e3.ipynb` |
| La segunda escala de modelo pasa de compromiso a extensión | Costo de cómputo local y prioridad del mínimo viable por curso |

---

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| Objetivo general y OE1–OE4 | [`../propuesta.md`](../propuesta.md) §2–§3 |
| Hipótesis H1–H4 y plan ante resultado negativo | [`../propuesta.md`](../propuesta.md) §4 |
| Cambio de estratificación de OE2 (D7) | [`../decisions/README.md`](../decisions/README.md) |
| 343 decisiones, 92 candidatos | [`../../config/corpus.toml`](../../config/corpus.toml), sección `[oe1]` |
| Viabilidad de E3: 45,5 % (5/11), IC [21,3 % – 72,0 %], proyección ~37 [17–58] | [`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb) |
| Plan por curso | README.md, sección Plan por curso; programa del curso (objetivos de AFG1, AFG2, AFG3) |
