Title: Gym Backend Business Requirements
Author: Rodrigo Tristany
Version: 3.2
Date: 11-20-2026
Status: Draft. v2.0 was approved for architecture; the multi-tenancy changes in v3.0 need review (see §10)

# Gym Backend

## 1. Purpose & Scope

This document defines the business requirements for the backend of a **multi-tenant gym management platform**. The platform is sold to several gyms (**tenants**). Each gym has one or more branches, its own users, settings and data, and never sees another gym's data. All gyms are served by **one backend and one database**.

The backend serves three applications:

- an **admin/staff web panel**
- a **client mobile app** (from Phase 2)
- a **client web app** (from Phase 2)

In Phase 1 only staff sign in; clients are reached by WhatsApp and email (§9).

### 1.1 In scope

- Tenants (gyms): onboarding by the platform owner, data isolation, per-gym settings and branding
- User accounts, authentication and configurable roles
- Exercise catalog, routines, class types, rooms and class scheduling
- Class booking, waitlist, cancellation and attendance
- Professor assignments, client exercise plans and progress logging
- Client documents: medical certificate, waiver, liability contract, guardian consent
- Memberships, booking limits, payment recording and financial export
- Notifications (email, WhatsApp, push), calendar sync and the audit log

### 1.2 Out of scope (for now)

- Personal training (1:1 sessions)
- Membership freeze
- Gym opening hours and holiday constraints
- Local tax and fiscal invoicing
- Client self-registration
- Gym self-registration (gyms are onboarded by the Platform admin)

### 1.3 Deferred decisions (the design must allow adding them later)

- Online payment gateway and recurring billing
- Billing the gyms for using the platform (subscription plans, invoicing)
- Check-in hardware device and vendor
- Expected scale per stage (Azure is the preferred cloud provider; see `NonFunctionalRequirements.md` §5)

---

## 2. Glossary

| Term | Definition |
|---|---|
| **Platform** | The whole system, operated by its owner, serving every tenant. |
| **Tenant (gym)** | A customer company using the platform. It owns its branches, users, settings, catalog and data. Data never crosses tenants. |
| **Branch** | A physical location of a tenant. A tenant has one or more branches; a small gym has exactly one. |
| **Account** | A person's single sign-in for the whole platform: email, password, 2FA, social logins and language. One account can belong to several gyms. It holds no gym data. |
| **Gym profile** | The data one gym keeps about a person (name, phone, ID number, date of birth, emergency contact, documents, memberships) and the person's roles in that gym. A person who trains at two gyms has one account and two gym profiles, which never see each other. |
| **Gym invitation** | A link or QR code that connects an account to a gym. It can be sent by staff (email or WhatsApp) or shown at the gym's reception. |
| **Room** | A space inside a branch where class sessions take place. It has a capacity. |
| **Exercise** | A single movement (e.g. squat) with a name, description, muscle group, equipment and optional media. |
| **Routine** | An ordered list of exercises, each with parameters (sets, reps, weight, rest, duration). |
| **Class type** | A kind of group class (e.g. Yoga) with a default duration and capacity. |
| **Class session** | A dated occurrence of a class type, in a room, run by a professor. It may be part of a recurring series. |
| **Booking** | A client's reservation of a spot in a class session. |
| **Waitlist** | An ordered queue of clients waiting for a spot in a full session. |
| **Assignment** | Exercises or routines that a professor prescribes to one of their assigned clients. |
| **Exercise plan** | A calendar of dated items (class types or sessions, routines, exercises) that a client builds for themself. |
| **Progress log** | A client's record of a completed workout (e.g. 3×10 at 50 kg on a given date). |
| **Membership** | A client's subscription to a membership tier for a period, or a credit balance. |
| **Membership tier** | A sellable product: monthly, annual, class pack or drop-in, with its own booking limits. |
| **Medical certificate** | A document certifying that the client is fit to exercise ("apto físico"). It is valid for one year. |
| **Waiver** | The general gym terms the client signs. |
| **Liability contract** | A document in which the client accepts responsibility for the routines, exercises and plans they create themself. |
| **Guardian consent** | A guardian's details and signed consent, required for minor clients. |

---

## 3. Actors & Roles

### 3.1 Built-in roles

There are two levels of roles:

- **Platform level**: the **Platform admin** (the platform owner) manages tenants. It is not part of any gym.
- **Gym level**: every other role exists **inside one tenant**, and its permissions apply only to that tenant's data.

Gym-level roles are **locked**: they cannot be edited or deleted. A gym's Admin can create **custom roles** with their own permission sets on top of them. A user **can hold several roles** at once within a gym, and can **belong to several gyms with different roles in each** (e.g. Professor at gym A and Client at gym B). Permissions always come from the gym the user is currently working in.

| Role | Level | Summary |
|---|---|---|
| **Platform admin** | Platform | Creates, configures, suspends and offboards tenants, and creates each tenant's first Admin. Sees platform health and usage. Has **no access to gym data**, except through audited support access granted by the gym (FR-TEN-07). |

| Role | Summary (gym level, always limited to the user's own tenant) |
|---|---|
| **Admin** | Full access to the whole gym (all its branches), including acting on behalf of any user of the gym. Manages staff, roles and settings. |
| **Receptionist** | Front-desk operations: client accounts, check-in, bookings on behalf of clients, payment recording, documents, client↔professor assignment. |
| **Professor** | Manages the content they own (exercises, routines, class types, sessions). Works with the clients assigned to them. |
| **Accountant** | Manages memberships and financial records. Can see client names and contact details only. |
| **Client** | Books classes, builds exercise plans, logs progress, and sees their own memberships and payments. |

### 3.2 Permission matrix

Every permission below applies **only within the user's own tenant**. The Platform admin has no column because it has no access to gym data; its permissions are listed in §3.3.

Legend: **C**reate · **R**ead · **U**pdate · **D**elete (archive) · **own** = records the user owns or that belong to them · **assigned** = clients assigned to the professor · **—** = no access

| Resource | Admin | Receptionist | Professor | Accountant | Client |
|---|---|---|---|---|---|
| Staff accounts & roles | CRUD | — | — | — | — |
| Client accounts | CRUD | CRU | R assigned | R (name, contact) | R/U own profile |
| Client↔Professor assignment | CRUD | CRUD | C/D (self) | — | R own |
| Exercises | CRUD | R | C, R, U/D own | — | R; CRUD own¹ |
| Routines | CRUD | R | C, R, U/D own | — | R; CRUD own¹ |
| Class types | CRUD | R | C, R, U/D own | — | R |
| Rooms & branches | CRUD | R | R | — | R |
| Class sessions | CRUD | R | C, R, U/D own | — | R |
| Class transfer (change owner) | Yes | — | Own classes | — | — |
| Bookings & waitlist | CRUD | CRUD | R own sessions | — | C/R/D own |
| Attendance / check-in | CRUD | CRU | R own sessions | — | C own² |
| Assignments | CRUD | R | CRUD for assigned clients | — | R own |
| Exercise plans | CRUD | R | R assigned | — | CRUD own¹ |
| Progress logs | R | — | R assigned | — | CRUD own |
| Medical certificate, waiver, guardian consent | CRUD | CRU (upload, approve) | R assigned | — | C/R own |
| Liability contract | R | R | — | — | C/R own (sign) |
| Membership tiers | CRUD | R | — | CRUD | R |
| Client memberships | CRUD | CR | — | CRUD | R own |
| Payments | CRUD | C, R | — | CRUD | R own |
| Financial export | Yes | — | — | Yes | — |
| Settings | CRUD | — | — | — | — |
| Audit log | R | — | — | — | — |

¹ Only after the client has signed the liability contract (BR-DOC-4).
² Self check-in on a hardware device; deferred (see §10).

### 3.3 Platform permissions

| Resource | Platform admin | Gym roles |
|---|---|---|
| Tenants (create, configure, suspend, offboard) | CRUD | — |
| A tenant's first Admin account | C | — |
| Tenant settings and branding | CRUD | Admin: R/U own tenant |
| Platform usage and health metrics | R | — |
| Platform audit log (tenant lifecycle, support access) | R | — |
| Gym data (clients, bookings, documents, payments…) | Only through support access (FR-TEN-07) | See §3.2 |

---

## 4. Functional Requirements

Priority uses MoSCoW: **M** = Must, **S** = Should, **C** = Could.

### 4.0 Tenancy (TEN)

| ID | Requirement | Pri |
|---|---|---|
| FR-TEN-01 | The Platform admin creates a tenant (name, legal name, tax ID, contact, default language, time zone, currency) and its first branch and Admin account. | M |
| FR-TEN-02 | **Every record belongs to exactly one tenant**, except the account (sign-in identity) and platform records. No user, query, report, export, notification, file or background job can read or change another tenant's data. A gym cannot tell whether one of its users also belongs to another gym. | M |
| FR-TEN-03 | Each tenant has its own settings (§6), membership tiers, roles, catalog (exercises, routines, class types) and documents (waiver and liability contract texts). | M |
| FR-TEN-04 | Each tenant has its own branding (name, logo, primary colours), used in the apps and in notifications. | S |
| FR-TEN-05 | Each tenant can send notifications from its own WhatsApp number and email sender address. Until configured, the platform's defaults are used, showing the gym's name. | S |
| FR-TEN-06 | The Platform admin can **suspend** a tenant: its users cannot sign in, and its scheduled jobs and notifications stop. Its data is kept. Reactivation restores access. | M |
| FR-TEN-07 | **Support access:** the platform owner can see a tenant's data only after that tenant's Admin grants time-limited access. Every action during support access is audit-logged in the tenant's audit log. | M |
| FR-TEN-08 | **Offboarding:** when a tenant leaves, the platform provides a full export of its data (structured files and documents), then deletes it after the agreed retention period (see `NonFunctionalRequirements.md` NFR-SE-31). | M |
| FR-TEN-09 | Users sign in **once** with their account. If they belong to one gym, they enter it directly; if they belong to several, they pick the gym and can switch later without signing in again. | M |
| FR-TEN-10 | An account is connected to a gym only through a **gym invitation**: staff send it by email or WhatsApp when they create the person's gym profile, or the person scans the gym's **QR code** in the app and staff approve the request. Invitations expire after **7 days** (configurable). | M |
| FR-TEN-11 | There is **one shared mobile app and one shared client web app** for all gyms. After the user enters a gym, the app applies that gym's branding (FR-TEN-04). Before that, it shows the platform's branding. | M |

**Acceptance criteria (accounts)**

- **FR-TEN-02 / FR-TEN-10**: *Given* a person with an account at gym A, *when* a Receptionist at gym B creates a client with the same email, *then* gym B sees a normal "invitation sent" result, learns nothing about gym A, and the person gets an invitation to connect their existing account to gym B.
- **FR-TEN-09**: *Given* an account that is a Client at gym A and a Professor at gym B, *when* the person switches from A to B, *then* they see only gym B's data, with Professor permissions.

**Acceptance criteria**

- **FR-TEN-02**: *Given* gyms A and B, *when* an Admin of gym A requests a client, booking, document or export by an ID that belongs to gym B, *then* the API responds as if the record did not exist.
- **FR-TEN-06**: *Given* a suspended tenant, *when* any of its users tries to sign in, *then* sign-in is refused, and no waitlist offer or reminder is sent for that tenant.

### 4.1 Authentication & Accounts (AUTH)

| ID | Requirement | Pri |
|---|---|---|
| FR-AUTH-01 | Users sign in with email and password. | M |
| FR-AUTH-02 | Users can sign in with Google and Apple. | S |
| FR-AUTH-03 | Two-factor authentication is **required** for an account that is Platform admin, or Admin, Accountant or Receptionist **in any gym**, and **optional** otherwise. | M |
| FR-AUTH-04 | Users can reset a forgotten password through email. | M |
| FR-AUTH-05 | The **Platform admin** creates each tenant's first Admin. Within a tenant, the **Admin** creates staff profiles, and the **Admin and Receptionist** create client profiles. If the email has no account yet, one is created through the invitation (FR-TEN-10). Clients cannot self-register. | M |
| FR-AUTH-06 | A gym **deactivates** a person's gym profile, never deletes it, so that its history is kept. Deactivating it in one gym does not affect the account or other gyms. | M |
| FR-AUTH-07 | Users choose Spanish or English as their language. | M |

**Acceptance criteria**

- **FR-AUTH-03**: *Given* a Receptionist without 2FA set up, *when* they sign in, *then* they must enrol in 2FA before they can access anything else.
- **FR-AUTH-05**: *Given* a Professor, *when* they try to create a client account, *then* the request is refused.

### 4.2 Roles & Permissions (ROLE)

| ID | Requirement | Pri |
|---|---|---|
| FR-ROLE-01 | The system provides the five built-in roles from §3.1. They cannot be edited or deleted. | M |
| FR-ROLE-02 | The Admin can create, edit and delete custom roles made of permissions. | S |
| FR-ROLE-03 | A user can hold several roles. Their effective permissions are the union of those roles. | M |
| FR-ROLE-04 | The Admin can act on behalf of any user **of the same tenant**. The audit log records both the Admin and the impersonated user. | M |

### 4.3 Branches & Rooms (BR)

| ID | Requirement | Pri |
|---|---|---|
| FR-BRN-01 | Every operational record (rooms, sessions, memberships, payments) belongs to a branch, and every branch belongs to one tenant. | M |
| FR-BRN-02 | The Admin manages branches and rooms (name, capacity) for their own tenant. A tenant starts with one branch. | M |
| FR-BRN-03 | Each branch has a time zone and a currency, inherited from the tenant by default (`America/Argentina/Buenos_Aires`, ARS). | M |

### 4.4 Exercise Catalog (EX)

| ID | Requirement | Pri |
|---|---|---|
| FR-EX-01 | Professors create exercises with a name, description, muscle group(s), equipment and optional image or video. | M |
| FR-EX-02 | Professors edit and archive only the exercises they own. The Admin can edit any exercise. | M |
| FR-EX-03 | Clients who have signed the liability contract can create private exercises for their own use. | S |
| FR-EX-04 | Exercises can be searched and filtered by name, muscle group and equipment. | S |

### 4.5 Routines (RT)

| ID | Requirement | Pri |
|---|---|---|
| FR-RT-01 | Professors create routines: an ordered list of exercises, each with sets, reps, weight, rest and/or duration. | M |
| FR-RT-02 | The same exercise may appear more than once in a routine. | M |
| FR-RT-03 | Clients who have signed the liability contract can create private routines. | S |
| FR-RT-04 | Editing a routine that is in use creates a **new version**. The owner chooses whether to offer the new version to affected clients. Each affected client then accepts it or keeps their current version. | M |

**Acceptance criteria**

- **FR-RT-04**: *Given* routine R (v1) is in two clients' plans, *when* its owner edits R and chooses to offer the update, *then* R v2 is created, both clients are notified, and each client's plan keeps v1 until that client accepts v2.

### 4.6 Classes & Scheduling (CL)

| ID | Requirement | Pri |
|---|---|---|
| FR-CL-01 | Professors create class types with a name, description, default duration and default capacity. | M |
| FR-CL-02 | Professors schedule class sessions (date, time, duration, room, capacity). They can create one-off sessions or **recurring series**. | M |
| FR-CL-03 | Single sessions in a series can be edited or cancelled without affecting the rest of the series. | M |
| FR-CL-04 | The system rejects a session that overlaps another session of the same professor or in the same room. | M |
| FR-CL-05 | Session capacity cannot exceed the room's capacity. | M |
| FR-CL-06 | The owner or the Admin can **transfer** a class type or session to another professor. Existing bookings are kept. | M |
| FR-CL-07 | When the gym cancels or reschedules a session, booked clients are notified, and the cancellation does not count against their monthly cancellation limit. | M |
| FR-CL-08 | When capacity is reduced below the number of bookings, the most recently booked clients are moved to the waitlist and notified. | M |

### 4.7 Booking, Waitlist & Attendance (BK)

| ID | Requirement | Pri |
|---|---|---|
| FR-BK-01 | Clients book sessions. The Receptionist and the Admin can book on a client's behalf. | M |
| FR-BK-02 | Booking opens **14 days** before the session and closes **1 hour** before it (both configurable). | M |
| FR-BK-03 | A booking is allowed only if the client's membership is active and within its tier limits, the client is not blocked, there is free capacity, and the client has no overlapping booking. | M |
| FR-BK-04 | When a session is full, the client can join the **waitlist**. The waitlist closes when booking closes. | M |
| FR-BK-05 | When a spot frees up, the first client in the waitlist receives an **offer by WhatsApp** and has **30 minutes** to accept (configurable). The client accepts with a **reply button in the WhatsApp message**, so no app or account is needed. The offer stays valid even after booking has closed. | M |
| FR-BK-06 | If an offer expires, it goes to the next client in the waitlist. The client who did not answer **keeps their place** in the queue. | M |
| FR-BK-07 | Clients can cancel a booking before the cancellation deadline (configurable). | M |
| FR-BK-08 | Clients can cancel at most **3 times per calendar month** (configurable). After that the client can no longer cancel, and staff is notified to decide. | M |
| FR-BK-09 | The Receptionist checks clients in at the gym (Phase 1). | M |
| FR-BK-10 | Clients check in themselves on a hardware device (Phase 2; the device is deferred). The check-in API is vendor-neutral. | C |
| FR-BK-11 | A booking with no check-in by the end of the session becomes a **no-show**. A no-show notifies the client, the professor, the Receptionist and the Admin. There is no automatic penalty. | M |
| FR-BK-12 | Clients can add their bookings to Google Calendar or iCal. | S |

**Acceptance criteria**

- **FR-BK-03**: *Given* a session with 1 free spot, *when* two clients try to book it at the same moment, *then* exactly one booking succeeds and the other client is offered the waitlist.
- **FR-BK-05**: *Given* a full session with clients A and B on the waitlist, *when* a booked client cancels, *then* A receives a WhatsApp offer. If A does not accept within 30 minutes, B receives the offer and A stays first in the queue.
- **FR-BK-08**: *Given* a client who has already cancelled 3 times this month, *when* they try to cancel again, *then* the request is refused and staff is notified.

### 4.8 Professor Assignments (AS)

| ID | Requirement | Pri |
|---|---|---|
| FR-AS-01 | The Admin, the Receptionist or the professor themself can assign a client to a professor. A client can have **several professors**. | M |
| FR-AS-02 | Professors see only the clients assigned to them. | M |
| FR-AS-03 | Professors assign exercises and routines, with personalised parameters and notes, to their assigned clients. | M |
| FR-AS-04 | Every assignment records which professor made it, and when. | M |

### 4.9 Client Exercise Plans (PL)

| ID | Requirement | Pri |
|---|---|---|
| FR-PL-01 | Clients create exercise plans as **calendars of dated items** (class types or sessions, routines, exercises). | M |
| FR-PL-02 | A client can have **several active plans**. | M |
| FR-PL-03 | Adding a class to a plan does **not** book it. Booking is always a separate step. | M |
| FR-PL-04 | Creating a plan, routine or exercise requires a signed **liability contract**. No professor approval is needed. | M |
| FR-PL-05 | Assigned professors can view their clients' plans. | S |

### 4.10 Progress Logging (LOG)

| ID | Requirement | Pri |
|---|---|---|
| FR-LOG-01 | Clients record completed workouts: the exercise, date, sets, reps, weight and/or duration, and optional notes. | M |
| FR-LOG-02 | A log entry can be linked to an assignment or a plan item. | S |
| FR-LOG-03 | Only the client creates or edits their logs. Assigned professors can view them. | M |

### 4.11 Client Documents (DOC)

| ID | Requirement | Pri |
|---|---|---|
| FR-DOC-01 | Required client data: name, email, phone, date of birth, ID number, emergency contact. | M |
| FR-DOC-02 | A **medical certificate** is uploaded as a file. It is valid for **1 year** from its date. | M |
| FR-DOC-03 | The client signs the **waiver** electronically, through a **single-use signing link** sent by WhatsApp or email (no account needed), or on a device at reception. Staff can also upload a waiver signed on paper. | M |
| FR-DOC-04 | A **minor** client must have guardian details (name, ID number, phone) and a consent form signed by the guardian. | M |
| FR-DOC-05 | The client signs the **liability contract** before creating their own routines, exercises or plans. | M |
| FR-DOC-06 | The Receptionist (or the Admin) uploads and approves the medical certificate and the guardian consent. | M |
| FR-DOC-07 | The system notifies clients before their medical certificate expires. | S |

**Acceptance criteria**

- **FR-DOC-02 / BR-DOC-2**: *Given* a client created 31 days ago without an approved medical certificate, *when* they try to book or check in, *then* the request is refused and they are notified why.

### 4.12 Memberships (MEM)

| ID | Requirement | Pri |
|---|---|---|
| FR-MEM-01 | The Accountant and the Admin manage membership tiers: **monthly, annual, class pack, drop-in**, each with a price. | M |
| FR-MEM-02 | Each tier sets its own **booking limits** (e.g. N classes per week), configurable. | M |
| FR-MEM-03 | Class packs and drop-ins hold **credits**. Each booking uses one credit. A cancellation made in time returns the credit. Credits **never expire**. | M |
| FR-MEM-04 | The Receptionist, the Accountant or the Admin sells or assigns a membership to a client. | M |
| FR-MEM-05 | A membership that is expired or unpaid for longer than the **grace period (5 days, configurable)** blocks booking and check-in. | M |

### 4.13 Payments & Finance (FIN)

| ID | Requirement | Pri |
|---|---|---|
| FR-FIN-01 | The Accountant, the Receptionist and the Admin record payments: amount, method (cash, transfer, card at the counter), date, membership. | M |
| FR-FIN-02 | Only the Accountant and the Admin can edit or void a payment. A void keeps the original record and requires a reason. | M |
| FR-FIN-03 | Clients can view their own payment history and membership status. | M |
| FR-FIN-04 | The Accountant and the Admin can download financial data (payments, memberships) as Excel or CSV, filtered by date range. | M |
| FR-FIN-05 | The payment model must allow an online payment gateway to be added later. | M |
| FR-FIN-06 | Overdue clients are flagged, and they are notified when the grace period begins. | S |

### 4.14 Notifications (NOT)

| ID | Requirement | Pri |
|---|---|---|
| FR-NOT-01 | The system sends notifications by **email, WhatsApp and push**. | M |
| FR-NOT-02 | Waitlist offers are sent by **WhatsApp**. | M |
| FR-NOT-03 | Notification events: booking confirmed or cancelled, session cancelled or rescheduled, waitlist offer, moved to the waitlist, no-show, cancellation limit reached, membership expiring or overdue, document missing or expiring, routine update offered, account blocked. | M |
| FR-NOT-04 | Notifications use the recipient's language (Spanish or English). | M |

### 4.15 Audit & Settings (AUD / CFG)

| ID | Requirement | Pri |
|---|---|---|
| FR-AUD-01 | **Every change** by any user is audit-logged: who, when, what, before and after values, and on whose behalf. | M |
| FR-AUD-02 | Audit records are kept for **4 months** (configurable), then purged. | M |
| FR-AUD-03 | Only the tenant's Admin can read that tenant's audit log. The Platform admin reads only the platform audit log (tenant lifecycle and support access). | M |
| FR-CFG-01 | The Admin manages all configurable settings (§6). | M |

---

## 5. Business Rules

| ID | Rule |
|---|---|
| BR-GEN-1 | Records with history are archived (soft-deleted), never hard-deleted. |
| BR-GEN-2 | Timestamps are stored in UTC and displayed in the branch's time zone. |
| BR-GEN-3 | Email is unique **across the platform**: one email, one account. The same account may belong to several gyms, with a separate gym profile in each. Only the person can change their account's email and password; gyms edit only their own gym profile. |
| BR-GEN-5 | Every record carries its tenant. Names that must be unique (exercises, roles, tiers…) are unique within a tenant, not across the platform. |
| BR-GEN-4 | Every entity records createdBy, createdAt, updatedBy and updatedAt. |
| BR-EX-1 | An exercise name is required, and must be unique per owner (case-insensitive). |
| BR-EX-2 | Archived exercises and routines stay visible in existing plans, assignments and logs, but cannot be added to new ones. |
| BR-RT-1 | A routine contains at least one exercise, and all numeric parameters are positive. |
| BR-CL-1 | A session cannot be scheduled in the past. |
| BR-CL-2 | A professor cannot run overlapping sessions, and a room cannot host overlapping sessions. |
| BR-CL-3 | Capacity is ≥ 1 and ≤ the room's capacity. |
| BR-BK-1 | A client cannot book the same session twice, or two sessions that overlap. |
| BR-BK-2 | Capacity is enforced atomically, so the last spot can never be booked twice. |
| BR-BK-3 | A session cannot be booked after it has started. |
| BR-BK-4 | Cancellations made by the gym do not count towards a client's monthly cancellation limit. |
| BR-DOC-1 | A new client can book during their first **30 days** without a medical certificate and a signed waiver. |
| BR-DOC-2 | After 30 days, or when the medical certificate expires, the client is **blocked** from booking and check-in, and notified, until the documents are valid. |
| BR-DOC-3 | Only the Admin, the Receptionist and the client's assigned professors can see the medical certificate. |
| BR-DOC-4 | A client cannot create plans, routines or exercises until they have signed the liability contract. |
| BR-MEM-1 | A client is blocked from booking and check-in when their membership is expired, or unpaid beyond the grace period. |
| BR-MEM-2 | A booking must respect the client's tier limits and, for credit-based tiers, a credit balance > 0. |
| BR-FIN-1 | Payments are never deleted. Corrections are made by voiding the payment, with a reason. |

---

## 6. Configurable Settings

Scopes: **Platform** = one value for all tenants, set by the Platform admin. **Tenant** = set by the gym's Admin for the whole gym. **Branch** = the tenant's value by default, optionally overridden per branch.

| Setting | Default | Scope |
|---|---|---|
| Gym name, logo, primary colour | Set at onboarding | Tenant |
| WhatsApp sender number, email sender address | Platform defaults | Tenant |
| Waiver and liability contract texts | Platform template | Tenant |
| Gym invitation validity | 7 days | Tenant |
| Booking opens before session | 14 days | Branch |
| Booking and waitlist close before session | 1 hour | Branch |
| Waitlist offer acceptance window | 30 minutes | Branch |
| Cancellation deadline before session | *To be set at launch* | Branch |
| Client cancellations per calendar month | 3 | Branch |
| Membership grace period | 5 days | Branch |
| Document grace period for new clients | 30 days | Branch |
| Medical certificate validity | 1 year | Branch |
| Booking limits | Per tier | Membership tier |
| Audit log retention | 4 months | Platform |
| Time zone / currency | America/Argentina/Buenos_Aires / ARS | Tenant, overridable per branch |
| Default language for new users | Spanish | Tenant |
| Supported languages | Spanish, English | Platform |

---

## 7. Integration Requirements

| ID | Integration | Decision |
|---|---|---|
| INT-01 | Email | Required (provider to be chosen). Per-tenant sender address and domain (FR-TEN-05). |
| INT-02 | WhatsApp | **Meta WhatsApp Cloud API**. Requires a WhatsApp Business account and pre-approved message templates. One platform account can hold one phone number per tenant (FR-TEN-05). |
| INT-03 | Push notifications | Required for the mobile app (e.g. Firebase Cloud Messaging / APNs). |
| INT-04 | File storage | Azure Blob Storage or AWS S3, hidden behind a storage abstraction. Holds exercise media, profile photos and signed documents, separated by tenant. |
| INT-05 | Social login | Google and Apple. |
| INT-06 | Calendar sync | iCal feed or export, usable from Google Calendar. |
| INT-07 | Financial export | Excel / CSV download. |
| INT-08 | Payment gateway | **Deferred.** |
| INT-09 | Check-in hardware | **Deferred.** Expose a vendor-neutral check-in API. |

---

## 8. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | **Security:** every endpoint requires authentication and role-based authorization. Data is encrypted in transit and at rest. |
| NFR-02 | **Privacy:** personal data and medical certificates are handled according to Argentina's personal data protection law (Ley 25.326). Access to medical certificates is restricted (BR-DOC-3). |
| NFR-03 | **Localization:** Spanish and English, for the API's messages and for notifications. |
| NFR-04 | **Multi-tenant and multi-branch:** one backend and one shared database serve every tenant; each tenant has one or more branches. The launch has one tenant with one branch. |
| NFR-08 | **Tenant isolation:** isolation is enforced in the data layer for every request and background job, not left to each endpoint, and is covered by automated tests (FR-TEN-02). |
| NFR-09 | **Horizontal scaling:** the backend is stateless, so capacity grows by adding identical instances. |
| NFR-05 | **Portability:** the backend runs in containers and stays cloud-neutral until the provider is chosen. |
| NFR-06 | **Concurrency:** booking and waitlist operations are safe when many users act at the same time (BR-BK-2). |
| NFR-07 | **Scale, availability and backups:** proposed in [`NonFunctionalRequirements.md`](NonFunctionalRequirements.md) (draft, pending sign-off; see §10). |

Detailed, measurable targets for availability, performance, scalability, security and cost are in [`NonFunctionalRequirements.md`](NonFunctionalRequirements.md).

---

## 9. Phasing

| Phase | Content |
|---|---|
| **Phase 1 (MVP): staff-operated** | Only **staff** sign in, through the **admin/staff web panel**. Clients exist as gym profiles **without an account**; staff act for them, and clients are reached by **WhatsApp and email**. Includes every **M** requirement except the client-facing ones listed for Phase 2: tenancy core (tenants, isolation, suspension, support access, offboarding export), staff accounts and invitations, roles, catalog, routines, classes, booking by staff, waitlist, reception check-in, assignments (recorded by professors), documents, memberships, manual payments, export, email and WhatsApp notifications, audit. Launches with **one tenant and one branch**. |
| **Phase 2: client accounts** | Clients get accounts (invitation link or gym QR code, FR-TEN-10) and the **shared mobile app and client web app** (FR-TEN-11). Client-facing requirements: self-service booking, waitlist and cancellation in the app (FR-BK-01/04/07 by the client), client exercises, routines and plans (FR-EX-03, FR-RT-03, FR-PL-*), progress logs (FR-LOG-*), the liability contract (FR-DOC-05), accepting routine versions (FR-RT-04), viewing assignments, memberships and payments (FR-FIN-03), push notifications (FR-NOT-01) and calendar sync (FR-BK-12). Plus the **S** and **C** requirements: tenant branding, per-tenant WhatsApp and email senders, custom roles, social login, self check-in on hardware. Onboarding of additional gyms. |
| **Later** | Billing the gyms, online payment gateway, personal training, membership freeze. |

### 9.1 Phase 1 rules for clients without an account

| Topic | How it works in Phase 1 |
|---|---|
| Client creation | The Admin or Receptionist creates the client's gym profile (FR-DOC-01). No invitation is sent; the profile is invited when Phase 2 starts. |
| Consent to data processing (Ley 25.326) | Collected at reception: signed on a device or on paper and uploaded, with the date and the text version. |
| Booking and cancelling | Done by the Receptionist or Admin on the client's behalf (FR-BK-01). Cancellation deadlines and the monthly limit (FR-BK-07/08) still apply, and cancellations by the gym still don't count (BR-BK-4). |
| Waitlist offer | Sent by WhatsApp and accepted with a reply button (FR-BK-05). |
| Waiver and guardian consent | Signed through a single-use link, at reception, or on paper and uploaded (FR-DOC-03/04). |
| Liability contract | Not needed: clients can't create their own content until Phase 2. |
| Professor assignments | Professors record them in the panel. The client receives a summary by WhatsApp or email. |
| Routine new versions (FR-RT-04) | The owner decides, per assigned client, whether to move the assignment to the new version. |
| Notifications | Email and WhatsApp only, in the language stored in the client's gym profile. Push starts in Phase 2. |
| Payments and memberships | Clients ask at reception; the receipt can be sent by email. |

---

## 10. Deferred & Open Items

| Item | Status |
|---|---|
| Online payment gateway and recurring billing | Deferred by decision |
| Check-in hardware device and vendor | Deferred by decision |
| Billing the gyms (price per gym, per branch or per active client; invoicing) | Deferred |
| Cloud provider | Azure preferred, to be confirmed |
| How the apps identify the tenant at sign-in | **Decided:** one account sign-in, then gym picker; gyms are joined by invitation link or QR code (FR-TEN-09/10) |
| One person in several gyms | **Decided:** one account, a separate gym profile per gym (BR-GEN-3) |
| Mobile app model | **Decided:** one shared app, branded per gym by its settings (FR-TEN-11) |
| Do clients get a usable account in Phase 1? | **Decided:** no. Phase 1 is staff-operated; client accounts and apps arrive in Phase 2 (§9, §9.1). |
| Data processing agreement template between the platform owner and each gym (Ley 25.326) | Open, legal. Needed before the first gym not owned by the platform owner goes live. |
| Expected scale (clients, staff, concurrent users), availability and backup targets | Proposed in [`NonFunctionalRequirements.md`](NonFunctionalRequirements.md); pending sign-off (its §6) |
| Default cancellation deadline | To be set at launch (configurable) |
| Email and push notification providers | To be chosen during architecture |

---

## 11. Change History

| Version | Date | Change |
|---|---|---|
| 1.0 | 11-19-2026 | Initial draft: 4 actors, 7 requirements. |
| 2.0 | 11-19-2026 | Full rewrite after the BA review (`Documentation/BRD-Analysis.md`). Added the Receptionist role, permission matrix, numbered requirements with priorities, business rules, settings, integrations and NFRs. |
| 2.1 | 11-20-2026 | Linked the proposed non-functional requirements (`Documentation/NonFunctionalRequirements.md`) from §8 and §10. |
| 3.0 | 11-20-2026 | The product becomes a **multi-tenant platform** (one backend, one database, many gyms with many branches each). Added the Tenant level, the Platform admin role and §3.3, the Tenancy requirements (§4.0), tenant-scoped settings, NFR-08/09, and the tenancy open items. |
| 3.1 | 11-20-2026 | Decided: one platform-wide account per person, with a gym profile per gym; joining a gym by invitation link or QR code; one shared app branded per gym. Added the Account, Gym profile and Gym invitation terms and FR-TEN-10/11. Client accounts in Phase 1 left open. |
| 3.2 | 11-20-2026 | Decided: **Phase 1 is staff-operated**. Clients have gym profiles without accounts and are reached by WhatsApp and email; client accounts and apps move to Phase 2. Reworked §9, added §9.1, and updated FR-BK-05 (WhatsApp reply button) and FR-DOC-03 (signing link). |
