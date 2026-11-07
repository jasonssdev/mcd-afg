# docs/avances/

Los **documentos vivos** del proyecto: el problema, la fuente de datos, los objetivos, la
bibliografía, los aspectos éticos, la metodología, el análisis exploratorio, las métricas, los
modelos y los resultados con sus conclusiones.

> **Por qué "avances" y no "entregables".** Estos documentos **cambian a medida que el
> proyecto avanza**. No son lo que se entrega: son el contenido del que se construye lo que
> se entrega. Lo que efectivamente se envía al curso —guiones de video, presentaciones,
> informes— vive en [`../entregables/`](../entregables/) y se congela al momento de entregar.

| Documento | Contenido |
|---|---|
| [`01-jss-problema.md`](01-jss-problema.md) | Definición del problema y el vacío que aborda |
| [`02-jss-fuente-de-datos.md`](02-jss-fuente-de-datos.md) | El corpus AMI, su auditoría y los riesgos declarados |
| [`03-jss-objetivos.md`](03-jss-objetivos.md) | Objetivo general, OE1–OE4 e hipótesis |
| [`04-jss-bibliografia.md`](04-jss-bibliografia.md) | Referencias en APA 7, con los preprints marcados |
| [`05-jss-aspectos-eticos.md`](05-jss-aspectos-eticos.md) | Tres principios, en profundidad |
| [`06-jss-metodologia.md`](06-jss-metodologia.md) | Los ocho pasos, con el diseño real del proyecto |
| [`07-jss-analisis-exploratorio.md`](07-jss-analisis-exploratorio.md) | El análisis exploratorio de datos de AFG2, con sus figuras e interpretación |
| [`08-jss-metricas-y-criterio-de-exito.md`](08-jss-metricas-y-criterio-de-exito.md) | Qué se mide, sobre qué, con qué umbral, y cómo se decide si el experimento tuvo éxito |
| [`09-jss-modelos-y-justificacion.md`](09-jss-modelos-y-justificacion.md) | Qué es «el modelo» en una tesis sin entrenamiento: los *pipelines* comparados, los modelos por rol, la búsqueda de parámetros, la línea base y las limitaciones |
| [`10-jss-confiabilidad-de-la-referencia.md`](10-jss-confiabilidad-de-la-referencia.md) | Resultados de confiabilidad de OE1 (fases 1 y 2): kappa de existencia, tipo y dirección, y su lectura; composición final de la referencia (14 series, 358 decisiones, 46 relaciones) tras la Fase 3 |
| [`11-jss-resultados-experimento-a.md`](11-jss-resultados-experimento-a.md) | Resultados del Experimento A (OE2): precisión, recall y F1 de decisiones, relaciones, validación manual de la alineación, límites y costo en tiempo |
| [`12-jss-resultados-experimento-b.md`](12-jss-resultados-experimento-b.md) | Resultados del Experimento B (OE3 y OE4): corrección por condición y estrato, D16, H2, C0 como referencia, validez del juez, etapa del fallo de C2, citas y abstención, límites |
| [`13-jss-conclusiones.md`](13-jss-conclusiones.md) | Conclusiones del proyecto: la respuesta a cada objetivo (OE1 a OE4) y a cada hipótesis (D16 y H1 a H4), qué significan los resultados, costos y punto de equilibrio, implicación práctica, límites y trabajo futuro |
| [`informes/`](informes/) | Los informes del curso como documentos vivos (pre-informe de AFG2 y, después, informe final de AFG3), armados a partir de estos avances |

## De dónde sale el contenido

Un documento de esta carpeta **no se redacta desde cero**. Se arma a partir de lo que ya está
registrado y verificado:

| Fuente | Qué aporta |
|---|---|
| [`../../notebooks/`](../../notebooks/) | Las cifras y los gráficos, ya ejecutados |
| [`../decisions/README.md`](../decisions/README.md) | Las decisiones tomadas y su evidencia |
| [`../decisions/`](../decisions/) | El razonamiento largo de cada decisión, en los ADR |
| La plataforma del curso | La rúbrica y el formato de cada entrega |

**Ninguna cifra se calcula aquí.** Si aparece un número, tiene que existir en un notebook que
lo produzca — es la regla de [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) §7.1. Un
documento que cita una cifra que ningún notebook reproduce es una afirmación sin respaldo.

## Versionado

Cada documento lleva cabecera de versión e historial de cambios. La regla, escrita en cada
uno:

> Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que altera una decisión, un
> objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar la evidencia que lo
> motivó**. El historial nunca se reescribe: se agrega una fila.

Lo que importa de un cambio mayor no es *qué* cambió, sino **qué dato obligó a cambiarlo**.

## Convención de nombres

```
NN-{iniciales}-{nombre}.md
```

Igual que los notebooks, para que el orden del proyecto se lea igual en ambos sitios. Las
iniciales de cada autor están en la tabla de [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md)
§1. **Nunca renumerar un documento existente**: el número es una referencia que otros
documentos citan.
