# Study Buddy Extension Plan

## Top-Level Overview

**Goal:** Extend the existing Study Buddy application (FastAPI + Next.js 14 + SQLite/PostgreSQL + SQLAlchemy async ORM) to add an institutional management layer: role-based access control (Admin/Teacher + Student), student management, assignment distribution, marks tracking, timetable management, notifications, and student-to-student note sharing.

**Approach:**
- All new backend tables are added via Alembic migrations — no existing data is destroyed.
- All existing AI study tool endpoints are preserved untouched; they will be protected by auth middleware.
- JWT-based auth (python-jose + passlib on backend, httpOnly cookie storage on frontend).
- Frontend navigation is restructured to a sidebar + route-based layout; existing tab features become nested routes under `/learn`.
- File uploads (assignments, notes, profile photos) are abstracted behind a `StorageService` interface backed by the local filesystem, swappable for cloud later.
- No new frameworks introduced — stay within FastAPI, SQLAlchemy, Next.js 14, Tailwind CSS, TypeScript.

**Scope:**
1. Auth foundation (JWT, roles, middleware)
2. Database migrations (all new tables)
3. Student registration & management
4. Assignment management
5. Notification system (in-app + email)
6. Marks distribution
7. Timetable generator
8. Student connections
9. Note sharing
10. Student dashboard
11. Admin/Teacher dashboard
12. Frontend navigation restructure + all new pages
13. Security hardening
14. Testing & validation

---

## Sub-Task 1 — Alembic Setup & Auth Foundation

### Intent
The existing project has no migrations system and no auth. This sub-task installs Alembic, creates the initial migration from existing ORM models, then adds the `User`, `Role`, and auth token infrastructure needed by every later sub-task.

### Expected Outcomes
- `alembic/` directory exists with `env.py` pointing at the existing `DATABASE_URL`.
- Running `alembic upgrade head` creates/preserves all existing tables and adds `users` table with fields: `id`, `email`, `password_hash`, `role` (enum: admin, student), `is_active`, `created_at`, `updated_at`.
- Backend has `/api/auth/register` (student self-registration), `/api/auth/login`, `/api/auth/logout`, `/api/auth/me` endpoints.
- JWT is issued on login, stored in `httpOnly` cookie by the Next.js API route acting as a proxy (or sent as Bearer — confirm in implementation).
- `get_current_user` FastAPI dependency correctly resolves user from token; `require_role("admin")` / `require_role("student")` guards exist.
- All existing AI endpoints (`/api/ask`, `/api/upload`, etc.) accept an optional auth header but remain backward-compatible for now (auth added progressively per later sub-tasks).
- `ADMIN_SEED_EMAIL` / `ADMIN_SEED_PASSWORD` env vars let the first admin be created by running `python seed_admin.py`.

### Todo List
1. Add `alembic`, `python-jose[cryptography]`, `passlib[bcrypt]` to `backend/requirements.txt`.
2. Run `alembic init alembic` inside `backend/` and configure `env.py` to use the SQLAlchemy `DATABASE_URL` from `config.py`.
3. Add `User` ORM model to `backend/models/db_models.py` with fields: `id` (UUID str), `email` (unique), `password_hash`, `role` (str, default "student"), `is_active` (bool, default True), `full_name` (str), `created_at`, `updated_at`.
4. Create initial Alembic migration (`alembic revision --autogenerate -m "add users table"`).
5. Create `backend/services/auth_service.py`: JWT encode/decode (HS256, 30-minute access token), password hash/verify with bcrypt.
6. Create `backend/routers/auth.py` with POST `/api/auth/register`, POST `/api/auth/login`, POST `/api/auth/logout`, GET `/api/auth/me`.
7. Create `backend/dependencies/auth.py` with `get_current_user`, `require_admin`, `require_student`, `get_optional_user` FastAPI dependency functions.
8. Register `auth` router in `backend/main.py`.
9. Create `backend/seed_admin.py` script that reads `ADMIN_SEED_EMAIL` and `ADMIN_SEED_PASSWORD` env vars, creates an admin user if not already present.
10. Add `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `ADMIN_SEED_EMAIL`, `ADMIN_SEED_PASSWORD` to `backend/.env.example` and `backend/config.py`.

### Relevant Context
- Existing ORM base: `backend/models/db_models.py`
- Existing config: `backend/config.py` (pydantic-settings)
- Existing DB init: `backend/database.py`
- Router registration: `backend/main.py`
- Tech: SQLAlchemy 2.x async, FastAPI `Depends()`

### Status
[ ] pending

---

## Sub-Task 2 — Database Migrations: All New Tables

### Intent
Create Alembic migrations for every new domain entity needed by sub-tasks 3–12. All migrations run against the existing `studybuddy.db` without touching existing tables (`documents`, `quiz_sessions`, `quiz_results`, `chat_sessions`, `chat_messages`, `flashcard_sessions`, `flashcards`, `feynman_results`, `saved_answers`, `shared_resources`).

### Expected Outcomes
- Running `alembic upgrade head` from a clean DB produces all tables below.
- All FK relationships are correct; SQLite FK pragma is enabled.
- ORM models exist in `backend/models/db_models.py` for each table.
- Pydantic schemas exist in `backend/models/schemas.py` for request/response of each entity.

### New Tables

| Table | Key Fields |
|-------|-----------|
| `student_profiles` | user_id (FK users), student_id (unique), phone, course, branch, semester, section, academic_year, dob, profile_photo_url |
| `classes` | id, name, course, created_by (FK users) |
| `sections` | id, name, class_id (FK classes) |
| `subjects` | id, name, code, class_id (FK classes), created_by (FK users) |
| `assignments` | id, title, subject_id (FK), class_id (FK), section_id (FK, nullable), description, instructions, file_url, due_date, due_time, max_marks, created_by (FK), is_published, created_at |
| `assignment_submissions` | id, assignment_id (FK), student_id (FK users), file_url, submitted_at, marks_obtained, feedback, is_evaluated, status (enum: submitted, late, evaluated) |
| `assessment_categories` | id, name, subject_id (FK), max_marks, weightage, created_by (FK) |
| `marks` | id, student_id (FK users), category_id (FK assessment_categories), obtained_marks, remarks, is_published, created_at, updated_at |
| `timetables` | id, class_id (FK), section_id (FK, nullable), start_time (time), periods_per_day (int), lunch_after_period (int), is_published, created_by (FK), created_at, updated_at |
| `timetable_slots` | id, timetable_id (FK), day_of_week (0-5, Mon-Sat), period_number (int), subject_id (FK, nullable), teacher_id (FK users, nullable), room (str, nullable) |
| `notifications` | id, user_id (FK users), title, message, type (enum: assignment, submission, marks, timetable, announcement, note, registration), reference_id (str, nullable), is_read, created_at |
| `announcements` | id, title, content, created_by (FK users), class_id (FK, nullable), section_id (FK, nullable), created_at |
| `connection_requests` | id, from_user_id (FK users), to_user_id (FK users), status (enum: pending, accepted, rejected), created_at, updated_at |
| `student_connections` | id, user_a_id (FK users), user_b_id (FK users), connected_at |
| `notes` | id, title, description, subject, course, semester, tags (str), file_url, uploaded_by (FK users), visibility (enum: connections, class, public), created_at |
| `note_accesses` | id, note_id (FK notes), user_id (FK users), accessed_at |

### Todo List
1. Add all new ORM models to `backend/models/db_models.py`.
2. Run `alembic revision --autogenerate -m "add institutional management tables"`.
3. Review generated migration file for correctness; fix any auto-generate misses.
4. Add all Pydantic request/response schemas to `backend/models/schemas.py` for each new entity (Create, Update, Response variants).
5. Add `PRAGMA foreign_keys = ON` to the SQLite connection event listener in `backend/database.py`.
6. Verify migration runs cleanly: `alembic upgrade head`.

### Relevant Context
- Existing models: `backend/models/db_models.py`
- Existing schemas: `backend/models/schemas.py`
- DB engine: `backend/database.py`

### Status
[ ] pending

---

## Sub-Task 3 — Student Registration & Profile Management

### Intent
Implement the complete student registration flow: self-registration by students, admin management of student accounts, and profile editing.

### Expected Outcomes
- `POST /api/auth/register` (student) validates all fields, hashes password, creates `User` + `StudentProfile` records atomically, sends registration confirmation email, returns JWT.
- `GET /api/admin/students` returns paginated list of students (admin only).
- `GET /api/admin/students/{id}` returns full student profile (admin only).
- `PATCH /api/admin/students/{id}/status` activates/deactivates a student (admin only).
- `GET /api/students/profile` returns the logged-in student's profile.
- `PATCH /api/students/profile` allows students to update allowed fields (phone, profile_photo, section).
- Profile photo upload stored via `StorageService`.
- Duplicate email and duplicate student_id are rejected with clear errors.

### Todo List
1. Create `backend/services/storage_service.py` with `save_file(file, folder) -> str` (returns URL), `delete_file(url)`. Backed by local filesystem (`./uploads/{folder}/`); interface ready for cloud swap.
2. Extend `POST /api/auth/register` in `backend/routers/auth.py` to accept full student registration fields and create `StudentProfile`.
3. Create `backend/routers/admin_students.py` with: `GET /api/admin/students`, `GET /api/admin/students/{id}`, `PATCH /api/admin/students/{id}/status`, `DELETE /api/admin/students/{id}` (soft delete via is_active).
4. Create `backend/routers/student_profile.py` with `GET /api/students/profile`, `PATCH /api/students/profile`, `POST /api/students/profile/photo`.
5. Register both new routers in `backend/main.py`.
6. Add validation: email uniqueness, student_id uniqueness, password minimum length, phone format.
7. Wire registration to trigger a notification (notification service created in Sub-Task 5).

### Relevant Context
- Auth router: `backend/routers/auth.py` (created in Sub-Task 1)
- Auth dependency: `backend/dependencies/auth.py`
- Storage service pattern: local filesystem, abstract interface

### Status
[ ] pending

---

## Sub-Task 4 — Class, Section, and Subject Management

### Intent
Give admins the ability to create and manage the academic structure (classes, sections, subjects) that assignments, timetables, and marks reference.

### Expected Outcomes
- Full CRUD for classes (`/api/admin/classes`), sections (`/api/admin/sections`), and subjects (`/api/admin/subjects`) — all admin-only.
- `GET /api/students/classes`, `GET /api/students/subjects` returns data relevant to the logged-in student's course/semester.
- Class/section/subject data used by assignment, marks, and timetable sub-tasks.

### Todo List
1. Create `backend/routers/admin_classes.py` with CRUD endpoints for Class, Section, Subject.
2. Add read-only endpoints in `backend/routers/student_classes.py` for students to list classes/subjects.
3. Register both routers in `backend/main.py`.
4. Add Pydantic schemas for Class, Section, Subject (Create/Update/Response).

### Relevant Context
- ORM models from Sub-Task 2
- Admin auth guard from Sub-Task 1

### Status
[ ] pending

---

## Sub-Task 5 — Notification & Email Service

### Intent
Build the two foundational services (notification creation and email dispatch) that every other sub-task calls when events occur. Must be implemented before assignment, marks, or timetable sub-tasks.

### Expected Outcomes
- `backend/services/notification_service.py` exposes `create_notification(db, user_id, title, message, type, reference_id)` — creates a `Notification` row and returns it.
- `create_bulk_notifications(db, user_ids, ...)` creates notifications for multiple students at once (used by assignment publish, timetable publish).
- `backend/services/email_service.py` exposes `send_email(to, subject, template_name, context)`. Uses SMTP via `aiosmtplib` (async). Reads `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` from env vars. If vars are not set, logs a warning and skips silently (no crash).
- Email templates in `backend/templates/email/`: `registration_confirmation.html`, `new_assignment.html`, `marks_published.html`, `timetable_published.html`. Templates use simple Python string formatting (no Jinja2 dep needed — but if Jinja2 is already in requirements, use it).
- Student notification API endpoints: `GET /api/notifications` (paginated, newest first), `PATCH /api/notifications/{id}/read`, `PATCH /api/notifications/read-all`, `GET /api/notifications/unread-count`.
- All notification endpoints require student or admin auth.

### Todo List
1. Add `aiosmtplib` to `backend/requirements.txt`.
2. Create `backend/services/notification_service.py` with `create_notification` and `create_bulk_notifications`.
3. Create `backend/services/email_service.py` with async `send_email`, template loader, and graceful no-op when SMTP env vars absent.
4. Create `backend/templates/email/` directory with 4 HTML email templates (Study Buddy branding, responsive, relevant fields).
5. Create `backend/routers/notifications.py` with notification read/list endpoints.
6. Add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `APP_BASE_URL` to `backend/config.py` and `.env.example`.
7. Register notifications router in `backend/main.py`.

### Relevant Context
- Notification ORM model: `backend/models/db_models.py` (Sub-Task 2)
- Config pattern: `backend/config.py` (pydantic-settings)

### Status
[ ] pending

---

## Sub-Task 6 — Assignment Management

### Intent
Implement the complete assignment lifecycle: creation by admin, publishing to a class/section, student viewing and submission, admin review and grading.

### Expected Outcomes
- Admin can create assignment (with optional file), publish it to a class/section.
- On publish, `create_bulk_notifications` is called for all students in the target class/section, and email is sent.
- Students see only assignments for their class/section.
- Students can submit an assignment (upload file) before the due date (or late — marked accordingly).
- Admin can view all submissions, filter by class/section/status, download files, enter marks, add feedback, mark as evaluated.
- On evaluation, student gets an in-app notification + email.
- Due-date approaching reminder: a background task checks for assignments due within 24 hours and sends reminders (use `asyncio` + FastAPI `lifespan` or `apscheduler` — pick whichever is lighter given existing deps).

### Todo List
1. Create `backend/routers/admin_assignments.py` with: `POST /api/admin/assignments`, `GET /api/admin/assignments`, `PATCH /api/admin/assignments/{id}`, `POST /api/admin/assignments/{id}/publish`, `DELETE /api/admin/assignments/{id}`.
2. Create `backend/routers/admin_submissions.py` with: `GET /api/admin/submissions` (filter params: assignment_id, class_id, section_id, status), `GET /api/admin/submissions/{id}`, `PATCH /api/admin/submissions/{id}/grade` (marks, feedback, mark_evaluated), `GET /api/admin/assignments/{id}/submissions`.
3. Create `backend/routers/student_assignments.py` with: `GET /api/assignments` (student's assignments), `GET /api/assignments/{id}`, `POST /api/assignments/{id}/submit`, `GET /api/assignments/{id}/submission`.
4. In publish handler, query `student_profiles` for matching class/section, call `create_bulk_notifications` and `email_service.send_email` for each.
5. In grade handler, call `create_notification` and `send_email` to the submitting student.
6. Add `apscheduler` to requirements; create `backend/tasks/deadline_reminder.py` that runs daily at 8 AM and sends notifications for assignments due within 24 hours.
7. Register all new routers in `backend/main.py`.
8. File uploads use `StorageService` (Sub-Task 3); validate file type (PDF, DOCX, PPTX, images, ZIP) and size (max configurable via env).

### Relevant Context
- Assignment/Submission ORM from Sub-Task 2
- Notification service from Sub-Task 5
- Storage service from Sub-Task 3
- Auth guards from Sub-Task 1

### Status
[ ] pending

---

## Sub-Task 7 — Marks Distribution System

### Intent
Implement the full marks management module: assessment categories with weightages, manual mark entry, automatic percentage/grade calculation, and controlled publishing.

### Expected Outcomes
- Admin creates `AssessmentCategory` records per subject (name, max_marks, weightage).
- Admin enters marks for individual students per category.
- System auto-calculates total obtained, total max, percentage, and grade (S ≥ 90%, A ≥ 80%, B ≥ 70%, C ≥ 60%, D ≥ 50%, F < 50%) using existing grade logic already present in `QuizResult`.
- Validation: `obtained_marks <= max_marks` enforced at DB and API level.
- Admin can publish marks for a subject/category — triggers notification + email to affected students.
- Students see only published marks.
- Student marks view: subject-wise breakdown, assessment-wise, overall percentage, grade, teacher remarks.

### Todo List
1. Create `backend/routers/admin_marks.py` with: `POST /api/admin/assessment-categories`, `GET /api/admin/assessment-categories`, `PATCH /api/admin/assessment-categories/{id}`, `POST /api/admin/marks` (bulk entry), `PATCH /api/admin/marks/{id}`, `POST /api/admin/marks/publish` (publish by subject/category), `GET /api/admin/marks/report` (class-wise overview).
2. Create `backend/routers/student_marks.py` with: `GET /api/marks` (student's own marks, published only), `GET /api/marks/subject/{subject_id}`, `GET /api/marks/summary` (overall percentage, grade, subject breakdown).
3. Create `backend/services/marks_service.py` with `calculate_summary(student_id, subject_id, db)` → total obtained, total max, percentage, grade.
4. In publish handler, call `create_bulk_notifications` + email for affected students.
5. Register routers in `backend/main.py`.

### Relevant Context
- Grade scale already exists in `quiz.py` router (S/A/B/C/D) — reuse same thresholds.
- Assessment/Marks ORM from Sub-Task 2

### Status
[ ] pending

---

## Sub-Task 8 — Timetable Generator

### Intent
Build a configurable timetable system where admin defines start time, periods per day, lunch placement, and assigns subjects/teachers to slots. Auto-calculates period times (45 min each) and detects conflicts.

### Expected Outcomes
- Admin creates a `Timetable` record specifying: class_id, section_id, start_time, periods_per_day, lunch_after_period (e.g., 4 = lunch after period 4).
- Admin creates `TimetableSlot` records: day_of_week (0–5), period_number, subject_id, teacher_id, room.
- `GET /api/admin/timetables/{id}/slots` returns slots with computed start/end times (backend calculates: start_time + (period_number - 1) * 45 min, with lunch offset applied).
- Conflict detection: before saving a slot, check no teacher has 2 simultaneous slots across timetables on the same day/period; same for room.
- Admin can publish timetable → notifies all students in the class/section.
- `GET /api/timetable` (student) returns the timetable for the student's class/section with computed times.
- `GET /api/admin/timetables/teacher/{teacher_id}` returns teacher's schedule across all classes.
- Timetable can be updated (add/remove slots) or deleted by admin.

### Todo List
1. Create `backend/services/timetable_service.py` with: `compute_slot_times(start_time, period_number, lunch_after_period)` → `(start: time, end: time)`, `check_teacher_conflict(db, teacher_id, timetable_id, day, period)`, `check_room_conflict(db, room, timetable_id, day, period)`.
2. Create `backend/routers/admin_timetable.py` with full CRUD for Timetable and TimetableSlot, conflict-check on slot creation/update, publish endpoint.
3. Create `backend/routers/student_timetable.py` with `GET /api/timetable` (returns student's timetable with computed times) and `GET /api/timetable/today` (today's schedule only).
4. In publish handler, call `create_bulk_notifications` + email.
5. Register routers in `backend/main.py`.

### Relevant Context
- Timetable/TimetableSlot ORM from Sub-Task 2
- Period duration: 45 minutes; lunch duration: 45 minutes — both constants in `config.py`

### Status
[ ] pending

---

## Sub-Task 9 — Student Connections & Note Sharing

### Intent
Allow students to connect with each other and share educational notes/resources, with visibility controls.

### Expected Outcomes
- Students can search other students by name, student_id, course, semester, section.
- Students can send/accept/reject connection requests; see their connections list.
- Students can upload notes (PDF, DOCX, PPTX, images); set visibility (connections / class / public).
- Note list respects visibility rules: `connections` notes shown only to connected students; `class` notes to same class; `public` to all Study Buddy students.
- Students can download notes (file served via `/api/notes/{id}/download`); access logged in `note_accesses`.
- Students can search/filter notes by subject, semester, tags.
- Students can delete their own notes.
- On note upload, notification sent to connected students (if visibility = connections).

### Todo List
1. Create `backend/routers/connections.py` with: `GET /api/students/search` (query params: name, student_id, course, semester, section), `POST /api/connections/request`, `PATCH /api/connections/{id}/respond` (accept/reject), `GET /api/connections`, `DELETE /api/connections/{id}`.
2. Create `backend/routers/notes.py` with: `POST /api/notes` (upload + metadata), `GET /api/notes` (filtered, visibility-aware), `GET /api/notes/{id}`, `GET /api/notes/{id}/download`, `DELETE /api/notes/{id}` (own notes only).
3. In note upload, if visibility = connections, call `create_bulk_notifications` for connected students.
4. Enforce visibility rules in the `GET /api/notes` query: LEFT JOIN with `student_connections` for connections visibility, filter by class_id for class visibility.
5. Log `NoteAccess` on each download.
6. File upload via `StorageService`; validate allowed types: PDF, DOCX, PPTX, PPT, PNG, JPG, WEBP; max size configurable.
7. Register both routers in `backend/main.py`.

### Relevant Context
- Connection/Note ORM from Sub-Task 2
- StorageService from Sub-Task 3
- Notification service from Sub-Task 5

### Status
[ ] pending

---

## Sub-Task 10 — Frontend: Auth Pages & Navigation Restructure

### Intent
Replace the current single-page tab layout with a sidebar + route-based navigation. Add login, register, and auth context. Existing AI study tools move to `/learn/*` routes. All new institutional pages get their own routes.

### Expected Outcomes
- New pages: `/login`, `/register` (student signup form with all required fields).
- Auth context (`src/context/AuthContext.tsx`) manages: current user, role, login/logout, token refresh.
- All pages are protected by `AuthGuard` component — redirect to `/login` if not authenticated.
- Sidebar component renders different nav items based on role:
  - **Student nav:** Dashboard, Assignments, Timetable, Marks, Notifications, Notes, Connections, Learn (AI tools), Profile
  - **Admin nav:** Dashboard, Students, Classes, Subjects, Assignments, Submissions, Marks, Timetable, Notes, Notifications, Announcements, Settings
- Current tab-based UI (`src/app/page.tsx`) is refactored into `/learn` page with sub-tabs intact — all 8 AI tools still work.
- Notification bell in top header shows unread count, opens dropdown with recent notifications.
- Responsive: sidebar collapses to hamburger menu on mobile.
- The `NEXT_PUBLIC_API_URL` API base is already set — all new API calls use the same Axios instance in `src/lib/api.ts`.

### Todo List
1. Create `src/context/AuthContext.tsx`: stores user, role, token; exposes `login(email, password)`, `logout()`, `register(formData)`; reads user from `/api/auth/me` on mount.
2. Create `src/components/layout/Sidebar.tsx`: role-aware nav links, collapse on mobile, active route highlight.
3. Create `src/components/layout/Header.tsx`: notification bell with unread count badge, user avatar, logout button.
4. Create `src/components/layout/AuthGuard.tsx`: redirects to `/login` if no session; optionally redirects students away from admin routes.
5. Refactor `src/app/layout.tsx` to wrap children in `AuthContext` + conditional `Sidebar` + `Header` layout (no sidebar shown on `/login` or `/register`).
6. Create `src/app/login/page.tsx` and `src/app/register/page.tsx` with forms matching the student registration fields.
7. Move current `src/app/page.tsx` content to `src/app/learn/page.tsx`; update `src/app/page.tsx` to redirect authenticated users to `/dashboard`.
8. Create empty page stubs for all new routes (to be filled in Sub-Tasks 11–12): `/dashboard`, `/assignments`, `/timetable`, `/marks`, `/notifications`, `/notes`, `/connections`, `/profile`, `/admin/students`, `/admin/assignments`, `/admin/submissions`, `/admin/marks`, `/admin/timetable`, `/admin/notifications`, `/admin/announcements`.
9. Create `src/hooks/useNotifications.ts` hook that polls `/api/notifications/unread-count` every 30 seconds and returns the count.
10. Update `src/lib/api.ts` Axios instance to include `withCredentials: true` (for httpOnly cookie auth) and a 401 interceptor that redirects to `/login`.

### Relevant Context
- Existing: `src/app/page.tsx`, `src/lib/api.ts`, `src/app/layout.tsx`
- Existing Tailwind + Framer Motion — use same styling conventions
- TypeScript strict mode — all new components must be fully typed

### Status
[ ] pending

---

## Sub-Task 11 — Frontend: Student Pages

### Intent
Build all student-facing pages: dashboard, assignments, marks, timetable, notifications, notes, connections, and profile.

### Expected Outcomes
Each page is responsive, uses Tailwind CSS consistent with existing design, and communicates with the backend API endpoints created in Sub-Tasks 3–9.

Pages to build:
- **`/dashboard`** — cards: Upcoming Assignments (next 3), Pending Submissions, Today's Timetable (next 2 classes), Recent Marks, Unread Notifications count, Quick Links to AI tools.
- **`/assignments`** — list of student's assignments (tabs: All, Pending, Submitted, Evaluated); each card shows title, subject, due date, countdown timer, status badge; click to open detail modal with instructions + download file + submit form.
- **`/marks`** — subject-wise table; summary card (overall %, grade); collapsible rows showing assessment breakdown.
- **`/timetable`** — weekly grid view (Mon–Sat × periods); highlights today; shows computed period times; current/next class highlighted.
- **`/notifications`** — list with type icon, timestamp, read/unread state; mark as read; mark all as read.
- **`/notes`** — grid of note cards; upload form (title, desc, subject, course, semester, tags, file, visibility); search + filter by subject/semester; download button.
- **`/connections`** — search bar with filters; incoming request cards (accept/reject); connected students list; remove connection.
- **`/profile`** — view and edit profile fields; profile photo upload; display read-only fields (student ID, email, course, academic year).

### Todo List
1. Create `src/app/dashboard/page.tsx` with 6 dashboard widgets using the APIs.
2. Create `src/app/assignments/page.tsx` + `src/components/features/AssignmentCard.tsx` + `src/components/features/AssignmentSubmitModal.tsx`.
3. Create `src/app/marks/page.tsx` + `src/components/features/MarksTable.tsx` + `src/components/features/MarksSummaryCard.tsx`.
4. Create `src/app/timetable/page.tsx` + `src/components/features/TimetableGrid.tsx` (weekly grid, computed period times).
5. Create `src/app/notifications/page.tsx` + `src/components/features/NotificationList.tsx`.
6. Create `src/app/notes/page.tsx` + `src/components/features/NoteCard.tsx` + `src/components/features/NoteUploadForm.tsx`.
7. Create `src/app/connections/page.tsx` + `src/components/features/StudentSearchCard.tsx` + `src/components/features/ConnectionRequestCard.tsx`.
8. Create `src/app/profile/page.tsx` with editable form and photo upload.
9. Add typed API helper functions to `src/lib/api.ts` for every new endpoint consumed by these pages.
10. Add all new TypeScript types to `src/types/index.ts`.

### Relevant Context
- Existing component style: Tailwind utility classes, Lucide React icons, Framer Motion animations for page transitions
- Existing hooks pattern: `src/hooks/` for API-connected state

### Status
[ ] pending

---

## Sub-Task 12 — Frontend: Admin/Teacher Pages

### Intent
Build all admin-facing pages: dashboard, student management, assignment creation, submission review, marks entry, timetable builder, announcements, and notifications management.

### Expected Outcomes
All admin pages are behind `AuthGuard` with `requireRole="admin"`.

Pages to build:
- **`/admin/dashboard`** — stat cards: Total Students, Active Students, Total Assignments, Pending Submissions, Recent Registrations; Quick Action buttons.
- **`/admin/students`** — searchable/filterable student table; view profile; activate/deactivate toggle.
- **`/admin/assignments`** — list assignments with publish status; create new assignment form (title, subject, class, section, due date, max marks, file upload); publish button.
- **`/admin/submissions`** — filter by assignment/class/section/status; table showing student name, status, submitted_at; click row to grade (marks input, feedback textarea, mark evaluated).
- **`/admin/marks`** — select subject → manage assessment categories (name, max marks, weightage); enter marks per student per category; publish button.
- **`/admin/timetable`** — create timetable form (class, section, start time, periods per day, lunch after period N); slot editor (day × period grid with dropdowns for subject, teacher, room); conflict alert; publish button.
- **`/admin/announcements`** — create announcement (title, content, target class/section or all); list of past announcements.
- **`/admin/notifications`** — view all notifications sent (read-only audit view); compose and send manual notification to a student or group.

### Todo List
1. Create `src/app/admin/dashboard/page.tsx` with stat cards and quick action buttons.
2. Create `src/app/admin/students/page.tsx` with student table, search, and profile drawer.
3. Create `src/app/admin/assignments/page.tsx` + `src/components/features/admin/AssignmentForm.tsx`.
4. Create `src/app/admin/submissions/page.tsx` + `src/components/features/admin/GradeSubmissionModal.tsx`.
5. Create `src/app/admin/marks/page.tsx` + `src/components/features/admin/MarksEntryTable.tsx` + `src/components/features/admin/AssessmentCategoryForm.tsx`.
6. Create `src/app/admin/timetable/page.tsx` + `src/components/features/admin/TimetableBuilder.tsx` (grid-based slot editor with conflict indicators).
7. Create `src/app/admin/announcements/page.tsx`.
8. Create `src/app/admin/notifications/page.tsx`.
9. Add `src/components/layout/AdminGuard.tsx` that redirects students who try to access `/admin/*` routes.
10. Add all admin API helper functions to `src/lib/api.ts`.

### Relevant Context
- All admin API endpoints created in Sub-Tasks 3–9
- Same Tailwind/Framer Motion/TypeScript conventions as student pages

### Status
[ ] pending

---

## Sub-Task 13 — Protect Existing AI Endpoints & Announcement API

### Intent
Now that auth exists and all new features work, add auth protection to the existing AI study tool endpoints so each user's documents, quizzes, and chats are isolated. Also add the announcements backend API.

### Expected Outcomes
- All existing AI endpoints require authentication (JWT token in cookie or Bearer header).
- `user_id` FK added (via Alembic migration) to: `documents`, `quiz_results`, `chat_sessions`, `saved_answers`, `feynman_results`, `flashcard_sessions`.
- Queries in all existing routers filter by `current_user.id` so users only see their own data.
- Existing frontend Axios instance sends credentials (already set in Sub-Task 10) — no other frontend changes needed.
- Admin announcement endpoints: `POST /api/admin/announcements`, `GET /api/admin/announcements`, `PATCH /api/admin/announcements/{id}`, `DELETE /api/admin/announcements/{id}`.
- Student announcement endpoint: `GET /api/announcements` (filtered to student's class/section + global).
- Existing `share` links remain public (no auth required — they use the existing `SharedResource` table).

### Todo List
1. Create Alembic migration: add nullable `user_id` FK to the 6 existing tables listed above.
2. Update each existing router to use `Depends(get_current_user)` and filter queries by `user_id`.
3. Update `backend/routers/upload.py` to associate uploaded documents with the current user.
4. Create `backend/routers/announcements.py` with admin CRUD and student read endpoints.
5. Register announcements router in `backend/main.py`.
6. Verify existing share link endpoints still work without auth (they resolve by `share_id` and don't expose user data).

### Relevant Context
- All existing routers in `backend/routers/`
- `get_current_user` dependency from Sub-Task 1
- Migration pattern from Sub-Task 2

### Status
[ ] pending

---

## Sub-Task 14 — Security Hardening & Validation

### Intent
Systematic security pass: file upload restrictions, authorization checks on every endpoint, input validation, environment variable audit.

### Expected Outcomes
- Every admin endpoint has `require_admin` guard.
- Every student endpoint has `require_student` guard with ownership checks (student cannot access another student's submissions/marks/notes).
- File upload validation: whitelist of allowed MIME types and extensions per upload type (assignment files: PDF/DOCX/PPTX/ZIP/images; notes: same; profile photo: PNG/JPG/WEBP); max file size checked before writing to disk.
- `obtained_marks <= max_marks` enforced at API level (Pydantic validator).
- Pagination added to all list endpoints (default page_size=20, max=100).
- CORS origins in `backend/config.py` enforced strictly (no `*`).
- `SECRET_KEY` must be set and cannot be a weak default — startup check added.
- All env vars documented in `backend/.env.example`.

### Todo List
1. Audit every new router and add missing role guards.
2. Add ownership checks: marks grade endpoint verifies the marks record belongs to an assignment that targets the requesting student's class; note delete verifies uploader is current user.
3. Add Pydantic validators for `obtained_marks <= max_marks` in the marks schema.
4. Add `validate_file_type(file, allowed_types)` utility function in `backend/utils/file_utils.py`; call it in all upload handlers.
5. Add startup validation in `backend/main.py`: if `SECRET_KEY` is unset or equals a known weak default, raise `RuntimeError` and refuse to start.
6. Add pagination query params (`page`, `page_size`) to all list endpoints using a shared `PaginationParams` dependency.
7. Update `backend/.env.example` with every env var introduced across all sub-tasks.

### Relevant Context
- All routers created in Sub-Tasks 1–13
- `backend/config.py` for env var additions
- Pydantic v2 validators: `@field_validator` syntax

### Status
[ ] pending

---

## Sub-Task 15 — Testing, Integration Validation & Documentation

### Intent
Verify all existing features still work, test each new feature end-to-end, and produce a final summary document.

### Expected Outcomes
- Existing AI tools (ask, quiz, explain, feynman, flashcards, concept map, cheatsheet, progress) all work for authenticated users.
- New features verified: register student, login, view dashboard, receive assignment notification, submit assignment, view marks, view timetable, share note, connect with student.
- Admin flow verified: seed admin login, register student from admin, create class/subject, create and publish assignment, grade submission, enter and publish marks, create and publish timetable.
- `TESTING.md` created documenting: how to seed the first admin, how to test each feature, test user credentials, API curl examples for key endpoints.
- All new environment variables added to `backend/.env.example` and `frontend/.env.example`.
- `README.md` updated with new setup steps (Alembic migrations, admin seeding, new env vars).

### Todo List
1. Run `alembic upgrade head` and verify all tables created cleanly.
2. Run `python seed_admin.py` and verify admin account created.
3. Test auth flow: register student → login → access `/dashboard` → logout → confirm redirect to `/login`.
4. Test assignment flow: admin creates assignment → student receives notification → student submits → admin grades → student sees marks.
5. Test timetable: admin creates timetable with conflict detection → publishes → student views with computed times.
6. Test note sharing: student A uploads note (connections visibility) → student B connects with A → student B sees note in their notes list → downloads it.
7. Test all 8 existing AI tools as authenticated student — confirm they work and are isolated per user.
8. Create `TESTING.md` with step-by-step test scenarios and expected results.
9. Update `README.md` with new env vars, migration steps, seeding instructions, and new feature overview.
10. Update `backend/.env.example` and `frontend/.env.example` with all new variables.

### Relevant Context
- All sub-tasks above must be complete before this runs
- Target: manual test each major flow; automated tests are out of scope for this plan (can be added later)

### Status
[ ] pending

---

## Environment Variables Required (Complete List)

### Backend (`backend/.env`)
```
# Existing
OPENAI_API_KEY=
GROQ_API_KEY=
DATABASE_URL=sqlite+aiosqlite:///./studybuddy.db
CORS_ORIGINS=http://localhost:3000
RATE_LIMIT_PER_MINUTE=20
UPLOAD_DIR=./uploads
CHROMA_PERSIST_DIR=./chroma_db
FAISS_INDEX_DIR=./faiss_indexes
MAX_FILE_SIZE_MB=20

# New: Auth
SECRET_KEY=<generate with: openssl rand -hex 32>
ACCESS_TOKEN_EXPIRE_MINUTES=30
ADMIN_SEED_EMAIL=admin@studybuddy.com
ADMIN_SEED_PASSWORD=<strong password>

# New: Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM=noreply@studybuddy.com
APP_BASE_URL=http://localhost:3000

# New: File Storage
ASSIGNMENT_FILE_MAX_MB=50
NOTE_FILE_MAX_MB=50
PROFILE_PHOTO_MAX_MB=5

# New: Timetable
PERIOD_DURATION_MINUTES=45
LUNCH_DURATION_MINUTES=45
```

### Frontend (`frontend/.env.local`)
```
# Existing
NEXT_PUBLIC_API_URL=http://localhost:8000

# New
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

---

## New API Endpoints Summary

| Method | Path | Role | Sub-Task |
|--------|------|------|----------|
| POST | `/api/auth/register` | public | 1, 3 |
| POST | `/api/auth/login` | public | 1 |
| POST | `/api/auth/logout` | any | 1 |
| GET | `/api/auth/me` | any | 1 |
| GET | `/api/admin/students` | admin | 3 |
| GET | `/api/admin/students/{id}` | admin | 3 |
| PATCH | `/api/admin/students/{id}/status` | admin | 3 |
| GET/POST/PATCH/DELETE | `/api/admin/classes` | admin | 4 |
| GET/POST/PATCH/DELETE | `/api/admin/sections` | admin | 4 |
| GET/POST/PATCH/DELETE | `/api/admin/subjects` | admin | 4 |
| GET | `/api/notifications` | any | 5 |
| PATCH | `/api/notifications/{id}/read` | any | 5 |
| PATCH | `/api/notifications/read-all` | any | 5 |
| GET | `/api/notifications/unread-count` | any | 5 |
| POST/GET/PATCH/DELETE | `/api/admin/assignments` | admin | 6 |
| POST | `/api/admin/assignments/{id}/publish` | admin | 6 |
| GET | `/api/admin/submissions` | admin | 6 |
| PATCH | `/api/admin/submissions/{id}/grade` | admin | 6 |
| GET | `/api/assignments` | student | 6 |
| POST | `/api/assignments/{id}/submit` | student | 6 |
| POST/GET/PATCH | `/api/admin/assessment-categories` | admin | 7 |
| POST/PATCH | `/api/admin/marks` | admin | 7 |
| POST | `/api/admin/marks/publish` | admin | 7 |
| GET | `/api/marks` | student | 7 |
| GET | `/api/marks/summary` | student | 7 |
| POST/GET/PATCH/DELETE | `/api/admin/timetables` | admin | 8 |
| POST | `/api/admin/timetables/{id}/publish` | admin | 8 |
| GET | `/api/timetable` | student | 8 |
| GET | `/api/timetable/today` | student | 8 |
| GET | `/api/students/search` | student | 9 |
| POST | `/api/connections/request` | student | 9 |
| PATCH | `/api/connections/{id}/respond` | student | 9 |
| GET/DELETE | `/api/connections` | student | 9 |
| POST/GET | `/api/notes` | student | 9 |
| GET/DELETE | `/api/notes/{id}` | student | 9 |
| GET | `/api/notes/{id}/download` | student | 9 |
| POST/GET/PATCH/DELETE | `/api/admin/announcements` | admin | 13 |
| GET | `/api/announcements` | student | 13 |

---

## New Frontend Routes Summary

| Route | Role | Sub-Task |
|-------|------|----------|
| `/login` | public | 10 |
| `/register` | public | 10 |
| `/learn` | student | 10 |
| `/dashboard` | student | 11 |
| `/assignments` | student | 11 |
| `/marks` | student | 11 |
| `/timetable` | student | 11 |
| `/notifications` | student | 11 |
| `/notes` | student | 11 |
| `/connections` | student | 11 |
| `/profile` | student | 11 |
| `/admin/dashboard` | admin | 12 |
| `/admin/students` | admin | 12 |
| `/admin/assignments` | admin | 12 |
| `/admin/submissions` | admin | 12 |
| `/admin/marks` | admin | 12 |
| `/admin/timetable` | admin | 12 |
| `/admin/announcements` | admin | 12 |
| `/admin/notifications` | admin | 12 |

---

## Database Migration Summary

| Migration | Tables Added/Modified |
|-----------|----------------------|
| `001_add_users` | `users` (new) |
| `002_add_institutional_tables` | 16 new tables (student_profiles through note_accesses) |
| `003_add_user_id_to_existing` | Add nullable `user_id` FK to 6 existing tables |

---

## How to Create the First Admin Account

```bash
cd backend
# Set env vars first (ADMIN_SEED_EMAIL, ADMIN_SEED_PASSWORD)
python seed_admin.py
# Output: "Admin account created: admin@studybuddy.com"
```

---

## Implementation Order Rationale

```
Sub-Task 1 (Auth) → Sub-Task 2 (DB) → Sub-Task 3 (Students) → Sub-Task 4 (Classes)
→ Sub-Task 5 (Notifications) → Sub-Task 6 (Assignments) → Sub-Task 7 (Marks)
→ Sub-Task 8 (Timetable) → Sub-Task 9 (Connections+Notes)
→ Sub-Task 10 (Frontend Nav) → Sub-Task 11 (Student Pages) → Sub-Task 12 (Admin Pages)
→ Sub-Task 13 (Protect existing + Announcements) → Sub-Task 14 (Security) → Sub-Task 15 (Testing)
```

Sub-tasks 1–9 are backend-only and can be validated independently with the existing FastAPI Swagger UI (`/docs`). Sub-tasks 10–12 are frontend-only. Sub-tasks 13–15 are integration/finishing work.
