# Aspectos éticos

| | |
|---|---|
| **Documento** | 05 — Aspectos éticos |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.2 |
| **Fecha** | 2026-09-20 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial. Aspectos éticos para AFG1. | Primera entrega del curso. |
| 1.1 | 2026-09-20 | Partes involucradas explícitas; se retira la atribución al curso de la regla "dos o tres principios" | Precisión de redacción |
| 1.2 | 2026-09-20 | Tabla que ancla cada principio a la etapa del flujo de datos donde se aplica | Revisión final de AFG1 |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## Por qué tres principios, no diez

Optamos por tratar tres principios en profundidad en lugar de enumerar muchos:
**transparencia y trazabilidad**, **justicia y equidad**, **responsabilidad**. Para cada uno
se hacen dos cosas: justificar su relevancia para este proyecto específico, y conectarlo con
una decisión concreta de la metodología. Un principio ético que no se traduce en una métrica
reportada es una declaración de buenas intenciones, no un compromiso verificable.

## Partes involucradas

- **Los participantes del corpus AMI.** Identificadores anonimizados, sin reidentificación.
- **Las personas que anotan.** Carga de trabajo y criterios explícitos en el manual de
  anotación.
- **Los revisores y lectores de la tesis.**
- **Las organizaciones que adoptarían un sistema así.** Es la razón por la que la ejecución
  local es un requisito de diseño.

## Dónde se aplica cada principio

| Etapa del flujo | Principio | Aplicación concreta |
|---|---|---|
| Definición del problema | Responsabilidad | El riesgo de persistir errores se convierte en objeto de medición (OE4), no en advertencia |
| Preprocesamiento y auditoría de datos | Justicia y equidad | Se auditan los ejes de rol y de lengua antes de modelar; la lengua se declara limitación por estar anidada en el sitio |
| Modelado y evaluación | Transparencia y trazabilidad | Toda decisión extraída conserva su evidencia; el juez automático pertenece a otra familia de modelos y se valida con personas |
| Implementación y uso | Responsabilidad, transparencia | Ejecución local como requisito de diseño; resultados por hablante solo agregados por categoría |

## 1. Transparencia y trazabilidad

No la tratamos como aspiración, sino como propiedad medible. **Toda decisión extraída mantiene
trazabilidad al fragmento de transcripción que la respalda**, y la tasa de soporte de
evidencia es un resultado reportado del Experimento B (documento 03, OE3), no una
característica declarada del sistema. Esto tiene una consecuencia dura: **una afirmación sin
fuente identificable cuenta como falla aunque sea correcta**. No basta con que el sistema
acierte; tiene que poder mostrar por qué.

Esta decisión conecta directamente con el diseño de la representación (documento 06, §5–6):
cada objeto de decisión se almacena con procedencia —reunión de origen, rango de actos de
diálogo— desde su creación, no como metadato añadido después. Y conecta con la auditoría
misma: el 92,4 % de anclaje a evidencia (documento 02, §4.7) es la misma métrica aplicada
retroactivamente al corpus de referencia, antes de aplicarla al sistema evaluado.

## 2. Justicia y equidad

El análisis primario es el eje de **rol del hablante** (Project Manager, Diseñador
Industrial, Experto en Marketing, Diseñador de Interfaz), con tasa base medida: el PM
concentra el 47,0 % de los actos de decisión atribuidos (documento 02, §4.6), consistente
entre sitios (44 %–50 %). Esto importa porque un sistema que extrae mejor lo que dice quien
preside la reunión amplifica una jerarquía que ya existe en el registro organizacional. La
pregunta correcta no es si el recall del PM es alto —47 % refleja el corpus, no
necesariamente un sesgo del sistema—, sino **si el sistema lo favorece más de lo que ya lo
favorece el material fuente**. Esa comparación (recall del sistema por rol contra la
proporción base del corpus) es la que se reporta.

El eje **nativo/no-nativo de inglés**, que la propuesta original trataba como
estratificación obligatoria, **baja a limitación declarada**. La razón no es de tamaño
muestral: la lengua materna está perfectamente anidada en el sitio de grabación —Edinburgh
casi todo nativo, Idiap mayoritariamente no nativo, y el sitio TNO sin un solo participante
registrado en `participants.xml`— así que en este corpus no existe forma de separar
"hablante no nativo" de "grabado en Idiap" (documento 02, §4.5). Declarar esta incapacidad
medida es en sí mismo información: un resultado nulo con la limitación explicitada vale más
que una estratificación que en realidad mide otra cosa y la disfraza de lengua.

## 3. Responsabilidad

El proyecto asume explícitamente el riesgo de compilar errores en la memoria organizacional
y lo convierte en objeto de medición —OE4— en lugar de en advertencia. La cifra principal
reportada, no una nota al pie, es la **proporción de respuestas incorrectas de C2
atribuibles a errores persistidos en la extracción** (documento 03, OE4; documento 06, §7).

Esta decisión no es cosmética: es la que separa este trabajo de la literatura que mide
exactitud de extracción en una sola pasada. El riesgo real de una base persistente es que un
error se escribe una vez y se lee muchas veces —adquiere apariencia de hecho verificado y se
convierte en premisa de razonamientos posteriores (documento 01, §3)—. Medir esa cadena, no
sólo el punto de extracción, es la operacionalización del principio.

**Marco de referencia:** NIST AI Risk Management Framework 1.0 (Tabassi, 2023), funciones
*Measure* y *Manage*, aplicado a las categorías de validez, transparencia y sesgo. El propio
NIST señala que el marco está en revisión, lo que se declara para no presentarlo como
estándar cerrado.

## Aclaración necesaria sobre privacidad

El corpus AMI es público y está licenciado CC BY 4.0 (documento 02, §1). **Este proyecto no
procesa datos personales sensibles.** El argumento de privacidad que sí es relevante no se
refiere a los datos del experimento, sino a la **condición de despliegue** del método: un
sistema de memoria de decisiones sólo es adoptable en una organización real si puede operar
sin enviar deliberaciones internas a servicios de terceros. La ejecución local es, por tanto,
un requisito de diseño para que los resultados sean transferibles a una organización real —no
una medida de protección del material experimental, que ya es público. Confundir ambas cosas
debilitaría tanto el argumento ético como el metodológico.

## Uso del corpus

Atribución conforme a CC BY 4.0. Los identificadores de participante se conservan en su
forma anonimizada original; no se intenta reidentificación. Los resultados estratificados
por hablante —incluidos rol y, donde se reporte como limitación, sitio de grabación— se
publican agregados por categoría, **nunca por individuo**.

---

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| Los tres principios tratados en profundidad: transparencia, justicia y equidad, responsabilidad | [`../propuesta.md`](../propuesta.md) §6.2–§6.4 |
| Tasa de soporte de evidencia 92,4 % (317/343) | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Autoría por rol, PM 47,0 % (44 %–50 % por sitio) | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Anidamiento lengua/sitio; eje de lengua baja a limitación | [`../BACKLOG.md`](../BACKLOG.md), decisión D7 |
| NIST AI RMF 1.0, funciones Measure y Manage | `bibliography/refs.bib` `tabassi2023airmf` |
| Corpus público, CC BY 4.0 | [`../../config/corpus.toml`](../../config/corpus.toml) |
