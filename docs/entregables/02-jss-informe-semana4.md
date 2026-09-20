| | |
|---|---|
| **Entrega** | Presentación formal del problema (semana 4, AFG1), máximo dos planas |
| **Fecha de envío** | Semana 4 del curso (fecha exacta por completar) |
| **Construido desde** | Versión previa de la propuesta, anterior a la auditoría de datos |
| **Estado** | Congelado tal como se envió. **No se edita.** |

> **Aviso de lectura.** Este documento refleja el diseño de la semana 4. Desde entonces el
> proyecto cambió: se agregó la condición C3 (base construida desde anotación humana), el
> objetivo de atribución de error (OE4), y la muestra pasó a 14 series tras la auditoría.
> La versión vigente de problema, objetivos y bibliografía está en `docs/avances/01`, `03` y
> `04`. Se conserva aquí para poder trazar qué se sabía cuando se entregó.

---

# Representación estructurada de decisiones frente a recuperación aumentada: evaluación experimental sobre transcripciones de reuniones

## 1. Problema

Las decisiones adoptadas en reuniones suelen quedar registradas en transcripciones y notas como texto no estructurado. Esto dificulta recuperar de manera directa qué se decidió, qué evidencia sustenta la decisión y cuál es su estado actual. El problema se acentúa cuando una decisión no se expresa en un único pasaje, sino que se propone, discute y cierra en distintos momentos, o cuando cambia entre reuniones sucesivas. En esos casos, responder una consulta exige reconstruir información distribuida y relacionar una decisión con sus revisiones o reemplazos posteriores. 

Los sistemas de recuperación aumentada por generación (RAG) ofrecen una forma de responder preguntas recuperando fragmentos relevantes desde las transcripciones originales y entregándolos a un modelo generador (Lewis et al., 2020). Sin embargo, una estrategia alternativa consiste en extraer automáticamente las decisiones y persistirlas como objetos estructurados que conserven su contenido, evidencia, estado, relaciones y procedencia. Esta segunda alternativa introduce un problema adicional: cualquier omisión o error producido durante la extracción puede propagarse a las consultas posteriores. Por ello, no es suficiente comparar respuestas finales sin conocer previamente la calidad con que se construyó la representación. 

El problema de investigación se formula, entonces, como la falta de evidencia experimental controlada sobre el desempeño relativo de dos estrategias aplicadas al mismo conjunto de reuniones: C1, RAG documental sobre las transcripciones, y C2, una base estructurada construida automáticamente a partir de esas mismas transcripciones. La comparación debe considerar especialmente consultas sobre evidencia, vigencia, evolución y reemplazo de decisiones, manteniendo constantes las preguntas, el modelo generador y los supuestos del contexto. El propósito no es asumir que una estrategia es superior, sino establecer en qué condiciones cada una ofrece mejores resultados y qué limitaciones introduce la extracción automática. Esta distinción es relevante porque ambas condiciones pueden fallar por mecanismos diferentes: C1 depende de recuperar fragmentos documentales suficientes para reconstruir una decisión, mientras que C2 depende de que la extracción previa preserve correctamente los atributos y vínculos necesarios para responder. En consecuencia, la evaluación debe considerar tanto la calidad de la evidencia recuperada como la respuesta final y su trazabilidad. 

## 2. Objetivos

* **Objetivo general**: Evaluar experimentalmente el aporte de una representación estructurada y generada automáticamente de decisiones frente a un sistema RAG documental aplicado directamente sobre transcripciones de reuniones, considerando la calidad, trazabilidad, temporalidad y eficiencia de las respuestas. 
* **Objetivos específicos**: 
  1. Evaluar la capacidad de métodos de extracción automática para detectar decisiones, vincularlas con su evidencia y representar su estado y relaciones temporales respecto de una referencia humana adjudicada. 
  2. Construir, con un extractor previamente seleccionado y congelado, la condición C2 de base estructurada automática. 
  3. Comparar C1 y C2 mediante un banco común de preguntas, distinguiendo tipos de consulta y evaluando por separado la recuperación de evidencia y la calidad de la respuesta. 
  4. Analizar las diferencias observadas entre ambas condiciones mediante métricas de calidad, trazabilidad y eficiencia, sin atribuir causalmente el resultado final a un único componente del pipeline. 

## 3. Revisión bibliográfica breve

La detección automática de decisiones en conversaciones multiparte cuenta con antecedentes directos. Hsueh y Moore (2007) estudiaron la identificación de actos de diálogo asociados a decisiones en reuniones, mientras que Fernández et al. (2008) y Bui et al. (2009) desarrollaron métodos específicos para modelar y extraer decisiones en diálogo multiparte. Estos trabajos muestran que la decisión puede tratarse como un objeto de análisis computacional, pero se concentran principalmente en su detección o extracción. Para el problema planteado, este antecedente es necesario pero no suficiente: una decisión útil para consulta posterior requiere conservar no sólo su identificación, sino también la evidencia que la sustenta y las relaciones que permiten interpretar cambios de estado entre reuniones. 

En paralelo, RAG formalizó una arquitectura en la que la generación se apoya en información recuperada desde una colección externa, permitiendo responder consultas sin incorporar todo el conocimiento en los parámetros del modelo (Lewis et al., 2020). Más recientemente, se ha mostrado que los modelos de lenguaje pueden producir registros estructurados a partir de texto y capturar entidades y relaciones en formatos utilizables por sistemas posteriores (Dagdelen et al., 2024). Estos antecedentes sustentan técnicamente las dos alternativas consideradas en este proyecto: recuperar directamente desde el texto o transformar previamente ese texto en una representación estructurada. La comparación resulta pertinente porque la primera alternativa conserva el documento como fuente primaria de recuperación, mientras que la segunda introduce una etapa de transformación que puede facilitar consultas sobre atributos y relaciones, pero también perder información si la extracción es incompleta o incorrecta. 

El estudio se realizará sobre el AMI Meeting Corpus, un corpus multimodal de reuniones que dispone de transcripciones y anotaciones lingüísticas y que incluye series de reuniones con continuidad temática (Carletta et al., 2006). Esta característica permite estudiar no sólo decisiones puntuales, sino también su evolución entre sesiones. A partir de estos antecedentes, el aporte del proyecto se sitúa en la comparación controlada entre RAG documental y una base estructurada automática sobre un mismo corpus y un mismo banco de preguntas, separando previamente la evaluación de la extracción de la comparación end-to-end de los dos pipelines. Esta separación permite interpretar los resultados sin confundir la calidad del extractor con el desempeño global de C2 y, al mismo tiempo, mantener una referencia común para contrastar ambas estrategias bajo condiciones equivalentes. 

## Referencias

* Carletta, J., Ashby, S., Bourban, S., Flynn, M., Guillemot, M., Hain, T., et al. (2006). The AMI Meeting Corpus: A Pre-announcement. In S. Renals & S. Bengio (Eds.), Machine Learning for Multimodal Interaction (pp. 28–39). Springer. https://doi.org/10.1007/11677482_3 
* Dagdelen, J., Dunn, A., Lee, S., Walker, N., Rosen, A. S., Ceder, G., Persson, K. A., & Jain, A. (2024). Structured information extraction from scientific text with large language models. Nature Communications, 15, 1418. https://doi.org/10.1038/s41467-024-45563-x 
* Fernández, R., Frampton, M., Ehlen, P., Purver, M., & Peters, S. (2008). Modelling and Detecting Decisions in Multi-party Dialogue. Proceedings of the 9th SIGdial Workshop on Discourse and Dialogue, 156–163. 
* Hsueh, P.-Y., & Moore, J. D. (2007). What Decisions Have You Made?: Automatic Decision Detection in Meeting Conversations. Human Language Technologies 2007: NAACL-HLT, 25–32. 
* Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. Advances in Neural Information Processing Systems, 33. 
* Bui, T., Frampton, M., Dowding, J., & Peters, S. (2009). Extracting Decisions from Multi-Party Dialogue Using Directed Graphical Models and Semantic Similarity. Proceedings of the SIGDIAL 2009 Conference, 235–243.

