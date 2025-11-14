import re
import subprocess
import sys
import pathlib
import urllib.parse
import psycopg2
import psycopg2.errors

def run_deploy(
    source_dir: pathlib.Path,
    host: str = "localhost",
    port: int = 5432,
    dbname: str = "postgres",
    user: str = None,
    password: str = None,
    schema: str = None,
    allow_create: bool = False
):
    """
    Deploy schema or schema changes to a target database.
    Args:
        source_dir (pathlib.Path): Path to the source schema directory.
        host (str): Database host (default: localhost).
        port (int): Database port (default: 5432).
        dbname (str): Database name (default: postgres).
        user (str): Username for database authentication.
        password (str): Password for database authentication.
        scheme (str): Database scheme (default: postgres).
    """
    print("Deploying schema to target database...")
    if not source_dir.exists():
        print(f"Error: Source directory does not exist: {source_dir}")
        sys.exit(1)
    if not host:
        print(f"Error: Target database host is required.")
        sys.exit(1)

    # Build connection string (disable SSL for PostgreSQL)
    scheme = "postgres"
    netloc = ""
    if user and password:
        netloc += f"{urllib.parse.quote(user)}:{urllib.parse.quote(password)}@"
    elif user:
        netloc += f"{urllib.parse.quote(user)}@"
    netloc += host
    if port:
        netloc += f":{port}"
    path = f"/{dbname}" if dbname else ""
    query = "sslmode=disable"
    if schema:
        query += f"&search_path={urllib.parse.quote(schema)}"
    target = urllib.parse.urlunparse((scheme, netloc, path, "", query, ""))

    # Optionally create database and schema if requested
    if allow_create:
        print(f"[deploy] Ensuring database '{dbname}' exists...")
        # Connect to the default 'postgres' database as admin
        admin_conn_str = f"host={host} port={port} dbname=postgres user={user} password={password} sslmode=disable"
        try:
            admin_conn = psycopg2.connect(admin_conn_str)
            admin_conn.autocommit = True
            with admin_conn.cursor() as cur:
                cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
                exists = cur.fetchone()
                if not exists:
                    cur.execute(f"CREATE DATABASE {dbname};")
                    print(f"[deploy] Database '{dbname}' created.")
                else:
                    print(f"[deploy] Database '{dbname}' already exists.")
            admin_conn.close()
        except Exception as e:
            print(f"[deploy] Error creating database: {e}")
            sys.exit(1)

        if schema:
            print(f"[deploy] Ensuring schema '{schema}' exists in database '{dbname}'...")
            schema_conn_str = f"host={host} port={port} dbname={dbname} user={user} password={password} sslmode=disable"
            try:
                schema_conn = psycopg2.connect(schema_conn_str)
                schema_conn.autocommit = True
                with schema_conn.cursor() as cur:
                    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
                    print(f"[deploy] Schema '{schema}' ensured.")
                schema_conn.close()
            except Exception as e:
                print(f"[deploy] Error creating schema: {e}")
                sys.exit(1)

    dev_url = "docker://postgres/15/dev?search_path=public"
    print(f"[deploy] Applying schema from {source_dir} to {target}")
    result = subprocess.run([
        "atlas", "schema", "apply",
        "--url", target,
        "--to", f"file://{source_dir.absolute()}",
        "--dev-url", dev_url
    ], capture_output=False)
    if result.returncode == 0:
        print("[deploy] ✅ Schema deployed successfully.")
    else:
        print("[deploy] ❌ Error deploying schema.")
        sys.exit(result.returncode)

    # Apply additional SQL files (prefix 500-999) manually
    sql_files = sorted([f for f in source_dir.glob("*.sql") if re.match(r"^(5[0-9]{2}|6[0-9]{2}|7[0-9]{2}|8[0-9]{2}|9[0-9]{2})_.*\.sql$", f.name)])
    print(f"[deploy] DEBUG: Found {len(sql_files)} files for manual deployment.")
    if sql_files:
        print(f"[deploy] Applying additional SQL files (500-999):")
        conn_str = f"host={host} port={port} dbname={dbname} user={user} password={password} sslmode=disable"
        try:
            conn = psycopg2.connect(conn_str)
            conn.autocommit = True
            with conn.cursor() as cur:
                for sql_file in sql_files:
                    print(f"  - {sql_file.name}")
                    try:
                        with open(sql_file, "r", encoding="utf-8") as f:
                            sql = f.read()
                        cur.execute(sql)
                        print(f"    ✅ Applied {sql_file.name}")
                    except Exception as e:
                        print(f"    ❌ Error applying {sql_file.name}: {e}")
                        conn.close()
                        sys.exit(1)
            conn.close()
        except Exception as e:
            print(f"[deploy] Error connecting to database for manual SQL file deployment: {e}")
            sys.exit(1)
    else:
        print(f"[deploy] No additional SQL files (500-999) found for manual deployment.")
