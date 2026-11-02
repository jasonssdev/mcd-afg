# Protocolo de alineación (sección 5.4 de la tesis)

| | |
|---|---|
| **Documento** | Protocolo de alineación |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 3.1 |
| **Fecha** | 2026-11-02 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial del protocolo (punto cero del proyecto). | Fijar el procedimiento de alineación antes de ver resultados de OE2. |
| 1.1 | 2026-10-15 | Se agrega la cabecera de versión y se usa la terminología estándar en la prosa («ground truth» y «τ»); los identificadores de código y de configuración (`tau`, `tau_grid`) no cambian. No cambia el procedimiento. | Auditoría de gobernanza del 2026-10-15: este protocolo no llevaba versión y mezclaba términos con los avances. |
| 2.0 | 2026-10-19 | El texto de referencia que se compara con las extracciones es la traducción automática al inglés de `final_object` y `final_content` (`data/processed/decisions/<SERIE>.reference-en.csv`, issue #141). Las etiquetas humanas siguen en español y son el ground truth: la traducción no cambia ningún estado ni etiqueta. El procedimiento (pasos 1 a 4) no cambia, y tampoco se fija τ, que corresponde al issue #142. | La extracción sale en el idioma original de las transcripciones (inglés) y la referencia está en español; comparar entre idiomas pone un techo artificial a la similitud: en el [notebook 15](../../notebooks/15-jss-screen-de-modelos-openkos.ipynb) (§6.4) la mediana es 0,689 en ES2015 y 0,724 en TS3009, y solo 3 de 27 y 3 de 21 decisiones llegan a 0,80. |
| 3.0 | 2026-10-19 | Se fija el umbral τ del Experimento A: **τ principal = 0,70**, con **0,75 y 0,80 como análisis de sensibilidad** y la curva completa sobre `tau_grid` siempre al lado (paso 4). Se declara que el juez automático (`gpt-oss:20b`, prompt `same-decision-v1`) **complementa** la validación manual del paso 3 y no la sustituye, y que una comprobación de concordancia juez–persona sobre 50 pares de la muestra juzgada queda pendiente. El procedimiento (pasos 1 a 4) y el tamaño mínimo de la validación manual (100 pares) no cambian. Se aparta de la regla prerregistrada `max(τ_nulo, τ_juez)` = 0,80. | El control nulo cruza dos equipos con el mismo encargo de diseño, así que parte de sus coincidencias son la misma decisión y el piso de azar está sobrestimado; el desvío responde a ese defecto del control, no a la cobertura que resulta. Cifras: cobertura nula 0,138, 0,053 y 0,015 con τ = 0,70, 0,75 y 0,80; proporción de «sí» del juez a lo más 0,32 por debajo de 0,70 y al menos 0,76 en cada bin desde 0,70 ([ADR 0012](../decisions/0012-adr-umbral-tau-del-experimento-a.md), [notebook 17](../../notebooks/17-jss-tau-referencia-en.ipynb)). |
| 3.1 | 2026-11-02 | Se registra el resultado de la comprobación de concordancia juez–persona que la versión 3.0 dejó pendiente: acuerdo de 43 de 50 pares (86 %) y kappa de Cohen de 0,716 (IC 95 % de 0,520 a 0,880); los 7 desacuerdos son del juez en «no» y la persona en «sí». Se mantiene τ = 0,70 y el juez como complemento. Se declara que, como el juez es más estricto que una persona, las cifras de alineación con τ = 0,70 son un **piso conservador** (sesgo en contra del sistema evaluado). El procedimiento (pasos 1 a 4) y los umbrales no cambian. | Cierra el punto pendiente de la versión 3.0. Por debajo de 0,70 el juez dice «sí» en el 21 % de los pares y la persona en el 42 % (24 pares); desde 0,70, 81 % y 88 % (26 pares). Evidencia limitada: una sola persona, que además adjudica y mantiene el proyecto, y solo ES2015 y TS3009 ([ADR 0012](../decisions/0012-adr-umbral-tau-del-experimento-a.md), [notebook 17](../../notebooks/17-jss-tau-referencia-en.ipynb) §8). |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

Congelado antes de ver los resultados de OE2. Implementado en
`src/afg/evaluation/alignment.py`, con test en `tests/test_alignment.py`.

## Por qué existe

Una decisión extraída no coincidirá literalmente con una decisión del ground truth. Si una decisión
extraída "es" una decisión del ground truth requiere un procedimiento de correspondencia declarado
*antes* de examinar los resultados — de lo contrario la elección de alineación misma se
convierte en un lugar donde ajustar (consciente o inconscientemente) las cifras reportadas.

## Idioma del texto de referencia

El texto de referencia que se compara con las extracciones es la **traducción automática al
inglés** de `final_object` y `final_content`, guardada en `<SERIE>.reference-en.csv`
(`load_reference(..., language="en")`). La extracción sale en el idioma original de las
transcripciones, el inglés, y comparar un texto en inglés con una referencia en español pone un
techo artificial a la similitud de embeddings. Las etiquetas humanas siguen siendo las de
`final_*` en español y son el ground truth: la traducción nunca decide un estado ni una relación.
La validación (`afg gold validate-translation`) garantiza que cada decisión de referencia tiene
traducción y que no está desactualizada respecto del español adjudicado. Método y reglas:
[`../anotacion/traduccion-referencia.md`](../anotacion/traduccion-referencia.md).

## Procedimiento

1. **Candidatos.** Calcular la similitud coseno de embeddings sobre el par
   `(decision_object, content)` para cada par (predicha, referencia) de decisiones, con el texto de la referencia en inglés.
   Cualquier par con similitud igual o superior a un umbral τ (`tau` en el código) es un candidato de
   coincidencia.
2. **Restricción uno a uno.** Resolver los candidatos como una asignación uno a uno de peso
   máximo mediante el algoritmo húngaro (`scipy.optimize.linear_sum_assignment`), nunca por
   vecino más cercano de forma voraz. La asignación voraz permitiría que varias extracciones
   reclamaran la misma decisión de referencia, inflando la precisión aparente.
3. **Validación manual.** El protocolo automático se contrasta contra el emparejamiento
   manual en una muestra de al menos 100 pares; la concordancia se reporta
   (`src/afg/evaluation/alignment.py::concordance`). El juez automático de la calibración de
   τ (véase «Umbral τ») complementa esta validación; no la sustituye.
4. **Sensibilidad.** F1 se reporta como una curva sobre una grilla de τ
   (`config/experiments.toml`, `[alignment].tau_grid`), nunca como un solo punto, con el τ
   principal y las sensibilidades de la sección «Umbral τ» marcados sobre ella. Si el
   orden entre condiciones cambia a lo largo de la grilla, eso se declara explícitamente en
   el resultado escrito, no se suaviza eligiendo un τ favorable.

## Umbral τ

El **τ principal es 0,70**; **0,75 y 0,80 se informan siempre como análisis de sensibilidad**, y
la curva completa sobre `tau_grid` va al lado. El valor se fijó con la referencia en inglés sobre
series de desarrollo, con dos insumos: la cobertura que una salida ajena (control nulo) alcanza con
cada τ y la proporción de pares que un juez automático llama «la misma decisión» (`gpt-oss:20b`,
`same-decision-v1`). Se aparta de la regla prerregistrada `max(τ_nulo, τ_juez)`, que daba 0,80,
porque el control nulo cruza dos equipos con el mismo encargo de diseño y sobrestima el azar; el
desvío y su evidencia están en el [ADR 0012](../decisions/0012-adr-umbral-tau-del-experimento-a.md).

El juez es un modelo: **complementa** la validación manual del paso 3 y no la reemplaza. Su
concordancia con una persona, sobre 50 pares de la muestra que juzgó, se midió el 2026-11-02: acuerdo
de 43 de 50 (86 %) y kappa de Cohen de 0,716 (IC 95 % de 0,520 a 0,880), sustancial. El juez es más
estricto que una persona (los 7 desacuerdos son del juez en «no» y la persona en «sí»; por debajo de
0,70 dice «sí» en el 21 % de los pares y la persona en el 42 %), de modo que el emparejamiento con
τ = 0,70 probablemente deja fuera coincidencias reales: las cifras de alineación son un **piso
conservador**, un sesgo en contra del sistema evaluado. Se mantiene τ = 0,70. La evidencia es limitada
(24 pares por debajo de 0,70, una sola persona que además adjudica y mantiene el proyecto, y solo las
series de desarrollo ES2015 y TS3009).

## Métricas explícitamente rechazadas

**PR-AUC** y **matrices de confusión** no se usan como métricas primarias: ambas presuponen
un clasificador que emite puntajes sobre un conjunto fijo de clases. Este sistema emite
conjuntos de objetos de decisión en lenguaje natural, que no tienen una estructura de
clases fija contra la cual puntuar.

**Recall@K** se conserva, pero solo para evaluar la etapa de *recuperación* dentro de C1 y
C2, donde sí existe un ranking — nunca como métrica de calidad de extracción.

## Backend de embeddings

Este módulo recibe la matriz de similitud como argumento (inyección de dependencias): no
tiene una dependencia en tiempo de importación de ningún modelo o biblioteca de embeddings
en particular. El paso de embeddings (calcular similitudes a partir de pares
`(decision_object, content)` con el modelo configurado en `config/experiments.toml`)
ocurre antes, en un llamador que tiene instalado el grupo de dependencias opcional
`embeddings`.
