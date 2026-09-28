# tsqldump

A cross-platform command-line utility for Microsoft SQL Server inspired by MySQL's `mysqldump`. It extracts database schemas (DDL, primary keys, foreign keys) and table data into clean, executable T-SQL scripts while preserving multi-byte Unicode strings, binary data, dates, and complex SQL types.

## Features

- **Multi-Byte / Unicode Preservation:** Automatically formats strings with `N'...'` literals to prevent character corruption across foreign languages and emojis.
- **Dependency Ordering:** Orders table definitions and data inserts to honor foreign key constraints.
- **Identity Column Support:** Generates `SET IDENTITY_INSERT` statements for tables with auto-incrementing identity columns.
- **Type-Fidelity:** Supports binary (`0x...`), GUIDs, XML, dates, numeric precision, and `NULL` values.
- **Cross-Platform:** Built in Python 3; runs natively on Windows, Linux, and macOS.
- **Isolated Testing Ecosystem:** Self-contained Docker test suite included under `test/`.

---

## License

This project is released under the **Apache License 2.0**.

You are free to use, modify, distribute, and integrate this software in commercial, non-profit, or internal CI/CD pipelines without restriction. See the [`LICENSE`](./LICENSE) file for full details.

---

## Quick Start / Local Usage

### Prerequisites

- Python 3.8+
- Microsoft SQL Server access

### Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/your-username/tsqldump.git](https://github.com/your-username/tsqldump.git)
   cd tsqldump
   ```

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Command Usage
   ```bash
   python3 src/tsqldump/main.py -S localhost,1433 -U sa -P 'YourPassword' -d MyDatabase -o dump.sql
   ```

### Command-Line Options

| Option | Long Option | Description |
| :--- | :--- | :--- |
| `-S` | `--server` | SQL Server host or `host,port` (e.g., `localhost,1433`). Required. |
| `-U` | `--user` | Database username. Required. |
| `-P` | `--password` | Database password. Required. |
| `-d` | `--database` | Target database name. Required. |
| `-o` | `--output` | File path to write SQL output (default: `stdout`). |
| | `--schema-only` | Dump database DDL and table definitions only. |
| | `--data-only` | Dump data `INSERT` statements only. |

## Running the Integration Test Suite

The repository contains a fully isolated integration test suite in the `test/` directory. It spins up a SQL Server 2022 container seeded with international multi-byte strings (CJK, Cyrillic, Arabic, Hebrew, Emojis) and native data types, executes `tsqldump`, restores the output into a fresh database, and asserts character-level equality.

### Option 1: Using the Makefile (Recommended)

To start the test database container and run the integration test suite:

`make test`

To tear down the test environment when finished:

`make test-clean`

### Option 2: Running via Docker Compose Directly

1. Navigate to the `test/` directory:
   `cd test`

1. Boot the test database container:
   `docker compose up -d test-db`

1. Run the integration test runner:
   `python3 run_tests.py`

1. Bring down the containers:
   `docker compose down -v`

## Packaging Executables (Optional)

To bundle `tsqldump` into a standalone, single-file binary with no Python runtime dependency (e.g., `tsqldump` on Linux/macOS or `tsqldump.exe` on Windows), use PyInstaller:

Install PyInstaller:
`pip install pyinstaller`

Build the standalone binary:
`pyinstaller --onefile --name tsqldump src/tsqldump/main.py`

The compiled executable will be written to `dist/tsqldump`.

