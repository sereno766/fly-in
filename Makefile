# ============================================================
# Fly-in — Makefile
# Automação de tarefas do projeto (setup, execução, testes, lint)
# ============================================================

# --- Configuração ---------------------------------------------------------
PYTHON      := python3
VENV_DIR    := venv
VENV_BIN    := $(VENV_DIR)/bin
PIP         := $(VENV_BIN)/pip
PY          := $(VENV_BIN)/python
MAIN        := src/main.py
MAP         ?= maps/easy_1.txt

# --- install ---------------------------------------------------------------
# Cria o ambiente virtual (se não existir) e instala as dependências.
.PHONY: install
install:
	@test -d $(VENV_DIR) || $(PYTHON) -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

# --- run ---------------------------------------------------------------
# Executa o script principal do projeto.
# Uso: make run MAP=maps/hard_2.txt
.PHONY: run
run:
	$(PY) $(MAIN) $(MAP)

# --- debug ---------------------------------------------------------------
# Executa o script principal em modo debug usando pdb.
.PHONY: debug
debug:
	$(PY) -m pdb $(MAIN) $(MAP)

# --- clean ---------------------------------------------------------------
# Remove arquivos temporários e caches.
.PHONY: clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# --- fclean ---------------------------------------------------------------
# Limpeza completa: além do clean, remove também o venv.
.PHONY: fclean
fclean: clean
	rm -rf $(VENV_DIR)

# --- lint ---------------------------------------------------------------
# Roda flake8 e mypy com as flags obrigatórias do enunciado.
.PHONY: lint
lint:
	$(VENV_BIN)/flake8 .
	$(VENV_BIN)/mypy . \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs

# --- lint-strict (opcional) -------------------------------------------------
# Verificação de tipos aprimorada (--strict).
.PHONY: lint-strict
lint-strict:
	$(VENV_BIN)/flake8 .
	$(VENV_BIN)/mypy . --strict

# --- test ---------------------------------------------------------------
# Roda os testes unitários (não obrigatório/entregue, mas útil no dev).
.PHONY: test
test:
	$(VENV_BIN)/pytest tests/ -v

# --- re ---------------------------------------------------------------
# Atalho: limpa tudo e reinstala do zero.
.PHONY: re
re: fclean install

# --- help ---------------------------------------------------------------
.PHONY: help
help:
	@echo "Alvos disponíveis:"
	@echo "  make install     - cria venv e instala dependências"
	@echo "  make run         - executa a simulação (MAP=arquivo opcional)"
	@echo "  make debug       - executa em modo debug (pdb)"
	@echo "  make clean       - remove caches (__pycache__, .mypy_cache, etc.)"
	@echo "  make fclean      - clean + remove o venv"
	@echo "  make lint        - flake8 + mypy (flags obrigatórias)"
	@echo "  make lint-strict - flake8 + mypy --strict"
	@echo "  make test        - roda os testes unitários"
	@echo "  make re          - fclean + install"
