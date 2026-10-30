# Cabin Security Management — FastAPI Backend

Backend API paired with the supplied React/Vite frontend. The implementation is fingerprint-only and uses an ESP32 polling command queue for door and OLED actions.

## 1. Architecture

```text
React / Vite
    │  Bearer JWT over HTTP
    ▼
FastAPI (/api/v1)
    ├── Central PostgreSQL database
    │     ├── Owner accounts and password hashes
    │     ├── Owner → tenant database mapping
    │     └── ESP32 device IDs and hashed device API keys
    │
    └── One PostgreSQL database per cabin owner
          ├── Visitors
          ├── R307 fingerprint-slot mapping
          ├── Access requests
          ├── Previous entries
          ├── Fingerprint enrollment jobs
          └── ESP32 command queue

ESP32 ── polls authenticated commands ──► FastAPI
ESP32 ── fingerprint event / command ack ──► FastAPI
ESP32 ── drives R307, relay, OLED and door hardware
```

Each owner is assigned a separate PostgreSQL database named `cabin_owner_<uuid>`. The central database stores only account/tenant routing data and device credentials. The backend chooses the tenant database from the authenticated owner record; the browser cannot submit a tenant database name or switch tenants.

The R307 sensor retains fingerprint templates. PostgreSQL stores only the R307 sensor slot number and its mapping to the visitor. Fingerprint images/templates are not uploaded to the backend.

## 2. Requirements

- Python 3.11 or newer (3.12/3.13 recommended)
- Docker Desktop with WSL2 on Windows, or a local PostgreSQL 16 server
- Node.js 18+ for the React frontend

## 3. Start PostgreSQL

From this backend folder:

```bash
docker compose up -d postgres
docker compose ps
```

Wait until `cabin-security-postgres` shows `healthy`.

The included Compose file creates the local development PostgreSQL service. It uses the development-only `postgres/postgres` credentials. Do not use these credentials in production. If port 5432 is already occupied on your laptop, change the Compose mapping (for example `5433:5432`) and update the three database URLs in `.env` to port 5433.

## 4. Create and activate a Python environment (Windows PowerShell)

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell blocks environment activation, run this once in the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

On Git Bash:

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## 5. Configure `.env`

The example file points to the included PostgreSQL Compose service. Generate two independent strong secrets (run the command twice):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste one value into `JWT_SECRET_KEY` and the other into `TENANT_PASSWORD_SECRET` in `.env`. Keep both values stable and private; never commit `.env`. Back up `TENANT_PASSWORD_SECRET` because the backend derives each tenant's PostgreSQL login password from it.

Important settings:

- `CONTROL_DATABASE_URL`: central owner and device credential database. The database `cabin_control` must exist; the included Compose service creates it.
- `TENANT_DATABASE_URL`: base host/port connection URL. The backend replaces its database name, username and password with owner-specific values when opening a tenant database.
- `TENANT_PASSWORD_SECRET`: stable secret used to derive a separate database password for each tenant role. Keep it stable and backed up; changing it without rotating every tenant role will disconnect the application from tenant databases.
- `PROVISION_DATABASE_URL`: PostgreSQL connection used to create/drop tenant roles and databases. The configured user must have `CREATEROLE` and `CREATEDB` privileges.
- `ALLOW_OWNER_REGISTRATION`: enables public `POST /api/v1/auth/register`. It defaults to `false` because the current React login page does not include a signup form. Use the CLI to create owners; only enable public registration when the frontend signup flow is available and the endpoint is protected by rate limiting/invitation controls.
- `CORS_ORIGINS`: comma-separated frontend origins. The development configuration also allows private LAN IPv4 origins on port 5173 for phone testing.

For production, use a restricted control-database role and a separate provisioner role with `CREATEDB` and `CREATEROLE`; do not run the API as PostgreSQL superuser. Tenant queries connect with a tenant-specific PostgreSQL role that owns only that tenant's database. The provisioner credential is used only during owner provisioning/deprovisioning and should be isolated further in a dedicated provisioning service for a hardened production deployment.

## 6. Create the first Cabin Owner

The current React ZIP contains a login screen but no owner signup screen. Create the first owner from the backend CLI:

```bash
python -m app.scripts.create_owner
```

Enter the owner's name, username, email, phone, department and password. This command:

1. Creates a unique owner record in the central database.
2. Creates a dedicated PostgreSQL login role and isolated database for that owner.
3. Creates tenant tables using that owner's database role; another tenant's database role has no database access.
4. Creates one ESP32 device credential.
5. Prints the device ID and device API key once.

Save the printed `ESP32 Device ID` and `ESP32 Device API key`. Configure these values in the ESP32 firmware. The backend stores only the API-key hash.

Alternatively, owner self-registration can be enabled through `ALLOW_OWNER_REGISTRATION=true` and `POST /api/v1/auth/register`. It returns the device key once, so the client must securely display/store it. Do not enable public registration on an exposed deployment without rate limiting and abuse protection.

## 7. Run the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

To use the backend from the React frontend, edit the frontend `.env`:

```env
VITE_USE_MOCK=false
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Restart Vite after changing `.env`:

```bash
npm run dev
```

### Phone testing on the same Wi-Fi

Use your laptop's IPv4 address in the frontend `.env`, not `localhost`, because `localhost` on the phone means the phone itself. For example:

```env
VITE_API_BASE_URL=http://10.170.197.254:8000/api/v1
```

Run both servers bound to `0.0.0.0`, connect phone and laptop to the same Wi-Fi, and allow TCP ports 5173 and 8000 through Windows Firewall for the private network. The laptop IP may change after reconnecting to Wi-Fi.

## 8. API contract used by this frontend

All owner endpoints below require `Authorization: Bearer <access_token>`.

| Method | Path | Body / query | Purpose |
|---|---|---|---|
| POST | `/auth/login` | `{ "username": "...", "password": "..." }` | Login; returns `access_token` |
| GET | `/auth/me` | — | Current Cabin Owner |
| POST | `/auth/register` | Owner profile and password | Provision owner and isolated database |
| GET | `/visitors` | `search, department, role, page, pageSize` | Filtered visitor list |
| POST | `/visitors` | `name, phone, department, role` | Create visitor |
| GET | `/visitors/{id}` | — | Visitor details |
| PUT | `/visitors/{id}` | Any visitor fields | Update visitor |
| DELETE | `/visitors/{id}` | — | Delete visitor; queues R307 template deletion |
| POST | `/visitors/{id}/fingerprints` | — | Queue R307 enrollment job; returns `202` and `enrollment_id` |
| GET | `/fingerprint-enrollments/{id}` | — | Poll enrollment completion |
| GET | `/access-requests` | — | Latest access requests |
| POST | `/access-requests/decision` | `{ "ids": [12], "decision": "allowed" }` | Bulk Allow or Deny; no duration needed |
| POST | `/access-requests/{id}/delay` | `{ "duration_minutes": 5 }` | Queue OLED message; door remains locked |
| GET | `/entries` | `search, department, role, result, page, pageSize` | Previous Entries page |

`pageSize` uses the camelCase query parameter because that is what the current React service sends. Other payload and response fields use `snake_case`.

## 9. Access decision behavior

- **Allow:** set the request status to `allowed` and queue `UNLOCK_DOOR` for the ESP32. The command includes a 3000 ms relay pulse suggestion. The ESP32 firmware must apply its local safety checks before energizing the relay.
- **Deny:** set the request status to `denied` and queue `KEEP_LOCKED`. No unlock command is created.
- **Select Duration:** clicking a visitor ID in Home targets that one request. Choosing 5, 10 or 30 minutes calls the delay endpoint immediately. It sets the request to `delayed` and queues `DISPLAY_MESSAGE` with `keep_locked: true` and `unlock: false`. This action never unlocks the door and does not schedule a future automatic unlock.

Previous Entries are written when the ESP32 acknowledges the requested hardware action. A delayed visit is recorded as a denied attempt for that visit. If the ESP32 reports a failed command, the request becomes `failed` and the entry is recorded as denied.

## 10. ESP32 device protocol

Every device request must include:

```http
X-Device-ID: <device_id>
X-Device-Key: <one-time-issued-device-api-key>
Content-Type: application/json
```

Recommended device loop:

1. Send `POST /api/v1/device/heartbeat` periodically with firmware version and local IP.
2. Poll `GET /api/v1/device/commands/next` approximately once per second.
3. If the result is `null`, continue polling.
4. Execute the command locally on ESP32 (R307, relay, OLED, buzzer/LED if configured).
5. Send `POST /api/v1/device/commands/{command_id}/ack` with `status: "succeeded"` or `"failed"` and the result.
6. After R307 identifies a stored fingerprint slot, send `POST /api/v1/device/fingerprint-events` with `{ "sensor_slot": 12 }`. The server creates a pending owner approval request.

Example command response:

```json
{
  "command_id": "b53f5d0c-0a15-4f5f-bf94-e4c5a201f3a1",
  "command_type": "DISPLAY_MESSAGE",
  "payload": {
    "duration_minutes": 5,
    "message": "Come back later after 5 minutes",
    "oled_lines": ["Come back later", "after 5 minutes"],
    "keep_locked": true,
    "unlock": false
  },
  "created_at": "2026-01-01T10:00:00Z"
}
```

Acknowledgement example for fingerprint enrollment:

```json
{
  "status": "succeeded",
  "result": { "sensor_slot": 12 }
}
```

The firmware must implement these command types:

- `ENROLL_FINGERPRINT`: capture/enroll a new finger on R307 and acknowledge the assigned sensor slot.
- `DELETE_FINGERPRINT`: delete the specified R307 sensor slot.
- `UNLOCK_DOOR`: pulse the relay only after the server has approved the request.
- `KEEP_LOCKED`: ensure the relay is not energized.
- `DISPLAY_MESSAGE`: keep the door locked and render the provided `oled_lines` / message.

Commands are leased for `DEVICE_COMMAND_LEASE_SECONDS`; if an acknowledgement is lost, an unacknowledged command is offered again after the lease expires. The firmware should make command execution idempotent using `command_id`, particularly for relay pulses and fingerprint deletion.

## 11. Important deployment/security notes

- This backend is a development-ready integration baseline, not a certified physical access-control product. Test with the relay disconnected before testing a real lock.
- Keep a physical exit path and manual override. Backend/network failure must never prevent safe egress.
- Device API keys must be kept out of source control and serial logs. A production deployment should add a device-key rotation workflow and TLS.
- Restrict CORS to the actual deployed frontend origin in production; disable `ALLOW_PRIVATE_LAN_ORIGINS`.
- The included schema initialization uses SQLAlchemy `create_all` to make local setup straightforward. Use Alembic migrations before production upgrades.
- Use HTTPS, strong database roles/passwords, backups, monitoring, rate limits on public owner registration, and a tested recovery procedure before deployment.

## Project structure

```text
cabin-security-backend/
├── app/
│   ├── api/routes/       # Auth, visitors, access, entries, ESP32 endpoints
│   ├── core/             # Settings and cryptographic helpers
│   ├── db/               # Central DB and dynamic tenant DB sessions
│   ├── models/           # Central and tenant SQLAlchemy models
│   ├── schemas/          # Request/response validation
│   ├── services/         # Provisioning, command queue, access decisions
│   └── scripts/          # First owner bootstrap CLI
├── tests/
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```
