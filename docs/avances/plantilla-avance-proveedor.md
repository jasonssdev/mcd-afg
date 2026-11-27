# Plantilla: avance por laboratorio de la extensión con modelos de pago

> **Esto es una plantilla, no un avance.** No lleva número. Para un laboratorio nuevo, se copia a
> `docs/avances/NN-jss-extraccion-<proveedor>.md` (con el siguiente correlativo libre), se reemplaza
> cada `{{MARCADOR}}`, se borran los bloques de instrucciones (`> **Instrucción.**`) y se
> agrega la fila a [`README.md`](README.md). El modelo a imitar es
> [`15-jss-extraccion-google.md`](15-jss-extraccion-google.md).

> **Instrucción.** Antes de escribir, ejecuta el notebook del laboratorio
> (`notebooks/NN-jss-extraccion-<proveedor>.ipynb`, copia del
> [notebook 35](../../notebooks/35-jss-extraccion-google.ipynb) con otro `PROVIDER`). **Toda cifra sale
> de ese notebook**: ninguna se calcula aquí ([`CONTRIBUTING.md`](../../CONTRIBUTING.md) §7.1). La
> columna «Celda» de la tabla del final dice de dónde sale cada marcador. Reglas de redacción:
> lenguaje para un lector no técnico, sin mencionar herramientas, sin primera persona del singular;
> el modelo pequeño y el grande se describen con su nombre de modelo, y las cifras con coma decimal.
> No se muestran frases de decisión ni contenido de transcripciones (ADR 0005).

---

# Extracción con modelos de {{PROVEEDOR}}

| | |
|---|---|
| **Documento** | {{NN}} — Extracción con modelos de {{PROVEEDOR}} |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.0 |
| **Fecha** | {{FECHA}} |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | {{FECHA}} | Versión inicial. Resultado de las corridas de los dos modelos de {{PROVEEDOR}} (`{{MODELO_PEQUENO}}` y `{{MODELO_GRANDE}}`) como extractor de C2, frente a la corrida formal y a la línea base de OpenKOS 0.7.3. | Las corridas completas de {{PROVEEDOR}} terminaron y ningún documento registraba su resultado. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

> **Alcance.** Este documento reporta solo la parte de {{PROVEEDOR}} de la extensión del Experimento A
> con modelos de pago ([ADR 0026](../decisions/0026-adr-extension-extractor-con-modelos-hosted.md)).
> Los resultados de los otros laboratorios tienen su propio documento, y uno general cierra la
> extensión. No presenta cifras del Experimento B. Las series son de **evaluación**: se muestran
> identificadores y cifras agregadas, nunca frases de decisión ni contenido de transcripciones
> ([ADR 0005](../decisions/0005-adr-development-evaluation-split.md)). Cada cifra remite al
> [notebook {{NN_NOTEBOOK}}](../../notebooks/{{ARCHIVO_NOTEBOOK}}), que es el análisis que la
> respalda. Es un resultado **descriptivo**: las series de evaluación ya se usaron en la corrida
> formal, de modo que nada de lo que sigue confirma una hipótesis de la tesis.

## En una página

- **Qué se hizo.** Se reemplazó el modelo pequeño que extrae las decisiones (`qwen3:8b`, que corre
  en el computador del proyecto) por dos modelos de pago de {{PROVEEDOR}}, y se repitió la extracción
  sobre las mismas 11 series de evaluación, 3 veces cada una. El modelo pequeño es
  `{{MODELO_PEQUENO}}` y el grande, `{{MODELO_GRANDE}}`.
- **Resultado del modelo grande.** {{UNA_FRASE: recall y precisión frente a la corrida formal, en
  lenguaje llano («encuentra el X % de las decisiones de la referencia, frente al Y %»), y el
  veredicto de la regla}}.
- **Resultado del modelo pequeño.** {{IDEM}}.
- **Costo y tiempo.** El modelo pequeño costó **USD {{COSTO_PEQUENO}}** y tardó {{DURACION_PEQUENO}};
  el grande costó **USD {{COSTO_GRANDE}}** y tardó {{DURACION_GRANDE}}. La corrida formal, local,
  tardó 11 h 48 min y no tiene costo de uso.
- **Qué significa para la tesis.** {{UNA_FRASE: si un extractor más fuerte de este laboratorio
  encuentra más decisiones; aclarar que las respuestas de C2 se miden aparte}}.

## 1. Qué pregunta responde y por qué importa

Copiar la sección 1 del [documento 15](15-jss-extraccion-google.md) y cambiar solo la frase final:
«Este documento cubre los dos de {{PROVEEDOR}}, el {{ORDINAL}} laboratorio en terminar».

## 2. Cómo se mide

Copiar la sección 2 del [documento 15](15-jss-extraccion-google.md) sin cambios (las definiciones de
precisión, recall, F1, la regla de mejora y el nivel del intervalo son las mismas para los seis
modelos). Si la regla del ADR 0026 cambió por una enmienda, actualizar el texto y declararlo en el
historial de versiones.

## 3. Resultados

### 3.1 Las corridas terminaron completas

{{PARES}} repeticiones terminadas por modelo (de 33), {{EXTRACCIONES_COMPLETAS}} extracciones por
reunión completas (de 132) y {{CON_ESTADO}} reuniones con marca de fallo de la extracción. Piloto de una
serie: USD {{COSTO_PILOTO_PEQUENO}} el pequeño y USD {{COSTO_PILOTO_GRANDE}} el grande. Si hubo
reuniones con marca de fallo o pares fallidos, decir cuántos y qué se hizo; esas reuniones aportan cero
decisiones a precisión y recall.

### 3.2 Calidad de la extracción

Con el criterio principal (umbral 0,70), cada cifra y su diferencia con la corrida formal:

| Medida | Corrida formal | {{ETIQUETA_PEQUENO}} | Diferencia ({{ETIQUETA_PEQUENO}}) | {{ETIQUETA_GRANDE}} | Diferencia ({{ETIQUETA_GRANDE}}) |
|---|---|---|---|---|---|
| Precisión | 0,149 | {{P_PEQ}} | {{DP_PEQ}} (de {{DP_PEQ_LO}} a {{DP_PEQ_HI}}) | {{P_GR}} | {{DP_GR}} (de {{DP_GR_LO}} a {{DP_GR_HI}}) |
| Recall | 0,308 | {{R_PEQ}} | {{DR_PEQ}} (de {{DR_PEQ_LO}} a {{DR_PEQ_HI}}) | {{R_GR}} | {{DR_GR}} (de {{DR_GR_LO}} a {{DR_GR_HI}}) |
| F1 | 0,201 | {{F_PEQ}} | {{DF_PEQ}} (de {{DF_PEQ_LO}} a {{DF_PEQ_HI}}) | {{F_GR}} | {{DF_GR}} (de {{DF_GR_LO}} a {{DF_GR_HI}}) |
| Veredicto | | | **{{VEREDICTO_PEQ}}** | | **{{VEREDICTO_GR}}** |

- **Un punto por modelo.** Explicar el veredicto con la regla (recall con intervalo entero sobre cero y
  precisión sin bajar más de 0,05). Si el intervalo del recall incluye el cero, decir que el
  veredicto es «sin diferencia demostrada» aunque la precisión o el F1 suban.
- **Sensibilidad al umbral.** Decir en qué umbrales (0,75 y 0,80) cambia el veredicto, como
  sensibilidad y no como criterio.
- **Contra la línea base de la misma versión.** Decir si los veredictos coinciden con los de la corrida
  formal.

### 3.3 Cuántas decisiones extrae cada modelo

La referencia tiene **6,3** decisiones por reunión en promedio; `qwen3:8b` extrae 13,1 (formal);
{{ETIQUETA_PEQUENO}}, **{{DEC_PEQ}}**; {{ETIQUETA_GRANDE}}, **{{DEC_GR}}**. Explicar con eso el patrón
entre precisión y recall.

### 3.4 Tiempo y costo

| | Mediana por reunión | Tiempo total de la corrida | Costo de la corrida | Costo mediano por reunión |
|---|---|---|---|---|
| `qwen3:8b` (corrida formal, local) | 307 s | 11 h 48 min | sin costo de uso | — |
| {{ETIQUETA_PEQUENO}} | {{SEG_PEQ}} s | {{DUR_PEQ}} | USD {{COSTO_PEQ}} | USD {{COSTO_REU_PEQ}} |
| {{ETIQUETA_GRANDE}} | {{SEG_GR}} s | {{DUR_GR}} | USD {{COSTO_GR}} | USD {{COSTO_REU_GR}} |

Decir si el costo es **exacto** o una **cota inferior** (la columna «Exactitud» del notebook), qué
precios se usaron con su fecha y si alguna promoción vence (las notas de precio de la sección 8 del
notebook), y recordar que el tiempo no es una comparación limpia (local frente a servidores del
proveedor).

## 4. Qué significa para la tesis

La pregunta de la tesis es si **un extractor más fuerte arregla el eslabón más débil**. Escribir, con
las cifras de este laboratorio: lo que sí muestra la medición, el equilibrio entre calidad, tiempo y
costo, lo que no se puede decir todavía (que las **respuestas** de C2 mejoren se mide aparte con el
Experimento B de C2, ADR 0026, tercera enmienda), los límites (dos modelos de un solo laboratorio, 11
series, `reasoning_effort = low`, modelos que cambian sin aviso, series ya usadas) y lo que sigue.

---

## De dónde sale cada cifra (se borra al usar la plantilla)

| Marcador | Celda del notebook del laboratorio |
|---|---|
| `{{MODELO_PEQUENO}}`, `{{MODELO_GRANDE}}` | Sección 1, tabla de modelos (columna «Modelo») |
| Duraciones, `{{DURACION_*}}`, `{{DUR_*}}` | Sección 2, fila «Duración (inicio a fin del manifiesto)» |
| `{{COSTO_PILOTO_*}}` | Sección 3, tabla de pilotos, columna «Costo (USD)» |
| `{{PARES}}`, `{{EXTRACCIONES_COMPLETAS}}`, `{{CON_ESTADO}}` | Sección 4, tabla de completitud |
| `{{P_*}}`, `{{R_*}}`, `{{F_*}}`, `{{D*_*}}`, veredictos | Sección 5, tablas contra la línea base principal (la formal) con τ = 0,70; los intervalos con tres decimales salen de la «Lectura» de esa sección |
| Sensibilidad al umbral | Sección 6, tabla y «Lectura» |
| `{{DEC_*}}` y referencia por reunión | Sección 7, primera tabla |
| `{{SEG_*}}` | Sección 7, tablas de tiempo (mediana por reunión) |
| `{{COSTO_*}}`, `{{COSTO_REU_*}}`, exactitud, precios y promociones | Sección 8, tabla y notas de precio |
| Resumen de veredictos | Sección 9, tabla |
