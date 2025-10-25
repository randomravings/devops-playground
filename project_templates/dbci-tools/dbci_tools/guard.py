#!/usr/bin/env python3
import sys, re, pathlib, argparse

RULES = [
    {"name":"raw_drop_table",
     "pattern": r"(?is)\bDROP\s+TABLE\b(?!\s+IF\s+EXISTS)",
     "message":"Use 'DROP TABLE IF EXISTS' or avoid raw table drops."},
    {"name":"alter_drop_column",
     "pattern": r"(?is)\bALTER\s+TABLE\b.*?\bDROP\s+COLUMN\b",
     "message":"Dropping columns is destructive\u2014gate behind review."},
    {"name":"raw_drop_schema",
     "pattern": r"(?is)\bDROP\s+SCHEMA\b(?!\s+IF\s+EXISTS)",
     "message":"Use 'DROP SCHEMA IF EXISTS' and handle carefully."},
    {"name":"create_no_if_not_exists",
     "pattern": r"(?is)\bCREATE\s+(TABLE|INDEX|SEQUENCE|VIEW|SCHEMA)\b(?![^;]*\bIF\s+NOT\s+EXISTS\b)",
     "message":"Prefer 'IF NOT EXISTS' for idempotency."},
]

ALLOW = re.compile(r"(?im)^\s*--\s*ALLOW:(\w+)\s*$")

def check_text(text: str):
    allowed = set(m.group(1).lower() for m in ALLOW.finditer(text))
    violations = []
    for r in RULES:
        if r["name"] in allowed:
            continue
        if re.search(r["pattern"], text):
            violations.append((r["name"], r["message"]))
    return violations

def main():
    ap = argparse.ArgumentParser(description="Run DDL guard checks against SQL files in a directory")
    ap.add_argument("dir", nargs="?", default="db/schema", help="directory containing .sql files (default: db/schema)")
    args = ap.parse_args()

    base = pathlib.Path(args.dir)
    # If the directory doesn't exist yet (initial commit), exit quietly.
    if not base.exists():
        return 0

    files = sorted(base.glob("*.sql"))
    if not files:
        print(f"[ddl_guard] no .sql files in {base}")
        return 0

    failed = False
    for f in files:
        v = check_text(f.read_text(encoding="utf-8", errors="ignore"))
        if v:
            failed = True
            print(f"\n[ddl_guard] {f.name}:")
            for name, msg in v:
                print(f"  - {name}: {msg}")
            print("  (Add `-- ALLOW:rule_name` above a reviewed statement to bypass.)")

    if failed:
        print("\n[ddl_guard] \u274c Guardrails failed.")
        return 1

    print("[ddl_guard] \u2705 All checks passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
