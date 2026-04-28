# acrylic-backend

Django + Django REST Framework · JWT Auth · SQLite (dev) · AWS S3 (planned) · SignWell E-Signature

---

## Prerequisites

- Python 3.10+
- pip
- Git

---

## First-Time Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd <project-folder>

# 2. Create and activate a virtual environment
python -m venv ../venv
source ../venv/bin/activate       # macOS/Linux
# ../venv/Scripts/activate        # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Create an admin superuser (you'll be prompted for username/email/password)
python manage.py createsuperuser

# 6. Load fixture data (genres, moods, instruments, songs)
python manage.py loaddata initial_data

# 7. Start the dev server
python manage.py runserver
```

---

## Environment Variables

Create a `.env` file in the project root:

```
SIGNWELL_API_KEY=your-key-here
SIGNWELL_TEST_MODE=True
SIGNWELL_WEBHOOK_SECRET=any-local-secret
SIGNWELL_RIGHTSHOLDER_TEMPLATE_ID=mock
SIGNWELL_BUYER_TEMPLATE_ID=mock
CURRENT_CONTRACT_VERSION=v1.0
FRONTEND_URL=http://localhost:3000
```

> `SIGNWELL_TEST_MODE=True` bypasses the real SignWell API and enables the mock signing endpoint for local development.

---

## Running the Server

```bash
source ../venv/bin/activate   # if not already active
python manage.py runserver
```

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:8000/api/` | API base URL |
| `http://127.0.0.1:8000/admin/` | Django admin panel |

---

## Admin Panel

1. Go to `http://127.0.0.1:8000/admin/`
2. Log in with the superuser credentials you created above

From the admin panel you can:

- **Approve songs** — set `status` to `approved` directly from the song list view
- **Manage users** — view accounts and change roles (`client`, `artist`, `admin`)
- **Edit metadata** — add or remove genres, mood tags, and instruments
- **View/edit/delete songs** — full CRUD on the song catalog
- **Manage contracts** — view signing status, create contracts manually for dev/testing without going through SignWell

---

## API Quick Reference

### Auth

```
POST /api/users/register/
Body: { "username": "", "email": "", "password": "", "role": "client" }

POST /api/users/login/
Body: { "username": "", "password": "" }
Returns: access token, refresh token, role
```

### Songs

```
GET   /api/songs/                  Browse public catalog (no auth required)
GET   /api/songs/<id>/             Single song detail (no auth required)
POST  /api/songs/upload/           Upload a song (JWT + rightsholder contract)
POST  /api/songs/<id>/play/        Increment play count (JWT + buyer contract)
PATCH /api/songs/<id>/edit/        Edit a draft or rejected song (JWT + rightsholder contract + ownership)
POST  /api/songs/<id>/archive/     Archive a song — soft delete (JWT + rightsholder contract + ownership)
POST  /api/songs/<id>/restore/     Restore archived song to draft (JWT + rightsholder contract + ownership)

GET   /api/songs/genres/           List all genres
GET   /api/songs/moods/            List all mood tags
GET   /api/songs/instruments/      List all instruments
```

### Contracts

```
POST /api/contracts/initiate/      Create a SignWell document, returns signing URL (JWT required)
POST /api/contracts/webhook/       Receive SignWell events — verified via HMAC (no auth)
GET  /api/contracts/mock-sign/     Simulate signing in dev only (SIGNWELL_TEST_MODE=True required)
```

### Filtering & Sorting

Append query params to `GET /api/songs/`:

```
?genre=jazz
?mood=chill
?instrument=piano
?min_bpm=100&max_bpm=140
?sort_by=play_count       # also: bpm, -bpm, duration, -duration, uploaded_at, -uploaded_at, -play_count
```

---

## Song Status Lifecycle

Songs move through statuses as follows:

```
upload → draft → pending_review → approved
                               → rejected → (edit) → pending_review
any status → archived → (restore) → draft
```

- **draft** — editable, not visible in catalog
- **pending_review** — locked, under admin review
- **approved** — locked, visible in catalog
- **rejected** — editable, not visible in catalog
- **archived** — locked, soft-deleted, hidden from catalog

> Songs are only editable in `draft` or `rejected` status. To update an approved track, archive it and re-upload.

---

## Permissions

Protected endpoints stack three permission checks in order:

1. **`IsAuthenticated`** — JWT must be present and valid
2. **`HasSignedContract`** — user must have a signed, non-expired, current-version contract (`rightsholder` for artists, `buyer` for clients)
3. **`IsTrackOwner`** — user must be the song's artist (object-level, edit/archive/restore only)

To test a gated endpoint locally, create a contract manually in the admin panel with `status=signed`, `contract_type=rightsholder`, `version=v1.0`, and an expiry date in the future.

---

## Testing with Postman

Since the React frontend isn't built yet, use Postman for all endpoint testing.

1. **Register** — `POST /api/users/register/` with a JSON body
2. **Login** — `POST /api/users/login/` and copy the `access` token from the response
3. **Authenticated requests** — Authorization tab → Bearer Token → paste access token
4. **Upload a song** — use `form-data` body; include `full_track` and `preview_clip` as file fields
5. **Edit a song** — use `PATCH` with a JSON body; only `draft` or `rejected` songs can be edited

---

## Running Tests

```bash
python manage.py test songs           # songs app
python manage.py test users           # users app
python manage.py test contracts       # contracts app
python manage.py test                 # all tests
python manage.py test songs -v 2      # verbose output
```

---

## Project Structure

```
config/          Project settings and root URL routing
users/           Auth app — registration, login, user roles, profiles
songs/           Song catalog — models, upload, browsing, metadata, catalog management
contracts/       E-signature — SignWell integration, contract model, permissions
media/           Local file storage for audio (gitignored)
manage.py        Django CLI entry point
requirements.txt Python dependencies
```

---

## Notes

- **`.env` and `db.sqlite3` are gitignored** — do not commit them
- **`media/` is gitignored** — uploaded files stay local; clear orphaned files with `rm -rf media/songs/`
- JWT access tokens are short-lived; refresh tokens are used to silently renew them
- `os.getenv()` always returns strings — booleans in `.env` must be compared explicitly (e.g. `os.getenv('SIGNWELL_TEST_MODE') == 'True'`)
- App-level `urls.py` files do not include their own prefix — prefixes are set once in `config/urls.py`
- AWS S3, React frontend, Stripe payments, licensing system, and Celery tasks are all deferred to future sprints