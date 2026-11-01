# Confiabilidad de la referencia humana (OE1)

| | |
|---|---|
| **Documento** | 10 — Confiabilidad de la referencia humana (OE1) |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.0 |
| **Fecha** | 2026-11-01 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-11-01 | Versión inicial. Resultados de confiabilidad de OE1 de las fases 1 y 2. | La Fase 2 quedó completa (cuatro series de control adjudicadas) y ningún documento reportaba aún estos resultados. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## Qué se quiere saber

Todo el experimento se mide contra una referencia hecha por personas: la lista de decisiones
y de relaciones entre ellas. Si dos personas competentes no se ponen de acuerdo sobre esa
referencia, no se puede exigir a una máquina que acierte. Por eso OE1 ([documento 03](03-jss-objetivos.md))
no supone que la referencia es confiable: **mide** cuánto coinciden dos personas.

## Cómo se midió

Dos personas (`gm` y `gv`) anotan por separado, sin conversar sobre casos. Una tercera
(`jss`) resuelve cada desacuerdo y deja escrita la razón; no anota ninguna fila por su cuenta.
El acuerdo se mide con **kappa de Cohen**: la proporción de coincidencias que supera lo que se
esperaría por azar. Cero equivale a coincidir como al azar; uno, a coincidir siempre. Se
calcula **un kappa por pregunta**, sin combinarlos:

- **Existencia:** ¿hay relación entre las dos decisiones?
- **Tipo:** si la hay, ¿de qué clase (`reafirma`, `refina`, `revierte`, `reemplaza`)?
- **Dirección:** ¿cuál decisión revisa a cuál?

El trabajo se hizo en tres fases:

| Fase | Series | Para qué sirve | ¿Se reporta? |
|---|---|---|---|
| 1 | ES2015, TS3009 | Calibrar la guía de anotación antes de tocar las series de evaluación | No: es diagnóstico |
| 2 | ES2016, IS1003, TS3005, ES2008 | Medir la confiabilidad sobre series de control | **Sí** |
| 3 | Las series restantes | Anotación individual para completar la referencia | No hay kappa: anota una sola persona |

La Fase 1 no se reporta porque se hizo sobre series de desarrollo, con la guía todavía en
ajuste: su único fin era comprobar que las dos personas entendían lo mismo. Reportar ese
primer kappa mediría la guía sin pulir y no la referencia final.

## Resultados de la Fase 2

Los kappas se calcularon juntando los pares de las cuatro series, porque cada serie aporta
entre 4 y 14 pares y un solo par distinto mueve mucho un kappa por serie.

| Pregunta | Pares | Desacuerdos | Acuerdo simple | Kappa |
|---|---|---|---|---|
| Existencia | 37 | 4 | 89,2 % | **0,783** |
| Tipo | 18 | 5 | 72,2 % | **0,554** |
| Dirección | 37 | 0 | 100 % | Indefinido |

**Cómo leerlo.**

- **Existencia (0,783).** Las dos personas casi siempre coinciden en *si* dos decisiones están
  enlazadas. En la escala de lectura de Landis y Koch, que es solo una ayuda, es un acuerdo sustancial.
- **Tipo (0,554).** Coinciden menos en *qué clase* de enlace es. La dificultad está en la
  frontera entre `reafirma`, `refina`, `revierte` y `reemplaza`, no en detectar el vínculo.
  En esa escala es un acuerdo moderado.
- **Dirección (indefinido).** En los 37 pares ambas personas marcaron la misma dirección, con
  un solo valor posible. El kappa no existe cuando no hay variación: no es un fallo de cálculo.
  El acuerdo fue total, pero no hay un kappa que reportar.

**Relación con H3.** H3 supone que, para una máquina, acertar la *dirección* de una relación es
más difícil que detectar que existe. Para las personas, la dirección no fue problema. Lo que
resultó difícil fue el *tipo*, así que la exactitud de tipo de cualquier sistema debe leerse
sabiendo que la referencia misma es solo moderadamente estable en ese eje.

**Contraste con el antecedente.** Fernández et al. (2008) obtuvieron un kappa negativo, peor
que el azar, al comparar dos anotaciones de decisiones sobre este mismo corpus
([documento 01](01-jss-problema.md)). Los 0,783 de existencia no son comparables punto a punto,
porque la pregunta y el procedimiento difieren, pero indican que con una guía escrita,
calibración previa y adjudicación, dos personas sí pueden coincidir sobre este material.

## Acuerdo sobre qué es una decisión (diagnóstico)

También se comparó si las dos personas coinciden en qué frases son decisiones. Esa cifra
(Tarea A) es solo diagnóstica y no se reporta como confiabilidad (manual de anotación, §6).
En la Fase 2 el acuerdo simple fue de 81,1 % (111 filas, 21 desacuerdos), pero el kappa
quedó en −0,054, cerca de cero. No significa que coincidan como al azar: casi todas las frases
son `decision` para ambas personas, y cuando una etiqueta domina así el azar ya explica casi todo
el acuerdo (paradoja de la prevalencia). Lo informativo es dónde difieren: en el umbral
entre decisión y meta o aspiración (manual §2a), un criterio que la guía ya cubre. Por eso la
guía no necesitó cambios después de la Fase 1.

## Frente a los objetivos

Los [documentos 03](03-jss-objetivos.md) y [08](08-jss-metricas-y-criterio-de-exito.md) fijan para OE1:

| Criterio | Resultado |
|---|---|
| Doble anotación independiente de al menos el 25 % de la evaluación | Cumplido: 4 de 11 series (36,4 %) |
| Kappa reportado por separado en existencia, tipo y dirección | Existencia y tipo reportados; dirección **indefinida** por falta de variación |
| Adjudicación documentada para todo desacuerdo | Cumplido en las cuatro series de control |
| Umbral de kappa | **No hay, por diseño**: los valores se reportan como salgan |

La única diferencia con lo previsto es la dirección: el criterio pedía un kappa en los tres
niveles y en uno no existe. Se reporta como indefinido, con su acuerdo simple del 100 %.

## Límites

- **Muestra pequeña.** Los kappas descansan en 37 pares (existencia) y 18 (tipo). Son la mejor
  estimación disponible, no una medida precisa: un par distinto cambia el valor.
- **Una sola persona adjudica.** Que `jss` coincida más con una de las dos personas no mide la
  calidad de ninguna; mide la distancia entre dos lecturas y la tercera.
- **Solo agregados.** Las series de control son de evaluación: se reportan conteos y kappas,
  no frases ni casos (ADR 0005).

## Estado

Estas cifras son **finales para OE1**: la Fase 3 no agrega ningún kappa. Lo que falta de la
anotación (la Fase 3 y la muestra de recall de la Tarea C de TS3005, issue #194) no cambia
estos valores.

## Fuentes

| Contenido | Fuente |
|---|---|
| Fase 1: método y conclusiones de la calibración | [`notebooks/04-jss-anotacion-f1-calibracion.ipynb`](../../notebooks/04-jss-anotacion-f1-calibracion.ipynb) |
| Fase 2: acuerdo por serie, kappa agrupado (§6) y límites (§7) | [`notebooks/18-jss-anotacion-f2-adjudicacion.ipynb`](../../notebooks/18-jss-anotacion-f2-adjudicacion.ipynb) |
| Kappa agrupado, total y por fase | [`reports/tables/agreement-pooled.csv`](../../reports/tables/agreement-pooled.csv) |
| Diseño de las fases | [`docs/anotacion/asignacion/README.md`](../anotacion/asignacion/README.md) |
| Antecedente de Fernández et al. (2008) | [documento 01](01-jss-problema.md) y [documento 04](04-jss-bibliografia.md) |
