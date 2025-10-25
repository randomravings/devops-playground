#!/usr/bin/env python3
import argparse, pathlib, subprocess, re, json
from typing import Dict, Set, List, Tuple

def parse_table_schema(sql_content: str) -> Dict[str, Set[str]]:
    """
    Parse SQL content and extract table names and their columns.
    Returns a dictionary where keys are table names and values are sets of column names.
    """
    tables = {}
    
    # Remove comments and normalize whitespace
    sql_content = re.sub(r'--.*?\n', '\n', sql_content)
    sql_content = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)
    
    # Find CREATE TABLE statements
    create_table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:`?(\w+)`?|\[(\w+)\]|"?(\w+)"?)\s*\((.*?)\);'
    
    for match in re.finditer(create_table_pattern, sql_content, re.IGNORECASE | re.DOTALL):
        # Get table name from one of the capture groups
        table_name = match.group(1) or match.group(2) or match.group(3)
        table_def = match.group(4)
        
        if table_name and table_def:
            columns = set()
            
            # Split table definition by commas, but be careful with nested parentheses
            parts = []
            paren_depth = 0
            current_part = ""
            
            for char in table_def:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                elif char == ',' and paren_depth == 0:
                    parts.append(current_part.strip())
                    current_part = ""
                    continue
                current_part += char
            
            if current_part.strip():
                parts.append(current_part.strip())
            
            # Extract column names from each part
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                
                # Skip constraints (PRIMARY KEY, FOREIGN KEY, CHECK, etc.)
                if re.match(r'^\s*(PRIMARY\s+KEY|FOREIGN\s+KEY|CHECK|CONSTRAINT|INDEX|KEY|UNIQUE)', part, re.IGNORECASE):
                    continue
                
                # Extract column name (first word, handling quotes/backticks)
                column_match = re.match(r'^\s*(?:`?(\w+)`?|\[(\w+)\]|"?(\w+)"?)', part)
                if column_match:
                    column_name = column_match.group(1) or column_match.group(2) or column_match.group(3)
                    if column_name:
                        columns.add(column_name.lower())
            
            tables[table_name.lower()] = columns
    
    return tables

def analyze_schema_changes(dir_a: pathlib.Path, dir_b: pathlib.Path) -> Dict:
    """
    Analyze schema changes between two directories of SQL files.
    Returns a dictionary with dropped/created tables and columns.
    """
    def get_schema_from_dir(dir_path: pathlib.Path) -> Dict[str, Set[str]]:
        all_tables = {}
        files = sorted(dir_path.glob("*.sql"))
        
        for sql_file in files:
            content = sql_file.read_text(encoding="utf-8", errors="ignore")
            tables = parse_table_schema(content)
            all_tables.update(tables)
        
        return all_tables
    
    schema_a = get_schema_from_dir(dir_a)
    schema_b = get_schema_from_dir(dir_b)
    
    tables_a = set(schema_a.keys())
    tables_b = set(schema_b.keys())
    
    # Table changes
    dropped_tables = tables_a - tables_b
    created_tables = tables_b - tables_a
    common_tables = tables_a & tables_b
    
    # Column changes for common tables
    dropped_columns = {}
    created_columns = {}
    
    for table in common_tables:
        cols_a = schema_a.get(table, set())
        cols_b = schema_b.get(table, set())
        
        dropped_cols = cols_a - cols_b
        created_cols = cols_b - cols_a
        
        if dropped_cols:
            dropped_columns[table] = dropped_cols
        if created_cols:
            created_columns[table] = created_cols
    
    return {
        'tables': {
            'dropped': sorted(dropped_tables),
            'created': sorted(created_tables)
        },
        'columns': {
            'dropped': {table: sorted(cols) for table, cols in dropped_columns.items()},
            'created': {table: sorted(cols) for table, cols in created_columns.items()}
        }
    }

def extract_create_statements(dir_path: pathlib.Path, table_names: Set[str]) -> Dict[str, str]:
    """Extract CREATE TABLE statements for specific tables from SQL files."""
    create_statements = {}
    
    if not dir_path.exists():
        return create_statements
        
    files = sorted(dir_path.glob("*.sql"))
    
    for sql_file in files:
        content = sql_file.read_text(encoding="utf-8", errors="ignore")
        
        # Remove comments but preserve the structure
        content_lines = content.split('\n')
        clean_content = []
        for line in content_lines:
            # Remove single-line comments but keep the line structure
            line_clean = re.sub(r'--.*$', '', line)
            clean_content.append(line_clean)
        
        content = '\n'.join(clean_content)
        
        # Find CREATE TABLE statements for our target tables
        create_table_pattern = r'(CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:`?(\w+)`?|\[(\w+)\]|"?(\w+)"?)\s*\([^;]*\);)'
        
        for match in re.finditer(create_table_pattern, content, re.IGNORECASE | re.DOTALL):
            full_statement = match.group(1).strip()
            table_name = (match.group(2) or match.group(3) or match.group(4) or '').lower()
            
            if table_name in table_names:
                create_statements[table_name] = full_statement
    
    return create_statements

def generate_change_script(changes: Dict, dir_b: pathlib.Path, output_file: pathlib.Path):
    """Generate SQL change script based on schema differences."""
    script_lines = []
    script_lines.append("-- Schema Change Script")
    script_lines.append("-- Generated automatically from schema diff analysis")
    script_lines.append("")
    
    # Drop columns first (before dropping tables)
    if changes['columns']['dropped']:
        script_lines.append("-- Drop columns")
        for table, columns in changes['columns']['dropped'].items():
            for column in sorted(columns):
                script_lines.append(f"ALTER TABLE {table} DROP COLUMN {column};")
        script_lines.append("")
    
    # Drop tables
    if changes['tables']['dropped']:
        script_lines.append("-- Drop tables")
        for table in sorted(changes['tables']['dropped']):
            script_lines.append(f"DROP TABLE IF EXISTS {table};")
        script_lines.append("")
    
    # Create tables with actual CREATE statements
    if changes['tables']['created']:
        script_lines.append("-- Create tables")
        
        # Extract actual CREATE statements from the new schema files
        created_table_names = set(changes['tables']['created'])
        create_statements = extract_create_statements(dir_b, created_table_names)
        
        for table in sorted(changes['tables']['created']):
            if table in create_statements:
                script_lines.append(create_statements[table])
            else:
                script_lines.append(f"-- CREATE TABLE {table} (...); -- NOTE: Statement not found, define manually")
            script_lines.append("")
    
    # Add columns
    if changes['columns']['created']:
        script_lines.append("-- Add columns")
        script_lines.append("-- NOTE: Column definitions need to be manually specified")
        for table, columns in changes['columns']['created'].items():
            for column in sorted(columns):
                script_lines.append(f"-- ALTER TABLE {table} ADD COLUMN {column} <TYPE>;")
        script_lines.append("")
    
    if not any([changes['tables']['dropped'], changes['tables']['created'], 
                changes['columns']['dropped'], changes['columns']['created']]):
        script_lines.append("-- No schema changes detected")
    
    # Write change script
    script_file = output_file.with_suffix('.change-script.sql')
    script_file.write_text("\n".join(script_lines), encoding="utf-8")
    
    print(f"[diff] Change script written to: {script_file}")
    return script_file

def generate_schema_report(changes: Dict, output_file: pathlib.Path):
    """Generate a human-readable schema changes report."""
    report_lines = []
    report_lines.append("# Schema Changes Report")
    report_lines.append("")
    
    # Table changes
    if changes['tables']['dropped'] or changes['tables']['created']:
        report_lines.append("## Table Changes")
        report_lines.append("")
        
        if changes['tables']['dropped']:
            report_lines.append("### Dropped Tables")
            for table in changes['tables']['dropped']:
                report_lines.append(f"- {table}")
            report_lines.append("")
        
        if changes['tables']['created']:
            report_lines.append("### Created Tables")
            for table in changes['tables']['created']:
                report_lines.append(f"+ {table}")
            report_lines.append("")
    
    # Column changes
    if changes['columns']['dropped'] or changes['columns']['created']:
        report_lines.append("## Column Changes")
        report_lines.append("")
        
        if changes['columns']['dropped']:
            report_lines.append("### Dropped Columns")
            for table, columns in changes['columns']['dropped'].items():
                report_lines.append(f"**{table}**:")
                for column in columns:
                    report_lines.append(f"  - {column}")
            report_lines.append("")
        
        if changes['columns']['created']:
            report_lines.append("### Created Columns")
            for table, columns in changes['columns']['created'].items():
                report_lines.append(f"**{table}**:")
                for column in columns:
                    report_lines.append(f"  + {column}")
            report_lines.append("")
    
    if not any([changes['tables']['dropped'], changes['tables']['created'], 
                changes['columns']['dropped'], changes['columns']['created']]):
        report_lines.append("No schema changes detected.")
    
    # Write report
    report_file = output_file.with_suffix('.schema-report.md')
    report_file.write_text("\n".join(report_lines), encoding="utf-8")
    
    # Write JSON summary
    json_file = output_file.with_suffix('.schema-changes.json')
    json_file.write_text(json.dumps(changes, indent=2), encoding="utf-8")
    
    print(f"[diff] Schema report written to: {report_file}")
    print(f"[diff] Schema changes JSON written to: {json_file}")
    
    return changes

def concat_sorted_sql(dir_path: pathlib.Path, out_file: pathlib.Path):
    files = sorted(dir_path.glob("*.sql"))
    with out_file.open("w", encoding="utf-8") as w:
        for f in files:
            w.write(f"-- file: {f.name}\n")
            content = f.read_text(encoding="utf-8", errors="ignore")
            # Ensure each file ends with a single newline for predictable diffs
            if not content.endswith("\n"):
                content = content + "\n"
            w.write(content)

def run_diff(a: pathlib.Path, b: pathlib.Path, out: pathlib.Path):
    # unified diff via `diff -u`
    res = subprocess.run(["diff", "-u", str(a), str(b)], capture_output=True, text=True)
    out.write_text(res.stdout or "", encoding="utf-8")
    # don't fail the build on differences; just produce the artifact
    print(f"[diff] wrote {out} (A=main, B=current).")

def main():
    ap = argparse.ArgumentParser(description="Generate diff between two normalized SQL directories")
    ap.add_argument("dir_a", help="First directory containing normalized SQL files (e.g., main branch)")
    ap.add_argument("dir_b", help="Second directory containing normalized SQL files (e.g., current branch)")
    ap.add_argument("-o", "--output", default="normalized_structural.diff", 
                    help="Output file for the diff (default: normalized_structural.diff)")
    ap.add_argument("--schema-analysis", action="store_true", 
                    help="Generate schema change analysis (tables/columns dropped/created)")
    ap.add_argument("--generate-script", action="store_true",
                    help="Generate SQL change script from schema differences")
    ap.add_argument("--fail-on-drops", action="store_true",
                    help="Exit with failure code if any tables or columns are dropped")
    args = ap.parse_args()

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

    # Create temporary concatenated files for comparison
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as a_file, \
         tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as b_file:
        
        a_sql = pathlib.Path(a_file.name)
        b_sql = pathlib.Path(b_file.name)
        
        try:
            # Concatenate SQL files from both directories
            concat_sorted_sql(dir_a, a_sql)
            concat_sorted_sql(dir_b, b_sql)
            
            # Generate and save the diff
            run_diff(a_sql, b_sql, output_file)
            
            # Generate schema analysis if requested
            if args.schema_analysis or args.generate_script or args.fail_on_drops:
                print("[diff] Analyzing schema changes...")
                changes = analyze_schema_changes(dir_a, dir_b)
                
                if args.schema_analysis:
                    generate_schema_report(changes, output_file)
                
                if args.generate_script:
                    generate_change_script(changes, dir_b, output_file)
                
                # Print summary to console
                dropped_table_count = len(changes['tables']['dropped'])
                created_table_count = len(changes['tables']['created'])
                dropped_col_count = sum(len(cols) for cols in changes['columns']['dropped'].values())
                created_col_count = sum(len(cols) for cols in changes['columns']['created'].values())
                
                if dropped_table_count or created_table_count:
                    print(f"[diff] Tables - Dropped: {dropped_table_count}, Created: {created_table_count}")
                
                if dropped_col_count or created_col_count:
                    print(f"[diff] Columns - Dropped: {dropped_col_count}, Created: {created_col_count}")
                
                # Check for drops and fail if requested
                if args.fail_on_drops:
                    has_drops = dropped_table_count > 0 or dropped_col_count > 0
                    if has_drops:
                        print(f"[diff] ERROR: Detected {dropped_table_count} dropped table(s) and {dropped_col_count} dropped column(s)")
                        if changes['tables']['dropped']:
                            print(f"[diff] Dropped tables: {', '.join(changes['tables']['dropped'])}")
                        if changes['columns']['dropped']:
                            for table, columns in changes['columns']['dropped'].items():
                                print(f"[diff] Dropped columns in {table}: {', '.join(sorted(columns))}")
                        return 1
                    else:
                        print("[diff] No drops detected - validation passed")
            
            return 0
        finally:
            # Clean up temporary files
            a_sql.unlink(missing_ok=True)
            b_sql.unlink(missing_ok=True)

if __name__ == "__main__":
    raise SystemExit(main())
