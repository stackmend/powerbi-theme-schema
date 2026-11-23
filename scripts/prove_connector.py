"""Real stdio MCP client -> server -> live official GitHub -> validation proof."""
import asyncio
import json
import sys
from pathlib import Path

from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]


async def main():
    params = StdioServerParameters(command=sys.executable, args=["-m", "pbitheme.server"], cwd=str(ROOT))
    async with Client(params) as client:
        async def call(name, arguments=None):
            result = await client.call_tool(name, arguments or {})
            if result.is_error:
                raise RuntimeError(str(result.content))
            return json.loads(next(part.text for part in result.content if part.type == "text"))
        metadata = await call("get_schema_metadata")
        assert metadata["retrieval"]["source"] == "live_official", metadata
        assert not metadata["retrieval"]["fallback"], metadata
        digest = metadata["sha256"]
        section = await call("get_schema_section", {"expected_sha256": digest, "path": "/properties/dataColors"})
        assert "schema" in section
        theme = json.loads((ROOT / "examples/chart-defaults.json").read_text())
        theme["$schema"] = metadata["upstream_url"]
        valid = await call("validate_theme", {"expected_sha256": digest, "theme": theme})
        assert valid["valid"], valid
        theme["inventedProperty"] = True
        invalid = await call("validate_theme", {"expected_sha256": digest, "theme": theme})
        assert not invalid["valid"], invalid
        print(json.dumps({"transport": "MCP stdio", "version": metadata["version"],
                          "retrieval": metadata["retrieval"], "valid_theme_accepted": valid["valid"],
                          "invented_property_rejected": not invalid["valid"],
                          "chatgpt_plugin_tested": False, "power_bi_desktop_tested": False}, indent=2))


asyncio.run(main())
