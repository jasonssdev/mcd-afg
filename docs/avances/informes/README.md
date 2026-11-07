# docs/avances/informes/

Los **informes del curso** como documentos vivos: el pre-informe de AFG2 y, más adelante, el
informe final de AFG3. Se arman a partir de los [avances](../README.md) y no los reemplazan:
un informe sintetiza lo que ya está registrado y verificado en los avances, sin copiarlo, y
no calcula ninguna cifra nueva.

| Documento | Contenido |
|---|---|
| [`01-jss-pre-informe.md`](01-jss-pre-informe.md) | Pre-informe de AFG2 en su versión anterior a los experimentos formales (solo resultados de desarrollo); se conserva sin cambios |
| [`02-jss-pre-informe.md`](02-jss-pre-informe.md) | Pre-informe de AFG2 posterior a los experimentos: reporta los resultados formales de OE1 a OE4 (entrega del 2026-11-09), base del informe final de AFG3 |

## Convención de nombres

```
NN-{iniciales}-{nombre}.md
```

La misma que usan los avances y los notebooks. Las iniciales de quien mantiene el documento
están en la tabla de [`../../../CONTRIBUTING.md`](../../../CONTRIBUTING.md) §1. Nunca se
renumera un documento existente.

## Versionado

Cada informe lleva cabecera de versión e historial de cambios, con la misma regla que los
avances:

> Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que altera una decisión, un
> objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar la evidencia que lo
> motivó**. El historial nunca se reescribe: se agrega una fila.

El PDF que se envía en cada fecha de entrega se registra en el historial de versiones del
informe, con la fecha de envío y la versión que se envió. Así, el documento que se entregó
siempre se puede reconstruir, aunque el texto vivo siga cambiando.
