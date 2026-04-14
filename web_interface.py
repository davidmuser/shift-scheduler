#!/usr/bin/env python3
# pyright: reportGeneralTypeIssues=false
"""
Web Interface for Non-Technical Users
User-friendly web interface for managing workers, shifts, and scheduling.
No JSON files, no coding needed - just simple forms and buttons.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import uuid
from typing import Any, Union, Tuple
import logging
from dotenv import load_dotenv



# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.models.data_models import (
    Worker, Shift, SkillLevel, Skill, SchedulingRequest, ObjectiveWeights, WorkerPreference,
    Business as BusinessModelDTO,
    User as UserDTO,
    ShiftStatus, UserRole, Schedule, ScheduleStatus,
    ScheduleAssignment, SchedulingSolution
)
from src.solver.core_solver import SchedulingResponse
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    create_engine,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import text as sa_text
import pathlib


# --- Database setup (Neon PostgreSQL via SQLAlchemy) ---
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    logger.warning('DATABASE_URL not set. Using SQLite fallback for local development.')
    DB_PATH = pathlib.Path('data')
    DB_PATH.mkdir(exist_ok=True)
    DATABASE_URL = f"sqlite:///{DB_PATH / 'app.db'}"

# Create engine with appropriate settings for PostgreSQL or SQLite
if "postgresql" in DATABASE_URL:
    # We remove "ssl": "require" because it's already in your URL string
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        echo=False
    )
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class BusinessModel(Base):
    """Business/tenant entity."""
    __tablename__ = 'businesses'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    unique_number = Column(String, unique=True, nullable=False, index=True)
    
    # Relationships
    users = relationship("UserModel", back_populates="business", cascade="all, delete-orphan")
    workers = relationship("WorkerModel", back_populates="business", cascade="all, delete-orphan")
    shifts = relationship("ShiftModel", back_populates="business", cascade="all, delete-orphan")
    shift_interests = relationship("ShiftInterestModel", back_populates="business", cascade="all, delete-orphan")
    published_schedules = relationship("PublishedScheduleModel", back_populates="business", cascade="all, delete-orphan")
    schedules = relationship("ScheduleModel", back_populates="business", cascade="all, delete-orphan")


class ScheduleModel(Base):
    """Represents a saved or published schedule."""
    __tablename__ = 'schedules'
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)
    status = Column(String, default='Draft', nullable=False)  # Draft, Published, Locked
    assignments = Column(Text, nullable=False)  # JSON string of assignments
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat(), onupdate=lambda: datetime.utcnow().isoformat())

    business = relationship("BusinessModel", back_populates="schedules")


class UserModel(Base):
    """Application user linked to a business."""
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # Manager / Worker
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False, index=True)
    # Optional direct link to a WorkerModel row for worker-role users.
    # This avoids fragile name-based matching when resolving worker sessions.
    worker_id = Column(Integer, ForeignKey('workers.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Relationships
    business = relationship("BusinessModel", back_populates="users")

    # A user's name must be unique within a business
    __table_args__ = (UniqueConstraint('business_id', 'name', name='_business_user_name_uc'),)


class WorkerModel(Base):
    """ORM model for workers. Skills and unavailable_dates stored as JSON text."""
    __tablename__ = 'workers'
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String, nullable=False)
    seniority_level = Column(Integer, default=0)
    hourly_rate = Column(Float, default=15.0)
    user_role = Column(String, default=UserRole.WORKER.value)
    # JSON-encoded lists/sets
    skills_json = Column(Text, default='[]')
    unavailable_dates_json = Column(Text, default='[]')
    # Prefer storing weekly availability (array of {day,start,end})
    availability_json = Column(Text, default='[]')
    preferences_json = Column(Text, default='{}')
    
    # Relationships
    business = relationship("BusinessModel", back_populates="workers")
    shift_interests = relationship("ShiftInterestModel", back_populates="worker", cascade="all, delete-orphan")

    # Composite unique constraint for name per business
    __table_args__ = (UniqueConstraint('business_id', 'name', name='_business_worker_name_uc'),)


class ShiftModel(Base):
    """ORM model for shifts. required_skills stored as JSON text."""
    __tablename__ = 'shifts'
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False, index=True)
    date = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    shift_type = Column(String, default='standard')
    required_skills_json = Column(Text, default='[]')
    workers_required = Column(Integer, default=1)
    hourly_rate_multiplier = Column(Float, default=1.0)
    is_weekend = Column(Boolean, default=False)
    # Support recurring weekly shifts (store weekdays as JSON list, 0=Mon..6=Sun or name strings)
    recurring_weekly = Column(Boolean, default=False)
    weekdays_json = Column(Text, default='[]')
    status = Column(String, default=ShiftStatus.OPEN.value)  # Open or Closed
    note = Column(Text, default='')  # Custom note for this shift

    # Relationships
    business = relationship("BusinessModel", back_populates="shifts")
    shift_interests = relationship("ShiftInterestModel", back_populates="shift", cascade="all, delete-orphan")


class ShiftInterestModel(Base):
    """Represents a worker expressing interest in a shift."""
    __tablename__ = 'shift_interests'
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey('shifts.id', ondelete='CASCADE'), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey('workers.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Relationships
    business = relationship("BusinessModel", back_populates="shift_interests")
    shift = relationship("ShiftModel", back_populates="shift_interests")
    worker = relationship("WorkerModel", back_populates="shift_interests")


class PublishedScheduleModel(Base):
    """Persisted, published schedule for a business and period.

    Stores the final assignments that a manager chose to publish so
    workers can see them, along with a lock flag that freezes
    availability changes for that period.
    """
    __tablename__ = 'published_schedules'
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False, index=True)
    period_start = Column(String, nullable=False)  # ISO date (YYYY-MM-DD)
    period_end = Column(String, nullable=False)    # ISO date (YYYY-MM-DD)
    is_locked = Column(Boolean, default=True)
    created_at = Column(String, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    solution_rank = Column(Integer, nullable=True)
    objective_value = Column(Float, nullable=True)
    assignments_json = Column(Text, default='[]')
    unresolved_comments_json = Column(Text, default='{}')

    business = relationship("BusinessModel", back_populates="published_schedules")


# ------------------------------------------------------------
# Helpers for business scoping and roles (simple session-based)
# ------------------------------------------------------------
def _get_business_id():
    bid = session.get('business_id')
    return int(bid) if bid is not None else None


def _get_worker_id():
    wid = session.get('worker_id')
    return int(wid) if wid is not None else None


def _require_business():
    bid = _get_business_id()
    if not bid:
        return None, jsonify({'error': 'No business in session. Register or join a business first.'}), 401
    return bid, None, None


def _require_role(role: str):
    current_role = session.get('user_role')
    if current_role != role:
        return False, jsonify({'error': f'{role} role required'}), 403
    return True, None, None


def _require_worker():
    """Resolve and require a worker context for the current session.

    Prefer an existing worker_id in the session. If missing but the
    logged-in user has a Worker role, attempt to resolve the worker
    from the UserModel.worker_id link, falling back to name-based
    lookup for legacy records. On success, cache worker_id in the
    session for future requests.
    """
    wid = _get_worker_id()
    if wid:
        return wid, None, None

    # Best-effort resolution for worker-role users without worker_id in session.
    bid = _get_business_id()
    current_role = session.get('user_role')
    current_user_id = session.get('user_id')

    if bid is not None and current_role == UserRole.WORKER.value and current_user_id is not None:
        db = SessionLocal()
        try:
            user_obj = db.query(UserModel).filter(
                UserModel.id == int(current_user_id),
                UserModel.business_id == bid,
            ).first()
            if user_obj is not None:
                # First, prefer a direct worker_id link if present.
                linked_wid = getattr(user_obj, 'worker_id', None)
                if linked_wid is not None:
                    wid = int(linked_wid)
                else:
                    # Fallback: legacy name-based matching within this business.
                    worker_obj = db.query(WorkerModel).filter(
                        WorkerModel.business_id == bid,
                        WorkerModel.name.ilike(user_obj.name),
                    ).first()
                    if worker_obj is not None:
                        wid = int(worker_obj.id)  # type: ignore[arg-type]
                        # Persist this association for the future.
                        try:
                            user_obj.worker_id = worker_obj.id
                            db.add(user_obj)
                            db.commit()
                        except Exception:
                            db.rollback()

                if wid is not None:
                    session['worker_id'] = wid
                    return wid, None, None
        finally:
            db.close()

    return None, jsonify({'error': 'Worker session required. Join a business as a worker to proceed.'}), 401


def _generate_business_number() -> str:
    return uuid.uuid4().hex[:8].upper()


def _set_session(business_id: int, business_name: str, user_role: str, user_id: int, user_name: str, worker_id: int | None = None):
    session['business_id'] = business_id
    session['business_name'] = business_name
    session['user_role'] = user_role
    session['user_id'] = user_id
    session['user_name'] = user_name
    if worker_id is not None:
        session['worker_id'] = worker_id


def _safe_json_loads(value, default):
    """Safely load JSON from possibly-null or Column-backed values."""
    if value in (None, ""):
        return default
    try:
        if not isinstance(value, (str, bytes, bytearray)):
            value = str(value)
        return json.loads(value)
    except Exception:
        return default


def _safe_json_dumps(value, fallback="[]"):
    """Safely dump JSON to string."""
    try:
        return json.dumps(value)
    except Exception:
        return fallback


def init_db():
    """Create DB tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def _ensure_column(table_name: str, col_name: str, col_def_sql: str) -> None:
    """Ensure a column exists on a table for SQLite and PostgreSQL.

    This is a lightweight, code-based migration helper so existing
    deployments (especially Neon/Postgres) gain new columns like
    users.worker_id without manual DDL.
    """
    conn = engine.raw_connection()
    try:
        cur = conn.cursor()
        dialect = engine.dialect.name

        if dialect == 'sqlite':
            # Existing behavior: inspect pragma and ALTER TABLE if missing
            cur.execute(f"PRAGMA table_info('{table_name}')")
            cols = [r[1] for r in cur.fetchall()]
            if col_name not in cols:
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_def_sql}")
                conn.commit()
        else:
            # For PostgreSQL (Neon) and other SQL engines, rely on
            # ADD COLUMN IF NOT EXISTS which is idempotent.
            # Example SQL: ALTER TABLE "users" ADD COLUMN IF NOT EXISTS worker_id INTEGER
            try:
                cur.execute(
                    f'ALTER TABLE "{table_name}" '
                    f'ADD COLUMN IF NOT EXISTS {col_def_sql}'
                )
                conn.commit()
            except Exception:
                # Best-effort; ignore if the column already exists or
                # the backend doesn't support IF NOT EXISTS.
                conn.rollback()
    finally:
        conn.close()

# Add new columns if missing (non-destructive for backward compatibility)
try:
    _ensure_column('workers', 'availability_json', "availability_json TEXT DEFAULT '[]'")
    _ensure_column('shifts', 'recurring_weekly', "recurring_weekly INTEGER DEFAULT 0")
    _ensure_column('shifts', 'weekdays_json', "weekdays_json TEXT DEFAULT '[]'")
    _ensure_column('workers', 'business_id', "business_id INTEGER")
    _ensure_column('workers', 'user_role', "user_role TEXT DEFAULT 'Worker'")
    _ensure_column('shifts', 'business_id', "business_id INTEGER")
    _ensure_column('shifts', 'status', "status TEXT DEFAULT 'Open'")
    _ensure_column('shifts', 'note', "note TEXT DEFAULT ''")
    _ensure_column('users', 'business_id', "business_id INTEGER")
    _ensure_column('users', 'worker_id', "worker_id INTEGER")
    _ensure_column('businesses', 'unique_number', "unique_number TEXT")
except Exception:
    # If this fails, it's non-fatal; DB will keep older schema
    pass
from src.solver.core_solver import ShiftSchedulingSolver

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
# ... existing code ...

app.secret_key = 'shift-scheduler-secret-key-change-in-production'

# Data storage (in-memory for now, can be switched to database)
"""
In-memory dicts were replaced with a SQLite DB. Use the DB session for CRUD.
"""
solutions = None


def _get_active_published_schedule(db, business_id: int) -> PublishedScheduleModel | None:
    """Return the most recently created published schedule for a business, if any."""
    try:
        return (
            db.query(PublishedScheduleModel)
            .filter(PublishedScheduleModel.business_id == int(business_id))
            .order_by(PublishedScheduleModel.created_at.desc(), PublishedScheduleModel.id.desc())
            .first()
        )
    except Exception:
        return None


# ============================================================================
# ROUTES - HOME & SETUP
# ============================================================================

@app.route('/')
def index():
    """Home page with login/registration."""
    # If user is already logged in, redirect based on role
    if session.get('business_id'):
        if session.get('user_role') == UserRole.MANAGER.value:
            return redirect('/setup')
        else:
            return redirect('/availability')
    return render_template('login.html')


@app.route('/login')
def login_page():
    """Login page."""
    # If user is already logged in, redirect based on role
    if session.get('business_id'):
        if session.get('user_role') == UserRole.MANAGER.value:
            return redirect('/setup')
        else:
            return redirect('/availability')
    return render_template('login.html')


@app.route('/setup')
def setup():
    """Setup wizard for workers and shifts (Manager only)."""
    # Redirect to login if not authenticated
    if not session.get('business_id'):
        return redirect('/')
    
    # Redirect workers to availability page
    if session.get('user_role') == UserRole.WORKER.value:
        return redirect('/availability')
        
    db = SessionLocal()
    business_number = '--'
    try:
        biz = db.query(BusinessModel).filter_by(id=session.get('business_id')).first()
        if biz:
            business_number = biz.unique_number
    finally:
        db.close()
    
    return render_template(
        'setup.html',
        business_name=session.get('business_name'),
        business_number=business_number,
        user_role=session.get('user_role'),
        user_name=session.get('user_name'),
    )


@app.route('/availability')
def availability():
    """Page for workers to see and declare availability for shifts."""
    if not session.get('business_id'):
        return redirect('/')
    
    # This page is primarily for workers, but managers can view it.
    # The API endpoints will handle role-specific actions.
    return render_template(
        'worker_availability.html',
        business_name=session.get('business_name'),
        user_role=session.get('user_role'),
        user_name=session.get('user_name')
    )


# =========================================================================
# ROUTES - BUSINESS REGISTRATION & JOIN
# =========================================================================


def _generate_unique_business_number(session):
    """Generate a unique business number not present in DB."""
    for _ in range(5):
        num = _generate_business_number()
        exists = session.query(BusinessModel).filter(BusinessModel.unique_number == num).first()
        if not exists:
            return num
    # fallback to UUID chunk
    return uuid.uuid4().hex[:10].upper()


@app.route('/api/register-business', methods=['POST'])  # type: ignore[misc]
def register_business():
    data = request.json or {}
    name = data.get('business_name') or data.get('name')
    manager_name = data.get('manager_name') or 'Manager'
    if not name:
        return jsonify({'error': 'business_name is required'}), 400

    db = SessionLocal()
    try:
        unique_number = _generate_unique_business_number(db)
        biz = BusinessModel(name=name, unique_number=unique_number)
        db.add(biz)
        db.commit()
        db.refresh(biz)

        user = UserModel(name=manager_name, role=UserRole.MANAGER.value, business_id=biz.id)
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create default shift templates (Morning and Evening)
        from datetime import datetime, timedelta
        today = datetime.now().date()
        
        # Morning shift: 06:00 - 14:00
        morning_shift = ShiftModel(
            business_id=biz.id,
            date=str(today),
            start_time='06:00',
            end_time='14:00',
            shift_type='Morning',
            workers_required=1,
            required_skills_json='[]',
            hourly_rate_multiplier=1.0,
            status='Open'
        )
        db.add(morning_shift)
        
        # Evening shift: 14:00 - 22:00
        evening_shift = ShiftModel(
            business_id=biz.id,
            date=str(today),
            start_time='14:00',
            end_time='22:00',
            shift_type='Evening',
            workers_required=1,
            required_skills_json='[]',
            hourly_rate_multiplier=1.0,
            status='Open'
        )
        db.add(evening_shift)
        db.commit()

        _set_session(int(biz.id), str(biz.name), UserRole.MANAGER.value, int(user.id), str(user.name))  # type: ignore[arg-type]

        return jsonify({
            'success': True,
            'business_id': biz.id,
            'business_name': biz.name,
            'business_number': biz.unique_number,
            'manager_user_id': user.id,
            'join_link': f"/join/{biz.unique_number}"
        }), 201
    except Exception as e:
        db.rollback()
        if 'UNIQUE constraint failed' in str(e) or 'duplicate key value violates unique constraint' in str(e):
            return jsonify({'error': f'A user with the name "{manager_name}" already exists in this business. Please choose a different name.'}), 409
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


@app.route('/api/login', methods=['POST'])
def login():
    """Login endpoint for existing users."""
    data = request.json or {}
    business_number = data.get('business_number', '').strip().upper()
    username = data.get('username', data.get('user_name', '')).strip()
    password = data.get('password', '')

    if not ((business_number and username) or (username and password)):
        return jsonify({'error': 'Provide business number and username, or just username and password'}), 400

    db = SessionLocal()
    try:
        user = None
        if business_number and username:
            biz = db.query(BusinessModel).filter(BusinessModel.unique_number == business_number).first()
            if not biz:
                return jsonify({'error': 'Business not found'}), 404
            user = db.query(UserModel).filter(UserModel.business_id == biz.id, UserModel.name.ilike(username)).first()
        elif username and password:
            user = db.query(UserModel).filter_by(name=username).first()

        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401

        biz = db.query(BusinessModel).filter_by(id=user.business_id).first()
        if not biz:
            return jsonify({'error': 'Business not found for this user'}), 404

        worker_id = None
        if user.role.lower() == 'worker':
            worker = db.query(WorkerModel).filter_by(business_id=biz.id, name=user.name).first()
            if worker:
                worker_id = worker.id

        _set_session(biz.id, biz.name, user.role, user.id, user.name, worker_id=worker_id)  # type: ignore
        
        if user.role.lower() == 'manager':
            return jsonify({"success": True, "message": "Login successful", "redirect_url": url_for('setup'), "user_role": "Manager"})
        else:
            return jsonify({"success": True, "message": "Login successful", "redirect_url": url_for('availability'), "user_role": "Worker"})
    except Exception as e:
        db.rollback()
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'An internal error occurred during login.'}), 500
    finally:
        db.close()


@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout endpoint - clear session."""
    try:
        session.clear()
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/logout', methods=['GET'])
def logout_page():
    """Logout page - clears session and redirects to login."""
    session.clear()
    return redirect('/')


@app.route('/join/<business_number>', methods=['GET'])
def get_join_info(business_number):
    db = SessionLocal()
    try:
        biz = db.query(BusinessModel).filter(BusinessModel.unique_number == business_number).first()
        if not biz:
            return jsonify({'error': 'Invalid business number'}), 404
        return jsonify({'business_id': biz.id, 'business_name': biz.name}), 200
    finally:
        db.close()


@app.route('/join/<business_number>', methods=['POST'])
def join_business(business_number):
    data = request.json or {}
    worker_name = data.get('name') or data.get('worker_name')
    if not worker_name:
        return jsonify({'error': 'Worker name is required'}), 400

    db = SessionLocal()
    try:
        biz = db.query(BusinessModel).filter(BusinessModel.unique_number == business_number).first()
        if not biz:
            return jsonify({'error': 'Invalid business number'}), 404

        worker = WorkerModel(
            business_id=biz.id,
            name=worker_name,
            seniority_level=int(data.get('seniority_level', 1)),
            hourly_rate=float(data.get('hourly_rate', 20.0)),
            skills_json=_safe_json_dumps(data.get('skills', [])),
            unavailable_dates_json=_safe_json_dumps(data.get('unavailable_dates', [])),
            availability_json=_safe_json_dumps(data.get('availability', [])),
            preferences_json=_safe_json_dumps(data.get('preferences', {})),
            user_role=UserRole.WORKER.value,
        )
        db.add(worker)
        db.commit()
        db.refresh(worker)

        # Create a linked UserModel so we have a durable User->Worker mapping.
        user = UserModel(name=worker_name, role=UserRole.WORKER.value, business_id=biz.id, worker_id=worker.id)
        db.add(user)
        db.commit()
        db.refresh(user)

        _set_session(biz.id, biz.name, UserRole.WORKER.value, user.id, user.name, worker_id=worker.id)  # type: ignore

        return jsonify({
            'success': True,
            'business_id': biz.id,
            'business_name': biz.name,
            'worker_id': worker.id,
            'user_id': user.id,
        }, 201)
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


# ============================================================================
# ROUTES - BUSINESS STATS
# ============================================================================

@app.route('/api/stats', methods=['GET'])  # type: ignore
def get_stats():
    """Get business statistics (workers, shifts, interests count)."""
    bid, err, code = _require_business()
    if err:
        return err, code

    db = SessionLocal()
    try:
        total_workers = db.query(WorkerModel).filter(WorkerModel.business_id == bid).count()
        total_shifts = db.query(ShiftModel).filter(ShiftModel.business_id == bid).count()
        total_interests = db.query(ShiftInterestModel).join(
            ShiftModel, ShiftInterestModel.shift_id == ShiftModel.id
        ).filter(ShiftModel.business_id == bid).count()

        return jsonify({
            'total_workers': total_workers,
            'total_shifts': total_shifts,
            'total_interests': total_interests,
            'business_id': bid,
            'business_number': db.query(BusinessModel.unique_number).filter(BusinessModel.id == bid).scalar()
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to get stats: {str(e)}'}), 500
    finally:
        db.close()


# ============================================================================
# ROUTES - WORKERS MANAGEMENT
# ============================================================================

def worker_to_dto(worker_instance: Any) -> "Worker":
    """Convert a WorkerModel ORM instance to a Pydantic DTO."""
    try:
        preferences_data = _safe_json_loads(worker_instance.preferences_json, {})
        
        worker_id = worker_instance.id
        if 'worker_id' not in preferences_data:
            preferences_data['worker_id'] = worker_id

        preferences = WorkerPreference(
            worker_id=worker_id,
            preferred_shift_types=preferences_data.get('preferred_shift_types', []),
            unavailable_dates=set(preferences_data.get('unavailable_dates', [])),
            max_shifts_per_week=preferences_data.get('max_shifts_per_week', 5),
            min_shifts_per_week=preferences_data.get('min_shifts_per_week', 0),
            no_consecutive_shifts=preferences_data.get('no_consecutive_shifts', True),
            prefer_weekends=preferences_data.get('prefer_weekends', False),
            avoid_weekends=preferences_data.get('avoid_weekends', False)
        )
        
        skills_list = _safe_json_loads(worker_instance.skills_json, [])
        
        return Worker(
            id=worker_instance.id,
            business_id=worker_instance.business_id,
            name=worker_instance.name,
            seniority_level=worker_instance.seniority_level,
            hourly_rate=worker_instance.hourly_rate,
            skills=[Skill(name=s) for s in skills_list],
            preferences=preferences,
        )
    except Exception as e:
        logger.error(f"Failed to convert worker ORM to DTO for worker ID {getattr(worker_instance, 'id', 'N/A')}", exc_info=True)
        raise

@app.route('/api/workers', methods=['GET'])
def get_workers() -> Any:
    """Get all workers as JSON."""
    bid, err, code = _require_business()
    if err:
        return err, code

    db = SessionLocal()
    try:
        db_workers = db.query(WorkerModel).filter(WorkerModel.business_id == bid).all()
        workers_list = []
        for w in db_workers:
            skills_raw = _safe_json_loads(getattr(w, 'skills_json', '[]'), [])
            skills = [s['name'] if isinstance(s, dict) else s for s in skills_raw]
            unavailable = list(_safe_json_loads(getattr(w, 'unavailable_dates_json', '[]'), []))
            availability = list(_safe_json_loads(getattr(w, 'availability_json', '[]'), []))

            workers_list.append({
                'id': w.id,
                'name': w.name,
                'seniority_level': w.seniority_level,
                'hourly_rate': w.hourly_rate,
                'skills': skills,
                'unavailable_dates': unavailable,
                'availability': availability,
                'user_role': getattr(w, 'user_role', UserRole.WORKER.value),
            })
        return jsonify(workers_list)
    finally:
        db.close()

@app.route('/api/workers', methods=['POST'])  # type: ignore
def add_worker():
    """Add a new worker from form data."""
    data = request.json or {}
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Worker name is required'}), 400

    bid, err, code = _require_business()
    if err:
        return err, code

    ok, err_resp, err_code = _require_role(UserRole.MANAGER.value)
    if not ok:
        return err_resp, err_code

    provided_staff = data.get('staff_id') or data.get('staffId')
    db = SessionLocal()
    try:
        # Check for duplicate name across both workers and users (managers)
        existing_worker = db.query(WorkerModel).filter(
            WorkerModel.business_id == bid,
            WorkerModel.name.ilike(data['name'])
        ).first()
        if existing_worker:
            return jsonify({'error': f"A worker named '{data['name']}' already exists."}), 409

        existing_user = db.query(UserModel).filter(
            UserModel.business_id == bid,
            UserModel.name.ilike(data['name'])
        ).first()
        if existing_user:
            return jsonify({'error': f"A user (manager) named '{data['name']}' already exists. Worker names must be unique."}), 409

        new_worker = WorkerModel(
            business_id=bid,
            name=data['name'],
            seniority_level=int(data.get('seniority_level', 1)),
            hourly_rate=float(data.get('hourly_rate', 20.0)),
            skills_json=_safe_json_dumps(data.get('skills', [])),
            unavailable_dates_json=_safe_json_dumps(data.get('unavailable_dates', [])),
            availability_json=_safe_json_dumps(data.get('availability', [])),
            preferences_json=_safe_json_dumps(data.get('preferences', {})),
            user_role=UserRole.WORKER.value,
        )
        db.add(new_worker)
        db.commit()
        db.refresh(new_worker)  # Ensure the new_worker object is up-to-date with DB data (like ID)
        
        # Create a linked UserModel so the worker can log in
        user = UserModel(name=data['name'], role=UserRole.WORKER.value, business_id=bid, worker_id=new_worker.id)
        db.add(user)
        db.commit()
        db.refresh(user)

        try:
            worker_dto = worker_to_dto(new_worker)
            return jsonify(worker_dto.model_dump(mode='json')), 201
        except Exception as e:
            logger.error(f"Error converting worker to DTO: {e}", exc_info=True)
            # Even if DTO conversion fails, the worker was created.
            # Return a success message but indicate the DTO issue.
            return jsonify({
                'message': 'Worker added, but failed to serialize response.',
                'worker_id': new_worker.id
            }), 201

    except Exception as e:
        db.rollback()
        logger.error(f"Error adding worker: {e}", exc_info=True)
        # Check for unique constraint violation
        if 'UNIQUE constraint failed' in str(e) or 'duplicate key value violates unique constraint' in str(e):
            return jsonify({'error': f"A user or worker with the name '{data['name']}' already exists."}), 409
        return jsonify({'error': 'An internal error occurred while adding the worker.'}), 500
    finally:
        db.close()


@app.route('/api/workers/<worker_id>', methods=['GET'])
def get_worker(worker_id) -> Any:
    """Get a specific worker (worker_id is an integer path segment)."""
    try:
        wid = int(worker_id)
    except Exception:
        return jsonify({'error': 'Invalid worker id'}), 400

    bid, err, code = _require_business()
    if err:
        return err, code

    db = SessionLocal()
    try:
        dbw = db.query(WorkerModel).filter(WorkerModel.id == wid, WorkerModel.business_id == bid).first()
        if not dbw:
            return jsonify({'error': 'Worker not found'}), 404
        skills = [s['name'] if isinstance(s, dict) else s for s in _safe_json_loads(getattr(dbw, 'skills_json', '[]'), [])]
        unavailable = list(_safe_json_loads(getattr(dbw, 'unavailable_dates_json', '[]'), []))
        availability = list(_safe_json_loads(getattr(dbw, 'availability_json', '[]'), []))

        return jsonify({
            'id': dbw.id,
            'name': dbw.name,
            'seniority_level': dbw.seniority_level,
            'hourly_rate': dbw.hourly_rate,
            'skills': skills,
            'unavailable_dates': unavailable,
            'availability': availability,
            'user_role': getattr(dbw, 'user_role', UserRole.WORKER.value),
        })
    finally:
        db.close()


@app.route('/api/workers/<worker_id>', methods=['PUT'])  # type: ignore[misc]
def update_worker(worker_id):
    """Update a worker."""
    try:
        wid = int(worker_id)
    except Exception:
        return jsonify({'error': 'Invalid worker id'}), 400

    bid, err, code = _require_business()
    if err:
        return err, code

    ok, err_resp, err_code = _require_role(UserRole.MANAGER.value)
    if not ok:
        return err_resp, err_code

    session = SessionLocal()
    try:
        dbw = session.query(WorkerModel).filter(WorkerModel.id == wid, WorkerModel.business_id == bid).first()
        if not dbw:
            return jsonify({'error': 'Worker not found'}), 404
        try:
            data = request.json or {}
            if 'name' in data:
                dbw.name = data['name']
            if 'seniority_level' in data:
                setattr(dbw, 'seniority_level', int(data['seniority_level']))
            if 'hourly_rate' in data:
                setattr(dbw, 'hourly_rate', float(data['hourly_rate']))

            # Update skills
            if 'skills' in data:
                skill_items = data['skills'] if isinstance(data['skills'], list) else [s.strip() for s in str(data['skills']).split(',') if s.strip()]
                skills_json = []
                for item in skill_items:
                    if isinstance(item, dict):
                        name = item.get('name') or item.get('skill')
                        level = item.get('level')
                        try:
                            lvl = SkillLevel(level) if level else SkillLevel.INTERMEDIATE
                            lvl_val = lvl.value
                        except Exception:
                            lvl_val = SkillLevel.INTERMEDIATE.value
                        if name:
                            skills_json.append({'name': str(name), 'level': lvl_val})
                    else:
                        skill_name = str(item).strip()
                        if skill_name:
                            skills_json.append({'name': skill_name, 'level': SkillLevel.INTERMEDIATE.value})
                setattr(dbw, 'skills_json', _safe_json_dumps(skills_json))

            # Update unavailable dates
            if 'unavailable_dates' in data:
                dates = data['unavailable_dates']
                if isinstance(dates, list):
                    setattr(dbw, 'unavailable_dates_json', _safe_json_dumps(dates))
                else:
                    setattr(dbw, 'unavailable_dates_json', _safe_json_dumps([d.strip() for d in str(dates).split(',') if d.strip()]))

            # Update availability
            if 'availability' in data:
                av = data['availability']
                try:
                    if isinstance(av, str):
                        av = json.loads(av)
                    setattr(dbw, 'availability_json', _safe_json_dumps(av))
                except Exception:
                    setattr(dbw, 'availability_json', _safe_json_dumps([]))

            session.add(dbw)
            session.commit()
            return jsonify({'success': True, 'message': 'Worker updated'})
        except Exception as e:
            session.rollback()
            return jsonify({'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/workers/<worker_id>', methods=['DELETE'])  # type: ignore[misc]
def delete_worker(worker_id):
    """Delete a worker by integer id."""
    try:
        wid = int(worker_id)
    except Exception:
        return jsonify({'error': 'Invalid worker id'}), 400

    bid, err, code = _require_business()
    if err:
        return err, code
    ok, err_resp, err_code = _require_role(UserRole.MANAGER.value)
    if not ok:
        return err_resp, err_code

    session = SessionLocal()
    try:
        dbw = session.query(WorkerModel).filter(WorkerModel.id == wid, WorkerModel.business_id == bid).first()
        if not dbw:
            return jsonify({'error': 'Worker not found'}), 404
            
        # Delete associated UserModel if it exists
        user_to_delete = session.query(UserModel).filter_by(worker_id=dbw.id).first()
        if user_to_delete:
            session.delete(user_to_delete)
        
        # Delete the worker and cascade delete related records
        session.delete(dbw)
        session.commit()
        
        return jsonify({'success': True, 'message': f'Worker deleted successfully'})
    except Exception as e:
        session.rollback()
        return jsonify({'error': f'Failed to delete worker: {str(e)}'}), 500
    finally:
        session.close()


# ============================================================================
# ROUTES - SHIFTS MANAGEMENT
# ============================================================================

@app.route('/api/shifts', methods=['GET'])  # type: ignore[misc]
def get_shifts() -> Any:
    """Get all shifts as JSON."""
    bid, err, code = _require_business()
    if err:
        return err, code

    session = SessionLocal()
    try:
        db_shifts = session.query(ShiftModel).filter(ShiftModel.business_id == bid).all()
        shifts_list = []
        for s in db_shifts:
            date_str = s.date
            start_str = s.start_time
            end_str = s.end_time
            shift_start_iso = f"{date_str}T{start_str}:00"
            shift_end_iso = f"{date_str}T{end_str}:00"
            required_workers = s.workers_required
            hourly_rate_multiplier = s.hourly_rate_multiplier or 1.0
            req_objs = _safe_json_loads(getattr(s, 'required_skills_json', '[]'), [])
            # recurring/weekdays
            recurring = bool(getattr(s, 'recurring_weekly', False))
            weekdays = []
            weekdays = list(_safe_json_loads(getattr(s, 'weekdays_json', '[]'), []))
            req_names = [item['name'] if isinstance(item, dict) else item for item in req_objs]

            shifts_list.append({
                'id': s.id,
                'date': date_str,
                'start_time': start_str,
                'end_time': end_str,
                'shift_start': shift_start_iso,
                'shift_end': shift_end_iso,
                'workers_required': required_workers,
                'required_workers': required_workers,
                'required_skills': req_names,
                'required_skills_objects': req_objs,
                'hourly_rate_multiplier': hourly_rate_multiplier,
                'is_weekend': bool(s.is_weekend),
                'recurring_weekly': recurring,
                'weekdays': weekdays,
                'business_id': getattr(s, 'business_id', bid),
                'status': getattr(s, 'status', ShiftStatus.OPEN.value),
                'note': getattr(s, 'note', ''),
            })
        return jsonify(shifts_list)
    finally:
        session.close()


@app.route('/api/shifts/availability', methods=['GET'])  # type: ignore[misc]
def get_shifts_availability() -> Any:
    """Get shifts organized by day with worker interest data for the availability calendar."""
    bid, err, code = _require_business()
    if err:
        return err, code

    session_local = SessionLocal()
    try:
        # Get current user's worker_id if they are a worker
        worker_id = session.get('worker_id')  # From Flask session, not SQLAlchemy session
        
        # Get all shifts
        db_shifts = session_local.query(ShiftModel).filter(ShiftModel.business_id == bid).all()
        
        # Get all interests for this business
        all_interests = session_local.query(ShiftInterestModel).filter(ShiftInterestModel.business_id == bid).all()
        
        # Build a set of shift_ids this worker is interested in
        worker_interested_shift_ids = set()
        if worker_id:
            worker_interested_shift_ids = {i.shift_id for i in all_interests if i.worker_id == worker_id}
        
        # Organize shifts by date
        shifts_by_day = {}
        for s in db_shifts:
            date_str = str(s.date)
            if date_str not in shifts_by_day:
                shifts_by_day[date_str] = []
            
            req_objs = _safe_json_loads(getattr(s, 'required_skills_json', '[]'), [])
            req_names = [item['name'] if isinstance(item, dict) else item for item in req_objs]
            
            shifts_by_day[date_str].append({
                'id': s.id,
                'date': date_str,
                'start_time': str(s.start_time),
                'end_time': str(s.end_time),
                'workers_required': int(s.workers_required) if s.workers_required else 1,  # type: ignore[arg-type]
                'required_skills': req_names,
                'required_skills_objects': req_objs,
                'is_weekend': bool(s.is_weekend),
                'status': getattr(s, 'status', ShiftStatus.OPEN.value),
            })
        
        # Build worker interests list (shifts current worker is interested in)
        worker_interests = list(worker_interested_shift_ids) if worker_id else []
        
        # Check if there's a published/locked schedule
        ps = None
        if bid is not None:
            ps = _get_active_published_schedule(session_local, bid)
        is_locked = bool(ps and getattr(ps, 'is_locked', False))
        locked_period_start = str(ps.period_start) if ps else None
        locked_period_end = str(ps.period_end) if ps else None
        
        return jsonify({
            'shifts_by_day': shifts_by_day,
            'worker_interests': worker_interests,
            'is_locked': is_locked,
            'locked_period_start': locked_period_start,
            'locked_period_end': locked_period_end,
        })
    except Exception as e:
        logger.error(f"Error in get_shifts_availability: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        session_local.close()


@app.route('/api/shifts', methods=['POST'])  # type: ignore[misc]
def add_shift():
    """Add a new shift from form data."""
    data = request.json or {}
    # Validate required fields (allow recurring weekly shifts without a specific date)
    if not data.get('date') and not (data.get('recurring_weekly') or data.get('recurringWeekly')):
        return jsonify({'error': 'Shift date is required (or mark as recurring weekly)'}), 400
    if not data.get('start_time'):
        return jsonify({'error': 'Start time is required'}), 400
    if not data.get('end_time'):
        return jsonify({'error': 'End time is required'}), 400

    bid, err, code = _require_business()
    if err:
        return err, code

    ok, err_resp, err_code = _require_role(UserRole.MANAGER.value)
    if not ok:
        return err_resp, err_code

    session = SessionLocal()
    try:
        shift_date = data.get('date', '')
        start_time = data['start_time']
        end_time = data['end_time']

        # Parse required skills
        req_skills = []
        if data.get('required_skills'):
            if isinstance(data['required_skills'], list):
                items = data['required_skills']
            else:
                items = [s.strip() for s in str(data['required_skills']).split(',') if s.strip()]
            for item in items:
                if isinstance(item, dict):
                    name = item.get('name') or item.get('skill')
                    level = item.get('level')
                    try:
                        lvl = SkillLevel(level) if level else SkillLevel.INTERMEDIATE
                        lvl_val = lvl.value
                    except Exception:
                        lvl_val = SkillLevel.INTERMEDIATE.value
                    if name:
                        req_skills.append({'name': str(name), 'level': lvl_val})
                else:
                    req_skills.append({'name': str(item), 'level': SkillLevel.INTERMEDIATE.value})

        is_weekend = bool(data.get('is_weekend', False))
        try:
            if not is_weekend:
                dt = datetime.strptime(shift_date, '%Y-%m-%d')
                is_weekend = dt.weekday() >= 5
        except Exception:
            pass
        hourly_rate_multiplier = float(data.get('hourly_rate_multiplier', data.get('hourly_rate_factor', 1.0)))
        workers_required = int(data.get('workers_required', data.get('required_workers', 1)))

        # Recurring weekly handling
        recurring_weekly = bool(data.get('recurring_weekly', False) or data.get('recurringWeekly', False))
        weekdays = []
        if recurring_weekly:
            # Accept weekdays as numbers or names
            w = data.get('weekdays') or data.get('weekdays_json') or data.get('weekdays[]')
            if isinstance(w, str):
                try:
                    w = json.loads(w)
                except Exception:
                    w = [int(x) for x in str(w).split(',') if x.strip().isdigit()]
            if isinstance(w, list):
                weekdays = w

        dbs = ShiftModel(
            business_id=bid,
            date=shift_date,
            start_time=start_time,
            end_time=end_time,
            required_skills_json=_safe_json_dumps(req_skills),
            workers_required=workers_required,
            hourly_rate_multiplier=hourly_rate_multiplier,
            is_weekend=is_weekend,
            recurring_weekly=bool(recurring_weekly),
            weekdays_json=_safe_json_dumps(weekdays),
            status=ShiftStatus.OPEN.value,
            note=data.get('note', '')
        )
        session.add(dbs)
        session.commit()

        return jsonify({
            'success': True,
            'message': f'Shift on {shift_date or "(recurring weekly)"} added successfully',
            'shift_id': dbs.id
        }, 201)
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/shifts/<shift_id>', methods=['DELETE'])  # type: ignore[misc]
def delete_shift(shift_id):
    """Delete a shift."""
    try:
        sid = int(shift_id)
    except Exception:
        return jsonify({'error': 'Invalid shift id'}), 400
    bid, err, code = _require_business()
    if err:
        return err, code

    ok, err_resp, err_code = _require_role(UserRole.MANAGER.value)
    if not ok:
        return err_resp, err_code

    session = SessionLocal()
    try:
        dbs = session.query(ShiftModel).filter(ShiftModel.id == sid, ShiftModel.business_id == bid).first()
        if not dbs:
            return jsonify({'error': 'Shift not found'}), 404
        
        # Delete the shift and cascade delete related records (interests, assignments, etc)
        session.delete(dbs)
        session.commit()
        
        return jsonify({'success': True, 'message': 'Shift deleted successfully'})
    except Exception as e:
        session.rollback()
        return jsonify({'error': f'Failed to delete shift: {str(e)}'}), 500
    finally:
        session.close()


@app.route('/api/shifts/<shift_id>/status', methods=['PUT'])  # type: ignore[misc]
def update_shift_status(shift_id):
    """Manager closes/reopens a shift (only closed shifts can have solver run)."""
    try:
        sid = int(shift_id)
    except Exception:
        return jsonify({'error': 'Invalid shift id'}), 400

    bid, err, code = _require_business()
    if err:
        return err, code

    ok, err_resp, err_code = _require_role(UserRole.MANAGER.value)
    if not ok:
        return err_resp, err_code

    data = request.json or {}
    new_status = data.get('status')
    if new_status not in (ShiftStatus.OPEN.value, ShiftStatus.CLOSED.value):
        return jsonify({'error': f'Invalid status. Must be "{ShiftStatus.OPEN.value}" or "{ShiftStatus.CLOSED.value}"'}), 400

    session = SessionLocal()
    try:
        dbs = session.query(ShiftModel).filter(ShiftModel.id == sid, ShiftModel.business_id == bid).first()
        if not dbs:
            return jsonify({'error': 'Shift not found'}), 404
        setattr(dbs, 'status', str(new_status))
        session.commit()
        return jsonify({
            'success': True,
            'message': f'Shift status updated to {new_status}',
            'shift_id': sid,
            'status': new_status
        })
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()


# =========================================================================
# ROUTES - SHIFT INTERESTS
# =========================================================================


@app.route('/api/shift-interests', methods=['GET'])  # type: ignore[misc]
def list_shift_interests():
    """Manager view: list interests per shift for this business."""
    bid, err, code = _require_business()
    if err:
        return err, code
    ok, err_resp, err_code = _require_role(UserRole.MANAGER.value)
    if not ok:
        return err_resp, err_code

    session = SessionLocal()
    try:
        interests = session.query(ShiftInterestModel).filter(ShiftInterestModel.business_id == bid).all()
        shifts = {s.id: s for s in session.query(ShiftModel).filter(ShiftModel.business_id == bid).all()}
        workers = {w.id: w for w in session.query(WorkerModel).filter(WorkerModel.business_id == bid).all()}

        grouped = {}
        for i in interests:
            grouped.setdefault(i.shift_id, []).append(i.worker_id)

        response = []
        for sid, worker_ids in grouped.items():
            sh = shifts.get(sid)
            response.append({
                'shift_id': sid,
                'date': sh.date if sh else None,
                'start_time': sh.start_time if sh else None,
                'end_time': sh.end_time if sh else None,
                'interested_worker_ids': worker_ids,
                'interested_workers': [workers[w].name for w in worker_ids if w in workers],
                'count': len(worker_ids),
            })

        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/shift-interests/me', methods=['GET'])  # type: ignore[misc]
def list_my_shift_interests():
    """Worker view: list shift ids the current worker is interested in."""
    bid, err, code = _require_business()
    if err:
        return err, code
    wid, err_resp, err_code = _require_worker()
    if err_resp:
        return err_resp, err_code

    session = SessionLocal()
    try:
        interests = session.query(ShiftInterestModel).filter(
            ShiftInterestModel.business_id == bid,
            ShiftInterestModel.worker_id == wid
        ).all()
        return jsonify({'worker_id': wid, 'shift_ids': [i.shift_id for i in interests]})
    finally:
        session.close()


@app.route('/api/shifts/interest', methods=['POST'])  # type: ignore[misc]
def handle_shift_interest():
    """
    Worker marks interest in a shift (or withdraws it).
    Expected JSON: { "shift_id": <id>, "interested": true/false }
    """
    data = request.json or {}
    shift_id = data.get('shift_id')
    interested = data.get('interested', True)
    
    if not shift_id:
        return jsonify({'error': 'shift_id is required'}), 400
    
    try:
        sid = int(shift_id)
    except Exception:
        return jsonify({'error': 'Invalid shift id'}), 400
    
    bid, err, code = _require_business()
    if err:
        return err, code
    
    wid, err_resp, err_code = _require_worker()
    if err_resp:
        return err_resp, err_code
    
    session = SessionLocal()
    try:
        shift = session.query(ShiftModel).filter(ShiftModel.id == sid, ShiftModel.business_id == bid).first()
        if not shift:
            return jsonify({'error': 'Shift not found'}), 404
        
        # If there is a locked published schedule covering this shift date, prevent changes
        if bid is not None:
            ps = _get_active_published_schedule(session, bid)
            if ps and getattr(ps, 'is_locked', True) and getattr(shift, 'date', None):
                try:
                    sd = datetime.strptime(str(shift.date), '%Y-%m-%d').date()
                    start = datetime.strptime(str(ps.period_start), '%Y-%m-%d').date()
                    end = datetime.strptime(str(ps.period_end), '%Y-%m-%d').date()
                    if start <= sd <= end:
                        return jsonify({'error': 'This schedule has been published and locked. Availability for these shifts can no longer be changed.'}), 403
                except Exception:
                    pass
        
        # Find existing interest
        exists = session.query(ShiftInterestModel).filter(
            ShiftInterestModel.business_id == bid,
            ShiftInterestModel.shift_id == sid,
            ShiftInterestModel.worker_id == wid
        ).first()
        
        if interested:
            # Mark as interested (add if not exists)
            if not exists:
                interest = ShiftInterestModel(business_id=bid, shift_id=sid, worker_id=wid)
                session.add(interest)
                session.commit()
            return jsonify({'success': True, 'message': 'Interest recorded'})
        else:
            # Withdraw interest (delete if exists)
            if exists:
                session.delete(exists)
                session.commit()
            return jsonify({'success': True, 'message': 'Interest withdrawn'})
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error handling shift interest: {e}")
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/shifts/<shift_id>/interest', methods=['POST'])  # type: ignore[misc]
def express_interest(shift_id):
    """Worker expresses interest in a shift."""
    try:
        sid = int(shift_id)
    except Exception:
        return jsonify({'error': 'Invalid shift id'}), 400

    bid, err, code = _require_business()
    if err:
        return err, code
    wid, err_resp, err_code = _require_worker()
    if err_resp:
        return err_resp, err_code

    session = SessionLocal()
    try:
        shift = session.query(ShiftModel).filter(ShiftModel.id == sid, ShiftModel.business_id == bid).first()
        if not shift:
            return jsonify({'error': 'Shift not found'}), 404

        # If there is a locked published schedule covering this shift date,
        # prevent workers from changing their interest to keep the design consistent.
        if bid is not None:
            ps = _get_active_published_schedule(session, bid)
            if ps and getattr(ps, 'is_locked', True) and getattr(shift, 'date', None):
                try:
                    sd = datetime.strptime(str(shift.date), '%Y-%m-%d').date()
                    start = datetime.strptime(str(ps.period_start), '%Y-%m-%d').date()
                    end = datetime.strptime(str(ps.period_end), '%Y-%m-%d').date()
                    if start <= sd <= end:
                        return jsonify({'error': 'This schedule has been published and locked. Availability for these shifts can no longer be changed.'}), 403
                except Exception:
                    pass

        exists = session.query(ShiftInterestModel).filter(
            ShiftInterestModel.business_id == bid,
            ShiftInterestModel.shift_id == sid,
            ShiftInterestModel.worker_id == wid
        ).first()
        if exists:
            return jsonify({'success': True, 'message': 'Interest already recorded'})

        interest = ShiftInterestModel(business_id=bid, shift_id=sid, worker_id=wid)
        session.add(interest)
        session.commit()
        return jsonify({'success': True, 'message': 'Interest recorded'})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/shift-interests', methods=['DELETE'])
def remove_shift_interest() -> Union[Response, Tuple[Response, int]]:
    """Remove a worker's interest in a shift."""
    bid, err_resp, err_code = _require_business()
    if err_resp:
        return err_resp, err_code or 500
    
    wid, err_resp, err_code = _require_worker()
    if err_resp:
        return err_resp, err_code or 500

    sid = request.args.get('shift_id')
    if not sid:
        return jsonify({'error': 'shift_id is required'}), 400

    session = SessionLocal()
    try:
        shift = session.query(ShiftModel).filter(ShiftModel.id == sid, ShiftModel.business_id == bid).first()
        if not shift:
            return jsonify({'error': 'Shift not found'}), 404

        # If there is a locked published schedule covering this shift date,
        # prevent workers from changing their interest to keep the design consistent.
        if bid is not None:
            ps = _get_active_published_schedule(session, bid)
            if ps and getattr(ps, 'is_locked', True) and getattr(shift, 'date', None):
                try:
                    sd = datetime.strptime(str(shift.date), '%Y-%m-%d').date()
                    start = datetime.strptime(str(ps.period_start), '%Y-%m-%d').date()
                    end = datetime.strptime(str(ps.period_end), '%Y-%m-%d').date()
                    if start <= sd <= end:
                        return jsonify({'error': 'This schedule has been published and locked. Availability for these shifts can no longer be changed.'}), 403
                except Exception:
                    pass

        interest = session.query(ShiftInterestModel).filter(
            ShiftInterestModel.worker_id == wid,
            ShiftInterestModel.shift_id == sid
        ).first()
        if not interest:
            return jsonify({'success': True, 'message': 'No interest found to remove'}), 200

        session.delete(interest)
        session.commit()
        return jsonify({'success': True, 'message': 'Interest removed'})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/shift/interest', methods=['PUT'])
def add_shift_interest() -> Union[Response, Tuple[Response, int]]:
    """Add a worker's interest in a shift."""
    bid, err_resp, err_code = _require_business()
    if err_resp:
        return err_resp, err_code or 500
    
    wid, err_resp, err_code = _require_worker()
    if err_resp:
        return err_resp, err_code or 500

    sid = request.args.get('shift_id')
    if not sid:
        return jsonify({'error': 'shift_id is required'}), 400

    session = SessionLocal()
    try:
        shift = session.query(ShiftModel).filter(ShiftModel.id == sid, ShiftModel.business_id == bid).first()
        if not shift:
            return jsonify({'error': 'Shift not found'}), 404

        if bid is not None:
            ps = _get_active_published_schedule(session, bid)
            if ps and getattr(ps, 'is_locked', True) and getattr(shift, 'date', None):
                try:
                    sd = datetime.strptime(str(shift.date), '%Y-%m-%d').date()
                    start = datetime.strptime(str(ps.period_start), '%Y-%m-%d').date()
                    end = datetime.strptime(str(ps.period_end), '%Y-%m-%d').date()
                    if start <= sd <= end:
                        return jsonify({'error': 'This schedule has been published and locked. Availability for these shifts can no longer be changed.'}), 403
                except Exception:
                    pass

        existing = session.query(ShiftInterestModel).filter(
            ShiftInterestModel.worker_id == wid,
            ShiftInterestModel.shift_id == sid
        ).first()
        if existing:
            return jsonify({'success': True, 'message': 'Interest already recorded'}), 200

        interest = ShiftInterestModel(business_id=bid, shift_id=sid, worker_id=wid)
        session.add(interest)
        session.commit()
        return jsonify({'success': True, 'message': 'Interest recorded'}), 201
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


# ============================================================================
# ROUTES - SCHEDULING
# ============================================================================

@app.route('/schedule')
def schedule_page():
    """Schedule optimization page."""
    return render_template(
        'schedule.html',
        business_name=session.get('business_name'),
        user_role=session.get('user_role'),
    )


@app.route('/api/schedule', methods=['POST'])  # type: ignore[misc]
def run_schedule():
    """Run the scheduling algorithm. Only works on closed shifts with interested workers."""
    global solutions
    bid, err, code = _require_business()
    if err:
        return err, code

    ok, err_resp, err_code = _require_role(UserRole.MANAGER.value)
    if not ok:
        return err_resp, err_code

    # Validate we have workers and shifts in DB for this business
    session = SessionLocal()
    try:
        total_workers = session.query(WorkerModel).filter(WorkerModel.business_id == bid).count()
        total_shifts = session.query(ShiftModel).filter(ShiftModel.business_id == bid).count()
    finally:
        session.close()

    if total_workers == 0:
        return jsonify({'error': 'No workers added. Please add workers first.'}), 400
    if total_shifts == 0:
        return jsonify({'error': 'No shifts available. Please add shifts first.'}), 400

    # Load DB objects (all shifts for scheduling)
    session = SessionLocal()
    try:
        db_workers = session.query(WorkerModel).filter(WorkerModel.business_id == bid).all()
        db_shifts = session.query(ShiftModel).filter(ShiftModel.business_id == bid).all()
        db_interests = session.query(ShiftInterestModel).filter(ShiftInterestModel.business_id == bid).all()
    finally:
        session.close()

    try:
        # Map shift_id -> set(worker_id) for interest scoping
        interest_map = {}
        for i in db_interests:
            try:
                sid = int(getattr(i, 'shift_id'))
                wid = int(getattr(i, 'worker_id'))
            except Exception:
                continue
            interest_map.setdefault(sid, set()).add(wid)

        # Build shifts
        shifts_list = []
        shift_allowed_map = {}
        for dbs in db_shifts:
            req_sk = []
            rs = _safe_json_loads(getattr(dbs, 'required_skills_json', '[]'), [])
            for r in rs:
                if isinstance(r, dict):
                    lvl = SkillLevel(r.get('level', SkillLevel.INTERMEDIATE.value))
                    req_sk.append(Skill(name=str(r.get('name') or ''), level=lvl))
                else:
                    req_sk.append(Skill(name=str(r), level=SkillLevel.INTERMEDIATE))

            recurring = bool(getattr(dbs, 'recurring_weekly', False))
            weekdays = list(_safe_json_loads(getattr(dbs, 'weekdays_json', '[]'), []))

            if recurring and weekdays:
                base_id = int(dbs.id)  # type: ignore[arg-type]
                today = datetime.now().date()
                for offset in range(0, 7):
                    d = today + timedelta(days=offset)
                    if d.weekday() in [int(x) for x in weekdays]:
                        new_id = base_id * 100 + offset + 1
                        shift_allowed_map[new_id] = set(interest_map.get(base_id, set()))
                        if bid is not None:
                            shifts_list.append(Shift(
                                id=new_id,
                                business_id=bid,
                                date=d.isoformat(),
                                start_time=str(dbs.start_time),
                                end_time=str(dbs.end_time),
                                required_skills=req_sk,
                                workers_required=int(dbs.workers_required),  # type: ignore[arg-type]
                                is_weekend=bool(dbs.is_weekend),
                            ))
            else:
                if bid is not None:
                    shifts_list.append(Shift(
                        id=int(dbs.id),  # type: ignore[arg-type]
                        business_id=bid,
                        date=str(dbs.date),
                        start_time=str(dbs.start_time),
                        end_time=str(dbs.end_time),
                        required_skills=req_sk,
                        workers_required=int(dbs.workers_required),  # type: ignore[arg-type]
                        is_weekend=bool(dbs.is_weekend),
                    ))
                base_id = int(getattr(dbs, 'id'))
                shift_allowed_map[base_id] = set(interest_map.get(base_id, set()))

        # Build workers
        shift_dates = sorted({s.date for s in shifts_list})
        workers_list = []

        def _is_shift_covered_by_availability(avails, date_str, shift_start, shift_end):
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
            except Exception:
                return False
            wday = dt.weekday()
            for a in avails:
                days = a.get('days') if isinstance(a, dict) else None
                start = a.get('start') if isinstance(a, dict) else None
                end = a.get('end') if isinstance(a, dict) else None
                if days is None or start is None or end is None:
                    continue
                try:
                    dd = [int(x) for x in days]
                except Exception:
                    dd = []
                if wday in dd and start <= shift_start and shift_end <= end:
                    return True
            return False

        for dbw in db_workers:
            skills = []
            sj = _safe_json_loads(getattr(dbw, 'skills_json', '[]'), [])
            for s in sj:
                if isinstance(s, dict):
                    lvl = SkillLevel(s.get('level', SkillLevel.INTERMEDIATE.value))
                    skills.append(Skill(name=s.get('name') or '', level=lvl))
                else:
                    skills.append(Skill(name=str(s), level=SkillLevel.INTERMEDIATE))

            availability = list(_safe_json_loads(getattr(dbw, 'availability_json', '[]'), []))

            unavailable_dates = set()
            if availability:
                for sd in shift_dates:
                    shifts_on_date = [sh for sh in shifts_list if sh.date == sd]
                    all_covered = True
                    for sh in shifts_on_date:
                        if not _is_shift_covered_by_availability(availability, sd, sh.start_time, sh.end_time):
                            all_covered = False
                            break
                    if not all_covered:
                        unavailable_dates.add(sd)
            else:
                unavailable_dates = set(_safe_json_loads(getattr(dbw, 'unavailable_dates_json', '[]'), []))

            prefs = WorkerPreference(
                worker_id=int(dbw.id),  # type: ignore[arg-type]
                unavailable_dates=set(unavailable_dates),
                max_shifts_per_week=5,
            )

            if bid is not None:
                workers_list.append(Worker(
                    id=int(dbw.id),  # type: ignore[arg-type]
                    business_id=bid,
                    name=str(dbw.name),
                    seniority_level=int(dbw.seniority_level),  # type: ignore[arg-type]
                    skills=skills,
                    hourly_rate=float(dbw.hourly_rate),  # type: ignore[arg-type]
                    preferences=prefs,
                ))

        # Determine scheduling period from valid shift dates
        parsed_dates = []
        for s in shifts_list:
            try:
                parsed_dates.append(datetime.strptime(s.date, '%Y-%m-%d').date())
            except Exception:
                continue
        if not parsed_dates:
            raise ValueError('No valid shift dates found. Please ensure shifts have YYYY-MM-DD dates.')

        scheduling_period_start = min(parsed_dates).isoformat()
        scheduling_period_end = max(parsed_dates).isoformat()

        if bid is not None:
            request_data = SchedulingRequest(
                business_id=bid,
                workers=workers_list,
                shifts=shifts_list,
                scheduling_period_start=scheduling_period_start,
                scheduling_period_end=scheduling_period_end,
                metadata={}
            )

            weights_data = (request.json or {}).get('weights', {})

            def _w(key, alt, default):
                return float(weights_data.get(key, weights_data.get(alt, default)))

            objective_weights = ObjectiveWeights(
                respect_time_off_requests=_w('respect_time_off_requests', 'time_off_request_weight', 10.0),
                reward_seniority=_w('reward_seniority', 'seniority_reward_weight', 5.0),
                balance_weekend_shifts=_w('balance_weekend_shifts', 'weekend_balance_weight', 8.0),
                reward_skill_matching=_w('reward_skill_matching', 'skill_matching_weight', 7.0),
                balance_workload=_w('balance_workload', 'workload_balance_weight', 6.0),
                minimize_compensation=_w('minimize_compensation', 'compensation_minimization_weight', 2.0),
                minimize_overstaffing=_w('minimize_overstaffing', 'overstaffing_penalty_weight', 3.0),
            )

            solver = ShiftSchedulingSolver(
                timeout_seconds=60,
                top_k=int(request.json.get('top_k', 3))
            )

            # If interests exist for a shift, restrict solver to interested workers; otherwise allow all
            worker_ids_set = {w.id for w in workers_list}
            allowed_pairs = []
            for sh in shifts_list:
                interested_workers = {w for w in shift_allowed_map.get(sh.id, set()) if w in worker_ids_set}
                if interested_workers:
                    allowed_pairs.extend([(wid, sh.id) for wid in interested_workers])
                else:
                    allowed_pairs.extend([(w.id, sh.id) for w in workers_list])

            request_data.metadata = {'allowed_pairs': allowed_pairs}

            response = solver.solve(request_data, objective_weights)
            solutions = response

            # If no complete solution found, generate partial solution with unassigned shifts for manual selection
            if not response.solutions:
                # Return partial solution: all shifts available for manual assignment
                partial_assignments = []
                assigned_shift_ids = set()
                
                # Add all shifts as unassigned so manager can manually select
                for shift in shifts_list:
                    partial_assignments.append(
                        ScheduleAssignment(
                            worker_id=None,
                            worker_name="Unassigned",
                            shift_id=shift.id,
                            shift_date=shift.date,
                            shift_start=shift.start_time,
                            shift_end=shift.end_time,
                            is_assigned=False
                        )
                    )
                
                # Create a single "blank" solution for manual editing
                partial_solution = SchedulingSolution(
                    rank=1,
                    objective_value=0,
                    assignments=partial_assignments,
                )
                
                session = SessionLocal()
                try:
                    new_schedule_db = ScheduleModel(
                        business_id=bid,
                        name=f"Schedule {scheduling_period_start} to {scheduling_period_end}",
                        start_date=scheduling_period_start,
                        end_date=scheduling_period_end,
                        status=ScheduleStatus.DRAFT.value,
                        assignments=json.dumps([a.dict() for a in partial_solution.assignments])
                    )
                    session.add(new_schedule_db)
                    session.commit()
                    session.refresh(new_schedule_db)
                    
                    # Build interested_by_shift mapping
                    interested_by_shift = {}
                    for shift_id, worker_ids in shift_allowed_map.items():
                        if worker_ids:
                            interested_by_shift[str(shift_id)] = list(worker_ids)
                    
                    # Build workers data
                    workers_data = [{'id': w.id, 'name': w.name} for w in workers_list]
                    
                    return jsonify(
                        schedule_id=new_schedule_db.id,
                        solutions=[partial_solution.dict()],
                        workers=workers_data,
                        interested_by_shift=interested_by_shift,
                        status=ScheduleStatus.DRAFT.value,
                        summary={
                            'total_workers': len(workers_list),
                            'total_shifts': len(shifts_list),
                            'message': 'No complete feasible solution found. All shifts available for manual assignment.'
                        }
                    )
                except Exception as e:
                    session.rollback()
                    logger.error(f"Error saving partial schedule: {e}")
                    return jsonify(error="Failed to save the schedule to the database."), 500
                finally:
                    session.close()

            # For simplicity, save the first solution found

            best_solution = response.solutions[0]

            session = SessionLocal()
            try:
                new_schedule_db = ScheduleModel(
                    business_id=bid,
                    name=f"Schedule {scheduling_period_start} to {scheduling_period_end}",
                    start_date=scheduling_period_start,
                    end_date=scheduling_period_end,
                    status=ScheduleStatus.DRAFT.value,
                    assignments=json.dumps([a.dict() for a in best_solution.assignments])
                )
                session.add(new_schedule_db)
                session.commit()
                session.refresh(new_schedule_db)
                
                # Build interested_by_shift mapping
                interested_by_shift = {}
                for shift_id, worker_ids in shift_allowed_map.items():
                    if worker_ids:
                        interested_by_shift[str(shift_id)] = list(worker_ids)
                
                # Build workers data
                workers_data = [{'id': w.id, 'name': w.name} for w in workers_list]
                
                return jsonify(
                    schedule_id=new_schedule_db.id,
                    solutions=[s.dict() for s in response.solutions],
                    workers=workers_data,
                    interested_by_shift=interested_by_shift,
                    status=ScheduleStatus.DRAFT.value,
                    summary={
                        'total_workers': len(workers_list),
                        'total_shifts': len(shifts_list)
                    }
                )
            except Exception as e:
                session.rollback()
                logger.error(f"Error saving new schedule: {e}")
                return jsonify(error="Failed to save the new schedule to the database."), 500
            finally:
                session.close()

    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/schedule/publish', methods=['POST'])  # type: ignore[misc]
def publish_schedule():
    """Publish a chosen schedule option and lock the period for workers.

    The frontend sends the currently selected solution (including any
    in-browser edits) so we can persist the final assignments.
    """
    bid, err, code = _require_business()
    if err:
        return err, code

    ok, err_resp, err_code = _require_role(UserRole.MANAGER.value)
    if not ok:
        return err_resp, err_code

    data = request.json or {}
    solution = data.get('solution') or {}
    assignments = solution.get('assignments') or data.get('assignments') or []

    if not assignments:
        return jsonify({'error': 'No assignments provided to publish.'}), 400

    # Infer scheduling period from assignment dates
    dates: list[datetime.date] = []
    for a in assignments:
        d = a.get('shift_date')
        if not d:
            continue
        try:
            dates.append(datetime.strptime(d, '%Y-%m-%d').date())
        except Exception:
            continue

    if not dates:
        return jsonify({'error': 'Assignments are missing valid shift_date values.'}), 400

    period_start = min(dates).isoformat()
    period_end = max(dates).isoformat()

    unresolved_comments = (
        data.get('unresolved_comments')
        or solution.get('unresolved_comments')
        or solution.get('_unresolvedComments')
        or {}
    )

    user_id = session.get('user_id')

    db = SessionLocal()
    try:
        # Replace any existing published schedule for this business
        db.query(PublishedScheduleModel).filter(PublishedScheduleModel.business_id == bid).delete()

        obj_val = solution.get('objective_value')
        pub = PublishedScheduleModel(
            business_id=bid,
            period_start=period_start,
            period_end=period_end,
            is_locked=True,
            created_at=datetime.utcnow().isoformat(),
            created_by_user_id=int(user_id) if user_id is not None else None,
            solution_rank=solution.get('rank'),
            objective_value=float(obj_val) if obj_val is not None else None,
            assignments_json=_safe_json_dumps(assignments, fallback="[]"),
            unresolved_comments_json=_safe_json_dumps(unresolved_comments, fallback="{}"),
        )
        db.add(pub)
        db.commit()

        return jsonify({
            'success': True,
            'message': f'Schedule published and locked for {period_start} to {period_end}.',
            'period_start': period_start,
            'period_end': period_end,
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


@app.route('/api/published-schedule', methods=['GET'])  # type: ignore[misc]
def get_published_schedule():
    """Return the latest published schedule for the current business, if any."""
    bid, err, code = _require_business()
    if err:
        return err, code

    db = SessionLocal()
    try:
        if bid is None:
            return jsonify({'published': False}), 200
        ps = _get_active_published_schedule(db, bid)
        if not ps:
            return jsonify({'published': False}), 200

        assignments = _safe_json_loads(getattr(ps, 'assignments_json', '[]'), [])
        unresolved = _safe_json_loads(getattr(ps, 'unresolved_comments_json', '{}'), {})

        return jsonify({
            'published': True,
            'is_locked': bool(getattr(ps, 'is_locked', True)),
            'period_start': ps.period_start,
            'period_end': ps.period_end,
            'solution_rank': getattr(ps, 'solution_rank', None),
            'objective_value': getattr(ps, 'objective_value', None),
            'assignments': assignments,
            'unresolved_comments': unresolved,
            'current_worker_id': _get_worker_id(),
        })
    finally:
        db.close()


@app.route('/api/published-schedule', methods=['DELETE'])  # type: ignore[misc]
def unpublish_schedule():
    """Delete/unpublish the currently published schedule."""
    bid, err, code = _require_business()
    if err:
        return err, code

    # Only managers can unpublish
    if session.get('user_role') != UserRole.MANAGER.value:
        return jsonify({'error': 'Only managers can unpublish schedules.'}), 403

    db = SessionLocal()
    try:
        if bid is None:
            return jsonify({'error': 'No business found'}), 400

        ps = _get_active_published_schedule(db, bid)
        if not ps:
            return jsonify({'error': 'No published schedule to unpublish.'}), 404

        db.delete(ps)
        db.commit()

        return jsonify({
            'success': True,
            'message': 'Schedule unpublished successfully.'
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({'error': f'Failed to unpublish schedule: {str(e)}'}), 500
    finally:
        db.close()


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Page not found'}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler."""
    # Log the exception for debugging
    logger.error(f"An unhandled exception occurred: {e}", exc_info=True)
    
    # For API requests, return JSON
    if request.path.startswith('/api/'):
        return jsonify(error="An unexpected error occurred. Please try again later."), 500
    
    # For other requests, you might want to render an error page
    return "An unexpected error occurred.", 500


# ============================================================================
# TEMPLATE GENERATORS (for quick testing without HTML files)
# ============================================================================

def generate_index_html():
    """Generate index.html if not exists."""
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    index_path = templates_dir / 'index.html'
    if not index_path.exists():
        index_path.write_text("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shift Scheduler</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <div class="container">
        <header>
            <h1>📅 Shift Scheduler</h1>
            <p>Easy scheduling for teams - no coding needed!</p>
        </header>
        
        <nav class="menu">
            <a href="/setup" class="btn btn-primary">➕ Add Workers & Shifts</a>
            <a href="/schedule" class="btn btn-success">🎯 Generate Schedule</a>
            <a href="#" class="btn btn-info" onclick="showStats()">📊 View Statistics</a>
        </nav>
        
        <section id="stats" class="stats-section"></section>
    </div>
    <script src="{{ url_for('static', filename='main.js') }}"></script>
</body>
</html>
        """)

# ============================================================================
# FOR TESTING PURPOSES ONLY
# ============================================================================
@app.route('/api/default-weights', methods=['GET'])
def get_default_weights():
    """Get default objective weights for the scheduling solver."""
    return jsonify({
        'respect_time_off_requests': 10.0,
        'reward_seniority': 5.0,
        'balance_weekend_shifts': 8.0,
        'reward_skill_matching': 7.0,
        'balance_workload': 6.0,
        'minimize_compensation': 2.0,
        'minimize_overstaffing': 3.0
    })


@app.route('/api/test/set_session', methods=['GET'])
def test_set_session():
    """
    FOR TESTING ONLY: Creates a test business/user and sets the session.
    """
    db = SessionLocal()
    try:
        biz = db.query(BusinessModel).filter(BusinessModel.unique_number == "TESTBIZ123").first()
        if not biz:
            biz = BusinessModel(name="Test Business", unique_number="TESTBIZ123")
            db.add(biz)
            db.commit()
            db.refresh(biz)

        user = db.query(UserModel).filter(UserModel.name == "Test Manager", UserModel.business_id == biz.id).first()
        if not user:
            user = UserModel(name="Test Manager", role=UserRole.MANAGER.value, business_id=biz.id)
            db.add(user)
            db.commit()
            db.refresh(user)
        
        _set_session(biz.id, biz.name, UserRole.MANAGER.value, user.id) # type: ignore
        return jsonify({"success": True, "message": "Test session set."})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for running the web interface."""
    import logging
    logging.basicConfig(level=logging.INFO)
    init_db()
    logging.info("Generating index.html...")
    generate_index_html()
    logging.info("Starting Flask app...")
    app.run(debug=False, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
