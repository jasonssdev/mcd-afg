# Validación manual de la alineación (paso 3 del protocolo)

**Para qué sirve.** El protocolo de alineación (`docs/protocols/alignment.md`, paso 3) exige
contrastar la alineación automática con un emparejamiento hecho a mano sobre al menos 100 pares.
Esta hoja reúne esos pares; quien etiqueta contesta si/no y el repositorio calcula la
concordancia entre ambas alineaciones. El juez automático no sustituye este paso.

**Quién.** El validador asignado en el issue: una persona del equipo que no haya visto las cifras
del Experimento A (ni la alineación ni los puntajes). **Cuánto toma.**
Entre 30 y 60 segundos por par, de 50 a 100 minutos en total.

## Paso a paso

1. **Esperar el aviso.** Quien mantiene el repositorio comenta en el [issue #290](https://github.com/jasonssdev/mcd-afg/issues/290) cuando la hoja ya está en `main`, con su ruta: `data/processed/alignment-validation/<corrida>.manual.csv`. Antes de ese comentario no hay nada que abrir.
2. **Traer la hoja.** En la terminal, dentro de la carpeta del repositorio: `git checkout main && git pull`.
3. **Abrir el CSV** con LibreOffice Calc o Numbers (Excel solo si se guarda como «CSV UTF-8»). El separador es la coma y la codificación UTF-8 ([`EMPIEZA-AQUI.md`](asignacion/EMPIEZA-AQUI.md) §4). Si el programa pregunta cómo interpretar el archivo, se elige UTF-8 y coma; los identificadores y las fechas no se dejan cambiar al programa (nada de convertir `ES2015.q1` o una fecha a otro formato).
4. **Llenar solo las columnas humanas:** `same` (`si` o `no`) y, si hace falta, `notes`. Ninguna otra columna se toca.
5. **Guardar como CSV UTF-8** (delimitado por comas) con el mismo nombre, las mismas columnas y las mismas filas, sin agregar ni reordenar.
6. **Revisar.** El comando de puntaje (`afg experiment a-validacion-puntaje`) lo corre quien mantiene el repositorio, no quien valida. Basta con volver a abrir el archivo y confirmar que no queda ninguna celda vacía en las columnas que se llenan.
7. **Entregar.** Se crea la rama `data/validacion-alineacion-gv`, se hace el commit del CSV y se abre el PR como indica [`EMPIEZA-AQUI.md`](asignacion/EMPIEZA-AQUI.md) §6, mencionando el issue #290 en la descripción.
8. **No abrir la clave (`data/interim/alignment-validation/<corrida>.clave.json`) ni las cifras del Experimento A hasta que el PR esté fusionado.**

## La pregunta

Cada fila trae la serie (`serie`) y dos frases de la misma reunión (`meeting_id`): `extracted_decision` (lo que extrajo
el sistema) y `reference_decision` (la decisión de referencia, traducida al inglés). En `same`:

- **`si`**: ambas frases describen la misma decisión, aunque estén redactadas distinto o una sea
  más detallada que la otra.
- **`no`**: describen decisiones distintas, o una trata un aspecto que la otra no menciona.

No hay tercera opción: si hay duda, se elige la respuesta más probable y se anota el motivo en
`notes` (opcional). No se deja ninguna fila vacía. Cada par se juzga solo: no hace falta cuidar
que una decisión quede emparejada una única vez.

## Cómo se llena

Hay una sola hoja por corrida: `data/processed/alignment-validation/<corrida>.manual.csv`. Se abre en una
hoja de cálculo y solo se escriben `same` y, si hace falta, `notes`.

- Guardar como **CSV UTF-8 (delimitado por comas)**, con las mismas siete columnas, sin agregar
  ni reordenar filas. Detalles en [`EMPIEZA-AQUI.md`](asignacion/EMPIEZA-AQUI.md) §4.
- **No abrir** la clave, `data/interim/alignment-validation/<corrida>.clave.json`. Guarda la
  similitud y lo que decidió la alineación automática; verlos sesgaría las respuestas. La clave
  queda fuera del repositorio (no se sube a GitHub) y la tiene quien arma la hoja, no quien
  valida. El orden de las filas ya está barajado.
- Las etiquetas son solo de la persona que las pone: nadie las prellena.

## Cómo se arma la muestra

**Con datos formales** la validación se hace sobre la corrida de evaluación del Experimento A
(repetición 0), con las once series de evaluación juntas. Los pares candidatos de todas las
series forman un solo conjunto y de él se sortean 100 pares; cada fila indica su serie. Si el
conjunto tiene menos de 100 pares, el comando se niega: la muestra no se reduce. Una corrida de
desarrollo se valida con su única serie, y `--series` (lista separada por comas) permite acotar
las series.

`uv run afg experiment a-validacion-hoja --run-name <corrida>` toma la corrida guardada y la
referencia de cada serie, alinea con τ = 0,70 y sortea los 100 pares
(`manual_validation_sample_size`) con la semilla 42: la mitad entre los que la alineación
automática empareja y la otra mitad entre pares de la misma reunión que descarta pero tienen
similitud de al menos 0,50. Si faltan pares emparejados, se completa con descartados. Semilla,
reparto y piso están en `[alignment.manual_validation]` de `config/experiments.toml`, fijados
antes de etiquetar; el sorteo es determinista. El comando se niega a pisar una hoja con
etiquetas (salvo `--force`).

## Después

```bash
uv run afg experiment a-validacion-puntaje --run-name <corrida>
```

Exige todas las etiquetas y reporta la **concordancia** del protocolo
(`alignment.concordance`: pares que ambas alineaciones emparejan, sobre los que empareja al menos
una), el acuerdo observado, la matriz de confusión, cuántos pares emparejados por la alineación
confirmó la persona y cuántos de los descartados emparejaría. No hay umbral de aprobación. Como
la muestra está estratificada, las proporciones por grupo describen cada grupo, no toda la serie.

El resultado queda en `reports/experiment-a/<corrida>/validacion-manual.json` y copia la clave,
de modo que el origen de cada par se conserva una vez que existen las etiquetas.
