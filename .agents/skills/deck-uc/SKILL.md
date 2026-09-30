---
name: deck-uc
description: "Sistema UC multimodal para crear y mejorar presentaciones PowerPoint, presentaciones audiovisuales/reels y documentos Word/informes/tesis. Storytelling primero, diseño editorial premium, identidad UC oficial obligatoria, guion detallado y auditoría correctiva antes de entregar."
---

# deck-uc

Skill portable para producir piezas UC profesionales en tres modos: **PRESENTACIÓN**, **VIDEO/REEL** y **WORD/INFORME/TESIS**. Comparte un único motor de narrativa, rigor, identidad UC, dirección de arte y auditoría; cada modo especializa la salida.

## 0. Selección de modo
Detectar el entregable solicitado:
- `PRESENTATION`: PowerPoint para exposición.
- `VIDEO_REEL`: PowerPoint/guion audiovisual para video, reel o cápsula narrada.
- `WORD`: informe, tesis, memoria, propuesta o documento académico/institucional.

Si el usuario pide más de un formato, construir una fuente narrativa común y adaptar cada salida; no copiar mecánicamente el mismo layout entre formatos.

## 1. Recursos obligatorios
Leer sólo los necesarios, pero respetar su jerarquía:
- `references/storytelling.md` — narrativa.
- `references/brand-uc.md` — reglas de marca comunes.
- `assets/manual-marca-uc.pdf` — autoridad normativa de marca.
- `references/premium-art-direction.md` + `references/visual-design.md` — estándar gráfico.
- `references/template-uc.md`, `references/norma-visual-uc.md`, `references/caracterizacion.md` — PowerPoint UC.
- `references/video-reel.md` — audiovisual.
- `references/word-editorial.md` — Word/tesis.

Assets:
> Los assets no están versionados (material institucional UC en un repositorio público). Se instalan con `make skill-assets`, que los copia desde la carpeta compartida del equipo y verifica su SHA-256 (`assets.sha256`). Si falta alguno de los archivos listados abajo, detenerse y pedir a la persona que ejecute `make skill-assets`; no improvisar sin el asset.

- `assets/template-uc.pptx` — template PowerPoint UC obligatorio.
- `assets/reference-premium-design.pptx` — benchmark de sofisticación visual, nunca fuente de contenido.
- `assets/reference-video-reel.pptx` — benchmark funcional audiovisual.
- `assets/word-uc-corporativa.docx` — master Word institucional principal.
- `assets/word-uc-unidad.docx` — variante por unidad.
- `assets/word-uc-sin-texto.docx` — recurso auxiliar.

## 2. Principio rector
**Historia primero -> relación visual después -> diseño -> auditoría correctiva -> entrega.**

Nunca comenzar eligiendo layouts, cards, SmartArt o una estética.

Flujo base:
**fuentes -> audiencia -> objetivo -> Big Idea -> arquitectura narrativa -> SCR/Dot-Dash -> action titles -> storyboard -> guion -> relación conceptual -> tesis visual -> arquetipo -> composición -> producción -> auditoría -> corrección -> reauditoría -> APPROVED**.

## 3. Rigor de contenido
- No inventar cifras, fuentes, evidencia, requisitos académicos ni conclusiones.
- Distinguir hechos, inferencias, hipótesis y recomendaciones.
- Mantener trazabilidad de fuentes.
- No crear gráficos cuantitativos sin datos.
- En tesis/informes, no inventar normas de facultad/programa.
- En audiovisual, distinguir demo, ejemplo, evidencia y resultado.

## 4. Storytelling obligatorio
Antes de diseñar:
1. audiencia y conocimiento;
2. objetivo: informar, alinear, explorar, activar, priorizar, decidir o escalar;
3. Big Idea única;
4. deductiva o inductiva;
5. SCR cuando haya tensión/cambio/problema;
6. Dot-Dash;
7. action titles/conclusiones;
8. storyboard;
9. validación: títulos/secciones leídos solos deben contar la historia;
10. guion antes del diseño final.

Una unidad visual = una idea principal.

## 5. Motor gráfico premium
Para cada slide/página/escena definir antes de dibujar:
- conclusión que debe quedar;
- relación entre ideas;
- tesis visual;
- orden de lectura;
- foco dominante;
- evidencia mínima;
- arquetipo/representación;
- rasgo que la diferencia de las dos anteriores.

Relaciones típicas: secuencia, causa-efecto, evolución, madurez, comparación, arquitectura, anatomía, ciclo, matriz, jerarquía, dependencia, decisión, métricas, tendencia, transformación, convergencia, tensión.

### Prohibiciones por defecto
No resolver automáticamente con:
- título + 3 cajas/cards;
- grillas 2xN de mini-cards;
- SmartArt-like;
- timelines de línea + puntos sin significado temporal;
- tablas disfrazadas de infografía;
- chevrons repetitivos;
- icon salad;
- rectángulos para agrupar todo;
- mismo skeleton repetido;
- decoración sin función.

### Dirección de arte
- composición editorial, asimetría controlada y whitespace;
- contraste de escala y jerarquía tipográfica;
- diagramas semánticos específicos para la idea;
- microdetalle preciso;
- color con función estable;
- un foco principal;
- legible en ~5 s y explorable en 30–60 s;
- alternar L1 editorial / L2 diagramática / L3 analítica según narrativa.

La referencia premium calibra calidad, **no reemplaza la identidad UC**.

## 6. Identidad UC
Aplicar `references/brand-uc.md` y el manual. En contexto chileno, usar marca madre nacional. Respetar lockup, proporciones, zona de seguridad, contraste y denominaciones. Nunca deformar, cortar, girar, usar como watermark ni superponer texto.

La UC debe sentirse por sistema, no por saturación de azul, marcos o logos.

## 7. Modo PRESENTATION
- Usar obligatoriamente `assets/template-uc.pptx` como base visual cuando se produzca PowerPoint.
- Conservar elementos institucionales que correspondan; no convertir el master en una jaula compositiva.
- Contenido 100% editable cuando la plataforma lo permita.
- No repetir el mismo arquetipo en slides consecutivas sin razón narrativa.
- En 8+ slides usar variedad semántica real de familias visuales cuando el contenido lo permita.
- Cada slide debe incluir Notas del presentador.

### Guion obligatorio por slide
- mensaje central;
- desarrollo oral;
- lectura del visual;
- evidencia/matiz;
- implicancia;
- transición.

El guion complementa; no lee la slide.

## 8. Modo VIDEO_REEL
Aplicar `references/video-reel.md` y usar `assets/reference-video-reel.pptx` como benchmark funcional.

Además del storytelling, definir por escena: locución, duración, timecode, visual, cue, animación/transición, formato y avance. Diseñar desde el formato final (9:16/1:1/16:9), con safe areas y sincronización voz-visual. La locución aprobada manda sobre offsets menores de timecode. No agregar animaciones decorativas.

## 9. Modo WORD
Aplicar `references/word-editorial.md`.

Base principal: `assets/word-uc-corporativa.docx`; usar variante de unidad cuando corresponda. El manual manda sobre cualquier interpretación.

No repetir el membrete completo como decoración en todas las páginas de una tesis. Separar capa institucional de capa editorial. Crear estilos Word semánticos, jerarquía H1/H2/H3, cuerpo, captions, tablas, figuras, TOC/navegación cuando corresponda, encabezados/pies, numeración, capítulos y anexos.

Si el usuario aporta una normativa de tesis de su programa, ésta prevalece para requisitos académicos compatibles con la marca.

## 10. Storyboard/plan enriquecido
Antes de producir, mantener internamente al menos:
```yaml
meta:
  mode: "PRESENTATION | VIDEO_REEL | WORD"
  audience: "..."
  objective: "..."
  big_idea: "..."
  narrative_mode: "deductive | inductive"
units:
  - title_or_section: "conclusión"
    role: "situation | conflict | resolution | argument | evidence | decision"
    evidence: ["..."]
    visual_intent:
      relationship: "..."
      thesis: "..."
      archetype: "..."
      reading_order: "..."
      emphasis: "..."
      uniqueness: "..."
    script:
      core_message: "..."
      talk_track: "..."
      visual_walkthrough: "..."
      evidence_or_caveat: "..."
      implication: "..."
      transition: "..."
```
Para VIDEO_REEL agregar `voiceover`, `timecode`, `cue`, `animation`, `format`. Para WORD agregar `style`, `section_break`, `caption/crossref` cuando aplique.

## 11. Auditoría final obligatoria — NO entregar la primera versión
La auditoría es correctiva, no declarativa:

**DISEÑAR -> RENDERIZAR/INSPECCIONAR -> AUDITAR -> CORREGIR -> REINSPECCIONAR -> VALIDAR -> ENTREGAR**.

### A. Auditoría global
Revisar miniaturas/páginas/escenas como sistema: narrativa, ritmo, variedad, densidad, marca, consistencia, slides/páginas débiles, repetición y cierre.

### B. Auditoría unidad por unidad
Revisar: mensaje, foco, tesis visual, jerarquía, edición, geometría, sofisticación, coherencia UC, legibilidad, fuentes y guion.

### C. Auditoría técnica
Detectar y corregir: clipping, overflow, solapes, fuentes sustituidas, conectores, saltos deficientes, objetos fuera del área segura, footers, numeración, contraste y resolución.

### D. Scorecard interno
Puntuar 0–2:
1. claridad;
2. tesis visual;
3. jerarquía;
4. síntesis;
5. sofisticación compositiva;
6. coherencia UC;
7. acabado técnico;
8. calidad del guion/soporte narrativo.

Ninguna dimensión puede quedar en 0. Umbral normal: **13/16**. Slides/páginas/escenas hero, resumen, argumento central y cierre: **14/16**. Si falla: `REVISE`, corregir y volver a auditar. Sólo entregar en `APPROVED`.

### E. Gate específico por modo
- PRESENTATION: inspeccionar deck completo y cada slide renderizada; verificar notas completas.
- VIDEO_REEL: verificar timing total, cues, sincronía, continuidad, safe areas y legibilidad al tamaño final.
- WORD: renderizar el DOCX y revisar **todas las páginas**; corregir márgenes, saltos, viudas/huérfanas, tablas, figuras, captions, TOC, headers/footers y páginas accidentales; re-renderizar tras cada corrección relevante.

## 12. Criterio de terminación
No afirmar que una pieza está lista sólo porque cabe o abre correctamente. Termina cuando:
- la historia se entiende;
- el visual comunica la relación correcta;
- el diseño se siente específico y premium, no genérico;
- la identidad UC es correcta;
- el guion/soporte narrativo está completo;
- la auditoría técnica y visual fue corregida;
- el estado final es `APPROVED`.
