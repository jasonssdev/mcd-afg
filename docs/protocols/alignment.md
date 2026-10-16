# Protocolo de alineación (sección 5.4 de la tesis)

| | |
|---|---|
| **Documento** | Protocolo de alineación |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.1 |
| **Fecha** | 2026-10-15 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial del protocolo (punto cero del proyecto). | Fijar el procedimiento de alineación antes de ver resultados de OE2. |
| 1.1 | 2026-10-15 | Se agrega la cabecera de versión y se usa la terminología estándar en la prosa («ground truth» y «τ»); los identificadores de código y de configuración (`tau`, `tau_grid`) no cambian. No cambia el procedimiento. | Auditoría de gobernanza del 2026-10-15: este protocolo no llevaba versión y mezclaba términos con los avances. |

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

## Procedimiento

1. **Candidatos.** Calcular la similitud coseno de embeddings sobre el par
   `(decision_object, content)` para cada par (predicha, referencia) de decisiones.
   Cualquier par con similitud igual o superior a un umbral τ (`tau` en el código) es un candidato de
   coincidencia.
2. **Restricción uno a uno.** Resolver los candidatos como una asignación uno a uno de peso
   máximo mediante el algoritmo húngaro (`scipy.optimize.linear_sum_assignment`), nunca por
   vecino más cercano de forma voraz. La asignación voraz permitiría que varias extracciones
   reclamaran la misma decisión de referencia, inflando la precisión aparente.
3. **Validación manual.** El protocolo automático se contrasta contra el emparejamiento
   manual en una muestra de al menos 100 pares; la concordancia se reporta
   (`src/afg/evaluation/alignment.py::concordance`).
4. **Sensibilidad.** F1 se reporta como una curva sobre una grilla de τ
   (`config/experiments.toml`, `[alignment].tau_grid`), nunca como un solo punto. Si el
   orden entre condiciones cambia a lo largo de la grilla, eso se declara explícitamente en
   el resultado escrito, no se suaviza eligiendo un τ favorable.

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
