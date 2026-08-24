# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repository is a fresh scaffold with no source code yet — only `LICENSE`, `README.md`, `.gitignore` (Python template), and `CLIENT.md` (product spec). There are no build, lint, or test commands to document yet because no project has been initialized. When scaffolding the backend, check `.gitignore` for the intended stack signal (it's a standard Python `.gitignore`, covering Django/Flask/pytest/ruff/uv/poetry/pdm patterns) and confirm the specific framework/tooling with the user before assuming one.

Once code exists, update this file with the actual build/lint/test commands and real architecture — do not leave this section stale.

## Product context (from CLIENT.md)

This backend serves a gym platform with three clients: a backend (this repo), a frontend admin dashboard, and a multiplatform mobile app. Domain model:

- **Exercise**: has a short video (5–10s), a description, and a category.
- **Subroutine**: a small group of exercises.
- **Routine**: a group of exercises and/or subroutines, performed for a configurable number of rounds.
- Exercises/routines/subroutines are preloaded (seeded) content, each with configurable rest time between exercises, exercise duration, and number of rounds.

Users:
- Must create an account (email/username + password); email can be changed if not already in use.
- Can create their own custom routines.
- Have a profile with favorite routines, subroutines, and exercises.

Roles:
- **Admin**: full management of gym/user data via the web dashboard.
- **Professor**: same as Admin but with reduced permissions (scope TBD).
- **User**: end client using the mobile app.

Auth: JWT-based, with frontend session handling.
