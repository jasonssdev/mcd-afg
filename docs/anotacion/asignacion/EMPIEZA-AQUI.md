# Empieza aquí — anotación OE1

Para quien nunca ha abierto este repositorio y le toca anotar. Una página; si necesitas más
detalle, cada paso enlaza adonde está.

## 1. Clona e instala

Sigue **"Tu primer día, paso a paso"** en [`../../../README.md`](../../../README.md) §3: fork,
clonar tu fork, `uv sync --group dev --group notebooks`, y verificar con `uv run afg --help` y
`uv run pytest -q`. No se repite aquí.

## 2. Un comando deja todo listo

```bash
uv run afg gold setup --annotator <tus iniciales>
```

Descarga el corpus AMI (pide confirmar la licencia CC BY 4.0 antes de bajar 228 MB), genera
las 171 transcripciones, y crea `<serie>.decisions.<iniciales>.csv` y
`<serie>.candidates.<iniciales>.csv` para cada serie que te toca, ya nombrados y con las
columnas de máquina llenas. Nunca copies ni renombres un CSV a mano; correr esto de nuevo no
borra lo que ya anotaste, y salta cualquier paso que ya esté hecho. Termina diciéndote la
ruta exacta del primer archivo que debes abrir — anótala, la usas en el paso 4.

## 3. Lee, en este orden, antes de escribir nada

1. [`../annotation-guidelines.md`](../annotation-guidelines.md) — qué cuenta como decisión, qué
   significa cada una de las seis relaciones.
2. [`../manual-anotacion-oe1.md`](../manual-anotacion-oe1.md) — el manual operativo, con un
   ejemplo real resuelto de punta a punta.
3. Tu documento personal: [`tareas-gv.md`](tareas-gv.md), [`tareas-gm.md`](tareas-gm.md) o
   [`tareas-jss.md`](tareas-jss.md). Trae tu "Tu día a día en tres comandos" arriba de todo y
   tus series, en orden, más abajo.
4. La transcripción de la reunión, generada en el paso 2 — anotar solo desde el resumen es el
   error que más cuesta corregir.

## 4. Llena solo las columnas humanas

Con la primera serie que te indicó `afg gold setup` (Fase 1 primero):

- **Tarea A** (`<serie>.decisions.<iniciales>.csv`): `status`, `decision_object`,
  `decision_content`, `notes` si hace falta.
- **Tarea B** (`<serie>.candidates.<iniciales>.csv`): `relation`, `direction_ok`,
  `confidence`, `notes` si hace falta.

`annotator` ya viene puesto. Ninguna columna de máquina se toca; los valores permitidos de
cada columna están en tu documento personal, §2.

## 5. Valida antes de abrir el PR

```bash
uv run afg gold validate --annotator <tus iniciales> --series <ID>
```

Tiene que salir sin errores. `0/N` no es un error: es trabajo por hacer. Sin `--series`
recorre todas tus series asignadas.

## 6. Abre el PR

Una serie, un PR — instrucciones exactas (rama, mensaje de commit, a quién le toca revisar)
en la sección "Cómo entregas" de tu documento personal.

---

El mantenedor sigue el avance de todo el equipo con `uv run afg gold status`, sin abrir un
solo archivo. El reparto completo — quién anota qué, en qué orden, cuándo se adjudica — está
en [`README.md`](README.md). Si alguna vez necesitas recrear un archivo puntual en vez de todo
el flujo, `afg gold prepare --annotator <iniciales>` sigue disponible.
