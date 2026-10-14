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

- `NN` — dos dígitos, el orden de la narrativa del proyecto.
- `{autor}` — iniciales. `jss` = Jason Sepúlveda S.
- `{nombre}` — tema, en minúsculas y con guiones.

Ejemplo: `00-jss-corpus-y-auditoria.ipynb`

## La serie

| | Notebook | Cubre | Estado |
|---|---|---|---|
| 00 | `00-jss-corpus-y-auditoria.ipynb` | Adquisición del corpus, verificación estructural (paso cero), auditoría de datos §5.1, y las decisiones de diseño que la auditoría obligó a tomar | ✅ |
| 01 | `01-jss-viabilidad-e3.ipynb` | Estimación **provisional** de la tasa de positivos del filtro y verificación de las relaciones identificadas a ojo. Decide si el estrato E3 se sostiene | ✅ |
| 02 | `02-jss-transcripciones.ipynb` | Del AMI Meeting Corpus (anotación *stand-off* NXT) a transcripciones legibles y congeladas: decisiones de render, los dos artefactos por reunión, cobertura del corpus y el manifiesto verificable | ✅ |
| 03 | `03-jss-eda.ipynb` | Análisis exploratorio de datos de AFG2 sobre las 14 series: proveniencia, calidad, faltantes, atípicos, relaciones, estructura multivariada y temporal, preguntas dirigidas e implicancias para el modelado. Solo estadísticas agregadas (ADR 0005) | ✅ |
| 04 | `04-jss-anotacion-f1-calibracion.ipynb` | Anotación **humana**, Fase 1: calibración sobre ES2015 y recalibración sobre TS3009 (doble anotación `gm`/`gv`, adjudicación de `jss`). Acuerdo **diagnóstico**, no reportable; vacíos de la guía que reveló | ES2015 ✅; TS3009 pendiente |
| 05 | `05-jss-anotacion-f2-control.ipynb` | Anotación humana, Fase 2: las cuatro series de control con doble anotación. El kappa **reportable** de OE1 | pendiente |
| 06 | `06-jss-anotacion-f3-referencia.ipynb` | Anotación humana, Fase 3: reparto individual y conjunto de referencia final de las 13 series | pendiente |
| 07 | `07-jss-experimento-a.ipynb` | OE2 — calidad de la extracción automática contra la referencia | pendiente |
| 08 | `08-jss-experimento-b.ipynb` | OE3/OE4 — C1 vs C2 vs C3 y atribución del error a su etapa | pendiente |

> **Por qué 01 y 04–06 están separados.** El 01 contiene etiquetas puestas por una máquina, con
> fines de planificación. Los 04–06 contienen la anotación real, hecha a mano, y el conjunto de
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

La capa de cálculo de la auditoría vive en `src/afg/audit/`.

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
  antes de ejecutar cualquier notebook; todos empiezan con una guarda que falla con un
  mensaje claro si falta.
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
