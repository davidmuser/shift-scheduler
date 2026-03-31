# Shift Scheduler - Multi-Tenant SaaS Platform

A powerful, user-friendly shift scheduling platform powered by Google OR-Tools CP-SAT solver. Built with Flask, SQLAlchemy, and Neon PostgreSQL for enterprise-grade multi-tenancy.

## 🎯 Overview

This SaaS platform enables Managers to create optimal shift schedules by:
1. **Creating Workers** with skills, seniority, and availability
2. **Posting Shifts** that need to be filled
3. **Workers expressing interest** in shifts they can work
4. **Manager closing shifts** to gather all interests
5. **Running the AI Solver** to assign workers from the interested pool
6. **Getting multiple schedule options** ranked by optimization metrics

## 🏗️ Architecture

### Multi-Tenancy
- Every Worker, Shift, and Interest record has a `business_id`
- Data isolation enforced at the database layer
- Each business operates independently with its own data

### Roles
- **Manager**: Can add/edit/delete workers, post shifts, close shifts for interest gathering, run solver
- **Worker**: Can view open shifts, express interest in shifts they can work

### Database
- **Neon PostgreSQL**: Cloud-hosted, scalable, with SSL connections
- **SQLAlchemy ORM**: Type-safe queries with relationship management
- **Cascade Deletes**: Automatic cleanup when business/shift/worker deleted

## 🚀 Quick Start

### Prerequisites
```bash
pip install -r requirements.txt
```

### Configuration
Create a `.env` file in the project root:
```bash
DATABASE_URL=postgresql://neondb_owner:npg_EIlADN65qWnQ@ep-delicate-moon-abu91e7z-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
FLASK_ENV=development
FLASK_DEBUG=true
SECRET_KEY=your-secret-key-here
```

### Start the Server
```bash
python web_interface.py
```
Visit: **http://localhost:5000**

## 📋 Business Registration & Multi-Tenancy

### Create a Business (Manager)
```bash
curl -X POST http://localhost:5000/api/register-business \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Acme Hospital",
    "manager_name": "Dr. Smith"
  }'
```

Response:
```json
{
  "success": true,
  "business_id": 1,
  "business_name": "Acme Hospital",
  "business_number": "AB12CD34",
  "join_link": "/join/AB12CD34"
}
```

### Share Join Link with Workers
Send workers the **join link**: `http://localhost:5000/join/AB12CD34`

Workers can sign up there with their name, seniority, hourly rate, and skills.

## 👥 Worker Management (Manager Only)

### Add a Worker
```bash
curl -X POST http://localhost:5000/api/workers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice",
    "seniority_level": 3,
    "hourly_rate": 25.00,
    "skills": ["ICU", "Pediatrics"],
    "availability": [
      {
        "days": [0, 1, 2, 3, 4],
        "start": "09:00",
        "end": "17:00"
      }
    ]
  }'
```

### Get All Workers
```bash
curl http://localhost:5000/api/workers
```

### Delete a Worker
```bash
curl -X DELETE http://localhost:5000/api/workers/1
```

## 📅 Shift Management (Manager Only)

### Create a Shift
```bash
curl -X POST http://localhost:5000/api/shifts \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-03-25",
    "start_time": "09:00",
    "end_time": "17:00",
    "workers_required": 2,
    "required_skills": ["ICU"],
    "hourly_rate_multiplier": 1.5
  }'
```

### Get All Shifts
```bash
curl http://localhost:5000/api/shifts
```

### Close a Shift (Opens for Interest)
```bash
curl -X PUT http://localhost:5000/api/shifts/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "Closed"}'
```

**Note**: Only "Closed" shifts are considered when running the solver.

## 💬 Shift Interest Flow (Worker & Manager)

### Worker: Express Interest in a Shift
```bash
curl -X POST http://localhost:5000/api/shifts/1/interest
```

### Worker: Withdraw Interest
```bash
curl -X DELETE http://localhost:5000/api/shifts/1/interest
```

### Worker: View My Interests
```bash
curl http://localhost:5000/api/shift-interests/me
```

### Manager: See Interest Dashboard
```bash
curl http://localhost:5000/api/shift-interests
```

Response shows which shifts have interested workers:
```json
[
  {
    "shift_id": 1,
    "date": "2025-03-25",
    "start_time": "09:00",
    "end_time": "17:00",
    "count": 3,
    "interested_workers": ["Alice", "Bob", "Charlie"]
  }
]
```

## 🎯 Run the Solver (Manager Only)

### Trigger Scheduling
```bash
curl -X POST http://localhost:5000/api/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "top_k": 3,
    "weights": {
      "time_off_request_weight": 10.0,
      "seniority_reward_weight": 5.0,
      "weekend_balance_weight": 8.0,
      "skill_matching_weight": 7.0,
      "workload_balance_weight": 6.0,
      "compensation_minimization_weight": 2.0,
      "overstaffing_penalty_weight": 3.0
    }
  }'
```

**Note**: 
- Solver ONLY considers **Closed** shifts with interests
- Workers are automatically filtered to only interested workers
- If no interests exist for a shift, all workers are eligible

Response:
```json
{
  "success": true,
  "message": "Generated 3 solutions",
  "solutions": [
    {
      "rank": 1,
      "objective_value": 1234.56,
      "assignments": [
        {
          "worker_id": 1,
          "worker_name": "Alice",
          "shift_id": 1,
          "shift_date": "2025-03-25",
          "shift_start": "09:00",
          "shift_end": "17:00"
        }
      ]
    }
  ],
  "summary": {
    "total_workers": 5,
    "total_shifts": 2,
    "total_solutions": 3
  }
}
```

## 🔐 Access Control

### Authentication Flow
1. Manager registers business → Session set with `business_id` and `user_role: "Manager"`
2. Worker joins business → Session set with `business_id`, `worker_id`, and `user_role: "Worker"`
3. All endpoints validate session and enforce role checks

### Manager-Only Endpoints
- `POST /api/workers` - Add worker
- `PUT /api/workers/<id>` - Edit worker
- `DELETE /api/workers/<id>` - Delete worker
- `POST /api/shifts` - Create shift
- `DELETE /api/shifts/<id>` - Delete shift
- `PUT /api/shifts/<id>/status` - Close/reopen shift
- `POST /api/schedule` - Run solver
- `GET /api/shift-interests` - View interest dashboard
- `POST /api/clear-all` - Clear business data

### Worker-Only Endpoints
- `POST /api/shifts/<id>/interest` - Express interest
- `DELETE /api/shifts/<id>/interest` - Withdraw interest
- `GET /api/shift-interests/me` - View my interests

### Public Endpoints
- `GET /api/workers` - List workers (scoped to business)
- `GET /api/shifts` - List shifts (scoped to business)
- `GET /api/stats` - Business statistics
- `GET /api/default-weights` - Default optimization weights

## 🗄️ Database Schema

### businesses
- `id` (PK)
- `name` (string)
- `unique_number` (unique)

### users
- `id` (PK)
- `name` (string)
- `role` (Manager | Worker)
- `business_id` (FK → businesses)

### workers
- `id` (PK)
- `business_id` (FK → businesses)
- `name` (string)
- `seniority_level` (int)
- `hourly_rate` (float)
- `user_role` (Worker)
- `skills_json` (JSON)
- `unavailable_dates_json` (JSON)
- `availability_json` (JSON)
- `preferences_json` (JSON)

### shifts
- `id` (PK)
- `business_id` (FK → businesses)
- `date` (string, YYYY-MM-DD)
- `start_time` (string, HH:MM)
- `end_time` (string, HH:MM)
- `status` (Open | Closed)
- `workers_required` (int)
- `hourly_rate_multiplier` (float)
- `required_skills_json` (JSON)
- `is_weekend` (bool)
- `recurring_weekly` (bool)
- `weekdays_json` (JSON)

### shift_interests
- `id` (PK)
- `business_id` (FK → businesses)
- `shift_id` (FK → shifts)
- `worker_id` (FK → workers)

## 📊 Optimization Weights

The solver optimizes multiple objectives simultaneously:

| Weight | Description | Default |
|--------|-------------|---------|
| `respect_time_off_requests` | Honor unavailable dates | 10.0 |
| `reward_seniority` | Prefer senior workers | 5.0 |
| `balance_weekend_shifts` | Distribute weekends fairly | 8.0 |
| `skill_matching_weight` | Assign workers with required skills | 7.0 |
| `workload_balance_weight` | Equal shifts per worker | 6.0 |
| `compensation_minimization_weight` | Lower payroll cost | 2.0 |
| `overstaffing_penalty_weight` | Avoid overstaffing | 3.0 |

Adjust weights based on priorities. Higher = more important.

## 🧪 Testing

### Create Test Data
```bash
# 1. Register business
curl -X POST http://localhost:5000/api/register-business \
  -H "Content-Type: application/json" \
  -d '{"business_name": "Test Hospital"}'

# 2. Add workers
curl -X POST http://localhost:5000/api/workers \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "seniority_level": 2, "hourly_rate": 25.0}'

# 3. Add shifts
curl -X POST http://localhost:5000/api/shifts \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-03-25",
    "start_time": "09:00",
    "end_time": "17:00",
    "workers_required": 2
  }'

# 4. Close shift
curl -X PUT http://localhost:5000/api/shifts/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "Closed"}'

# 5. Run solver
curl -X POST http://localhost:5000/api/schedule \
  -H "Content-Type: application/json" \
  -d '{"top_k": 3, "weights": {}}'
```

## 🔧 Environment Variables

```bash
# PostgreSQL Connection (Required for production)
DATABASE_URL=postgresql://user:password@host/dbname

# Flask
FLASK_ENV=development|production
FLASK_DEBUG=true|false
SECRET_KEY=your-secret-key

# Server
HOST=0.0.0.0
PORT=5000
```

## 📈 Production Deployment

### Step 1: Set up Neon PostgreSQL
1. Go to [neon.tech](https://neon.tech)
2. Create project and database
3. Copy connection string to `.env`

### Step 2: Install Production Dependencies
```bash
pip install gunicorn
```

### Step 3: Run with Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:5000 web_interface:app
```

### Step 4: (Optional) Use Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🐛 Troubleshooting

### Database Connection Error
- Verify `DATABASE_URL` in `.env`
- Check Neon network allowed IPs
- Ensure `psycopg2-binary` is installed

### Shift Not Found for Solver
- Verify shift is **Closed** status
- Check you're running as **Manager**
- Ensure workers have interests recorded

### No Solutions Generated
- Add more workers to the system
- Reduce optimization constraints or adjust weights
- Check worker availability overlaps with shifts

## 📝 License

MIT License - Feel free to use for personal and commercial projects.

## 🤝 Support

For issues, feature requests, or questions:
1. Check the troubleshooting section above
2. Review API documentation in this README
3. Check error messages in Flask console logs

---

**Last Updated**: March 2025
**Version**: 2.0 (Multi-Tenant SaaS)
