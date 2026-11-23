# pbiThemeBot schema connector

Executable schema retrieval and validation for a conversational Power BI theme assistant.
Users should be able to ask for a theme, refine it through conversation, and download
JSON that has actually passed validation. This repository supplies the reference and
validation layer; it is not itself a hosted chatbot or an installed ChatGPT plugin.

Microsoft's [Report Theme JSON Schema directory](https://github.com/microsoft/powerbi-desktop-samples/tree/main/Report%20Theme%20JSON%20Schema)
is the authority. The selected version is recorded in `latest.json`. Schemas are retained
byte-for-byte, with SHA-256, Git blob identity and an immutable upstream commit URL.
Microsoft's corresponding README and LICENSE are retained under `upstream/<version>/`.
This project is independent of Microsoft.

## Run locally

Requires Python 3.13. Dependencies and transitive dependencies are pinned.

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pbitheme.validate examples/chart-defaults.json
.venv/bin/python -m pbitheme.sync
.venv/bin/python scripts/prove_connector.py
```

The CLI validates JSON Schema syntax. The MCP validator additionally requires the
exact version-pinned `$schema` URL returned by the metadata tool. Neither test is a
Power BI Desktop import test. The examples originated in the migration handoff and
are illustrative rather than evidence of historical user conversations.

## Connect a conversational client

Launch the MCP server over stdio with `.venv/bin/python -m pbitheme.server`, using
this repository as the working directory. The server exposes:

- `get_schema_metadata`: reads the public mirror manifest, fetches the selected schema
  directly from Microsoft's immutable commit, validates it and reports provenance.
- `search_schema` and `get_schema_section`: retrieve authoritative schema material
  without sending the entire large schema into every chat turn.
- `get_authoring_guidance`: retrieves Microsoft's matching README.
- `validate_theme`: executes Draft 7 validation and returns actionable JSON paths.

Pass the checksum returned by metadata to subsequent tools. Recent selections stay
available in process memory, so a conversation does not silently switch schemas.
Every new metadata call checks the remote manifest; publishing an update does not
require replacing Knowledge attachments. If discovery or retrieval fails, the tool
explicitly identifies its verified fallback and does not claim it is current.

For local HTTP testing: `.venv/bin/python -m pbitheme.server --http` serves on
`http://127.0.0.1:8000/mcp`. This is a local development endpoint. ChatGPT requires an
accessible hosted integration; localhost is not a deployed ChatGPT connector.
See [migration setup](docs/migration.md) for remaining work.

## Synchronization and rollback

The workflows under `.github/workflows/` run validation on pushes and pull requests.
The sync checks Mondays at 09:00 UTC (18:00 Korea time) and supports manual runs.
GitHub may delay scheduled jobs. It selects numeric versions,
pins the upstream commit before downloading, checks the Git blob, Draft 7 schema,
local references, expected structure and example regressions before publishing.
Only the publishing job has repository write permission. No-change runs make no commit.

An upstream change to an already archived version is rejected for review. Failed
checks leave the last published pointer intact. Review failed runs in GitHub Actions;
notification delivery depends on the account's GitHub notification settings.

To roll back, disable the sync workflow, replace `latest.json` with the desired file
from `metadata/`, and commit it. Deploy the matching checkout to connectors as well:
connectors reject a remote version lower than their bundled baseline. Re-run tests
before re-enabling sync. Archives are never rewritten automatically.

## Scope and limitations

The manifest identifies the latest **verified published schema**, not necessarily
the newest Power BI Desktop release. Validation does not guarantee that a setting
has a useful visual effect, override existing report formatting, or support every
Desktop version. Model-specific conditional formatting is outside theme JSON.

The source handoff and original Knowledge files are kept locally in ignored
`references/`; they are not automatically published. No credentials belong in this repo.
