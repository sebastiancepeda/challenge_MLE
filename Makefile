.ONESHELL:
ENV_PREFIX=$(if $(wildcard .venv/bin/pip),.venv/bin/,)

.PHONY: help
help:             	## Show the help.
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@fgrep "##" Makefile | fgrep -v fgrep

.PHONY: venv
venv:			## Create a virtual environment
	@echo "Creating virtualenv ..."
	@rm -rf .venv
	@python3 -m venv .venv
	@./.venv/bin/pip install -U pip
	@echo
	@echo "Run 'source .venv/bin/activate' to enable the environment"

.PHONY: install
install:		## Install dependencies
	$(ENV_PREFIX)pip install -r requirements-dev.txt
	$(ENV_PREFIX)pip install -r requirements-test.txt
	$(ENV_PREFIX)pip install -r requirements.txt

STRESS_URL = https://latam-delay-api-jklkpx77uq-uc.a.run.app
.PHONY: stress-test
stress-test:
	@mkdir -p reports
	@curl -fsS -o /dev/null $(STRESS_URL)/health
	$(ENV_PREFIX)locust -f tests/stress/api_stress.py --print-stats --html reports/stress-test.html --run-time 60s --headless --users 100 --spawn-rate 1 -H $(STRESS_URL)

.PHONY: model-test
model-test:			## Run tests and coverage
	mkdir reports || true
	$(ENV_PREFIX)pytest --cov-config=.coveragerc --cov-report term --cov-report html:reports/html --cov-report xml:reports/coverage.xml --junitxml=reports/junit.xml --cov=challenge tests/model

.PHONY: api-test
api-test:			## Run tests and coverage
	mkdir reports || true
	$(ENV_PREFIX)pytest --cov-config=.coveragerc --cov-report term --cov-report html:reports/html --cov-report xml:reports/coverage.xml --junitxml=reports/junit.xml --cov=challenge tests/api

.PHONY: build
build:			## Build locally the python artifact
	$(ENV_PREFIX)python setup.py bdist_wheel