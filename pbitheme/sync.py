"""Weekly sync: validate all candidates before changing the current pointer."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from .schema import API, DIRECTORY, PATTERN, REPO, ROOT, check_schema, errors_for, fetch, sha256, version_key


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def sync(root=ROOT, get=fetch):
    commit = json.loads(get(f"{API}/commits/main"))["sha"]
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise ValueError("Invalid upstream commit")
    entries = json.loads(get(f"{API}/contents/{DIRECTORY}?ref={commit}"))
    candidates = [x for x in entries if x.get("type") == "file" and PATTERN.fullmatch(x["name"])]
    if not candidates:
        raise ValueError("No official versioned schema files found")
    candidate = max(candidates, key=lambda x: version_key(x["name"]))
    name = candidate["name"]
    base = f"https://raw.githubusercontent.com/{REPO}/{commit}"
    url = f"{base}/{DIRECTORY}/{name}"
    raw = get(url)
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if blob != candidate["sha"]:
        raise ValueError("Downloaded bytes do not match the GitHub blob")
    schema = check_schema(raw)
    for example in (root / "examples").glob("*.json"):
        errors = errors_for(schema, json.loads(example.read_text()))
        if errors:
            raise ValueError(f"Example regression in {example.name}: {errors}")
    archive = root / "schemas" / name
    current_path = root / "latest.json"
    current = json.loads(current_path.read_text()) if current_path.exists() else None
    if current and version_key(current["filename"]) > version_key(name):
        raise ValueError("Upstream version regressed; refusing downgrade")
    if archive.exists() and archive.read_bytes() != raw:
        raise ValueError("An archived version changed upstream; review required, archive retained")
    if current and current["filename"] == name and current["sha256"] == sha256(raw):
        # Verify the archive before reporting a successful no-op.
        if not archive.exists() or sha256(archive.read_bytes()) != current["sha256"]:
            raise ValueError("Current local archive is missing or corrupt")
        return {"changed": False, "version": current["version"]}
    readme = get(f"{base}/{DIRECTORY}/README.md")
    license_bytes = get(f"{base}/LICENSE")
    metadata = {
        "version": PATTERN.fullmatch(name)[1], "filename": name,
        "exploration_version": schema["description"], "draft": "draft-07",
        "sha256": sha256(raw), "git_blob_sha": blob, "upstream_commit": commit,
        "upstream_url": url, "archive_path": f"schemas/{name}",
        "readme_path": f"upstream/{PATTERN.fullmatch(name)[1]}/README.md",
        "readme_sha256": sha256(readme), "license_sha256": sha256(license_bytes),
    }
    # All downloads and checks succeeded. The pointer is replaced last.
    atomic_write(archive, raw)
    atomic_write(root / metadata["readme_path"], readme)
    atomic_write(root / "upstream" / metadata["version"] / "LICENSE", license_bytes)
    encoded = (json.dumps(metadata, indent=2) + "\n").encode()
    atomic_write(root / "metadata" / f"{metadata['version']}.json", encoded)
    atomic_write(current_path, encoded)
    return {"changed": True, "version": metadata["version"], "sha256": metadata["sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(sync(args.root), indent=2))
