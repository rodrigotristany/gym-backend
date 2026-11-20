Title: Gym Backend Non-Functional Requirements
Author: Rodrigo Tristany
Version: 0.4 (draft for review)
Date: 11-20-2026
Status: Proposed. Resolves BRD §8 NFR-07 and the "Expected scale / availability / backup" item in BRD §10. Aligned with BRD v3.2 (multi-tenant platform, one account per person across gyms, staff-operated Phase 1).

# Gym Backend: Non-Functional Requirements

## 0. How to read this document

Each requirement has:

- **Source**: `BRD` = stated in `BusinessRequirements.md` v2.0; `Derived` = follows directly from a BRD rule; `Proposed` = not in the BRD, suggested here and needs sign-off.
- **Target**: a measurable value that can be tested or monitored.
- **Rationale**: why this value, so it can be challenged with facts rather than taste.

### 0.1 Architecture this document assumes (BRD v3.0)

- **One backend**, stateless, scaled **horizontally** by adding identical instances (BRD NFR-09).
- **One shared database** for all tenants. Every row carries a `TenantId`, and the data layer filters by it automatically (BRD NFR-08).
- **Multi-tenant, multi-branch**: many gyms (tenants), each with one or more branches (BRD NFR-04).

### 0.2 Growth stages (Proposed, everything below depends on them)

Targets are given for the stage the platform is in. The platform moves to the next stage by **changing the size of resources**, not by changing the architecture. **Confirm or correct these numbers first.**

| Assumption (whole platform) | Stage 0: soft start | Stage 1: early growth | Stage 2: design ceiling |
|---|---|---|---|
| Tenants (gyms) | 1 | ≈ 10 | ≈ 50 |
| Branches | 1 | ≈ 15 | ≈ 80 |
| Active clients | ≤ 300 | ≈ 2,500 | ≈ 15,000 |
| Staff users | ≤ 5 (e.g. 1 admin, 1 professor) | ≈ 100 | ≈ 600 |
| Class sessions per week | ≤ 40 | ≈ 500 | ≈ 3,000 |
| Average bookings per client per week | 3 | 3 | 3 |
| Opening hours | 07:00–23:00 ART, 7 days | same | same |
| Peak hours | 07:00–09:00 and 18:00–21:00 ART | same | same |

All gyms are assumed to be in Argentina, so their peaks **coincide**. That's why the stage sizes are based on totals for the whole platform, not per gym.

**Phase 1 is staff-operated** (BRD §9): only staff sign in, and clients interact only through WhatsApp replies and single-use links. API load in Phase 1 is therefore a small fraction of the figures below, which are sized for Phase 2, when clients get the app. Phase 1 must still meet every latency target in §2.

---

## 1. Availability

The BRD only says "to be defined" (NFR-07). Nothing is life-critical, but booking, waitlist offers and reception check-in all happen during opening hours, and a waitlist offer that fails to send breaks a business rule (FR-BK-05). With one shared backend and database, **an outage affects every gym at once**, so the targets apply to the platform as a whole.

| ID | Requirement | Target | Source | Rationale |
|---|---|---|---|---|
| NFR-AV-01 | Monthly uptime of the public API | **≥ 99.5 %** per calendar month, measured by an external probe every 1 min against a health endpoint that touches the database | Proposed | 99.5 % allows a single-region, single-database deployment, which keeps cost in line with §5. 99.9 % would need a zone-redundant database and at least 2 always-on instances, roughly doubling the infrastructure bill. Revisit at Stage 2, when an outage hits many paying gyms. |
| NFR-AV-02 | Maximum unplanned downtime | **≤ 3 h 36 min per month** (the 99.5 % budget for a 30-day month); no single incident > 1 h during opening hours | Proposed | 43,200 min × 0.5 % = 216 min. The 1-hour cap keeps a single outage from wiping out a whole peak period. |
| NFR-AV-03 | Planned maintenance | Only between **01:00 and 05:00 ART**, announced to staff **48 h** ahead, ≤ 4 h per month, **excluded** from the uptime figure | Proposed | The gym is closed then (assumed hours), so nobody books or checks in. |
| NFR-AV-04 | Deployments | **Zero-downtime** rolling deployments; database migrations must be backward-compatible with the previous app version | Proposed | Lets fixes ship during opening hours without spending the downtime budget. Containers (NFR-05) make this cheap. All tenants always run the same version. |
| NFR-AV-05 | Background jobs (waitlist offer expiry, no-show marking, notifications, document/membership expiry) | No job lost on restart; jobs resume within **5 min** of the service coming back | Derived (FR-BK-05/06/11) | A waitlist offer has a 30-minute window. Losing the expiry timer would freeze the queue for that session. Jobs must be persisted (e.g. a DB-backed queue), not held in memory. |
| NFR-AV-06 | Degraded mode for external providers | If WhatsApp, email or push is down, the core operation (booking, cancellation, check-in) **still succeeds** and the notification is retried for at least **24 h** with back-off | Proposed | Third-party outages must not block the front desk. Notifications go through an outbox. |
| NFR-AV-07 | Recovery Point Objective (RPO) | **≤ 15 min** of data loss | Proposed | Bookings, check-ins and payments are recorded live at the desk. 15 min is what managed point-in-time restore gives at no extra cost and is small enough to rebuild by hand from receipts. |
| NFR-AV-08 | Recovery Time Objective (RTO) | **≤ 4 h** to restore service after a full regional or database loss | Proposed | Matches a single-region design. Reception can fall back to a paper list for a few hours. |
| NFR-AV-09 | Backups | Automated daily backups plus point-in-time restore, **retained 30 days**; a weekly copy kept **in a second region for 90 days**; a restore test **every quarter** | Proposed | Protects against accidental deletion and ransomware, not only hardware failure. Untested backups don't count. |
| NFR-AV-10 | File storage durability | Signed documents and medical certificates on storage with **≥ 11 nines** durability and soft-delete/versioning enabled for **30 days** | Derived (INT-04, BR-GEN-1) | Both S3 and Azure Blob meet this by default. Versioning covers accidental overwrites. |
| NFR-AV-11 | Restoring one tenant | Restore **one tenant's** data to a point in time **without rolling back other tenants**, within **1 business day** | Proposed | In a shared database, a full restore would undo every other gym's work. The usual way is to restore a copy of the database and copy that tenant's rows back. Prepare and test the script before Stage 1. |
| NFR-AV-12 | Incident communication | A public status page; affected gym Admins notified within **30 min** of a confirmed outage, and a short incident report within **5 business days** | Proposed | Gyms are paying customers; they need to tell their own clients what is happening. |

---

## 2. Performance

The BRD has no performance targets. Targets below are **server-side** (from request received to response sent, measured by the API's own telemetry) under the §3 peak load, unless stated otherwise.

### 2.1 API response time

| ID | Endpoint class | p50 | p95 | p99 | Source | Rationale |
|---|---|---|---|---|---|---|
| NFR-PF-01 | Simple reads (profile, session details, membership status, a single plan) | **≤ 80 ms** | **≤ 250 ms** | **≤ 600 ms** | Proposed | Single-row or indexed lookups. Feels instant on mobile once network latency (≈ 30–150 ms from Argentina, depending on region; see §5) is added. |
| NFR-PF-02 | List & search (class schedule for a week, exercise search, client list for staff), paginated | **≤ 120 ms** | **≤ 400 ms** | **≤ 900 ms** | Proposed | Joins and filters over a few thousand rows; must stay fast with all Stage 2 tenants (≈ 15,000 clients) in one shared database, so every index starts with `TenantId`. |
| NFR-PF-03 | Booking writes (book, cancel, join waitlist, accept offer, check-in) | **≤ 150 ms** | **≤ 500 ms** | **≤ 1,000 ms** | Derived (BR-BK-2) | Capacity is enforced atomically, which adds a lock or a conditional update. Check-in happens at a queue at the desk, so it must not stall. |
| NFR-PF-04 | Other writes (create routine, schedule series, record payment) | **≤ 200 ms** | **≤ 600 ms** | **≤ 1,500 ms** | Proposed | Includes audit-log write (FR-AUD-01) in the same transaction. A recurring series creating up to 52 sessions sits in this class. |
| NFR-PF-05 | Sign-in (password hash + optional 2FA check) | **≤ 300 ms** | **≤ 800 ms** | **≤ 1,500 ms** | Proposed | Password hashing is deliberately slow (§4); this budget leaves room for it. |
| NFR-PF-06 | Financial export (FR-FIN-04) | — | **≤ 10 s** for up to 12 months of one branch | — | Proposed | Larger ranges run as a background job and the file is delivered by link, so an export never blocks a request thread. |
| NFR-PF-07 | File upload (medical certificate, exercise media) | — | API acknowledges in **≤ 2 s** after the client finishes the upload | — | Proposed | Upload goes direct to storage with a pre-signed URL; the API only records metadata. Limits: documents ≤ **10 MB** (PDF/JPG/PNG), images ≤ **5 MB**, video ≤ **100 MB**. |
| NFR-PF-08 | Error rate | **< 0.5 %** of requests return 5xx in any 1-hour window | — | — | Proposed | Paired with latency so that "fast failures" don't look healthy. |

### 2.2 Time-sensitive processing

| ID | Requirement | Target | Source | Rationale |
|---|---|---|---|---|
| NFR-PF-09 | Waitlist offer sent after a spot frees | **≤ 60 s** (p95) to hand the message to the WhatsApp API | Derived (FR-BK-05) | The client has only 30 min to accept; every minute of delay is lost decision time. |
| NFR-PF-10 | Waitlist offer expiry processed | **≤ 60 s** after the window closes | Derived (FR-BK-06) | The next client's 30 minutes must start promptly. |
| NFR-PF-11 | Transactional notifications (booking confirmed/cancelled, session cancelled) | Handed to the provider in **≤ 2 min** (p95) | Proposed | Clients expect near-real-time confirmation; a session cancellation may concern clients already on their way. |
| NFR-PF-12 | No-show marking | Within **15 min** after the session ends | Derived (FR-BK-11) | Fast enough for the professor and reception to act the same day. |
| NFR-PF-13 | Scheduled reminders (document/membership expiry) | Sent once a day at **10:00 branch local time** | Proposed | Avoids night-time WhatsApp/push messages. |

### 2.3 Page load (client applications)

This repository is the backend only, but the backend sets the limits the apps can reach. These targets are shared with the front-end teams.

| ID | Requirement | Target | Source | Rationale |
|---|---|---|---|---|
| NFR-PF-14 | Web apps (admin panel, client web) | Google Core Web Vitals "good" at the **75th percentile**: **LCP ≤ 2.5 s**, **INP ≤ 200 ms**, **CLS ≤ 0.1**, on a mid-range phone over 4G | Proposed | Industry standard thresholds; also what search ranking uses for the client web app. |
| NFR-PF-15 | Mobile app (from Phase 2) | Cold start to a usable home screen **≤ 2 s**; class schedule screen **≤ 1.5 s** on 4G | Proposed | Typical expectation for a booking app used on the spot. |
| NFR-PF-16 | Backend support for the above | Responses compressed (Brotli/gzip); list endpoints paginated (**default 20, max 100** items); one request is enough to render each main screen (no chains of > 2 dependent calls); static media served through a CDN | Proposed | Payload size and round-trips dominate page load on mobile networks more than server time does. |

---

## 3. Scalability

| ID | Requirement | Target | Source | Rationale |
|---|---|---|---|---|
| NFR-SC-01 | Concurrent users | **Stage 0: 30 · Stage 1: 250 · Stage 2: 1,500** concurrent active users with §2 targets met | Proposed | ≈ 10 % of the platform's active clients in the same peak hour, plus staff. All gyms share Argentina's peak hours. |
| NFR-SC-02 | Scaling method | Move from one stage to the next by **adding API instances and resizing the database only** (no code change) | BRD (NFR-09) | The API must be stateless (no in-memory sessions, locks or timers) so any instance can serve any tenant. |
| NFR-SC-03 | Sustained throughput | **Stage 0: 10 req/s · Stage 1: 80 req/s · Stage 2: 500 req/s**, with §2 targets met | Proposed | Concurrent users × one request every ~3 s. Load-tested at **2×** the next stage's value before reaching it. |
| NFR-SC-04 | Data growth (database) | Plan for **≈ 0.2 GB/year per 1,000 clients**, i.e. ≈ 3 GB/year at Stage 2; the DB must handle **5 years** of data without archiving | Proposed | Per 1,000 clients: bookings ≈ 1,000 × 3 × 52 ≈ 156 k rows/year; progress logs ≈ 270 k rows/year; audit log capped by its 4-month retention (FR-AUD-02). Small volumes for any relational database, even shared. |
| NFR-SC-05 | Data growth (file storage) | Plan for **≈ 3 GB/year of documents per 1,000 clients**, plus exercise media; a per-tenant media quota (e.g. **10 GB** included) | Proposed | One medical certificate per client per year (~1–2 MB) plus waivers, consents and photos. Video dominates and varies by gym, so it needs a quota; compress video on upload. |
| NFR-SC-06 | Peak scenario A: contested booking | **100 clients** trying to book the last spots of one session within the same **10 s**: zero overbooking, every loser gets a clear "full, join waitlist" answer, p95 ≤ 1 s | Derived (BR-BK-2, FR-BK-03 AC) | Popular evening classes open 14 days ahead at the same clock time as the session, so the first minute after opening is the hot spot. |
| NFR-SC-07 | Peak scenario B: evening rush | **3×** the average hourly load between 18:00 and 21:00 ART, with §2 targets met | Proposed | Gyms concentrate traffic in two daily peaks; morning is usually smaller. |
| NFR-SC-08 | Peak scenario C: mass notification | A cancelled session notifies up to **room capacity (≤ 100 clients)** within **2 min**; a gym-wide notice to **5,000 clients** completes within **30 min** without slowing the API or other gyms' notifications | Derived (FR-CL-07) | Notifications run in background workers, queued fairly per tenant and rate-limited to stay under WhatsApp/email provider limits. |
| NFR-SC-09 | Peak scenario D: start of month | Membership renewals, payment recording and overdue checks on the **1st–5th** of each month, at **2×** normal staff write load | Proposed | Monthly tiers and the 5-day grace period (FR-MEM-05) cluster financial activity. |
| NFR-SC-10 | Tenant and branch onboarding | Adding a gym or a branch is **configuration only** (no deployment, no new infrastructure); a new gym is usable within **1 business day** of signing | Derived (NFR-04, FR-TEN-01) | This is what makes the shared model cheap per gym. |
| NFR-SC-11 | Noisy neighbour protection | Per-tenant API rate limit (default **20 req/s** sustained, burst **60**) and per-tenant fair queuing of background jobs; one tenant's export, import or notification burst cannot push another tenant beyond its §2 targets | Proposed | In a shared backend, the biggest gym must not slow down the smallest. |
| NFR-SC-12 | Per-tenant usage metrics | Active clients, requests, storage and WhatsApp messages recorded **per tenant per day** | Proposed | Needed to spot noisy neighbours, plan the next stage, and later price and bill the gyms (BRD §1.3). |

---

## 4. Security

The BRD states the principles (NFR-01, NFR-02, FR-AUTH-01..04, FR-ROLE-*, BR-DOC-3). This section makes them testable.

### 4.1 Authentication

| ID | Requirement | Target | Source | Rationale |
|---|---|---|---|---|
| NFR-SE-01 | Sign-in methods | Email + password (Phase 1); Google and Apple via OpenID Connect (Phase 2) | BRD (FR-AUTH-01/02) | — |
| NFR-SE-02 | Tokens | One account can belong to several gyms (BRD BR-GEN-3), so access tokens carry the **gym currently selected**; switching gym issues a new access token without a new sign-in, and a token issued for one gym is rejected for any other. **Short-lived access token (JWT, 15 min)** + **rotating refresh token** (30 days mobile, 12 h staff web panel), revocable server-side; reuse of an old refresh token revokes the whole token family | Proposed | Three apps (web + mobile) need a token model rather than cookies only. Short access tokens limit damage if one leaks; the shorter staff lifetime reflects their wider permissions. Web apps keep the refresh token in an **HttpOnly, Secure, SameSite** cookie, never in local storage. |
| NFR-SE-03 | Two-factor authentication | **TOTP** (authenticator app) required for an account that is Platform admin, or Admin, Accountant or Receptionist in any gym; optional for others; **10 one-time recovery codes** per user | BRD (FR-AUTH-03) | TOTP avoids SMS cost and SIM-swap risk. |
| NFR-SE-04 | Password policy | Minimum **10 characters**, checked against a breached-password list; no forced periodic rotation; hashed with **ASP.NET Core Identity's PBKDF2 (≥ 100,000 iterations) or Argon2id** | Proposed | Follows NIST SP 800-63B. The project is ASP.NET Core, so Identity's hasher is the low-effort default. |
| NFR-SE-05 | Brute-force protection | Account lockout for **15 min after 5** failed attempts; sign-in and password-reset endpoints rate-limited to **10 requests/min per IP** | Proposed | Stops credential stuffing without locking out the front desk for long. |
| NFR-SE-06 | Password reset | Single-use link, valid **30 min**; the response is identical whether the email exists or not | Derived (FR-AUTH-04) | Prevents account enumeration. |
| NFR-SE-07 | Impersonation | Admin "act as" sessions are limited to **30 min**, visibly flagged in every response, and every action is audited with both identities | Derived (FR-ROLE-04) | Makes the strongest privilege in the system traceable and time-boxed. |

### 4.2 Authorization

| ID | Requirement | Target | Source | Rationale |
|---|---|---|---|---|
| NFR-SE-08 | Model | **Permission-based RBAC**: roles are sets of permissions; a user's permissions are the union of their roles; endpoints check **permissions, not role names** | BRD (FR-ROLE-01..03) | Custom roles (FR-ROLE-02) only work if the code checks permissions. |
| NFR-SE-09 | Resource-level checks | "own" and "assigned" rules from the §3.2 matrix are enforced **in the API on every request** (e.g. ASP.NET Core policy + resource handlers), never only in the UI | BRD (§3.2) | Prevents IDOR: a client changing an ID in the URL to read another client's data. |
| NFR-SE-10 | Field-level restriction | Accountant responses contain only name and contact fields of clients; medical certificates are returned only to Admin, Receptionist and assigned professors | BRD (§3.2, BR-DOC-3) | Enforced by separate response models per role, covered by automated tests. |
| NFR-SE-11 | Default deny | Every endpoint requires an authenticated user unless explicitly marked public (sign-in, password reset, health); a test fails the build if an endpoint has no authorization policy | Derived (NFR-01) | Turns "every endpoint" into something CI can check. |
| NFR-SE-12 | Branch isolation | Within a tenant, staff only see data of branches they are assigned to (Admin: all branches of their tenant) | Proposed | Needed once a gym opens a second branch; cheap to build in now. |

### 4.2a Tenant isolation

This is the highest-impact security risk of the shared model: one bug can expose one gym's clients, health documents or payments to another gym.

| ID | Requirement | Target | Source | Rationale |
|---|---|---|---|---|
| NFR-SE-25 | Isolation in the data layer | Every tenant-owned table has a non-null `TenantId`. The only shared tables are **accounts** (email, password hash, 2FA, social logins, language) and platform records; all personal data a gym keeps lives in its **gym profile**, which is tenant-owned. The data layer the data layer (e.g. EF Core global query filters, with PostgreSQL row-level security as a second line of defence) applies the current tenant to **every** query and write; code cannot bypass it except in reviewed platform-only code | BRD (FR-TEN-02, NFR-08) | Relying on each endpoint to remember a `WHERE TenantId = …` fails sooner or later. Two independent layers catch each other's mistakes. |
| NFR-SE-26 | Isolation everywhere else | The tenant applies to **file paths** (one folder/prefix per tenant), **cache keys**, **background jobs** (each job carries and restores its tenant), **logs and traces** (tagged with tenant), **exports** and **notifications** | BRD (FR-TEN-02) | Leaks usually happen outside the main queries: a job without a tenant, or a shared cache key. |
| NFR-SE-27 | Isolation tests | Automated tests create two tenants and check that **every endpoint** returns "not found" for the other tenant's IDs; the build fails if a new tenant-owned table has no filter | Proposed | Turns FR-TEN-02 into something CI checks on every change. |
| NFR-SE-32 | No cross-gym leaks through accounts | Creating a profile with an email that already has an account gives the **same response and timing** as a new email; gyms never see an account's other gyms, sign-in history or profile data from elsewhere | BRD (FR-TEN-02, FR-TEN-10) | A shared account is the one place where gyms touch the same record. Without this rule, staff could probe which of their clients also train at a competitor. |
| NFR-SE-33 | Invitations and QR codes | Invitation links and gym QR codes contain only a **random, unguessable token** (no gym or person data); invitation tokens are single-use and expire (BRD §6, default 7 days); a gym can **rotate** its reception QR code at any time; joining by QR always needs staff approval | BRD (FR-TEN-10) | A photo of the reception QR shared online must not let strangers join a gym or learn anything about it. |
| NFR-SE-28 | Unique identifiers | Public IDs are **random (UUID)**, never sequential | Proposed | Sequential IDs reveal other gyms' volumes and make guessing other tenants' records easier. |
| NFR-SE-29 | Platform admin and support access | Platform admin accounts are separate from gym accounts and require 2FA; support access to a tenant (FR-TEN-07) lasts at most **24 h**, is granted by that tenant's Admin, and is visible to them in their audit log | BRD (FR-TEN-07) | The platform owner is the only actor who could reach every gym, so that access must be exceptional and visible. |

### 4.3 Data protection

| ID | Requirement | Target | Source | Rationale |
|---|---|---|---|---|
| NFR-SE-13 | Encryption in transit | **TLS 1.2 minimum, TLS 1.3 preferred**; HSTS with 1-year max-age; no plain HTTP except redirect | BRD (NFR-01) | — |
| NFR-SE-14 | Encryption at rest | Database, backups and file storage encrypted with **AES-256** (provider-managed keys at launch) | BRD (NFR-01) | Free and on by default on both AWS and Azure. |
| NFR-SE-15 | Sensitive fields | National ID numbers (client and guardian) and date of birth additionally **encrypted at column level**; health documents stored in a **private** bucket/container | Proposed | Health data is "sensitive data" under Ley 25.326 (art. 2 and 7); a database dump alone should not expose it. |
| NFR-SE-16 | Document access | Files are served only through **pre-signed URLs valid ≤ 5 min**, generated after the permission check; every download is audit-logged | Derived (BR-DOC-3) | Storage URLs are never public or long-lived. |
| NFR-SE-17 | Secrets | No secrets in source or images; stored in **Azure Key Vault / AWS Secrets Manager**; rotated at least **yearly** and immediately after staff with access leave | Proposed | — |
| NFR-SE-34 | Links and WhatsApp replies for clients without an account (Phase 1) | Signing links and offer-acceptance links use a **random single-use token**, valid only for that action and at most **48 h** (an offer link expires with the offer); a WhatsApp reply is accepted only from the **phone number the offer was sent to**, and only for that offer; the page behind a link shows the minimum data needed (gym name, session, first name) | BRD (§9.1, FR-BK-05, FR-DOC-03) | In Phase 1 the link or the phone number is the client's only proof of identity, so a forwarded link must not expose more than that one action. |
| NFR-SE-18 | Logging hygiene | Application logs contain **no** passwords, tokens, ID numbers or document contents; log retention **30 days** | Proposed | Logs are usually the least protected copy of data. |

### 4.4 Compliance

| ID | Requirement | Target | Source | Rationale |
|---|---|---|---|---|
| NFR-SE-19 | Argentina personal data law (**Ley 25.326**) | Each gym is the **data controller** of its clients' data and registers its database with the **AAIP** (Registro Nacional de Bases de Datos); the platform collects informed consent at account creation on the gym's behalf; it lets the gym answer access requests within **10 calendar days** and rectification/deletion within **5 business days** | BRD (NFR-02) | These are the statutory deadlines (art. 14 and 16). The API needs a "data export for one client" and an "anonymize client" operation to meet them. |
| NFR-SE-30 | Platform as data processor | The platform owner acts as **data processor** (art. 25) for every gym: a signed **data processing agreement** per gym before onboarding, covering purpose, security measures, sub-processors (cloud, WhatsApp, email) and what happens to data when the contract ends | Proposed | Art. 25 lets a service provider process data on behalf of the controller only under such terms. **Confirm with legal counsel.** |
| NFR-SE-31 | Tenant offboarding | On request, a full export of the tenant's data (CSV/JSON + documents) within **10 business days**; deletion of all its data, including from backups as they expire, **90 days** after the contract ends unless the gym asks for earlier deletion | BRD (FR-TEN-08) | Backups can't be edited, so "deleted from backups" means "aged out" within the 30/90-day backup retention (NFR-AV-09). |
| NFR-SE-20 | Minors | Guardian consent (FR-DOC-04) is stored with the consent text version and timestamp | Derived | Proof of consent must survive changes to the form. |
| NFR-SE-21 | International data transfer | If hosting outside Argentina (e.g. Brazil or US regions), use the **AAIP model contractual clauses** with the cloud provider, or obtain explicit consent | Proposed | Neither Brazil nor the US is on Argentina's adequacy list. **Confirm with legal counsel.** |
| NFR-SE-22 | Payment card data | **No card data stored or processed** in Phase 1 (card at the counter only). When the gateway is added, use hosted fields / redirect so the system stays at **PCI DSS SAQ A** scope | Derived (FR-FIN-01, FR-FIN-05) | Keeps PCI out of the system entirely. |
| NFR-SE-23 | Retention conflict to resolve | Audit records for **payment and membership changes** kept for **10 years** instead of 4 months | Proposed | FR-AUD-02 purges audit at 4 months, but Argentine commercial law (Civil and Commercial Code, art. 328) requires keeping accounting support for 10 years. **Confirm with the accountant.** |
| NFR-SE-24 | Security baseline & testing | Meet **OWASP ASVS Level 2**; dependency and container-image scanning on every build (no known **critical/high** CVEs at release); an external penetration test before go-live | Proposed | ASVS L2 is the recommended level for apps holding personal and health data. |

---

## 5. Cost & Hosting

The BRD gives no budget. Azure is the preferred provider (BRD §10), and the backend must stay portable (NFR-05, INT-04). In the shared model most costs are **fixed** (they don't depend on the number of gyms), so the key metric is **cost per gym**, which falls as gyms are added.

| ID | Requirement | Target | Source | Rationale |
|---|---|---|---|---|
| NFR-CO-01 | Infrastructure budget per stage | **Stage 0: ≤ USD 50 / month · Stage 1: ≤ USD 200 / month · Stage 2: ≤ USD 800 / month** for production. No permanent staging environment at Stage 0; **≤ USD 30 / month** for staging from Stage 1 | Proposed | Matches the estimates in §5.1. At Stage 0, testing runs locally with Docker Compose (`compose.yaml`). |
| NFR-CO-02 | Cost per gym | Infrastructure cost **≤ USD 20 per gym per month** from Stage 1 onwards, falling as gyms are added | Proposed | Leaves a healthy margin whatever price is charged to gyms (BRD §1.3). Tracked with the per-tenant usage metrics (NFR-SC-12). |
| NFR-CO-03 | Hosting model | **Managed cloud, not self-hosted**: managed container service + managed relational database + object storage | Proposed | A small team cannot cheaply provide patching, backups and 99.5 % on self-managed servers. |
| NFR-CO-04 | Subscriptions | All tenants run in **one Azure subscription owned by the platform owner**; gyms have no Azure access. Production and non-production live in separate resource groups (separate subscriptions from Stage 1) | Proposed | The shared model has one deployment, so one subscription is enough. A separate non-production subscription stops a test mistake from touching production. |
| NFR-CO-05 | Region | **Azure Brazil South** (São Paulo) | Proposed | ≈ 30–40 ms round-trip from Buenos Aires vs. ≈ 130–160 ms from US East, which matters for the §2 mobile targets. Brazil South costs ≈ 30–50 % more than US East; at Stage 0 that is about USD 10 / month. Revisit with NFR-SE-21. |
| NFR-CO-06 | Portability | Only portable building blocks: **Docker containers, PostgreSQL**, blob storage behind the storage abstraction, OpenTelemetry for observability. No provider-specific SDKs outside adapter classes | BRD (NFR-05, INT-04) | Allows a move to another provider with configuration and adapters only. PostgreSQL is available managed on every major cloud and has no licence cost. |
| NFR-CO-07 | Messaging cost cap | WhatsApp sent **only** for waitlist offers and urgent events (session cancelled); everything else by push/email first. Alert when one tenant's monthly WhatsApp spend exceeds **USD 20** or the platform's exceeds **USD 100** | Proposed | Meta charges per template message, and it is the only cost that grows directly with each gym's activity. Push (FCM/APNs) is free; email costs fractions of a cent. |
| NFR-CO-08 | Cost monitoring | Azure budget alerts at **80 %** and **100 %** of NFR-CO-01; resources tagged by environment | Proposed | — |
| NFR-CO-09 | Stage upgrade triggers | Move to the next stage's sizing when any of these lasts **7 days**: database CPU > **70 %** at peak, API p95 above the §2 targets, database storage > **75 %** full, or memory > **80 %** | Proposed | Upgrades are driven by measurements, not by the number of gyms signed. |

### 5.1 Indicative monthly estimate per stage (Azure, Brazil South, production)

Approximate list prices. **Verify with the Azure pricing calculator before committing.**

| Item | Stage 0: soft start (1 gym) | Stage 1: ≈ 10 gyms | Stage 2: ≈ 50 gyms |
|---|---|---|---|
| **API + background worker**: Azure Container Apps (consumption plan; the monthly free allowance covers part of Stage 0) | 1 replica, 0.25 vCPU / 0.5 GB: **5–15** | 2 replicas, 0.5 vCPU / 1 GB: **40–70** | 3–6 replicas, 1 vCPU / 2 GB: **150–250** |
| **Database**: Azure Database for PostgreSQL Flexible Server, single zone, PITR backups | Burstable B1ms (1 vCore, 2 GB, 32 GB): **15–25** | Burstable B2s (2 vCores, 4 GB, 64 GB): **40–60** | General Purpose D2ds (2 vCores, 8 GB, 128 GB), zone-redundant optional: **150–300** |
| **Blob storage** (+ CDN from Stage 1) | **< 1** | **5–10** | **20–40** |
| **Container images** (GitHub Container Registry, or Azure Container Registry Basic ≈ 5) | **0–5** | **5** | **5** |
| **Key Vault, Application Insights / Log Analytics** (5 GB/month free) | **0–2** | **5–15** | **20–50** |
| **Email** (Azure Communication Services) | **< 1** | **1–3** | **5–15** |
| **WhatsApp** (usage-based, waitlist offers and cancellations only) | **2–5** | **15–40** | **60–150** |
| **Domain** (TLS certificates are free and managed) | **≈ 1** | **≈ 1** | **≈ 1** |
| **Total** | **≈ 25–50** | **≈ 110–200** | **≈ 410–810** |
| **Per gym** | ≈ 25–50 | **≈ 11–20** | **≈ 8–16** |

Notes:

- **Azure free account (first 12 months):** includes 750 hours a month of the B1ms PostgreSQL tier, which brings Stage 0 to about **USD 5–20 / month** in the first year.
- **Stage 0 trade-offs:** one API replica means a crash causes a minute or two of downtime while it restarts; a burstable database slows down under sustained load. Both are acceptable for one small gym, and the 99.5 % target (NFR-AV-01) is still reachable. From Stage 1, **2 replicas** keep zero-downtime deployments and survive an instance failure.
- **Background jobs must stay on**: waitlist expiry and no-show marking (NFR-AV-05) need at least one always-running worker, so the API cannot scale to zero in production.
- Stage 2 is driven mostly by WhatsApp volume and the larger database. By then, per-tenant metrics (NFR-SC-12) will show the real figures to refine the budget and the price charged to gyms.

### 5.2 Why one subscription and one database

| Option | Cost per extra gym | Effort to run | Chosen |
|---|---|---|---|
| **Shared backend + shared database** (`TenantId` on every row) | ≈ USD 0–5 | One deployment, one database to back up and migrate | ✅ (BRD NFR-04) |
| Shared backend, one database per gym | ≈ USD 2–10 | Migrations and backups multiply per gym | Possible later for a gym that demands physical separation |
| Full copy per gym (own resources or own Azure subscription) | ≈ USD 25–40+ | N deployments to update, monitor and back up | Only for a large chain, as a premium "dedicated" offer |

Because the tenant is a column, a single gym can later be **moved** to its own database by copying its rows, without changing the application. Starting shared doesn't rule out the other options.

---

## 6. Open decisions needed to close this document

| # | Decision | Owner | Blocks |
|---|---|---|---|
| 1 | Confirm the §0.2 growth stages (gyms, clients, opening hours, peak hours) | Business | §1–§3, §5 |
| 2 | Accept 99.5 % availability, or pay for 99.9 % (≈ 2× infrastructure cost); when to revisit | Business | NFR-AV-01, NFR-CO-01 |
| 3 | Monthly infrastructure budget per stage | Business | NFR-CO-01/02 |
| 4 | Confirm Azure and Brazil South; legal basis for data transfer to Brazil | Business + legal | NFR-CO-05, NFR-SE-21 |
| 5 | Audit retention for financial records (4 months vs. 10 years) | Accountant + legal | NFR-SE-23, FR-AUD-02 |
| 6 | Data processing agreement template for gyms; offboarding retention (90 days proposed) | Legal | NFR-SE-30/31 |
| 7 | Per-tenant limits: API rate limit, media quota, WhatsApp cap | Business | NFR-SC-05, NFR-SC-11, NFR-CO-07 |
| 8 | Database engine (PostgreSQL recommended) | Architecture | NFR-CO-06 |
