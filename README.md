# mcd-afg

**Evaluación experimental de la extracción automática y la representación persistente de
decisiones organizacionales, frente a Recuperación Aumentada (RAG).**

Actividad Final de Graduación · Magíster en Ciencia de Datos · Pontificia Universidad Católica

Este README es la puerta de entrada al repositorio. Está escrito para alguien que lo ve por
primera vez: explica qué investiga el proyecto, cómo instalarlo, qué leer y en qué orden, qué
hay en cada carpeta y cómo empezar a trabajar.

**Índice**

1. [Qué investiga este proyecto](#1-qué-investiga-este-proyecto)
2. [Equipo y roles](#2-equipo-y-roles)
3. [Tu primer día, paso a paso](#3-tu-primer-día-paso-a-paso)
4. [Mapa del repositorio: qué hay y qué revisar](#4-mapa-del-repositorio-qué-hay-y-qué-revisar)
5. [Plan por curso](#5-plan-por-curso)
6. [Comandos del proyecto](#6-comandos-del-proyecto)
7. [Cómo contribuir](#7-cómo-contribuir)
8. [Estado](#8-estado)
9. [Datos y licencia](#9-datos-y-licencia)

---

## 1. Qué investiga este proyecto

Las organizaciones pierden sus decisiones. No porque no queden registradas —hoy casi toda
reunión se transcribe— sino porque quedan como **texto conversacional**, donde una decisión no
es una entidad recuperable sino un pasaje difuso repartido entre varios turnos de habla.

El problema se agrava cuando la decisión **cambia**: un equipo decide algo en octubre, lo
matiza en noviembre y lo revierte en diciembre. Las tres reuniones quedan transcritas; ninguna
contiene el hecho más importante, que es la **relación** entre ellas.

Este proyecto mide, sobre el [AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/corpus/),
tres cosas que hoy se confunden:

| | Condición | Rol en el experimento |
|---|---|---|
| **C1** | RAG documental sobre las transcripciones | **Piso** — la práctica actual |
| **C2** | Base estructurada construida automáticamente | **La propuesta bajo evaluación** |
| **C3** | Base estructurada desde anotación humana | **Referencia superior** |

Los cuatro objetivos específicos, en una línea cada uno:

| | Objetivo | Qué produce |
|---|---|---|
| **OE1** | Construir un conjunto de referencia de decisiones con sus relaciones entre reuniones, anotado por personas | Los CSV anotados y el kappa entre anotadores |
| **OE2** | Medir la calidad de la extracción automática contra esa referencia | Precisión, cobertura y F1 |
| **OE3** | Comparar C1, C2 y C3 sobre un mismo banco de preguntas | Corrección, soporte de evidencia, costo amortizado |
| **OE4** | Atribuir cada error de C2 a su etapa de origen: extracción, recuperación o síntesis | La proporción de errores que vienen de la extracción |

La propuesta completa está en [`docs/propuesta.md`](docs/propuesta.md); es la referencia del
proyecto y se cita por sección. Varias decisiones posteriores la contradicen porque la
auditoría de datos lo obligó; todas están registradas con su evidencia en
[`docs/BACKLOG.md`](docs/BACKLOG.md).

> **Este repositorio no es el motor.** El motor de compilación es
> [OpenKOS](https://github.com/jasonssdev/openkos), desarrollado aparte. Aquí vive el
> **harness de evaluación**: la construcción del conjunto de referencia y la medición.

---

## 2. Equipo y roles

| Iniciales | Nombre | Rol en el proyecto |
|---|---|---|
| `jss` | Jason Sepúlveda S. | Mantenedor del repositorio; instrumento OpenKOS; adjudica los desacuerdos de la doble anotación de OE1 |
| `gv` | Germán Vega | Anotador OE1 (Tareas A a D); valida el banco de preguntas |
| `gm` | Gustavo Martínez | Anotador OE1 (Tareas A a D); escribe el banco de preguntas |

El reparto sigue dos reglas del diseño: quien adjudica los desacuerdos de la doble anotación
no anota, y quien escribe el banco de preguntas no lo valida ni ejecuta los sistemas. Así cada
artefacto lo revisa alguien que no lo produjo. Las iniciales identifican al autor de cada
notebook y documento (`03-jss-objetivos.md`, por ejemplo).

---

## 3. Tu primer día, paso a paso

### 3.1 Requisitos previos

| Herramienta | Para qué | Cómo instalarla |
|---|---|---|
| **git** | Control de versiones | macOS: `xcode-select --install` · Linux: `sudo apt install git` · Windows: [git-scm.com](https://git-scm.com/downloads) |
| **uv** | Entorno, dependencias y Python | macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh \| sh` · Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` · [Guía oficial](https://docs.astral.sh/uv/getting-started/installation/) |
| **Cuenta de GitHub** | Fork y pull requests | [github.com](https://github.com) |

**No hace falta instalar Python a mano.** `uv` descarga e instala la versión exacta que pide
el proyecto (3.13, fijada en `.python-version`) la primera vez que se ejecuta `uv sync`.
Tampoco hace falta instalar Jupyter aparte: viene en el grupo `notebooks`.

Comprueba que las dos herramientas responden:

```bash
git --version
uv --version
```

### 3.2 Fork, clon e instalación (el fork es obligatorio)

Nadie trabaja directamente sobre `jasonssdev/mcd-afg`. Cada integrante trabaja en **su
propio fork** y envía cambios por pull request.

**1. Crea tu fork.** En [github.com/jasonssdev/mcd-afg](https://github.com/jasonssdev/mcd-afg)
pulsa **Fork** (arriba a la derecha) y acepta los valores por defecto. Eso crea
`github.com/<tu-usuario>/mcd-afg`.

**2. Clona tu fork, no el original.**

```bash
git clone git@github.com:<tu-usuario>/mcd-afg.git
cd mcd-afg
```

Si no tienes llaves SSH configuradas, usa HTTPS:
`git clone https://github.com/<tu-usuario>/mcd-afg.git`.

**3. Conecta el repositorio original como `upstream`** para poder traer los cambios del
equipo:

```bash
git remote add upstream https://github.com/jasonssdev/mcd-afg.git
git remote -v    # debe mostrar origin (tu fork) y upstream (el original)
```

**4. Instala el entorno.** Un solo comando crea `.venv/`, instala Python 3.13 si falta, y
deja todas las dependencias de desarrollo y de notebooks:

```bash
uv sync --group dev --group notebooks
```

**5. Verifica que todo funciona:**

```bash
uv run afg --help     # el CLI del proyecto responde
uv run pytest -q      # los tests pasan (257)
```

### 3.3 Descarga el corpus

El corpus **no está en el repositorio**: pesa 228 MB y está en `.gitignore`. Se descarga una
vez por máquina:

```bash
uv run afg corpus download     # descarga, verifica y extrae en data/raw/ami/ (CC BY 4.0)
uv run afg corpus inventory    # paso cero: confirma que el corpus está completo
```

Todos los comandos del proyecto fallan con un mensaje claro si el corpus no está.

### 3.4 Qué leer, y en qué orden

Unas dos horas de lectura bastan para entender el proyecto. En este orden:

| Paso | Qué leer | Para qué | Tiempo |
|---|---|---|---|
| 1 | Este README completo | Orientarte | 15 min |
| 2 | [`docs/propuesta.md`](docs/propuesta.md), secciones 1 a 4 | El problema, los objetivos y las hipótesis, tal como se propusieron | 30 min |
| 3 | [`docs/avances/01-jss-problema.md`](docs/avances/01-jss-problema.md) y [`03-jss-objetivos.md`](docs/avances/03-jss-objetivos.md) | La versión vigente de problema y objetivos, con lo que cambió y por qué | 20 min |
| 4 | [`notebooks/00-jss-corpus-y-auditoria.ipynb`](notebooks/00-jss-corpus-y-auditoria.ipynb), solo leer | Qué se midió en el corpus y qué decisiones obligó a tomar. Se lee en GitHub con sus salidas; no hace falta ejecutarlo | 30 min |
| 5 | [`docs/BACKLOG.md`](docs/BACKLOG.md), sección "Decisiones ya tomadas" | Las diez decisiones que no se reabren sin evidencia nueva | 10 min |
| 6 | [`docs/anotacion/README.md`](docs/anotacion/README.md) | Qué hace cada persona en la anotación y con qué archivos | 15 min |
| 7 | [`CONTRIBUTING.md`](CONTRIBUTING.md) | Cómo se envía el trabajo y las convenciones del repositorio | 15 min |

### 3.5 Tu primer trabajo real

**Si anotas (Germán, Gustavo):**

1. Lee [`docs/anotacion/annotation-guidelines.md`](docs/anotacion/annotation-guidelines.md):
   qué cuenta como decisión y qué significa cada relación.
2. Abre [`docs/anotacion/manual-anotacion-oe1.md`](docs/anotacion/manual-anotacion-oe1.md) y
   sigue el ejemplo del botón turbo (§3) con el CSV de la serie IS1004 abierto al lado.
   IS1004 es una serie de **desarrollo**: sirve para practicar y sus etiquetas no se reportan.
3. Genera tu archivo de trabajo y anota la Tarea A de esa serie:
   ```bash
   uv run afg gold build --series IS1004
   # abre data/processed/decisions/IS1004.decisions.csv y llena las columnas humanas
   ```
4. Abre tu primera pull request con el CSV (ver 3.6). Es la forma de calibrar criterios entre
   los dos anotadores antes de tocar las series que sí se reportan.

**Si eres el adjudicador (Jason):** tu trabajo empieza cuando exista una serie de control
anotada por ambos; el procedimiento está en el manual, §6.

### 3.6 Cómo enviar tu trabajo

Siempre desde una rama de tu fork, nunca desde `main`:

```bash
git fetch upstream
git checkout -b data/anotacion-is1004 upstream/main   # tipo/descripcion-corta
# ... trabajas ...
uv run pytest -q && uv run ruff check . && uv run mypy src/afg
git add -A && git commit -m "data(oe1): anotar Tarea A de IS1004"
git push -u origin data/anotacion-is1004
```

Luego abres el pull request desde tu fork contra `main` del repositorio original y completas
la plantilla. Lo revisa una persona distinta de quien lo abrió. Antes de empezar un trabajo
nuevo, actualiza tu fork:

```bash
git checkout main && git fetch upstream && git merge upstream/main && git push origin main
```

---

## 4. Mapa del repositorio: qué hay y qué revisar

| Carpeta o archivo | Qué contiene | Quién lo usa y cuándo |
|---|---|---|
| `README.md` | Esta guía | Todos, el primer día |
| `CONTRIBUTING.md` | Flujo de trabajo, roles, convenciones (nombres, idioma, cifras, etiquetas humanas) | Todos, antes de la primera PR |
| `docs/propuesta.md` | La propuesta de tesis completa. Se cita por sección (§1.4, §5.4). No se edita: sus revisiones pendientes están en el backlog | Todos, para entender el diseño original |
| `docs/avances/` | Los seis documentos vivos: problema, fuente de datos, objetivos, bibliografía, ética, metodología. Cada uno con versión e historial | Todos. Son la versión vigente del proyecto y de aquí salen las entregas |
| `docs/entregables/` | Lo que se entregó al curso, congelado tal como se envió: guiones de video, informe de la semana 4 | Quien prepara una entrega; se agrega, no se edita |
| `docs/anotacion/` | **El trabajo humano**: quién anota qué, el manual paso a paso de los CSV, la definición del constructo | Anotadores y adjudicador |
| `docs/protocols/` | El protocolo de alineamiento entre decisiones extraídas y de referencia (máquina) | Quien trabaje en OE2 |
| `docs/decisions/` | Registros de decisiones de arquitectura (ADR): por qué el repositorio es como es | Quien quiera saber por qué algo se hizo así |
| `docs/BACKLOG.md` | Decisiones tomadas con su evidencia, resultados del paso cero, y lo pendiente por prioridad | Todos, cada semana |
| `notebooks/` | El registro académico: qué se hizo, qué se midió y por qué se decidió. Versionados con sus salidas | Todos; se leen en GitHub sin ejecutar |
| `bibliography/` | `refs.bib` (49 referencias verificadas), criterios de inclusión, tabla de cribado y notas por referencia | Quien cite algo |
| `config/` | Parámetros versionados: series elegidas, partición desarrollo/evaluación, modelos, umbrales | Se lee; se cambia solo con un ADR |
| `data/` | `raw/` (corpus, ignorado por git), `interim/`, `processed/` (los CSV de anotación) | Anotadores escriben en `processed/` |
| `reports/` | Tablas y figuras generadas por el código | Se regeneran; no se editan a mano |
| `src/afg/` | El código: ingesta del corpus, conjunto de referencia, bloqueo de candidatos, kappa, alineamiento, métricas | Quien programe. Toda cifra del proyecto sale de aquí |
| `tests/` | 257 tests que fijan las cifras medidas como regresiones | Corren antes de cada PR |

**Qué revisar en una pull request ajena.** Que los tests pasen; que ninguna cifra se calcule
en un notebook o documento en vez de en `src/afg/`; que las etiquetas del conjunto de
referencia las haya puesto una persona; que no se haya leído contenido de las series de
evaluación fuera de la anotación; y que los nombres de archivo sigan la convención.

---

## 5. Plan por curso

La AFG se cursa en tres cursos de ocho semanas cada uno:

| Curso | Qué se entrega | Objetivos |
|---|---|---|
| **AFG1** | Problema, estado del arte, metodología, ética, conjunto de referencia listo para anotar (herramientas de OE1) y anotación iniciada en desarrollo | OE1 (herramientas) |
| **AFG2** | OE1 cerrado (anotación + kappa); OE2 sobre las 14 series con una escala de modelo (3 corridas); OE3 con banco de preguntas ≥100 y las tres condiciones, versión mínima | OE1, OE2, OE3 (mínimo) |
| **AFG3** | OE4, análisis de errores, intervalos bootstrap, conclusiones | OE4 |

**Extensiones si hay tiempo:** segunda escala de modelo (H3), validación humana ampliada.
Esta tabla está sincronizada con `docs/BACKLOG.md` y `docs/avances/03-jss-objetivos.md`; si
cambia, se actualiza en los tres lugares. El punto de decisión de AFG2 y el mínimo por
objetivo están en [`docs/avances/03-jss-objetivos.md`](docs/avances/03-jss-objetivos.md),
sección "Alcance por curso".

---

## 6. Comandos del proyecto

Todo pasa por un solo CLI, `afg`. No hay scripts sueltos.

```bash
uv run afg corpus download          # descarga las anotaciones de AMI
uv run afg corpus inventory         # paso cero: qué contiene el corpus
uv run afg corpus participants      # composición lingüística y por rol

uv run afg gold build --series IS1004          # archivo de trabajo de la Tarea A
uv run afg gold candidates --series IS1004     # pares candidatos a adjudicar (Tarea B)
uv run afg gold recall-sample --series IS1004 --n 50 --seed 42   # Tarea C
uv run afg gold evidence --meeting IS1004d --term turbo          # busca evidencia en la transcripción
uv run afg gold agreement --series IS1004      # kappa: existencia / tipo / dirección (Tarea D)

uv run afg biblio audit             # cobertura de la bibliografía
```

### Notebooks

```bash
uv run jupyter lab
```

| | Notebook | Cubre |
|---|---|---|
| 00 | `00-jss-corpus-y-auditoria.ipynb` | Adquisición, paso cero, auditoría de datos, y qué cambió por ella |
| 01 | `01-jss-viabilidad-e3.ipynb` | Estimación provisional de viabilidad del estrato de evolución |
| 02 | `02-jss-anotacion-oe1.ipynb` | *(pendiente)* anotación humana y conjunto de referencia |

Los notebooks son el **registro académico** del proyecto y se versionan con sus salidas, para
que un revisor pueda leerlos sin ejecutar nada. Si tocas uno, re-ejecútalo de punta a punta
antes de subirlo. Ver [`notebooks/README.md`](notebooks/README.md).

### Extras opcionales

No se instalan por defecto, para que `uv sync` sea rápido:

```bash
uv sync --extra instrument    # openkos, el motor bajo evaluación
uv sync --extra llm           # ollama, modelos locales
uv sync --extra retrieval     # rank-bm25, canal léxico de C1
uv sync --extra embeddings    # sentence-transformers (pesado)
```

`.env.example` está vacío a propósito; se completa cuando alguna condición lo necesite.

---

## 7. Cómo contribuir

**Nada entra a `main` directamente.** Fork → rama → pull request, revisado por una persona
del equipo distinta de quien la abrió, incluidas las del mantenedor
[@jasonssdev](https://github.com/jasonssdev). El flujo completo y las convenciones están en
[`CONTRIBUTING.md`](CONTRIBUTING.md).

Tres convenciones que más se rompen sin querer:

1. **Cada aporte lo firma la persona que lo hace** (CONTRIBUTING.md, Autoría).
2. **Los notebooks no calculan.** Toda cifra viene de una función con test en `src/afg/`.
   Una celda que calcula es una fuente de verdad paralela que nadie testea, y en este
   proyecto eso ya produjo un error de un factor de cuatro.
3. **Las etiquetas del conjunto de referencia las pone una persona.** Si un modelo las
   produce, la condición C3 tiene errores de extracción por construcción y el cuarto objetivo
   del proyecto deja de medir nada.

---

## 8. Estado

**El experimento no ha empezado.** El corpus está descargado, auditado y la muestra elegida;
las herramientas de construcción del conjunto de referencia están implementadas y con test.
Falta la anotación humana, y con ella todo lo demás.

| | Objetivo | Estado | Curso |
|---|---|---|---|
| **OE1** | Conjunto de referencia con relaciones entre reuniones | Herramientas listas; falta anotar | AFG1 → AFG2 |
| **OE2** | Calidad de la extracción automática | No empezado | AFG2 |
| **OE3** | Comparación C1 / C2 / C3 | No empezado | AFG2 |
| **OE4** | Atribución del error a su etapa de origen | Código listo; nada que correr | AFG3 |

Lo pendiente, por prioridad, está en [`docs/BACKLOG.md`](docs/BACKLOG.md).

---

## 9. Datos y licencia

El **AMI Meeting Corpus** es público y se usa bajo
[CC BY 4.0](https://groups.inf.ed.ac.uk/ami/corpus/license.shtml), que es la autoridad sobre
los términos de uso. El corpus se referencia con Carletta et al. (2006) y Carletta (2007). Los
identificadores de participante se conservan anonimizados; no se intenta reidentificación, y
los resultados por hablante se reportan agregados por categoría, nunca por individuo.

El código de este repositorio está bajo licencia MIT ([`LICENSE`](LICENSE)).
