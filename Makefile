.PHONY: test lint format typecheck check clean gifs

test: check
	uv run pytest

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

format-check:
	uv run ruff format --check src/ tests/

typecheck:
	uv run mypy src/

check: lint format-check typecheck

TAPES := $(wildcard docs/tapes/*.tape)

gifs: $(TAPES)
	@mkdir -p docs/screenshots
	@for tape in $(TAPES); do \
		echo "Recording $$(basename $$tape .tape).gif..."; \
		vhs $$tape; \
	done
	@echo "Done. GIFs in docs/screenshots/"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist/
