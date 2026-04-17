.PHONY: install precompute schema genzod build dev test test-py test-site test-e2e clean deploy-local

# -------- setup ------------------------------------------------------------

install:
	cd precompute && uv sync --extra dev
	cd site && npm ci

# -------- precompute -------------------------------------------------------

schema:
	cd precompute && uv run python -m f1.schema

precompute: schema
	cd precompute && uv run python -m f1.build

# -------- site -------------------------------------------------------------

genzod:
	cd site && npm run gen:zod

build: precompute genzod
	mkdir -p site/public/data
	cp precompute/out/australia-2026.json site/public/data/
	cd site && npm run build

dev: precompute genzod
	mkdir -p site/public/data
	cp precompute/out/australia-2026.json site/public/data/
	cd site && npm run dev

# -------- tests ------------------------------------------------------------

test-py:
	cd precompute && uv run pytest

test-site:
	cd site && npm run test

test-e2e: precompute genzod
	# Playwright's webServer.command builds with VITE_BASE=/ so tests can
	# hit page.goto("/") without a subpath. We only need data staged here.
	mkdir -p site/public/data
	cp precompute/out/australia-2026.json site/public/data/
	cd site && npm run test:e2e

test: test-py test-site test-e2e

# -------- deploy (local) ---------------------------------------------------

# Builds and then pushes site/dist to the gh-pages branch using gh-pages npm.
# Requires: npm i -D gh-pages (added on first use).
deploy-local: test build
	cd site && npx --yes gh-pages@6 -d dist

# -------- housekeeping -----------------------------------------------------

clean:
	rm -rf precompute/out/*
	rm -rf site/dist site/public/data/*.json
	rm -rf site/test-results site/playwright-report
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
