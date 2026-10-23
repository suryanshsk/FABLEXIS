# Contributing

Keep changes small and provider-independent where possible. Add or update tests for schema, timing, CLI, and rendering behavior. Run:

```powershell
python -m unittest discover -s tests -v
python validate.py
```

Do not commit secrets, downloaded media, or generated `out/` directories.
