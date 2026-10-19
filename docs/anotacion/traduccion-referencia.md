# Traducción de la referencia al inglés

| | |
|---|---|
| **Documento** | Guía de traducción de la referencia |
| **Autor** | Jason Sepúlveda S. |
| **Versión** | 1.0 |
| **Fecha** | 2026-10-19 |
| **Estado** | Vigente |

## Historial de versiones

| Versión | Fecha | Cambio | Motivo |
|---|---|---|---|
| 1.0 | 2026-10-19 | Versión inicial: formato, comandos, reglas y qué hacer cuando cambia la adjudicación. | Issue #141: comparar las extracciones (en inglés) con una referencia en el mismo idioma. |

## Para qué sirve

Las transcripciones de AMI y lo que extrae la máquina están en inglés; las etiquetas humanas
de la referencia (`final_object`, `final_content`) están en español. Para comparar texto con
texto en el mismo idioma, cada serie adjudicada tiene una **traducción automática al inglés**
de esas dos columnas. Se aplica a las series ya adjudicadas (hoy ES2015 y TS3009); las
siguientes se traducen con este mismo método.

Dos reglas que no cambian:

- **La traducción no es una etiqueta.** No decide ningún estado ni relación y no cambia
  `final_status`. Las etiquetas humanas, en español, siguen siendo el ground truth
  ([`CONTRIBUTING.md`](../../CONTRIBUTING.md) §7.6).
- **Solo se traducen las decisiones de la referencia**: las filas cuyo `final_status` es
  `decision`, incluidas las hijas de una fila `compuesta` (las mismas que devuelve
  `load_reference`).

## El archivo

Uno por serie: `data/processed/decisions/<SERIE>.reference-en.csv`. Es un archivo aparte para
no tocar el CSV adjudicado, que `afg gold adjudicate --force` puede regenerar.

| Columna | Qué contiene |
|---|---|
| `decision_id` | Identificador de la decisión; exactamente una fila por decisión de la referencia |
| `final_object`, `final_content` | Copia del español adjudicado. No se edita: sirve para detectar traducciones desactualizadas |
| `object_en`, `content_en` | La traducción (obligatorias) |
| `translation_method` | Cómo se obtuvo la traducción. Hoy el único valor es `automatica` |
| `notes` | Opcional: una línea corta, en inglés, solo si una elección de traducción no era obvia |

El archivo se lee como UTF-8 (con o sin BOM) y se escribe como UTF-8 sin BOM.

## Pasos

```bash
uv run afg gold translation-template --series ES2015   # 1. crea la plantilla (español lleno, inglés vacío)
# 2. se llenan object_en y content_en de cada fila (reglas abajo)
uv run afg gold validate-translation --series ES2015   # 3. debe terminar sin errores
```

La plantilla no sobrescribe un archivo existente; `--force` la regenera desde cero y borra lo
traducido. La validación comprueba que:

1. cada decisión de la referencia tiene exactamente una fila, sin filas de más ni repetidas;
2. `object_en` y `content_en` no están vacíos;
3. la copia en español coincide con el adjudicado actual (si no, la fila está «desactualizada»);
4. `translation_method` es un valor permitido.

Para usar la referencia en inglés: `load_series_reference("ES2015", language="en")`. Con
`language="es"` (el valor por omisión) todo queda como antes. Con `"en"`, si el archivo falta,
está incompleto o desactualizado, la carga falla con el mensaje de la validación.

## Reglas de traducción

- Se traduce la **etiqueta en español** a un inglés natural: mismo significado, sin agregar ni
  quitar información.
- Los números, las unidades y las monedas conservan su valor y su forma («25 euros» sigue
  siendo «25 euros»), salvo el separador decimal, que pasa a la convención inglesa
  («12,50 euros» se escribe «12.50 euros»); los nombres propios no se cambian.
- «Control» o «mando», cuando nombran el aparato, se traducen como *remote* (o *remote
  control*), no como *control*, que en inglés no designa el aparato.
- `object_en`: sintagma nominal corto, como el objeto en español. `content_en`: la decisión
  como proposición, con la misma estructura que el español.
- Se puede leer `sentence_text` o `evidence_text` **solo para desambiguar** el significado. No
  se copia su redacción ni se parafrasea la transcripción: las extracciones citan la
  transcripción, y copiarla inflaría la similitud con ellas.
- No se consulta ninguna salida de extracción (`reports/experiment-a/`, corridas de OpenKOS):
  hacerlo sería fuga.
- Los errores de ortografía de la etiqueta no se arrastran: se traduce el sentido y, si la
  lectura no era obvia, se anota en `notes`.

## Si cambia una adjudicación

Si `final_object` o `final_content` cambian en el CSV adjudicado, `validate-translation`
marca esa fila como «desactualizada». Se corrige así: se actualiza `object_en`/`content_en`
según el español nuevo y se copia el español actual en `final_object`/`final_content` de esa
fila. Si cambió el conjunto de decisiones, la validación informa también las que faltan o
sobran. No hace falta regenerar la plantilla completa (`--force` borraría lo ya traducido).

## Limitación

La traducción es automática y no la revisa una persona fila por fila. Un error de traducción
actuaría como ruido en la referencia. La validación garantiza que la traducción esté completa y
vigente, no que sea perfecta; esta salvedad se declara en
[`../avances/06-jss-metodologia.md`](../avances/06-jss-metodologia.md) (§1) y en
[`../protocols/alignment.md`](../protocols/alignment.md).
