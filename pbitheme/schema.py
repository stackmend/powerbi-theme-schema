"""Only verified, unmodified Microsoft schemas are used for validation."""
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import unquote
from urllib.request import Request, urlopen

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]
REPO = "microsoft/powerbi-desktop-samples"
DIRECTORY = "Report%20Theme%20JSON%20Schema"
API = f"https://api.github.com/repos/{REPO}"
PATTERN = re.compile(r"reportThemeSchema-(\d+(?:\.\d+)+)\.json")
MANIFEST_URL = "https://raw.githubusercontent.com/stackmend/powerbi-theme-schema/main/latest.json"


def fetch(url):
    headers = {"User-Agent": "pbiThemeBot-schema-sync", "Accept": "application/vnd.github+json"}
    if url.startswith("https://api.github.com/") and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urlopen(Request(url, headers=headers), timeout=45) as response:
        data = response.read(10_000_001)
    if len(data) > 10_000_000:
        raise ValueError("Upstream response exceeds size limit")
    return data


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def version_key(name):
    match = PATTERN.fullmatch(name)
    if not match:
        raise ValueError(f"Unrecognized schema filename: {name}")
    return tuple(map(int, match[1].split(".")))


def pointer(document, path):
    if path == "":
        return document
    if not path.startswith("/"):
        raise ValueError("Use an RFC 6901 JSON pointer starting with /")
    for part in path.split("/")[1:]:
        key = part.replace("~1", "/").replace("~0", "~")
        document = document[int(key)] if isinstance(document, list) else document[key]
    return document


def check_schema(raw):
    schema = json.loads(raw)
    Draft7Validator.check_schema(schema)
    if schema.get("type") != "object" or "name" not in schema.get("required", []):
        raise ValueError("Missing expected theme root structure")
    if not {"name", "dataColors", "visualStyles", "textClasses", "$schema"} <= schema.get("properties", {}).keys():
        raise ValueError("Expected Power BI theme properties are missing")
    if schema.get("additionalProperties") is not False:
        raise ValueError("Unexpected open root schema")
    if not schema.get("definitions"):
        raise ValueError("Missing definitions")

    def visit(value):
        if isinstance(value, dict):
            if "$ref" in value:
                ref = value["$ref"]
                if ref != "#" and not ref.startswith("#/"):
                    raise ValueError(f"Unsupported nonlocal reference: {ref}")
                pointer(schema, unquote(ref[1:]))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schema)
    validator = Draft7Validator(schema)
    validator.validate({"name": "Smoke test", "dataColors": ["#2463EB", "#F97316"]})
    if validator.is_valid({"name": "Invalid", "totallyInventedProperty": True}):
        raise ValueError("Schema accepts the invented-property negative control")
    return schema


def errors_for(schema, theme):
    return [
        {"path": error.json_path, "message": error.message, "rule": error.validator}
        for error in Draft7Validator(schema).iter_errors(theme)
    ]


def load_local(root=ROOT):
    metadata = json.loads((root / "latest.json").read_text())
    raw = (root / metadata["archive_path"]).read_bytes()
    if sha256(raw) != metadata["sha256"]:
        raise ValueError("Archived schema checksum mismatch")
    return metadata, check_schema(raw)


def load_live(root=ROOT):
    """Discover current selection from the mirror, then fetch Microsoft directly."""
    metadata, cached = load_local(root)
    try:
        current = json.loads(fetch(MANIFEST_URL))
        commit = current["upstream_commit"]
        name = current["filename"]
        if not re.fullmatch(r"[0-9a-f]{40}", commit) or not PATTERN.fullmatch(name):
            raise ValueError("Invalid manifest provenance")
        if current["upstream_url"] != f"https://raw.githubusercontent.com/{REPO}/{commit}/{DIRECTORY}/{name}":
            raise ValueError("Manifest does not reference the official immutable Microsoft source")
        if version_key(name) < version_key(metadata["filename"]):
            raise ValueError("Remote manifest regressed below the verified local version")
        raw = fetch(current["upstream_url"])
        if sha256(raw) != current["sha256"]:
            raise ValueError("Live schema checksum mismatch")
        return current, check_schema(raw), {"source": "live_official", "fallback": False, "manifest_url": MANIFEST_URL}
    except Exception as exc:
        discovery_error = str(exc)
    try:
        raw = fetch(metadata["upstream_url"])
        if sha256(raw) != metadata["sha256"]:
            raise ValueError("Live schema checksum mismatch")
        return metadata, check_schema(raw), {"source": "live_official", "fallback": True,
            "reason": "Latest discovery failed; fetched pinned local version: " + discovery_error}
    except Exception as exc:
        return metadata, cached, {"source": "verified_local_archive", "fallback": True,
                                 "reason": discovery_error + "; " + str(exc)}
