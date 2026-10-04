#!/usr/bin/env python3

# tsqldump/test/run-test.py

"""
tsqldump Integration Test Suite

Verifies end-to-end functionality of tsqldump:
1. Connects to the initialized test SQL Server container.
2. Runs tsqldump on 'TestDumpDB' to produce a dump file.
3. Creates a fresh, empty target database 'RestoredTestDumpDB'.
4. Executes the dump file against 'RestoredTestDumpDB'.
5. Asserts exact string equality across international multi-byte text (CJK, Arabic, Cyrillic, Emojis).
"""

import os
import sys
import subprocess
import pymssql

# Connection settings matching test/Dockerfile.db and docker-compose.yml
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "1433"))
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YourSecurePassword123!")

# Project directory paths
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(TEST_DIR, ".."))
CLI_PATH = os.path.join(REPO_ROOT, "main.py")

SOURCE_DB = "TestDumpDB"
TARGET_DB = "RestoredTestDumpDB"
DUMP_FILE = os.path.join(REPO_ROOT, "test", "output", "test_dump.sql")

def get_connection(db_name="master"):
    """Creates an autocommit pymssql connection to SQL Server."""
    conn = pymssql.connect(
        server=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=db_name,
        charset="UTF-8",
        autocommit=True
    )
    return conn

def run_tsqldump():
    """Executes the tsqldump CLI to generate a database dump file."""
    print(f"[*] Running tsqldump on '{SOURCE_DB}'...")

    cmd = [
        sys.executable, CLI_PATH,
        "-S", f"{DB_HOST},{DB_PORT}",
        "-U", DB_USER,
        "-P", DB_PASSWORD,
        "-d", SOURCE_DB,
        "-o", DUMP_FILE
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"[!] tsqldump failed with exit code {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        sys.exit(1)

    print(f"[+] Dump created successfully: {DUMP_FILE} ({os.path.getsize(DUMP_FILE)} bytes)")


def recreate_target_db():
    """Drops (if exists) and recreates the fresh target database."""
    print(f"[*] Preparing target database '{TARGET_DB}'...")
    conn = get_connection("master")
    cursor = conn.cursor()

    # Kill active connections and drop target database if present
    cursor.execute(f"""
        IF EXISTS (SELECT name FROM sys.databases WHERE name = '{TARGET_DB}')
        BEGIN
            ALTER DATABASE [{TARGET_DB}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
            DROP DATABASE [{TARGET_DB}];
        END
    """)
    cursor.execute(f"CREATE DATABASE [{TARGET_DB}];")
    conn.close()
    print(f"[+] Target database '{TARGET_DB}' created.")


def restore_dump():
    """Executes the generated SQL dump script against the target database."""
    print(f"[*] Restoring dump into '{TARGET_DB}'...")

    # Ensure a completely pristine database state before restoring
    conn_master = get_connection("master")
    cursor_master = conn_master.cursor()
    # Drop existing connections and database cleanly
    cursor_master.execute("""
        IF DB_ID('RestoredTestDumpDB') IS NOT NULL
        BEGIN
            ALTER DATABASE [RestoredTestDumpDB] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
            DROP DATABASE [RestoredTestDumpDB];
        END
    """)
    # at this moment, DB is guaranteed *not* to exist
    cursor_master.execute("CREATE DATABASE [RestoredTestDumpDB];")
    # and here, it's guaranteed *to* exist
    conn_master.close()

    conn = get_connection(TARGET_DB)
    cursor = conn.cursor()

    with open(DUMP_FILE, "r", encoding="utf-8") as f:
        sql_script = f.read()

    # Execute batch by batch (splitting on GO if present, or executing blocks)
    batches = sql_script.split("\nGO\n") if "\nGO\n" in sql_script else [sql_script]
    for i, batch in enumerate(batches):
        cleaned_batch = batch.strip()
        if not cleaned_batch:
            continue

        # Remove leading comments to check the actual statement
        lines = [line.strip() for line in cleaned_batch.splitlines() if line.strip() and not line.strip().startswith("--")]
        statement = lines[0].upper() if lines else ""

        # Skip USE statements so we don't switch context away from RestoredTestDumpDB
        if statement.startswith("USE "):
            print(f"Skipping context switch batch #{i+1}: {cleaned_batch[:40]}...")
            continue

        print(f"Executing Batch #{i+1}:\n{cleaned_batch[:80]}...\n")
        cursor.execute(cleaned_batch)

    conn.close()
    print(f"[+] Restore completed successfully into '{TARGET_DB}'.")


def verify_data():
    """
    Queries both source and restored databases to assert exact string and data equality.
    """
    print("[*] Verifying data integrity and Unicode string equality...")

    conn_src = get_connection(SOURCE_DB)
    conn_tgt = get_connection(TARGET_DB)

    cursor_src = conn_src.cursor(as_dict=True)
    cursor_tgt = conn_tgt.cursor(as_dict=True)

    # -------------------------------------------------------------------------
    # STANZA 1: Verify UnicodeTest table
    # -------------------------------------------------------------------------
    cursor_src.execute("SELECT LanguageName, SampleText, EmojiSample FROM UnicodeTest ORDER BY ID ASC;")
    src_rows = cursor_src.fetchall()

    cursor_tgt.execute("SELECT LanguageName, SampleText, EmojiSample FROM UnicodeTest ORDER BY ID ASC;")
    tgt_rows = cursor_tgt.fetchall()

    assert len(src_rows) == len(tgt_rows), f"Row count mismatch in UnicodeTest: {len(src_rows)} vs {len(tgt_rows)}"

    for i, (src, tgt) in enumerate(zip(src_rows, tgt_rows), start=1):
        print(f"    Checking row {i} [{src['LanguageName']}]:")

        # Exact string assertion on SampleText
        assert src["SampleText"] == tgt["SampleText"], (
            f"SampleText mismatch at row {i} ({src['LanguageName']}):\n"
            f"  Expected: {src['SampleText']}\n"
            f"  Got:      {tgt['SampleText']}"
        )

        # Exact string assertion on EmojiSample
        assert src["EmojiSample"] == tgt["EmojiSample"], (
            f"EmojiSample mismatch at row {i} ({src['LanguageName']}):\n"
            f"  Expected: {src['EmojiSample']}\n"
            f"  Got:      {tgt['EmojiSample']}"
        )
        print(f"      ✓ SampleText: '{src['SampleText']}'")
        print(f"      ✓ EmojiSample: '{src['EmojiSample']}'")

    # -------------------------------------------------------------------------
    # STANZA 2: Verify Products table with foreign keys & numeric text
    # -------------------------------------------------------------------------
    cursor_src.execute("SELECT ProductID, ProductName, Price FROM Products ORDER BY ProductID ASC;")
    src_products = cursor_src.fetchall()

    cursor_tgt.execute("SELECT ProductID, ProductName, Price FROM Products ORDER BY ProductID ASC;")
    tgt_products = cursor_tgt.fetchall()

    assert len(src_products) == len(tgt_products), "Row count mismatch in Products"

    for src_p, tgt_p in zip(src_products, tgt_products):
        assert src_p["ProductName"] == tgt_p["ProductName"], (
            f"ProductName mismatch: Expected '{src_p['ProductName']}', got '{tgt_p['ProductName']}'"
        )
        assert src_p["Price"] == tgt_p["Price"], (
            f"Price mismatch: Expected {src_p['Price']}, got {tgt_p['Price']}"
        )
        print(f"    ✓ Product {src_p['ProductID']} ({src_p['ProductName']}): Price verified")

    # -------------------------------------------------------------------------
    # STANZA 3: Verify AllTypesTest table
    # -------------------------------------------------------------------------
    cursor_src.execute("SELECT * FROM AllTypesTest;")
    src_all = cursor_src.fetchone()

    cursor_tgt.execute("SELECT * FROM AllTypesTest;")
    tgt_all = cursor_tgt.fetchone()

    assert src_all is not None, "Source database returned no rows for verification query!"
    assert tgt_all is not None, "Restored database returned no rows for verification query!"

    for col_name in src_all.keys():
        src_val = src_all[col_name]
        tgt_val = tgt_all[col_name]
        assert src_val == tgt_val, f"Type mismatch in column '{col_name}': Expected {src_val!r}, got {tgt_val!r}"
        print(f"    ✓ Data type column '{col_name}' verified: {tgt_val!r}")

    conn_src.close()
    conn_tgt.close()
    print("\n[🎉] ALL TESTS PASSED! Multi-byte characters and schemas preserved perfectly.")


def main():
    try:
        run_tsqldump()
        recreate_target_db()

        print(f"[*] Dump file path: {os.path.abspath(DUMP_FILE)}")
        print(f"[*] File exists? {os.path.exists(DUMP_FILE)}")
        if os.path.exists(DUMP_FILE):
            print(f"[*] File size: {os.path.getsize(DUMP_FILE)} bytes")

        try:
            restore_dump()
        except Exception as e:
            print("\n" + "="*50)
            print("[!] RESTORE FAILED. Printing contents of dump file:")
            print("="*50)
            if os.path.exists(DUMP_FILE):
                with open(DUMP_FILE, "r", encoding="utf-8") as f:
                    print(f.read())
            else:
                print(f"[!] Dump file NOT found at: {DUMP_FILE}")
            print("="*50 + "\n")
            raise e

        verify_data()
    finally:
        # Clean up dump file after test execution
        if os.path.exists(DUMP_FILE):
            os.remove(DUMP_FILE)


if __name__ == "__main__":
    main()

