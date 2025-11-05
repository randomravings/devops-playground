# ETL Framework Recipes

## The 4 Commands

Run from framework directory, targeting your ETL project:

```bash
cd etl-framework

# 1. Setup environment
./run.sh setup --project-dir ../demo-etl --warehouse csv

# 2. Run for specific date
./run.sh run --project-dir ../demo-etl -d 2024-02-01

# 3. Run tests
./run.sh test --project-dir ../demo-etl

# 4. Teardown
./run.sh teardown --project-dir ../demo-etl --force
```
