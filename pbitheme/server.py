"""Read-only MCP connector; schema validation executes here, not in model prose."""
import argparse
import json

from mcp.server import MCPServer

from .schema import DIRECTORY, REPO, ROOT, errors_for, fetch, load_live, load_local, pointer, sha256

SELECTIONS = {}

server = MCPServer("pbiThemeBot", instructions=(
    "Get schema metadata, consult schema sections, then validate every final theme. "
    "Preserve conversation requirements while revising. Never invent properties. "
    "Schema validity is not a Power BI Desktop import test."
))


def selected(expected_sha256):
    if expected_sha256 in SELECTIONS:
        return SELECTIONS[expected_sha256]
    metadata, schema = load_local()
    if expected_sha256 != metadata["sha256"]:
        raise ValueError("Schema selection changed. Get metadata and recheck the theme against the selected version.")
    return metadata, schema


@server.tool()
def get_schema_metadata() -> dict:
    """Fetch the selected official schema live and verify it; report any local fallback explicitly.

    Returns version, checksum and immutable raw URL. This is the latest verified
    selection in the deployed archive, not a claim that upstream was checked today.
    Pass sha256 to subsequent lookup and validation calls.
    """
    metadata, schema, retrieval = load_live()
    SELECTIONS[metadata["sha256"]] = (metadata, schema)
    while len(SELECTIONS) > 8:
        del SELECTIONS[next(iter(SELECTIONS))]
    return {**metadata, "retrieval": retrieval, "root_properties": list(schema["properties"])}


@server.tool()
def get_schema_section(expected_sha256: str, path: str) -> dict:
    """Read an exact RFC 6901 pointer, e.g. /properties/textClasses or /definitions/Fill.

    Returned $ref entries can be retrieved by their /definitions/... pointer.
    Large sections return child keys so you can narrow the next lookup.
    """
    metadata, schema = selected(expected_sha256)
    section = pointer(schema, path)
    if len(json.dumps(section)) > 60000:
        return {"path": path, "too_large": True, "child_keys": list(section) if isinstance(section, dict) else [],
                "message": "Request a more specific child pointer", "version": metadata["version"]}
    return {"path": path, "schema": section, "version": metadata["version"]}


@server.tool()
def search_schema(expected_sha256: str, query: str) -> dict:
    """Find schema pointers by property name, title or description. Inspect matched sections before generation."""
    _, schema = selected(expected_sha256)
    if len(query.strip()) < 3:
        raise ValueError("Use at least three characters")
    needle = query.casefold().strip()
    matches = []

    def walk(value, path=""):
        if len(matches) >= 30:
            return
        if isinstance(value, dict):
            label = " ".join(str(value.get(k, "")) for k in ("title", "description"))
            if needle in label.casefold() or needle in path.rsplit("/", 1)[-1].casefold():
                matches.append({"path": path, "title": value.get("title"), "description": value.get("description")})
            for key, child in value.items():
                walk(child, path + "/" + key.replace("~", "~0").replace("/", "~1"))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}/{index}")

    walk(schema)
    return {"matches": matches, "limit": 30, "may_have_more": len(matches) == 30}


@server.tool()
def get_authoring_guidance(expected_sha256: str) -> dict:
    """Read the official README accompanying this schema, including known limitations."""
    metadata, _ = selected(expected_sha256)
    url = f"https://raw.githubusercontent.com/{REPO}/{metadata['upstream_commit']}/{DIRECTORY}/README.md"
    try:
        raw = fetch(url)
    except Exception:
        raw = (ROOT / "upstream" / metadata["version"] / "README.md").read_bytes()
    if sha256(raw) != metadata["readme_sha256"]:
        raise ValueError("README checksum mismatch")
    return {"version": metadata["version"], "markdown": raw.decode()}


@server.tool()
def validate_theme(expected_sha256: str, theme: dict) -> dict:
    """Execute Draft 7 validation on the EXACT final theme, including its $schema URL.

    Fix errors and rerun. This does not modify the theme or test Desktop import.
    """
    if len(json.dumps(theme)) > 256000:
        raise ValueError("Theme exceeds 256 KB limit")
    metadata, schema = selected(expected_sha256)
    errors = errors_for(schema, theme)
    if theme.get("$schema") != metadata["upstream_url"]:
        errors.append({"path": "$.$schema", "rule": "pbiThemeBot provenance", "message": "Use the exact upstream_url returned by get_schema_metadata"})
    return {"valid": not errors, "errors": errors[:20], "error_count": len(errors),
            "version": metadata["version"], "sha256": metadata["sha256"],
            "theme_sha256": sha256(json.dumps(theme, sort_keys=True, separators=(",", ":")).encode()),
            "validator": "jsonschema Draft7Validator", "power_bi_desktop_tested": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Local HTTP development transport on 127.0.0.1:8000")
    args = parser.parse_args()
    if args.http:
        server.run(transport="streamable-http", host="127.0.0.1", port=8000)
    else:
        server.run()
