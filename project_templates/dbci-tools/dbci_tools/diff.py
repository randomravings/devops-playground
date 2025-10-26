#!/usr/bin/env python3
import argparse, pathlib, subprocess, json, shutil
from typing import Dict

def check_atlas_available() -> bool:
    """Check if Atlas CLI is available in PATH."""
    return shutil.which("atlas") is not None

def run_atlas_diff(dir_a: pathlib.Path, dir_b: pathlib.Path, dev_url: str = None) -> str:
    """
    Run Atlas schema diff between two directories.
    Returns the raw Atlas output (migration SQL).
    
    Handles the special case where dir_a is empty (no schema in baseline).
    Uses ATLAS_DEV_URL env var if dev_url not provided, defaults to docker://postgres.
    """
    import os
    
    if dev_url is None:
        dev_url = os.getenv("ATLAS_DEV_URL", "docker://postgres/15/dev?search_path=public")
    
    # Check if dir_a is empty - if so, we need to handle specially
    dir_a_files = list(dir_a.glob("*.sql"))
    dir_a_is_empty = len(dir_a_files) == 0
    
    if dir_a_is_empty:
        # Create a minimal empty schema file so Atlas can process it
        print(f"[diff] Source directory is empty, creating baseline placeholder...")
        empty_schema_file = dir_a / ".empty_schema.sql"
        empty_schema_file.write_text("-- Empty baseline schema\n", encoding="utf-8")
    
    cmd = [
        "atlas", "schema", "diff",
        "--from", f"file://{dir_a.absolute()}",
        "--to", f"file://{dir_b.absolute()}",
        "--dev-url", dev_url
    ]
    
    print(f"[diff] Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        # Clean up the placeholder file if we created it
        if dir_a_is_empty:
            empty_schema_file = dir_a / ".empty_schema.sql"
            if empty_schema_file.exists():
                empty_schema_file.unlink()
        
        # Atlas returns migration SQL in stdout
        # Exit code 0 = no changes or successful diff
        # Exit code 1 = changes found (this is actually what we want)
        # Exit code 2+ = actual errors
        
        if result.returncode > 1:
            print(f"[diff] Error: Atlas returned exit code {result.returncode}")
            if result.stderr:
                print(f"[diff] Atlas stderr: {result.stderr}")
            raise Exception(f"Atlas diff failed: {result.stderr}")
        
        return result.stdout
        
    except Exception as e:
        print(f"[diff] Error running Atlas: {e}")
        raise

def analyze_atlas_output(atlas_output: str) -> Dict:
    """
    Analyze Atlas migration SQL output to extract changes.
    Returns a dictionary with schema change information.
    """
    changes = {
        'tables': {
            'dropped': [],
            'created': []
        },
        'columns': {
            'dropped': {},
            'created': {}
        },
        'other_changes': []
    }
    
    if not atlas_output or atlas_output.strip() == "Schemas are synced, no changes to be made.":
        return changes
    
    lines = atlas_output.strip().split('\n')
    
    for line in lines:
        line_upper = line.strip().upper()
        
        # Detect table drops
        if line_upper.startswith('DROP TABLE'):
            # Extract table name: DROP TABLE `users` or DROP TABLE IF EXISTS `users`
            parts = line.split()
            for i, part in enumerate(parts):
                if part.upper() == 'TABLE':
                    if i + 1 < len(parts):
                        table_name = parts[i + 1].strip('`;,')
                        if table_name.upper() not in ('IF', 'EXISTS'):
                            changes['tables']['dropped'].append(table_name)
                            break
                    elif i + 3 < len(parts):  # IF EXISTS case
                        table_name = parts[i + 3].strip('`;,')
                        changes['tables']['dropped'].append(table_name)
                        break
        
        # Detect table creates
        elif line_upper.startswith('CREATE TABLE'):
            parts = line.split()
            for i, part in enumerate(parts):
                if part.upper() == 'TABLE':
                    if i + 1 < len(parts):
                        table_name = parts[i + 1].strip('`;,(')
                        if table_name.upper() not in ('IF', 'NOT', 'EXISTS'):
                            changes['tables']['created'].append(table_name)
                            break
        
        # Detect column drops
        elif 'DROP COLUMN' in line_upper:
            # ALTER TABLE `users` DROP COLUMN `old_column`
            parts = line.split()
            table_name = None
            for i, part in enumerate(parts):
                if part.upper() == 'TABLE':
                    if i + 1 < len(parts):
                        table_name = parts[i + 1].strip('`;,')
                        break
            
            for i, part in enumerate(parts):
                if part.upper() == 'COLUMN':
                    if i + 1 < len(parts):
                        column_name = parts[i + 1].strip('`;,')
                        if table_name:
                            if table_name not in changes['columns']['dropped']:
                                changes['columns']['dropped'][table_name] = []
                            changes['columns']['dropped'][table_name].append(column_name)
                        break
        
        # Detect column adds
        elif 'ADD COLUMN' in line_upper:
            # ALTER TABLE `users` ADD COLUMN `new_column` TEXT
            parts = line.split()
            table_name = None
            for i, part in enumerate(parts):
                if part.upper() == 'TABLE':
                    if i + 1 < len(parts):
                        table_name = parts[i + 1].strip('`;,')
                        break
            
            for i, part in enumerate(parts):
                if part.upper() == 'COLUMN':
                    if i + 1 < len(parts):
                        column_name = parts[i + 1].strip('`;,')
                        if table_name:
                            if table_name not in changes['columns']['created']:
                                changes['columns']['created'][table_name] = []
                            changes['columns']['created'][table_name].append(column_name)
                        break
        
        # Capture other changes (ALTER, MODIFY, etc.)
        elif line.strip() and not line.strip().startswith('--'):
            if any(keyword in line_upper for keyword in ['ALTER', 'MODIFY', 'RENAME', 'INDEX', 'CONSTRAINT']):
                changes['other_changes'].append(line.strip())
    
    return changes

def generate_atlas_report(atlas_output: str, changes: Dict, output_file: pathlib.Path):
    """Generate a human-readable schema changes report from Atlas output."""
    report_lines = []
    report_lines.append("# Schema Changes Report (Atlas)")
    report_lines.append("")
    report_lines.append("Generated using Atlas CLI for accurate schema comparison.")
    report_lines.append("")
    
    # Check if there are any changes
    has_changes = (
        changes['tables']['dropped'] or 
        changes['tables']['created'] or 
        changes['columns']['dropped'] or 
        changes['columns']['created'] or
        changes['other_changes']
    )
    
    if not has_changes:
        report_lines.append("**No schema changes detected.**")
        report_lines.append("")
        report_lines.append("The schemas are synchronized.")
    else:
        # Table changes
        if changes['tables']['dropped'] or changes['tables']['created']:
            report_lines.append("## Table Changes")
            report_lines.append("")
            
            if changes['tables']['dropped']:
                report_lines.append("### Dropped Tables")
                for table in sorted(changes['tables']['dropped']):
                    report_lines.append(f"- ⚠️ `{table}`")
                report_lines.append("")
            
            if changes['tables']['created']:
                report_lines.append("### Created Tables")
                for table in sorted(changes['tables']['created']):
                    report_lines.append(f"+ ✅ `{table}`")
                report_lines.append("")
        
        # Column changes
        if changes['columns']['dropped'] or changes['columns']['created']:
            report_lines.append("## Column Changes")
            report_lines.append("")
            
            if changes['columns']['dropped']:
                report_lines.append("### Dropped Columns")
                for table in sorted(changes['columns']['dropped'].keys()):
                    columns = changes['columns']['dropped'][table]
                    report_lines.append(f"**`{table}`**:")
                    for column in sorted(columns):
                        report_lines.append(f"  - ⚠️ `{column}`")
                report_lines.append("")
            
            if changes['columns']['created']:
                report_lines.append("### Created Columns")
                for table in sorted(changes['columns']['created'].keys()):
                    columns = changes['columns']['created'][table]
                    report_lines.append(f"**`{table}`**:")
                    for column in sorted(columns):
                        report_lines.append(f"  + ✅ `{column}`")
                report_lines.append("")
        
        # Other changes (constraints, indexes, etc.)
        if changes['other_changes']:
            report_lines.append("## Other Changes")
            report_lines.append("")
            report_lines.append("Additional modifications detected (constraints, indexes, column types, etc.):")
            report_lines.append("")
            for change in changes['other_changes'][:10]:  # Limit to first 10
                report_lines.append(f"- `{change}`")
            if len(changes['other_changes']) > 10:
                report_lines.append(f"- ... and {len(changes['other_changes']) - 10} more changes")
            report_lines.append("")
    
    # Write report
    report_file = output_file.with_suffix('.schema-report.md')
    report_file.write_text("\n".join(report_lines), encoding="utf-8")
    
    # Write JSON summary
    json_file = output_file.with_suffix('.schema-changes.json')
    json_file.write_text(json.dumps(changes, indent=2), encoding="utf-8")
    
    print(f"[diff] Schema report written to: {report_file}")
    print(f"[diff] Schema changes JSON written to: {json_file}")
    
    return changes

def main():
    ap = argparse.ArgumentParser(
        description="Generate schema diff between two SQL directories using Atlas CLI",
        epilog="Atlas CLI must be installed and available in PATH."
    )
    ap.add_argument("dir_a", help="First directory containing SQL files (e.g., main branch)")
    ap.add_argument("dir_b", help="Second directory containing SQL files (e.g., current branch)")
    ap.add_argument("-o", "--output", default="atlas.migration.sql", 
                    help="Output file for Atlas migration SQL")
    ap.add_argument("--dev-url", default=None,
                    help="PostgreSQL dev database URL (defaults to trying postgres-dev then docker://)")
    ap.add_argument("--schema-analysis", action="store_true", 
                    help="Generate additional schema analysis reports (JSON + markdown)")
    ap.add_argument("--fail-on-drops", action="store_true",
                    help="Exit with failure code if any tables or columns are dropped")
    args = ap.parse_args()

    # Check if Atlas is available
    if not check_atlas_available():
        print("[diff] ERROR: Atlas CLI is not installed or not in PATH")
        print("[diff] Install Atlas: curl -sSf https://atlasgo.sh | sh")
        return 1

    dir_a = pathlib.Path(args.dir_a)
    dir_b = pathlib.Path(args.dir_b)
    output_file = pathlib.Path(args.output)

    # Validate that both directories exist
    if not dir_a.exists():
        print(f"[diff] Error: Directory A does not exist: {dir_a}")
        return 1
    
    if not dir_b.exists():
        print(f"[diff] Error: Directory B does not exist: {dir_b}")
        return 1

    # Create output directory if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Run Atlas schema diff
        print(f"[diff] Comparing schemas using Atlas...")
        print(f"[diff]   FROM: {dir_a}")
        print(f"[diff]   TO:   {dir_b}")
        print(f"[diff]   DEV:  {args.dev_url}")
        
        atlas_output = run_atlas_diff(dir_a, dir_b, args.dev_url)
        
        # Save the migration SQL
        output_file.write_text(atlas_output, encoding="utf-8")
        print(f"[diff] Migration SQL written to: {output_file}")
        
        # Analyze the output for structured information
        changes = analyze_atlas_output(atlas_output)
        
        # Generate reports if requested
        if args.schema_analysis:
            generate_atlas_report(atlas_output, changes, output_file)
        
        # Print summary to console
        dropped_table_count = len(changes['tables']['dropped'])
        created_table_count = len(changes['tables']['created'])
        dropped_col_count = sum(len(cols) for cols in changes['columns']['dropped'].values())
        created_col_count = sum(len(cols) for cols in changes['columns']['created'].values())
        other_changes_count = len(changes['other_changes'])
        
        if dropped_table_count or created_table_count:
            print(f"[diff] Tables - Dropped: {dropped_table_count}, Created: {created_table_count}")
        
        if dropped_col_count or created_col_count:
            print(f"[diff] Columns - Dropped: {dropped_col_count}, Created: {created_col_count}")
        
        if other_changes_count:
            print(f"[diff] Other changes: {other_changes_count} (constraints, indexes, types, etc.)")
        
        if not (dropped_table_count or created_table_count or dropped_col_count or created_col_count or other_changes_count):
            print("[diff] ✅ No schema changes detected - schemas are synchronized")
        
        # Check for drops and fail if requested
        if args.fail_on_drops:
            has_drops = dropped_table_count > 0 or dropped_col_count > 0
            if has_drops:
                print(f"[diff] ❌ ERROR: Detected {dropped_table_count} dropped table(s) and {dropped_col_count} dropped column(s)")
                if changes['tables']['dropped']:
                    print(f"[diff] Dropped tables: {', '.join(changes['tables']['dropped'])}")
                if changes['columns']['dropped']:
                    for table, columns in changes['columns']['dropped'].items():
                        print(f"[diff] Dropped columns in {table}: {', '.join(sorted(columns))}")
                return 1
            else:
                print("[diff] ✅ No drops detected - validation passed")
        
        return 0
        
    except Exception as e:
        print(f"[diff] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
