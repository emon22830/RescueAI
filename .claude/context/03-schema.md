---
doc: schema
version: 1
updated: 2026-09-14
status: active
applies_to: ">=0.1.0"
---

# Database

Source of truth: `backend/schema.sql`. Run it in the Supabase SQL editor.
**Never run against a live database without reading it first.**

## Tables

```
projects        id · name · goal · created_at

integrations    id · project_id → projects · provider · connected · created_at
                unique (project_id, provider)

agent_runs      id · project_id → projects · status · started_at · completed_at
                evidence_count · finding_count · error
                status ∈ running | completed | failed

evidence        id · project_id · run_id → agent_runs · source · type
                title · content · url · "timestamp" · metadata jsonb

findings        id · project_id · run_id → agent_runs · title · severity
                confidence · description · evidence jsonb
                severity ∈ low | medium | high | critical

actions         id · project_id · run_id → agent_runs · integration · action
                description · params jsonb · status · result
                approved_at · executed_at
                status ∈ pending | executed | failed
```

`source` and `integration` are both constrained to
`slack | gmail | drive | linear | github | calendar`.

## Things that will bite you

- **`"timestamp"` is quoted** in the DDL. It is a Postgres keyword; the column name comes
  from the `Evidence` model field, so it stays.
- **`findings.evidence` is jsonb, denormalized on purpose.** The UI needs the cited
  evidence in one read. The `evidence` table is the full raw record for that run; the
  jsonb column is the subset a given finding cites.
- **Everything hangs off `run_id`.** Findings and actions are always read for the latest
  completed run — see ADR-0004.
- Deletes cascade from `projects`.

## Changing the schema

1. Edit `backend/schema.sql`
2. Apply it in Supabase
3. Bump `version` in this file's frontmatter and in `manifest.json`
4. Add an ADR if the change is not additive
