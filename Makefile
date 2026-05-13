# qux — developer task runner.
#
# `make help` (or just `make`) lists targets. Override the tool paths if you
# don't use the in-repo venv: e.g. `make test PYTHON=python3`.

PYTHON      ?= .venv/bin/python
PIP         ?= .venv/bin/pip
RUFF        ?= .venv/bin/ruff
PYLINT      ?= .venv/bin/pylint
LINT_IMPORTS ?= .venv/bin/lint-imports
ISORT       ?= .venv/bin/isort
BLACK       ?= .venv/bin/black
CHECK_DOCS  ?= python3 ~/.claude/skills/racecar-doc-coherence/scripts/check_docs.py

SOURCES := src/qux

.DEFAULT_GOAL := help
.PHONY: help install test test-v format ruff lint arch docs check build clean

help: ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Editable install with dev extras.
	$(PIP) install -e '.[dev]'

test: ## Run the full test suite (dots + summary).
	$(PYTHON) runtests.py

test-v: ## Run the full test suite verbosely (one line per test).
	QUX_TEST_VERBOSITY=2 $(PYTHON) runtests.py

format: ## Apply isort then black (must run in that order).
	$(ISORT) $(SOURCES)
	$(BLACK) $(SOURCES)

ruff: ## Fast linter (ruff) — auto-fixes safe drift on each invocation.
	$(RUFF) check $(SOURCES) --fix

lint: ## Pylint with the pylint-django plugin (settings: qux.tests.settings).
	$(PYLINT) $(SOURCES)

arch: ## Verify import-linter contracts (utilities don't depend on apps; apps stay independent).
	$(LINT_IMPORTS) --config pyproject.toml

docs: ## Mechanical doc-coherence pre-pass (link/anchor/section-number drift).
	$(CHECK_DOCS)

check: ruff lint arch docs ## All static checks. Run before pushing.

build: ## Build sdist + wheel into dist/.
	$(PYTHON) -m build

clean: ## Remove caches and build artifacts.
	rm -rf build/ dist/ src/qux.egg-info/
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
