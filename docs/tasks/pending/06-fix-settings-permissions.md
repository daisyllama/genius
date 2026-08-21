# Task: Fix .claude/settings.json Permissions

**Status:** Pending  
**Priority:** 6  
**Date Created:** 2026-08-19

## Context

File: `.claude/settings.json`

Current `permissions.allow` array is too literal and narrow—each entry is an exact command match rather than a flexible prefix pattern. This makes general workflows awkward (e.g., `Bash(python3 *)` instead of individual entries).

## Objective

Refactor permissions to use prefix wildcards and tool-level rules instead of exact command matches.

**Current approach (too specific):**
```json
"allow": [
  "Bash(python3 -c 'specific command')",
  "Bash(python3 -m json.tool)",
  "Bash(python3)"
]
```

**Better approach (flexible):**
```json
"allow": [
  "Bash(python3 *)",
  "Bash(git *)",
  "Edit(.claude/*)",
  "Read"
]
```

## Acceptance Criteria

- Permissions refactored to use wildcards
- SessionStart hook remains functional
- General Bash/Git/Edit/Read workflows no longer prompt
- Tested with a few commands to confirm

## Notes

- See .claude/settings.json schema documentation for wildcard syntax
- Consider what should be allowed by default vs. what should always prompt
