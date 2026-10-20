# System Architecture

## Layers

1. **Presentation layer**
   - `ui.py`
   - Tkinter administrator dashboard, forms, tables and reports.

2. **Application services**
   - `face_engine.py`
   - `reports.py`
   - `alerts.py`
   - `backup.py`

3. **Security services**
   - `security.py`
   - PBKDF2-HMAC-SHA256 password hashing with random salts.

4. **Persistence layer**
   - `database.py`
   - SQLite with foreign keys, WAL mode, indexes and transaction handling.

5. **Storage**
   - Registered face samples
   - Unknown-person captures
   - Trained LBPH model
   - CSV reports and database backups

## Main workflows

### Registration

Administrator login → create person → capture 30 normalized grayscale face
samples → save metadata → train LBPH model → audit event.

### Recognition

Load model → open available camera → detect face → normalize crop → LBPH
prediction → threshold decision → attendance or unknown event → optional email
alert → audit/report review.

## Database relationships

- `persons 1 ── * face_samples`
- `persons 1 ── * attendance`
- Unknown events are stored separately because an identity is not known.
- Administrator security events are stored in `audit_logs`.

## Production extensions

- Anti-spoofing/liveness model
- PostgreSQL and encrypted object storage
- REST API with role-based authorization
- Multi-camera workers
- Hardware access-control integration
- Central notification queue
- Docker deployment and automated tests
