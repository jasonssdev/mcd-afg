# `data/raw/`

Zona de aterrizaje para los datos del corpus descargados por `afg corpus download`. Nada
de lo que hay en este directorio (aparte de este archivo y los marcadores `.gitkeep`) se
versiona en git — ver el bloque específico del proyecto en `.gitignore`.

## Qué aterriza aquí

- `data/raw/ami/` — las anotaciones manuales del AMI Meeting Corpus, extraídas
  (`ami_public_manual_1.6.2.zip` desde
  `https://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/`), descomprimidas por
  `src/afg/corpus/download.py`.

## Procedencia y licencia

- **Fuente:** anotaciones del AMI Meeting Corpus, University of Edinburgh
  (`https://groups.inf.ed.ac.uk/ami/corpus/`).
- **Licencia:** CC BY 4.0, según la página de licencia. Esa página no declara una fecha de
  vigencia; el 10-04-2017 es solo la fecha de publicación del paquete
  `ami_public_manual_1.6.2.zip` en el archivo de descargas, no una fecha de entrada en
  vigor de la licencia. Cite la página de licencia, no los artículos originales del
  corpus, que describen una licencia anterior y más restrictiva (sección 5.0 de la tesis).
- **Requisito de atribución:** cualquier redistribución de material derivado debe atribuir
  al AMI Meeting Corpus según CC BY 4.0. Ver `bibliography/refs.bib` (`carletta2006ami`,
  `carletta2007killercorpus`) para las citas a usar.
- **Sin re-identificación:** los identificadores de participantes se usan tal como se
  publicaron, en su forma anonimizada. Este proyecto no intenta re-identificar
  participantes (sección 6.5 de la tesis).

Este directorio está deliberadamente vacío en un checkout nuevo. La descarga nunca es
automática: solo ocurre cuando una persona ejecuta `uv run afg corpus download` (ver la
sección "Paso cero" de README.md) para poblarlo.
