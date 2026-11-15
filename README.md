# Cabin Security Management Backend

FastAPI + PostgreSQL backend for a multi-tenant Cabin Security and Access Control Management System.

The backend handles owner authentication, platform administration, visitor management, fingerprint enrollment, ESP32 device communication, access requests, door control and entry logs.

**Authentication note:** This implementation intentionally has no email verification, OTP, SMTP or email-confirmation workflow. Owner registration activates accounts immediately.

## Technology Stack

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- JWT Authentication
- Docker
- Docker Compose
- REST API

## System Architecture

```text
             React + Vite
                  |
                  v
             Nginx Proxy
                  |
                  v
            FastAPI Backend
                  |
          +-------+-------+
          |               |
          v               v
      PostgreSQL       ESP32 Device
                          |
                    Fingerprint Sensor
                          |
                      Door Relay
```

The backend supports multiple cabin owners through tenant-based data isolation.

## Requirements

- Python 3.12
- Docker Desktop
- Docker Engine
- Docker Compose
- Git

## Project Structure

```text
cabin-security-backend/
│
├── alembic/
├── app/
│   ├── api/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   └── main.py
│
├── tests/
├── .dockerignore
├── .env
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Configure the following security-sensitive values in `.env`:

| Variable | Description |
|---|---|
| `POSTGRES_PASSWORD` | PostgreSQL database password |
| `JWT_SECRET_KEY` | Secret used for JWT authentication |
| `DEVICE_API_KEY_PEPPER` | Pepper used for device API key hashing |
| `DATABASE_URL` | PostgreSQL connection URL |
| `ADMIN_EMAIL` | Platform administrator email, if configured |
| `ADMIN_PASSWORD` | Platform administrator password, if configured |

Use unique, strong secrets for all production deployments.

**Security:** Never commit `.env` to GitHub. Keep `.env.example` free from actual credentials.

## Run With Docker Compose

Docker Compose is the recommended method for running the backend and database.

### Step 1: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and configure the required credentials.

### Step 2: Build and Start Containers

```bash
docker compose up --build -d
```

### Step 3: Check Container Status

```bash
docker compose ps
```

### Step 4: View Backend Logs

```bash
docker compose logs -f api
```

### Step 5: Access API Documentation

Swagger UI:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

Health endpoint:

```text
http://localhost:8000/api/health
```

Database health:

```text
http://localhost:8000/api/health/database
```

## Platform Administrator Setup

Create the initial platform administrator from inside the API container:

```bash
docker compose exec api sh -c 'ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD="Use-A-Strong-Password" python -m app.utils.create_admin'
```

Replace the example credentials with your own strong administrator credentials.

The administrator can access the platform administration interface.

## Owner Registration

Endpoint:

```http
POST /api/auth/register
```

Required fields:

| Field | Description |
|---|---|
| `full_name` | Owner full name |
| `email` | Owner email address |
| `password` | Owner password |
| `phone` | Contact number |
| `cabin_name` | Cabin name |
| `cabin_location` | Cabin location |

The registration process:

1. Creates a new tenant.
2. Creates an active cabin owner.
3. Seeds the default Student, Teacher, Employee and Guest roles.
4. Generates access and refresh tokens.
5. Returns authentication tokens immediately.

No email verification or OTP is required.

## Device Registration and Authentication

Devices are registered through the owner-authenticated endpoint:

```http
POST /api/devices
```

Example request:

```json
{
  "name": "Cabin Security ESP32"
}
```

The backend returns a `device_api_key`.

**Important:** Copy and securely store the device API key immediately. It is stored in the database only as a peppered SHA-256 digest.

Send the device key in the following HTTP header:

```http
X-Device-Key: YOUR_DEVICE_API_KEY
```

Device authentication is independent of owner JWT authentication.

### Device Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/device/heartbeat` | Update device heartbeat |
| GET | `/api/device/config` | Fetch device configuration |
| GET | `/api/device/commands` | Fetch pending commands |
| POST | `/api/device/commands/{command_id}/ack` | Acknowledge commands |
| POST | `/api/device/authenticate` | Submit authentication event |
| POST | `/api/device/fingerprints/result` | Report enrollment result |

## Fingerprint Enrollment

The fingerprint enrollment workflow uses the ESP32 and fingerprint sensor.

1. Owner registers a visitor.
2. Owner initiates fingerprint enrollment.
3. Backend queues an enrollment command.
4. ESP32 retrieves the pending command.
5. Fingerprint sensor performs enrollment.
6. Device sends the enrollment result to the backend.
7. Backend stores the sensor template ID and associated metadata.

Fingerprint images and biometric templates are not stored in PostgreSQL. Only sensor template IDs and metadata are stored.

## Access Control and Door Management

The backend supports access request management and door control.

### Access Approval

When an owner approves an access request:

1. Backend updates the access request.
2. Backend queues an `unlock_door` command.
3. ESP32 retrieves the command.
4. ESP32 controls the physical relay.

### Access Denial

When an owner denies an access request, the backend queues a device message.

### Return Duration

Selecting a return duration queues a display-only command. It does not approve access or unlock the door.

## API Endpoint Inventory

All API routes are prefixed with `/api`.

### Authentication

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Register owner and tenant |
| POST | `/api/auth/login` | Owner login |
| POST | `/api/auth/refresh` | Rotate refresh token |
| POST | `/api/auth/logout` | Revoke refresh token |
| GET | `/api/auth/me` | Current owner profile |

### Platform Administration

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/admin/login` | Admin login |
| GET | `/api/admin/owners` | List cabin owners |
| PATCH | `/api/admin/owners/{owner_id}/status` | Activate/deactivate owner |
| GET | `/api/admin/stats` | Platform statistics |

### Visitor Management

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/visitors` | Register visitor and issue one-time PIN |
| GET | `/api/visitors` | Search/list visitors |
| GET | `/api/visitors/{visitor_id}` | Visitor details |
| PATCH | `/api/visitors/{visitor_id}` | Update visitor |
| POST | `/api/visitors/{visitor_id}/reset-pin` | Issue new PIN |

### Visitor Roles

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/visitor-roles` | Create role |
| GET | `/api/visitor-roles` | List roles |
| PATCH | `/api/visitor-roles/{role_id}` | Rename role |
| DELETE | `/api/visitor-roles/{role_id}` | Deactivate role |

### Fingerprint Management

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/fingerprints/enroll` | Queue fingerprint enrollment |
| GET | `/api/fingerprints` | List fingerprint mappings |
| DELETE | `/api/fingerprints/{visitor_id}` | Queue sensor deletion and remove mapping |
| POST | `/api/device/fingerprints/result` | Device reports enrollment result |

### Access Requests

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/access-requests` | List owner requests |
| POST | `/api/access-requests/{request_id}/approve` | Approve and queue unlock |
| POST | `/api/access-requests/{request_id}/deny` | Deny and queue device message |
| POST | `/api/access-requests/display-duration` | Queue return-duration display |

### Device Management

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/devices` | Register device |
| GET | `/api/devices` | List tenant devices |
| PATCH | `/api/devices/{device_id}/status` | Activate/deactivate device |

### Device Communication

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/device/heartbeat` | Device heartbeat |
| GET | `/api/device/config` | Device configuration |
| GET | `/api/device/commands` | Retrieve pending/retryable commands |
| POST | `/api/device/commands/{command_id}/ack` | Acknowledge command |
| POST | `/api/device/authenticate` | Submit authentication event |

### Door Management

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/door/unlock` | Owner-initiated unlock command |

### Logs and Dashboard

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/entry-logs` | Filtered entry history |
| GET | `/api/dashboard/stats` | Tenant dashboard metrics |

### Health Monitoring

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | API health |
| GET | `/api/health/database` | Database health |

## Database Relationships

The application uses PostgreSQL with tenant-based data separation.

- `tenants` has one cabin owner and multiple tenant-owned records.
- `visitors` belongs to a tenant and a visitor role.
- `devices` belongs to a tenant.
- `access_requests` belongs to a tenant and can reference a visitor and device.
- `device_commands` belongs to a tenant and device.
- `refresh_tokens` belongs to a cabin owner.
- `platform_admins` are global identities and are not tenant-owned.

### Security and Data Isolation

- Tenant-owned queries include the authenticated owner's `tenant_id`.
- Clients cannot select or override their tenant ID.
- Device authentication is independent of owner JWT authentication.
- Refresh tokens are stored as SHA-256 digests.
- Device API keys are stored as peppered SHA-256 digests.

## Device Command Management

The backend uses a command queue for device communication.

- Devices poll for pending commands.
- Commands can expire.
- Commands are acknowledged idempotently.
- Unacknowledged deliveries become eligible for retry after 10 seconds.

## Database Migrations

The project uses Alembic for database schema management.

Apply migrations:

```bash
docker compose exec api alembic upgrade head
```

Generate a new migration:

```bash
docker compose exec api alembic revision --autogenerate -m "describe change"
```

Review the generated migration before applying it.

Apply the migration:

```bash
docker compose exec api alembic upgrade head
```

## Local Development Without Docker

### Step 1: Create Virtual Environment

```bash
python -m venv .venv
```

Activate on Windows:

```powershell
.venv\Scripts\activate
```

Activate on Linux/macOS:

```bash
source .venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Database

Configure `DATABASE_URL` in `.env` to point to your PostgreSQL database.

### Step 4: Apply Migrations

```bash
alembic upgrade head
```

### Step 5: Start FastAPI

```bash
uvicorn app.main:app --reload
```

Access the API:

```text
http://localhost:8000/docs
```

## Docker Management Commands

Start containers:

```bash
docker compose up -d
```

Rebuild and start:

```bash
docker compose up --build -d
```

Stop containers:

```bash
docker compose down
```

View logs:

```bash
docker compose logs -f
```

Restart API:

```bash
docker compose restart api
```

Check running containers:

```bash
docker compose ps
```

## Frontend Integration

The frontend communicates with this backend through Nginx.

Frontend:

```text
http://localhost:5173
```

Backend:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

The frontend Nginx configuration uses:

```text
http://host.docker.internal:8000
```

Ensure that the backend API port is published on the Docker host.

## Troubleshooting

### Backend Not Starting

```bash
docker compose logs -f api
```

### Database Connection Error

Check PostgreSQL status:

```bash
docker compose ps
```

Check database logs:

```bash
docker compose logs db
```

### API Not Accessible

Check:

```text
http://localhost:8000/docs
```

Verify that the API container is running and port 8000 is published.

### Frontend Shows 502 Bad Gateway

Check backend availability and the frontend Nginx upstream configuration.

### Migration Errors

```bash
docker compose exec api alembic upgrade head
```

## Security Considerations

This project is a strong development baseline, not a certified security product.

Before production deployment, consider:

- Rate limiting.
- Audit hardening.
- TLS termination.
- Secret rotation.
- Command-delivery leasing and retry semantics.
- Hardware-in-the-loop testing.
- Secure device provisioning.

## License

Add your project's chosen license before public distribution.
