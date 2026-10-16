# Bibliografía

| | |
|---|---|
| **Documento** | 04 — Bibliografía |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.5 |
| **Fecha** | 2026-10-15 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial. Bibliografía APA 7 para AFG1. | Primera entrega del curso. |
| 1.1 | 2026-09-20 | Correcciones de autores, títulos y sufijos a/b; entrada de la licencia AMI en refs.bib. | Verificación contra la API de arXiv y DOI, 2026-09-20. |
| 1.2 | 2026-10-01 | Se agrega una guía de lectura al inicio y, en cada sección temática, un párrafo que explica en lenguaje llano para qué sirve ese grupo de fuentes en el proyecto. Las entradas bibliográficas no cambian: ni una letra. | Retroalimentación de la revisión entre equipos de la semana 8: el problema y la metodología no se entendían, menos aún para una audiencia no técnica. |
| 1.3 | 2026-10-15 | Se agrega la sección «Trabajos relacionados y su vínculo con el proyecto»: análisis de cuatro grupos de trabajos ya incluidos en la bibliografía (GraphRAG; detección de decisiones en AMI; auditoría de decisiones; modelos de lenguaje como jueces), con lo que el proyecto toma de cada uno y el vacío que aborda frente a él. No se agrega ni se modifica ninguna entrada bibliográfica. | La rúbrica de la presentación final de AFG2 pide al menos dos trabajos relacionados, con un análisis claro de cómo se relacionan con el proyecto y lo complementan. |
| 1.4 | 2026-10-15 | Se usan los nombres estándar de métricas y técnicas sin traducir (LLM-as-a-judge). | Convención del equipo: los nombres de métricas y técnicas no se traducen. |
| 1.5 | 2026-10-15 | Se actualiza la nota de ConsistencyGate al estado cerrado: el trabajo fue leído (2026-10-07) y no acota la afirmación de novedad (`propuesta.md` §9). Se corrigen las referencias de numeración a las secciones reales de este documento (1 a 7). Las entradas bibliográficas no cambian. | Auditoría de gobernanza del 2026-10-15: la nota seguía pidiendo una lectura ya hecha y citaba secciones 8.x que no existen en este documento. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

## Cómo leer esta bibliografía

Una bibliografía de tesis suele leerse como una lista de nombres. Esta se puede leer de
otra manera: como el mapa de las conversaciones en que el proyecto participa. Cada sección
temática reúne los trabajos que responden a una misma pregunta, y empieza con un párrafo que
dice, sin tecnicismos, cuál es esa pregunta y qué aporta el grupo al proyecto. Quien quiera
entender por qué el proyecto está planteado como está, puede leer solo esos párrafos. Quien
necesite verificar una cita, encontrará debajo la entrada completa.

Las secciones siguen el orden del argumento del proyecto: primero los datos y los intentos
anteriores de detectar decisiones en reuniones (sección 1); después la técnica de la que el
proyecto parte y quiere superar, la recuperación aumentada (sección 2); luego lo que se
sabe sobre extraer información con modelos de lenguaje y sobre los errores que eso
introduce (sección 3); cómo se evalúa si una respuesta es correcta y tiene fuente (sección
4); cómo se representa que el conocimiento cambia con el tiempo (sección 5); qué entiende
la literatura de gestión por memoria organizacional (sección 6); y, por último, los marcos
para registrar de dónde viene cada dato y para gestionar riesgos (sección 7).

## Nota de estilo y verificación

Formato **APA 7ª edición**, un único estilo en todo el documento. Las 49 entradas provienen
de [`../../bibliography/refs.bib`](../../bibliography/refs.bib), que a su vez transcribe la
bibliografía verificada de la propuesta (§8). **Todas fueron contrastadas contra fuente
primaria** (ACL Anthology, Crossref, DOI del editor, w3.org, nist.gov) antes de incorporarse
al proyecto. Los **preprints sin revisión por pares** se marcan explícitamente con
`[Preprint, sin revisión por pares]` en cada entrada — no se citan como si fueran artículos
revisados.

## Fuente de datos pública

El curso exige que, si la fuente de datos es pública, figure en la bibliografía —no basta
mencionarla en el texto ni en una nota al pie. El corpus AMI se cita dos veces con roles
distintos: el artículo de referencia (ya en la sección 1) y, por separado, la **página de
licencia vigente**, que es la autoridad real de los términos de uso (documento 02,
§1).

Carletta, J., Ashby, S., Bourban, S., Flynn, M., Guillemot, M., Hain, T., Kadlec, J.,
Karaiskos, V., Kraaij, W., Kronenthal, M., Lathoud, G., Lincoln, M., Lisowska, A., McCowan,
I., Post, W., Reidsma, D., & Wellner, P. (2006). The AMI Meeting Corpus: A pre-announcement.
En *Machine Learning for Multimodal Interaction (MLMI 2005)* (Lecture Notes in Computer
Science, vol. 3869, pp. 28–39). Springer. https://doi.org/10.1007/11677482_3

AMI Meeting Corpus. (s.f.). *Licence* [Página web]. University of Edinburgh.
Recuperado el 20 de septiembre de 2026, de
https://groups.inf.ed.ac.uk/ami/corpus/license.shtml — **fuente de datos pública**;
CC BY 4.0. Sustituye el régimen descrito en Carletta et al. (2006) y Carletta (2007).

> **Precisión sobre la fecha.** Verificamos la página el 20-09-2026: declara
> "Creative Commons Attribution 4.0 International Public License (CC BY 4.0)" pero **no
> declara fecha de vigencia**. La fecha de abril de 2017 que circula —y que usamos en
> la propuesta— proviene de la fecha del paquete `ami_public_manual_1.6.2.zip`
> (10-04-2017), no de la página de licencia. Usamos `s.f.` en la cita y no afirmamos la fecha,
> porque este documento sostiene precisamente que hay que citar la licencia vigente y no
> los artículos; afirmar una fecha no verificada sería el mismo error en otra dirección.

## 1. Corpus y detección de decisiones en reuniones

*Para qué sirve este grupo.* Aquí están los datos y quienes ya intentaron lo mismo. Las
entradas de Carletta y Renals describen el corpus AMI: cómo se grabaron las reuniones y qué
marcas se agregaron a mano. Hsueh y Moore, Fernández et al. y Bui et al. son los equipos que
intentaron detectar decisiones automáticamente sobre ese corpus hace más de quince años; el
documento 01 cuenta que dos de ellos, trabajando sobre las mismas reuniones, no se pusieron
de acuerdo en qué era una decisión. Murray et al. es el antecedente más cercano: pusieron a
personas a reconstruir la historia de una decisión leyendo una serie completa de reuniones,
y demostraron que la tarea es real y difícil, aunque no dejaron datos reutilizables. QMSum y
el survey de Rennard et al. muestran dónde está hoy el resumen automático de reuniones, que
es la alternativa más común a lo que este proyecto propone.

Carletta, J. (2007). Unleashing the killer corpus: Experiences in creating the
multi-everything AMI Meeting Corpus. *Language Resources and Evaluation*, *41*(2), 181–190.
https://doi.org/10.1007/s10579-007-9040-x

Renals, S., Hain, T., & Bourlard, H. (2007). Recognition and understanding of meetings: The
AMI and AMIDA projects. En *2007 IEEE Workshop on Automatic Speech Recognition and
Understanding (ASRU)*. IEEE.

Hsueh, P.-Y., & Moore, J. D. (2007a). What decisions have you made? Automatic decision
detection in meeting conversations. En *Proceedings of NAACL-HLT 2007* (pp. 25–32).
Association for Computational Linguistics. (ACL Anthology N07-1004)

Hsueh, P.-Y., & Moore, J. D. (2007b). Automatic decision detection in meeting speech. En
*Machine Learning for Multimodal Interaction (MLMI 2007)* (Lecture Notes in Computer
Science, vol. 4892, pp. 168–179). Springer. https://doi.org/10.1007/978-3-540-78155-4_15
— nota: Springer fecha el volumen en 2008; es un artículo distinto del anterior, no un
duplicado.

Fernández, R., Frampton, M., Ehlen, P., Purver, M., & Peters, S. (2008). Modelling and
detecting decisions in multi-party dialogue. En *Proceedings of the 9th SIGdial Workshop on
Discourse and Dialogue* (pp. 156–163). Association for Computational Linguistics. (ACL
Anthology W08-0125)

Bui, T. H., Frampton, M., Dowding, J., & Peters, S. (2009). Extracting decisions from
multi-party dialogue using directed graphical models and semantic similarity. En
*Proceedings of SIGDIAL 2009* (pp. 235–243). Association for Computational Linguistics. (ACL
Anthology W09-3934)

Murray, G., Kleinbauer, T., Poller, P., Becker, T., Renals, S., & Kilgour, J. (2009).
Extrinsic summarization evaluation: A decision audit task. *ACM Transactions on Speech and
Language Processing*, *6*(2).

Zhong, M., Yin, D., Yu, T., Zaidi, A., Mutuma, M., Jha, R., Hassan Awadallah, A., Celikyilmaz,
A., Liu, Y., Qiu, X., & Radev, D. (2021). QMSum: A new benchmark for query-based
multi-domain meeting summarization. En *Proceedings of NAACL-HLT 2021* (pp. 5905–5921).
Association for Computational Linguistics. https://doi.org/10.18653/v1/2021.naacl-main.472

Rennard, V., Shang, G., Hunter, J., & Vazirgiannis, M. (2023). Abstractive meeting
summarization: A survey. *Transactions of the Association for Computational Linguistics*,
*11*, 861–884. https://doi.org/10.1162/tacl_a_00578

## 2. Recuperación aumentada y estructuración

*Para qué sirve este grupo.* La recuperación aumentada, RAG, es la técnica que busca en los
documentos los fragmentos parecidos a una pregunta y redacta una respuesta con ellos; es la
condición C1 del experimento, la práctica actual contra la que se compara todo. Lewis et
al. la definen. GraphRAG y LightRAG son la familia de soluciones más cercana a la propuesta:
construir primero un índice estructurado y consultar después; el documento 01 explica que
sus evaluaciones comparan sistemas completos y no permiten saber cuánto aporta la
estructura por sí sola. RAGAs y ARES son marcos para evaluar sistemas RAG; definen métricas
del mismo tipo que las que el documento 03 usa en OE3, como si la respuesta se apoya en los
fragmentos recuperados.

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis,
M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation
for knowledge-intensive NLP tasks. En *Advances in Neural Information Processing Systems 33*
(pp. 9459–9474). (arXiv:2005.11401)

Edge, D., Trinh, H., Cheng, N., Bradley, J., Chao, A., Mody, A., Truitt, S., Metropolitansky,
D., Ness, R. O., & Larson, J. (2024). *From local to global: A graph RAG approach to
query-focused summarization* (arXiv:2404.16130) [Preprint, sin revisión por pares].
https://doi.org/10.48550/arXiv.2404.16130

Guo, Z., Xia, L., Yu, Y., Ao, T., & Huang, C. (2025). LightRAG: Simple and fast
retrieval-augmented generation. En *Findings of the Association for Computational
Linguistics: EMNLP 2025* (pp. 10746–10761). Association for Computational Linguistics.
https://doi.org/10.18653/v1/2025.findings-emnlp.568

Es, S., James, J., Espinosa Anke, L., & Schockaert, S. (2024). RAGAs: Automated evaluation of
retrieval augmented generation. En *Proceedings of the 18th Conference of the European
Chapter of the Association for Computational Linguistics: System Demonstrations* (pp.
150–158). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.eacl-demo.16

Saad-Falcon, J., Khattab, O., Potts, C., & Zaharia, M. (2024). ARES: An automated evaluation
framework for retrieval-augmented generation systems. En *Proceedings of NAACL-HLT 2024*
(pp. 338–354). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.naacl-long.20

## 3. Extracción de información y construcción de bases de conocimiento con LLM

*Para qué sirve este grupo.* La condición C2 se construye con un modelo de lenguaje que lee
transcripciones y escribe una base de decisiones. Este grupo reúne lo que se sabe sobre esa
operación: qué tan bien extraen información estructurada los modelos (Dagdelen, Wadhwa, Xu),
cómo se construyen grafos de conocimiento con ellos y cómo se mide el resultado
(Text2KGBench, Zhu et al.), y, sobre todo, qué pasa con los errores. Jarnac et al. revisan
cómo manejar la incertidumbre de lo extraído; Cai y O'Connor muestran que un error de
extracción se propaga a todo lo que se calcula después sobre el grafo; y ConsistencyGate
nombra el mismo modo de falla que este proyecto mide en OE4: la memoria que se contamina
con lo que la máquina anotó mal.

Dagdelen, J., Dunn, A., Lee, S., Walker, N., Rosen, A. S., Ceder, G., Persson, K. A., & Jain,
A. (2024). Structured information extraction from scientific text with large language
models. *Nature Communications*, *15*, Artículo 1418. https://doi.org/10.1038/s41467-024-45563-x

Wadhwa, S., Amir, S., & Wallace, B. (2023). Revisiting relation extraction in the era of
large language models. En *Proceedings of the 61st Annual Meeting of the Association for
Computational Linguistics (ACL 2023)* (pp. 15566–15589). Association for Computational
Linguistics. https://doi.org/10.18653/v1/2023.acl-long.868

Xu, D., Chen, W., Peng, W., Zhang, C., Xu, T., Zhao, X., Wu, X., Zheng, Y., Wang, Y., & Chen,
E. (2024). Large language models for generative information extraction: A survey. *Frontiers
of Computer Science*, *18*(6), Artículo 186357. https://doi.org/10.1007/s11704-024-40555-y

Mihindukulasooriya, N., Tiwari, S., Enguix, C. F., & Lata, K. (2023). Text2KGBench: A
benchmark for ontology-driven knowledge graph generation from text. En *Proceedings of the
22nd International Semantic Web Conference (ISWC 2023)* (Lecture Notes in Computer Science,
pp. 247–265). Springer. https://doi.org/10.1007/978-3-031-47243-5_14

Zhu, Y., Wang, X., Chen, J., Qiao, S., Ou, Y., Yao, Y., Deng, S., Chen, H., & Zhang, N.
(2024). LLMs for knowledge graph construction and reasoning: Recent capabilities and future
opportunities. *World Wide Web*, *27*(5), Artículo 58. https://doi.org/10.1007/s11280-024-01297-w

Jarnac, L., Chabot, Y., & Couceiro, M. (2025). Uncertainty management in the construction of
knowledge graphs: A survey. *Transactions on Graph Data and Knowledge*, *3*(1), 3:1–3:48.
https://doi.org/10.4230/TGDK.3.1.3

Cai, E., & O'Connor, B. (2025). *Understanding the effect of knowledge graph extraction error
on downstream graph analyses: A case study on affiliation graphs* (arXiv:2506.12367)
[Preprint, sin revisión por pares]. https://doi.org/10.48550/arXiv.2506.12367

Zhang, Y., & Li, S. (2026). *ConsistencyGate: Preventing memory contamination in LLM agents
via self-consistency admission control* (arXiv:2607.22962) [Preprint, sin revisión por
pares]. https://doi.org/10.48550/arXiv.2607.22962 — nombra el mismo modo de falla
("contaminación de memoria") que este proyecto mide vía OE4. Leído el 2026-10-07: no acota la
afirmación de novedad, porque resuelve la admisión de hechos aislados en conversaciones de
chat y no el enlace entre decisiones de reuniones distintas (`propuesta.md` §9; documento 01,
§4). Se cita como trabajo relacionado.

## 4. Alucinación, atribución y evaluación

*Para qué sirve este grupo.* Para medir si una respuesta es correcta y tiene fuente hace
falta vocabulario y método. "Alucinación" es el nombre que recibe una respuesta que suena
plausible pero no está respaldada por los datos; Ji et al. y Huang et al. la clasifican, y de
Ji et al. se toma la distinción entre inventar algo que contradice la fuente y agregar algo
que la fuente no dice. "Atribución" es que la respuesta señale el pasaje que la respalda;
Rashkin et al. y Bohnet et al. definen cómo medirla, y es la base de la regla del documento
05 según la cual una respuesta sin fuente cuenta como falla. Las tres últimas entradas
tratan sobre usar un modelo de lenguaje como juez de otro (la técnica llamada LLM-as-a-judge): Zheng et al. muestran que puede
funcionar, y Wang et al. y Panickssery et al. muestran sus sesgos, en particular que un
modelo tiende a favorecer sus propias respuestas. Por eso el LLM-as-a-judge del proyecto pertenece a
otra familia de modelos y se valida con personas.

Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., Bang, Y., Madotto, A., &
Fung, P. (2023). Survey of hallucination in natural language generation. *ACM Computing
Surveys*, *55*(12), Artículo 248. https://doi.org/10.1145/3571730 — fuente de la distinción
intrínseca/extrínseca usada en este proyecto.

Huang, L., Yu, W., Ma, W., Zhong, W., Feng, Z., Wang, H., Chen, Q., Peng, W., Feng, X., Qin,
B., & Liu, T. (2025). A survey on hallucination in large language models: Principles,
taxonomy, challenges, and open questions. *ACM Transactions on Information Systems*,
*43*(2), Artículo 42. https://doi.org/10.1145/3703155

Rashkin, H., Nikolaev, V., Lamm, M., Aroyo, L., Collins, M., Das, D., Petrov, S., Tomar, G.
S., Turc, I., & Reitter, D. (2023). Measuring attribution in natural language generation
models. *Computational Linguistics*, *49*(4), 777–840. https://doi.org/10.1162/coli_a_00486

Bohnet, B., Tran, V. Q., Verga, P., Aharoni, R., Andor, D., Baldini Soares, L., Ciaramita,
M., Eisenstein, J., Ganchev, K., Herzig, J., Hui, K., Kwiatkowski, T., Ma, J., Ni, J.,
Sestorain Saralegui, L., Schuster, T., Cohen, W. W., Collins, M., Das, D., ... Webster, K.
(2022). *Attributed question answering: Evaluation and modeling for attributed large
language models* (arXiv:2212.08037) [Preprint, sin revisión por pares].
https://doi.org/10.48550/arXiv.2212.08037

Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D.,
Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023). Judging LLM-as-a-judge with
MT-Bench and Chatbot Arena. En *Advances in Neural Information Processing Systems 36
(NeurIPS 2023), Datasets and Benchmarks Track* (pp. 46595–46623).

Wang, P., Li, L., Chen, L., Cai, Z., Zhu, D., Lin, B., Cao, Y., Liu, Q., Liu, T., & Sui, Z.
(2024). Large language models are not fair evaluators. En *Proceedings of the 62nd Annual
Meeting of the Association for Computational Linguistics (ACL 2024)* (pp. 9440–9450).
Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.acl-long.511

Panickssery, A., Bowman, S. R., & Feng, S. (2024). LLM evaluators recognize and favor their
own generations. En *Advances in Neural Information Processing Systems 37 (NeurIPS 2024)*
(pp. 68772–68802).

## 5. Temporalidad del conocimiento

*Para qué sirve este grupo.* El centro del proyecto es que una decisión cambia con el
tiempo, y un sistema tiene que saber cuál versión está vigente. Las primeras cinco entradas
(StreamingQA, FreshLLMs, RealTime QA, Chen et al., Dhingra et al.) estudian cómo los
modelos de lenguaje responden preguntas cuya respuesta cambia según la fecha, y qué ocurre
cuando la información con que cuentan quedó atrás; la hipótesis H4 del documento 03 se
apoya en esa literatura. Cai et al. revisan los grafos de conocimiento temporales, donde cada
hecho lleva su intervalo de validez. Kulkarni y Michels aportan la distinción, tomada de las
bases de datos, entre el tiempo en que algo fue cierto y el tiempo en que se registró; el
proyecto la usa para representar que una decisión se tomó en una reunión y se revirtió en
otra.

Liska, A., Kocisky, T., Gribovskaya, E., Terzi, T., Sezener, E., Agrawal, D., de Masson
d'Autume, C., Scholtes, T., Zaheer, M., Young, S., Molloy, R., Lazaridou, A., & Blunsom, P.
(2022). StreamingQA: A benchmark for adaptation to new knowledge over time in question
answering models. En *Proceedings of the 39th International Conference on Machine Learning
(ICML 2022)* (PMLR, vol. 162, pp. 13604–13622).

Vu, T., Iyyer, M., Wang, X., Constant, N., Wei, J., Wei, J., Tar, C., Sung, Y.-H., Zhou, D.,
Le, Q., & Luong, T. (2024). FreshLLMs: Refreshing large language models with search engine
augmentation. En *Findings of the Association for Computational Linguistics: ACL 2024*
(pp. 13697–13720). Association for Computational Linguistics.
https://doi.org/10.18653/v1/2024.findings-acl.813

Kasai, J., Sakaguchi, K., Le Bras, R., Asai, A., Yu, X., Radev, D., Smith, N. A., Choi, Y., &
Inui, K. (2023). RealTime QA: What's the answer right now? En *Advances in Neural
Information Processing Systems 36 (NeurIPS 2023), Datasets and Benchmarks Track* (pp.
49025–49043).

Chen, W., Wang, X., & Wang, W. Y. (2021). A dataset for answering time-sensitive questions.
En *Advances in Neural Information Processing Systems 34 (NeurIPS 2021), Datasets and
Benchmarks Track*. (arXiv:2108.06314)

Dhingra, B., Cole, J. R., Eisenschlos, J. M., Gillick, D., Eisenstein, J., & Cohen, W. W.
(2022). Time-aware language models as temporal knowledge bases. *Transactions of the
Association for Computational Linguistics*, *10*, 257–273. https://doi.org/10.1162/tacl_a_00459

Cai, B., Xiang, Y., Gao, L., Zhang, H., Li, Y., & Li, J. (2023). Temporal knowledge graph
completion: A survey. En *Proceedings of the 32nd International Joint Conference on
Artificial Intelligence (IJCAI-23), Survey Track* (pp. 6545–6553). https://doi.org/10.24963/ijcai.2023/734

Kulkarni, K., & Michels, J.-E. (2012). Temporal features in SQL:2011. *ACM SIGMOD Record*,
*41*(3), 34–43. https://doi.org/10.1145/2380776.2380786 — define tiempo de validez frente a
tiempo de transacción, usado aquí para el modelo de relación temporal.

## 6. Memoria organizacional y racionalidad de diseño

*Para qué sirve este grupo.* El problema que el proyecto aborda no es nuevo: la gestión
lleva décadas preguntándose cómo una organización recuerda lo que decidió y por qué. Walsh y
Ungson, Stein, y Klammer y Gueldenberg son la literatura de memoria organizacional, incluido
cómo se olvida. Las entradas de racionalidad de diseño (Kunz y Rittel, Buckingham Shum y
Hammond, Grudin) son los intentos, desde los años setenta, de registrar las decisiones de
diseño con sus alternativas y argumentos; su pregunta central, visible en el título de
Buckingham Shum y Hammond, es cuánto cuesta registrar y cuánto se gana con ello, y es la
misma pregunta que lleva a este proyecto a intentar extraer las decisiones de las
transcripciones en lugar de pedir que alguien las escriba. Zhou et al. es el intento más reciente de hacerlo con
modelos de lenguaje.

Walsh, J. P., & Ungson, G. R. (1991). Organizational memory. *Academy of Management Review*,
*16*(1), 57–91. https://doi.org/10.5465/amr.1991.4278992

Stein, E. W. (1995). Organization memory: Review of concepts and recommendations for
management. *International Journal of Information Management*, *15*(1), 17–32.
https://doi.org/10.1016/0268-4012(94)00003-C

Klammer, A., & Gueldenberg, S. (2019). Unlearning and forgetting in organizations: A
systematic review of literature. *Journal of Knowledge Management*, *23*(5), 860–888.
https://doi.org/10.1108/JKM-05-2018-0277

Kunz, W., & Rittel, H. W. J. (1970). *Issues as elements of information systems* (Working
Paper No. 131). Institute of Urban and Regional Development, University of California,
Berkeley. — fuente primaria de IBIS (Issue-Based Information System).

Buckingham Shum, S. J., & Hammond, N. (1994). Argumentation-based design rationale: What use
at what cost? *International Journal of Human-Computer Studies*, *40*(4), 603–652.
https://doi.org/10.1006/ijhc.1994.1029

Grudin, J. (1996). Evaluating opportunities for design capture. En T. P. Moran & J. M.
Carroll (Eds.), *Design rationale: Concepts, techniques, and use* (cap. 21). Lawrence
Erlbaum.

Zhou, X., Li, R., Liang, P., Zhang, B., Shahin, M., Li, Z., & Yang, C. (2026). Using LLMs in
generating design rationale for software architecture decisions. *ACM Transactions on
Software Engineering and Methodology*, *35*(8), 1–38. https://doi.org/10.1145/3785010

## 7. Procedencia y marcos de riesgo

*Para qué sirve este grupo.* Procedencia es el registro de dónde viene cada dato: de qué
reunión, de qué pasaje, por qué proceso. PROV-O es el estándar del W3C para expresarlo, y
Singh et al. proponen aplicar la misma idea a las decisiones que toman sistemas
automatizados, para poder rendir cuentas de ellas. El marco de riesgos del NIST es el que
el documento 05 usa para organizar los aspectos éticos. La especificación OKF describe el
formato en que el instrumento OpenKOS guarda la base de decisiones de C2; se cita como
borrador porque lo es.

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV ontology* (W3C
Recommendation, 30 de abril de 2013). World Wide Web Consortium.

Singh, J., Cobbe, J., & Norval, C. (2019). Decision provenance: Harnessing data flow for
accountable systems. *IEEE Access*, *7*, 6562–6574. https://doi.org/10.1109/ACCESS.2018.2887201

Tabassi, E. (2023). *Artificial intelligence risk management framework (AI RMF 1.0)* (NIST AI
100-1). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.AI.100-1
— NIST indica que este marco está en revisión.

Google Cloud. (2026). *Open Knowledge Format (OKF): Especificación v0.1* [Borrador]. Formato
de la representación persistente usada por el instrumento OpenKOS (documento 06, §5–6).
Documento borrador sin DOI ni versión estable publicada; se cita como tal.

## Trabajos relacionados y su vínculo con el proyecto

Las secciones anteriores ordenan las fuentes por tema. Esta sección hace otra cosa: toma cuatro
grupos de trabajos de la lista, los más cercanos a lo que el proyecto hace, y para cada uno
dice qué hace, qué toma de él el proyecto y qué vacío aborda el proyecto frente a él. Lo que
se afirma de cada trabajo es lo que ya consta en esta bibliografía y en los documentos
[01](01-jss-problema.md) y [09](09-jss-modelos-y-justificacion.md); no se agregan referencias.

### Estructura frente a búsqueda directa: Edge et al. (2024), GraphRAG

*Qué hace.* Propone construir primero un índice estructurado a partir de los documentos y
consultar después ese índice, en lugar de buscar fragmentos en el texto original (sección 2;
documento 01, §2). Es la familia de soluciones más cercana a la propuesta del proyecto.

*Qué toma el proyecto.* La idea de que consultar algo construido a partir de los documentos
puede responder lo que la búsqueda de fragmentos no alcanza. En el proyecto, esa idea es la
condición C2 (documento 03, OE3).

*Qué vacío aborda.* La evidencia disponible compara sistemas completos entre sí: si el sistema
con índice responde mejor, no se sabe cuánto de la mejora viene de tener el índice y cuánto
del modelo que lo construyó (documento 01, §2). El proyecto complementa ese trabajo con la
condición C3, la misma base construida desde la anotación humana: la distancia entre C1 y C3
mide el valor de la estructura, y la distancia entre C3 y C2 mide el costo de construirla con
una máquina que se equivoca. GraphRAG es además un preprint sin revisión por pares, por lo que
se lo usa como antecedente y no como evidencia concluyente.

### Detección de decisiones en AMI: Hsueh y Moore (2007a) y Fernández et al. (2008)

*Qué hacen.* Ambos equipos intentaron detectar automáticamente las decisiones en las reuniones
del corpus AMI, el mismo que usa este proyecto. Hsueh y Moore marcaron como relacionado con
decisiones apenas el 1,4 % de los actos de diálogo; Fernández et al. hicieron lo mismo sobre
las mismas reuniones con un criterio propio. Al comparar ambos resultados, el acuerdo fue peor
que el azar (kappa negativo, 12,22 % de solapamiento) (documento 01, §3).

*Qué toma el proyecto.* La conclusión de que una etiqueta no puede darse por buena solo porque
la escribió una persona. De ahí que el proyecto mida el acuerdo entre anotadores en lugar de
suponerlo (kappa por existencia, tipo y dirección, documento 03, OE1) y exija evidencia en cada
decisión.

*Qué vacío aborda.* Esos trabajos se ocupan de reconocer decisiones, no de seguirlas de una
reunión a otra. La capa del corpus pensada para enlazar decisiones no distribuye datos
(documento 02, §5). El proyecto aporta la anotación que falta, el enlace tipado entre
reuniones sucesivas, con evidencia obligatoria y confiabilidad medida.

### Seguimiento de una decisión a lo largo de reuniones: Murray et al. (2009), auditoría de decisiones

*Qué hace.* Es el antecedente más cercano: pusieron a personas a reconstruir la historia de
una decisión leyendo una serie completa de reuniones, y demostraron que la tarea es real y
difícil (sección 1).

*Qué toma el proyecto.* La confirmación de que la unidad natural es la serie completa y de
que reconstruir la historia de una decisión exige leer varias reuniones. Por eso el proyecto
elige y anota series completas (documento 02, §2).

*Qué vacío aborda.* El trabajo no dejó datos reutilizables. El proyecto construye un conjunto
de referencia reutilizable y, sobre él, mide si una máquina puede hacer ese seguimiento y a
qué costo, algo que una auditoría hecha por personas no responde.

### LLM-as-a-judge: Zheng et al. (2023), con Wang et al. (2024) y Panickssery et al. (2024)

*Qué hacen.* Zheng et al. muestran que un modelo de lenguaje puede calificar las respuestas de
otro de manera útil. Wang et al. y Panickssery et al. muestran sus sesgos; en particular, que
un modelo tiende a favorecer sus propias respuestas (sección 4).

*Qué toma el proyecto.* Ambas lecciones. Califica las unas 900 respuestas del Experimento B un
LLM-as-a-judge (`gpt-oss:20b`), de una familia de modelos distinta de la del modelo que
extrae, y una persona verifica al menos el 20 % de sus veredictos (documento 09, §4).

*Qué vacío aborda.* Ningún banco público mide la tarea de calificar respuestas sobre
decisiones de reuniones (documento 09, §4), así que el proyecto calibra su propio LLM-as-a-judge con 42
respuestas etiquetadas a mano, con seis requisitos fijados antes de ver resultados (kappa
0,951), y declara la limitación de esa calibración (documento 09, §4).

---

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| Las 49 entradas y su organización temática (secciones 1 a 7) | [`../../bibliography/refs.bib`](../../bibliography/refs.bib) |
| Verificación contra fuente primaria | [`../../bibliography/refs.bib`](../../bibliography/refs.bib), cabecera del archivo |
| Preprints marcados: Edge et al. 2024, Cai & O'Connor 2025, Zhang & Li 2026, Bohnet et al. 2022 | [`../../bibliography/refs.bib`](../../bibliography/refs.bib), campo `keywords` |
| Página de licencia AMI como fuente de datos pública | [`../../config/corpus.toml`](../../config/corpus.toml) |
| Sección «Trabajos relacionados»: cifras de Hsueh y Moore / Fernández et al. y del LLM-as-a-judge | [`01-jss-problema.md`](01-jss-problema.md) §2–3; [`09-jss-modelos-y-justificacion.md`](09-jss-modelos-y-justificacion.md) §4 |
