.PHONY: install test lint audit run

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=src --cov-report=html

lint:
	python -m flake8 src/ tests/ --max-line-length=100

audit:
	python -m src.rules.engine

run:
	streamlit run app/dashboard.py
