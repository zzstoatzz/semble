# run tests
test:
    uv run pytest tests/ -x

# format and lint
fmt:
    uv run ruff format src/ tests/
    uv run ruff check src/ tests/ --fix

# type check
check:
    uv run ty check
