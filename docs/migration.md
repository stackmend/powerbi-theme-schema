# ChatGPT migration and portfolio integration

Verified on 2026-11-23 against the official
[migration FAQ](https://help.openai.com/en/articles/20001519-custom-gpt-retirement-and-migration-faq)
and [migration guide](https://learn.chatgpt.com/docs/migrate-custom-gpts).

The standard retirement date is December 11, 2026; account-specific exceptions may
apply. Migration copies published instructions into a skill and Knowledge into
references. Actions do not transfer. The replacement starts private and public
availability requires a separate submission. Standard Chat cannot be assumed to
execute bundled validation scripts. An accessible MCP tool provides execution
independently of whether the chat surface runs code.

## Current boundary

The owner has not migrated the GPT yet. The repository implements an MCP connector
and a real client-to-server test. That test does NOT establish installation, access,
tool invocation, downloads or correct conversation behavior inside ChatGPT.

## Next steps

1. In the GPT editor, finish essential edits and publish the version to preserve.
   Use My GPTs → Migrate to plugin when offered. Review copied instructions/files.
2. Host this connector behind an HTTPS endpoint using a service/account selected by
   the owner. Configure appropriate request limits and any required authentication.
   This repository's localhost HTTP transport is a development option, not hosting.
3. Connect that endpoint using the custom integration options available to the
   owner's account, then add it to the plugin. The endpoint cannot be replaced by a
   raw GitHub URL: GitHub hosts schema files but does not execute validation tools.
4. Update the copied instructions to use the tools below instead of the static
   Knowledge schema as the source of truth. Preserve the original interaction style.
5. In ChatGPT, explicitly select the plugin and test basic branding, chart-specific
   formatting, a follow-up revision, an invalid-property request and an unavailable
   network fallback. Verify actual tool calls and validate the exact downloaded bytes.
6. Test access with another intended user before publishing or replacing the portfolio link.

## Proposed replacement instruction text

Help users create and iteratively refine Power BI report themes. At the start of a
theme task, call get_schema_metadata and disclose the selected version or fallback.
Read get_authoring_guidance. Use search_schema and get_schema_section to consult
the exact supported properties, types, enums and referenced definitions before
generating JSON. Microsoft's selected schema is the only syntax authority; don't
invent keys. Preserve requested design choices across follow-up turns.

Use metadata.upstream_url for the final theme's lowercase "$schema" property.
Pass metadata.sha256 to each lookup and validation call. Run validate_theme on the
exact final object; fix errors and repeat before calling it validated or offering a
download. Revalidate after every edit. If tools are unavailable, explicitly say the
output is not validated. Do not claim a Desktop import test occurred. Explain
unsupported requests and offer schema-supported alternatives.

## Portfolio destination

The intended experience remains conversational: ask → clarify → generate → refine
→ download. A future public web chat can call the same retrieval/validation layer,
with model credentials kept on its backend. Preset examples should be starter
prompts, not a replacement for the visitor's own requests. No public chat, model
billing, plugin submission or paid hosting has been activated by this repository.
