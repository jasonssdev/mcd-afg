# docs/entregables/

Lo que **efectivamente se entrega** al curso: guiones de video, contenido de presentaciones,
informes enviados, y cualquier documento que salga del repositorio hacia la universidad.

## La diferencia con `avances/`

| | [`../avances/`](../avances/) | `entregables/` (aquí) |
|---|---|---|
| **Qué es** | El contenido del proyecto | Lo que se envía |
| **Cambia** | Sí, a medida que el proyecto avanza | No: se congela al entregar |
| **Versionado** | Cabecera de versión + historial de cambios | Fecha de entrega fija |
| **Ejemplos** | Problema, objetivos, metodología | Guion de video, presentación, informe |

Un entregable **se construye a partir de los avances**, no al revés. Si al preparar una
presentación descubres que un objetivo está mal redactado, el arreglo va en
[`../avances/03-jss-objetivos.md`](../avances/03-jss-objetivos.md) —subiendo su versión— y
recién después se refleja aquí.

## La regla que hace que esto funcione

**Ninguna cifra se calcula en un entregable.** Todo número que aparezca en un guion o una
presentación tiene que existir en un notebook que lo reproduzca
([`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) §7.1). Un entregable que cita una cifra que
ningún notebook respalda es una afirmación sin evidencia, y en una defensa eso se nota.

Cuando un entregable se envía, la cifra que contiene queda fija. Si después esa cifra se
corrige, hay que saber dónde quedó publicada la versión vieja — por eso los entregables se
conservan aquí en vez de sobrescribirse.

## Convención de nombres

```
NN-{iniciales}-{nombre}.md
```

Las iniciales de cada autor están en la tabla de
[`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) §1. Conviene que el nombre diga qué es y
para cuándo, por ejemplo `01-jss-guion-video-semana8.md`.

Cada entregable debería abrir declarando: **a qué entrega corresponde, en qué fecha se envió,
y de qué versión de los avances se construyó.** Eso último es lo que permite, meses después,
saber qué sabíamos cuando lo entregamos.

## Estado

| Entregable | Archivo | Estado |
|---|---|---|
| Video de avance #1 (semana 2) | [`00-jss-guion-video-semana2.md`](00-jss-guion-video-semana2.md) | Enviado; congelado. Falta registrar la fecha exacta |
| Video de avance #2 (semana 3) | [`01-jss-guion-video-semana3.md`](01-jss-guion-video-semana3.md) | Enviado; congelado. Falta registrar la fecha exacta |
| Presentación formal del problema (semana 4) | [`02-jss-informe-semana4.md`](02-jss-informe-semana4.md) | Enviado; congelado. Falta registrar la fecha exacta |
| Video de avance #3 (semana 7): propuesta metodológica + datos disponibles | [`03-jss-guion-video-semana7.md`](03-jss-guion-video-semana7.md) | Guion listo; falta grabar y registrar la fecha de envío |

Pendiente inmediato: el guion de la **presentación final** (semana 8), con las cuatro secciones
que exige la rúbrica: contextualización y problema, al menos dos trabajos relacionados,
propuesta metodológica por fases, y alcances éticos con partes involucradas. Se construye
desde los avances 01, 04, 06 y 05.
