## What changed

<!-- One or two sentences. Link the issue if there is one. -->

## How I verified it

- [ ] `py -m compileall -q app main.py tests`
- [ ] `py -m unittest discover -s tests` — 30 tests pass
- [ ] UI touched → checked in Simplified Chinese **and** Arabic (RTL)

## Checklist

- [ ] Standard library only — no new runtime dependency
- [ ] New UI strings exist in all ten locales (`app/i18n.py`)
- [ ] No API keys, `config.json`, `persona*.json` or personal answers in the diff
