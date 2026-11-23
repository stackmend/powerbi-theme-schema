import argparse
import json

from .schema import errors_for, load_local


def validate(theme):
    metadata, schema = load_local()
    errors = errors_for(schema, theme)
    return {"valid": not errors, "version": metadata["version"], "sha256": metadata["sha256"], "errors": errors,
            "power_bi_desktop_tested": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate a theme against the verified current Microsoft schema")
    parser.add_argument("theme")
    args = parser.parse_args()
    with open(args.theme) as handle:
        result = validate(json.load(handle))
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)
