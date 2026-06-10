# run tests
test:
    uv run pytest -x

# format and lint
fmt:
    uv run ruff format src/ tests/ semble-mcp/
    uv run ruff check src/ tests/ semble-mcp/ --fix

# type check
check:
    uv run ty check
