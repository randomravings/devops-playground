#!/usr/bin/env python3
"""Run sqlfluff against a directory using an additional config file.

This module provides a programmatic `run_sqlfluff` function and a simple CLI entrypoint.

Behavior:
- If `config` is provided, pass it to sqlfluff via `--config`.
- Runs `sqlfluff lint` by default, or `sqlfluff fix` when `fix=True`.
- Returns the subprocess return code.
"""
import argparse
import subprocess
import pathlib
import sys


def run_sqlfluff(target_dir: pathlib.Path, config: pathlib.Path | None = None, fix: bool = False, dialect: str | None = None) -> int:
    """Run sqlfluff lint (or fix) on target_dir using optional config file.

    Returns the subprocess return code (0 = success).
    """
    if not target_dir.exists():
        print(f"[sqlfluff_runner] target directory {target_dir} does not exist; skipping.")
        return 0

    cmd = [sys.executable, "-m", "sqlfluff", "lint"]
    if fix:
        cmd = [sys.executable, "-m", "sqlfluff", "fix", "--force"]
    if config is not None:
        cmd += ["--config", str(config)]
    if dialect is not None:
        cmd += ["--dialect", dialect]

    # target directory (sqlfluff accepts dirs)
    cmd.append(str(target_dir))

    print(f"[sqlfluff_runner] running: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    return res.returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run sqlfluff lint or fix on a directory with optional config")
    ap.add_argument("dir", nargs="?", default="db/schema", help="Directory containing SQL files (default: db/schema)")
    ap.add_argument("--config", help="Path to an additional sqlfluff config file to use")
    ap.add_argument("--fix", action="store_true", help="Run sqlfluff fix instead of lint")
    ap.add_argument("--dialect", help="SQL dialect to pass to sqlfluff (optional)")
    args = ap.parse_args(argv)

    target = pathlib.Path(args.dir)
    cfg = pathlib.Path(args.config) if args.config else None
    rc = run_sqlfluff(target, config=cfg, fix=args.fix, dialect=args.dialect)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
