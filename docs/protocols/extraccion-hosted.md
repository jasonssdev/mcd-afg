# Protocolo de la extensión con modelos de pago

| | |
|---|---|
| **Documento** | Guía de ejecución de la extensión del Experimento A con modelos de pago |
| **Estado** | Vigente. Aplica el [ADR 0026](../decisions/0026-adr-extension-extractor-con-modelos-hosted.md); los resultados se leen en el [notebook 33](../../notebooks/33-jss-extraccion-con-modelos-de-pago.ipynb) |

## Para quién es

Para quien corre la extensión: repetir la extracción de decisiones de C2 con seis modelos de pago
(dos por laboratorio) y compararla con la corrida formal `experimento-a-formal`. El diseño, la regla de
decisión y los límites están en el ADR; aquí solo se dice **cómo correr cada paso, en qué orden y qué
hacer cuando algo falla**. La extensión es descriptiva: no toca `config/experiments.toml` ni
`config/freeze.json`, y sus informes nunca reemplazan al `informe.json` de la corrida formal.

## Requisitos previos

1. **OpenKOS 0.7.2, instalado aparte.** El entorno congelado usa la 0.7.0 y no se modifica. La 0.7.2 vive
   en `data/interim/openkos-0.7.2` (fuera de git):

   ```bash
   uv venv data/interim/openkos-0.7.2
   uv pip install --python data/interim/openkos-0.7.2/bin/python openkos==0.7.2
   data/interim/openkos-0.7.2/bin/openkos --version   # debe decir: openkos 0.7.2
   ```

   Otro ejecutable se indica con la variable `AFG_HOSTED_OPENKOS_EXECUTABLE`. El comando se niega a
   correr si la versión no es exactamente 0.7.2.
2. **Ollama en marcha con `bge-m3`.** Los *embeddings* siguen siendo locales, también en los modelos de
   pago. El puente de continuidad necesita además `qwen3:8b`.
3. **Facturación activa en cada proveedor.** El nivel gratuito de Google (unas 20 solicitudes por día y
   por modelo) no alcanza: la corrida falla con el error 429. Se habilita la facturación de OpenAI,
   Anthropic y Google antes de empezar.
4. **Claves solo en el entorno, nunca en un archivo.** OpenKOS lee la clave de la variable
   `OPENKOS_OPENAI_API_KEY`, y esa única variable sirve a los tres proveedores, de modo que se fija **la
   clave del proveedor del modelo que se va a correr, justo antes de cada comando**:

   ```bash
   read -rs OPENKOS_OPENAI_API_KEY && export OPENKOS_OPENAI_API_KEY   # pega la clave; no se muestra
   # ... correr los comandos de ese proveedor ...
   unset OPENKOS_OPENAI_API_KEY
   ```

   La clave no se escribe en `.env`, en la configuración, en un manifiesto ni en el historial del
   intérprete. El código solo comprueba que la variable exista; nunca muestra su valor.
5. **Árbol de trabajo limpio** y en la rama de la extensión: el manifiesto de cada corrida registra el
   commit.

## Etiquetas y carpetas

Las etiquetas salen de `config/hosted_extraction.toml`: `openai-small`, `openai-large`,
`anthropic-small`, `anthropic-large`, `google-small` y `google-large`. Cada corrida deja su carpeta en
`reports/experiment-a/`:

| Paso | Carpeta |
|---|---|
| Puente de continuidad | `experimento-a-puente-0-7-2` |
| Segunda línea base (`qwen3:8b` con OpenKOS 0.7.2) | `experimento-a-base-0-7-2` |
| Piloto de un modelo | `experimento-a-piloto-<etiqueta>` |
| Corrida completa de un modelo | `experimento-a-hosted-<etiqueta>` |
| Comparación | `hosted-comparison/` (`comparacion.json` y `comparacion.csv`) |

Los espacios de trabajo de OpenKOS quedan en `data/interim/openkos/<corrida>/`.

## Orden

1. **Puente.** Una vez, antes de comparar.
   Entre el puente y los pilotos (o en paralelo con ellos) va la **segunda línea base** (paso 1 bis).
2. **Piloto por modelo.** La serie ES2002 con una repetición, para medir tiempo y costo y detectar
   identificadores o parámetros rechazados antes de gastar la corrida completa.
3. **Revisar el piloto.** Informe descriptivo y comparación del piloto.
4. **Corrida completa por modelo.** Once series de evaluación, tres repeticiones.
5. **Informe por modelo.**
6. **Comparación de todos los modelos.**
7. **Registrar los costos** en la tabla `[costs]` de `config/hosted_extraction.toml`.
8. **Volver a ejecutar el notebook 33.**

## Comandos

Todos se corren desde la raíz del repositorio. Los atajos de `make` (última columna de cada paso)
llaman a los mismos comandos y no contienen claves.

### 1. Puente de continuidad

`qwen3:8b` con OpenKOS 0.7.2 en el Ollama local, una serie (ES2002) y una repetición. No usa clave de
ningún proveedor.

```bash
uv run afg experiment a-hosted --bridge        # make hosted-bridge
```

### 1 bis. Segunda línea base (`qwen3:8b` con OpenKOS 0.7.2)

El puente salió algo por encima del rango de las tres corridas formales con una sola corrida (enmienda
del ADR 0026). Para quitar la versión de OpenKOS de la comparación, los modelos de pago se comparan
también con `qwen3:8b` sobre la misma OpenKOS 0.7.2: el *backend* `ollama`, la semilla y la
temperatura formales y `transcript_decisions`, sobre las once series de evaluación con tres corridas
cada una. La corrida formal sigue siendo la línea base principal y los resultados se informan contra
ambas. No usa clave de ningún proveedor.

```bash
uv run afg experiment a-hosted --local-baseline        # make hosted-local-baseline
```

- **Duración:** unos 30 minutos por serie-corrida en el equipo local, unas 16 horas en total (33
  pares). Es reanudable: repetir el mismo comando omite los pares ya terminados.
- **Cuándo correrla:** antes de las corridas de pago o en paralelo con ellas. Comparte el Ollama local
  con los *embeddings* de las corridas de pago, así que correr ambas a la vez hace más lentas las dos.
- Es descriptiva como el resto: `a-report` exige `--descriptive` para esta carpeta.

### 2. Piloto de un modelo

```bash
export OPENKOS_OPENAI_API_KEY=...              # la del proveedor de <etiqueta>
uv run afg experiment a-hosted --model <etiqueta> --pilot      # make hosted-pilot LABEL=<etiqueta>
```

### 3. Revisar el piloto

```bash
uv run afg experiment a-report --c2-extraction experimento-a-piloto-<etiqueta> --descriptive
uv run afg experiment a-hosted-compare --models <etiqueta> --pilot
```

Se revisa que la corrida haya terminado sin errores, que las extracciones estén completas (el
`ingest` de las cuatro reuniones terminó), el tiempo por reunión y el costo que muestra el panel del
proveedor. Si algo no cuadra, se corrige antes de la corrida completa (ver «Si algo falla»).

### 4. Corrida completa de un modelo

```bash
uv run afg experiment a-hosted --model <etiqueta>
```

Corre las once series de evaluación con tres repeticiones. `make hosted-run LABEL=<etiqueta>` hace este
paso y el siguiente.

### 5. Informe de un modelo

```bash
uv run afg experiment a-report --c2-extraction experimento-a-hosted-<etiqueta> --descriptive
```

El informe se guarda como `informe-descriptivo.json`. Sin `--descriptive`, el comando se niega: una
extensión con modelos de pago solo tiene informe descriptivo.

### 6. Comparación de todos los modelos

```bash
uv run afg experiment a-hosted-compare --include-bridge        # make hosted-compare
```

Compara cada modelo con la línea base (diferencia pareada en precision, recall y F1, con nivel
Bonferroni por los seis modelos) y, con `--baseline formal|local|both` (por defecto `both`), con la
corrida formal, con la segunda línea base o con ambas. Si la segunda línea base existe, agrega el
«efecto de versión» (`qwen3:8b` en OpenKOS 0.7.2 contra la corrida formal), que no cuenta en el nivel
Bonferroni; si no existe, la columna `local` figura como «sin corrida». El CSV lleva una columna
`baseline`. Agrega, además, tiempo, extracciones completas, decisiones por reunión y
costo. Las etiquetas sin corrida se informan como «sin corrida». Con `--models <etiqueta>` (repetible) se
limita a algunas.

### 7. Registrar los costos

Después de cada corrida completa se lee del panel de cada proveedor el monto facturado por esa corrida
y se escribe en `config/hosted_extraction.toml`, en la tabla `[costs]` (hoy comentada), por ejemplo
`openai-small = 3.42`. Es un dato descriptivo que la comparación copia a sus salidas.

### 8. Volver a ejecutar el notebook 33

```bash
uv run jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=900 notebooks/33-jss-extraccion-con-modelos-de-pago.ipynb
# make hosted-notebook
```

El notebook se versiona con sus salidas (`CONTRIBUTING.md`, sección 7.3). Calcula similitudes con
`bge-m3`, así que necesita Ollama en marcha. Se vuelve a ejecutar después del puente, después de cada
corrida completa y después de registrar los costos. Antes de la corrida completa, sus secciones sin datos
muestran el aviso «pendiente».

## Tiempos y costos esperados

- **Línea base local:** una serie-repetición de `qwen3:8b` tarda unos 24 minutos; la corrida formal
  completa tardó 11 h 48 min.
- **Modelos de pago:** el tiempo y el costo no se conocen antes del piloto; el piloto es lo que los
  mide. Cada modelo hace 33 extracciones de cuatro reuniones (11 series por 3 repeticiones). El costo se
  proyecta con el piloto y se confirma con el panel del proveedor.
- **Puente:** una serie y una repetición, unos 24 minutos.
- **Segunda línea base local:** 33 pares serie-repetición, unos 30 minutos cada uno, unas 16 horas en
  total.

## Si algo falla

- **Reanudar una corrida interrumpida:** se repite el mismo comando. `a-hosted` omite los pares
  (serie, repetición) ya terminados y rehace desde un espacio limpio los que quedaron a medias o
  fallaron. No hace falta nada más y no cambia lo medido.
- **El proveedor rechaza `temperature`, `seed` o `reasoning_effort`.** El ADR fija estos parámetros
  (decisión 5): `reasoning_effort = low` en los seis modelos y ni `temperature` ni `seed` hacia los
  modelos de pago. Un rechazo **no se resuelve cambiando el parámetro por cuenta propia**: se detiene la
  corrida de ese modelo, se anota el error exacto y la fecha, y se decide en una enmienda al ADR. Ese
  modelo queda como «sin corrida» o «parcial» en el notebook, con la razón escrita en la sección 7.
- **El identificador de un modelo ya no se sirve** (error de modelo no encontrado). Se aplica la regla de
  reemplazo del ADR 0026, decisión 3: se cambia por el sucesor del mismo nivel en
  `config/hosted_extraction.toml` y se deja escrito en dos lugares: el manifiesto de la corrida (que
  guarda el identificador usado) y la sección 7 del notebook 33. Una corrida parcial con el identificador
  anterior no se mezcla con la del sucesor: se empieza una corrida nueva.
- **Errores 429 (límite de solicitudes) o 5xx (falla del proveedor).** OpenKOS 0.7.2 reintenta las fallas
  transitorias por sí mismo. Si el par (serie, repetición) igual falla, se espera unos minutos y se
  repite el comando. Un 429 persistente con Google suele indicar que falta la facturación (requisito 3).
- **Falta la clave.** El comando se detiene antes de llamar a ningún modelo y nombra la variable
  `OPENKOS_OPENAI_API_KEY`. Se fija la clave del proveedor correcto y se repite.
- **La clave es de otro proveedor.** La corrida falla con un error de autenticación. Se detiene, se
  fija la clave correcta y se repite el comando.
- **Ollama no responde o falta `bge-m3`.** El comando se niega antes de empezar y dice qué falta.
- **El puente queda fuera del rango formal.** No se repite hasta que quede dentro: el notebook lo declara
  y la comparación con los modelos de pago pierde fuerza (ADR 0026, decisión 6).
- **Nunca se borra ni se sobrescribe** la carpeta de una corrida ni `experimento-a-formal`. Una corrida
  abandonada se declara en el notebook (nombre, motivo) y no se usa para elegir resultados.

## Qué no se hace

- No se corre nada de esta extensión con series de desarrollo: el comando solo acepta las de evaluación.
- No se escribe una clave en ningún archivo ni se pega en un issue, un PR o un registro.
- No se reportan los resultados como confirmatorios: la extensión es descriptiva (ADR 0026, decisión 9).
