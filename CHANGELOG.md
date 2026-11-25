# Changelog

Semantic versioning: major = behaviour change, minor = new features, patch = fixes only.

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
