# docs/

- **`propuesta.md`** — la propuesta de tesis completa, tal como se escribió en AFG1. Se cita
  por sección (§1.4, §5.4, ...) desde el código, la configuración y los avances. No se
  edita: las revisiones pendientes se siguen en el issue #20.

- **`anotacion/`** — **el trabajo humano.** Punto de entrada para quien anota: quién hace qué,
  en qué orden, con qué CSV y cuánto toma (`README.md`); la definición del constructo
  (`annotation-guidelines.md`); y el manual operativo paso a paso con un ejemplo real
  (`manual-anotacion-oe1.md`).
- **`protocols/`** — protocolos de la máquina, congelados antes de mirar resultados.
  - `alignment.md` — el protocolo de alineamiento de la sección 5.4 de la propuesta.
- **`decisions/`** — el registro de decisiones, en dos formatos: los **ADR** del arnés de
  evaluación en sí (un archivo por decisión, convención de nombres
  **`NNNN-adr-{nombre}.md`**, secuencia de cuatro dígitos para que el directorio se ordene
  en el orden en que se tomaron) y las **entradas D**, decisiones de diseño o de método con
  su evidencia, en la tabla de [`decisions/README.md`](decisions/README.md). Es
  *append-only*: nada se edita en su sitio; una decisión revisada se reemplaza con otra
  nueva. Las decisiones de investigación de la tesis viven en `propuesta.md`. El trabajo
  pendiente vive en issues de GitHub, no aquí.
- **`avances/`** — los **documentos vivos** del proyecto (en español): problema, fuente de
  datos, objetivos, bibliografía, ética, metodología. Cada uno lleva su propio encabezado
  de versión y su historial de cambios, porque cambian a medida que avanza el trabajo. Se
  arman a partir de los notebooks y del registro de decisiones; ninguna cifra se calcula ahí.
- **`entregables/`** — lo que efectivamente se **entrega** (en español): guiones de video,
  contenido de presentación, informes enviados. Se construyen a partir de `avances/`,
  congelados en el momento del envío.

Todo lo que hay bajo `docs/` está escrito en español.

Ver `README.md` en la raíz del proyecto para la pregunta de investigación, las condiciones
y los objetivos generales; este directorio documenta *cómo se construye y se ejecuta el
arnés*, no *qué argumenta la tesis*.

## Los cuatro N (no confundirlos)

El proyecto maneja varias cantidades que se parecen y no son lo mismo. Confundirlas es la
forma más fácil de escribir una cifra equivocada, así que se listan juntas:

| Nivel | N | Estado |
|---|---|---|
| Reuniones | **56** (14 series × 4) | medido, fijo |
| Frases `DECISIONS` | **343** | medido, fijo |
| Registros §5.2 tras la Tarea A | **~330** | **estimado**; el piloto dio ~96 % de rendimiento porque las compuestas se desdoblan |
| Pares entre reuniones | **3.071** | medido, fijo |
| Pares candidatos | **92** (0,30 + ≥2) | medido |
| **Relaciones reales** | **DESCONOCIDO** | **el número que decide si E3 vive** |
| Preguntas del banco | **≥100** (25 × 4) | **no existe** |

Reparto por el split: desarrollo 77 decisiones / 11 candidatos · evaluación 266 / 81.

> **Dos series aportan casi nada a E3:** IS1006 e IS1009 dan 1 candidato cada una.
> Siguen aportando decisiones a OE2.

Las cifras medidas se verifican en [`../config/corpus.toml`](../config/corpus.toml) sección
`[oe1]` y en [`avances/02-jss-fuente-de-datos.md`](avances/02-jss-fuente-de-datos.md) §4.3
y §4.4; el rendimiento del piloto que sustenta la estimación de ~330 está en
[`decisions/README.md`](decisions/README.md).
