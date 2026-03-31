# Migration Guide: SQLite → Neon PostgreSQL SaaS

## Overview
This guide helps you migrate from the SQLite development version to the production Neon PostgreSQL multi-tenant SaaS platform.

## Key Changes

### 1. Database Layer
**Before**: SQLite (local file)
```python
DATABASE_URL = f"sqlite:///{data_path / 'app.db'}"
```

**After**: Neon PostgreSQL (cloud)
```python
DATABASE_URL = os.getenv('DATABASE_URL')  # From .env
```

### 2. Multi-Tenancy
**Before**: No business scoping
```python
workers = session.query(WorkerModel).all()  # Returns ALL workers
```

**After**: Business-scoped
```python
workers = session.query(WorkerModel).filter(
    WorkerModel.business_id == business_id
).all()  # Only returns workers for this business
```

### 3. Models
**Before**: WorkerModel without business_id
**After**: All models have `business_id` FK and relationships defined

```python
class WorkerModel(Base):
    business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)
    business = relationship("BusinessModel", back_populates="workers")
```

### 4. Shift Status Workflow
**Before**: No shift status concept
**After**: Shifts have status ("Open" or "Closed")

- **Open**: Workers can see and express interest
- **Closed**: Solver can use interested workers for scheduling

### 5. Role-Based Access Control
**Before**: No roles
**After**: Two roles with different permissions

| Action | Manager | Worker |
|--------|---------|--------|
| Add/Edit/Delete Workers | ✅ | ❌ |
| Create/Close Shifts | ✅ | ❌ |
| View Shifts | ✅ | ✅ |
| Express Interest | ❌ | ✅ |
| Run Solver | ✅ | ❌ |

## Migration Steps

### Step 1: Export Legacy Data (Optional)
If you have existing SQLite data you want to preserve:

```python
# Export workers
import sqlite3
conn = sqlite3.connect('data/app.db')
workers = conn.execute("SELECT * FROM workers").fetchall()
# Save to CSV or JSON for reference
```

### Step 2: Set Up Neon Database
1. Create account at [neon.tech](https://neon.tech)
2. Create new project
3. Copy connection string:
   ```
   postgresql://user:password@host/database?sslmode=require
   ```

### Step 3: Update Environment
```bash
# Copy template
cp .env.example .env

# Edit .env with your Neon connection string
nano .env
```

### Step 4: Install New Dependencies
```bash
pip install -r requirements.txt
```

Key new dependencies:
- `python-dotenv>=1.0.0` - Environment variable management
- `psycopg2-binary>=2.9.0` - PostgreSQL driver
- `SQLAlchemy>=2.0.0` - Updated ORM

### Step 5: Create Tables
```bash
python web_interface.py
# The app auto-creates tables on startup
```

Or manually:
```python
from web_interface import Base, engine
Base.metadata.create_all(bind=engine)
```

### Step 6: Test Connection
```bash
curl http://localhost:5000/api/stats
# Should return: {"total_workers": 0, "total_shifts": 0, ...}
```

## API Changes

### Register Business (NEW)
```bash
POST /api/register-business
{
  "business_name": "Your Company",
  "manager_name": "Manager Name"
}
```

### Shift Status Management (NEW)
```bash
# Close a shift (enable interest gathering)
PUT /api/shifts/1/status
{"status": "Closed"}

# Reopen a shift
PUT /api/shifts/1/status
{"status": "Open"}
```

### Shift Interest Flow (NEW)
```bash
# Worker expresses interest
POST /api/shifts/1/interest

# Manager sees all interests
GET /api/shift-interests

# Worker sees their interests
GET /api/shift-interests/me
```

### Solver with Interest Filtering (UPDATED)
```bash
# Only runs on CLOSED shifts
# Only considers INTERESTED workers
POST /api/schedule
{
  "top_k": 3,
  "weights": {...}
}
```

## Session Management

### Manager Session
```python
_set_session(
    business_id=1,
    business_name="Acme Hospital",
    user_role="Manager",
    user_id=1
)
```

### Worker Session
```python
_set_session(
    business_id=1,
    business_name="Acme Hospital",
    user_role="Worker",
    user_id=2,
    worker_id=5
)
```

## Access Control Helpers

### Check Business Access
```python
bid, err, code = _require_business()
if err:
    return err, code
```

### Check Manager Role
```python
ok, err_resp, err_code = _require_role("Manager")
if not ok:
    return err_resp, err_code
```

### Check Worker Session
```python
wid, err_resp, err_code = _require_worker()
if err_resp:
    return err_resp, err_code
```

## Testing Your Migration

### 1. Create Business
```bash
curl -X POST http://localhost:5000/api/register-business \
  -H "Content-Type: application/json" \
  -d '{"business_name": "Test Co"}'
```

### 2. Add Workers
```bash
curl -X POST http://localhost:5000/api/workers \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "seniority_level": 2, "hourly_rate": 25.0}'
```

### 3. Create Shift
```bash
curl -X POST http://localhost:5000/api/shifts \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-04-01",
    "start_time": "09:00",
    "end_time": "17:00",
    "workers_required": 2
  }'
```

### 4. Close Shift
```bash
curl -X PUT http://localhost:5000/api/shifts/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "Closed"}'
```

### 5. Run Solver
```bash
curl -X POST http://localhost:5000/api/schedule \
  -H "Content-Type: application/json" \
  -d '{"top_k": 3, "weights": {}}'
```

## Troubleshooting

### "psycopg2 not found"
```bash
pip install psycopg2-binary
```

### "DATABASE_URL not set"
```bash
# Create .env file
echo "DATABASE_URL=postgresql://..." > .env
source .env
python web_interface.py
```

### "SSL connection error"
Ensure your connection string includes:
```
?sslmode=require&channel_binding=require
```

### "Table already exists"
This is normal on PostgreSQL. SQLAlchemy skips creation if tables exist.

### "Access denied for user"
Check DATABASE_URL credentials in .env

## Rollback (If Needed)

To revert to SQLite development mode:
1. Remove or comment out `DATABASE_URL` in `.env`
2. Restart app - it will auto-fallback to SQLite
3. Data will be in `data/app.db`

## Performance Tips

### For PostgreSQL
- Add indices on frequently queried columns (done automatically)
- Use connection pooling (enabled in SQLAlchemy)
- Monitor query performance in Neon dashboard

### For Large Datasets
- Paginate API responses
- Use bulk operations for imports
- Consider read replicas for reporting

## Next Steps

1. ✅ Complete migration
2. Deploy to production (Gunicorn + Nginx)
3. Set up monitoring and logging
4. Configure backups
5. Enable SSL/TLS for web server
6. Implement audit logging for compliance

---

**Need Help?**
- Check error logs: `tail -f web_interface.log`
- Verify database: `psql $DATABASE_URL -c "\dt"`
- Test endpoints: Use `curl` or Postman
