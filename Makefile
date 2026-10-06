# ==============================================================================
# tsqldump/Makefile
# ==============================================================================

.PHONY: help setup build test test-clean clean install uninstall

PYTHON := python3
TEST_DIR := test
PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
BINARY_NAME := tsqldump

help:
	@echo "tsqldump Management Commands:"
	@echo "  make setup          Set up host system, installing local Python dependencies"
	@echo "  make test           Spin up test DB and execute integration test suite"
	@echo "  make test-clean     Clean up test containers and temporary files"
	@echo "  make build          Package tsqldump into a standalone binary via PyInstaller"
	@echo "  make clean          Remove build artifacts and temporary files"
	@echo "  make install        TBD"
	@echo "  make uninstall      TBD"

# 1. Host dependency installation
setup:
	$(PYTHON) -m pip install -r requirements.txt

# 2. Containerized build (outputs to dist/tsqldump)
build:
	@mkdir -p dist
	docker run --rm \
		-e HOME=/tmp \
		-v "$$(pwd):/app" \
		-w /app \
		--user="$$(id -u):$$(id -g)" \
		python:3.11 \
		sh -c "pip install --no-cache-dir pyinstaller -r requirements.txt && python -m PyInstaller --onefile --name $(BINARY_NAME) main.py"

# 3. Canonical install: Copies built binary to target system PATH
install:
	@if [ ! -f "dist/$(BINARY_NAME)" ]; then \
		echo "Error: dist/$(BINARY_NAME) does not exist. Run 'make build' first."; \
		exit 1; \
	fi
	install -d $(DESTDIR)$(BINDIR)
	install -m 755 dist/$(BINARY_NAME) $(DESTDIR)$(BINDIR)/$(BINARY_NAME)
	@echo "Successfully installed $(BINARY_NAME) to $(DESTDIR)$(BINDIR)/"

# 4. Uninstall binary from system PATH
uninstall:
	rm -f $(DESTDIR)$(BINDIR)/$(BINARY_NAME)
	@echo "Removed $(DESTDIR)$(BINDIR)/$(BINARY_NAME)"

test:
	@mkdir -p test/output
	HOST_UID=$$(id -u) HOST_GID=$$(id -g) \
		docker compose \
			-f test/docker-compose.yml \
			up --build \
			--exit-code-from test-runner
	@echo "✓ Integration tests passed inside container!"

test-clean:
	docker compose -f test/docker-compose.yml down -v

clean: test-clean
	rm -rf build/ dist/ *.spec __pycache__

logs:
	docker logs tsqldump_test_db

errors:
	docker exec -it tsqldump_test_db /opt/mssql-tools18/bin/sqlcmd \
	   -S localhost -U sa -P 'YourSecurePassword123!' -C \
	   -Q "EXEC sp_readerrorlog 0, 1;"
