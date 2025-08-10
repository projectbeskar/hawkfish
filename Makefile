.PHONY: venv install lint test run fmt

venv:
	python -m venv .venv
	. .venv/bin/activate && pip install -U pip

install:
	. .venv/bin/activate && pip install -e .[dev]

lint:
	. .venv/bin/activate && ruff check .
	. .venv/bin/activate && mypy src

test:
	. .venv/bin/activate && pytest -q

run:
	. .venv/bin/activate && python -m hawkfish_controller --host 0.0.0.0 --port 8080

fmt:
	. .venv/bin/activate && ruff check --select I --fix .


