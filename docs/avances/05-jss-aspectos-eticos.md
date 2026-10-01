# Aspectos éticos

| | |
|---|---|
| **Documento** | 05 — Aspectos éticos |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.3 |
| **Fecha** | 2026-10-01 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial. Aspectos éticos para AFG1. | Primera entrega del curso. |
| 1.1 | 2026-09-20 | Partes involucradas explícitas; se retira la atribución al curso de la regla "dos o tres principios" | Precisión de redacción |
| 1.2 | 2026-09-20 | Tabla que ancla cada principio a la etapa del flujo de datos donde se aplica | Revisión final de AFG1 |
| 1.3 | 2026-10-01 | Reescritura completa de la redacción: cada principio se presenta primero con un caso real de los datos y después con la regla que se deriva, cada término técnico se explica al aparecer y se agrega un glosario breve. Los tres principios, las cifras, las partes involucradas y el marco de referencia no cambian. | Retroalimentación de la revisión entre equipos de la semana 8: el problema y la metodología no se entendían, menos aún para una audiencia no técnica. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## Tres situaciones que ya ocurrieron en los datos

Las cuestiones éticas de este proyecto no son hipotéticas. Las tres aparecieron al revisar
el corpus, antes de construir nada.

La primera: el resumen oficial de una reunión afirma que el equipo eliminó un botón del
control remoto. La transcripción muestra que se mantuvo. Un sistema que repitiera ese
resumen respondería con seguridad algo falso, y sin la fuente al lado nadie podría notarlo.

La segunda: en estas reuniones, casi la mitad de las decisiones las enuncia el jefe de
proyecto. Si alguien pregunta qué se decidió sobre el material de la carcasa y el sistema
sólo recupera lo que dijo quien preside, el diseñador industrial que propuso la idea
desaparece del registro.

La tercera: una base de decisiones se escribe una vez y se lee muchas veces. Si la máquina
anota mal una decisión y nadie la corrige, meses después ese error ya no parece un error.
Parece un hecho, y alguien decide sobre él.

De esas tres situaciones salen los tres principios de este documento. Cada uno se traduce
en algo que se mide, no sólo en algo que se declara.

## Por qué tres principios, no diez

Optamos por tratar tres principios en profundidad en lugar de enumerar muchos:
**transparencia y trazabilidad**, **justicia y equidad**, **responsabilidad**. Para cada uno
se hacen dos cosas: justificar su relevancia para este proyecto específico, y conectarlo con
una decisión concreta de la metodología. Un principio ético que no se traduce en una métrica
reportada es una declaración de buenas intenciones, no un compromiso verificable.

## Partes involucradas

- **Los participantes del corpus AMI.** Las personas que aparecen en las grabaciones. Sus
  identificadores están anonimizados y no se intenta reidentificarlas.
- **Las personas que anotan.** Los integrantes del equipo que marcan a mano las decisiones
  y sus relaciones. Su carga de trabajo y sus criterios están explícitos en el manual de
  anotación.
- **Los revisores y lectores de la tesis.** Quienes necesitan poder verificar cada cifra.
- **Las organizaciones que adoptarían un sistema así.** Las que grabarían sus propias
  reuniones. Es la razón por la que la ejecución local, es decir, que el sistema corra en
  computadores propios sin enviar datos a terceros, es un requisito de diseño.

## Dónde se aplica cada principio

El proyecto tiene cuatro etapas, desde definir el problema hasta imaginar el sistema en uso.
Cada principio tiene un lugar concreto en ese recorrido:

| Etapa del flujo | Principio | Aplicación concreta |
|---|---|---|
| Definición del problema | Responsabilidad | El riesgo de persistir errores se convierte en objeto de medición (OE4), no en advertencia |
| Preprocesamiento y auditoría de datos | Justicia y equidad | Se auditan los ejes de rol y de lengua antes de modelar; la lengua se declara limitación por estar anidada en el sitio |
| Modelado y evaluación | Transparencia y trazabilidad | Toda decisión extraída conserva su evidencia; el juez automático pertenece a otra familia de modelos y se valida con personas |
| Implementación y uso | Responsabilidad, transparencia | Ejecución local como requisito de diseño; resultados por hablante solo agregados por categoría |

## 1. Transparencia y trazabilidad

**El caso.** El resumen abstractivo de AMI para una de las reuniones de desarrollo afirma
que el equipo eliminó el botón turbo del control remoto. Al ir a la transcripción, el botón
se mantuvo (documento 02, §5). El resumen lo escribió una persona, y aun así está mal. Un
sistema que respondiera "se eliminó el botón turbo" citando ese resumen daría una respuesta
segura, bien redactada y falsa. Lo único que habría permitido detectarlo es el fragmento de
conversación que supuestamente la respalda, porque ese fragmento no existe.

**La regla.** No tratamos la transparencia como aspiración, sino como propiedad medible.
**Toda decisión extraída mantiene trazabilidad al fragmento de transcripción que la
respalda**, y la tasa de soporte de evidencia (qué proporción de las respuestas viene con
su fragmento) es un resultado reportado del Experimento B (documento 03, OE3), no una
característica declarada del sistema. Esto tiene una consecuencia dura: **una afirmación sin
fuente identificable cuenta como falla aunque sea correcta**. No basta con que el sistema
acierte; tiene que poder mostrar por qué.

Esta decisión conecta directamente con el diseño de la representación (documento 06, §5–6):
cada objeto de decisión se almacena con procedencia —reunión de origen, rango de actos de
diálogo— desde su creación, no como metadato añadido después. Es la diferencia entre un
expediente donde cada afirmación trae su documento adjunto y uno donde los adjuntos se
buscan después, si alguien los pide. Y conecta con la auditoría misma: el 92,4 % de anclaje
a evidencia (documento 02, §4.7) es la misma métrica aplicada retroactivamente al corpus de
referencia, antes de aplicarla al sistema evaluado. Primero se midió cuántas decisiones del
propio corpus tienen fuente; después se exigirá lo mismo al sistema.

## 2. Justicia y equidad

**El caso.** En el escenario del corpus cada participante tiene un rol: jefe de proyecto
(PM), diseñador industrial (ID), experto en marketing (ME) y diseñador de interfaz (UI). El
PM concentra el 47,0 % de los actos de decisión atribuidos (documento 02, §4.6), y la
proporción es consistente entre sitios (44 %–50 %). Eso viene del material: quien preside
habla más y cierra las discusiones. Ahora bien, si alguien pregunta qué decidió el equipo
sobre el material de la carcasa y el sistema sólo recupera lo que dijo el PM, el diseñador
industrial que propuso la idea desaparece del registro. El sistema no habría creado la
jerarquía, pero la habría amplificado.

**La regla.** El análisis primario es el eje de **rol del hablante**, con tasa base medida.
Un sistema que extrae mejor lo que dice quien preside la reunión amplifica una jerarquía
que ya existe en el registro organizacional. La pregunta correcta no es si el recall del PM
es alto (recall es la proporción de decisiones reales de un hablante que el sistema
recupera; 47 % refleja el corpus, no necesariamente un sesgo del sistema), sino **si el
sistema lo favorece más de lo que ya lo favorece el material fuente**. Esa comparación
(recall del sistema por rol contra la proporción base del corpus) es la que se reporta.

**Lo que no se puede medir, y por qué se dice.** El eje **nativo/no-nativo de inglés**, que
la propuesta original trataba como estratificación obligatoria (es decir, como un desglose
que debía reportarse siempre), **baja a limitación declarada**. La razón no es de tamaño
muestral: la lengua materna está perfectamente anidada en el sitio de grabación —Edinburgh
casi todo nativo, Idiap mayoritariamente no nativo, y el sitio TNO sin un solo participante
registrado en `participants.xml`— así que en este corpus no existe forma de separar
"hablante no nativo" de "grabado en Idiap" (documento 02, §4.5). Si el sistema funcionara
peor en Idiap, no se sabría si es por la lengua o por la sala. Declarar esta incapacidad
medida es en sí mismo información: un resultado nulo con la limitación explicitada vale más
que una estratificación que en realidad mide otra cosa y la disfraza de lengua.

## 3. Responsabilidad

**El caso.** Con RAG, si el sistema responde mal, el error dura lo que dura esa respuesta;
la siguiente pregunta vuelve a leer los documentos originales. Con una base de decisiones
no. Si la máquina anota mal que el equipo eliminó el botón turbo, esa anotación queda
escrita, se lee en cada consulta y, si nadie la corrige, con el tiempo deja de parecer un
error: se convierte en la premisa de la siguiente decisión del equipo.

**La regla.** El proyecto asume explícitamente el riesgo de compilar errores en la memoria
organizacional y lo convierte en objeto de medición —OE4— en lugar de en advertencia. La
cifra principal reportada, no una nota al pie, es la **proporción de respuestas incorrectas
de C2 atribuibles a errores persistidos en la extracción** (documento 03, OE4; documento 06,
§7). C2 es la condición en que la base la construye la máquina; de cada respuesta equivocada
se determina si el error nació al escribir la base, al buscar en ella o al redactar.

Esta decisión no es cosmética: es la que separa este trabajo de la literatura que mide
exactitud de extracción en una sola pasada. El riesgo real de una base persistente es que un
error se escribe una vez y se lee muchas veces —adquiere apariencia de hecho verificado y se
convierte en premisa de razonamientos posteriores (documento 01, §3)—. Medir esa cadena, no
sólo el punto de extracción, es la operacionalización del principio: la forma concreta en
que el principio se vuelve un número.

**Marco de referencia:** NIST AI Risk Management Framework 1.0 (Tabassi, 2023), funciones
*Measure* y *Manage*, aplicado a las categorías de validez, transparencia y sesgo. Es la guía
del instituto de estándares de Estados Unidos para gestionar riesgos de sistemas de
inteligencia artificial; sus funciones *Measure* (medir) y *Manage* (gestionar) son las que
este proyecto aplica. El propio NIST señala que el marco está en revisión, lo que se declara
para no presentarlo como estándar cerrado.

## Aclaración necesaria sobre privacidad

El corpus AMI es público y está licenciado CC BY 4.0 (documento 02, §1). **Este proyecto no
procesa datos personales sensibles.** El argumento de privacidad que sí es relevante no se
refiere a los datos del experimento, sino a la **condición de despliegue** del método: un
sistema de memoria de decisiones sólo es adoptable en una organización real si puede operar
sin enviar deliberaciones internas a servicios de terceros. Ninguna empresa va a subir sus
reuniones de directorio a un servicio externo para que las resuma. La ejecución local es,
por tanto, un requisito de diseño para que los resultados sean transferibles a una
organización real —no una medida de protección del material experimental, que ya es público.
Confundir ambas cosas debilitaría tanto el argumento ético como el metodológico.

## Uso del corpus

Atribución conforme a CC BY 4.0. Los identificadores de participante se conservan en su
forma anonimizada original; no se intenta reidentificación. Los resultados estratificados
por hablante —incluidos rol y, donde se reporte como limitación, sitio de grabación— se
publican agregados por categoría, **nunca por individuo**.

## Glosario breve

| Término | Qué significa en este documento |
|---|---|
| Trazabilidad | Que cada decisión registrada apunte al fragmento exacto de conversación que la respalda. |
| Tasa de soporte de evidencia | Proporción de respuestas del sistema que vienen acompañadas de su fragmento de respaldo. |
| Recall por rol | De las decisiones que dijo una persona con cierto rol, qué proporción recupera el sistema. |
| Estratificación | Desglosar los resultados por grupos (rol, sitio) para ver si el sistema trata a todos igual. |
| Limitación declarada | Un desglose que no se puede hacer con estos datos y se dice explícitamente, en lugar de reportarse como si midiera algo. |
| Ejecución local | Que el sistema corra en computadores propios, sin enviar las reuniones a servicios externos. |

---

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| Los tres principios tratados en profundidad: transparencia, justicia y equidad, responsabilidad | [`../propuesta.md`](../propuesta.md) §6.2–§6.4 |
| Tasa de soporte de evidencia 92,4 % (317/343) | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Autoría por rol, PM 47,0 % (44 %–50 % por sitio) | [`../../notebooks/00-jss-corpus-y-auditoria.ipynb`](../../notebooks/00-jss-corpus-y-auditoria.ipynb) |
| Anidamiento lengua/sitio; eje de lengua baja a limitación | [`../decisions/README.md`](../decisions/README.md), decisión D7 |
| NIST AI RMF 1.0, funciones Measure y Manage | `bibliography/refs.bib` `tabassi2023airmf` |
| Corpus público, CC BY 4.0 | [`../../config/corpus.toml`](../../config/corpus.toml) |
| Botón turbo: el resumen afirma una eliminación que la transcripción contradice | [`02-jss-fuente-de-datos.md`](02-jss-fuente-de-datos.md) §5; [`../anotacion/manual-anotacion-oe1.md`](../anotacion/manual-anotacion-oe1.md) §3 |
