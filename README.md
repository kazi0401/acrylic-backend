# acrylic-backend

Django + Django REST Framework · JWT Auth · SQLite (dev) · AWS S3 (planned) · SignWell E-Signature · Stripe (stubbed)

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

# 6. Load fixture data (genres, moods, instruments, songs, test users)
python manage.py loaddata initial_data

# 7. Start the dev server
python manage.py runserver
```

---

## Environment Variables (Optional)

Inside config/settings.py, environment variables default, but for later an env file is a good idea.
Create a `.env` file in the project root:

```
SIGNWELL_API_KEY=your-key-here
SIGNWELL_TEST_MODE=True
SIGNWELL_WEBHOOK_SECRET=any-local-secret
SIGNWELL_RIGHTSHOLDER_TEMPLATE_ID=mock
SIGNWELL_BUYER_TEMPLATE_ID=mock
CURRENT_CONTRACT_VERSION=v1.0
FRONTEND_URL=http://localhost:3000
STRIPE_TEST_MODE=True
STRIPE_SECRET_KEY=sk_test_dummy
```

> `SIGNWELL_TEST_MODE=True` bypasses the real SignWell API and enables the mock signing endpoint for local development.

> `STRIPE_TEST_MODE=True` bypasses real Stripe API calls. All payment and subscription operations return mocked responses. Real Stripe integration is deferred until API access is available.

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
- **Manage subscription tiers** — create, edit, activate/deactivate tiers without code changes
- **View buyer subscriptions** — view subscription history per client, Stripe fields are readonly
- **View license records** — all fields readonly except status (for manual revocation)

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

### License Requests

```
POST  /api/license-requests/               Submit a request for a song not in the catalog (JWT + buyer contract)
GET   /api/license-requests/               List your own submitted requests (JWT + buyer contract)
GET   /api/license-requests/<id>/          Retrieve a single request (JWT + buyer contract, must own request)
PATCH /api/license-requests/<id>/review/   Admin updates status and notes (JWT + admin role)
```

### Subscriptions

```
GET  /api/subscriptions/tiers/      List active subscription tiers (no auth required)
POST /api/subscriptions/subscribe/  Subscribe to a tier (JWT + buyer contract)
GET  /api/subscriptions/me/         View your active subscription (JWT + buyer contract)
POST /api/subscriptions/cancel/     Cancel your active subscription (JWT + buyer contract)
```

### Licenses

```
POST /api/licenses/preclear/        License a PreClear track — triggers Stripe charge (JWT + buyer contract)
POST /api/licenses/artist-promo/    License an Artist Promo track — requires active subscription (JWT + buyer contract)
GET  /api/licenses/my-licenses/     List all your licenses (JWT + buyer contract)
GET  /api/licenses/<id>/            Retrieve a single license (JWT + buyer contract, must own license)
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

## Track Tier System

Rightsholders assign a tier to each track on upload. The tier controls the licensing flow for buyers.

| Tier | Pricing | Licensing Flow |
|------|---------|----------------|
| `bid2clear` | Min bid (deferred) | Negotiation workflow — not yet implemented |
| `preclear` | Fixed price + 30% fee | Buyer pays directly via Stripe PaymentIntent |
| `artist_promo` | No fee | Subscription buyers only, no charge |

> `bid2clear` songs are visible in the catalog but cannot be licensed yet. The bidding workflow is deferred to a future sprint.

---

## Licensing Flows

### PreClear
1. Buyer POSTs to `/api/licenses/preclear/` with `song` and `usage_details`
2. System creates a Stripe PaymentIntent for `song.fixed_price`
3. Payment is confirmed — returns 402 if payment fails
4. License record created with `license_type=preclear` and `price_paid` snapshot

### Artist Promo
1. Buyer must have an active subscription (`POST /api/subscriptions/subscribe/`)
2. Buyer POSTs to `/api/licenses/artist-promo/` with `song` and `usage_details`
3. No charge. License record created linked to the active subscription.

---

## Permissions

Protected endpoints stack permission checks in order:

1. **`IsAuthenticated`** — JWT must be present and valid
2. **`HasSignedContract`** — user must have a signed, non-expired, current-version contract (`rightsholder` for artists, `buyer` for clients)
3. **`IsTrackOwner`** — user must be the song's artist (object-level, edit/archive/restore only)
4. **`IsAdmin`** — user must have `role=admin` (admin review endpoints only)
5. **`HasActiveSubscription`** — buyer must have an active `BuyerSubscription` (Artist Promo licenses only)

To test a gated endpoint locally, create a contract manually in the admin panel with `status=signed`, `contract_type=rightsholder` or `buyer`, `version=v1.0`, and an expiry date in the future.

---

## Testing with Postman

Since the React frontend isn't built yet, use Postman for all endpoint testing.

1. **Register** — `POST /api/users/register/` with a JSON body
2. **Login** — `POST /api/users/login/` and copy the `access` token from the response
3. **Authenticated requests** — Authorization tab → Bearer Token → paste access token
4. **Upload a song** — use `form-data` body; include `full_track` and `preview_clip` as file fields
5. **Edit a song** — use `PATCH` with a JSON body; only `draft` or `rejected` songs can be edited
6. **Subscribe** — `POST /api/subscriptions/subscribe/` with `{ "tier_id": 1 }` (requires signed buyer contract)
7. **License a PreClear track** — `POST /api/licenses/preclear/` with `{ "song": 1, "usage_details": "..." }`
8. **License an Artist Promo track** — `POST /api/licenses/artist-promo/` with `{ "song": 2, "usage_details": "..." }` (requires active subscription)

---

## Running Tests

```bash
python manage.py test songs           # songs app
python manage.py test users           # users app
python manage.py test contracts       # contracts app
python manage.py test license_requests # license requests app
python manage.py test subscriptions   # subscriptions app
python manage.py test licenses        # licenses app
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
license_requests/ License request app — buyer submissions for out-of-catalog songs, admin review queue
subscriptions/   Subscription app — tiers, buyer subscriptions, Stripe billing stubs
licenses/        License app — completed license records, PreClear and Artist Promo flows
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
- Signals auto-create `ClientProfile` and `ArtistProfile` on user registration — never call `ClientProfile.objects.create()` directly, use `user.client_profile` instead
- AWS S3, React frontend, real Stripe payments, Bid2Clear licensing, artist payouts, and Celery tasks are all deferred to future sprints