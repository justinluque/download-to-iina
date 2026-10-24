.PHONY: test build icons

test:
	python3 -m unittest discover -s tests
	node --test tests/*.test.cjs

build:
	python3 scripts/package.py

icons:
	python3 scripts/icons.py
