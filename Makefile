.PHONY: install test lint audit run html

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=src --cov-report=html

lint:
	python -m flake8 src/ tests/ --max-line-length=100

audit:
	python -m src.rules.engine --data-dir data --output-dir output

html:
	python scripts/generate_html_dashboard.py

run:
	streamlit run dashboard.py
