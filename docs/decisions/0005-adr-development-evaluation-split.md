# 5. División desarrollo / evaluación, y series de control revisadas

Fecha: 2026-09-20
Estado: Aceptada
Reemplaza parte de: [0004](0004-adr-oe1-series-selection.md) — la selección de 14 series se
mantiene sin cambios; solo se revisa la lista de series de control.

## Contexto

El ADR 0004 fijó 14 series para OE1 pero no dijo cómo se particionarían. Esa omisión
importa porque **hay tres cosas ajustadas en este diseño**, y cualquier cosa ajustada sobre
los datos cuyos resultados se reportan produce cifras optimistas:

1. **El tamaño de chunk y el número de fragmentos recuperados de C1.** La sección 5.3 de la
   tesis es explícita: *"parámetros de segmentación y número de fragmentos recuperados
   ajustados sobre un conjunto de desarrollo separado, no fijados arbitrariamente. Una
   línea base debilitada invalida el experimento completo."*
2. **El umbral de alineación τ** (sección 5.4). Parcialmente mitigado al reportar F1 como
   una curva sobre τ en vez de en un punto, pero la elección de la grilla sigue siendo una
   elección.
3. **El punto de operación del bloqueador.** Demostrado, no hipotetizado: pasar de
   `min_overlap_tokens = 1` a `2` cambia el número de candidatos de 712 a 92 en estas
   mismas 14 series. Un parámetro con ese nivel de influencia no puede fijarse mirando los
   datos sobre los que se evaluará.

### Esto no es un split de entrenamiento y prueba

Ningún modelo se ajusta sobre estos datos. No hay conjunto de entrenamiento, e importar ese
vocabulario sería un error de categoría que invitaría a quienes revisen a pedir curvas de
aprendizaje que no existen. La partición separa **datos usados para tomar decisiones** de
**datos usados para reportar resultados**.

### ES2015 e IS1004 ya están contaminadas

Ambas se usaron como piloto (ver `docs/anotacion/manual-anotacion-oe1.md` §3). Sus frases
de decisión se leyeron por completo, sus pares candidatos se inspeccionaron, y la
transcripción del botón turbo de IS1004d se trazó palabra por palabra. No pueden servir
como datos de evaluación limpios para nada que dependa de no haberlas visto antes. Asignarlas
a desarrollo no cuesta nada, porque el costo ya está pagado.

## Decisión

### Partición

| Conjunto | Series | Propósito |
|---|---|---|
| **Desarrollo** (3) | ES2015, IS1004, TS3009 | Ajustar el chunking y el top-k de C1, la grilla de τ, el punto de operación del bloqueador y los formatos de prompt. **Sus cifras nunca se reportan como resultados.** |
| **Evaluación** (11) | ES2002, ES2008, ES2014, ES2016, IS1003, IS1006, IS1008, IS1009, TS3003, TS3005, TS3011 | Donde se miden OE2, OE3 y OE4 |
| **Reserva** (18) | la lista fuera de muestra del ADR 0004 | Sin tocar. Disponible si E3 termina necesitando más material |

ES2015 e IS1004 son las series piloto contaminadas. TS3009 se les une para que desarrollo
cubra los tres sitios de grabación, y porque es una serie de bajo rendimiento (4 candidatos
en el punto de operación actual) cuya pérdida en evaluación cuesta poco.

Balance de sitio en evaluación: **4 ES / 4 IS / 3 TS** — sigue balanceado en la variable
que el ADR 0004 identificó como la que estructuralmente importa.

### Series de control revisadas para doble anotación

El ADR 0004 fijó ES2015, ES2008, IS1004, TS3005. Dos de ellas ahora quedan en desarrollo, y
el acuerdo entre anotadoras debe medirse sobre los datos cuyos resultados se reportan.

**Revisión: ES2008, ES2016, IS1003, TS3005** — 4 de las 11 series de evaluación (36,4 %),
una por sitio más una segunda de ES. TS3005 y ES2016 también llevan la capa DDS, así que
los desacuerdos pueden triangularse contra una anotación independiente.

Revisar esto no cuesta nada: **todavía no se ha anotado ni una sola fila.** La advertencia
del ADR 0004 de que cambiar la selección invalida la anotación ya hecha bajo ella es
precisamente lo que hace que revisar ahora, y no después, sea el momento correcto.

## Consecuencias

- Cualquier parámetro ajustado sobre desarrollo debe **congelarse antes de tocar
  evaluación**, y su valor debe registrarse con el ADR o la configuración que lo fijó.
- Las cifras de las series de desarrollo pueden aparecer en la tesis como ilustración o
  como descripción de método, pero nunca en una tabla de resultados.
- Las cuatro N deben reportarse por separado y nunca confundirse: 56 reuniones; 343
  frases de decisión abstractivas (`DECISIONS`); 3.071 pares entre reuniones; 92 pares
  candidatos en el punto de operación actual. El número de **relaciones reales** sigue sin
  medirse y es la cifra que decide si el estrato de E3 es viable.
- Evaluación se reduce a 11 series. Recalculado a partir de las mediciones por serie:
  **desarrollo tiene 77 de las 343 frases de decisión y 11 de los 92 pares candidatos;
  evaluación tiene 266 y 81.**
- **Dos series aportan casi nada**: IS1006 e IS1009 producen 1 candidato cada una en el
  punto de operación actual. Igual aportan decisiones a OE2, pero prácticamente nada a E3.

## Alternativas rechazadas

- **Sin conjunto de desarrollo.** Obligaría a ajustar sobre datos de evaluación
  (deshonesto) o a fijar parámetros arbitrariamente — y la sección 5.3 prohíbe
  explícitamente la opción arbitraria para C1, porque una línea base debilitada invalida
  todo el experimento.
- **Usar las 18 series de reserva para desarrollo.** Más limpio en principio, pero exigiría
  anotarlas, duplicando aproximadamente el presupuesto humano sin ganancia — el ajuste de
  desarrollo para C1 y el bloqueador no necesita relaciones gold.
- **Mantener las series de control del ADR 0004.** Mediría el acuerdo entre anotadoras
  parcialmente sobre datos de desarrollo, que no es lo que sostiene a los resultados
  reportados.
