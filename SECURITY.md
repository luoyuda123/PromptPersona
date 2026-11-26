# Security Policy

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Use GitHub's private reporting flow instead:

1. Go to the repository's **Security** tab → **Report a vulnerability** (private advisory), or
2. Open a draft advisory at https://github.com/luoyuda123/PromptPersona/security/advisories/new

Include the version (see Releases), the affected file, and reproduction steps. You can expect an initial response within **7 days**.

## Scope

In scope:

- Local data handling: `config.json`, `persona.json`, `secret_note.json`, `persona_system.txt`
- API key storage and transmission to configured model endpoints
- The packaged Windows executable produced by the release workflow

Out of scope:

- Vulnerabilities in third-party model providers or their APIs
- The unsigned-exe SmartScreen warning (a known, documented trade-off — verify the published SHA-256 instead)
- Attacks that require an already-compromised local machine

## What the app does with your data

- No telemetry, no analytics, no auto-update calls.
- The only outbound requests go to the base URL you configure, using the key you entered.
- Files are written atomically (temp file + `os.replace`) in the app directory, so a crash cannot leave a half-written config.
- `config.json` contains your API key in plain text — treat it like any local credential and never commit it (`.gitignore` already excludes it).
