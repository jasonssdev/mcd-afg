.PHONY: help setup setup-full lint fmt typecheck test check corpus inventory biblio lab clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Install dev + notebook dependency groups
	uv sync --group dev --group notebooks

setup-full: ## Install every optional dependency group and extra
	uv sync --all-extras --group dev --group notebooks

lint: ## Ruff check (no fixes applied)
	uv run ruff check .

fmt: ## Ruff format
	uv run ruff format .

typecheck: ## mypy over src/afg
	uv run mypy src/afg

test: ## pytest
	uv run pytest -q

check: lint typecheck test ## lint + typecheck + test

corpus: ## Download the AMI manual annotations (interactive confirmation, CC BY 4.0)
	uv run afg corpus download

inventory: ## Paso cero: verify corpus completeness and count decisions/links
	uv run afg corpus inventory

biblio: ## Bibliography coverage audit
	uv run afg biblio audit

lab: ## Launch Jupyter Lab
	uv run jupyter lab

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
	find . -name '__pycache__' -not -path './.git/*' -exec rm -rf {} +
