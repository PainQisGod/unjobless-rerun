# Un-Jobless - Rerun

A working job board built with Flask and SQLite. Reworked from the previous version.

## Run it

    pip install -r requirements.txt
    python app.py

Open http://127.0.0.1:5000. The database file (`unjobless.db`) is created on first run and filled with six sample jobs.

## What it does

- Browse, search (title, company, location, keywords), filter (location, category, job type) and sort jobs
- Job detail page with address, phone, experience and salary
- Anyone can apply (name, email, optional phone and message); applications are saved
- Anyone can post a job at /post
- Admin area at /admin: see applications, hide or delete jobs, delete applications

## Settings (environment variables)

| Name | Default | Use |
| --- | --- | --- |
| ADMIN_PASSWORD | admin123 | Password for /admin. Change it before going online. |
| SECRET_KEY | dev-only-change-me | Signs login sessions. Set a long random value online. |
| DATABASE | unjobless.db next to app.py | Path of the SQLite file. |

Example (Windows PowerShell):

    $env:ADMIN_PASSWORD="my-strong-password"; $env:SECRET_KEY="a-long-random-string"; python app.py

## Put it online

    gunicorn app:app

Works on hosts like Render or Railway. Use a persistent disk or volume for the database file, and set the three variables above.
