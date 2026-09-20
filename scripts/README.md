# scripts/

Este directorio no contiene scripts independientes, deliberadamente. Toda operación que
soporta este proyecto es accesible a través de la CLI `afg` (`src/afg/cli.py`), instalada
como script de consola por `pyproject.toml`:

```bash
uv run afg --help
```

Mantener un único punto de entrada evita el desajuste habitual entre la lógica real de un
paquete y un conjunto de scripts sueltos que terminan reimplementando partes de ella. Si
alguna vez se necesita una operación puntual que no pertenece a la CLI, agréguela aquí con
un comentario que explique por qué no es un comando de la CLI; no deje que este directorio
crezca en silencio.
