.PHONY: lint format check test

format:
	isort .
	black .

lint:
	flake8 .

check: format lint

test:
	pytest -v --cov
