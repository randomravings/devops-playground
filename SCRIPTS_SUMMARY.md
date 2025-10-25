# Virtual Environment Scripts

Simplified virtual environment management for the devops_tools package.

## 📜 Scripts

### env_setup.sh

Creates virtual environment and installs the package:

```bash
./env_setup.sh
```

**What it does:**

- Creates `.venv/` directory with Python virtual environment
- Upgrades pip to latest version
- Installs `devops_tools` package in editable mode

### env_cleanup.sh

Removes virtual environment and build artifacts:

```bash
./env_cleanup.sh
```

**What it does:**

- Removes `.venv/` directory
- Removes build artifacts (`devops_tools.egg-info`, `build/`, `dist/`)
- Removes Python cache files (`__pycache__/`, `*.pyc`)

## 💡 Usage Pattern

```bash
./env_setup.sh                      # One-time setup
source .venv/bin/activate           # Activate venv
python examples/full_setup.py       # Run example scripts
devops-tools --help                 # Use CLI
deactivate                          # Exit venv
./env_cleanup.sh                    # Remove everything
```

## 🔄 Changes from Previous Version

**Removed:**
- `Makefile` - Redundant with shell scripts
- `run.py` - Users should directly run examples with activated venv
- `make setup`, `make install`, `make clean` commands

**Simplified:**
- `env_setup.sh` - Focused only on venv creation and package installation
- Added `env_cleanup.sh` - Single script for complete cleanup

## 🎯 Design Philosophy

**Single Responsibility:**
- `env_setup.sh` → Create and configure venv
- `env_cleanup.sh` → Remove venv and artifacts
- Examples should be run directly after activating venv

**No Overlap:**
- No duplicate functionality between scripts
- Clear separation of concerns
- Simple, focused tools

**Direct Execution:**
- Activate venv once, run multiple scripts
- No wrapper scripts needed
- Standard Python workflow
