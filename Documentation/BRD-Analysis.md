# BRD Analysis — Gym Backend

| | |
|---|---|
| **Source document** | `Documentation/BusinessRequirements.md` (Rodrigo Tristany, 11-19-2026) |
| **Reviewer role** | Senior Business Analyst |
| **Review date** | 2026-11-19 |
| **Status** | Closed. All decisions are in the Decisions Log (§10) and in BRD v2.0 (`BusinessRequirements.md`). Note: §§0–9 are the original review and still show the open questions. |

---

## 0. Executive Summary

The BRD has **4 actors and 7 one-line requirements**. That is enough to show what the product is meant to do. It is not enough to design a backend from. The main gaps are:

1. **No data model.** "Class", "routine", "exercise" and "exercise plan" are never defined, and neither are the relationships between them.
2. **The "financial section" is undefined.** One actor (Accountant) exists only to use it, but nothing says what it contains: memberships, payments, invoices, payroll?
3. **No membership or subscription concept.** A gym backend almost always needs one, and access to classes usually depends on it.
4. **The permission model is coarse.** Phrases like "access all the system" and "access the financial section" do not say who can read, create, update or delete what.
5. **No non-functional requirements.** Authentication, audit, multi-branch support, time zones, notifications, integrations and data privacy are all missing.

The rest of this document breaks down each requirement as written, states the assumptions I had to make, and tags every open question with **[CLARIFICATION NEEDED]**. Each one has an ID (e.g. `[CN-R1]`) so we can track it to resolution.

---

## 1. Glossary (as inferred, to be confirmed)

| Term | Inferred meaning | Status |
|---|---|---|
| **Admin** | Gym owner or manager with unrestricted access | [CLARIFICATION NEEDED] `CN-G1`: Is there one admin or several? Is there a "super admin" over multiple gyms or branches? |
| **Professor** | Trainer or instructor who runs classes and designs workouts | [CLARIFICATION NEEDED] `CN-G2`: Is "Professor" the final name (vs. Trainer/Coach)? Are group-class instructors and personal trainers the same role? |
| **Accountant** | Back-office finance user | [CLARIFICATION NEEDED] `CN-G3`: Internal employee or external accountant? |
| **Client** | Gym member | [CLARIFICATION NEEDED] `CN-G4`: Must a client hold an active membership to use the system, or can prospects or visitors register? |
| **Class** | A group session (e.g. Spinning, Yoga) held at a time and place with limited capacity | [CLARIFICATION NEEDED] `CN-G5`: Definition not given |
| **Routine** | An ordered set of exercises (a workout template) | [CLARIFICATION NEEDED] `CN-G6`: Definition not given |
| **Exercise** | A single movement with parameters (sets, reps, weight, duration) | [CLARIFICATION NEEDED] `CN-G7`: Definition not given. Are the parameters part of the exercise or of its use inside a routine? |
| **Exercise plan** | A client's personal plan combining classes, routines and exercises over a period | [CLARIFICATION NEEDED] `CN-G8`: Definition not given. This is the most ambiguous entity in the BRD. |
| **Financial section** | Unknown | [CLARIFICATION NEEDED] `CN-G9`: See §5 |

---

## 2. User Roles & Permissions

### 2.1 Roles as stated

| Role | Stated permissions (verbatim intent) |
|---|---|
| Admin | "Access all the system" |
| Accountant | "Access the financial section" |
| Professor | Access/edit classes, routines, exercises; schedule classes; add exercises to a client |
| Client | Select classes/routines/exercises to create an exercise plan; schedule the classes they will attend |

### 2.2 Proposed permission matrix (draft, to be validated)

Legend: **C**reate · **R**ead · **U**pdate · **D**elete · **—** none · **own** = only records they own · **?** = unknown

| Resource | Admin | Professor | Accountant | Client |
|---|---|---|---|---|
| Users / staff accounts | CRUD | — | — | R/U own profile |
| Client profiles | CRUD | R (assigned? all?) ? | R (billing data) ? | R/U own |
| Exercise catalog | CRUD | CRUD ? | — | R |
| Routines | CRUD | CRUD ? | — | R (+ C own?) ? |
| Class types (definitions) | CRUD | CRU ? | — | R |
| Class sessions (schedule) | CRUD | CRUD ? | — | R |
| Class bookings | CRUD | R (own classes) / U attendance ? | — | C/R/D own |
| Exercise plans | CRUD | C/R/U for clients ? | — | CRUD own ? |
| Client-assigned exercises | CRUD | CRUD | — | R own |
| Financial data | CRUD ? | — | CRUD ? | R own payments ? |
| Reports | All | Own classes ? | Financial | — |

### 2.3 Ambiguities

- **[CLARIFICATION NEEDED] `CN-R1`**: "Admin can access all the system". Does that include acting *on behalf of* other roles, e.g. booking a class for a client or editing a professor's routine? Does it include deleting financial records?
- **[CLARIFICATION NEEDED] `CN-R2`**: Can one user hold **several roles**? For example, an admin who also teaches classes, or a professor who also trains at the gym as a client.
- **[CLARIFICATION NEEDED] `CN-R3`**: Can a professor edit **any** class, routine or exercise, or only those they created? If two professors share a catalog, who owns what?
- **[CLARIFICATION NEEDED] `CN-R4`**: Can a professor see **all clients** or only clients assigned to them? Is there a client-to-professor assignment at all?
- **[CLARIFICATION NEEDED] `CN-R5`**: Does the accountant need **read access to non-financial data**, such as client names and contact info for invoices, or class attendance for instructor payroll?
- **[CLARIFICATION NEEDED] `CN-R6`**: Can the accountant **modify** financial records (refunds, adjustments), or only view and report on them?
- **[CLARIFICATION NEEDED] `CN-R7`**: Can clients see **their own** financial data (payment history, invoices, membership status)?
- **[CLARIFICATION NEEDED] `CN-R8`**: Who **creates accounts**? Do clients self-register, or does admin or reception create them? Who creates staff accounts?
- **[CLARIFICATION NEEDED] `CN-R9`**: Is a **Receptionist / Front-desk** role needed (check-in, selling memberships, registering clients)? Gyms normally have one, and it is missing from the BRD.
- **[CLARIFICATION NEEDED] `CN-R10`**: Should roles be **fixed** (hard-coded) or **configurable** (admin defines roles and permission sets)?

---

## 3. Core Entities & Relationships

### 3.1 Inferred entities

| Entity | Key attributes (proposed) | Source |
|---|---|---|
| **User** | id, name, email, phone, password/credentials, status, role(s) | Implied by actors |
| **ClientProfile** | userId, birth date, health notes?, goals?, assigned professor? | Implied |
| **StaffProfile** | userId, specialties?, hire date? | Implied |
| **Exercise** | id, name, description, muscle group, equipment, media (video/image)?, createdBy | Stated |
| **Routine** | id, name, description, level?, createdBy, ordered list of RoutineExercise | Stated |
| **RoutineExercise** | routineId, exerciseId, order, sets, reps, weight, rest, duration | Inferred |
| **ClassType** | id, name, description, default duration, default capacity | Inferred |
| **ClassSession** | id, classTypeId, professorId, start, end, room/location, capacity, status | Stated ("schedule classes") |
| **Booking** | id, clientId, classSessionId, status (booked/cancelled/attended/no-show), timestamps | Stated ("schedule the class is going to attend") |
| **ClientExerciseAssignment** | clientId, exerciseId (or routineId?), professorId, parameters, notes | Stated ("add exercises to client") |
| **ExercisePlan** | id, clientId, name, start/end date, items (classes/routines/exercises) | Stated |
| **Financial entities** | Membership, MembershipPlan, Payment, Invoice, Expense? | **Not stated.** Inferred from "financial section" |

### 3.2 Relationship diagram (proposed)

```
User 1─1 ClientProfile
User 1─1 StaffProfile (Professor / Accountant / Admin)

Professor 1─* ClassSession *─1 ClassType
ClassSession 1─* Booking *─1 Client

Exercise *─* Routine        (via RoutineExercise: order, sets, reps…)
Professor 1─* Exercise / Routine  (createdBy)

Client 1─* ClientExerciseAssignment *─1 Exercise   (assigned by Professor)

Client 1─* ExercisePlan
ExercisePlan *─* ClassSession | ClassType ?   [CN-E3]
ExercisePlan *─* Routine
ExercisePlan *─* Exercise

Client 1─* Membership *─1 MembershipPlan          [CN-F1]
Membership 1─* Payment                            [CN-F2]
```

### 3.3 Ambiguities

- **[CLARIFICATION NEEDED] `CN-E1`**: Is a **Class** a *type* (e.g. "Yoga") or a *dated occurrence* (e.g. "Yoga, Mon 18:00")? The BRD uses "class" for both: "edit classes" vs. "schedule classes". I propose splitting it into `ClassType` and `ClassSession`.
- **[CLARIFICATION NEEDED] `CN-E2`**: Are classes **recurring**, e.g. "every Monday at 18:00 for 3 months"? If so, how are exceptions handled: a holiday, a substitute professor, one cancelled occurrence?
- **[CLARIFICATION NEEDED] `CN-E3`**: When a client puts a **class in an exercise plan**, is that a specific session, a class type ("I'll do Yoga twice a week"), or does it create a booking?
- **[CLARIFICATION NEEDED] `CN-E4`**: How do an **exercise plan** and "**professor adds exercises to client**" relate? Are they the same thing (a professor editing the client's plan) or two separate concepts (a professor prescription vs. a client self-made plan)?
- **[CLARIFICATION NEEDED] `CN-E5`**: Can a client have **more than one active exercise plan** at a time? Do plans have a start and end date, or are they open-ended?
- **[CLARIFICATION NEEDED] `CN-E6`**: Can **clients create their own routines or exercises**, or only choose from the professors' catalog?
- **[CLARIFICATION NEEDED] `CN-E7`**: If a professor edits a routine that is already in clients' plans, do those plans **see the change** (live reference) or keep the **old version** (snapshot)?
- **[CLARIFICATION NEEDED] `CN-E8`**: Do we need to track **workout progress or logs**, i.e. a client recording that they did 3×10 at 50 kg today? The BRD does not mention it, but it is usually the main reason for having exercise plans.
- **[CLARIFICATION NEEDED] `CN-E9`**: Are there **rooms, locations or equipment** that limit scheduling, so that two classes cannot use the same room at once?
- **[CLARIFICATION NEEDED] `CN-E10`**: Is this a **single gym** or **multiple branches** (multi-tenant)?
- **[CLARIFICATION NEEDED] `CN-E11`**: Delete behaviour. Should records be **soft-deleted** (kept for history) or hard-deleted? This matters for exercises in use, classes with bookings, and clients with payment history.

---

## 4. Workflows by Feature

### 4.1 Feature: Authentication & Account Management *(implied, not in BRD)*

**Proposed workflow: Client onboarding**
1. A client account is created, by self-registration or by staff ([CN-R8]).
2. The client verifies their email or phone? [CLARIFICATION NEEDED] `CN-A1`
3. The client completes a profile, possibly including a health questionnaire or waiver. [CLARIFICATION NEEDED] `CN-A2`
4. The client buys or is assigned a membership ([CN-F1]).
5. The client gets access to booking and planning features.

**Edge cases:** duplicate email; a client who returns after leaving (reactivation); a minor client (guardian consent?); a forgotten password; a staff member who leaves (deactivate without losing history).

- **[CLARIFICATION NEEDED] `CN-A3`**: Authentication method. Email + password? Social login? SSO for staff? Two-factor authentication for admin and accountant?
- **[CLARIFICATION NEEDED] `CN-A4`**: Which clients will use this backend: mobile app, web app, or both? This changes the token and session strategy.

---

### 4.2 Feature: Exercise Catalog Management (Professor)

**BRD:** *"The professor can access and edit … exercises."*

**Workflow: Create exercise**
1. The professor signs in.
2. They open the exercise catalog.
3. They choose "New exercise" and enter name, description, muscle group(s), equipment and media.
4. The system validates the input (unique name? required fields?).
5. The exercise is saved and becomes available to routines, plans and assignments.

**Workflow: Edit or delete exercise**
1. The professor selects an exercise.
2. They edit fields, or request deletion.
3. If the exercise is used in routines, plans or assignments, the system blocks the change, warns, or archives it instead ([CN-E7], [CN-E11]).

**Business rules (proposed):**
- BR-EX-1: The exercise name is required and must be unique (case-insensitive) within the gym.
- BR-EX-2: An exercise that is referenced elsewhere cannot be hard-deleted; it can only be archived.
- BR-EX-3: Archived exercises do not appear in selection lists, but stay visible in historical plans.

**Edge cases:** two professors edit the same exercise at the same time (optimistic concurrency); media upload fails or is too large; a duplicate exercise has a slightly different name.

- **[CLARIFICATION NEEDED] `CN-EX1`**: Does the system start with a **predefined exercise library**, or is it empty and filled by professors?
- **[CLARIFICATION NEEDED] `CN-EX2`**: Are images or videos required? If so, where are they stored (see Integrations §6)?

---

### 4.3 Feature: Routine Management (Professor)

**BRD:** *"The professor can access and edit … routines."*

**Workflow: Create routine**
1. The professor creates a routine with a name, description, difficulty level and goal.
2. They add exercises from the catalog, in order.
3. For each exercise they set sets, reps, weight or intensity, rest and duration.
4. They save. The routine becomes available to clients for selection ([CN-E6]).

**Business rules (proposed):**
- BR-RT-1: A routine must contain at least one exercise.
- BR-RT-2: Exercise order within a routine is explicit and unique.
- BR-RT-3: Numeric parameters must be positive. Reps and duration may be mutually exclusive (rep-based vs. time-based exercise).

**Edge cases:** the same exercise appears twice in a routine (e.g. warm-up and finisher), so this must be allowed; an exercise is archived while it is in a routine; a routine is edited while clients are following it ([CN-E7]).

- **[CLARIFICATION NEEDED] `CN-RT1`**: Are routines **public** (all clients can see them) or **private**, only for assigned clients?
- **[CLARIFICATION NEEDED] `CN-RT2`**: Do routines need structure beyond a flat list, such as days ("Day A / Day B"), supersets, circuits or progression rules?

---

### 4.4 Feature: Class Management & Scheduling (Professor)

**BRD:** *"The professor can access and edit the classes"* and *"The professor can schedule classes."*

**Workflow: Define class type**
1. The professor (or admin?) creates a class type with name, description, default duration and default capacity.

**Workflow: Schedule class session**
1. The professor picks a class type.
2. They set date, start time, duration, room and capacity.
3. They optionally set recurrence ([CN-E2]).
4. The system checks for conflicts: the professor double-booked, the room double-booked ([CN-E9]), a date in the past.
5. The session is published and becomes bookable by clients.

**Workflow: Cancel or reschedule a session**
1. The professor (or admin) cancels or moves a session.
2. The system handles existing bookings: it notifies clients ([CN-I1]) and either cancels or moves their bookings.

**Business rules (proposed):**
- BR-CL-1: A session cannot be scheduled in the past.
- BR-CL-2: A professor cannot have overlapping sessions.
- BR-CL-3: A room cannot host overlapping sessions (if rooms exist).
- BR-CL-4: Capacity must be ≥ 1, and cannot be lowered below the current number of bookings without handling the overflow.
- BR-CL-5: A cancelled session cannot be booked, and its existing bookings move to a "cancelled by gym" status.

**Edge cases:** the professor is sick and needs a substitute; a session falls outside gym opening hours; a time-zone or daylight-saving shift on recurring sessions; a session is edited after clients have checked in.

- **[CLARIFICATION NEEDED] `CN-CL1`**: Can a professor schedule sessions for **other professors**, or only for themselves?
- **[CLARIFICATION NEEDED] `CN-CL2`**: Do we need to define **gym opening hours and holidays** as constraints?
- **[CLARIFICATION NEEDED] `CN-CL3`**: Are there **personal training (1:1) sessions** as well as group classes?

---

### 4.5 Feature: Assign Exercises to Client (Professor)

**BRD:** *"The professor can add exercises to client."*

**Workflow (proposed):**
1. The professor searches for or selects a client ([CN-R4]).
2. They open the client's current plan or assignments.
3. They add exercises (or whole routines?) with personalised parameters and notes.
4. They save. The client can see the assigned exercises.

**Business rules (proposed):**
- BR-AS-1: Only active clients can receive assignments.
- BR-AS-2: Every assignment records which professor made it, and when.

**Edge cases:** the client already has the same exercise assigned; the professor's access to the client ends (the client is reassigned); the client has a health restriction that conflicts with the exercise.

- **[CLARIFICATION NEEDED] `CN-AS1`**: Can the professor assign **whole routines** or only individual exercises? The BRD says "exercises" only.
- **[CLARIFICATION NEEDED] `CN-AS2`**: Can the client **edit or remove** exercises a professor assigned?
- **[CLARIFICATION NEEDED] `CN-AS3`**: Should the system store client **health conditions or injuries** and warn about contraindicated exercises? (If so, this is sensitive data; see §7.)

---

### 4.6 Feature: Client Exercise Plan

**BRD:** *"The client can select classes, routines and exercises and create a exercise plan."*

**Workflow (proposed):**
1. The client signs in.
2. They create a new plan with a name, goal and start/end dates.
3. They browse and add class types or sessions ([CN-E3]), routines and individual exercises.
4. They optionally place items on days of the week (a weekly template).
5. They save. The plan becomes their active plan ([CN-E5]).

**Business rules (proposed):**
- BR-PL-1: A plan belongs to exactly one client.
- BR-PL-2: A plan must contain at least one item.
- BR-PL-3: The end date, if present, must be ≥ the start date.

**Edge cases:** a class in the plan is discontinued; the client's membership expires while the plan is active; the professor and the client edit the same plan at once.

- **[CLARIFICATION NEEDED] `CN-PL1`**: Does adding a class to a plan **automatically book** it, or is booking always a separate step?
- **[CLARIFICATION NEEDED] `CN-PL2`**: Does a professor need to **approve or review** a client-created plan?
- **[CLARIFICATION NEEDED] `CN-PL3`**: Is the plan a **weekly template** (repeats) or a **calendar** (specific dates)?

---

### 4.7 Feature: Class Booking (Client)

**BRD:** *"The client can schedule the class is going to attend."*

**Workflow: Book**
1. The client browses upcoming sessions (filtered by date, class type or professor).
2. They select a session and confirm the booking.
3. The system checks that the membership is active and allows this class ([CN-F3]), that the session has free capacity, that the client has no overlapping booking, and that the booking window is open.
4. The booking is created and a confirmation is sent ([CN-I1]).

**Workflow: Cancel booking**
1. The client cancels a booking.
2. The system checks the cancellation deadline. A late cancellation may cause a penalty ([CN-BK3]).
3. The spot is released, and a waitlisted client is promoted if a waitlist exists ([CN-BK2]).

**Workflow: Attendance**
1. At class time, the professor or reception marks attendance, or the client checks in ([CN-BK4]).
2. Clients who were not marked become no-shows.

**Business rules (proposed):**
- BR-BK-1: A client cannot book the same session twice.
- BR-BK-2: Bookings cannot exceed capacity. This must be checked atomically, because two clients can race for the last spot.
- BR-BK-3: A client cannot book overlapping sessions.
- BR-BK-4: A session cannot be booked after it has started.

**Edge cases:** the last spot is taken at the same time by two clients (concurrency); a session is cancelled after a booking; the membership expires between booking and class day; a client books and then their account is suspended.

- **[CLARIFICATION NEEDED] `CN-BK1`**: What is the **booking window**? For example, it opens 7 days before and closes 1 hour before.
- **[CLARIFICATION NEEDED] `CN-BK2`**: Is a **waitlist** needed?
- **[CLARIFICATION NEEDED] `CN-BK3`**: Is there a **cancellation deadline or penalty**, such as a no-show policy or blocking after N no-shows?
- **[CLARIFICATION NEEDED] `CN-BK4`**: Do we track **attendance or check-in**? Who records it?
- **[CLARIFICATION NEEDED] `CN-BK5`**: Is there a **limit on bookings** per client per day or week (e.g. a membership allows 8 classes a month)?

---

### 4.8 Feature: Financial Section (Accountant)

**BRD:** *"The accountant can access the financial section."* Nothing else is specified.

This is the **largest gap** in the BRD. Typical scope for a gym:

| Sub-feature | Description | In scope? |
|---|---|---|
| Membership plans | Monthly, quarterly, annual, class packs, drop-in | [CLARIFICATION NEEDED] `CN-F1` |
| Client memberships | Who has which plan, start/end, status (active, frozen, expired) | [CLARIFICATION NEEDED] `CN-F1` |
| Payments | Recording payments, methods (cash, card, transfer), partial payments | [CLARIFICATION NEEDED] `CN-F2` |
| Online payments | Payment gateway integration, recurring billing | [CLARIFICATION NEEDED] `CN-F4` |
| Invoicing / receipts | Generating fiscal invoices, local tax compliance | [CLARIFICATION NEEDED] `CN-F5` |
| Debt / overdue | Tracking overdue clients, blocking access | [CLARIFICATION NEEDED] `CN-F6` |
| Expenses | Rent, equipment, utilities | [CLARIFICATION NEEDED] `CN-F7` |
| Staff payroll | Professor pay (per class? salary?) | [CLARIFICATION NEEDED] `CN-F8` |
| Reports | Revenue per period, per plan, active members, churn | [CLARIFICATION NEEDED] `CN-F9` |
| Refunds / discounts | Promotions, family discounts, refunds | [CLARIFICATION NEEDED] `CN-F10` |

- **[CLARIFICATION NEEDED] `CN-F3`**: Does membership status **control access** to booking and plans? For example, an expired membership means no booking.
- **[CLARIFICATION NEEDED] `CN-F11`**: Currency or currencies? Tax rules and country?
- **[CLARIFICATION NEEDED] `CN-F12`**: Can the accountant **edit or void** payments? Do changes require an audit trail?

**Edge cases (generic):** a duplicate payment is recorded; a payment arrives after the membership expired; a refund on a partially used membership; a membership is frozen during injury or travel.

---

### 4.9 Feature: Administration (Admin)

**BRD:** *"The admin can access all the system."*

**Implied workflows:** manage staff accounts (create, deactivate, assign roles); manage clients; configure gym settings (hours, rooms, policies); view all reports; override any record.

- **[CLARIFICATION NEEDED] `CN-AD1`**: Should admin actions be **audit-logged** (who changed what, and when)?
- **[CLARIFICATION NEEDED] `CN-AD2`**: Should there be a **dashboard or KPIs** for the admin (active members, occupancy rate, revenue)?

---

## 5. Cross-cutting Business Rules (proposed defaults)

| ID | Rule | Status |
|---|---|---|
| BR-X-1 | All timestamps are stored in UTC and displayed in the gym's time zone | Proposed |
| BR-X-2 | Every entity records createdBy, createdAt, updatedBy, updatedAt | Proposed |
| BR-X-3 | Users are deactivated, never hard-deleted, if they have history | Proposed |
| BR-X-4 | Email is unique per user | Proposed |
| BR-X-5 | All API access requires authentication; authorization is role-based | Proposed |
| BR-X-6 | Validation errors return field-level messages | Proposed |

---

## 6. Integration Requirements

The BRD lists **no integrations**. Likely candidates:

- **[CLARIFICATION NEEDED] `CN-I1`**: **Notifications.** Email, SMS, push or WhatsApp? Triggers: booking confirmation, class cancellation, membership expiry, payment due.
- **[CLARIFICATION NEEDED] `CN-I2`**: **Payment gateway.** Stripe, Mercado Pago, PayPal, or none (manual payments only)?
- **[CLARIFICATION NEEDED] `CN-I3`**: **File storage** for exercise media and profile photos (S3, Azure Blob, local).
- **[CLARIFICATION NEEDED] `CN-I4`**: **Access control hardware**, such as turnstiles or QR or RFID check-in at the gym entrance.
- **[CLARIFICATION NEEDED] `CN-I5`**: **Accounting or invoicing system**, e.g. export to accounting software or an electronic fiscal invoicing authority.
- **[CLARIFICATION NEEDED] `CN-I6`**: **Calendar sync**, e.g. export bookings to Google Calendar or iCal.
- **[CLARIFICATION NEEDED] `CN-I7`**: **Frontend consumers.** Which apps call this API (admin web panel, client mobile app)?

---

## 7. Non-Functional Requirements (all missing)

- **[CLARIFICATION NEEDED] `CN-N1`**: Expected scale: number of clients, staff, concurrent users, branches.
- **[CLARIFICATION NEEDED] `CN-N2`**: Data privacy and regulation. Health data and payment data have legal implications (GDPR or a local data-protection law). Which country or countries?
- **[CLARIFICATION NEEDED] `CN-N3`**: Languages and localization of content, such as exercise names and notifications.
- **[CLARIFICATION NEEDED] `CN-N4`**: Availability, backup and data-retention expectations.
- **[CLARIFICATION NEEDED] `CN-N5`**: Audit logging requirements, especially for financial changes.

---

## 8. Issues in the BRD Text Itself

| # | Issue | Suggested fix |
|---|---|---|
| 1 | Typos: "finantial" → "financial"; "a exercise plan" → "an exercise plan"; "the class is going to attend" → "the classes they are going to attend" | Edit text |
| 2 | Requirements are not numbered, so they cannot be traced | Use IDs (e.g. `FR-01`) |
| 3 | No acceptance criteria | Add Given/When/Then per requirement |
| 4 | No scope statement (in/out of scope, MVP vs. later) | Add a Scope section |
| 5 | No glossary | Add the one from §1 once confirmed |
| 6 | Requirements mix "access" (read) and "edit" (write) inconsistently | Use explicit CRUD verbs |
| 7 | No priorities | Use MoSCoW (Must/Should/Could/Won't) |

---

## 9. Clarification Tracker

| Section | IDs | Count |
|---|---|---|
| Glossary | CN-G1 … CN-G9 | 9 |
| Roles & permissions | CN-R1 … CN-R10 | 10 |
| Entities | CN-E1 … CN-E11 | 11 |
| Auth / accounts | CN-A1 … CN-A4 | 4 |
| Exercises / routines | CN-EX1, CN-EX2, CN-RT1, CN-RT2 | 4 |
| Classes / booking | CN-CL1 … CN-CL3, CN-BK1 … CN-BK5 | 8 |
| Assignments / plans | CN-AS1 … CN-AS3, CN-PL1 … CN-PL3 | 6 |
| Financial | CN-F1 … CN-F12 | 12 |
| Admin | CN-AD1, CN-AD2 | 2 |
| Integrations | CN-I1 … CN-I7 | 7 |
| Non-functional | CN-N1 … CN-N5 | 5 |
| **Total** | | **78** |

---

## 10. Decisions Log

### Section 1: User Roles & Permissions (answered 2026-11-19)

| ID | Decision |
|---|---|
| CN-R9 | **Receptionist** role added. Its permissions are not yet defined (see follow-up R-F1). |
| CN-R2 | A user **can hold several roles** (e.g. Admin + Professor, Professor + Client). |
| CN-R1 | Admin can do **everything**, including acting on behalf of other users and deleting financial records. **Every admin action must be audit-logged.** |
| CN-R3 | Professors edit **only the classes, routines and exercises they own**. **Class ownership can be transferred** to another professor. |
| CN-R4 | Professors see and assign exercises **only to clients assigned to them**. This needs a Client↔Professor assignment entity. |
| CN-R5/R6 | Answered "Yes and no". Interpreted as: Accountant **can edit** financial records and has **no access** to non-financial data. Pending confirmation (R-F2). |
| CN-R7 | Clients **can see** their own payment history and membership status. |
| CN-R8 | **Staff creates client accounts** (no self-registration for now). **Admin creates staff accounts.** |
| CN-R10 | Roles are **configurable**: Admin can define custom roles and permission sets. |

**Follow-ups opened**

- **[CLARIFICATION NEEDED] `R-F1`**: What can the Receptionist do?
- **[CLARIFICATION NEEDED] `R-F2`**: Confirm the interpretation of answer 6.
- **[CLARIFICATION NEEDED] `R-F3`**: Who can transfer a class (current owner, admin)? Do the existing bookings move with it?
- **[CLARIFICATION NEEDED] `R-F4`**: Who assigns clients to professors? Can a client have more than one professor?
- **[CLARIFICATION NEEDED] `R-F5`**: Do the four base roles (plus Receptionist) still exist as built-in defaults on top of custom roles?
- **[CLARIFICATION NEEDED] `R-F6`**: Is "staff creates client accounts" limited to Admin and Receptionist, or can Professors create them too?

### Section 2: Core Features & Workflows (answered 2026-11-19)

| ID | Decision |
|---|---|
| CN-E1/E2 | A **ClassType** has dated **ClassSessions**. Sessions **can be recurring**. |
| CN-E10 | **Multi-branch ready** in the data model (a Branch entity), but launched as a **single gym**. |
| CN-E9 | **Rooms exist** and have a capacity. Sessions cannot overlap in the same room. |
| CN-CL3 | **No personal training (1:1)** for now. |
| CN-E4 | **Two separate concepts:** professor assignments (prescription) and client-built plans. |
| CN-E5/PL3 | Plans are **calendars with specific dates**. A client **can have several active plans**. |
| CN-PL1/E3 | Adding a class to a plan **does not book it**. Booking is a separate step. |
| CN-E6/PL2 | Clients **can create their own routines and exercises**. **Professor approval** of them is an **optional setting**. |
| CN-E7 | When a routine in use is edited, the **system asks** whether to update existing plans or keep their current version (see follow-up W-F1). |
| CN-E8 | **Workout progress logging is in scope** (sets, reps, weight per day). |
| CN-BK1 | Booking **opens 14 days before** and **closes 1 hour before**. Both are configurable. |
| CN-BK2 | A **waitlist** is used. |
| CN-BK3 | The cancellation deadline and the no-show penalty are **configurable**. |
| CN-BK5 | A client can **cancel at most 3 times** (configurable). The period this applies to is still open (W-F3). |
| CN-BK4 | Attendance is tracked. **Phase 1:** reception checks clients in. **Phase 2:** clients check in themselves on a **hardware device** on site (integration, see CN-I4). |

**Follow-ups opened**

- **[CLARIFICATION NEEDED] `W-F1`**: Routine edit: who is asked, the editing professor or each affected client? Does the client's own plan count?
- **[CLARIFICATION NEEDED] `W-F2`**: Is the approval setting global, per branch, or per professor? Can clients use unapproved content in their own plans while they wait?
- **[CLARIFICATION NEEDED] `W-F3`**: "Cancel 3 times": per week, per month, or per membership period? What happens on the 4th: blocked from cancelling, or blocked from booking?
- **[CLARIFICATION NEEDED] `W-F4`**: Is there also a booking limit (e.g. N classes per week, set by the membership)?
- **[CLARIFICATION NEEDED] `W-F5`**: Who can log progress: the client only, or the professor too? Can a log be linked to a professor assignment, a plan item, or both?

### Section 3: Business Rules & Constraints (answered 2026-11-19)

| ID | Decision |
|---|---|
| CN-F1 | Membership types: **monthly, annual, class packs and drop-in**. |
| CN-F3 | An expired or unpaid membership **blocks booking and check-in** (assumed, see B-F1). |
| CN-F (freeze) | **No membership freeze.** |
| CN-F6 | Overdue clients get a **5-day grace period** (configurable) before they are blocked. |
| CN-BK2 | Waitlist: when a spot frees up, the next client is **offered** it and has **30 minutes to accept**. The waitlist **closes with booking** (1 hour before the session). |
| CN-BK3 | A no-show triggers a **notification to the client, the professor, reception and the admin** so they can resolve it. There is no automatic sanction. |
| CN-CL (cancel) | When the gym cancels or reschedules a session, it notifies the booked clients. This **does not count** against their cancellation limit. |
| BR-CL-4 | If capacity drops below the number of bookings, the **most recently booked** clients are notified and **moved to the waitlist**. |
| CN-E11 | Records with history are **archived (soft-deleted)**, never hard-deleted. |
| CN-A2 | Extended client data is **required**: date of birth, ID number, emergency contact, health questionnaire, waiver. **Minors are allowed**, with guardian consent. |
| CN-CL2 | **No** opening-hours or holiday restrictions on scheduling. |
| CN-F11 | Default country **Argentina** (configurable): `America/Argentina/Buenos_Aires` time zone and ARS currency. **No local tax / fiscal invoicing** requirements. |
| CN-N5 | **Every change** by any user is audit-logged. Logs are kept for **4 months** (configurable). |

**Follow-ups opened**

- **[CLARIFICATION NEEDED] `B-F1`**: Confirm that an expired or unpaid membership (after the grace period) blocks both booking and check-in.
- **[CLARIFICATION NEEDED] `B-F2`**: Class packs and drop-ins: does each booking or attendance use up one credit? Is a credit returned on a cancellation made in time? Do packs expire?
- **[CLARIFICATION NEEDED] `B-F3`**: Waitlist offers: if the 30 minutes would run past the closing time (1 hour before the session), does the offer still stand? Does a waitlisted client who doesn't respond keep their place in the queue?
- **[CLARIFICATION NEEDED] `B-F4`**: Minors: what does guardian consent require? A guardian user account, or guardian data plus a signed form?
- **[CLARIFICATION NEEDED] `B-F5`**: Health questionnaire: what are its fields, and who can see the answers (professor? reception?). This is sensitive data under Argentina's personal data protection law (Ley 25.326).
- **[CLARIFICATION NEEDED] `B-F6`**: Health questionnaire and waiver: what happens when a client hasn't completed them yet? Should booking be blocked until they do?

### Section 3 follow-ups: resolved

| ID | Decision |
|---|---|
| B-F1 | Confirmed: after the grace period, an expired or unpaid membership blocks **both booking and check-in**. |
| B-F2 | Packs and drop-ins: **each booking uses 1 credit**. A cancellation made in time **refunds the credit**. Packs **do not expire**. |
| B-F3 | A waitlist offer **stays valid even if it runs past booking close**. A client who doesn't answer the offer **keeps their place** in the queue. |
| B-F4 | **No guardian account.** Guardian details are stored on the minor's profile, together with the signed consent (assumed, see O-2). |
| B-F5 | **No health questionnaire.** It is replaced by an uploaded **medical certificate of fitness to exercise** ("apto físico"). It is a document stored for the client, so it is still sensitive data. |
| B-F6 | Clients **can book before** providing the medical certificate and the signed waiver. They have **30 days** to do it. |

### Section 4: Integration Requirements (answered 2026-11-19)

| ID | Decision |
|---|---|
| CN-I1 | Notifications by **email, WhatsApp and push**. **Waitlist offers go by WhatsApp.** |
| CN-I2 | Online payments and payment gateway: **on hold, not decided**. Design the payment model so a gateway can be added later. |
| CN-I4 | Check-in hardware: **not decided**. Design a vendor-neutral check-in API. |
| CN-I3 | File storage: **Azure Blob or AWS S3** (not yet chosen). Hide it behind a storage abstraction. |
| CN-I7 | Apps using the API: **admin/staff web panel, client mobile app and client web app**. |
| CN-A3 | Sign-in: **email/password plus Google/Apple sign-in**, and **two-factor authentication** for privileged roles (assumed, see O-4). |
| CN-I5 | **Accounting export: yes** (format and target not specified, see O-5). |
| CN-I6 | **Calendar sync** (Google Calendar / iCal): yes. |
| CN-N3 | Languages: **Spanish and English**. |
| CN-N1/N4 | Hosting and scale: **not decided**. |

### Still open (needed before or during architecture)

**Roles follow-ups: resolved**

| ID | Decision |
|---|---|
| R-F1 | **Receptionist** can: create and edit client accounts; check clients in; book or cancel classes for clients; record payments; view memberships and payment status; upload and approve medical certificates and waivers; assign clients to professors. |
| R-F2 | **Accountant** can edit financial records and **can see client names and contact details**. No other non-financial data. |
| R-F3 | A class can be transferred by **its current owner or the Admin**. **Bookings are kept.** |
| R-F4 | Clients can be assigned to professors by **Admin, Receptionist or the professor**. A client **can have several professors**. |
| R-F5 | Admin, Professor, Accountant, Receptionist and Client are **built-in, locked roles**. Admin can add **custom roles** on top. |
| R-F6 | Client accounts are created by **Admin and Receptionist only**. |

**Workflow follow-ups: resolved**

| ID | Decision |
|---|---|
| W-F1 | Routine edits: **both are asked**. The editing professor decides whether to offer the update. If they do, **each affected client** chooses to accept it or keep their current version (assumed flow). |
| W-F2 | **Professor approval is removed** (this supersedes the earlier CN-E6/PL2 decision). Before creating their own content or plans, a client must **sign a liability contract** accepting responsibility for the plan and its consequences. |
| W-F3 | Cancellation limit is **per calendar month**. On reaching it the client **cannot cancel**, and **staff is notified** to decide. |
| W-F4 | **Booking limits per membership tier**, configurable (e.g. 3 classes per week). |
| W-F5 | **Only the client** records progress logs. **Assigned professors can view** them. |

**Final open items: resolved**

| ID | Decision |
|---|---|
| O-8 | The liability contract must be signed **before** a client can create their own content or plans (no grace period). Treated as a document separate from the general waiver. |
| O-1 | The medical certificate is **valid for 1 year**. It is visible to **Admin, Receptionist and Professors**. If it is missing after 30 days, or has expired, the client is **blocked** (booking and check-in) and **notified**. |
| O-2 | Minors: **guardian details stored on the minor's profile, plus a consent form signed by the guardian**. |
| O-3 | WhatsApp provider: **Meta WhatsApp Cloud API**. |
| O-4 | 2FA is **required for Admin, Accountant and Receptionist**, and **optional** for Professor, Client and custom roles. |
| O-5 | Accounting export is a **file download only** (Excel/CSV). |
| O-7 | Payments are **recorded by** Accountant, Receptionist and Admin, and **edited or voided by** Accountant and Admin only. |
| O-6 | Hosting and scale: **still undecided**. The architecture stays cloud-neutral (containers; storage behind an abstraction). |

**Deferred by decision (not blocking):** payment gateway and online billing (CN-I2), check-in hardware (CN-I4), cloud provider and scale (O-6).

- **[CLARIFICATION NEEDED] `O-1`**: Medical certificate: does it **expire** (often yearly)? Who validates it (reception?) and who can see it? What happens after the 30 days if it is still missing: block booking, block check-in, or only notify?
- **[CLARIFICATION NEEDED] `O-2`**: Confirm minors' guardian consent = guardian details + a signed consent document.
- **[CLARIFICATION NEEDED] `O-3`**: WhatsApp needs a business provider (WhatsApp Cloud API by Meta, Twilio, etc.) and pre-approved message templates. Do you have a preference?
- **[CLARIFICATION NEEDED] `O-4`**: Is 2FA **required** or **optional**, and for which roles: Admin and Accountant only, or all staff?
- **[CLARIFICATION NEEDED] `O-5`**: Accounting export: an Excel/CSV download, or integration with specific accounting software?
- **[CLARIFICATION NEEDED] `O-6`**: Hosting: Azure or AWS? Expected client and staff counts at launch?
- **[CLARIFICATION NEEDED] `O-7`**: Who records payments while there is no gateway: the Accountant only, or Reception too?

**Next step:** resolve these section by section (Roles → Features & Workflows → Business Rules → Integrations), then rewrite the BRD as v2 with numbered requirements and acceptance criteria.
