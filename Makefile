export DBT_PROFILES_DIR := .
MF ?= mf

all: data build validate export dashboard test catalog

data:
	python3 data_generation/generate_raw.py --customers 1500 --seed 42 --out data/raw

build:
	cd dbt_project && dbt build

validate:
	cd dbt_project && $(MF) validate-configs

export:
	python3 scripts/export_and_plot.py

catalog:
	python3 scripts/generate_catalog.py

test:
	python3 -m pytest -q tests

dashboard:
	python3 scripts/build_dashboard.py
