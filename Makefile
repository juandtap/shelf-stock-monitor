BACKEND_DIR := apps/backend

.PHONY: check lint format-check format typecheck test

check: lint format-check typecheck test

lint:
	cd $(BACKEND_DIR) && uv run ruff check .

format-check:
	cd $(BACKEND_DIR) && uv run ruff format --check .

format:
	cd $(BACKEND_DIR) && uv run ruff check . --fix
	cd $(BACKEND_DIR) && uv run ruff format .

typecheck:
	cd $(BACKEND_DIR) && uv run mypy app tests

test:
	cd $(BACKEND_DIR) && uv run pytest -v