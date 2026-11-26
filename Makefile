.PHONY: help setup setup-full setup-deck skill-assets skill-link deck-render lint fmt typecheck test check corpus inventory biblio lab hosted-bridge hosted-local-baseline hosted-pilot hosted-run hosted-compare hosted-derive hosted-derive-baseline hosted-answers-c1 hosted-answers hosted-answers-baseline hosted-answers-compare hosted-notebook clean

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

hosted-bridge: ## Hosted extension: continuity bridge (historical, done on OpenKOS 0.7.2; refuses to re-run)
	uv run afg experiment a-hosted --bridge

hosted-local-baseline: ## Hosted extension: secondary baseline (qwen3:8b on OpenKOS 0.7.3, 11 series x 3 runs, local Ollama; resumable)
	uv run afg experiment a-hosted --local-baseline

hosted-pilot: ## Hosted extension: pilot of one model (ES2002 x 1): make hosted-pilot LABEL=<label>
	@test -n "$(LABEL)" || { echo "Usage: make hosted-pilot LABEL=<label> (see config/hosted_extraction.toml)"; exit 2; }
	@test -n "$$OPENKOS_OPENAI_API_KEY" || { echo "OPENKOS_OPENAI_API_KEY is not set: export the key of the provider of $(LABEL) in your shell first (never in a file)."; exit 2; }
	uv run afg experiment a-hosted --model "$(LABEL)" --pilot

hosted-run: ## Hosted extension: full run of one model + descriptive report: make hosted-run LABEL=<label>
	@test -n "$(LABEL)" || { echo "Usage: make hosted-run LABEL=<label> (see config/hosted_extraction.toml)"; exit 2; }
	@test -n "$$OPENKOS_OPENAI_API_KEY" || { echo "OPENKOS_OPENAI_API_KEY is not set: export the key of the provider of $(LABEL) in your shell first (never in a file)."; exit 2; }
	uv run afg experiment a-hosted --model "$(LABEL)"
	uv run afg experiment a-report --c2-extraction "experimento-a-hosted-$(LABEL)" --descriptive

hosted-compare: ## Hosted extension: paired comparison of every model with both baselines (+ bridge check)
	uv run afg experiment a-hosted-compare --include-bridge

QUESTIONS ?= data/processed/questions/banco-preguntas.csv

hosted-derive: ## Hosted answers: derive the query workspaces of one model (no model call): make hosted-derive LABEL=<label>
	@test -n "$(LABEL)" || { echo "Usage: make hosted-derive LABEL=<label> (see config/hosted_extraction.toml)"; exit 2; }
	uv run afg experiment b-derive --source "experimento-a-hosted-$(LABEL)"

hosted-derive-baseline: ## Hosted answers: derive the query workspaces of the 0.7.3 baseline (no model call)
	uv run afg experiment b-derive --source experimento-a-base-0-7-3

hosted-answers-c1: ## Hosted answers: control C1 on the extension infrastructure (Ollama 0.40.16, local, long; ADR 0026 amendment 4)
	uv run afg experiment b --questions "$(QUESTIONS)" --conditions c1 --environment hosted --run-name experimento-b-c1-ollama-0-40-16

hosted-answers: ## Hosted answers: Experiment B of C2 over the derived workspaces of one model (local Ollama, long): make hosted-answers LABEL=<label>
	@test -n "$(LABEL)" || { echo "Usage: make hosted-answers LABEL=<label> (run make hosted-derive LABEL=<label> first)"; exit 2; }
	uv run afg experiment b --questions "$(QUESTIONS)" --conditions c2 --c2-derived "experimento-a-hosted-$(LABEL)-consulta" --run-name "experimento-b-hosted-$(LABEL)"

hosted-answers-baseline: ## Hosted answers: Experiment B of C2 over the derived 0.7.3 baseline (local Ollama, long)
	uv run afg experiment b --questions "$(QUESTIONS)" --conditions c2 --c2-derived experimento-a-base-0-7-3-consulta --run-name experimento-b-base-0-7-3

hosted-answers-compare: ## Hosted answers: paired comparison of every C2 run with the current C1, plus the infrastructure effect (reads stored runs)
	uv run afg experiment b-hosted-compare

hosted-notebook: ## Hosted extension: re-execute notebook 33 in place
	uv run jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 notebooks/33-jss-extraccion-con-modelos-de-pago.ipynb

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
	find . -name '__pycache__' -not -path './.git/*' -exec rm -rf {} +
