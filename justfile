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

# install the Pi eval harness
[working-directory: 'evals']
evals-install:
    npm ci

# run the Pi harness; arguments pass through (e.g. run reading-recommendation library-filing)
[working-directory: 'evals']
[positional-arguments]
evals *args:
    node --env-file-if-exists=../.env --import tsx src/cli.ts "$@"

# type check and test the Pi harness without inference calls
[working-directory: 'evals']
evals-check:
    npm run check
    npm test

# check the configured judge against regression cases (uses inference)
[working-directory: 'evals']
evals-judge-check:
    SEMBLE_LIVE_JUDGE_TEST=1 node --env-file-if-exists=../.env --import tsx --test src/judge.test.ts
