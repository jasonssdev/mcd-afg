# 4. Selección de series para OE1

Fecha: 2026-09-20
Estado: Aceptada (cifra de candidatos corregida por D9)

## Contexto

El ADR 0003 y los resultados del paso cero movieron el marco muestral de OE1 desde la capa
de *Decision Discussion Segmentation* (6 series completas) a la capa `DECISIONS` de
resúmenes abstractivos (33 series completas de cuatro reuniones, 649 decisiones). Esa
expansión convierte la muestra en una **elección** en vez de algo dado, por lo que la
elección debe registrarse con sus criterios antes de que comience cualquier anotación — de
lo contrario la selección se convierte en un grado de libertad que se puede ajustar después
de ver los resultados.

Datos medidos, calculados a partir de `ami_public_manual_1.6.2`:

- 33 series tienen resúmenes abstractivos en las cuatro reuniones.
- 32 de esas también tienen `summlink` en las cuatro reuniones. **TS3012 no lo tiene** (3
  de 4), así que sus decisiones no pueden anclarse a actos de diálogo y queda inelegible.
- 6 series además llevan la capa DDS: ES2015, ES2016, IS1004, IS1006, IS1008, TS3005.

### El hallazgo estructural que dio forma a esta decisión

Los datos de lengua materna no están dispersos por el corpus — están **perfectamente
anidados dentro del sitio de grabación**:

| Sitio | Prefijo | Series | Perfil de lengua materna |
|---|---|---|---|
| Edinburgh | `ES` | 15 | Casi enteramente inglés nativo (4/0), salvo ES2004–ES2007 y ES2016 con 3/1 |
| Idiap | `IS` | 8 | Mayoritariamente no nativo (0/4 o 1/3), salvo IS1008 con 3/1 |
| TNO | `TS` | 10 | **Ningún participante figura en `participants.xml`** — 40 desconocidos |

Esto no es un accidente de muestreo que se corrija eligiendo mejores series. En AMI, "hablante
no nativo" no puede separarse de "grabado en Idiap", y todo el bloque de TNO no tiene ningún
dato de lengua. Esto confirma y refuerza la decisión D7 (degradar el eje nativo/no nativo de
estratificación obligatoria a limitación reportada) por razones estructurales, no por tamaño
de muestra.

También significa que **el sitio de grabación es la variable que realmente necesita
balancearse**, porque cualquier resultado desbalanceado sería un artefacto de sitio.

## Decisión

Anotar **14 series**, seleccionadas con estos criterios aplicados en orden:

1. **Obligatorio: `summlink` en las cuatro reuniones.** Sin eso una decisión no puede
   anclarse a evidencia, lo que incumple la condición 3 de la definición de la sección 5.2
   de la tesis. Excluye a TS3012.
2. **Obligatorio: incluir las 6 series DDS.** Son las únicas donde las decisiones derivadas
   de resúmenes abstractivos pueden contrastarse contra una anotación de decisiones
   independiente — este es el subconjunto de validación del que depende la decisión D2.
3. **Balancear el sitio de grabación**, según el hallazgo anterior: apuntar a una
   representación aproximadamente equitativa entre ES / IS / TS para que ningún resultado
   pueda atribuirse al sitio.
4. **Dentro de un sitio, preferir volumen de decisiones**, ya que más decisiones producen
   más pares entre reuniones y por lo tanto más material para E3.

### La selección

| Sitio | Series | Decisiones | Pares entre reuniones |
|---|---|---|---|
| ES | ES2002, ES2008, ES2014, **ES2015\***, **ES2016\*** | 137 | 1.357 |
| IS | IS1003, **IS1004\***, **IS1006\***, **IS1008\***, IS1009 | 99 | 716 |
| TS | TS3003, **TS3005\***, TS3009, TS3011 | 107 | 998 |
| **Total** | **14 series, 56 reuniones** | **343** | **3.071** |

`*` = también lleva la capa DDS (subconjunto de validación).

A la tasa de bloqueo medida de ~5,5 % (piloto, coeficiente de solapamiento ≥ 0,30), esto
produce **≈ 170 pares candidatos** para adjudicación humana — dentro del presupuesto de
5 a 10 horas, frente a 3.071 pares exhaustivos.

> **Corrección (2026-09-20, decisión D9 del backlog).** La tasa del piloto no era
> generalizable. Sobre las 14 series reales el bloqueador con solo el coeficiente
> seleccionaba 712 pares (23,2 %); con el mínimo de 2 tokens compartidos quedan **92**
> pares candidatos. La cifra vigente es 92; las 170 fueron una extrapolación desde las dos
> series de tasa más baja.

Las 18 series elegibles restantes quedan **fuera de la muestra** y no deben inspeccionarse
durante la anotación.

### Series de control para doble anotación

Fijadas ahora, antes de la anotación, como exige OE1:

> **Revisado por el ADR 0005.** La lista vigente es ES2008, ES2016, IS1003, TS3005; ver
> [`0005-adr-development-evaluation-split.md`](0005-adr-development-evaluation-split.md).

> **Registro histórico — lista original de este ADR, superada por el ADR 0005.** Se
> conserva sin editar porque un ADR documenta el historial; no es la lista vigente y no debe
> leerse como tal.
>
> **ES2015, ES2008, IS1004, TS3005** — 4 de 14 series (28,6 %), 115 de 343 decisiones
> (33,5 %), una por sitio más la serie ES más grande. Tres de las cuatro también llevan DDS,
> así que los desacuerdos pueden triangularse contra una capa de anotación independiente.

Ambas anotadoras trabajan sobre copias limpias; el kappa de Cohen se reporta por separado
para existencia del enlace, tipo de relación y **dirección** (hipótesis H3 de la tesis).

## Consecuencias

- La muestra ahora es lo bastante grande como para que el riesgo de la sección 7 de la
  tesis ("muy pocos enlaces temporales para sostener el estrato de E3") deje de ser la
  restricción vinculante. Se reemplaza por otra más tratable: el recall del bloqueador, que
  la tarea C mide directamente.
- El balance de sitio ahora es una propiedad de diseño declarada y debe reportarse junto
  con los resultados.
- **Esta selección no rescata el eje de lengua y no debe presentarse como si lo hiciera.**
  De las 14 series, el bloque TS (4 series, 16 participantes) no tiene ningún dato de
  lengua. La sección 6.3 reporta el eje de forma descriptiva con el bucket de desconocidos
  visible; el eje de rol del hablante, balanceado 6/6/6/6, es el análisis primario de
  equidad.
- Cambiar la selección más adelante invalida cualquier anotación ya hecha bajo ella. Si
  debe cambiar, hay que reemplazar este ADR en vez de editarlo.

## Alternativas rechazadas

- **Las 32 series elegibles completas.** ≈ 1.500 decisiones y ~11.000 pares; incluso a una
  tasa de bloqueo del 5,5 % son ~600 adjudicaciones, más allá del presupuesto humano
  disponible, y no dejaría subconjunto de reserva.
- **Mantener las 6 series DDS originales.** 136 decisiones, 1.111 pares, y el perfil de
  sitio es 2 ES / 3 IS / 1 TS — desbalanceado justo en la variable que resulta ser
  estructuralmente relevante.
- **Maximizar el volumen de decisiones ignorando el sitio.** Seleccionaría fuertemente de
  ES y TS (las series más grandes) y subrepresentaría Idiap, haciendo cualquier diferencia
  ininterpretable.
