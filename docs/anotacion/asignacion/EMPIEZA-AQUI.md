# Empieza aquí — anotación OE1

Para quien nunca ha abierto este repositorio y le toca anotar. Una página; si necesitas más
detalle, cada paso enlaza adonde está.

## 1. Clona e instala

Sigue **"Tu primer día, paso a paso"** en [`../../../README.md`](../../../README.md) §3: fork,
clonar tu fork, `uv sync --group dev --group notebooks`, y verificar con `uv run afg --help` y
`uv run pytest -q`. No se repite aquí.

## 2. Lee, en este orden, antes de escribir nada

1. [`../annotation-guidelines.md`](../annotation-guidelines.md) — qué cuenta como decisión, qué
   significa cada una de las seis relaciones.
2. [`../manual-anotacion-oe1.md`](../manual-anotacion-oe1.md) — el manual operativo, con un
   ejemplo real resuelto de punta a punta.
3. Tu documento personal: [`tareas-gv.md`](tareas-gv.md), [`tareas-gm.md`](tareas-gm.md) o
   [`tareas-jss.md`](tareas-jss.md). Trae tu "Tu día a día en tres comandos" arriba de todo y
   tus series, en orden, más abajo.

## 3. Crea tus archivos

```bash
uv run afg gold prepare --annotator <tus iniciales>
```

Crea `<serie>.decisions.<iniciales>.csv` y `<serie>.candidates.<iniciales>.csv` para cada
serie que te toca (ver tu documento personal), ya nombrados y con las columnas de máquina
llenas. Nunca copies ni renombres un CSV a mano; correr esto de nuevo no borra lo que ya
anotaste.

## 4. Llena solo las columnas humanas

Con la primera serie de tu documento personal (Fase 1 primero):

- **Tarea A** (`<serie>.decisions.<iniciales>.csv`): `status`, `decision_object`,
  `decision_content`, `notes` si hace falta.
- **Tarea B** (`<serie>.candidates.<iniciales>.csv`): `relation`, `direction_ok`,
  `confidence`, `notes` si hace falta.

`annotator` ya viene puesto. Ninguna columna de máquina se toca; los valores permitidos de
cada columna están en tu documento personal, §2.

## 5. Valida antes de abrir el PR

```bash
uv run afg gold validate --annotator <tus iniciales>
```

Tiene que salir sin errores. `0/N` no es un error: es trabajo por hacer. Agrega `--series
<ID>` para revisar solo la serie cuyo PR vas a abrir.

## 6. Abre el PR

Una serie, un PR — instrucciones exactas (rama, mensaje de commit, a quién le toca revisar)
en la sección "Cómo entregas" de tu documento personal.

---

El mantenedor sigue el avance de todo el equipo con `uv run afg gold status`, sin abrir un
solo archivo. El reparto completo — quién anota qué, en qué orden, cuándo se adjudica — está
en [`README.md`](README.md).
