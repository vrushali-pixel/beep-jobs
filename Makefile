.PHONY: install test lint format run discover sample score serve

install:        ## install the package and dev tools
	pip install -e ".[dev]"

test:           ## run all tests (offline, no API key needed)
	pytest

lint:           ## check style and common bugs
	ruff check src tests

format:         ## auto-fix what ruff can fix
	ruff check --fix src tests

run:            ## the daily pipeline (needs internet; GEMINI_API_KEY for AI tagging)
	fresherjobs run

discover:       ## check every company board
	fresherjobs discover

sample:         ## 50 posts to hand-check
	fresherjobs sample

score:          ## accuracy + cost per 1,000 posts
	fresherjobs score eval/sample_50_checked.csv

serve:          ## open the page locally at http://localhost:8000
	cd site && python -m http.server 8000
