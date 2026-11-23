# Verification record — November 23, 2026

Selected schema: 2.159, exploration version 5.78. Original 2.149 Knowledge file and
README hashes matched the handoff; local originals are retained in `references/`.

Completed:

- Fetched the official GitHub directory, selected numeric maximum and pinned its commit.
- Verified original schema bytes against GitHub's blob SHA and recorded SHA-256.
- Passed Draft 7 meta-schema, internal-reference and structural checks.
- Eight automated tests passed, covering valid examples, invalid types/properties/enums,
  broken references, checksum failure, rollback rejection, no-change sync, same-version
  mutation rejection, pointer retention on failure, live discovery and explicit fallback.
- A real MCP stdio client discovered the public Stackmend manifest, fetched the
  immutable Microsoft schema with no fallback, retrieved a schema section, accepted
  the chart-specific theme and rejected the same theme with an invented property.
- The same live retrieval and valid/invalid theme proof passed over local MCP HTTP.
- A second live sync returned `changed: false`; the Git working tree stayed clean.

Not completed:

- GitHub Actions installation or scheduled/manual workflow runs. GitHub rejected
  publishing workflow files because the active OAuth login lacks `workflow` scope.
  The public repository retains the ready-to-install files in `workflow-templates/`.
- Hosting the connector at a public HTTPS endpoint.
- GPT migration, plugin installation, in-ChatGPT tool invocation, public plugin submission.
- Model-driven generation/revision in a public portfolio chatbot.
- Power BI Desktop import and rendering tests.

To enable Actions, the owner can grant the GitHub CLI the needed scope:

```sh
gh auth refresh -h github.com -s workflow
```

After authentication, move the two templates into `.github/workflows/`, update the
README's installation status, commit and push. Dispatch `sync.yml` manually and
inspect the completed run before claiming the weekly schedule is operational.

Reproduce the connector proof with `.venv/bin/python scripts/prove_connector.py`.
It fails if latest discovery falls back, even if the pinned schema remains retrievable.
