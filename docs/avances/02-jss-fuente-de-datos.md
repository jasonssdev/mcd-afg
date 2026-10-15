# Fuente de datos

| | |
|---|---|
| **Documento** | 02 — Fuente de datos |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.3 |
| **Fecha** | 2026-10-15 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial. Fuente de datos, auditoría y riesgos para AFG1. | Primera entrega del curso. |
| 1.1 | 2026-09-20 | Redacción en voz impersonal / de equipo. | El proyecto es de un equipo de tres personas; ningún documento se redacta en primera persona singular. |
| 1.2 | 2026-10-01 | Reescritura completa de la redacción: el corpus se presenta desde lo que contiene una serie de reuniones, cada término técnico se explica al aparecer y se agrega un glosario breve. Las cifras, las referencias, las decisiones y la numeración de secciones no cambian. | Retroalimentación de la revisión entre equipos de la semana 8: el problema y la metodología no se entendían, menos aún para una audiencia no técnica. |
| 1.3 | 2026-10-15 | Se agrega la sección 7, «Calidad y relevancia de los datos»: resumen de lo que el análisis exploratorio ([documento 07](07-jss-analisis-exploratorio.md)) encontró sobre valores faltantes, duplicados y valores atípicos, y de la relevancia de los datos para el problema, con las cifras del documento 07 y su fuente. Se agregan filas de trazabilidad. No cambia ninguna cifra, decisión ni sección anterior. | La rúbrica del pre-informe de AFG2 (sección 3) pide describir el origen, el tipo, la calidad y la relevancia de los datos; este documento cubría origen y tipo, y la calidad y la relevancia estaban solo en el documento 07. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## Qué hay dentro de los datos

Para medir si un sistema recuerda bien las decisiones de un equipo hace falta un conjunto
de reuniones reales donde se sepa qué se decidió, quién lo dijo y qué pasó después. Grabar
reuniones propias no es viable en el plazo del proyecto, y las reuniones de una empresa no
se pueden publicar. Lo que sí existe es un corpus público: una colección de reuniones
grabadas, transcritas y marcadas a mano por investigadores, pensada justamente para que
otros la estudien.

Este documento describe ese corpus, qué parte de él se usa, cómo se verificó que sirve y
qué problemas se encontraron al revisarlo. Una regla atraviesa todo el documento: ninguna
cifra se toma de la documentación del corpus por fe. Cada una se midió sobre los archivos
descargados.

## 1. El corpus y su licencia

Se trabaja sobre el **AMI Meeting Corpus** (Carletta et al., 2006; Carletta, 2007). Son
~100 horas de reuniones grabadas en tres centros de investigación europeos. Cerca de dos
tercios siguen un mismo escenario: un equipo de cuatro personas, cada una con un rol
asignado, diseña un control remoto de televisión. El resto son reuniones libres. Se descarga
el paquete de anotaciones manuales `ami_public_manual_1.6.2.zip` (22,9 MB comprimido,
228 MB extraído) desde la página oficial del corpus. Ese paquete no trae audio ni video:
trae las transcripciones y las capas de marcas hechas a mano, que es lo que el proyecto
necesita.

**Licencia: CC BY 4.0.** Es la licencia que permite usar y redistribuir el material citando
la fuente. Se cita la página de licencia como autoridad de los términos de uso, no los
artículos originales del corpus (Carletta et al., 2006; Carletta, 2007), que describen una
licencia anterior más restrictiva. Esta es una condición explícita del curso para el uso de
fuentes de datos públicas, y una advertencia que el equipo debía verificar antes de asumir
el régimen de uso: de haberse fiado de los artículos, el proyecto habría partido de un
permiso equivocado.

## 2. La estructura en series y por qué importa

El corpus no es una bolsa de reuniones sueltas. En el escenario del control remoto, el
mismo equipo de cuatro personas se junta cuatro veces, en orden: una reunión de arranque
(*kick-off*), una de diseño funcional, una de diseño conceptual y una de diseño detallado.
A ese bloque de cuatro reuniones se le llama **serie**.

La serie es lo que hace posible el proyecto. Para medir si una decisión evolucionó hace
falta ver al mismo equipo decidir algo y volver sobre ello después. Con reuniones sueltas de
equipos distintos no existe "evolución de una decisión" que medir. Por eso, cuando se elige
qué datos usar, la unidad que se elige no es la reunión sino la **serie completa**: o entran
las cuatro reuniones o no entra ninguna. Esto aplica al conjunto de referencia (OE1) y al
Experimento B.

## 3. Capas usadas y cadena de evidencia

Sobre la transcripción de cada reunión, los investigadores de AMI agregaron **capas de
anotación**: marcas hechas a mano que señalan, por ejemplo, dónde empieza y termina cada
intervención, qué frases del resumen corresponden a qué momentos de la conversación, o qué
pasajes discuten una decisión. Se usan cuatro, verificadas por conteo directo de archivos
sobre el paquete descargado:

- `abstractive` (142 archivos): el resumen escrito a mano de cada reunión, con un apartado
  `DECISIONS` que lista lo que se decidió.
- `summlink` (137): enlaza cada frase del resumen con los momentos de la conversación que
  la respaldan.
- `decision/manual` (47): la capa *Decision Discussion Segmentation* o DDS, que marca los
  tramos de conversación donde se discute una decisión.
- `dialogueAct` (556) y `words` (687): las intervenciones y las palabras, el soporte de
  evidencia más fino.

De las 56 reuniones seleccionadas (ver §4), 54 tienen además la capa `topic`, que divide la
reunión por temas.

Con estas capas, cada decisión tiene una **cadena de evidencia**: se parte de la frase del
apartado `DECISIONS` del resumen, `summlink` lleva a los actos de diálogo que la respaldan,
y de ahí a las palabras exactas. **Resumen abstractivo → `summlink` → acto de diálogo →
palabras.** Es la misma forma de definir "decisión" que usan Hsueh y Moore (2007), lo que
permite comparar los resultados con la literatura.

## 4. Auditoría de datos

Antes de anotar nada, se revisó el corpus con la misma desconfianza con que se revisaría un
dato de terceros: qué series sirven, cuántas decisiones hay realmente, quién las toma y si el
material tiene errores. Esta sección registra esa revisión. Las cifras se calcularon en
[`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb).

### 4.1 Marco muestral

El marco muestral es el conjunto de series entre las que se puede elegir. Había dos
candidatos y se midieron ambos (decisión D1 del registro de decisiones). La capa DDS, que
marca los tramos de discusión de decisiones y parecía la más directa, está completa en solo
**6 series** (136 decisiones). El resumen abstractivo, en cambio, está completo en las cuatro
reuniones de **33 series** (649 decisiones). Se eligió el segundo marco: cinco veces más
material. La capa DDS no se descarta: pasa a **subconjunto de validación** dentro de las
series que la tienen (D2), es decir, sirve para comprobar sobre una parte de los datos que
lo que dice el resumen coincide con lo que marca la capa. De las 33, **32** tienen además
`summlink` completo; **TS3012** queda inelegible por tenerlo sólo en 3 de 4 reuniones, y
sin esa capa la cadena de evidencia se corta.

### 4.2 Selección de 14 series

De las 32 series elegibles se seleccionaron **14** (56 reuniones). Los tres centros donde se
grabó el corpus se identifican con las letras ES (Edinburgh), IS (Idiap) y TS (TNO), y el
criterio fue **balancear por sitio de grabación**, no por lengua materna de los
participantes. La razón se explica en §5: en este corpus la lengua y el sitio van juntos y
no se pueden separar. Dentro de cada sitio se prefirieron las series con más decisiones.

El resultado son **343 frases `DECISIONS`**, es decir, 343 decisiones registradas en los
resúmenes. Como el objetivo es encontrar relaciones entre decisiones de reuniones
distintas, lo que se anota son pares: una decisión de una reunión frente a una de otra
reunión de la misma serie. Esos pares son **3.071**. Anotarlos todos a mano no es viable, así
que un filtro automático (§4.4) deja **92 pares candidatos** para la anotación humana. El
detalle del criterio y las series descartadas está en
[`../decisions/0004-adr-oe1-series-selection.md`](../decisions/0004-adr-oe1-series-selection.md).

### 4.3 Partición desarrollo / evaluación

Las 14 series se dividen en dos grupos con funciones distintas. No es la partición
*train/test* habitual del aprendizaje automático, porque aquí nada se entrena. Separa los
datos que se usan para **tomar decisiones de diseño** (qué parámetros usa la línea base C1,
qué umbral de alineamiento τ se aplica, dónde se fija el filtro de candidatos) de los datos
que se usan para **reportar resultados**. La regla es la de cualquier examen: no se puede
practicar con las mismas preguntas que después se califican.

- **Desarrollo:** ES2015, IS1004, TS3009 — 77 decisiones / 11 candidatos. Sobre estas
  tres series se mira, se prueba y se ajusta.
- **Evaluación:** 11 series — 266 decisiones / 81 candidatos, con balance de sitio 4 ES / 4
  IS / 3 TS. Sobre estas no se mira nada hasta que todo está fijado.
- **Control de doble anotación** (≥25 % exigido por OE1): ES2008, ES2016, IS1003, TS3005
  — 36,4 % de la evaluación. Estas cuatro series las anotan dos personas por separado, para
  medir cuánto coinciden.

Todo parámetro ajustado en desarrollo se congela antes de tocar evaluación. Detalle en
[`../decisions/0005-adr-development-evaluation-split.md`](../decisions/0005-adr-development-evaluation-split.md).

### 4.4 Los cuatro N

Hay cuatro cantidades que aparecen una y otra vez en el proyecto. Las cuatro están medidas
sobre los archivos y no cambian.

| Nivel | N | Estado |
|---|---|---|
| Reuniones | 56 (14 series × 4) | Medido, fijo |
| Frases `DECISIONS` | 343 | Medido, fijo |
| Pares entre reuniones | 3.071 | Medido, fijo |
| Pares candidatos (bloqueador) | 92 | Medido, fijo |

El paso de 3.071 a 92 lo hace el **bloqueador**: un filtro automático que descarta los pares
de decisiones que, por sus palabras, es casi imposible que hablen de lo mismo, y conserva
los que vale la pena que una persona lea. Compara las palabras de las dos frases y exige dos
cosas a la vez: un **coeficiente de solapamiento ≥ 0,30**, es decir, que de las palabras de
la frase más corta, al menos esa proporción aparezca también en la otra, y **`\|A∩B\| ≥ 2`**,
que compartan al menos dos palabras en términos absolutos.

La segunda condición importa. Sólo con el coeficiente, el bloqueador seleccionaba 712 de
3.071 pares (23,2 %, ≈18 h de anotación); con el mínimo absoluto de palabras compartidas
añadido, 92 (3,0 %, ≈2,3 h). Y lo hizo sin perder el **caso de regresión** del bloqueador:
el par del botón turbo, `IS1004c` → `IS1004d` (D9). Un caso de regresión es un ejemplo que
se guarda a propósito para comprobar, cada vez que se cambia el filtro, que sigue pasando.

Ese par **no es una relación confirmada**. La verificación contra transcripción mostró que la
reversión que el resumen abstractivo afirmaba nunca ocurrió (§5;
[`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb)).
Se conserva por su forma, no por su contenido: las dos frases son cortas y comparten pocas
palabras, por lo que es el par de solape más exigente medido en el piloto. Con el
coeficiente de solapamiento da 0,400; con Jaccard, otra medida habitual que divide por el
total de palabras distintas de ambas frases en lugar de por la frase más corta, da 0,118 y
el par se pierde (D5). Por eso el caso acota el punto de operación por ambos lados: umbral
≤ 0,40 **y** mínimo ≤ 2. Que la relación resultara falsa no debilita la prueba: lo que el
caso fija es que el bloqueador sea sensible a una frase corta, no que exista un enlace.

### 4.5 Composición lingüística

Hay 189 participantes en el corpus: **91 nativos de inglés, 96 no nativos, 2 desconocidos**.
A primera vista eso permitiría estudiar si el sistema funciona peor con hablantes no
nativos. No es así. La lengua materna está **perfectamente anidada en el sitio de
grabación**: Edinburgh (ES) es casi todo nativo, Idiap (IS) es mayoritariamente no nativo, y
**TNO (TS) no tiene ningún participante registrado en `participants.xml`**. Si en Idiap
algo saliera peor, no habría manera de saber si fue por la lengua de los participantes o por
cualquier otra cosa propia de ese centro: el micrófono, la sala, la forma de moderar. En AMI
no es posible separar "hablante no nativo" de "grabado en Idiap". Esa es la razón
estructural, no de tamaño muestral, por la que se balancea por sitio y no por lengua (§5).

### 4.6 Autoría por rol

Cada participante del escenario tiene un rol: jefe de proyecto (PM), diseñador industrial
(ID), experto en marketing (ME) y diseñador de interfaz (UI). Sobre 685 actos atribuidos en
las 14 series, el reparto de quién dice las decisiones es: **PM 47,0 % · ID 22,8 % · ME
15,3 % · UI 14,9 %**. Casi la mitad de las decisiones las enuncia quien preside. La
proporción del PM se mantiene entre 44 % y 50 % en cada sitio por separado, lo que indica
que es **estructural** (quien preside habla y decide más) y no un artefacto de la muestra.
Este dato vuelve en el documento de aspectos éticos: un sistema que recupere mejor lo que
dijo el jefe de proyecto borraría del registro a quien propuso la idea.

### 4.7 Anclaje a evidencia

**317 de 343 decisiones (92,4 %)** tienen al menos un acto de diálogo como evidencia
identificada por la cadena del §3. Dicho de otro modo: para 317 decisiones del resumen se
puede señalar el momento exacto de la conversación en que ocurrieron. Las demás están en
el resumen pero no apuntan a ningún pasaje, y esa ausencia es una señal de alerta que se usa
más adelante (§5).

### 4.8 Segmentación por tópico como proxy — descartada

Una idea tentadora sería usar los cambios de tema de la reunión como pista de dónde
terminan las decisiones: si cambia el tema, probablemente se cerró algo. La propuesta ya
citaba a Hsueh y Moore para descartarlo ("menos de la mitad de las veces" coinciden). **Se
midió esto directamente sobre la muestra del proyecto**: los límites de tema coinciden con
los límites de decisión en el 9,0 % de los casos con una tolerancia de 5 palabras, y sólo en
el 16,5 % con 80 palabras. Es muy por debajo de lo que reporta la literatura. Es una
medición propia, no una cita, y confirma con más fuerza la decisión de no usarlo.

## 5. Riesgos declarados

Ningún conjunto de datos es neutro. Estos son los riesgos que se conocen de antemano, y lo
que el proyecto puede o no puede afirmar por su causa.

- **Sesgo de dominio.** Todas las reuniones tratan el mismo producto (un control remoto).
  Lo que se mida aquí vale para este tipo de reuniones de diseño; no se afirmará
  generalización a otros dominios.
- **Habla actuada.** Los participantes siguen un guion de escenario, como actores con
  libertad de improvisar. Las decisiones son reales como actos conversacionales (la gente
  discute y acuerda de verdad), pero sus consecuencias organizacionales son simuladas: nadie
  fabricó el control remoto.
- **Anidamiento lengua/sitio.** Descrito en §4.5. Cualquier lectura de "efecto de lengua" en
  este corpus es indistinguible de un efecto de sitio de grabación.
- **Huecos en la capa de decisiones.** La capa `decisionlink` de AMI existe en el diseño
  pero no distribuye datos (documento 01, §4). Y el análisis de casos del piloto encontró una
  relación real entre dos reuniones (IS1004b → IS1004c) que el bloqueador **no** seleccionó
  como candidata: un falso negativo confirmado, es decir, un par que debía pasar el filtro y
  no pasó. Proviene de una revisión dirigida, no de la muestra formal con que se medirá
  cuántos pares se pierden.
- **El material de origen contiene errores.** El resumen abstractivo de AMI para IS1004d
  afirma que se eliminó el botón turbo; la transcripción muestra que se mantuvo. Lo
  llamativo es que la señal `evidencia = 0 actos` (una decisión del resumen que no apunta a
  ningún pasaje de la conversación, §4.7) predijo este error antes de leer la transcripción.
  Es el argumento a favor de exigir evidencia obligatoria en cada decisión (§5.2 del
  documento 06).

## 6. Plan de saneamiento

Frente a esos riesgos, cuatro reglas de trabajo.

1. **Nunca decidir en la capa automática.** Todo lo que el bloqueo y la normalización
   automática producen son *sugerencias* en una columna `machine_flags`
   (`sin_evidencia`, `posible_compuesta`, `frase_corta`), nunca en la columna `status`. La
   máquina puede avisar "esta frase parece no tener evidencia"; sólo un humano decide si
   algo es una decisión y qué relación tiene con otra.
2. **Contrastar contra la transcripción, no contra el resumen.** El caso del botón turbo
   demuestra que el resumen abstractivo puede estar equivocado; el protocolo de anotación
   exige volver a los actos de diálogo, no aceptar el resumen como verdad.
3. **Doble anotación y kappa por tipo.** Sobre el 36,4 % de la evaluación, dos personas
   anotan por separado y se mide cuánto coinciden con kappa, una medida de acuerdo que
   descuenta las coincidencias por azar. Se mide por separado para cada pregunta (¿existe la
   relación? ¿de qué tipo es? ¿en qué dirección va?), nunca combinado, y cada desacuerdo se
   resuelve en una adjudicación documentada.
4. **Congelar antes de anotar.** El punto de operación del bloqueador, el criterio de
   selección de series y el split quedan fijados en
   [`../../config/corpus.toml`](../../config/corpus.toml) antes de que empiece la anotación
   humana, para que ningún ajuste posterior pueda leerse como sobreajuste a los resultados.

## 7. Calidad y relevancia de los datos

Las secciones anteriores describen de dónde vienen los datos y cómo se eligió la muestra. Esta
sección resume lo que el análisis exploratorio
([documento 07](07-jss-analisis-exploratorio.md)) encontró sobre su **calidad** y su
**relevancia** para el problema. No repite el análisis: las cifras vienen del
[notebook 03](../../notebooks/03-jss-eda.ipynb) y se explican con sus figuras en el documento 07.

### 7.1 Calidad

**Valores faltantes.** Un valor faltante es una celda vacía. De las 77 variables revisadas,
solo tres tienen celdas vacías (documento 07, [§4.1](07-jss-analisis-exploratorio.md#41-valores-faltantes);
notebook 03, §3.1):

| Variable | Faltantes | Origen del faltante |
|---|---|---|
| Hora de inicio de la reunión | 32 de 56 (57,1 %) | Depende del sitio de grabación: AMI la trae en IS, no la trae en TS y la pierde en 16 de 20 reuniones de ES. |
| Lengua materna declarada | 64 de 224 (28,6 %) | Faltan todos los hablantes de TS; el archivo de participantes no los incluye (ver §4.5). |
| Evidencia de la decisión | 26 de 343 (7,6 %) | Decisiones del resumen sin ninguna intervención enlazada (ver §4.7). |

Los dos primeros faltantes son estructurales, es decir, vienen de cómo AMI armó sus archivos.
El tercero no falta al azar: no falta ninguna en la primera reunión de la serie (0 de 51) y la
proporción sube a 11,2 % (10 de 89) en la tercera y 11,5 % (11 de 96) en la cuarta. Por eso
las 26 decisiones sin evidencia se tratan como una señal de revisión manual y no como un dato
corriente; es la misma señal que anticipó el error del botón turbo (§5).

**Decisiones sin evidencia: se marcan, no se imputan.** Imputar es reemplazar un valor
faltante por uno estimado. El proyecto no imputa nada, porque las etiquetas de referencia las
pone una persona, porque estimar la evidencia de una decisión fabricaría un respaldo que no
existe y porque los otros faltantes son metadatos que ningún resultado usa. El faltante se
conserva como categoría y se señala (documento 07, [§4.2](07-jss-analisis-exploratorio.md#42-por-qué-no-se-imputa)).

**Duplicados.** Hay 4 frases idénticas y 8 casi idénticas dentro de una misma serie, siempre
en reuniones consecutivas y nunca dentro de una misma reunión. Ese patrón corresponde a una
decisión reafirmada, no a un error de captura. Se conservan con una marca, porque las
reafirmaciones son parte de lo que el proyecto quiere medir (documento 07,
[§4.3](07-jss-analisis-exploratorio.md#43-duplicados)).

**Valores atípicos.** Quedaron marcadas 15 de 56 reuniones por al menos un método estadístico.
Ninguna se eliminó ni se corrigió: el resultado neto es 0 filas eliminadas, 0 valores
corregidos y 0 valores imputados, porque los casos revisados son fenómenos reales (por ejemplo,
una reunión muy larga) y no errores de captura (documento 07,
[§5](07-jss-analisis-exploratorio.md#5-valores-atípicos)). La excepción es TS3003c, cuya
duración declarada supera en 286 segundos (11,1 %) a la del último turno transcrito; sin el
audio no se puede resolver, y por eso la duración del archivo no se usa como variable
explicativa.

**Capa ausente.** La segmentación de decisiones de AMI existe solo para 6 de las 14 series y
se usa únicamente como subconjunto de validación (documento 07, §4.1; notebook 03, §3.2).

### 7.2 Relevancia para el problema

Los datos sirven al problema porque reúnen tres rasgos: varias reuniones consecutivas por equipo, decisiones ya registradas en el resumen
y un enlace de cada decisión con la conversación que la respalda, cuando existe. Con ellos se
puede estudiar cómo una decisión se retoma, cambia o se revierte en la reunión siguiente
(§2 y §3). La muestra son 14 series con 343 decisiones, elegidas con criterios registrados
antes de anotar y no al azar (documento 07, [§1](07-jss-analisis-exploratorio.md#1-origen-tipo-y-relevancia-de-los-datos)).

Su alcance tiene límites que se declaran: un solo dominio (el diseño de un control remoto),
habla actuada y una muestra no aleatoria, por lo que los resultados describen estas 14 series
y no se extrapolan a otros corpus (documento 07, [§9](07-jss-analisis-exploratorio.md#9-limitaciones); riesgos en §5).

## Glosario breve

| Término | Qué significa en este documento |
|---|---|
| Serie | Cuatro reuniones consecutivas del mismo equipo sobre el mismo producto. Es la unidad con la que se elige y se anota. |
| Capa de anotación | Marcas hechas a mano por los investigadores del corpus sobre la transcripción: resúmenes, enlaces, intervenciones, temas. |
| Resumen abstractivo | El resumen escrito a mano de cada reunión, con un apartado de decisiones. Es el punto de partida de cada decisión, pero puede estar equivocado. |
| Cadena de evidencia | El camino desde una frase del resumen hasta las palabras exactas de la conversación que la respaldan. |
| Par candidato | Dos decisiones de reuniones distintas de la misma serie que el bloqueador considera que podrían estar relacionadas. |
| Bloqueador | Filtro automático que reduce los 3.071 pares posibles a los 92 que una persona revisará. |
| Coeficiente de solapamiento | Proporción de palabras de la frase más corta que también están en la otra. Jaccard, la alternativa, divide por el total de palabras distintas y castiga a las frases cortas. |
| Desarrollo / evaluación | Las series donde se ajusta y se prueba, frente a las series donde sólo se reportan resultados. |
| Kappa | Medida de acuerdo entre dos anotadores que descuenta las coincidencias por azar. |

## Cambios respecto de la propuesta original

| Qué cambió | Evidencia que lo obligó |
|---|---|
| Marco muestral: de 6 series DDS (136 decisiones) a 33 series con resumen abstractivo (649), reduciéndose a 14 series seleccionadas | Medición directa sobre `ami_public_manual_1.6.2`; decisión D1 |
| El balanceo de la muestra es por **sitio**, no por lengua materna | La lengua está perfectamente anidada en el sitio (D7, D8); TS3005/bloque TS entero sin datos en `participants.xml` |
| El eje nativo/no-nativo baja de estratificación obligatoria a limitación declarada | 30,3 % de participantes desconocidos en las 33 series; ver documento 03 y 05 |
| El conteo de candidatos pasó de una extrapolación de ~170 a 92 medidos | El bloqueador con sólo coeficiente daba 712/3.071 (23,2 %); con `\|A∩B\|≥2` añadido, 92 (3,0 %) — D9 |
| El bloqueador usa coeficiente de solapamiento, no Jaccard | Jaccard = 0,118 pierde el par del botón turbo; solapamiento = 0,400 lo captura — D5 |
| La reversión del botón turbo, identificada a ojo en el piloto, resultó **falsa** al contrastar con la transcripción | Documentado en [`../anotacion/manual-anotacion-oe1.md`](../anotacion/manual-anotacion-oe1.md) §3 |

La versión 1.2 cambia la forma de contarlo, no el contenido: las cifras, las decisiones y la
numeración de secciones son las mismas de la versión 1.1.

---

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| Licencia CC BY 4.0 (verificada en la página oficial el 20-09-2026), tamaño del paquete | [`../../config/corpus.toml`](../../config/corpus.toml) |
| Capas: 142/137/47/556/687/54 archivos | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Marco muestral 33/649 vs 6/136; D1, D2 | [`../decisions/README.md`](../decisions/README.md) |
| Selección de 14 series, criterio de balance por sitio | [`../decisions/0004-adr-oe1-series-selection.md`](../decisions/0004-adr-oe1-series-selection.md) |
| Split desarrollo/evaluación, control de doble anotación | [`../decisions/0005-adr-development-evaluation-split.md`](../decisions/0005-adr-development-evaluation-split.md) |
| Los cuatro N (56, 343, 3.071, 92) | [`../../config/corpus.toml`](../../config/corpus.toml), sección `[oe1]`; [`../README.md`](../README.md), sección "Los cuatro N" |
| 91/96/2 participantes; anidamiento lengua/sitio; TS sin `participants.xml` | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Autoría por rol (PM 47,0 % etc.) | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Anclaje a evidencia 317/343 (92,4 %) | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Proxy de tópico: 9,0 % / 16,5 % | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Bloqueador: 712/3.071 con sólo coeficiente, 92 con mínimo absoluto | [`../decisions/README.md`](../decisions/README.md), decisión D9 |
| Botón turbo: falso positivo del resumen abstractivo | [`../anotacion/manual-anotacion-oe1.md`](../anotacion/manual-anotacion-oe1.md) §3 |
| Caso IS1004b → IS1004c no seleccionado por el bloqueador | [`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb) |
| Calidad: faltantes (32/56, 64/224, 26/343), duplicados (4 y 8), atípicos (15 de 56 reuniones; 0 eliminadas, 0 corregidas, 0 imputadas), segmentación en 6 de 14 series | [`07-jss-analisis-exploratorio.md`](07-jss-analisis-exploratorio.md) §4–5; [`../../notebooks/03-jss-eda.ipynb`](../../notebooks/03-jss-eda.ipynb) §2.4, §3, §5 |
