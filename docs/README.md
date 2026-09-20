# docs/

- **`propuesta.md`** — la propuesta de tesis completa, tal como se escribió en AFG1. Se cita
  por sección (§1.4, §5.4, ...) desde el código, la configuración y los avances. No se
  edita: las revisiones pendientes están en `BACKLOG.md` (P7).

- **`anotacion/`** — **el trabajo humano.** Punto de entrada para quien anota: quién hace qué,
  en qué orden, con qué CSV y cuánto toma (`README.md`); la definición del constructo
  (`annotation-guidelines.md`); y el manual operativo paso a paso con un ejemplo real
  (`manual-anotacion-oe1.md`).
- **`protocols/`** — protocolos de la máquina, congelados antes de mirar resultados.
  - `alignment.md` — el protocolo de alineamiento de la sección 5.4 de la propuesta.
- **`BACKLOG.md`** — trabajo pendiente en orden de dependencia, más las decisiones ya
  tomadas (con su evidencia) para que no se reabran en silencio.
- **`decisions/`** — registros de decisiones de arquitectura (ADR) de este arnés de
  evaluación en sí (no de las decisiones de investigación de la tesis, que viven en
  `propuesta.md` y en `BACKLOG.md`). Convención de
  nombres: **`NNNN-adr-{nombre}.md`**, secuencia de cuatro dígitos, para que el directorio
  se ordene en el orden en que se tomaron las decisiones.
- **`avances/`** — los **documentos vivos** del proyecto (en español): problema, fuente de
  datos, objetivos, bibliografía, ética, metodología. Cada uno lleva su propio encabezado
  de versión y su historial de cambios, porque cambian a medida que avanza el trabajo. Se
  arman a partir de los notebooks y del backlog; ninguna cifra se calcula ahí.
- **`entregables/`** — lo que efectivamente se **entrega** (en español): guiones de video,
  contenido de presentación, informes enviados. Se construyen a partir de `avances/`,
  congelados en el momento del envío.

Todo lo que hay bajo `docs/` está escrito en español.

Ver `README.md` en la raíz del proyecto para la pregunta de investigación, las condiciones
y los objetivos generales; este directorio documenta *cómo se construye y se ejecuta el
arnés*, no *qué argumenta la tesis*.
