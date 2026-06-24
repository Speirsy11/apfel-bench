.PHONY: help test test-backend test-frontend test-live dev backend frontend stop clean install

# Defaults — override on the command line, e.g. `make dev PORT=9000`
PORT          ?= 8080
VITE_PORT     ?= 5173
APFEL_PORT    ?= 11435
APFEL_BIN     ?= apfel
ROOT          := $(shell pwd)
BACKEND       := $(ROOT)/backend
FRONTEND      := $(ROOT)/frontend
VENV          := $(BACKEND)/.venv
VENV_PY       := $(VENV)/bin/python

help:  ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Set up backend venv and install deps.
	cd $(BACKEND) && [ -d .venv ] || /opt/homebrew/bin/python3 -m venv .venv
	$(VENV_PY) -m pip install --quiet -e "$(BACKEND)[dev]"
	cd $(FRONTEND) && bun install

test: test-backend test-frontend  ## Run all unit tests (skips live integration).

test-backend:  ## Run backend pytest.
	cd $(BACKEND) && $(VENV_PY) -m pytest

test-frontend:  ## Run frontend vitest.
	cd $(FRONTEND) && bun run test

test-live:  ## Run live integration tests (requires running apfel).
	cd $(BACKEND) && APFEL_INTEGRATION=1 $(VENV_PY) -m pytest

backend:  ## Run the FastAPI backend only.
	cd $(BACKEND) && $(VENV_PY) -m apfel_bench.main

frontend:  ## Run the Vite dev server only.
	cd $(FRONTEND) && bun run dev

dev:  ## Run backend + frontend together with live reload (Ctrl-C stops both).
	./scripts/dev.sh

stop:  ## Stop anything started by this Makefile.
	-pkill -f "apfel_bench.main" 2>/dev/null
	-pkill -f "vite" 2>/dev/null
	@echo "stopped."

clean:  ## Remove build artifacts and venvs.
	rm -rf $(VENV) $(FRONTEND)/node_modules $(FRONTEND)/dist $(BACKEND)/build $(BACKEND)/dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	@echo "cleaned."
