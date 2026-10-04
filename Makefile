# ==============================================================================
# tsqldump/Makefile
# ==============================================================================

.PHONY: help install test test-clean build clean

PYTHON := python3
TEST_DIR := test

help:
	@echo "tsqldump Management Commands:"
	@echo "  make install        Install local Python dependencies"
	@echo "  make test           Spin up test DB and execute integration test suite"
	@echo "  make test-clean     Clean up test containers and temporary files"
	@echo "  make build          Package tsqldump into a standalone binary via PyInstaller"
	@echo "  make clean          Remove build artifacts and temporary files"

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	docker compose -f test/docker-compose.yml up --build --exit-code-from test-runner
	@echo "✓ Integration tests passed inside container!"

test-clean:
	docker compose -f test/docker-compose.yml down -v

build:
	$(PYTHON) -m pip install pyinstaller
	pyinstaller --onefile --name tsqldump src/tsqldump/main.py

clean: test-clean
	rm -rf build/ dist/ *.spec __pycache__ src/tsqldump/__pycache__

logs:
	docker logs tsqldump_test_db

errors:
	docker exec -it tsqldump_test_db /opt/mssql-tools18/bin/sqlcmd \
	   -S localhost -U sa -P 'YourSecurePassword123!' -C \
	   -Q "EXEC sp_readerrorlog 0, 1;"
