.PHONY: help setup setup-full setup-deck skill-assets skill-link deck-render lint fmt typecheck test check corpus inventory biblio lab clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Install dev + notebook dependency groups
	uv sync --group dev --group notebooks

setup-full: ## Install every optional dependency group and extra
	uv sync --all-extras --group dev --group notebooks

setup-deck: ## Install dev + deck groups (python-pptx, python-docx) and check for LibreOffice
	uv sync --group dev --group deck
	@command -v soffice >/dev/null 2>&1 \
		&& echo "LibreOffice found: $$(command -v soffice)" \
		|| echo "Warning: LibreOffice (soffice) not found. Rendering decks for visual review needs it; see README section 6."

skill-assets: ## Install the deck-uc assets from the locally synced shared folder
	uv run afg skills sync-assets deck-uc

skill-link: ## Link deck-uc into a tool's skills folder: make skill-link DEST=<folder>
	@test -n "$(DEST)" || { echo "Usage: make skill-link DEST=<folder>"; exit 2; }
	uv run afg skills link deck-uc "$(DEST)"

deck-render: ## Render a PPTX/DOCX to PDF for visual review: make deck-render FILE=<path> [OUT=<dir>]
	@test -n "$(FILE)" || { echo "Usage: make deck-render FILE=<path> [OUT=<dir>]"; exit 2; }
	@command -v soffice >/dev/null 2>&1 || { echo "LibreOffice (soffice) not found; see README section 6."; exit 1; }
	soffice --headless --convert-to pdf --outdir "$(or $(OUT),$(dir $(FILE)))" "$(FILE)"

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
