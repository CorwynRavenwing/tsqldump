# ==============================================================================
# tsqldump/Makefile
# ==============================================================================

.PHONY: help install test test-db-up test-db-down test-clean build clean

PYTHON := python3
TEST_DIR := test

help:
	@echo "tsqldump Management Commands:"
	@echo "  make install        Install local Python dependencies"
	@echo "  make test           Spin up test DB and execute integration test suite"
	@echo "  make test-db-up     Boot test SQL Server container in test/"
	@echo "  make test-db-down   Stop test SQL Server container"
	@echo "  make test-clean     Clean up test containers and temporary files"
	@echo "  make build          Package tsqldump into a standalone binary via PyInstaller"
	@echo "  make clean          Remove build artifacts and temporary files"

install:
	$(PYTHON) -m pip install -r requirements.txt

test-db-up:
	cd $(TEST_DIR) && docker compose up -d test-db
	@echo "Waiting for test database container to pass health check..."
	@until [ "$$(docker inspect --format='{{json .State.Health.Status}}' tsqldump_test_db 2>/dev/null)" = '"healthy"' ]; do sleep 2; done
	@echo "Test database container is ready!"

test: test-db-up
	$(PYTHON) $(TEST_DIR)/run_tests.py

test-db-down:
	cd $(TEST_DIR) && docker compose down

test-clean:
	cd $(TEST_DIR) && docker compose down -v
	rm -f $(TEST_DIR)/test_dump.sql

build:
	$(PYTHON) -m pip install pyinstaller
	pyinstaller --onefile --name tsqldump src/tsqldump/main.py

clean: test-clean
	rm -rf build/ dist/ *.spec __pycache__ src/tsqldump/__pycache__

