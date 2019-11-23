SHELL := /bin/bash

# these files should pass flakes8
FLAKE8_WHITELIST=$(shell find . -name "*.py" \
                    ! -path "./docs/*" ! -path "./.tox/*" \
                    ! -path "./env/*" ! -path "./venv/*" \
                    ! -path "**/compat.py")

open := $(shell { which xdg-open || which open; } 2>/dev/null)

.PHONY: clean-pyc clean-build docs clean


help:  ## This help dialog.
	@IFS=$$'\n' ; \
	help_lines=(`fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##/:/'`); \
	printf "%-15s %s\n" "target" "help" ; \
	printf "%-15s %s\n" "------" "----" ; \
	for help_line in $${help_lines[@]}; do \
		IFS=$$':' ; \
		help_split=($$help_line) ; \
		help_command=`echo $${help_split[0]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		help_info=`echo $${help_split[2]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		printf '\033[36m'; \
		printf "%-15s %s" $$help_command ; \
		printf '\033[0m'; \
		printf "%s\n" $$help_info; \
	done


init:  ## Install the project in development mode (using virtualenv is highly recommended)
	pip install -U setuptools pip
	pip install -e .[mysql,postgresql,profiler,test,dev]

clean: clean-build clean-pyc clean-test  ## Remove all build, test, coverage and Python artifacts

clean-build:  ## Remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:  ## Remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:  ## Eemove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

test:  ## Run tests quickly with the default Python
	py.test

test-all:  ## Run tests on every Python version with tox
	tox

coverage: ## Check code coverage quickly with the default Python
	coverage erase
	tox $(TOX)
	coverage combine
	coverage report --include=* -m
	coverage html
	$(open) htmlcov/index.html

lint:  ## Check style with flake8
	flake8 $(FLAKE8_WHITELIST)

docs:  ## Generate Sphinx HTML documentation, including API docs
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(open) docs/_build/html/index.html

dist: clean  ## Package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

servedocs: docs ## compile the docs watching for changes
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release: clean  ## Package and upload a release
	python setup.py register
	python setup.py sdist upload
	python setup.py bdist_wheel upload

generate-travis-config:  ## Bump the release version
	@python scripts/generate-travis-config.py

bumpversion:  ## Bump the release version
	@python scripts/bumpversion.py release

newversion:  ## Set the new development version
	@python scripts/bumpversion.py newversion $(filter-out $@,$(MAKECMDGOALS))

docker-test:  ## Build docker images
	@bash scripts/run-test-with-docker.sh

docker-all-test:  ## Build docker images
	@bash scripts/run-all-test-with-docker.sh

%:
	@:
