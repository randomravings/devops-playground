#!/usr/bin/env python3
import argparse, pathlib, subprocess, tempfile, shutil

def run_pg_format(path: pathlib.Path):
    subprocess.run(["pg_format", "-i", str(path)], check=True)

def collapse_blank_lines(path: pathlib.Path):
    txt = path.read_text(encoding="utf-8", errors="ignore")
    out = []
    blank = 0
    for line in txt.splitlines():
        line = line.rstrip()
        if line == "":
            blank += 1
        else:
            blank = 0
        if blank < 2:
            out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")

def main():
    ap = argparse.ArgumentParser(description="Normalize SQL files from source directory to output directory")
    ap.add_argument("source", nargs="?", default="db/schema", help="Source directory containing SQL files")
    ap.add_argument("-o", "--output", required=True, help="Output directory for normalized files")
    args = ap.parse_args()

    source_dir = pathlib.Path(args.source)
    output_dir = pathlib.Path(args.output)
    
    # If the source directory doesn't exist yet (initial commit), exit quietly.
    if not source_dir.exists():
        print(f"[normalize] source directory {source_dir} does not exist")
        return 0

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(source_dir.glob("*.sql"))
    if not files:
        print(f"[normalize] no .sql files in {source_dir}")
        return 0

    for source_file in files:
        # Copy file to output directory
        output_file = output_dir / source_file.name
        shutil.copy2(source_file, output_file)
        
        # Normalize the copied file
        run_pg_format(output_file)
        collapse_blank_lines(output_file)

    print(f"[normalize] normalized {len(files)} files from {source_dir} to {output_dir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
