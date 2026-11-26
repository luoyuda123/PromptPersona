# Changelog

Semantic versioning: major = behaviour change, minor = new features, patch = fixes only.

## Unreleased

Repository and release engineering only — the app behaviour is unchanged from `1.0.0`.

- Added a static landing page under `docs/` (GitHub Pages), plus Open Graph / Twitter card metadata
- `build-exe.yml` now publishes a GitHub Release on `v*` tags and writes `SHA256SUMS.txt` next to the exe; it also builds the portable zip
- Added `SECURITY.md` (private advisories), `CONTRIBUTING.md`, issue forms, a PR template and monthly Dependabot updates for GitHub Actions
- Added `pyproject.toml` (ruff, import sorting) and a lint job in CI
- Repository metadata: 18 topics, English description, Discussions enabled
- Removed internal design drafts from the public history working tree

## 1.0.0 (2026-11-25)

First usable release.

- 12-dimension questionnaire → persona with stable Chinese dimension labels (`persona.json`), plus a paste-ready Chinese system prompt (`persona_system.txt`)
- Ten interface languages: Simplified/Traditional Chinese, English, Japanese, Korean, French, Russian, Spanish, German, Arabic (RTL with mirrored panels and alignment)
- Language-aware catalog: built-in model suggestions are filtered by the current UI language, manual entries are unrestricted
- Model mounting: auto-discovery, manual add, reorder, enable/disable, connection test, clear
- Three execution strategies: poll (persisted cursor), parallel comparison (up to 8 workers), primary only
- OpenAI-compatible access (`POST {base_url}/chat/completions`), including local Ollama
- Fully local persistence: atomic JSON/TXT writes for config, persona and private note; nothing is reported anywhere
- 30 unit tests, including a local stub server covering HTTP success, HTTP error and non-JSON bodies
- GitHub Actions: Python 3.9 / 3.12 / 3.13 plus Windows; a `v*` tag builds a single-file exe automatically
- `v1.0.0` ships a signed-by-CI Windows exe on the Releases page (SHA-256 in README)
