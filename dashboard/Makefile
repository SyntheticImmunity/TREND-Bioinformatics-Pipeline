.PHONY: help install ingest dev backend frontend test test-equivalence test-e2e clean docker-build docker-up docker-down

REPO_ROOT := $(abspath ..)
LIB4_INFO := $(REPO_ROOT)/codes/2. HPC_cluster_scripts/required_metadata/Lib4_info_concise_060621.csv
ENHANCER_META := $(REPO_ROOT)/codes/3. Post_HPC_enhancer_activity_analysis_scripts/required_metadata/all_enhancer_metadata_111525.csv
STATE_DIR := backend/state
LIBRARY_DB := $(STATE_DIR)/library.sqlite
LIBRARY_SUMMARY := $(STATE_DIR)/library_summary.json

help:
	@echo "TREND Dashboard - common targets:"
	@echo "  make install         Install Python backend in editable mode (with dev deps)"
	@echo "  make ingest          Build library.sqlite + library_summary.json from metadata CSVs"
	@echo "  make backend         Run FastAPI backend on http://localhost:8000"
	@echo "  make frontend        Run Vite dev server on http://localhost:5173"
	@echo "  make dev             docker compose up (canonical reviewer entry point)"
	@echo "  make test            Run all tests"
	@echo "  make test-equivalence  Run C2 equivalence tests only"
	@echo "  make clean           Remove generated state (keeps source intact)"

install:
	pip install -e ".[dev]"

ingest: $(LIBRARY_DB) $(LIBRARY_SUMMARY)

$(LIBRARY_DB) $(LIBRARY_SUMMARY): $(LIB4_INFO) $(ENHANCER_META)
	@mkdir -p $(STATE_DIR)
	python -m backend.library.ingest \
	    --lib4-info "$(LIB4_INFO)" \
	    --enhancer-meta "$(ENHANCER_META)" \
	    --library-db "$(LIBRARY_DB)" \
	    --library-summary "$(LIBRARY_SUMMARY)"

backend: ingest
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm install && npm run dev

dev: docker-up

docker-build:
	docker compose build

docker-up:
	docker compose up

docker-down:
	docker compose down

test:
	cd .. && pytest tests/ -v

test-equivalence:
	cd .. && pytest tests/equivalence/ -v

test-e2e:
	cd .. && pytest tests/e2e/ -v

clean:
	rm -f $(LIBRARY_DB) $(LIBRARY_SUMMARY)
	rm -rf backend/state/runs.sqlite
	rm -rf frontend/node_modules frontend/dist
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
