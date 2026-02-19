.PHONY: test lint format typecheck check clean

test: check
	uv run pytest

lint:
	uv run ruff check

format:
	uv run ruff format

format-check:
	uv run ruff format --check

typecheck:
	uv run mypy

check: lint format-check typecheck

TAPES := $(wildcard docs/tapes/*.tape)
GIFS  := $(patsubst docs/tapes/%.tape,docs/screenshots/%.gif,$(TAPES))

gifs: $(GIFS)
	@echo "Done. GIFs in docs/screenshots/"

docs/screenshots/%.gif: docs/tapes/%.tape
	@mkdir -p docs/screenshots
	@echo "Recording $*.gif..."
	@vhs $<

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist/
