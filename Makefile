PYTHON ?= python
PIP ?= $(PYTHON) -m pip

.PHONY: install install-dev test live mock match history export validate list lint clean

install:          ## Base install (mock mode works everywhere)
	$(PIP) install -e '.[dev]'

install-fetchers: ## Full install including live-fetch session types
	$(PIP) install -e '.[dev,fetchers]'

test:             ## Run the unit test suite (offline-safe)
	$(PYTHON) -m pytest tests -q

live: install-fetchers
	$(PYTHON) -m scrapers.cli run --live

mock:             ## Demo run against bundled sample data (default)
	$(PYTHON) -m scrapers.cli run --mock

match:            ## Re-run matching only, on already-collected raw data
	$(PYTHON) -m scrapers.cli match

history:          ## Show price-history velocity + restock/price-drop alerts
	$(PYTHON) -m scrapers.cli history

export:           ## Regenerate reports from the latest matched outputs
	$(PYTHON) -m scrapers.cli export

validate:         ## Validate config + sources without scraping
	$(PYTHON) -m scrapers.cli validate-config

list:
	$(PYTHON) -m scrapers.cli list-sources

lint:             ## Static analysis (ruff)
	ruff check .

clean:            ## Remove build/cache artifacts
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache build dist *.egg-info .ruff_cache data/runs
