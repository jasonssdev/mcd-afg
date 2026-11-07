# Resultados del Experimento A (OE2)

| | |
|---|---|
| **Documento** | 11 — Resultados del Experimento A (OE2) |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.0 |
| **Fecha** | 2026-11-07 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-11-07 | Versión inicial. Resultados de la corrida formal del Experimento A (`experimento-a-formal`) sobre las once series de evaluación, con la validación manual de la alineación. | La corrida formal y su validación quedaron completas (issues #289 y #290) y ningún documento reportaba aún estos resultados. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

> **Alcance.** Este documento reporta solo el Experimento A. Los resultados del Experimento B
> (OE3 y OE4) se reportan en el avance 12 y no se anticipan aquí. Las series son de
> **evaluación**: se muestran identificadores de serie y cifras agregadas, nunca frases de
> decisión ni contenido de transcripciones ([ADR 0005](../decisions/0005-adr-development-evaluation-split.md)).
> Cada cifra remite al [notebook 28](../../notebooks/28-jss-experimento-a.ipynb) (sección
> indicada entre paréntesis) o a los archivos versionados que ese notebook lee.

## En una página

- **La pregunta.** Cuando un modelo de lenguaje local lee las transcripciones de reuniones,
  ¿encuentra las mismas decisiones que encontraron personas? ¿Y encuentra las relaciones entre
  decisiones (por ejemplo, «esta decisión reemplaza a aquella»)?
- **Decisiones.** Con el criterio principal, la máquina encuentra cerca de **3 de cada 10**
  decisiones de la referencia (recall 0,308) y solo cerca de **1,5 de cada 10** de lo que
  extrae corresponde a una decisión de la referencia (precisión 0,149). El F1 agrupado es
  0,201 (intervalo de 95 %: 0,161 a 0,240). La medida es estable entre repeticiones.
- **Relaciones.** De extremo a extremo se encuentra **1 de cada 10** enlaces de la referencia
  (11 de 111). Casi toda la pérdida viene de antes: para encontrar un enlace hay que haber
  encontrado primero sus dos decisiones. Cuando ambas decisiones sí se encontraron, la
  máquina acierta algo menos de la mitad de los enlaces (11 de 24).
- **Validez de la medición.** Una persona verificó a mano la regla automática que decide si dos
  decisiones son «la misma»: la concordancia fue 0,825 y **cumple** el criterio de ≥ 0,80. Los
  errores de la regla son sobre todo por omisión, lo que sugiere que las cifras tienden a
  quedarse algo por debajo de lo real; el tamaño de ese sesgo no está medido.
- **Alcance.** Una sola corrida, un solo modelo generador pequeño, once series. Las cifras
  describen ese caso; no se ajustaron ni se repitieron para mejorarlas.

## 1. Qué pregunta responde y por qué importa

El objetivo específico OE2 ([documento 03](03-jss-objetivos.md)) es medir la calidad de la
extracción automática: cuando un modelo de lenguaje lee una transcripción, ¿encuentra las
mismas decisiones que una persona? ¿Y detecta que una decisión posterior cambió a una anterior?

Importa por dos razones. La primera es que el sistema que se estudia (OpenKOS, [ADR 0003](../decisions/0003-adr-openkos-as-instrument.md))
construye un registro de decisiones **a partir de lo que extrae la máquina**; si esa extracción
es pobre, el registro hereda sus errores. La segunda es que el Experimento B compara el sistema
con y sin esos errores (condiciones C2 y C3): para interpretar esa comparación hay que saber
primero **cuánto** se equivoca la extracción y **en qué**. Este experimento da esa medida.

No es una prueba de éxito o fracaso. El [documento 08](08-jss-metricas-y-criterio-de-exito.md) (§4.3 y
decisión abierta A) declara que OE2 no tiene criterio de éxito: las cifras se reportan como
salen y se leen con la curva sobre τ. El único umbral de este experimento es de **validez de
la medición** (concordancia ≥ 0,80 de la alineación, sección 5).

## 2. Qué se hizo

### 2.1 La corrida

| Elemento | Valor | Fuente |
|---|---|---|
| Corrida | `experimento-a-formal` | Notebook 28, §1 |
| Series | 11 series de evaluación: ES2002, ES2008, ES2014, ES2016, IS1003, IS1006, IS1008, IS1009, TS3003, TS3005, TS3011 | Notebook 28, §1 |
| Repeticiones | 3 por serie, 33 corridas completas, todas sin error | Notebook 28, §1 y §6 |
| Modelo generador | `qwen3:8b`, temperatura 0,1, semilla 42 | Notebook 28, §1 |
| Modelo de similitud (*embeddings*) | `bge-m3` | Notebook 28, §1 |
| Sistema | OpenKOS 0.7.0, Ollama 0.32.9 | Notebook 28, §1 |
| Árbol de trabajo | Limpio (`git_dirty = False`); entorno fijado cumplido | Notebook 28, §1 |
| Congelamiento | [ADR 0024](../decisions/0024-adr-hoja-oe4-autocontenida.md) para la extracción; [ADR 0025](../decisions/0025-adr-relaciones-con-extremo-compuesto.md) para las relaciones | Notebook 28, §1 y §5 |

Se repite 3 veces cada serie porque un modelo de lenguaje no da exactamente la misma respuesta
cada vez; las repeticiones permiten medir cuánto varía el resultado por pura aleatoriedad.

**Qué hace el sistema.** Lee la transcripción de cada reunión y propone una lista de
decisiones (con su rol de hablante) y de relaciones entre ellas. **Qué es la referencia.**
Es la lista de decisiones y de relaciones que anotaron personas (OE1, [documento 10](10-jss-confiabilidad-de-la-referencia.md)).
En 4 de las 11 series la referencia fue adjudicada (dos personas anotan por separado y una tercera
resuelve los desacuerdos: ES2008, ES2016, IS1003 y TS3005) y en las otras 7 viene de una sola
persona (`single:gv` o `single:gm`) (`informe.json`, `reference_kinds`; notebook 28, §3). La
referencia de cada serie se compara en inglés (traducción automática de las etiquetas humanas;
[documento 06](06-jss-metodologia.md) v5.0).

Una precisión de lectura: los totales «agrupados» suman las 33 corridas, de modo que cuentan
cada decisión de la referencia tres veces. La referencia de las once series tiene 278 decisiones
(85 + 193 en la repetición 0, cifra derivada de la tabla por repetición del notebook 28, §3); el
total agrupado de 834 es 3 × 278.

### 2.2 Glosario

| Término | Qué significa, en simple |
|---|---|
| **Serie** | Un conjunto de reuniones de un mismo proyecto (por ejemplo, ES2002). Las once series de evaluación quedaron reservadas para este experimento (ADR 0005). |
| **Alineación** | La regla que decide si una decisión extraída por la máquina «es la misma» que una de la referencia. Se calcula la similitud entre los textos y se empareja de a una por vez, de la mejor manera global ([protocolo de alineación](../protocols/alignment.md)). |
| **τ (tau)** | El umbral de similitud para aceptar un emparejamiento. Con τ más alto la regla es más exigente. El valor principal es **0,70**; 0,75 y 0,80 son sensibilidades ([ADR 0012](../decisions/0012-adr-umbral-tau-del-experimento-a.md)). |
| **Precisión** | De lo que la máquina extrajo, qué parte está en la referencia. Mide cuánto «ruido» agrega. |
| **Recall (exhaustividad)** | De lo que hay en la referencia, qué parte encontró la máquina. Mide cuánto se le «escapa». |
| **F1** | Un solo número que combina precisión y recall; baja si cualquiera de los dos es bajo. |
| **Intervalo de 95 %** | Rango plausible de la cifra si se hubieran tomado otras reuniones. Se calcula remuestreando reuniones. Un intervalo ancho avisa que la cifra es poco precisa. |
| **Relación (enlace)** | Un vínculo entre dos decisiones: una posterior cambia, reafirma, refina o reemplaza a una anterior. Se evalúan su existencia, su tipo y su dirección (cuál revisa a cuál). |
| **Extremo a extremo** | Cuenta como acierto solo si la máquina encontró las dos decisiones del enlace **y** el enlace. Incluye la pérdida de decisiones. |
| **Condicionada** | Se considera solo los enlaces de la referencia cuyas dos decisiones sí fueron encontradas (alineadas). Aísla la calidad de la detección de relaciones. |
| **Concordancia** | Entre los pares que al menos uno de dos criterios empareja (la regla automática o una persona), la fracción que ambos emparejan. |

## 3. Resultados de decisiones

Todas las cifras de esta sección salen del notebook 28, §3 (`informe.json`).

### 3.1 Cifra principal y sensibilidad a τ

| τ | Lectura | Precisión [IC 95 %] | Recall [IC 95 %] | F1 [IC 95 %] | Aciertos / sobrantes / faltantes |
|---|---|---|---|---|---|
| 0,70 | principal | 0,149 [0,117; 0,184] | 0,308 [0,247; 0,373] | **0,201** [0,161; 0,240] | 257 / 1.471 / 577 |
| 0,75 | sensibilidad | 0,100 [0,073; 0,129] | 0,206 [0,152; 0,265] | 0,134 [0,100; 0,169] | 172 / 1.556 / 662 |
| 0,80 | sensibilidad | 0,050 [0,031; 0,071] | 0,104 [0,066; 0,149] | 0,068 [0,043; 0,094] | 87 / 1.641 / 747 |

(Totales de las 33 corridas, intervalos por remuestreo de reuniones; 44 reuniones de origen.)

**Cómo leerlo.**

- **Recall de 0,308.** Con el criterio principal, la máquina encuentra algo menos de un tercio
  de las decisiones que las personas identificaron. Dos de cada tres se le escapan.
- **Precisión de 0,149.** De cada 100 decisiones que la máquina propone, unas 15 corresponden a
  una decisión de la referencia. Los 1.471 «sobrantes» no son necesariamente errores de
  contenido: esta medición solo dice que no coinciden con la referencia, y no distingue una
  decisión inventada de una real que las personas no registraron (sección 7).
- **Lo que significa el F1 de 0,201.** Es un desempeño bajo en términos absolutos. Se debe leer
  junto a dos referencias: el piso del azar y los otros τ.
- **Frente al piso del azar.** El control nulo del [ADR 0012](../decisions/0012-adr-umbral-tau-del-experimento-a.md)
  (cruzar la salida de una serie con la referencia de otra) cubre el 13,8 % de la referencia
  con τ = 0,70, el 5,3 % con 0,75 y el 1,5 % con 0,80 (notebook 28, §3, columna
  `null_coverage`). El recall de 0,308 lo supera con τ = 0,70; con 0,80 la distancia es menor
  en términos absolutos (0,104 frente a 0,015), pero la cifra misma ya es muy baja. El control
  tiene un defecto declarado en el ADR 0012 (el piso nulo está algo sobrestimado), de modo que
  la comparación es conservadora.
- **Sensibilidad a τ.** Cuanto más exigente es la alineación, más baja el F1: de 0,201 a 0,134
  y a 0,068. Eso es esperable, y por eso el ADR 0012 fija τ = 0,70 como punto de lectura y
  exige mostrar los otros dos al lado. Ninguna conclusión de este documento depende de elegir
  el τ más favorable.

### 3.2 Estabilidad entre repeticiones

| Métrica | Media de las 3 repeticiones ± desviación |
|---|---|
| Precisión | 0,149 ± 0,003 |
| Recall | 0,308 ± 0,004 |
| F1 | 0,201 ± 0,003 |

Fuente: notebook 28, §3 (`across_runs`). **Interpretación:** repetir la extracción da
prácticamente lo mismo (la desviación es de unas milésimas). La baja precisión no es un
artefacto de una corrida mala ni de la aleatoriedad del modelo: es una propiedad estable de
este modelo y esta configuración. El F1 por repetición fue 0,199, 0,199 y 0,204.

### 3.3 Variación entre series

El F1 por serie con τ = 0,70 va de **0,130 (IS1008) a 0,260 (IS1006)**, con mediana de 0,210
(notebook 28, §3).

| Serie | Referencia | Precisión | Recall | F1 | IC 95 % del F1 |
|---|---|---|---|---|---|
| ES2002 | un anotador (`gv`) | 0,195 | 0,344 | 0,249 | 0,135 a 0,370 |
| ES2008 | adjudicada | 0,180 | 0,250 | 0,210 | 0,122 a 0,259 |
| ES2014 | un anotador (`gm`) | 0,131 | 0,271 | 0,176 | 0,063 a 0,262 |
| ES2016 | adjudicada | 0,165 | 0,429 | 0,238 | 0,216 a 0,288 |
| IS1003 | adjudicada | 0,098 | 0,227 | 0,137 | 0,000 a 0,202 |
| IS1006 | un anotador (`gv`) | 0,178 | 0,479 | 0,260 | 0,043 a 0,500 |
| IS1008 | un anotador (`gm`) | 0,079 | 0,364 | 0,130 | 0,047 a 0,198 |
| IS1009 | un anotador (`gv`) | 0,133 | 0,167 | 0,148 | 0,000 a 0,419 |
| TS3003 | un anotador (`gv`) | 0,178 | 0,355 | 0,237 | 0,142 a 0,412 |
| TS3005 | adjudicada | 0,189 | 0,324 | 0,239 | 0,067 a 0,339 |
| TS3011 | un anotador (`gm`) | 0,100 | 0,270 | 0,146 | 0,025 a 0,233 |

**Interpretación.** Los resultados por serie son parejos en lo esencial: en todas el F1 es
bajo (entre 0,13 y 0,26) y en todas la precisión es menor que el recall. Los intervalos por
serie son muy anchos porque cada una tiene solo 4 reuniones. Por eso las diferencias entre
series (por ejemplo, IS1006 frente a IS1008) **son descriptivas y no se interpretan como
diferencias reales** entre tipos de proyecto.

### 3.4 Por rol del hablante

| Rol | Decisiones de referencia | Recall | Precisión |
|---|---|---|---|
| PM (jefe de proyecto) | 360 | 0,347 | 0,197 |
| ID (diseñador industrial) | 153 | 0,340 | 0,120 |
| ME (experto en marketing) | 147 | 0,272 | 0,122 |
| UI (diseñador de interfaz) | 117 | 0,128 | 0,111 |
| Sin rol asignado (`unknown`) | 57 | 0,439 | no aplica |

(Totales de las 33 corridas; notebook 28, §3, `by_role`. Los roles son los del corpus AMI,
[documento 02](02-jss-fuente-de-datos.md).)

**Interpretación.** El recall más alto entre los roles identificados es el de PM (0,347) y el
más bajo el de UI (0,128): las decisiones del diseñador de interfaz son las que más se le
escapan a la máquina. El desglose por rol es obligatorio en OE2 y se publica aunque no
permita explicar la causa; con estos datos no se sabe *por qué* UI es más difícil. Las
decisiones sin rol no tienen precisión porque la máquina no predice ese rol.

## 4. Resultados de relaciones

Cifras del notebook 28, §3.1 (`relaciones.json`), también totales de las 33 corridas. Para
evitar confusiones: los 111 enlaces de la referencia son 37 enlaces distintos contados en tres
repeticiones (37 es la cifra del [notebook 27](../../notebooks/27-jss-relaciones-con-extremo-compuesto.ipynb)).
Los 11 enlaces detectados están en el mismo conteo agrupado.

### 4.1 Los datos de partida

| Concepto | Cifra |
|---|---|
| Enlaces de la referencia | 111 |
| … con sus dos decisiones alineadas | 24 |
| Relaciones propuestas por la máquina | 903 (546 enlaces) |
| … con sus dos decisiones alineadas | 27 |
| Errores de lectura de la salida | 0 |

### 4.2 Dos vistas de la existencia del enlace

| Vista | Precisión | Recall |
|---|---|---|
| Extremo a extremo | 0,020 (11 de 546) [0,011; 0,036] | 0,099 (11 de 111) [0,056; 0,169] |
| Condicionada a que ambos extremos estén alineados | 0,407 (11 de 27) [0,245; 0,593] | 0,458 (11 de 24) [0,279; 0,649] |

**Por qué difieren tanto.** Una relación solo puede encontrarse si las dos decisiones que une
fueron encontradas antes. Con un recall de decisiones de 0,308, es de esperar que pocos
enlaces tengan ambos extremos: solo 24 de 111 (alrededor de uno de cada cinco). De ahí que la
vista extremo a extremo sea baja: arrastra la pérdida de decisiones. De los falsos positivos de
existencia extremo a extremo, **519 de 535 corresponden a enlaces con algún extremo sin
alinear** y 16 a pares que el filtro de candidatos nunca ofreció.

**Interpretación.** El cuello de botella está en **encontrar las decisiones**, no en
clasificar la relación una vez que ambas existen. Cuando los dos extremos sí están, la
máquina encuentra algo menos de la mitad de los enlaces (0,458) con una precisión parecida
(0,407). Esos intervalos son amplios porque la base es pequeña (24 y 27 casos): son una
señal, no una medida fina.

### 4.3 Tipo y dirección entre los 11 enlaces detectados

| Qué se acierta | Cifra |
|---|---|
| Dirección (cuál decisión revisa a cuál) | 11 de 11 (intervalo 0,741 a 1,000) |
| Tipo, vista principal (une «revierte» y «reemplaza») | 6 de 11 (0,545; intervalo 0,280 a 0,787) |
| Tipo, vista estricta | 3 de 11 (0,273; intervalo 0,097 a 0,566) |

**Interpretación.** Entre los enlaces que sí detectó, la máquina acertó la dirección en todos
y el tipo en poco más de la mitad. Con solo 11 casos, estos números no permiten afirmar nada
fino: los intervalos son muy anchos. Lo que sí muestran es que, en esta corrida, el tipo del
enlace falló más que la dirección. Esto coincide con la dificultad de las personas: en OE1
el tipo también fue el eje más difícil de acordar (kappa 0,554 frente a una dirección sin
desacuerdos; [documento 10](10-jss-confiabilidad-de-la-referencia.md)).

## 5. Validez de la medición

Una cifra de precisión o recall solo vale si la regla que decide «es la misma decisión» es
confiable. Por eso el protocolo exige contrastarla con una persona
([documento 08](08-jss-metricas-y-criterio-de-exito.md), tabla de métricas).

### 5.1 Validación manual de la alineación (issue #290)

Una persona del equipo, sin ver la respuesta de la regla automática, respondió para 100 pares
de las once series (repetición 0, semilla 42) si la frase extraída y la de la referencia son
la misma decisión. La muestra es estratificada: 50 pares que la regla empareja y 50 pares de
la misma reunión que la regla descarta. El criterio de aprobación (concordancia ≥ 0,80) viene
del [documento 08](08-jss-metricas-y-criterio-de-exito.md) y del issue #290; el código que
puntúa no define umbral. Fuente: notebook 28, §4 (`validacion-manual.json`).

|  | Persona: misma decisión | Persona: distinta |
|---|---|---|
| **Regla automática: empareja** | 47 | 3 |
| **Regla automática: descarta** | 7 | 43 |

| Indicador | Valor |
|---|---|
| Concordancia (pares coincidentes sobre la unión de pares emparejados) | **0,825** |
| Criterio ≥ 0,80 | **Cumple** |
| Acuerdo observado | 90 de 100 (0,900) |
| Kappa de Cohen | 0,800 |
| Emparejados por la regla y confirmados a mano | 47 de 50 |
| Descartados por la regla que la persona sí empareja | 7 de 50 |

**Interpretación.**

- La regla automática y la persona coinciden en 9 de cada 10 pares. La concordancia de 0,825
  cumple el umbral, de modo que la medición de las secciones 3 y 4 se considera válida en
  este aspecto.
- De los 10 desacuerdos, 7 son pares que la regla descarta y la persona sí empareja, y 3 son
  los inversos. **La regla se equivoca más por omisión que por exceso**: tiende a subestimar
  cuánto encuentra la máquina. Esto **sugiere** que las cifras con τ = 0,70 quedan algo por
  debajo de lo real, aunque los 3 pares que la regla empareja de más empujan en sentido
  contrario y el saldo neto no está medido. Este resultado concuerda con
  el del juez automático del ADR 0012 (86 % de acuerdo, kappa 0,716, más estricto que la
  persona).
- Un alcance importante: las proporciones de la tabla describen cada grupo de 50, no el
  conjunto de las series, porque la muestra es estratificada. **No sirven para corregir las
  cifras de la sección 3**: solo indican la dirección del sesgo, no su tamaño.

### 5.2 La corrección del ADR 0025 y su comprobación

Después de la corrida se encontró que 9 relaciones de la referencia (11 extremos, en ES2008,
ES2014, ES2016 e IS1008) apuntaban a una decisión «compuesta» que no existe en la lista de
decisiones de la referencia. Esos enlaces no podían encontrarse nunca. El
[ADR 0025](../decisions/0025-adr-relaciones-con-extremo-compuesto.md) reasignó cada extremo a la
decisión hija correspondiente, sin repetir la extracción (el código y el entorno no cambiaron),
y se rehicieron las relaciones y el informe (notebook 28, §5).

**Resultado.** La salida de relaciones antes y después del ADR 0025 es **idéntica** en las 33
entradas y en todos los totales (111 enlaces, 24 alineados en ambos extremos, 11 detectados).
Solo cambian la procedencia y la duración.

**Comprobación de apoyo (notebook 28, §5.1).** Para saber si el resultado idéntico era
esperable, se revisó, en cada repetición, si alguno de esos 9 enlaces reasignados quedaba con
sus dos extremos alineados con τ = 0,70. Ninguno lo logra: 0 de 9 en cada una de las 3
repeticiones (a lo más un extremo alineado por enlace). Entonces la reasignación no podía
sumar enlaces alineados, lo que es **compatible** con que los totales no cambiaran.

**Advertencia.** Esa comprobación es evidencia de apoyo, no una demostración de la causa: usa
las extracciones guardadas y no los espacios de trabajo de OpenKOS que lee el paso de
relaciones, así que podría diferir levemente de la alineación exacta de ese paso. El notebook
declara que la causa no está establecida y aquí se mantiene esa declaración.

### 5.3 Integridad de la corrida

Los 33 pares se completaron en una ventana continua, sin reinicios ni interrupciones (la pausa
mayor entre un par y el siguiente fue de 0,001 s), con una sola versión de OpenKOS, sin
errores, sin decisiones sin evidencia, y con las 1.728 citas encontradas (0 de 1.728 no
encontradas) (notebook 28, §6). La conclusión de que no hubo reinicios se apoya en las marcas
de tiempo, porque el manifiesto no guarda un campo de reanudación.

## 6. Qué significa para las hipótesis y para el Experimento B

Este experimento no pone a prueba H1 ni H4 (se miden en el Experimento B) y mide H2 y H3 solo
de manera parcial. Cada conexión tiene su alcance:

- **H2** («la brecha C3 − C2 será mayor en relaciones que en decisiones»). H2 **se mide en el
  Experimento B** ([ADR 0018](../decisions/0018-adr-medicion-de-h2-y-h3.md), decisión 1); este
  experimento no la resuelve. El informe calcula una **cifra complementaria**, la brecha de
  extracción, que no es H2: es 1 menos el recall frente a la referencia (`informe.json`,
  `hypotheses`). En decisiones es 0,692 [0,627; 0,753]; en relaciones extremo a extremo,
  0,901 [0,831; 0,944] (diferencia de 0,209); y condicionada, 0,542 [0,351; 0,721]
  (diferencia de −0,150, con un intervalo que cruza el cero). Su lectura es la de la sección 4:
  la brecha de relaciones extremo a extremo es mayor, pero en buena parte porque incluye la
  brecha de decisiones, y al quitar ese efecto el contraste cambia de signo y queda
  no concluyente (`verdicts`: respaldada extremo a extremo, no concluyente condicionada). Por el sesgo mecánico que el ADR 0018 describe, esta cifra se lee como
  contexto, no como evidencia a favor ni en contra de H2.
- **H3** («la dirección de las relaciones será un modo de falla dominante»). H3 sí se mide aquí,
  entre los enlaces detectados ([ADR 0018](../decisions/0018-adr-medicion-de-h2-y-h3.md), decisión 4).
  Con los 11 enlaces detectados, la dirección no falló en ninguno (0 de 11, cota superior
  de 0,259) y el tipo falló en 5 de 11 (0,455, intervalo 0,213 a 0,720) (`informe.json`, `hypotheses.h3`).
  El veredicto del informe es **no concluyente**: son muy pocos enlaces, y la cláusula sobre
  el tamaño del modelo no se puede evaluar porque solo se midió una escala (`qwen3:8b`).
  Lo que sí muestra es que, en esta muestra, la dirección no fue el modo de falla más frecuente.
- **Qué aporta al Experimento B.** Dos lecturas, ambas descriptivas. Primero, la condición C2
  se construye con la extracción de la máquina ([ADR 0015](../decisions/0015-adr-modelo-extractor-de-c2.md))
  y, con las cifras de este experimento, esa base contiene solo cerca de un tercio de las
  decisiones de la referencia, mientras que C3 parte de la referencia completa. Una diferencia entre C2 y C3 en el Experimento B habrá que leerla sabiendo esto. Segundo, la
  baja precisión implica que la base de C2 contiene muchas decisiones que no están en la
  referencia. Ninguna de las dos lecturas predice el resultado de B ni se usa para
  interpretarlo antes de medirlo.

Los resultados del Experimento B se reportan en el avance 12.

## 7. Limitaciones y riesgos declarados

- **Un solo modelo, una sola corrida formal.** Las cifras son las de `qwen3:8b` con la
  configuración congelada (33 corridas: 11 series × 3 repeticiones). No se generalizan a otros
  modelos ni a otras escalas, y la cláusula de H3 sobre el tamaño del modelo queda sin medir.
- **La alineación es automática.** Su concordancia con una persona se midió en 100 pares y
  cumple el criterio, pero la validación la hizo **una sola persona**, sobre una muestra
  estratificada de la repetición 0; describe τ = 0,70, no los otros τ.
- **Elección de τ.** τ = 0,70 es una decisión metodológica que se apartó de una regla fijada
  antes de ver los resultados, por un defecto del control nulo (ADR 0012). Con τ = 0,75 y 0,80
  las cifras bajan mucho (sección 3.1); por eso se muestran los tres valores.
- **Tamaño de la muestra.** 11 series y 4 reuniones por serie: las cifras por serie son
  descriptivas, y los intervalos de relaciones (24 y 27 casos en la vista condicionada, 11
  en tipo y dirección) son amplios.
- **La referencia no es perfecta.** En 7 de las 11 series la referencia viene de una sola
  persona, no está adjudicada ([documento 10](10-jss-confiabilidad-de-la-referencia.md)). Una
  decisión extraída que no figura en la referencia puede ser un error de la máquina o una
  decisión real que las personas no registraron; esta medición no las distingue y por eso la
  precisión baja no se interpreta como «la máquina inventa».
- **La referencia se compara en inglés**, traducida automáticamente a partir de las etiquetas
  humanas (documento 06). La traducción desplaza la curva de τ.
- **Relaciones que el filtro no ofrece.** El filtro de candidatos del instrumento deja fuera
  algunos pares reales, así que el recall de existencia es una cota superior
  ([documento 08](08-jss-metricas-y-criterio-de-exito.md), §4.2).
- **Pasos con duración no registrada.** La duración del informe, de la hoja de validación y
  del puntaje no se guardó en ninguna salida versionada (sección 8).
- **La causa de que el ADR 0025 no alterara los totales no está demostrada** (sección 5.2).

## 8. Costo en tiempo

| Paso | Duración | Fuente |
|---|---|---|
| Extracción (11 series × 3 repeticiones) | 11 h 48 min 42 s | Notebook 28, §2 (suma de los 33 pares) |
| Relaciones, primera corrida (ADR 0024) | 49 min 52 s | Notebook 28, §2 (`relaciones.json` del PR #297) |
| Relaciones, rehechas con el ADR 0025 | 44 s | Notebook 28, §2 (`relaciones.json`) |
| Informe | no registrada | Notebook 28, §2 |
| Hoja de validación manual | no registrada | Notebook 28, §2 |
| Puntaje de la validación manual | no registrada | Notebook 28, §2 |

La extracción tomó menos que las 14 h estimadas en el issue #289. Cada par (una serie, una
repetición) tomó entre 12 y 31 minutos; ES2016 fue la serie más lenta (1 h 27 min 44 s las
tres repeticiones) e IS1008 la más rápida (41 min 11 s). Por qué las relaciones tardaron 44 s
la segunda vez y 49 min 52 s la primera no se explica con la salida guardada, y no se atribuye
a ninguna causa. El tiempo de la validación manual a cargo de la persona no está registrado.
Para planificar corridas futuras, el costo es de unas 12 horas de máquina para la extracción
completa más menos de una hora de relaciones.

## 9. Referencias

| Contenido | Fuente |
|---|---|
| Análisis de la corrida (todas las cifras de este documento) | [`notebooks/28-jss-experimento-a.ipynb`](../../notebooks/28-jss-experimento-a.ipynb) |
| Procedencia de la corrida | [`manifest.json`](../../reports/experiment-a/experimento-a-formal/manifest.json) |
| Informe de decisiones, rol, hipótesis | [`informe.json`](../../reports/experiment-a/experimento-a-formal/informe.json) |
| Relaciones | [`relaciones.json`](../../reports/experiment-a/experimento-a-formal/relaciones.json) |
| Validación manual de la alineación | [`validacion-manual.json`](../../reports/experiment-a/experimento-a-formal/validacion-manual.json) |
| Relaciones con extremo compuesto | [`notebooks/27-jss-relaciones-con-extremo-compuesto.ipynb`](../../notebooks/27-jss-relaciones-con-extremo-compuesto.ipynb) |
| Separación desarrollo/evaluación | [ADR 0005](../decisions/0005-adr-development-evaluation-split.md) |
| Umbral τ | [ADR 0012](../decisions/0012-adr-umbral-tau-del-experimento-a.md) |
| Relaciones temporales de OpenKOS | [ADR 0016](../decisions/0016-adr-relaciones-temporales-de-openkos.md) |
| Medición de H2 y H3 | [ADR 0018](../decisions/0018-adr-medicion-de-h2-y-h3.md) |
| Congelamiento de la corrida | [ADR 0024](../decisions/0024-adr-hoja-oe4-autocontenida.md) |
| Corrección de extremos compuestos | [ADR 0025](../decisions/0025-adr-relaciones-con-extremo-compuesto.md) |
| Objetivos, hipótesis y métricas | [documento 03](03-jss-objetivos.md), [documento 08](08-jss-metricas-y-criterio-de-exito.md) |
| Confiabilidad de la referencia (OE1) | [documento 10](10-jss-confiabilidad-de-la-referencia.md) |
| Épica y tareas | Épica #288; issues #289 (corrida formal), #290 (validación manual), #298 (extremos compuestos); PR #297 (relaciones con el ADR 0024), PR #304 (puntaje de la validación), PR #305 (notebook 28) |
