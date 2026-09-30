MOVING_FORWARD_PLAN.md


# 0. let's verify that the parent/child relationship between those two tables is also being exported?


# Part (A): How mysqldump Handles Routines, Triggers & Views

mysqldump exposes specific CLI flags to control non-table database objects:

Feature | mysqldump CLI Flag | Default Behavior in mysqldump | Standard Output Behavior
Views | Always included (unless --no-create-info) | Enabled by default | Output as CREATE ALGORITHM=... VIEW...
Triggers | --triggers / --skip-triggers | ON by default | Included inline after table creation/data
Stored Procedures & Functions | --routines (-R) | OFF by default | Requires -R flag to include CREATE PROCEDURE/FUNCTION

Since tsqldump targets SQL Server, we can mirror these exact flag names in our CLI argument parser while tailoring the underlying SQL generation to T-SQL syntax.

# Part (B): Proposed Roadmap for tsqldump Integration

We can expand tsqldump to support routines, triggers, and views across the full pipeline:

1. CLI Arguments in main.py

Add standard flags to argparse:

* --routines (-R): Include Stored Procedures and Scalar/Table-Valued Functions.

* --triggers: Include Table Triggers (enabled by default, with --skip-triggers to disable).

* --views: Include Database Views (enabled by default).

2. T-SQL Extraction Queries (main.py)

* Views: Query sys.views and sys.sql_modules to fetch definitions (OBJECT_DEFINITION(object_id)).

* Routines: Query sys.objects where type IN ('P', 'FN', 'IF', 'TF') and fetch definitions via sys.sql_modules.

* Triggers: Query sys.triggers and retrieve definitions via sys.sql_modules.

3. Execution Ordering in Dump Output

To avoid dependency crashes during restore, objects should be written in this sequence:

1. Table Schemas (CREATE TABLE)
2. Views (CREATE VIEW)
3. Data Inserts (INSERT INTO)
4. Foreign Keys (ALTER TABLE ... ADD CONSTRAINT)
5. Stored Procedures & Functions (CREATE PROCEDURE / FUNCTION)
6. Triggers (CREATE TRIGGER)

# Next Action

To get this built into the pipeline:

1. Seed Data: Add sample Views, Functions, Stored Procedures, and Triggers to seed_data() in test/run_tests.py.

2. Extractor Logic: Implement sys.sql_modules extraction routines in main.py with CLI flags (--routines, --triggers, --views).

3. Verification: Extend verify_data() in test/run_tests.py to test object existence and execute test procedures/views against RestoredTestDumpDB.
