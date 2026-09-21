# Contribuir a mcd-afg

Guía práctica para colaborar en este proyecto: quién hace qué, el flujo de
trabajo y las convenciones de fondo (naming, idioma, alcance
desarrollo/evaluación).

---

## 1. Quién es quién

| Iniciales | Nombre | GitHub | Rol en el proyecto |
|---|---|---|---|
| `jss` | Jason Sepúlveda S. | [`jasonssdev`](https://github.com/jasonssdev) | Mantenedor del repositorio; instrumento OpenKOS; adjudica los desacuerdos de la doble anotación de OE1 |
| `gv` | Germán Vega | [`Vega-German`](https://github.com/Vega-German) | Anotador OE1 (Tareas A a D); valida el banco de preguntas |
| `gm` | Gustavo Martínez | [`gmartinezbMCD`](https://github.com/gmartinezbMCD) | Anotador OE1 (Tareas A a D); escribe el banco de preguntas |

El reparto sigue dos reglas del diseño: quien adjudica los desacuerdos de la
doble anotación no anota, y quien escribe el banco de preguntas no lo valida ni
ejecuta los sistemas. Así cada artefacto lo revisa alguien que no lo produjo.

## 2. Flujo: fork → rama → commit → push → PR

Los requisitos previos (git, uv, cuenta de GitHub) y la instalación completa
están en [`README.md`](README.md), sección "Tu primer día, paso a paso". Resumen del flujo:

1. **Fork** del repositorio a tu cuenta de GitHub (botón **Fork** en
   [github.com/jasonssdev/mcd-afg](https://github.com/jasonssdev/mcd-afg)).
   Es obligatorio: nadie clona ni escribe sobre el repositorio original.
2. **Clona tu fork**, no el original:
   `git clone git@github.com:<tu-usuario>/mcd-afg.git`
3. Agrega el original como `upstream`:
   `git remote add upstream https://github.com/jasonssdev/mcd-afg.git`
4. Crea una rama a partir de `main` actualizado:
   `git fetch upstream && git checkout -b tipo/descripcion-corta upstream/main`
5. Haz commits pequeños y descriptivos.
6. Sube la rama a tu fork: `git push -u origin tipo/descripcion-corta`
7. Abre un pull request desde tu fork contra `main` del repositorio original.

Nadie hace push directo a `main`, ni siquiera para cambios triviales.

### Nombres de rama

```
tipo/descripcion-corta
```

| Tipo | Para qué |
|---|---|
| `feat` | Funcionalidad nueva |
| `fix` | Corrección de un error |
| `docs` | Documentación (`docs/`, `README.md`, notebooks como narrativa) |
| `exp` | Trabajo exploratorio o experimental |
| `data` | Cambios relacionados con datos, corpus o esquemas |

Ejemplo: `fix/blocker-min-overlap-tokens`.

## 3. Revisión

**Nada llega a `main` sin pasar por revisión.**
[@jasonssdev](https://github.com/jasonssdev) es el CODEOWNER responsable de la
integración a `main` y quien hace el merge — ver
[`.github/CODEOWNERS`](.github/CODEOWNERS): revisa **toda** PR que entre a
`main`, venga de quien venga, incluidas las suyas propias.

Las PR del resto del equipo las revisa el mantenedor. Las PR del mantenedor las
revisa él mismo, y eso es deliberado: la responsabilidad de lo que entra a `main`
es suya de todos modos, así que exigir una firma ajena añadiría una espera sin
añadir una mirada. Cualquier integrante puede revisar y comentar cualquier PR;
lo que esta regla fija es quién no puede faltar, no quién sobra.

### Esto no depende de la buena voluntad de nadie

La rama `main` está protegida en GitHub, así que la regla la aplica la máquina:

| Regla | Efecto |
|---|---|
| 1 aprobación requerida | Una PR sin aprobar no se puede mergear |
| Revisión de CODEOWNER obligatoria | No basta cualquier aprobación: tiene que ser la del mantenedor, porque [`.github/CODEOWNERS`](.github/CODEOWNERS) le asigna todo el repositorio |
| Aprobaciones obsoletas descartadas | Si empujas un commit nuevo, la aprobación anterior caduca y hay que revisar otra vez |
| Conversaciones resueltas | Un comentario de revisión abierto bloquea el merge |
| Sin force push ni borrado de `main` | Sin excepciones, tampoco para el mantenedor |

La protección **no** se aplica a administradores, y eso es deliberado: GitHub
prohíbe aprobar tu propia PR, así que si le aplicara también al mantenedor
quedaría bloqueado en su propio repositorio. En la práctica significa que el
resto del equipo no puede integrar nada sin su aprobación, y que él integra lo
suyo bajo su propia responsabilidad.

El permiso que necesita un colaborador es **Write**. `Maintain` y `Admin`
saltan la protección, así que no se reparten.

## 4. Commits

[Conventional commits](https://www.conventionalcommits.org/), en español o en
inglés — el que prefieras, pero sé consistente dentro de un mismo PR.

```
tipo(alcance opcional): descripción breve en modo imperativo
```

Ejemplos: `fix(blocker): exigir |A∩B| >= 2`, `docs: actualizar BACKLOG con D9`.

### Autoría

Cada aporte lo firma la cuenta de git de la persona que lo hizo. No se agregan
coautores automáticos, banners de herramientas ni notas de "generado por" en
commits, código, documentos ni descripciones de PR. Quien firma un aporte es
responsable de su contenido.

## 5. Configuración local

Después de clonar tu fork:

```bash
uv sync --group dev --group notebooks   # instala Python 3.13 si falta y todas las dependencias
uv run afg --help                       # verifica el CLI
uv run pytest -q                        # verifica los tests
```

Si vas a trabajar con el corpus, descárgalo aparte (está en `.gitignore`):

```bash
uv run afg corpus download
```

## 6. Antes de abrir un PR

Ejecuta y confirma que pasan:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src/afg
```

Si tu cambio tocó un notebook, **re-ejecútalo de punta a punta** antes de
subirlo — un notebook con outputs obsoletos es peor que uno sin outputs
(ver [`notebooks/README.md`](notebooks/README.md)):

```bash
uv run jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=900 notebooks/<archivo>.ipynb
```

El [template de PR](.github/pull_request_template.md) pide el resultado de
cada uno de estos comandos, no solo que marques una casilla.

## 7. Convenciones

El resto de la documentación cita estas reglas como `CONTRIBUTING.md §7.N`.

### 7.1 Todo número viene de `src/afg/` y se lee desde un notebook

Si algo produjo una cifra, una decisión o un entregable, tiene que ser
reproducible y legible desde un notebook en [`notebooks/`](notebooks/). Código
sin notebook no es un registro: nadie en la universidad va a leer
`src/afg/audit/evidence.py` para saber cuántas decisiones tiene el corpus. Una
celda de notebook que calcula algo es una fuente de verdad paralela sin test —
en este proyecto una extrapolación hecha fuera del paquete estimó ~170
candidatos; correr la función real sobre las 14 series dio 712 (solo con el
coeficiente de solapamiento); y esa cifra solo bajó a la final de 92 después
de una decisión de diseño, exigir además `|A∩B| >= 2` (ver `docs/BACKLOG.md`,
decisión D9). Correr el código real no bastaba: llegar a 92 exigió además
decidir el filtro.

| Capa | Contiene | Regla |
|---|---|---|
| `src/afg/` | Todo el cómputo | Con test. Fuente única de verdad para cada cifra |
| `notebooks/` | La narrativa | Importa, llama, grafica, explica. **No define lógica** |
| `docs/` | Decisiones y protocolos | ADRs, backlog, manual de anotación |

Después de implementar algo en `src/afg/`, revisa si la serie de notebooks
sigue contando la historia completa. Si no, el trabajo no está terminado.

### 7.2 Convenciones de nombres

| Artefacto | Patrón | Ejemplo |
|---|---|---|
| Notebooks | `NN-{iniciales}-{nombre}.ipynb` | `01-jss-viabilidad-e3.ipynb` |
| Documentos vivos (`docs/avances/`) | `NN-{iniciales}-{nombre}.md` | `03-jss-objetivos.md` |
| Entregables (`docs/entregables/`) | `NN-{iniciales}-{nombre}.md` | `01-jss-guion-video-semana8.md` |
| ADRs | `NNNN-adr-{nombre}.md` | `0005-adr-development-evaluation-split.md` |
| Ramas | `{tipo}/{descripcion-corta}` | `feat/blocker-min-overlap` |

`NN` son dos dígitos y refleja el orden de la narrativa del proyecto, no la
fecha de creación. `NNNN` para ADRs es de cuatro dígitos y estrictamente
secuencial. `{iniciales}` identifica al autor (ver §1). `{nombre}` va en
minúsculas, separado por guiones, sin tildes. **Nunca renumerar un archivo
existente**: el número es una referencia que otros documentos citan; se
agrega uno nuevo en vez de renumerar.

### 7.3 Notebooks

- Naming: ver §7.2.
- Escritos **en español, en voz impersonal o en primera persona del plural**
  (nunca en singular: el proyecto es de un equipo), académicos pero simples,
  para un revisor que no programa.
- **Versionados CON sus outputs.** Son entregables académicos; un revisor
  debe poder leer los resultados sin ejecutar nada ni tener el corpus. Los
  outputs son el registro.
- Por eso: **re-ejecutar antes de entregar**. Un notebook con outputs
  obsoletos es peor que uno sin outputs, porque miente con autoridad.
  ```bash
  uv run jupyter nbconvert --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=900 notebooks/<archivo>.ipynb
  ```
- Los errores y los caminos equivocados se dejan escritos, no se ocultan: el
  razonamiento es parte del aporte.

### 7.4 Idioma

| Artefacto | Idioma |
|---|---|
| Código, identificadores, comentarios, docstrings | Inglés |
| `config/` (comentarios) | Inglés |
| `README.md`, `CONTRIBUTING.md`, `docs/` (incluidos ADRs y protocolos) | Español |
| Notebooks | Español |
| Plantillas de issues y PR | Español |

Todo lo que lee una persona va en español: README, CONTRIBUTING, `docs/`
completo, notebooks y plantillas. Todo lo que lee una máquina o forma parte
del código va en inglés: código, identificadores, comentarios y comentarios de
configuración. Las etiquetas de anotación (`introduce`, `reafirma`, `refina`,
`revierte`, `reemplaza`, `no_relacionada`) se mantienen en español dentro del
código: son el conjunto de etiquetas que define la tesis. La propuesta
(`docs/propuesta.md`) es el texto original y no se edita; sus revisiones
pendientes se anotan en `docs/BACKLOG.md` (P7).

### 7.5 Cifras

- **Nunca citar una cifra que no se ha medido sobre los datos reales.** No
  extrapolar desde una muestra pequeña sin decirlo y sin reportar un
  intervalo.
- La verdad medida vive en **tests**, no hardcodeada en código de producción.
- Cuando una cifra se corrige, se corrige **en todas partes** — un backlog con
  dos respuestas a la misma pregunta es peor que ninguno.

### 7.6 Las etiquetas del conjunto de referencia las pone un humano

El conjunto de referencia (OE1) es el primer aporte de la tesis y la
definición de la condición C3 ("la misma representación sin errores de
extracción"). Si un modelo produjera esas etiquetas, C3 tendría errores de
extracción por construcción, y la brecha C2 − C3 —que es todo OE4— dejaría de
medir nada.

Las máquinas pueden extraer candidatos, resolver evidencia, proponer qué pares
mirar, marcar señales de revisión y calcular acuerdo. No pueden decidir si
algo es una decisión, ni qué relación existe entre dos decisiones. Las
sugerencias de una máquina van en una columna aparte (`machine_flags`), nunca
en `status`.

### 7.7 Desarrollo vs evaluación

Ver
[`docs/decisions/0005-adr-development-evaluation-split.md`](docs/decisions/0005-adr-development-evaluation-split.md).
No es un split train/test — nada se entrena. Separa los datos usados para
**tomar decisiones** de los datos usados para **reportar resultados**.

- **Análisis estructural** (conteos, cobertura, distribuciones, roles,
  duraciones): cualquier serie.
- **Análisis de contenido** (leer texto de decisiones, pares candidatos,
  transcripciones): **solo desarrollo** (ES2015, IS1004, TS3009). Leer
  contenido de evaluación lo contamina, incluso si es para reportarlo al
  equipo.

Todo lo ajustado sobre desarrollo debe quedar **congelado antes de tocar
evaluación**.

### 7.8 El corpus

- `data/raw/` está en `.gitignore`. `uv run afg corpus download` lo descarga
  (CC BY 4.0).
- **Nunca afirmar un hecho de AMI sin verificarlo contra el corpus
  extraído.** Los supuestos no verificados llevan
  `# ASSUMPTION (verify at paso cero):` y se resuelven, no se dejan pudrir.
- No confiar en los resúmenes abstractivos. Son anotación humana y contienen
  al menos una decisión que la transcripción contradice (ver el ejemplo
  trabajado en
  [`docs/anotacion/manual-anotacion-oe1.md`](docs/anotacion/manual-anotacion-oe1.md)
  §3).

### 7.9 Colaboración: avances y entregables

- Una PR que cambia una cifra publicada debe decir **dónde más aparece esa
  cifra** y actualizar cada lugar (§7.5).
- Una PR que agrega o cambia cómputo debe decir **qué notebook lo cubre**
  (§7.1).
- El backlog de tareas vive en **issues de GitHub**;
  [`docs/BACKLOG.md`](docs/BACKLOG.md) es el registro de decisiones tomadas y
  su evidencia, no una lista de tareas.
- **`docs/avances/` cambia; `docs/entregables/` se congela.** Los documentos
  vivos (problema, objetivos, metodología...) se versionan y actualizan a
  medida que el proyecto avanza. Lo que efectivamente se entrega —guiones de
  video, presentaciones, informes— se construye *desde* ellos y se conserva
  tal como se envió, para que una cifra corregida después se pueda trazar a
  dónde se publicó.

### 7.10 Comandos

```bash
uv sync --group dev --group notebooks   # setup
uv run pytest -q                        # tests
uv run ruff check . && uv run mypy src/afg
uv run afg --help                       # el CLI
```

Ruff también revisa las celdas de los notebooks. `make check` corre lint,
typecheck y tests juntos.
