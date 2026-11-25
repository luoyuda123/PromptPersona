# Contributing

The goal is to **stay simple**: standard library only, no runtime third-party dependencies, no build step. Please keep those three promises.

## Local checks

```bash
py -m compileall -q app main.py tests   # syntax
py -m unittest discover -s tests -v     # all 30 tests must pass
```

On Windows you can double-click `运行测试.bat`.

## Code conventions

- `app/storage.py` owns every read/write: JSON goes through "temp file + `os.replace`" atomic writes, missing files fall back to defaults. Do not sprinkle `open()` around.
- `app/i18n.py` is the single source of copy: a new key must land in all ten locales at once (the tests assert identical key sets), and no hard-coded UI strings.
- Public helpers in `app/providers.py` return `{ok, text}` or `{ok: False, error}` — never raise into the UI.
- Two Tkinter traps: `ttk` style `font` must be a string (brace the font name if it contains spaces), and `tk.Text` has no `justify` option (use a tag instead).
- RTL (Arabic) changes need a visual pass: panel order, button sides, text alignment, Treeview column order.
- Core logic changes need assertions in `tests/test_core.py`; network cases must use the local stub server, never a live endpoint.
- Text files are UTF-8; `.bat` files stay CRLF (handled by `.gitattributes`).

## Commit messages

`type: summary`

- `feat: add Italian locale`
- `fix: correct Treeview column order under RTL`
- `docs: clarify the packaging steps`
- `test: cover non-JSON responses`
- `chore: tighten ignore rules`

## Opening an issue

Include Python version, OS, steps to reproduce, expected vs. actual behaviour. For UI problems attach the traceback from `startup-error.log` — after removing API keys and other private data.
