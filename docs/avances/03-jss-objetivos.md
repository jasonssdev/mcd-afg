# Objetivos

| | |
|---|---|
| **Documento** | 03 — Objetivos |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 2.2 |
| **Fecha** | 2026-10-01 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial. Objetivos e hipótesis para AFG1. | Primera entrega del curso. |
| 2.0 | 2026-09-20 | Alcance por curso y cambios de H3 | Plan realista para tres cursos y reconciliación de la escala de modelo configurada |
| 2.1 | 2026-09-20 | Aporte propositivo explícito; origen de la observación de H3; punto de decisión de AFG2; nota de sincronización del plan | Revisión final de AFG1 |
| 2.2 | 2026-10-01 | Reescritura completa de la redacción: cada objetivo se presenta desde la pregunta que responde, cada término técnico se explica al aparecer y se agrega un glosario breve. El objetivo general, los objetivos específicos, los criterios de cumplimiento, las hipótesis y las cifras no cambian. | Retroalimentación de la revisión entre equipos de la semana 8: el problema y la metodología no se entendían, menos aún para una audiencia no técnica. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## Qué se quiere saber, en pocas palabras

El documento 01 termina con una pregunta: cuando un equipo toma decisiones a lo largo de
varias reuniones, ¿conviene construir una base donde cada decisión quede registrada con su
historia, o basta con buscar en las transcripciones cada vez que alguien pregunta? Y si
conviene construirla, ¿cuánto se pierde cuando la construye una máquina que se equivoca?

Para responder hace falta un experimento con todo lo demás igual. Este documento fija qué
se va a medir, en qué orden, qué se considera cumplido en cada paso y qué se espera
encontrar. Está escrito antes de ejecutar nada, a propósito: así los resultados no pueden
reinterpretarse después para que parezcan lo que se buscaba.

## Objetivo general

Diseñar, implementar y evaluar experimentalmente un método de extracción automática y
representación persistente de decisiones organizacionales —incluyendo su evolución a través
de reuniones sucesivas— utilizando modelos de lenguaje de ejecución local, con el fin de
**cuantificar por separado** el valor aportado por la representación, el costo introducido
por los errores de su extracción automática, y las condiciones bajo las cuales el resultado
neto supera a un sistema RAG aplicado directamente sobre las transcripciones originales.

Dicho sin tecnicismos: se construye un sistema que lee transcripciones de reuniones, saca
de ellas las decisiones y las guarda en una base con sus relaciones (qué decisión cambió a
cuál). Se hace con modelos de lenguaje que corren en un computador propio, sin enviar datos
a servicios externos. Y se mide, por separado, tres cosas: cuánto ayuda tener esa base,
cuánto daño hacen los errores que la máquina comete al construirla, y en qué casos el saldo
final es mejor que la práctica actual, que es buscar directamente en las transcripciones con
RAG (la técnica que recupera fragmentos de texto parecidos a la pregunta y redacta una
respuesta con ellos; documento 01, §2).

### Qué propone este proyecto, además de medir

El aporte no es solo una medición. El proyecto propone cuatro cosas que no existen en el
estado del arte revisado:

1. Un **conjunto de referencia con enlaces tipados entre decisiones de reuniones
   sucesivas** sobre un corpus real. Es un conjunto de reuniones donde personas marcaron a
   mano qué decisiones hay y cómo se relacionan entre reuniones (por ejemplo, "esta
   decisión revierte aquella"). Ninguna capa de anotación publicada lo ofrece.
2. Un **diseño de tres condiciones** que separa el valor de la representación del costo de
   su extracción, en lugar de comparar sistemas completos. Se explica en OE3.
3. Una **taxonomía determinista de atribución de error** (extracción, recuperación,
   síntesis): un procedimiento con reglas fijas para decir, ante cada respuesta equivocada,
   en qué etapa del sistema nació el error. Es aplicable a cualquier sistema que persista
   conocimiento extraído.
4. El **punto de equilibrio amortizado** como métrica operativa de decisión, en lugar de la
   latencia aislada: no cuánto tarda una consulta, sino a partir de cuántas consultas
   compensa haber construido la base.

La medición es lo que permite evaluar esas propuestas; las propuestas son el aporte.

## Objetivos específicos

Los cuatro objetivos específicos son cuatro pasos en orden. Cada uno necesita el anterior.
Primero se construye la referencia contra la que se mide todo (OE1). Después se mide qué tan
bien extrae la máquina (OE2). Luego se compara el sistema completo contra las alternativas
(OE3). Y al final se explica cada error (OE4).

### OE1 — Construir un conjunto de referencia de decisiones con evolución entre reuniones

**La pregunta.** ¿Contra qué se compara lo que extrae la máquina? Hace falta una "respuesta
correcta" por cada reunión: la lista de decisiones y, para cada par de reuniones de la misma
serie, qué decisión revisa a cuál.

**Qué se hace.** Se deriva un conjunto de referencia a partir de las capas de anotación ya
existentes en AMI (resumen abstractivo, `summlink`, capa DDS como validación; documento 02,
§3), extendiéndolas con la única anotación que el corpus no posee: el enlace temporal entre
reuniones. Cada enlace lleva una etiqueta de un conjunto cerrado,
`{ introduce, reafirma, refina, revierte, reemplaza, no-relacionada }`, y evidencia
obligatoria (reunión y rango de actos de diálogo): el anotador tiene que señalar el pasaje
exacto que respalda la etiqueta.

**Las etiquetas las pone un humano, nunca un modelo.** Esta regla sostiene todo el diseño.
Si un modelo de lenguaje construyera OE1, la condición C3 (la base construida desde esta
anotación; ver OE3) tendría errores de extracción por construcción, y la brecha C2 − C3, que
es todo OE4, dejaría de medir nada: se estaría comparando los errores de una máquina contra
los errores de otra. Los modelos sólo pueden proponer candidatos, resolver evidencia y
calcular acuerdo; nunca decidir si algo es una decisión.

**Confiabilidad declarada, no asumida.** El documento 01 muestra que dos equipos expertos no
coincidieron en qué era una decisión. Por eso no basta con que una persona anote: hay que
medir cuánto coinciden dos personas. Doble anotación independiente sobre el 36,4 % de la
evaluación (≥25 % exigido), kappa de Cohen reportado por separado para existencia, tipo y
dirección de la relación, y protocolo de adjudicación documentado. Kappa es la medida de
acuerdo que descuenta las coincidencias por azar; se reporta por separado porque es más
fácil coincidir en que dos decisiones se relacionan que en el tipo exacto de relación, y
mezclar las tres preguntas en una sola cifra ocultaría dónde está el desacuerdo.

**Criterio de cumplimiento:** el conjunto de referencia existe para las 14 series (343
decisiones, 92 pares candidatos adjudicados), con kappa reportado en los tres niveles y
adjudicación documentada para todo desacuerdo.

### OE2 — Medir la calidad de la extracción automática (Experimento A)

**La pregunta.** Cuando un modelo de lenguaje lee una transcripción, ¿encuentra las mismas
decisiones que encontró una persona? ¿Y detecta igual de bien que una decisión posterior
cambió a una anterior?

**Qué se hace.** Se cuantifica la capacidad de modelos de lenguaje de ejecución local para
extraer decisiones y sus relaciones temporales, contra el conjunto de referencia de OE1.

- **Nivel decisión:** precisión, cobertura y F1. Precisión es qué proporción de lo que la
  máquina extrajo era realmente una decisión; cobertura, qué proporción de las decisiones
  reales encontró; F1 combina ambas en un solo número. Para decidir si una decisión extraída
  "es la misma" que una de la referencia, se usa el protocolo de alineamiento del documento
  06 (asignación húngara, curva sobre τ): se emparejan las decisiones de la máquina con las
  de la referencia buscando la mejor correspondencia global, y se reporta cómo cambia el
  resultado según cuán estricto sea el parecido exigido (τ).
- **Nivel relación temporal:** exactitud de la etiqueta y, reportada por separado, exactitud
  de la **dirección**: si el sistema identifica correctamente cuál decisión revisa a cuál.
  Decir que dos decisiones se relacionan es una cosa; decir cuál vino después y cambió a la
  otra es otra, y se espera que sea más difícil (H3).
- **Estratificación obligatoria por rol del hablante.** Los resultados se desglosan según
  quién enunció la decisión (jefe de proyecto, diseñador, etc.), porque el documento 05
  muestra que el reparto es muy desigual. El eje nativo/no-nativo de inglés **ya no es
  estratificación obligatoria**: pasa a limitación declarada (ver "Cambios" abajo y el
  documento 05, §2).

**Criterio de cumplimiento:** P/R/F1 a nivel decisión reportados como curva sobre τ;
exactitud de tipo y de dirección reportadas por separado; desglose por rol publicado aunque
no se detecte diferencia.

### OE3 — Medir la utilidad funcional en tres condiciones (Experimento B)

**La pregunta.** Al final, lo que importa es si alguien que pregunta "¿qué decidimos sobre
el botón turbo y por qué cambiamos?" recibe una respuesta correcta y con fuente. ¿Lo hace
mejor un sistema con base de decisiones que uno que busca en las transcripciones?

**Qué se hace.** Se compara el desempeño frente a un mismo banco de preguntas estratificado,
bajo tres condiciones que comparten modelo generativo, modelo de *embeddings*, hardware y
presupuesto de contexto. Todo lo demás igual: si una condición responde mejor, la única
explicación posible es cómo organiza la información.

| | Condición | Rol |
|---|---|---|
| **C1** | RAG documental sobre las transcripciones originales | Piso — la práctica actual |
| **C2** | Base estructurada construida automáticamente | La propuesta bajo evaluación |
| **C3** | Base estructurada construida desde la anotación de OE1 | Referencia superior, no "techo teórico" |

Las tres condiciones se leen juntas. C1 es lo que haría hoy cualquier organización: buscar
en las transcripciones. C2 es la propuesta: la misma base de decisiones, construida por la
máquina. C3 es esa misma base, pero construida desde la anotación humana de OE1, es decir,
sin errores de extracción. La distancia entre C1 y C3 mide cuánto vale tener la base. La
distancia entre C3 y C2 mide cuánto cuestan los errores de la máquina al construirla. Sin
C3, una comparación C1 contra C2 no podría distinguir ambas cosas; ese es el límite de los
trabajos previos que el documento 01 señala.

Las preguntas del banco se agrupan en estratos, es decir, en tipos: desde el hecho puntual
("¿qué se decidió sobre X?", E1) hasta la evolución ("¿cómo cambió la decisión sobre X entre
reuniones?", E3), pasando por un estrato de preguntas incontestables (E4), que sirven para
comprobar que el sistema sabe decir "no hay información" en lugar de inventar.

Métricas de calidad: corrección de la respuesta, tasa de soporte de evidencia (si la
respuesta viene acompañada de un pasaje que la respalda), tasa de citación correcta (si ese
pasaje es realmente el que corresponde), y corrección del rechazo ante preguntas
incontestables (estrato E4). Métricas operativas: memoria residente, y **costo amortizado**:
el punto de equilibrio en número de consultas a partir del cual compilar y consultar es más
barato que consultar siempre por RAG. Construir la base cuesta una vez; cada consulta sobre
ella cuesta menos que una consulta RAG. La pregunta es a partir de cuántas consultas se
recupera la inversión.

**Criterio de cumplimiento:** las tres condiciones evaluadas sobre el mismo banco de
preguntas estratificado (E1–E4, ≥25 por estrato), con intervalos de confianza por *bootstrap*
reportados para cada métrica. El *bootstrap* es un procedimiento que repite el cálculo muchas
veces sobre muestras tomadas al azar del mismo banco, para saber cuánto podría variar el
resultado con otras preguntas parecidas.

### OE4 — Atribuir el error final a su etapa de origen

**La pregunta.** Cuando C2 responde mal, ¿dónde nació el error? Saberlo cambia qué conviene
mejorar: no es lo mismo que la máquina haya anotado mal una decisión, que la haya anotado
bien pero no la haya encontrado al responder, o que la haya encontrado y aun así haya
redactado algo que la contradice.

**Qué se hace.** Para cada respuesta incorrecta o sin soporte de C2, se determina si el
error se originó en la **extracción** (el hecho quedó mal escrito en la base), la
**recuperación** (el hecho correcto existía pero no fue recuperado) o la **síntesis** (el
material correcto fue recuperado y la respuesta lo contradice), mediante el procedimiento
determinista del documento 06 §7. Determinista quiere decir que son reglas fijas aplicadas
en orden, no un juicio caso a caso.

**Criterio de cumplimiento:** toda respuesta fallida de C2 queda clasificada en una y sólo
una de las tres categorías, con la proporción atribuible a extracción reportada como cifra
principal (documento 05, principio de responsabilidad). Esa proporción es la cifra
principal porque es el error que se escribe una vez y se lee muchas veces: el riesgo propio
de construir una base.

## Alcance por curso

El proyecto se desarrolla a lo largo de tres cursos. El reparto es el siguiente:

| Curso | Qué se entrega | Objetivos |
|---|---|---|
| **AFG1** | Problema, estado del arte, metodología, ética, conjunto de referencia listo para anotar (herramientas de OE1) y anotación iniciada en desarrollo | OE1 (herramientas) |
| **AFG2** | OE1 cerrado (anotación + kappa); OE2 sobre las 14 series con una escala de modelo (3 corridas); OE3 con banco de preguntas ≥100 y las tres condiciones, versión mínima | OE1, OE2, OE3 (mínimo) |
| **AFG3** | OE4, análisis de errores, intervalos bootstrap, conclusiones | OE4 |

Extensiones si hay tiempo: segunda escala de modelo (H3), validación humana ampliada.

> La versión canónica de esta tabla está en `README.md` (sección "Plan por curso"). Si
> cambia, se actualiza en ambos lugares.

**Punto de decisión en AFG2.** El riesgo mayor del plan es que el instrumento no funcione a
tiempo. Por eso hay una fecha fija para comprobarlo: al cierre de la semana 3 de AFG2, el
adaptador de OpenKOS (el sistema que construye la base de decisiones en C2) debe correr de
punta a punta sobre las tres series de desarrollo (extracción, persistencia y consulta). Si
no lo hace, OE3 se reduce a comparar **C1 contra C3** (el valor de la representación sin
errores de extracción) y OE4 se pospone a AFG3 o se declara fuera de alcance. La decisión se
toma en esa fecha y se registra en `docs/decisions/`, no se descubre en la semana 7.

| Objetivo | Mínimo comprometido | Extensión |
|---|---|---|
| **OE1** | 14 series anotadas, kappa en 3 niveles, adjudicación | — |
| **OE2** | Una escala (qwen3:8b o equivalente), 3 corridas, curva sobre τ, desglose por rol | Segunda escala |
| **OE3** | Banco ≥100 preguntas (25 × 4 estratos), tres condiciones, juez automático con validación humana del 20 % | Validación humana ampliada |
| **OE4** | Clasificación determinista de todas las respuestas fallidas de C2 | — |

"Escala" se refiere al tamaño del modelo de lenguaje, medido en miles de millones de
parámetros; "corridas" son repeticiones completas del experimento con el mismo modelo, para
ver cuánto varía. El "juez automático" es un segundo modelo que califica si una respuesta es
correcta, y la validación humana del 20 % comprueba que ese juez califica como lo haría una
persona.

## Hipótesis

Declaradas antes de la ejecución para evitar reinterpretación posterior. Una hipótesis es
una apuesta escrita de antemano sobre lo que se va a encontrar; si el resultado la
contradice, el resultado igual vale, y se dice.

| | Hipótesis | Fundamento |
|---|---|---|
| **H1** | C2 y C3 superarán a C1 en preguntas de evolución (E3), con diferencia pequeña o nula en hecho puntual (E1) | La ventaja de la representación es relacional |
| **H2** | La brecha C3 − C2 será mayor en relaciones temporales que en identificación de decisiones | Extraer que algo se decidió es más fácil que extraer correctamente que una decisión reemplaza a otra |
| **H3** | La dirección de las relaciones temporales será un modo de falla dominante, sin mejora proporcional al tamaño del modelo | Observación informal en el instrumento a dos escalas (≈8B y ≈30B): alrededor de un 25 % de direcciones invertidas, sin mejora clara con la escala. Es una observación previa, no una medición del proyecto; la segunda escala es una extensión. |
| **H4** | C1 mostrará mayor tasa de respuestas confiadas pero desactualizadas en preguntas de evolución | Consistente con lo reportado en la literatura de recuperación insuficiente |

En palabras llanas: se espera que la base de decisiones ayude sobre todo cuando la pregunta
es sobre cómo cambió algo, y poco cuando es un dato suelto (H1). Se espera que la máquina se
equivoque más al decir cómo se relacionan dos decisiones que al detectarlas (H2), y que su
error más frecuente sea invertir la dirección: decir que A cambió a B cuando fue al revés
(H3). Y se espera que el sistema que busca en las transcripciones responda con seguridad
cosas que ya quedaron desactualizadas (H4), como el resumen del botón turbo del documento
01.

**Origen de la observación de H3.** Proviene de corridas informales previas de OpenKOS
realizadas por Jason Sepúlveda antes de este proyecto, sin registro en este repositorio. Por
eso no se cita como cifra del proyecto ni entra en ningún notebook: es la motivación de la
hipótesis, no evidencia. La medición formal es OE2.

**Plan ante resultado negativo.** Si H1 no se sostiene —si RAG documental iguala a la
representación estructurada incluso en preguntas de evolución—, el resultado es igualmente
publicable: sería la primera medición controlada que acota el valor de compilar en este
dominio. Ninguna conclusión del proyecto depende de que la representación estructurada gane;
el aporte es la medición, no el sistema.

**Nota provisional sobre E3.** El estrato E3, el de las preguntas sobre evolución, necesita
≥25 preguntas, y para escribirlas hacen falta relaciones reales entre decisiones. ¿Hay
suficientes? La evidencia disponible —11 candidatos de desarrollo adjudicados por máquina,
tasa de positivos 45,5 % (5/11), IC 95 % Wilson [21,3 % – 72,0 %], proyectado a evaluación
~37 relaciones, IC [17 – 58]— hace a E3 **plausible, no demostrado**: el valor central
alcanza el mínimo, la cota inferior del intervalo no. El intervalo de confianza (IC) expresa
el rango en que podría estar la cifra real dado lo poco que se ha visto; con 11 casos, ese
rango es ancho. Estas etiquetas fueron puestas por una máquina, sirven sólo para decidir si
vale la pena anotar, y no son el conjunto de referencia de OE1.

## Glosario breve

| Término | Qué significa en este documento |
|---|---|
| Conjunto de referencia | Las decisiones y relaciones marcadas a mano contra las que se mide todo lo demás. Es OE1. |
| C1, C2, C3 | Las tres condiciones que se comparan: buscar en las transcripciones (C1), base construida por la máquina (C2), base construida desde la anotación humana (C3). |
| Precisión, cobertura, F1 | De lo extraído, cuánto era correcto; de lo correcto, cuánto se extrajo; y la combinación de ambas. |
| τ (tau) | El umbral de parecido a partir del cual dos decisiones se consideran la misma. Los resultados se reportan para varios valores. |
| Estrato (E1–E4) | Tipo de pregunta del banco, desde el hecho puntual (E1) hasta las preguntas incontestables (E4), pasando por las de evolución (E3). |
| Costo amortizado | A partir de cuántas consultas compensa haber construido la base. |
| Intervalo de confianza | El rango en que podría estar la cifra real, dado el tamaño de la muestra. |

## Cambios respecto de la propuesta original

| Qué cambió | Evidencia que lo obligó |
|---|---|
| OE2 ya no exige estratificación obligatoria por condición nativo/no-nativo de inglés | La lengua materna está anidada en el sitio de grabación y el bloque TS carece de dato de lengua (documento 02, §4.5; documento 05, §2) — decisión D7 |
| La base de OE1 pasó de 6 series / 136 decisiones a 14 series / 343 decisiones | Marco muestral revisado (documento 02, §4.1) — decisión D1 |
| La viabilidad de E3 se declara explícitamente provisional, con intervalo de confianza | Adjudicación de desarrollo (11 candidatos), no de evaluación — `notebooks/01-jss-viabilidad-e3.ipynb` |
| La segunda escala de modelo pasa de compromiso a extensión | Costo de cómputo local y prioridad del mínimo viable por curso |

La versión 2.2 cambia la forma de contarlo, no el contenido: el objetivo general, los
objetivos específicos, los criterios de cumplimiento, las hipótesis y las cifras son los
mismos de la versión 2.1.

---

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| Objetivo general y OE1–OE4 | [`../propuesta.md`](../propuesta.md) §2–§3 |
| Hipótesis H1–H4 y plan ante resultado negativo | [`../propuesta.md`](../propuesta.md) §4 |
| Cambio de estratificación de OE2 (D7) | [`../decisions/README.md`](../decisions/README.md) |
| 343 decisiones, 92 candidatos | [`../../config/corpus.toml`](../../config/corpus.toml), sección `[oe1]` |
| Viabilidad de E3: 45,5 % (5/11), IC [21,3 % – 72,0 %], proyección ~37 [17–58] | [`../../notebooks/01-jss-viabilidad-e3.ipynb`](../../notebooks/01-jss-viabilidad-e3.ipynb) |
| Plan por curso | README.md, sección Plan por curso; programa del curso (objetivos de AFG1, AFG2, AFG3) |
| Botón turbo como ejemplo de respuesta desactualizada | [`02-jss-fuente-de-datos.md`](02-jss-fuente-de-datos.md) §5 |
