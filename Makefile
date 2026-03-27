.PHONY: lint format check test

format:
	isort .
	black .

lint:
	flake8 .

check: format lint

test:
	pytest

coverage:
	pytest --cov-report=html:tests/coverage_html
	open tests/coverage_html/index.html