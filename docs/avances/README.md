# docs/avances/

Los **documentos vivos** del proyecto: el problema, la fuente de datos, los objetivos, la
bibliografía, los aspectos éticos y la metodología.

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
