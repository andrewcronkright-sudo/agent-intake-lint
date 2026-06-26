# Contributing

Thanks for helping improve `agent-intake-lint`.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests
```

Keep new checks deterministic and offline. The tool should be safe to run in
private repositories and shared Markdown vaults without sending content to a
network service.

## Good First Issues

- Add a frontmatter field rule that another team uses.
- Improve diagnostic wording.
- Add an example note that documents a common failure mode.
- Add output formats that are easy for CI systems to consume.
