# Caracterización · deckUC

## Propósito

**deckUC** es un motor para crear **piezas gráficas con la norma
gráfica y visual de la Pontificia Universidad Católica de Chile (PUC / UC)**:
presentaciones y láminas STILL con la marca UC (Poppins, Azul A `#0176DE` /
Azul B `#1A1E2B` / Amarillo `#FEC60D`, escudo institucional).

Motor **propio** (código original deckUC, no derivado de terceros); solo usa
`pptxgenjs` (MIT) para escribir el `.pptx`. Render local, sin red.

## Qué SÍ puede hacer

| Capacidad | Detalle |
|---|---|
| **Presentaciones (.pptx 16:9)** | Deck completo desde un plan JSON; 10 layouts. |
| **Láminas STILL** | Portada, separador, contenido, proceso, comparación, KPIs, tabla, figura, cita, cierre. |
| **Marca UC aplicada** | Paleta, Poppins y escudo por defecto; variante digital (Roboto) por entorno. |
| **Recursos UC incluidos** | Escudo (4 variantes) y fuentes bundleadas. |
| **Editable** | El `.pptx` es 100% editable en PowerPoint / Keynote / LibreOffice. |
| **Cero invención** | El contenido debe trazar a una fuente; vacíos se preguntan. |
| **Auto-QA visual** | Render + revisión lámina por lámina antes de declarar "listo". |

## Qué NO puede hacer (límites)

| Límite | Motivo |
|---|---|
| **No hace video** | Fuera de alcance: solo presentaciones + STILL. |
| **No hace web/UI/landing** | Fuera de alcance. |
| **No inventa contenido** | Regla de veracidad: cifras, resultados y citas vienen de tus fuentes. |
| **No garantiza CMYK/Pantone** | La norma impresa completa está en el manual UC (SharePoint, login). |
| **Necesita Node.js** | El motor corre sobre Node + pptxgenjs (incluido en `node_modules`). |
| **Fuentes en el sistema** | Para ver Poppins al abrir el `.pptx`, instálala con `install.sh`/`install.ps1`. |

## Uso rápido

```bash
node src/build.js --plan examples/ejemplo_plan.json --out examples/ejemplo.pptx
```

Basta con pedir, p. ej.: "haz una presentación UC para la defensa
de tesis con estas secciones ...". El agente arma el plan y construye el deck.
