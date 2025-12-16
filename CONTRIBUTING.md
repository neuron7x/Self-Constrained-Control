# Contributing

## Development setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,sim]"
pre-commit install
```

## Quality gates
```bash
ruff check .
ruff format .
mypy src
pytest
```

## PR expectations
- Small, reviewable changes
- Tests for bugfixes/features
- No breaking public API without a version bump and changelog note
