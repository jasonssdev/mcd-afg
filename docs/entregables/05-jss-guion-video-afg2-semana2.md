# Guion — Video de avance #1 de AFG2, semana 2: análisis exploratorio

| | |
|---|---|
| **Entrega** | Video de avance #1 de AFG2 (semana 2) — análisis exploratorio |
| **Fecha de envío** | Pendiente |
| **Versión** | 1.0 |
| **Construido desde** | `docs/avances/01-jss-problema.md` v1.2 · `docs/avances/02-jss-fuente-de-datos.md` v1.3 · `docs/avances/07-jss-analisis-exploratorio.md` v1.0 · `docs/avances/08-jss-metricas-y-criterio-de-exito.md` v1.0 · `notebooks/11-jss-figuras-video-eda.ipynb` (figuras; las cifras provienen del notebook 03) |
| **Duración objetivo** | 7:41 (máximo permitido: 8:00) |
| **Formato** | Tres presentadores en cuatro bloques consecutivos, en este orden: Jason, Germán, Gustavo, Jason. Con diapositivas de apoyo |
| **Extensión hablada** | 1.115 palabras: 329 + 282 + 365 + 139. A 145 palabras por minuto son 7:41; a 140, 7:58 |

> **Por qué existe este documento.** En el video final del primer curso, la retroalimentación
> fue que no se entendió bien. Este guion prioriza la claridad por encima de la cantidad: un
> espectador sin formación técnica, que sabe más o menos de qué trata el proyecto, debe poder
> seguirlo. Por eso cada término técnico se conserva, pero se explica con palabras corrientes
> la primera vez que aparece, y casi cada idea va acompañada de un ejemplo cotidiano o del caso
> del botón turbo. Se dicen pocas cifras en cámara y solo las que cargan el mensaje.

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-10-15 | Versión inicial: guion del primer video de avance de AFG2, centrado en el análisis exploratorio de datos y escrito para una audiencia no técnica. | Rúbrica del video de avance #1 y retroalimentación del video final de AFG1. |

## Qué pide el curso y dónde se cubre

Objetivo del video según la rúbrica: presentar una primera aproximación a los datos del
proyecto, mostrando cómo se organizan, limpian o exploran, y compartir hallazgos iniciales,
dificultades detectadas o preguntas que orientarán el análisis posterior. Formato: máximo 8
minutos, libre, con diapositivas de apoyo.

| Elemento del nivel "logrado" | Dónde se cubre |
|---|---|
| Organización de los datos | Bloque 1 (Jason): cinco niveles, 14 series, 343 decisiones, 3.071 pares; figura 1 |
| Limpieza inicial | Bloque 2 (Germán): faltantes, por qué no se imputa ni se borra nada; figura 2 |
| Visualizaciones o estadística descriptiva | Bloque 2 (figura 3, diagrama de caja con medianas); bloque 3 (figuras 4 y 5, el filtro y su efecto según el largo de la frase) |
| Hallazgos preliminares | Bloque 2 (26 decisiones sin evidencia; la primera reunión tiene menos decisiones); bloque 3 (de 3.071 a 92 pares) |
| Retos encontrados | Bloque 2 (decisiones sin evidencia); bloque 3 (el filtro y las frases cortas, calibrado con un solo caso de control); bloque 4 (resumen) |
| Influencia en los siguientes pasos | Cada bloque cierra con "qué cambia"; bloque 4 los reúne y nombra el criterio de éxito |
| Conexión con el problema de investigación | Bloque 1 (el botón turbo y la pregunta del proyecto); todos los bloques vuelven a ella; bloque 4 cierra con el mismo caso |

## Reparto de tiempos

| Bloque | Persona | Palabras | Tiempo (145 ppm) | Mensaje central |
|---|---|---|---|---|
| Contexto, qué cubre el video y organización de los datos | Jason Sepúlveda | 329 | 0:00 – 2:16 | El botón turbo; qué es un análisis exploratorio; cinco niveles de datos: pocas series, muchos pares |
| Calidad, limpieza inicial y primer hallazgo | Germán Vega | 282 | 2:16 – 4:13 | 26 decisiones sin evidencia; no se inventa ni se borra nada; la primera reunión tiene menos decisiones |
| El filtro léxico y su límite | Gustavo Martínez | 365 | 4:13 – 6:44 | De 3.071 pares a 92 con una regla simple; funciona peor con frases cortas |
| Retos, próximos pasos y cierre | Jason Sepúlveda | 139 | 6:44 – 7:41 | Qué cambia en cada paso; cómo se juzgará el éxito |

Reparto por persona: Jason 468 palabras, Germán 282, Gustavo 365. Jason abre y cierra porque
presenta el contexto y reúne los pasos siguientes; el filtro léxico, que es lo más difícil de
explicar, queda completo en un solo bloque a cargo de Gustavo.

## Notas de grabación

- El texto está escrito para decirse, no para leerse. Frases cortas, una idea por oración. Las
  palabras en **negrita** se apoyan con la voz.
- Cada bloque abre nombrando a quien habla y cierra pasando el turno.
- Cada término técnico se explica en la misma oración en que aparece. Si al ensayar una frase
  necesita que la audiencia ya sepa algo, se reescribe.
- Cronometrar un ensayo completo antes de grabar. El margen sobre el tope de 8:00 es de unos
  19 segundos a 145 palabras por minuto y de solo 2 segundos a 140. Hablar a un ritmo ágil y
  sin pausas largas entre bloques. La frase sobre Jaccard (bloque 3) y la de los valores
  atípicos (bloque 2) ya se recortaron por tiempo; ambas siguen explicadas en el avance 07.
- Las líneas que empiezan con ▶ no se dicen: marcan el momento exacto en que cambia la lámina,
  con la figura que corresponde.
- No recortar los ejemplos cotidianos (el botón turbo, las dos frases del ejemplo del filtro,
  "cambiar color"): son lo que hace entendible cada bloque.
- Las cifras de este guion salen de `docs/avances/07-jss-analisis-exploratorio.md` y del
  notebook 11. Ninguna se calcula aquí.

---

## Bloque 1 — Jason Sepúlveda (0:00 – 2:16)

### Texto hablado

Hola. Soy **Jason Sepúlveda**. Junto a **Germán Vega** y **Gustavo Martínez** presentamos el avance de nuestro proyecto.

Primero, en pocas palabras, de qué trata el proyecto. Cuando un equipo se reúne varias veces, sus decisiones cambian de una reunión a otra. Si después alguien le pregunta a un asistente de inteligencia artificial qué se decidió, lo común es que el asistente busque los trozos de conversación más parecidos a la pregunta, y así puede encontrar la versión antigua de la decisión. Nuestro proyecto compara esa forma de buscar con una **memoria ordenada** de las decisiones, que registra cómo fue cambiando cada una. La pregunta es: ¿cuál responde mejor cuando una decisión cambió?

> **▶ Lámina de título: «¿Se eliminó el botón turbo? Resumen: sí. Grabación: no.»**

Saber cuál es la respuesta correcta no es trivial. En un caso real de nuestros datos, un equipo diseña un control remoto en cuatro reuniones. El resumen oficial dice que se eliminó el botón "turbo", pero en la grabación el botón se mantuvo. Por eso, antes de comparar, hay que conocer muy bien los datos.

Este avance muestra cómo son nuestros datos antes de usarlos. Es decir hicimos un **análisis exploratorio**: mirar los datos con calma, como revisar los ingredientes antes de cocinar. Veremos cómo están organizados, qué problemas de calidad tienen y qué hacemos con ellos, qué encontramos al describirlos, y qué dificultades aparecieron y cómo cambian los próximos pasos.

> **▶ Figura 1 — se muestra al decir «Empiezo por la organización».**
>
> ![Los datos se organizan en cinco niveles: 14 series, 56 reuniones, 224 hablantes en una reunión, 343 decisiones y 3.071 pares](figuras/eda-estructura-de-los-datos.png)

Empiezo por la organización. Usamos reuniones públicas, grabadas y transcritas. Cada equipo se reúne cuatro veces, y esas cuatro reuniones forman una **serie**. Tenemos 14 series, o sea 56 reuniones, con 343 decisiones. Cada decisión es una frase del resumen de la reunión, por ejemplo "el control tendrá un botón turbo".

Para saber si una decisión cambió, hay que compararla con otra de una reunión anterior. A cada comparación la llamamos **par de decisiones**, y hay 3.071. Pocas series, muchísimos pares. Pero esos pares comparten decisiones, así que el tamaño real de la muestra son las 14 series.

Germán sigue con la calidad de los datos.

### Lámina

Figura: `figuras/eda-estructura-de-los-datos.png`. En pantalla, tres frases cortas: "14 series · 343 decisiones · 3.071 pares", "Pocas series, muchos pares", "La unidad real de la muestra: la serie".

Nota de entrega: durante la historia del botón turbo puede mostrarse una lámina de título con la frase "¿Se eliminó el botón turbo?" y, bajo ella, "Resumen: sí. Transcripción: no".

---

## Bloque 2 — Germán Vega (2:16 – 4:13)

### Texto hablado

Gracias, Jason. Soy **Germán Vega**. Hablo de la calidad de los datos y de un primer hallazgo.

Un **valor faltante** es una casilla vacía en una tabla. Revisamos las 77 variables, que son las columnas que describen cada registro, como la duración de una reunión. Solo tres tienen casillas vacías. Dos son datos sueltos, como la hora de inicio, que no afectan nuestro trabajo. La tercera sí importa.

> **▶ Figura 2 — se muestra al decir «Es la evidencia de una decisión».**
>
> ![Proporción de decisiones sin evidencia según la posición de la reunión: 0 % en a, 4,7 % en b, 11,2 % en c y 11,5 % en d](figuras/eda-decisiones-sin-evidencia-por-posicion.png)

Es la **evidencia** de una decisión: las intervenciones de la conversación que la respaldan. De 343 decisiones, 26 no tienen ninguna. No faltan al azar: en la primera reunión no falta ninguna, y desde la tercera, alrededor de 11 de cada 100. Una de ellas es la del botón turbo equivocado. Es una sospecha, no un resultado: con un solo caso no podemos decir que todas sean errores.

¿Qué hacemos? No **imputamos**, es decir, no llenamos esas casillas con un valor estimado: sería inventar un respaldo que no existe. Tampoco borramos nada. Las marcamos y las revisaremos a mano.

> **▶ Figura 3 — se muestra al decir «Ahora, un primer hallazgo».**
>
> ![Diagrama de caja del número de decisiones por reunión según su posición en la serie: la mediana es 3,5 en a, 8,0 en b, 6,5 en c y 7,0 en d](figuras/eda-decisiones-por-posicion.png)

Ahora, un primer hallazgo. Este es un **diagrama de caja**. La caja encierra a la mitad central de las reuniones, y la línea gruesa marca la **mediana**: el valor del medio, que deja a la mitad de las reuniones con menos decisiones y a la otra mitad con más. La primera reunión tiene una mediana de 3,5 decisiones. Las otras tres, 8,0, 6,5 y 7,0: la primera tiene cerca de la mitad.

Por eso, las preguntas sobre cómo evoluciona una decisión se apoyarán sobre todo en las reuniones b, c y d. Aún no sabemos si esto se debe al diseño del escenario o a un cambio real.

Gustavo explica cómo elegimos qué pares revisar.

### Láminas

Figura 2: `figuras/eda-decisiones-sin-evidencia-por-posicion.png`. En pantalla: "26 de 343 decisiones sin evidencia", "No se imputa, no se borra: se marca".

Figura 3: `figuras/eda-decisiones-por-posicion.png`. En pantalla: "Mediana de decisiones por reunión: 3,5 frente a 8,0 · 6,5 · 7,0", "Las preguntas de evolución se apoyan en b, c y d".

Nota de entrega: cambiar de la figura 2 a la figura 3 al decir "Ahora, un primer hallazgo". Al explicar el diagrama de caja, señalar con el cursor la línea gruesa de la reunión a y luego la de la b. El diagrama de caja es lo más abstracto del video: decir la explicación despacio.

---

## Bloque 3 — Gustavo Martínez (4:13 – 6:44)

### Texto hablado

Gracias, Germán. Soy **Gustavo Martínez**. Explico el paso que más condiciona el proyecto.

Una persona tiene que revisar cada par y decidir si una decisión cambia, revierte o repite a la otra. Son 3.071 pares: unas 77 horas de trabajo. Y casi todos no tienen relación: "el control será amarillo" frente a "la reunión termina a las cinco".

Nuestra idea: si dos decisiones hablan de lo mismo, probablemente comparten palabras. Antes de que una persona mire un par, una regla automática descarta los que casi no comparten palabras. Es un **filtro léxico**, porque solo mira palabras. No da la respuesta; solo decide qué pares vale la pena revisar.

Primero se quitan las palabras que no dicen nada del tema, como "de" o "el". Quedan las **palabras de contenido**. Luego se mide el parecido con el **coeficiente de solapamiento**: palabras compartidas, divididas por las palabras de la frase más corta. Es decir, ¿qué parte de la frase corta está dentro de la larga?

> **▶ Lámina del ejemplo: las dos frases con «botón» y «turbo» resaltadas y la cuenta «2 ÷ 3 = 0,67».**

Un ejemplo. Frase larga: "el control tendrá rueda de desplazamiento, pantalla, botón turbo, botón de encendido y carcasa amarilla". Frase corta: "se elimina el botón turbo". La corta tiene tres palabras de contenido y comparte dos. Dos entre tres: 0,67, sobre el umbral de 0,30. Pasa.

Pero con frases muy cortas el coeficiente se infla: "cambiar color" frente a "el color del logo es azul" da 0,50 con una sola palabra en común. Por eso exigimos además dos palabras compartidas.

> **▶ Figura 4 — se muestra al decir «Resultado».**
>
> ![Embudo del filtro: 3.071 pares (76,8 horas), 712 con el coeficiente solo (17,8 horas) y 92 con el coeficiente más 2 palabras en común (2,3 horas); el par de control del botón turbo se conserva](figuras/eda-embudo-del-filtro-lexico.png)

Resultado: de 3.071 pares quedan 92, y las horas bajan de unas 77 a unas 2,3. El par del botón turbo se conserva.

> **▶ Figura 5 — se muestra al decir «Pero hay un límite».**
>
> ![Porcentaje de pares que pasan cada criterio según las palabras de contenido de la decisión más corta del par: con 2 y 3 palabras el coeficiente solo deja pasar 36,6 % y 42,1 %, y el filtro completo 0,3 % y 2,0 %](figuras/eda-filtro-segun-longitud-de-frase.png)

Pero hay un límite. En este gráfico, la línea naranja es el coeficiente solo y la verde, el filtro completo. Con una frase de tres palabras, el coeficiente solo deja pasar 42,1 % de los pares, casi la mitad y por casualidad; el filtro completo, 2,0 %. Corrige el exceso, pero casi no deja pasar pares entre frases cortas, y las reversiones suelen ser cortas. Además, lo calibramos con un solo par de control, el del botón turbo. Por eso 92 es lo máximo que el filtro deja anotar, no el total de relaciones que existen.

Jason resume qué sigue.

### Láminas

Figura 4: `figuras/eda-embudo-del-filtro-lexico.png`. En pantalla: "De 3.071 pares a 92", "≈ 77 horas → ≈ 2,3 horas", "El par del botón turbo se conserva". Antes del gráfico, una lámina con el ejemplo de las dos frases y la cuenta "2 ÷ 3 = 0,67" (frases del ejemplo ilustrativo de `docs/avances/07-jss-analisis-exploratorio.md` §7.3).

Figura 5: `figuras/eda-filtro-segun-longitud-de-frase.png`. En pantalla: "Frases cortas: el filtro casi no deja pasar pares", "Calibrado con un solo par de control", "92 es un máximo, no el total de relaciones".

Nota de entrega: es el bloque más denso. Hacer una pausa breve después de "0,67". En el ejemplo, mostrar en la lámina las palabras compartidas ("botón", "turbo") resaltadas. Las cifras 36,6 % y 0,3 % se quedan en la imagen; en la voz solo 42,1 % y 2,0 %.

---

## Bloque 4 — Jason Sepúlveda (6:44 – 7:41)

### Texto hablado

Gracias, Gustavo. Cierro con lo que cambia para los próximos pasos.

> **▶ Lámina de cierre con los cuatro pasos (ver abajo).**

Primero, las 26 decisiones sin evidencia se revisarán a mano. Segundo, las preguntas sobre cambios se apoyarán en las reuniones b, c y d. Tercero, mantendremos el filtro, declararemos que puede perder relaciones entre frases cortas y mediremos cuántas pierde. Esa medida se llama **recall**: de todas las relaciones reales, qué parte deja pasar el filtro. Para medirla, nuestro equipo anotará una muestra de pares que el filtro rechazó, ya generada. Cuarto, como son solo 14 series, informaremos qué tan grande es cada diferencia, y no solo si existe.

El éxito del experimento se juzgará con una regla fijada antes de ver los resultados.

Todo parte de lo que nos enseñó el botón turbo: los números por sí solos no encuentran un error de sentido. Hay que leer.

### Lámina

Sin figura nueva. Lámina de cierre con cuatro líneas, una por paso: "Revisar a mano las 26 decisiones sin evidencia", "Preguntas de evolución sobre las reuniones b, c y d", "Mantener el filtro, declarar su sesgo y medir su recall", "Informar el tamaño de cada diferencia". Opcional: volver a la lámina de título del bloque 1 ("¿Se eliminó el botón turbo?") durante la última frase.

Nota de entrega: pasar despacio por los cuatro pasos y mirar a cámara en la frase final.

---

## Trazabilidad de las cifras dichas en cámara

| Cifra | Dónde se verifica |
|---|---|
| El botón turbo: el resumen afirma una eliminación que la transcripción contradice | `docs/avances/07-jss-analisis-exploratorio.md`, "Un caso real para empezar"; `docs/avances/01-jss-problema.md` |
| 14 series, 56 reuniones, 343 decisiones, 3.071 pares | `docs/avances/07-jss-analisis-exploratorio.md` §2; notebook 11, figura 1 |
| 77 variables; solo tres con casillas vacías | `docs/avances/07-jss-analisis-exploratorio.md` §3 y §4.1 |
| 26 de 343 decisiones sin evidencia; 0 % en la reunión a y alrededor de 11 % desde la c | `docs/avances/07-jss-analisis-exploratorio.md` §4.1; notebook 11, figura 2 |
| No se imputa ni se elimina nada | `docs/avances/07-jss-analisis-exploratorio.md` §4.2 y §5 |
| Medianas de decisiones por reunión: 3,5 frente a 8,0, 6,5 y 7,0 | `docs/avances/07-jss-analisis-exploratorio.md` §6.2; notebook 11, figura 3 |
| 77 horas a 1,5 minutos por par; 92 pares y 2,3 horas | `docs/avances/07-jss-analisis-exploratorio.md` §7.1 y §7.3; notebook 11, figura 4 |
| Ejemplo ilustrativo: 2 ÷ 3 = 0,67 con el coeficiente; "cambiar color" = 0,50; umbral de 0,30 y 2 palabras | `docs/avances/07-jss-analisis-exploratorio.md` §7.3 (ejemplos ilustrativos, no datos del corpus) |
| 42,1 % frente a 2,0 % con frases de tres palabras | `docs/avances/07-jss-analisis-exploratorio.md` §7.6; notebook 11, figura 5 |
| Filtro calibrado con un solo par de control; 92 es un máximo | `docs/avances/07-jss-analisis-exploratorio.md` §7.4 |
| Muestra de pares rechazados, generada y sin anotar (Tarea C) | `docs/avances/07-jss-analisis-exploratorio.md` §7.5 |
| Criterio de éxito fijado antes de correr el experimento | `docs/avances/08-jss-metricas-y-criterio-de-exito.md` §2.1 |
