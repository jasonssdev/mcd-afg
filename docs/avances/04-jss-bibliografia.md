# Bibliografía

| | |
|---|---|
| **Documento** | 04 — Bibliografía |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.1 |
| **Fecha** | 2026-09-20 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-09-20 | Versión inicial. Bibliografía APA 7 para AFG1. | Primera entrega del curso. |
| 1.1 | 2026-09-20 | Correcciones de autores, títulos y sufijos a/b; entrada de la licencia AMI en refs.bib. | Verificación contra la API de arXiv y DOI, 2026-09-20. |

> **Cómo versionar.** Un cambio de redacción sube el decimal (1.0 → 1.1). Un cambio que
> altera una decisión, un objetivo o una cifra sube el entero (1.x → 2.0) y **debe declarar
> la evidencia que lo motivó**. El historial nunca se reescribe: se agrega una fila.

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
distintos: el artículo de referencia (ya en la sección 8.1) y, por separado, la **página de
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
("contaminación de memoria") que este proyecto mide vía OE4; debe leerse antes de fijar la
afirmación de novedad final de la tesis (documento 01, §4).

## 4. Alucinación, atribución y evaluación

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

---

## Trazabilidad

| Afirmación | Dónde se verifica |
|---|---|
| Las 49 entradas y su organización temática (8.1–8.7) | [`../../bibliography/refs.bib`](../../bibliography/refs.bib) |
| Verificación contra fuente primaria | [`../../bibliography/refs.bib`](../../bibliography/refs.bib), cabecera del archivo |
| Preprints marcados: Edge et al. 2024, Cai & O'Connor 2025, Zhang & Li 2026, Bohnet et al. 2022 | [`../../bibliography/refs.bib`](../../bibliography/refs.bib), campo `keywords` |
| Página de licencia AMI como fuente de datos pública | [`../../config/corpus.toml`](../../config/corpus.toml) |
