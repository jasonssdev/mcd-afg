| | |
|---|---|
| **Entrega** | Video de avance #2 (semana 3), AFG1 |
| **Fecha de envío** | Semana 3 del curso (fecha exacta por completar) |
| **Versión** | 1.0 |
| **Construido desde** | Versión previa de la propuesta, anterior a la auditoría de datos |
| **Estado** | Congelado tal como se envió. **No se edita.** |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Incorporación al repositorio del guion tal como se envió. | Registro del entregable. |

> **Aviso de lectura.** Refleja el diseño de la semana 3. La versión vigente de problema,
> objetivos y metodología está en `docs/avances/`.

---

# Guion --- Video de avance, Semana 3

**Duración objetivo:** 5:00\
**Formato:** tres presentadores, bloques consecutivos\
**Extensión total hablada:** ≈ 700 palabras (ritmo de 140--150
palabras/min)

  ------------------------------------------------------------------------
  Bloque           Persona                         Tiempo Mensaje central
  ---------------- ---------------- --------------------- ----------------
  Apertura         Persona 1                 0:00 -- 1:35 Qué problema
                                                          resolvemos y
                                                          cómo lo
                                                          convertimos en
                                                          una comparación
                                                          medible

  Literatura       Persona 2                 1:35 -- 3:20 Qué encontramos,
                                                          qué decisiones
                                                          metodológicas
                                                          respalda y qué
                                                          brecha abordamos

  Metodología      Persona 3                 3:20 -- 5:00 Cómo evaluaremos
                                                          extracción,
                                                          retrieval y
                                                          respuesta, y qué
                                                          sigue
  ------------------------------------------------------------------------

------------------------------------------------------------------------

## Notas de grabación

-   El texto está escrito **para decirse, no para leerse**. Frases
    cortas.
-   Las palabras en **negrita** son las que conviene apoyar con la voz.
-   Cada bloque abre nombrando a quien habla y cierra pasando el turno.
-   No lean matrices, tablas ni métricas completas en cámara: **se
    muestran como apoyo visual**.
-   En todo el video utilizar únicamente el diseño actualizado: **C1 RAG
    documental ↔ C2 base estructurada automática**.

------------------------------------------------------------------------

## PERSONA 1 --- El problema y el diseño

**0:00 -- 1:35 · ≈ 215 palabras**

> **Apoyo visual:** título del proyecto → problema → diagrama C1 RAG
> documental vs. C2 base estructurada automática

Hola, somos \[nombres\] y este es nuestro avance de la semana tres.

Nuestro proyecto parte de un problema muy concreto. Las organizaciones
toman decisiones en reuniones, esas reuniones se transcriben, y después
recuperar **qué se decidió, por qué, con qué evidencia y si esa decisión
sigue vigente** no es trivial.

Una alternativa habitual es RAG: recuperar fragmentos desde las
transcripciones cada vez que alguien hace una consulta. Nosotros
queremos compararlo con otra estrategia: **extraer automáticamente las
decisiones, persistirlas en una base estructurada y consultar esa
representación**.

Para medirlo definimos dos condiciones. **C1** es RAG documental directo
sobre las transcripciones. **C2** es una base estructurada construida
automáticamente a partir de esas mismas transcripciones. Ambas se
evaluarán sobre el AMI Meeting Corpus y recibirán las mismas preguntas.

Pero antes de comparar C1 y C2 necesitamos saber qué tan bien podemos
construir automáticamente esa base. Por eso el marco separa dos
experimentos: el **Experimento A evalúa la extracción automática**, y el
**Experimento B compara C1 contra C2**.

Esta separación es importante porque C2 depende de lo que logremos
extraer. Y justamente esa relación entre extracción, representación y
recuperación es parte de lo que revisamos en la literatura.

Te paso, \[nombre\].

------------------------------------------------------------------------

## PERSONA 2 --- La literatura y la brecha

**1:35 -- 3:20 · ≈ 235 palabras**

> **Apoyo visual:** ejes de literatura → antecedentes principales →
> repositorios revisados → frase de la brecha

Gracias, \[nombre\].

Organizamos la revisión en **seis ejes temáticos** y aplicamos dos
criterios: cada fuente debe respaldar una decisión concreta del diseño y
debe tener una referencia verificable. También distinguimos artículos
revisados por pares, preprints y artefactos de ingeniería.

De esa revisión surgieron varias decisiones importantes.

Primero, antecedentes como **HippoRAG 2** muestran que una
representación estructurada no necesariamente supera a la recuperación
documental en todos los tipos de pregunta. Por eso nuestra evaluación
estará **segmentada por tipo de consulta**, en lugar de reducir todo a
una única métrica global.

Segundo, la literatura de memoria temporal respalda preservar la
evolución de la información. En nuestro caso, una decisión revisada o
reemplazada no debería simplemente desaparecer: necesitamos mantener
**estado, temporalidad y procedencia**.

Tercero, la extracción estructurada introduce sus propios errores. Por
eso el Ground Truth humano se mantiene como **referencia de
evaluación**, pero no se utiliza para construir o corregir C2 durante el
test.

La brecha que buscamos estudiar es entonces más específica: en nuestra
revisión no identificamos una comparación controlada entre **RAG
documental y una base estructurada generada automáticamente**,
manteniendo constantes el corpus, las preguntas y el generador, y
evaluando por separado extracción, retrieval y respuesta.

Ahí es donde entra nuestra propuesta metodológica.

\[nombre\], adelante.

------------------------------------------------------------------------

## PERSONA 3 --- Metodología y próximos pasos

**3:20 -- 5:00 · ≈ 240 palabras**

> **Apoyo visual:** Ground Truth → Experimento A → C1/C2 → métricas de
> retrieval y respuesta → próximos pasos

Gracias.

Trabajamos sobre el **AMI Meeting Corpus**, utilizando series de
reuniones donde existe continuidad entre encuentros. Esa continuidad es
importante porque queremos evaluar no sólo decisiones puntuales, sino
también preguntas sobre **estado vigente, evolución y reemplazo**.

Primero construimos un **Ground Truth humano adjudicado**. Su función es
servir como referencia para medir la extracción; no es una tercera
condición ni se utiliza para poblar la base automática.

Después ejecutamos el **Experimento A**. Ahí evaluamos qué tan bien los
extractores detectan decisiones, recuperan su evidencia y representan
correctamente sus relaciones temporales. Con esas métricas seleccionamos
y congelamos un único extractor.

Ese extractor construye **C2**, la base estructurada automática.

Luego viene el **Experimento B**. Las mismas preguntas pasan por **C1,
RAG documental, y C2, base estructurada automática**, utilizando el
mismo generador.

La evaluación se separa en niveles. Para retrieval usamos métricas como
**Precision@k, Recall@k, MRR y nDCG@k** cuando existan juicios de
relevancia válidos. Después evaluamos la respuesta en corrección,
completitud, temporalidad, fidelidad, evidencia y abstención, además de
eficiencia.

El contraste principal será **C2 menos C1**, pero lo interpretaremos
como una comparación **end-to-end**. Sin una base estructurada manual no
podemos separar causalmente cuánto del resultado corresponde a
extracción, representación o recuperación.

Lo que sigue es avanzar con el piloto de anotación, validar el Ground
Truth y cerrar las configuraciones antes de ejecutar los experimentos.

Eso es todo. Gracias por ver.

------------------------------------------------------------------------

## Ajustes de tiempo

**Si van largos --- recortar en este orden:**

1.  Persona 2: reducir la explicación de los criterios de revisión.
2.  Persona 3: resumir la enumeración de métricas de retrieval.
3.  Persona 1: acortar la explicación de RAG.

**Si van cortos --- agregar en este orden:**

1.  Persona 2: mencionar el antecedente open source más cercano
    identificado en la revisión y explicar brevemente la diferencia.
2.  Persona 3: explicar que `@k` significa evaluar los primeros *k*
    resultados recuperados.
3.  Persona 1: dar un ejemplo de pregunta temporal, como "¿qué decisión
    está vigente actualmente y cuál reemplazó?".

------------------------------------------------------------------------

## Checklist previo a grabar

-   [ ] Diagrama **C1 RAG documental ↔ C2 base estructurada automática**
    listo y legible.
-   [ ] No aparece ninguna referencia a **C3**, "tres condiciones" o
    "base estructurada manual".
-   [ ] Ground Truth presentado únicamente como **referencia de
    evaluación**.
-   [ ] Experimento A presentado como evaluación de extracción y
    selección del extractor.
-   [ ] Experimento B presentado como comparación **C1 vs. C2**.
-   [ ] C2 descrita como base construida exclusivamente mediante el
    extractor automático congelado.
-   [ ] `C2 − C1` descrito como comparación **end-to-end**, no como
    efecto causal puro de la representación.
-   [ ] Nombres reales reemplazados en `[nombre]`.
-   [ ] Cada persona cronometró su bloque en voz alta al menos una vez.
-   [ ] Ninguna afirmación dice «no existe»; usar «no identificamos en
    nuestra revisión».
-   [ ] Audio probado --- importa más que el video.
