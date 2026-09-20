# 0003. Usar OpenKOS como instrumento de extracción/persistencia, no como entregable del proyecto

## Estado

Aceptada

## Contexto

La sección 5.9 de la tesis traza una línea explícita entre el *instrumento* (OpenKOS:
ingesta, extracción tipada con procedencia, almacenamiento en Open Knowledge Format,
recuperación híbrida, verificación de suficiencia de contexto — preexistente, desarrollado
previamente por uno de los integrantes del equipo, Apache-2.0) y el *aporte de este trabajo* (el conjunto de referencia OE1 con enlaces
temporales, el diseño experimental de tres condiciones, el protocolo de alineación y la
medición de atribución de error).

Si esta distinción no se hace estructuralmente, es fácil que el código del arnés se
confunda con una reimplementación de partes de un motor de extracción/recuperación, lo que
duplicaría OpenKOS y enturbiaría la evaluación: el proyecto dejaría de medir con claridad
OpenKOS-como-instrumento frente a una línea base de RAG documental.

## Decisión

- `openkos` es una **dependencia opcional** (`uv sync --extra instrument`), nunca una
  dependencia requerida para que pasen los tests, el lint o el chequeo de tipos del arnés.
- Todo contacto con OpenKOS pasa por un único adaptador,
  `src/afg/extraction/openkos_adapter.py`, que implementa el protocolo genérico
  `src/afg/extraction/protocol.py::Extractor`. Ningún otro módulo importa `openkos`
  directamente.
- C2 (`src/afg/conditions/c2_compiled_auto.py`) depende de `Extractor` (el protocolo), no
  de `OpenKosAdapter` (la clase concreta) — de modo que un futuro motor alternativo podría
  sustituirse sin tocar la condición misma.

## Consecuencias

- La superficie evaluable de este proyecto es la medición, no el motor, en línea con el
  encuadre de la propia sección 5.9 de la tesis ("el aporte evaluable es la medición, no
  la construcción del motor").
- Intercambiar o simular el backend de extracción (por ejemplo, para un test unitario, o
  para una futura comparación de motores) solo requiere una nueva implementación de
  `Extractor`.

> **Riesgo registrado (2026-09-20).** El formato de persistencia de C2 y C3 es el Open
> Knowledge Format (OKF) v0.1, un borrador sin versión estable. Antes de compilar en AFG2 se
> fija la versión exacta de OpenKOS y de OKF en `config/experiments.toml`; si el formato cambia
> después, las bases compiladas no se migran: se recompilan con la versión fijada.
