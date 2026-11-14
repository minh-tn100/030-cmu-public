# Uses .venv if it exists (create it with `make setup`), else python3 on PATH.
# Python >= 3.10 is required; macOS's system python3 (3.9) is too old.
PY := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
BOOTSTRAP ?= $(shell for p in python3.13 python3.12 python3.11 python3.10 python3; do \
	command -v $$p >/dev/null 2>&1 && $$p -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null && { echo $$p; break; }; done)

.PHONY: setup check-python test recall recall-st eval demo-stub demo-claude clean

setup:
	@test -n "$(BOOTSTRAP)" || { echo "error: need Python >= 3.10 on PATH (e.g. brew install python@3.12)"; exit 1; }
	$(BOOTSTRAP) -m venv .venv
	.venv/bin/pip install -q --upgrade pip
	.venv/bin/pip install -q -e ".[claude,skills]"
	.venv/bin/python -m spacy download en_core_web_md
	@echo "setup done: run 'make test'"

check-python:
	@$(PY) -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else "error: $(PY) is Python %d.%d; need >= 3.10. Run make setup." % sys.version_info[:2])'

test: check-python
	$(PY) -m pytest -q

recall: check-python
	$(PY) -m eval.run_recall

recall-st: check-python
	$(PY) -m eval.run_recall --st

eval: check-python             # offline agent eval with the deterministic stub
	$(PY) -m eval.run_agent_eval

demo-stub: check-python        # no key, no network: out-stub/report.html
	$(PY) cli.py review --llm stub --out out-stub

demo-claude: check-python      # needs ANTHROPIC_API_KEY: out-claude/{report.html,RESULTS.md,audit.jsonl}
	$(PY) cli.py review --llm claude --compare --max-calls 100 --out out-claude && $(PY) -m eval.report_eval out-claude

clean:
	rm -rf out-stub out-claude .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
