# acrylic-backend

Django + Django REST Framework · JWT Auth · SQLite (dev) · AWS S3 (planned)

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

# 6. Load fixture data (3 genres, 3 moods, 3 instruments, 3 approved songs)
python manage.py loaddata initial_data

# 7. Start the dev server
python manage.py runserver
```

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

- **Approve songs** — toggle `is_approved` directly from the song list view
- **Manage users** — view accounts and change roles (`client`, `artist`, `admin`)
- **Edit metadata** — add or remove genres, mood tags, and instruments
- **View/edit/delete songs** — full CRUD on the song catalog

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
GET  /api/songs/                  Browse public catalog (no auth)
GET  /api/songs/<id>/             Single song detail (no auth)
POST /api/songs/upload/           Upload a song (JWT required)
POST /api/songs/<id>/play/        Increment play count (no auth)

GET  /api/songs/genres/           List all genres
GET  /api/songs/moods/            List all mood tags
GET  /api/songs/instruments/      List all instruments
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

## Testing with Postman

Since the React frontend isn't built yet, use Postman for all endpoint testing.

1. **Register** — `POST /api/users/register/` with a JSON body
2. **Login** — `POST /api/users/login/` and copy the `access` token from the response
3. **Authenticated requests** — add header `Authorization: Bearer <access_token>`
4. **Upload a song** — use `form-data` body in Postman; include `full_track` and `preview_clip` as file fields

---

## Project Structure

```
config/          Project settings and root URL routing
users/           Auth app — registration, login, user roles
songs/           Song catalog — models, upload, browsing, metadata
media/           Local file storage for audio (gitignored)
manage.py        Django CLI entry point
requirements.txt Python dependencies
```

---

## Notes

- **`.env` and `db.sqlite3` are gitignored** — do not commit them
- **`media/` is gitignored** — uploaded files stay local only
- The `is_approved` flag on a song must be toggled to `True` (via admin) before it appears in the public catalog
- JWT access tokens are short-lived; refresh tokens are used to silently renew them
- AWS S3, the Angular/React frontend, licensing system, and automated tests are all deferred to future sprints