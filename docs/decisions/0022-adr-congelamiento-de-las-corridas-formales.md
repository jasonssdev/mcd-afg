# 0022. Se congela todo lo que usan las corridas formales sobre las series de evaluación

## Estado

**Reemplazada por el [ADR 0023](0023-adr-recongelamiento-tras-la-auditoria.md) (2026-11-05)**: una auditoría previa a la primera corrida encontró defectos en el código y huecos en el registro (transcripciones, `corpus.toml`, `annotation.toml`), y no existía ninguna corrida que invalidar. El texto que sigue se conserva como estaba cuando se aceptó.

Aceptada (2026-11-05), por decisión de `jss`. Resuelve el [issue #237](https://github.com/jasonssdev/mcd-afg/issues/237). Es el último paso antes de los experimentos: con este ADR fusionado y el registro escrito, las issues de las corridas formales (Experimento A, C3, Experimento B y análisis) pueden crearse. Aplica la regla del [ADR 0005](0005-adr-development-evaluation-split.md): nada se ajusta ya con las series de evaluación.

## Contexto

Las corridas formales sobre las once series de evaluación solo valen si lo que las alimenta no cambia entre la primera y la última. Las dependencias del issue están cerradas: la anotación de la fase 3, las traducciones, el banco de preguntas ([ADR 0021](0021-adr-minimo-de-e3-segun-relaciones-disponibles.md)), el recall del bloqueador ([ADR 0020](0020-adr-se-mantiene-el-bloqueador-lexico.md)) y el código de los experimentos, incluido el bloqueo atado al congelamiento (`afg freeze`, [protocolo](../protocols/congelamiento.md)).

## Decisión

Se congela lo siguiente, con la huella SHA-256 de cada archivo. Las huellas se calcularon con `afg freeze write --adr 0022` en modo de prueba, sobre la base de la rama de este ADR; el PR de este ADR cambia solo documentación, de modo que siguen vigentes tras la fusión.

### 1. Referencia (14 series)

Decisiones y relaciones de cada serie, tal como se resuelven (archivo adjudicado o, sin él, el de anotación individual), y su traducción al inglés.

| Serie | Archivo | Ruta | SHA-256 |
|---|---|---|---|
| ES2002 | Decisiones | `data/processed/decisions/ES2002.decisions.gv.csv` | `14fe72d98ce988697e0a7c25fdd0cce3ee405d6b60ed8ce842fb0e7a8bfcb5b1` |
| ES2002 | Relaciones | `data/processed/relations/ES2002.candidates.gv.csv` | `83b538254b87f74227c42a0935b7b19db1228509abf6aeec2c07c524137168ec` |
| ES2002 | Traducción al inglés | `data/processed/decisions/ES2002.reference-en.csv` | `933eaf4651f8271dcb47ba59bdc45e699ec720f2bad43dd4c814fa7346179a89` |
| ES2008 | Decisiones | `data/processed/decisions/ES2008.decisions.adjudicated.csv` | `de2dd1714cfb8fdf35961393d722a0b1d7cc0499d282662446c8eed92d12f6e3` |
| ES2008 | Relaciones | `data/processed/relations/ES2008.candidates.adjudicated.csv` | `cbe8289167b8b224bf721e5646f04f76478fb436e44e6246a4e558299dad92e5` |
| ES2008 | Traducción al inglés | `data/processed/decisions/ES2008.reference-en.csv` | `9ea384858df633f5cba764ec34b9058c00bf8fbaa21cfd083e853806e68f0b7e` |
| ES2014 | Decisiones | `data/processed/decisions/ES2014.decisions.gm.csv` | `fd96a28833eebbd7a49a6c35c564ce820ccb25ffd6ed278542df81f48e08a464` |
| ES2014 | Relaciones | `data/processed/relations/ES2014.candidates.gm.csv` | `f3e6bd00be363e847f07dd959eb32b72abdd8b47bc7a9dac7fc14439488ffe11` |
| ES2014 | Traducción al inglés | `data/processed/decisions/ES2014.reference-en.csv` | `cb5cc007c86c577c39af294ac948e1dc6ea9590fd8b563318f6a21a9e32b756a` |
| ES2015 | Decisiones | `data/processed/decisions/ES2015.decisions.adjudicated.csv` | `de3e6439e7e8fe79b623d1d58f72a009fb691ebe0ee96d01f1c105e18debad9c` |
| ES2015 | Relaciones | `data/processed/relations/ES2015.candidates.adjudicated.csv` | `bb734f45b444114ac16b9ae1b8bddd94e9c1fe9ce8099ff64b7659d294ce6f08` |
| ES2015 | Traducción al inglés | `data/processed/decisions/ES2015.reference-en.csv` | `0116bf904e8190f02a1c581b7cce1c69988ad29837ff99b811c5569fcdd60bc6` |
| ES2016 | Decisiones | `data/processed/decisions/ES2016.decisions.adjudicated.csv` | `d51299644dc8df741b04c2f1e207ae26710407bbd10c119210367ddb7eddb370` |
| ES2016 | Relaciones | `data/processed/relations/ES2016.candidates.adjudicated.csv` | `b30cdad015cbfd84b42c50eb6d192d004c430dbfd65813d392f799f943255800` |
| ES2016 | Traducción al inglés | `data/processed/decisions/ES2016.reference-en.csv` | `08b5e87cbe31bada389435edf51df338ceab8c85a1ef9b1182d2009ea51a0c8c` |
| IS1003 | Decisiones | `data/processed/decisions/IS1003.decisions.adjudicated.csv` | `c770be4d0a92fb16d3527e043b52b065714d52dd4eaa02a1ad8ee36750d9bc63` |
| IS1003 | Relaciones | `data/processed/relations/IS1003.candidates.adjudicated.csv` | `821cd7cd79162f8e16bf36c65e377153f9f687fffc346a6c15e9a1c795d95688` |
| IS1003 | Traducción al inglés | `data/processed/decisions/IS1003.reference-en.csv` | `249fcbe543610a91d0a7640cf238ab2896550637de4401d921967aec0680153c` |
| IS1004 | Decisiones | `data/processed/decisions/IS1004.decisions.gv.csv` | `e904d65f0a52df361f56cc11356ad8607cf4e5c82e455c99b2160f27e60def5f` |
| IS1004 | Relaciones | `data/processed/relations/IS1004.candidates.gv.csv` | `7d88cfecc52f0a33809fabfe4f61ec04c91190acbae0f018b2d3a33335f54e80` |
| IS1004 | Traducción al inglés | `data/processed/decisions/IS1004.reference-en.csv` | `d6a82f1635611de11db1ec29b14bf158f64a8635800ce8045050f2a7b79f1dda` |
| IS1006 | Decisiones | `data/processed/decisions/IS1006.decisions.gv.csv` | `2482a54e5de9f43a14c8d986da1b5492cca65d10de91a5dde659a6a9366fbff6` |
| IS1006 | Relaciones | `data/processed/relations/IS1006.candidates.gv.csv` | `83b7ac1b196b630a5b79913d928aa8ad155cc2bc5c4e3976ba6dd633b02ea074` |
| IS1006 | Traducción al inglés | `data/processed/decisions/IS1006.reference-en.csv` | `3b798cee348e52997193935c3d99e7406235302c0ffd48f8008227e306d0ea06` |
| IS1008 | Decisiones | `data/processed/decisions/IS1008.decisions.gm.csv` | `140a54c1a618dad1b7d2300af2ffe6c469399a65aa638d676402bbea0484e402` |
| IS1008 | Relaciones | `data/processed/relations/IS1008.candidates.gm.csv` | `fe1c046b821c7c5d49f3732ed65c4db7ff998fadd9fd0e4dfc8d895609c308f9` |
| IS1008 | Traducción al inglés | `data/processed/decisions/IS1008.reference-en.csv` | `003481dffa157af8e30785d8ded898cc084cc2e145740acbbf4ccb7cd5396cfa` |
| IS1009 | Decisiones | `data/processed/decisions/IS1009.decisions.gv.csv` | `02a73c3cd083590c986874a2d353a101572f442da9ce5f8c0438df84804fa9db` |
| IS1009 | Relaciones | `data/processed/relations/IS1009.candidates.gv.csv` | `b822601a8bf2d866566bdd6352fceca19dce4a0dcd670e869479641e2015fb41` |
| IS1009 | Traducción al inglés | `data/processed/decisions/IS1009.reference-en.csv` | `26377d8264460d18b2d693de6e9ea3d40257b66fc8d1814a9cca990255badb1c` |
| TS3003 | Decisiones | `data/processed/decisions/TS3003.decisions.gv.csv` | `7dd1f7fc69b6c2a040d27d89f7d85252f69d3a27b9a134196bb4953abd2695d4` |
| TS3003 | Relaciones | `data/processed/relations/TS3003.candidates.gv.csv` | `403c5cc895adce29a2c06bc9192b3d9836e6c0f0aae0c393dbea83203f261be3` |
| TS3003 | Traducción al inglés | `data/processed/decisions/TS3003.reference-en.csv` | `051e32b530c2ccaaa507ab4d634ad898c292245b27231f9eee9d2285b40e3051` |
| TS3005 | Decisiones | `data/processed/decisions/TS3005.decisions.adjudicated.csv` | `b9eef17f824db0ea3fb26217e51050487e936be9022d50651f0b799df245ea88` |
| TS3005 | Relaciones | `data/processed/relations/TS3005.candidates.adjudicated.csv` | `1840c393e952c49de036a0f4e8354ff2ccd596f098dfa8800c96bb344963ef32` |
| TS3005 | Traducción al inglés | `data/processed/decisions/TS3005.reference-en.csv` | `9a08097584caad1e6f5ea28db850ca7a9895b08b014b811f20758ea57f44288a` |
| TS3009 | Decisiones | `data/processed/decisions/TS3009.decisions.adjudicated.csv` | `40aa8312480462bcedddaa31a5f379d893ccf8235e3ed7dcf845c666cb46921a` |
| TS3009 | Relaciones | `data/processed/relations/TS3009.candidates.adjudicated.csv` | `0a7490eb16a028b486cbfe9c4ca6dc00cc51d100669f8b7e9bb03d95465a1271` |
| TS3009 | Traducción al inglés | `data/processed/decisions/TS3009.reference-en.csv` | `4776683a6a94d65faf6a16c0d1545d9ca2826d59cb1a567559669809130fad85` |
| TS3011 | Decisiones | `data/processed/decisions/TS3011.decisions.gm.csv` | `c0d2105870713ed24ac5502b5dea7504e6803f8f0227ce3f8d28c203b8bace17` |
| TS3011 | Relaciones | `data/processed/relations/TS3011.candidates.gm.csv` | `b1a54752798ab299b5bc5ea1f2e8ae20b78df5b0fb18cfc6e41e5c410d0f8c1a` |
| TS3011 | Traducción al inglés | `data/processed/decisions/TS3011.reference-en.csv` | `d7e53bc01e5f9e936109c1c56387b4b1ad51290e8568fbae556890794ee53886` |

### 2. Banco de preguntas

`data/processed/questions/banco-preguntas.csv`, SHA-256 `d6b7d6bbb80415128967b7e9efc6f46eff6dfd1ce3d5ae23fc6f0f0adb2a0cc5`. Contiene 99 preguntas validadas por `gv`: E1 25, E2 25, E3 24 y E4 25. E3 queda en 24 porque las once series de evaluación ofrecen 24 relaciones de evolución distintas ([ADR 0021](0021-adr-minimo-de-e3-segun-relaciones-disponibles.md)); el faltante frente a 25 se informa como limitación de potencia y no se rellena.

### 3. Configuración

`config/experiments.toml` completo, SHA-256 `fa1864adaa4a0030594753e3917bc346bdbf155c772c67f695649ed1c3f17c2a`, que incluye:

- **Entorno fijado** (`[pinned_environment]`): Ollama 0.32.9, OpenKOS 0.7.0 y las huellas de los modelos:

| Modelo | Huella |
|---|---|
| `bge-m3` | `7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab` |
| `gemma4:26b-a4b` | `001e5dafc3c77684c2307ebc6ab8e336e10c9b18eca52acf547d72fc83c3ca8c` |
| `gpt-oss:20b` | `f38aa0c53da5f8c49d08c43a99df24ff53167fe68e24664a7777288e7656fdfe` |
| `qwen3:8b` | `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41` |

- **Umbral τ = 0,70**, con 0,75 y 0,80 como sensibilidad ([ADR 0012](0012-adr-umbral-tau-del-experimento-a.md)).
- **Parámetros de C1**: fragmentos de 1.200 caracteres, solapamiento de 0 caracteres y K = 5 ([ADR 0007](0007-adr-ajuste-c1-y-presupuesto-de-contexto.md), enmienda del 2026-11-02).

### 4. Código

El commit exacto desde el que se corre es **el commit de fusión de este ADR en `main`**. El ADR no puede contener el hash de su propia fusión, así que ese commit se registra en `config/freeze.json` con `uv run afg freeze write --adr 0022`, ejecutado sobre `main` justo después de la fusión; en un segundo PR que agrega solo ese archivo. **La fuente de verdad del commit es ese registro, no este texto.** El registro repetirá las huellas de este ADR y deben coincidir; si alguna difiere, no se corre. La comprobación de código del bloqueo cubre `src`, `pyproject.toml` y `uv.lock`, por lo que el PR del registro no altera lo congelado.

### 5. Cifras de la referencia

- **Recall del bloqueador léxico: 0,407** (intervalo de Wilson al 95 % de 0,245 a 0,596), con las cuatro muestras de la Tarea C: 6 falsos negativos en 200 pares ([ADR 0020](0020-adr-se-mantiene-el-bloqueador-lexico.md); [notebook 18](../../notebooks/18-jss-anotacion-f2-adjudicacion.ipynb), §8).
- La referencia de relaciones es incompleta por esa pérdida, y se declara como limitación de la ground truth de relaciones donde aparezcan resultados de relaciones.

### 6. Regla

**Nada de lo congelado cambia sin un ADR nuevo.** `afg` lo hace cumplir: `afg experiment a`, `a-batch`, `a-relations`, `afg c3 build` y `afg experiment b` corren sobre una serie de evaluación solo si el registro existe, la serie está en él y no difiere la configuración, la referencia, el banco de preguntas ni el código. Las series de desarrollo (ES2015, IS1004, TS3009) corren sin registro, y una serie sin partición en `config/corpus.toml` nunca corre. Si algo difiere, el comando se detiene y lista cada diferencia con la huella actual y la congelada. Las issues de las corridas formales se crean una vez cerrado el issue #237.

## Consecuencias

- **Verificación del entorno en la máquina de las corridas** (2026-11-05, antes de fusionar): la comprobación de `[pinned_environment]` que ejecutan los comandos que llaman modelos (`require_pinned_environment`, con los cuatro modelos y OpenKOS) terminó sin diferencias: Ollama 0.32.9, OpenKOS 0.7.0 y las cuatro huellas de la tabla coinciden. No se llamó a ningún modelo.
- **Cambiar un modelo, una versión, un parámetro, una etiqueta de la referencia o una pregunta** exige un ADR nuevo y un registro nuevo; el registro existente no se sobrescribe.
- **Las limitaciones declaradas se heredan**: 24 preguntas de E3 ([ADR 0021](0021-adr-minimo-de-e3-segun-relaciones-disponibles.md)) y recall del bloqueador de 0,407 ([ADR 0020](0020-adr-se-mantiene-el-bloqueador-lexico.md)).
- **Hasta que `config/freeze.json` exista** el bloqueo impide cualquier corrida sobre series de evaluación; el issue #237 se cierra con el registro escrito y las 14 series en él.

## Respaldo

- Código: `src/afg/experiments/freeze.py` (`build_freeze_record`, `write_freeze_record`, `read_freeze_record`, `freeze_differences`, `gate_partition`) y `check_pinned_environment` en `src/afg/experiments/pinned_environment.py`.
- Tests: `tests/test_freeze.py` y `tests/test_cli_freeze_gate.py`.
- Protocolo: [`docs/protocols/congelamiento.md`](../protocols/congelamiento.md).
- Registro: `config/freeze.json`, que se agrega en el PR posterior a la fusión de este ADR.
