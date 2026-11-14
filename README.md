# Cabin Security Management Backend

FastAPI + PostgreSQL backend for a multi-tenant cabin access-control system. The implementation intentionally has **no email verification, OTP, SMTP, or email-confirmation workflow**. Owner registration activates the account immediately.

## Run with Docker

1. Copy `.env.example` to `.env`.
2. Set unique strong values for `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, and `DEVICE_API_KEY_PEPPER`. Keep `.env` private.
3. Start: `docker compose up --build -d`.
4. Open Swagger: http://localhost:8000/docs.
5. Create the platform admin from inside the API container: `docker compose exec api sh -c 'ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD="Use-A-Strong-Password" python -m app.utils.create_admin'`.

## Owner registration

`POST /api/auth/register` accepts `full_name`, `email`, `password`, `phone`, `cabin_name`, and `cabin_location`. It creates an active tenant and owner, seeds Student/Teacher/Employee/Guest roles, and returns access and refresh tokens immediately. No email confirmation is sent or required.

## Device setup

Register a device from the owner-authenticated `POST /api/devices` endpoint. Copy the returned `device_api_key` immediately. Send it as the `X-Device-Key` header on device endpoints. The key is stored only as a peppered SHA-256 digest.

Device endpoints: `POST /api/device/heartbeat`, `GET /api/device/config`, `GET /api/device/commands`, `POST /api/device/commands/{command_id}/ack`, and `POST /api/device/authenticate`.

## Important implementation notes

- Tenant-owned queries always include the authenticated owner's `tenant_id`; clients cannot choose their tenant.
- Device authentication is independent from owner JWT authentication.
- Fingerprint images/templates are not stored in PostgreSQL; only sensor template IDs and metadata are stored.
- The device enrollment flow queues a command; the device reports its enrollment result through `/api/device/fingerprints/result`.
- Selecting a return duration queues a display-only command. It does not approve access.
- Access approval queues an `unlock_door` command; the ESP32 controls the physical relay.
- This is a strong development baseline, not a certified security product. Before production deployment, add rate limiting, audit hardening, TLS termination, secret rotation, command-delivery leasing/retry semantics, and hardware-in-the-loop tests.

## Local development

Create a Python 3.12 virtual environment, install `requirements.txt`, configure `DATABASE_URL`, then run `alembic upgrade head` and `uvicorn app.main:app --reload`.

## API endpoint inventory

All routes are prefixed with `/api`.

| Router | Endpoint | Purpose |
|---|---|---|
| Auth | `POST /auth/register` | Create active owner + tenant; return tokens |
| Auth | `POST /auth/login` | Owner login |
| Auth | `POST /auth/refresh` | Rotate refresh token |
| Auth | `POST /auth/logout` | Revoke refresh token |
| Auth | `GET /auth/me` | Current owner profile |
| Admin | `POST /admin/login` | Platform admin login |
| Admin | `GET /admin/owners` | List cabin owners |
| Admin | `PATCH /admin/owners/{owner_id}/status` | Activate/deactivate owner |
| Admin | `GET /admin/stats` | Platform statistics |
| Visitors | `POST /visitors` | Register visitor and issue one-time PIN |
| Visitors | `GET /visitors` | Search/list tenant visitors |
| Visitors | `GET /visitors/{visitor_id}` | Visitor detail |
| Visitors | `PATCH /visitors/{visitor_id}` | Update visitor |
| Visitors | `POST /visitors/{visitor_id}/reset-pin` | Issue new one-time PIN |
| Roles | `POST /visitor-roles` | Create role |
| Roles | `GET /visitor-roles` | List roles |
| Roles | `PATCH /visitor-roles/{role_id}` | Rename role |
| Roles | `DELETE /visitor-roles/{role_id}` | Deactivate role |
| Fingerprints | `POST /fingerprints/enroll` | Queue device enrollment |
| Fingerprints | `GET /fingerprints` | List mappings |
| Fingerprints | `DELETE /fingerprints/{visitor_id}` | Queue sensor deletion and remove mapping |
| Fingerprints/device | `POST /device/fingerprints/result` | Device reports enrollment result |
| Access | `GET /access-requests` | List owner requests |
| Access | `POST /access-requests/{request_id}/approve` | Approve and queue unlock |
| Access | `POST /access-requests/{request_id}/deny` | Deny and queue device message |
| Access | `POST /access-requests/display-duration` | Queue return-after display message |
| Devices | `POST /devices` | Register device; return API key once |
| Devices | `GET /devices` | List tenant devices |
| Devices | `PATCH /devices/{device_id}/status` | Activate/deactivate device |
| Device | `POST /device/heartbeat` | Update online heartbeat |
| Device | `GET /device/config` | Fetch device configuration |
| Device | `GET /device/commands` | Poll pending/retryable commands |
| Device | `POST /device/commands/{command_id}/ack` | Acknowledge command |
| Device | `POST /device/authenticate` | Submit PIN/fingerprint authentication event |
| Door | `POST /door/unlock` | Owner-initiated unlock command |
| Logs | `GET /entry-logs` | Filtered entry history |
| Dashboard | `GET /dashboard/stats` | Tenant dashboard metrics |
| Health | `GET /health` | API health |
| Health | `GET /health/database` | Database health |

## Database relationships

- `tenants` has one `cabin_owners` record and many tenant-owned visitors, roles, devices, commands, requests, logs, and fingerprint mappings.
- `visitors` belongs to one `tenant` and one `visitor_role`; it has one PIN credential and at most one fingerprint mapping.
- `devices` belongs to one tenant and has many commands, fingerprint mappings, access requests, and entry logs.
- `access_requests` belongs to a tenant and optionally references a visitor and device.
- `device_commands` belongs to a tenant and device. Commands expire and are acknowledged idempotently; unacknowledged deliveries are eligible for retry after 10 seconds.
- `refresh_tokens` belongs to a cabin owner and stores only a SHA-256 token digest, not the raw token.
- `platform_admins` are global identities and are not tenant-owned.

## Migrations

The initial migration creates the schema from the SQLAlchemy metadata. For subsequent schema changes, create a revision with `alembic revision --autogenerate -m "describe change"`, inspect the generated migration, then apply it using `alembic upgrade head`.
