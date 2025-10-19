# Pull Request

## Summary
- Describe the change and why it’s needed.

## Checklist
- [ ] CI parity: local ruff/black checks match CI
  - Lint: `ruff check .` (non-blocking in CI), `black --check .`
- [ ] Tests executed locally (or appropriate subset)
  - `pytest -q tests/test_config.py tests/test_db.py tests/test_models.py tests/test_parsers.py`
- [ ] Documentation kept in sync
  - If commands or workflows changed, update `/WARP.md` (and keep `docs/WARP.md` pointer intact)
  - If CLI behavior changed, update `docs/QUICKSTART_CLI.md` and `docs/CLI_GUIDE.md`

## Links
- Quickstart: `docs/QUICKSTART.md`
- CLI Quickstart: `docs/QUICKSTART_CLI.md`
- CLI Guide: `docs/CLI_GUIDE.md`
- Database/Testing: `docs/DATABASE_AND_TESTING.md`
- Warp guidance: `/WARP.md`
