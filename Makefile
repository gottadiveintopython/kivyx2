PYTHON = python
PYTEST = $(PYTHON) -m pytest
FLAKE8 = $(PYTHON) -m flake8

test:
	env KCFG_GRAPHICS_MAXFPS=0 $(PYTEST) ./tests

style:
	$(FLAKE8) --count --select=E,W,F --show-source --statistics --max-line-length=119 ./src/kivyx
	$(FLAKE8) --count --select=E,W,F --show-source --statistics --ignore E501 ./tests
	$(FLAKE8) --count --select=E,W,F --show-source --statistics --max-line-length=119 --ignore F401,E402 ./examples

html:
	sphinx-build -b html ./sphinx ./docs

livehtml:
	sphinx-autobuild -b html ./sphinx ./docs
