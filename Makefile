PYTHON = python
PYTEST = $(PYTHON) -m pytest
FLAKE8 = $(PYTHON) -m flake8

test:
	env KCFG_GRAPHICS_MAXFPS=0 $(PYTEST) ./tests

style:
	$(FLAKE8) --count --select=E9,F63,F7,F82 --show-source --statistics ./tests ./src/kivyx ./examples
	$(FLAKE8) --count --max-complexity=10 --max-line-length=119 --statistics ./src/kivyx ./examples

html:
	sphinx-build -b html ./sphinx ./docs

livehtml:
	sphinx-autobuild -b html ./sphinx ./docs
