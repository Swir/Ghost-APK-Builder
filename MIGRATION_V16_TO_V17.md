# Migration from Ghost v16.4 to v17

v17 is intentionally not an in-place patch of the 1290-line v16.4 script. It preserves the legacy source for reference while replacing the most fragile assumptions.

- Android Studio projects are no longer used as build templates.
- The old `~/AndroidStudioProjects/Ghost_Apex_Workspace` workflow is not required.
- Old config passwords are not imported.
- WSA-specific installation is removed from the primary workflow.
- Target API 34 projects must be moved to API 36 for the current Google Play submission profile.
- Kotlin snippets should be reviewed against the new deterministic app template before production use.
