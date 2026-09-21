# notebooks/

Los notebooks son el **registro académico paso a paso** del proyecto: lo que se hizo, lo que
se midió y, sobre todo, **por qué se decidió lo que se decidió**. Están escritos para que un
revisor de la universidad pueda seguir el razonamiento sin leer el código fuente.

> Excepción de idioma declarada: estos notebooks van en **español**, igual que
> `docs/anotacion/manual-anotacion-oe1.md`, porque sus lectores son el equipo y los revisores
> de una tesis en español. El código, la configuración y el resto de `docs/` siguen en inglés.

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
| 03 | `03-jss-anotacion-oe1.ipynb` | Ejecución de la anotación **humana**: acuerdo entre anotadores, kappa, adjudicación, el conjunto de referencia resultante | pendiente |
| 04 | `04-jss-experimento-a.ipynb` | OE2 — calidad de la extracción automática contra la referencia | pendiente |
| 05 | `05-jss-experimento-b.ipynb` | OE3/OE4 — C1 vs C2 vs C3 y atribución del error a su etapa | pendiente |

> **Por qué 01 y 03 están separados.** El 01 contiene etiquetas puestas por una máquina, con
> fines de planificación. El 03 contendrá el conjunto de referencia real, hecho a mano.
> Mezclarlos invitaría a que alguien cite las provisionales como si fueran la referencia.

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
