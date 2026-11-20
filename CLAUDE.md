# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

Backend for a **multi-tenant gym management platform** (many gyms, each with branches, in one backend and one shared database). The project is at the end of requirements/architecture: the code is still the ASP.NET Core template (`WeatherForecastController`, a placeholder NUnit test). The design lives in `Documentation/`, and implementation should follow it.

## Commands

.NET 10 SDK. Run from the repository root.

```bash
dotnet build GymBackend.sln
dotnet test GymBackend.sln
dotnet test --filter "FullyQualifiedName~GymBackend.Tests.Tests.Test1"   # single test (NUnit)
dotnet run --project GymBackend --launch-profile http                    # http://localhost:5091 (https profile: 7029)
docker compose up --build                                                 # container build via GymBackend/Dockerfile
```

The OpenAPI document is served at `/openapi/v1.json` in Development only. No linter or formatter is configured.

## Documentation (read before designing or implementing features)

- `Documentation/BusinessRequirements.md` (BRD v3.2): requirements with IDs (`FR-BK-03`, `BR-BK-2`, …), the role/permission matrix (§3.2), configurable settings and their scope (§6), and phasing (§9). Cite these IDs in code comments, tests and commits.
- `Documentation/NonFunctionalRequirements.md` (v0.4, proposed): measurable targets (`NFR-PF-*`, `NFR-SE-*`, `NFR-SC-*`, `NFR-CO-*`), growth stages and cost budget.
- `Documentation/ArchitectureOptions.md` (v0.1, proposed): compares three architectures and recommends a **modular monolith** on ASP.NET Core + PostgreSQL, deployed to Azure Container Apps. Its §6 lists the ADRs that are not decided yet; don't treat those as settled.
- `Documentation/BRD-Analysis.md`: the original BA review; historical, superseded by the BRD.

## Rules that shape all code

- **Tenant isolation is the top risk.** Every tenant-owned record carries `TenantId`, and filtering is enforced centrally in the data layer (EF Core global filters + PostgreSQL row-level security), never per endpoint. The same applies to file paths, cache keys, background jobs, logs and exports. Another tenant's IDs must behave as "not found". The only shared tables are accounts (sign-in identity) and platform records (FR-TEN-02, NFR-SE-25..27).
- **Account vs. gym profile:** one platform-wide account per person (email, password, 2FA, language); each gym keeps its own gym profile with the personal data and roles. A gym must never learn about a person's other gyms (BR-GEN-3, NFR-SE-32).
- **Phase 1 is staff-operated:** only staff sign in. Clients are gym profiles without accounts, reached by WhatsApp/email, and act only through single-use links and WhatsApp reply buttons (BRD §9.1, NFR-SE-34).
- **Authorization checks permissions, not role names.** Roles are permission sets (built-in roles locked, custom roles allowed), and "own"/"assigned" rules are checked per resource (NFR-SE-08..11).
- **Booking is concurrency-critical:** capacity, credits and overlaps must be enforced atomically (BR-BK-2, NFR-SC-06).
- **Timers and notifications must be durable** (persisted jobs/outbox, never in-memory), because the API must stay stateless and horizontally scalable (NFR-AV-05, NFR-09).
- **Audit every change** (who, on whose behalf, before/after) in the same transaction (FR-AUD-01). Records with history are archived, never hard-deleted; payments are voided with a reason (BR-GEN-1, BR-FIN-1).
- Store timestamps in UTC and display them in the branch time zone. Spanish and English for API messages and notifications.
- **Stay portable:** containers, PostgreSQL, and provider SDKs (Azure, Meta WhatsApp, email) only behind adapter interfaces (NFR-05, NFR-CO-06).

## Documentation conventions

Docs open with a `Title/Author/Version/Date/Status` header and end with a change-history table. When you change a requirement doc, bump the version and add a history row. Dates use `MM-DD-YYYY`.
