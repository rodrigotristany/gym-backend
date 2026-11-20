# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

GymBackend: the backend of a **multi-tenant gym management platform** (many gyms, each with branches, served by one backend and one shared PostgreSQL database), built as a **modular monolith** Web API.

**Current state:** the code is still the ASP.NET Core template (`GymBackend/` with `WeatherForecastController`, and `GymBackend.Tests/` with a placeholder NUnit test). The structure and stack below are the **target**. When scaffolding, move the host to `src/GymBackend.Host/` and replace the NUnit test project with xUnit.

## Commands

.NET 10 SDK. Run from the repository root.

```bash
dotnet build GymBackend.sln
dotnet test GymBackend.sln
dotnet test --filter "FullyQualifiedName~CreateBooking_WhenSessionFull_ReturnsConflict"   # single test
dotnet run --project GymBackend --launch-profile http                                    # http://localhost:5091 (https: 7029)
docker compose up --build
```

EF Core migrations are per module (one DbContext and one PostgreSQL schema per module):

```bash
dotnet ef migrations add <Name> --project src/Modules.<Module>.Infrastructure --startup-project src/GymBackend.Host --context <Module>DbContext
```

## Documentation (read before designing or implementing a feature)

- `Documentation/BusinessRequirements.md` (BRD v3.2): requirements with IDs (`FR-BK-03`, `BR-BK-2`…), the permission matrix (§3.2), settings and their scope (§6), and phasing (§9). Cite these IDs in tests and commits.
- `Documentation/NonFunctionalRequirements.md` (v0.4, proposed): measurable targets (`NFR-PF-*`, `NFR-SE-*`…), growth stages, cost budget.
- `Documentation/ArchitectureOptions.md` (v0.1, proposed): the modular monolith design, module list and database approach. The ADRs in its §6 are not decided yet.
- `Documentation/BRD-Analysis.md`: historical, superseded by the BRD.

## Project rules (from the requirements)

- **Tenant isolation is the top risk.** Every tenant-owned table has a non-null `tenant_id`. Filtering is enforced centrally (EF Core global query filters + PostgreSQL row-level security), never per endpoint or per handler. The same applies to file paths, cache keys, background jobs, logs and exports. Another tenant's IDs must behave as "not found". The only shared tables are accounts and platform records (FR-TEN-02, NFR-SE-25..27).
- **Account vs. gym profile:** one platform-wide account per person (email, password, 2FA, language); each gym keeps its own gym profile with personal data and roles. A gym must never learn about a person's other gyms (BR-GEN-3, NFR-SE-32).
- **Phase 1 is staff-operated:** only staff sign in. Clients are gym profiles without accounts and act only through single-use links and WhatsApp reply buttons (BRD §9.1, NFR-SE-34).
- **Authorization checks permissions, not role names.** "Own" and "assigned" rules are checked against the loaded resource (NFR-SE-08..11). Every endpoint has a policy (default deny).
- **Booking is concurrency-critical:** capacity, credits and overlaps are enforced atomically in the database (BR-BK-2, NFR-SC-06).
- **Timers and notifications are durable** (outbox and job tables in PostgreSQL, never in memory). The API stays stateless (NFR-AV-05, NFR-09).
- **Audit every change** (who, on whose behalf, before/after) in the same transaction (FR-AUD-01). Records with history are archived, never hard-deleted; payments are voided with a reason (BR-GEN-1, BR-FIN-1).
- Timestamps are stored in UTC and shown in the branch time zone. API messages and notifications support Spanish and English.
- Provider SDKs (Azure, Meta WhatsApp, email) appear only behind adapter interfaces (NFR-05, NFR-CO-06).

## Tech stack

- .NET 10, ASP.NET Core Minimal APIs
- EF Core 10 + PostgreSQL (Npgsql), snake_case via `EFCore.NamingConventions`, one schema per module
- FluentValidation for request validation
- `Result<T>` for error handling (no exceptions for business logic)
- JWT access tokens + rotating refresh tokens (token server choice is still ADR-05)
- OpenTelemetry for tracing and metrics; Serilog for structured logging
- OpenAPI via `Microsoft.AspNetCore.OpenApi`
- Docker

## Architecture

- Modular monolith with vertical slices inside each module.
- Each module has four projects. Allowed references:
  - `Modules.<Name>.Domain`: entities, value objects, enums. References only `Modules.Common.Domain`.
  - `Modules.<Name>.Infrastructure`: DbContext, EF configurations, migrations. References its own Domain.
  - `Modules.<Name>.Core`: endpoints, handlers, validators. References its own Domain and Infrastructure, and other modules' **PublicApi only**.
  - `Modules.<Name>.PublicApi`: cross-module contracts (interfaces, DTOs, integration events). Depends on nothing module-specific.
- Handlers use the module's DbContext directly. This is a deliberate vertical-slice choice: the domain stays free of infrastructure, but Core is not infrastructure-agnostic.
- A module never reads another module's tables. Cross-module calls go through PublicApi. They may join the caller's database transaction where an invariant needs it (e.g. booking + credit consumption).
- Shared code: `Modules.Common.Domain` (`Result<T>`, `IHandler`, `IEvent`) and `Modules.Common.API` (endpoint abstractions, error handling). `GymBackend.Host` holds `Program.cs` and DI composition.
- NetArchTest rules enforce these references and "internal by default".

## Feature layout and naming

```
Features/<UseCase>/<UseCase>.Endpoint.cs
Features/<UseCase>/<UseCase>.Handler.cs
Features/<UseCase>/<UseCase>.Validator.cs
Features/<UseCase>/<UseCase>.Mapping.cs      # only if 2+ mappings
Features/Shared/Routes/RouteConsts.cs
Features/Shared/Errors/<Module>Errors.cs
```

## Code conventions

- Positional records for request/response DTOs
- File-scoped namespaces, primary constructors for DI, sealed implementation classes
- `internal` by default; `public` only for PublicApi contracts and what the Host needs
- Manual mapping with extension methods
- Handlers are concrete sealed classes returning `Result<T>`. `IHandler` is a marker used only for DI scanning; there is no generic `IHandler<TRequest, TResponse>` and no dispatcher. Endpoints receive the handler by injection.
- Endpoints implement `IApiEndpoint`; routes come from `RouteConsts`. Validation runs as an endpoint filter. A failed `Result` becomes RFC 7807 ProblemDetails, with the status code taken from the error type (not found → 404, conflict → 409, validation → 400).

## Patterns we do NOT use

- Repository pattern or unit-of-work wrappers over EF Core
- AutoMapper or any mapping library
- MediatR or any mediator library
- Exceptions for business logic flow
- `[FromServices]` attribute

## DI registration

- Each module exposes `Add<Module>Module(this IServiceCollection services, IConfiguration configuration)`.
- Auto-scan per module assembly: `RegisterHandlersFromAssemblyContaining<T>()`, `AddValidatorsFromAssembly(...)`, `RegisterApiEndpointsFromAssemblyContaining<T>()`.

## Testing

- xUnit, Moq, Bogus for test data
- Testcontainers (PostgreSQL) for integration tests, with Respawn for cleanup between tests. Because of `FORCE ROW LEVEL SECURITY`, Respawn must connect with a role that has `BYPASSRLS`, or it silently leaves rows behind.
- NetArchTest.Rules for architecture tests
- Integration tests include the tenant-isolation suite: two tenants, and every endpoint returns 404 for the other tenant's IDs (NFR-SE-27).
- Test naming: `Method_Scenario_ExpectedResult`

## Documentation conventions

Docs open with a `Title/Author/Version/Date/Status` header and end with a change-history table. When you change a requirement doc, bump the version and add a history row. Dates use `MM-DD-YYYY`.
