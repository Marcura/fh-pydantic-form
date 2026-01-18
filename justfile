# Run `just` or `just help` to see available recipes

set shell := ["zsh", "-lc"]
set dotenv-load := false

# Show available recipes
help:
  @just --list

# Sync dev dependencies with uv
sync:
  uv sync --all-extras --dev

# Install Playwright Chromium (with system deps)
playwright:
  uv run playwright install chromium --with-deps

# Install prek/pre-commit hooks
hooks:
  uv run prek install

# Run tests (excluding Playwright)
test *args:
  uv run pytest tests -m "not playwright" {{args}}

# Run Playwright browser tests
test-browser *args:
  uv run pytest tests/e2e -m playwright --browser chromium {{args}}

# Run all tests (non-Playwright then Playwright)
test-all *args:
  uv run pytest tests -m "not playwright" {{args}}
  uv run pytest tests/e2e -m playwright --browser chromium

# Run type checking
typecheck:
  uv run ty

# Run prek across the repo
lint:
  uv run prek run -a
