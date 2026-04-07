test:
	env KCFG_GRAPHICS_MAXFPS=0 python -m pytest ./tests

html:
	sphinx-build -b html ./sphinx ./docs
