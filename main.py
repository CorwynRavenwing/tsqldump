#!/usr/bin/env python3

# tsqldump/main.py

"""
tsqldump - Microsoft SQL Server Database Dump Utility

Extracts database schemas and table data into an executable T-SQL script.
Handles Unicode strings (N'...'), binary hex literals (0x...), dates, GUIDs,
foreign key ordering, and IDENTITY insertion settings.
"""

import argparse
import datetime
import decimal
import sys
import uuid
import pymssql

def parse_args():
    parser = argparse.ArgumentParser(
        description="tsqldump - MSSQL database dump utility"
    )

    # Connection flags
    parser.add_argument(
        "-S", "--server",
        required=True,
        help="SQL Server host or host,port"
    )
    parser.add_argument(
        "-U", "--user",
        required=True,
        help="Database username"
    )
    parser.add_argument(
        "-P", "--password",
        required=True,
        help="Database password"
    )
    parser.add_argument(
        "-d", "--database",
        required=True,
        help="Target database name"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: stdout)"
    )

    # Mode flags
    parser.add_argument(
        # "-d",
        "--data-only",
        action="store_true",
        help="Dump data INSERTs only, not schema.",
        default=False,
    )
    parser.add_argument(
        # "-s",
        "--schema-only",
        action="store_true",
        default=False,
        help="Dump schema DDL only, not data.",
    )

    # Object flags
    parser.add_argument(
        "-R",
        "--routines",
        action="store_true",
        default=False,
        help="Dump stored procedures and functions."
    )
    parser.add_argument(
        "--triggers",
        action="store_true",
        default=True,
        help="Dump triggers (default: enabled).",
    )
    parser.add_argument(
        "--skip-triggers",
        action="store_false",
        dest="triggers",
        help="Do not dump triggers."
    )
    parser.add_argument(
        "--views",
        action="store_true",
        default=True,
        help="Dump views (default: enabled).",
    )
    parser.add_argument(
        "--skip-views",
        action="store_false",
        dest="views",
        help="Do not dump views."
    )

    return parser.parse_args()


def format_literal(val):
    """Formats Python values retrieved from SQL Server into valid T-SQL literals."""
    if val is None:
        return "NULL"

    if isinstance(val, bool):
        return "1" if val else "0"

    if isinstance(val, (int, float, decimal.Decimal)):
        return str(val)

    if isinstance(val, bytes):
        return "0x" + val.hex().upper()

    if isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
        return f"'{val.isoformat()}'"

    if isinstance(val, uuid.UUID):
        return f"'{str(val).upper()}'"

    if isinstance(val, str):
        # Escape single quotes by doubling them
        escaped = val.replace("'", "''")
        # Prepend 'N' to ensure Unicode NVARCHAR literals are preserved
        return f"N'{escaped}'"

    # Fallback string representation
    escaped = str(val).replace("'", "''")
    return f"N'{escaped}'"


class TSQLDumper:
    def __init__(self, host, port, user, password, database, output_stream):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.out = output_stream
        self.conn = None

    def connect(self):
        self.conn = pymssql.connect(
            server=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="UTF-8",
            autocommit=True
        )

    def write(self, text=""):
        self.out.write(text + "\n")

    def get_tables(self):
        """Fetches tables sorted to honor foreign key dependencies."""
        cursor = self.conn.cursor(as_dict=True)
        query = """
        SELECT
            s.name AS schema_name,
            t.name AS table_name,
            t.object_id
        FROM sys.tables t
        JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE t.is_ms_shipped = 0
        ORDER BY t.name ASC;
        """
        cursor.execute(query)
        tables = cursor.fetchall()

        # Simple topological dependency sort based on foreign keys
        cursor.execute("""
        SELECT
            OBJECT_SCHEMA_NAME(parent_object_id) AS parent_schema,
            OBJECT_NAME(parent_object_id) AS parent_table,
            OBJECT_SCHEMA_NAME(referenced_object_id) AS ref_schema,
            OBJECT_NAME(referenced_object_id) AS ref_table
        FROM sys.foreign_keys
        WHERE parent_object_id != referenced_object_id;
        """)
        fk_deps = cursor.fetchall()

        deps = {}
        for row in tables:
            key = (row["schema_name"], row["table_name"])
            deps[key] = set()

        for fk in fk_deps:
            parent = (fk["parent_schema"], fk["parent_table"])
            ref = (fk["ref_schema"], fk["ref_table"])
            if parent in deps and ref in deps and parent != ref:
                deps[parent].add(ref)

        ordered = []
        visited = set()

        def visit(node):
            if node not in visited:
                visited.add(node)
                for dep in deps.get(node, []):
                    visit(dep)
                ordered.append(node)

        for table_key in deps:
            visit(table_key)

        return ordered

    def dump_header(self):
        self.write(f"-- ========================================================")
        self.write(f"-- tsqldump Microsoft SQL Server Dump")
        self.write(f"-- Database: {self.database}")
        self.write(f"-- Date: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        self.write(f"-- ========================================================\n")
        self.write(f"USE [{self.database}];")
        self.write("GO\n")

    def dump_table_ddl(self, schema, table):
        cursor = self.conn.cursor(as_dict=True)

        # Fetch columns
        cursor.execute("""
        SELECT
            c.name,
            TYPE_NAME(c.user_type_id) AS type_name,
            c.max_length,
            c.precision,
            c.scale,
            c.is_nullable,
            c.is_identity
        FROM sys.columns c
        WHERE c.object_id = OBJECT_ID(%s)
        ORDER BY c.column_id;
        """, (f"{schema}.{table}",))
        columns = cursor.fetchall()

        col_defs = []
        has_identity = False
        for c in columns:
            name = c["name"]
            type_name = c["type_name"].upper()
            is_null = "NULL" if c["is_nullable"] else "NOT NULL"

            if c["is_identity"]:
                has_identity = True
                identity_str = " IDENTITY(1,1)"
            else:
                identity_str = ""

            # Type length/precision formatting
            if type_name in ("NVARCHAR", "NCHAR"):
                length = "MAX" if c["max_length"] == -1 else str(c["max_length"] // 2)
                type_spec = f"{type_name}({length})"
            elif type_name in ("VARCHAR", "CHAR", "VARBINARY", "BINARY"):
                length = "MAX" if c["max_length"] == -1 else str(c["max_length"])
                type_spec = f"{type_name}({length})"
            elif type_name in ("DECIMAL", "NUMERIC"):
                type_spec = f"{type_name}({c['precision']},{c['scale']})"
            else:
                type_spec = type_name

            col_defs.append(f"    [{name}] {type_spec}{identity_str} {is_null}")

        # Fetch Primary Keys
        cursor.execute("""
        SELECT c.name
        FROM sys.indexes i
        JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        WHERE i.is_primary_key = 1 AND i.object_id = OBJECT_ID(%s)
        ORDER BY ic.key_ordinal;
        """, (f"{schema}.{table}",))
        pk_cols = [r["name"] for r in cursor.fetchall()]

        if pk_cols:
            pk_str = ", ".join(f"[{col}]" for col in pk_cols)
            col_defs.append(f"    PRIMARY KEY ({pk_str})")

        self.write(f"-- Schema DDL for [{schema}].[{table}]")
        self.write(f"IF OBJECT_ID(N'[{schema}].[{table}]', N'U') IS NOT NULL")
        self.write(f"    DROP TABLE [{schema}].[{table}];")
        self.write("GO\n")
        self.write(f"CREATE TABLE [{schema}].[{table}] (")
        self.write(",\n".join(col_defs))
        self.write(");")
        self.write("GO\n")

        return has_identity

    def dump_table_data(self, schema, table, has_identity):
        cursor = self.conn.cursor(as_dict=True)
        cursor.execute(f"SELECT * FROM [{schema}].[{table}];")
        rows = cursor.fetchall()

        if not rows:
            return

        self.write(f"-- Data for [{schema}].[{table}]")
        if has_identity:
            self.write(f"SET IDENTITY_INSERT [{schema}].[{table}] ON;")

        col_names = list(rows[0].keys())
        cols_str = ", ".join(f"[{c}]" for c in col_names)

        for row in rows:
            values_str = ", ".join(format_literal(row[col]) for col in col_names)
            self.write(f"INSERT INTO [{schema}].[{table}] ({cols_str}) VALUES ({values_str});")

        if has_identity:
            self.write(f"SET IDENTITY_INSERT [{schema}].[{table}] OFF;")

        self.write("GO\n")

    def dump_foreign_keys(self, tables):
        """Applies foreign keys after table creation and data inserts."""
        cursor = self.conn.cursor(as_dict=True)
        cursor.execute("""
        SELECT
            fk.name AS fk_name,
            OBJECT_SCHEMA_NAME(fk.parent_object_id) AS parent_schema,
            OBJECT_NAME(fk.parent_object_id) AS parent_table,
            COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS parent_col,
            OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS ref_schema,
            OBJECT_NAME(fk.referenced_object_id) AS ref_table,
            COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS ref_col
        FROM sys.foreign_keys fk
        JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
        """)
        fks = cursor.fetchall()

        if not fks:
            return

        self.write("-- Foreign Key Constraints")
        for fk in fks:
            p_schema, p_tbl = fk["parent_schema"], fk["parent_table"]
            r_schema, r_tbl = fk["ref_schema"], fk["ref_table"]

            # Only add foreign keys for dumped tables
            if (p_schema, p_tbl) in tables and (r_schema, r_tbl) in tables:
                self.write(
                    f"ALTER TABLE [{p_schema}].[{p_tbl}] ADD CONSTRAINT [{fk['fk_name']}] "
                    f"FOREIGN KEY ([{fk['parent_col']}]) REFERENCES [{r_schema}].[{r_tbl}] ([{fk['ref_col']}]);"
                )
        self.write("GO\n")

    def dump_views(self) -> None:
        """Extract view definitions from sys.views and sys.sql_modules."""
        cursor = self.conn.cursor(as_dict=True)
        query = """
            SELECT
                SCHEMA_NAME(v.schema_id) AS schema_name,
                v.name AS view_name,
                m.definition
            FROM sys.views v
            JOIN sys.sql_modules m ON v.object_id = m.object_id
            WHERE v.is_ms_shipped = 0
            ORDER BY schema_name, view_name;
        """
        cursor.execute(query)
        views = cursor.fetchall()

        for v in views:
            schema = v['schema_name']
            name = v['view_name']
            definition = v['definition'].strip()

            self.write(f"-- View DDL for [{schema}].[{name}]\n")
            self.write(f"IF OBJECT_ID(N'[{schema}].[{name}]', N'V') IS NOT NULL\n")
            self.write(f"    DROP VIEW [{schema}].[{name}];\n")
            self.write("GO\n\n")
            self.write(f"{definition}\n")
            self.write("GO\n\n")

    def dump_routines(self) -> None:
        """Extract Stored Procedures and Functions from sys.objects and sys.sql_modules."""
        cursor = self.conn.cursor(as_dict=True)
        query = """
            SELECT
                SCHEMA_NAME(o.schema_id) AS schema_name,
                o.name AS routine_name,
                o.type AS routine_type,
                m.definition
            FROM sys.objects o
            JOIN sys.sql_modules m ON o.object_id = m.object_id
            WHERE o.is_ms_shipped = 0
              AND o.type IN ('P', 'FN', 'IF', 'TF')
            ORDER BY o.type, schema_name, routine_name;
        """
        cursor.execute(query)
        routines = cursor.fetchall()

        for r in routines:
            schema = r['schema_name']
            name = r['routine_name']
            r_type = r['routine_type'].strip()
            definition = r['definition'].strip()

            drop_type = 'P' if r_type == 'P' else 'FN'
            obj_kw = 'PROCEDURE' if r_type == 'P' else 'FUNCTION'
            type_desc = "Stored Procedure" if r_type == 'P' else "Function"

            self.write(f"-- {type_desc} DDL for [{schema}].[{name}]\n")
            self.write(f"IF OBJECT_ID(N'[{schema}].[{name}]', N'{drop_type}') IS NOT NULL\n")
            self.write(f"    DROP {obj_kw} [{schema}].[{name}];\n")
            self.write("GO\n\n")
            self.write(f"{definition}\n")
            self.write("GO\n\n")

    def dump_triggers(self) -> None:
        """Extract Table Triggers from sys.triggers and sys.sql_modules."""
        cursor = self.conn.cursor(as_dict=True)
        query = """
            SELECT
                OBJECT_SCHEMA_NAME(t.parent_id) AS schema_name,
                t.name AS trigger_name,
                m.definition
            FROM sys.triggers t
            JOIN sys.sql_modules m ON t.object_id = m.object_id
            WHERE t.is_ms_shipped = 0
            ORDER BY schema_name, trigger_name;
        """

        cursor.execute(query)
        triggers = cursor.fetchall()

        for trg in triggers:
            schema = trg['schema_name'] or 'dbo'
            name = trg['trigger_name']
            definition = trg['definition'].strip()

            self.write(f"-- Trigger DDL for [{schema}].[{name}]\n")
            self.write(f"IF OBJECT_ID(N'[{schema}].[{name}]', N'TR') IS NOT NULL\n")
            self.write(f"    DROP TRIGGER [{schema}].[{name}];\n")
            self.write("GO\n\n")
            self.write(f"{definition}\n")
            self.write("GO\n\n")

    def dump(self, schema_only=False, data_only=False, routines=False, triggers=True, views=True):
        self.connect()
        self.dump_header()

        tables = self.get_tables()
        table_identity_map = {}

        if not data_only:
            # self.dump_tables_schema()
            for schema, table in tables:
                has_id = self.dump_table_ddl(schema, table)
                table_identity_map[(schema, table)] = has_id

        if not schema_only:
            # self.dump_data()
            for schema, table in tables:
                has_id = table_identity_map.get((schema, table), False)
                self.dump_table_data(schema, table, has_id)

        if not data_only:
            self.dump_foreign_keys(tables)

        if not data_only:
            if views:
                self.dump_views()

        if not data_only:
            if routines:
                self.dump_routines()

        if not data_only:
            if triggers:
                self.dump_triggers()


def main():
    args = parse_args()

    # Split host/port if specified as "host,port"
    if "," in args.server:
        host, port_str = args.server.split(",", 1)
        port = int(port_str)
    else:
        host = args.server
        port = 1433

    out_stream = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout

    try:
        # Instantiate dumper with connection details and output stream
        dumper = TSQLDumper(
            host=host,
            port=port,
            user=args.user,
            password=args.password,
            database=args.database,
            output_stream=out_stream
        )
        # Invoke dump with the matching signature
        dumper.dump(
            schema_only=args.schema_only,
            data_only=args.data_only,
            routines=args.routines,
            triggers=args.triggers,
            views=args.views,
        )
    except Exception as e:
        sys.stderr.write(f"Error during dump: {e}\n")
        sys.exit(1)
    finally:
        if args.output and out_stream:
            out_stream.close()


if __name__ == "__main__":
    main()
