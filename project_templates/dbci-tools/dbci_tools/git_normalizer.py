#!/usr/bin/env python3
import argparse
import pathlib
import subprocess
import tempfile
import shutil
from .normalizer import run_pg_format, collapse_blank_lines


def git_checkout_and_normalize(repo_path: pathlib.Path, target_dir: pathlib.Path, source_subdir: str = "db/schema", branch: str = "origin/main"):
    """
    Checkout a specific branch from the current repository and normalize SQL files to target directory.
    Always creates the target directory, even if no schema exists (for empty baseline comparisons).
    
    Args:
        repo_path: Path to the git repository (project root)
        target_dir: Target directory for normalized files
        source_subdir: Subdirectory within the repo containing SQL files
        branch: Git branch/ref to checkout (default: origin/main)
    """
    # Always create target directory (even if empty for degenerate case)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[git-normalize] Fetching {branch} schema from {repo_path}...")
    
    # Extract just the branch name (e.g., "origin/main" -> "main")
    if "/" in branch:
        remote, branch_name = branch.split("/", 1)
    else:
        remote = "origin"
        branch_name = branch
    
    # Fetch the specific branch we need
    print(f"[git-normalize] Fetching {remote}/{branch_name}...")
    fetch_result = subprocess.run([
        "git", "-C", str(repo_path), 
        "fetch", "--depth=1", "--no-tags", remote, f"{branch_name}:refs/remotes/{remote}/{branch_name}"
    ], capture_output=True, text=True, check=False)
    
    if fetch_result.returncode != 0:
        print(f"[git-normalize] Warning: git fetch failed: {fetch_result.stderr.strip()}")
        # Try without refspec in case the branch is already there
        fetch_result = subprocess.run([
            "git", "-C", str(repo_path), 
            "fetch", "--depth=1", "--no-tags", remote, branch_name
        ], capture_output=True, text=True, check=False)
    
    # Use the full ref path
    ref = f"{remote}/{branch_name}"
    
    # Check if the source directory exists in the branch
    try:
        result = subprocess.run([
            "git", "-C", str(repo_path), "ls-tree", ref, source_subdir
        ], capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            print(f"[git-normalize] No {source_subdir} found in {ref} (empty or initial commit)")
            print(f"[git-normalize] Created empty target directory: {target_dir}")
            return 0
            
    except Exception as e:
        print(f"[git-normalize] Error checking branch {branch}: {e}")
        print(f"[git-normalize] Created empty target directory: {target_dir}")
        return 0
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        checkout_dir = tmp_path / "checkout"
        checkout_dir.mkdir()
        
        # Checkout the specific files using git archive (cleaner than checkout)
        try:
            # Use git archive to extract files from the ref
            archive_result = subprocess.run([
                "git", "-C", str(repo_path),
                "archive", ref, source_subdir
            ], capture_output=True, check=True)
            
            # Extract the tar archive to checkout_dir
            subprocess.run([
                "tar", "-x", "-C", str(checkout_dir)
            ], input=archive_result.stdout, check=True)
            
        except subprocess.CalledProcessError as e:
            print(f"[git-normalize] Failed to extract {source_subdir} from {ref}: {e}")
            print(f"[git-normalize] Created empty target directory: {target_dir}")
            return 0
        
        # Find SQL files in the checked out subdirectory
        source_dir = checkout_dir / source_subdir
        
        if not source_dir.exists():
            print(f"[git-normalize] Source directory {source_subdir} not found after checkout")
            print(f"[git-normalize] Created empty target directory: {target_dir}")
            return 0
        
        files = sorted(source_dir.glob("*.sql"))
        if not files:
            print(f"[git-normalize] No .sql files found in {source_dir}")
            print(f"[git-normalize] Created empty target directory: {target_dir}")
            return 0
        
        print(f"[git-normalize] Found {len(files)} SQL files, normalizing to {target_dir}...")
        
        for source_file in files:
            # Copy file to target directory
            target_file = target_dir / source_file.name
            shutil.copy2(source_file, target_file)
            
            # Normalize the copied file
            run_pg_format(target_file)
            collapse_blank_lines(target_file)
        
        print(f"[git-normalize] Successfully normalized {len(files)} files from {ref} to {target_dir}")
        return len(files)


def main():
    ap = argparse.ArgumentParser(description="Checkout git branch and normalize SQL files to target directory")
    ap.add_argument("repo_path", nargs="?", default=".", help="Path to git repository (default: current directory)")
    ap.add_argument("-o", "--output", required=True, help="Target directory for normalized files")
    ap.add_argument("-s", "--source-dir", default="db/schema", 
                    help="Subdirectory within repo containing SQL files (default: db/schema)")
    ap.add_argument("-b", "--branch", default="origin/main", 
                    help="Git branch/ref to checkout (default: origin/main)")
    
    args = ap.parse_args()
    
    repo_path = pathlib.Path(args.repo_path)
    target_dir = pathlib.Path(args.output)
    source_subdir = args.source_dir
    branch = args.branch
    
    try:
        git_checkout_and_normalize(repo_path, target_dir, source_subdir, branch)
        return 0
    except subprocess.CalledProcessError as e:
        print(f"[git-normalize] Error: Git operation failed: {e}")
        return 1
    except Exception as e:
        print(f"[git-normalize] Error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())