from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from .config import settings
from .database import engine, get_db
from .models import Base
from .api import auth, student_schedule, file_upload, pair_management, schedule_generation
from .core.permissions import get_current_user
from .models.user import User
from .models.student_schedule import StudentSchedule, StudentPair, ScheduleAssignment, OperationSchedule, ScheduleWeekSchedule
from typing import Optional

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CNU Dental Clinic Scheduler",
    description="CNU Dental Clinic Scheduling System",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(student_schedule.router)
app.include_router(file_upload.router)
app.include_router(pair_management.router)
app.include_router(schedule_generation.router)


# Helper function to get current user from session
async def get_current_user_from_session(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get current user from session token"""
    try:
        # Check for token in cookies or Authorization header
        token = request.cookies.get("access_token")
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            return None
            
        # Verify token and get user
        from .core.security import verify_token
        username = verify_token(token)
        if not username:
            return None
            
        user = db.query(User).filter(User.username == username).first()
        return user if user and user.is_active else None
    except:
        return None

# HTML Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, current_user: Optional[User] = Depends(get_current_user_from_session)):
    if current_user:
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})

@app.post("/login")
async def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle login form submission"""
    from .core.security import verify_password
    
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Invalid username or password"
        })
    
    if not user.is_active:
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Account is deactivated"
        })
    
    # Create access token
    from .core.security import create_access_token
    from datetime import timedelta
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(hours=24))
    
    # Redirect to dashboard with token in cookie
    response = RedirectResponse(url="/dashboard")
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=86400)
    return response

@app.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    error: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    return templates.TemplateResponse("register.html", {"request": request, "error": error, "current_user": current_user})

@app.post("/register")
async def register_form(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("student"),
    first_name: str = Form(""),
    last_name: str = Form(""),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """Handle registration form submission"""
    from .core.security import get_password_hash
    
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    
    if existing_user:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Username or email already exists"
        })
    
    # Determine role: only admins may set non-student roles
    final_role = role
    is_admin = bool(current_user and current_user.role == 'admin')
    if not is_admin:
        # Fallback: try to read token directly from cookie if dependency failed
        try:
            token = request.cookies.get("access_token")
            if token:
                from .core.security import verify_token
                username_from_token = verify_token(token)
                if username_from_token:
                    user_check = db.query(User).filter(User.username == username_from_token).first()
                    if user_check and user_check.role == 'admin':
                        is_admin = True
        except Exception:
            pass
    if not is_admin:
        final_role = 'student'

    # Create new user
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        email=email,
        password_hash=hashed_password,
        role=final_role,
        first_name=first_name,
        last_name=last_name,
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Redirect to login with success message
    return RedirectResponse(url="/login")

@app.get("/dashboard", response_class=HTMLResponse)
@app.post("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request, 
    current_user: Optional[User] = Depends(get_current_user_from_session),
    db: Session = Depends(get_db)
):
    if not current_user:
        return RedirectResponse(url="/login")
    
    # Get stats based on user role
    stats = {}
    
    if current_user.role == 'admin':
        stats = {
            'total_students': db.query(StudentSchedule).count(),
            'total_pairs': db.query(StudentPair).count(),
            'total_operations': db.query(OperationSchedule).count()
        }
    elif current_user.role in ['faculty', 'front_desk']:
        stats = {
            'total_students': db.query(StudentSchedule).count(),
            'total_pairs': db.query(StudentPair).count(),
            'assigned_slots': db.query(ScheduleAssignment).filter(ScheduleAssignment.status == 'assigned').count(),
            'empty_slots': db.query(ScheduleAssignment).filter(ScheduleAssignment.status == 'empty').count()
        }
        # Get this week's assignments (preview list) with related data for non-front desk
        from sqlalchemy.orm import selectinload
        this_week_assignments = db.query(ScheduleAssignment).options(
            selectinload(ScheduleAssignment.operation),
            selectinload(ScheduleAssignment.pair).selectinload(StudentPair.student1),
            selectinload(ScheduleAssignment.pair).selectinload(StudentPair.student2)
        ).limit(200).all()
        # Sort by chair number then time slot for consistent display
        time_order = ['8:00–9:20', '9:20–10:40', '10:40–12:00', '13:00–14:20', '14:20–15:40', '15:40–17:00']
        def _chair_num(chair: str) -> int:
            import re
            m = re.search(r"(\d+)", chair or '')
            return int(m.group(1)) if m else 0
        def _time_index(t: str) -> int:
            try:
                return time_order.index(t)
            except ValueError:
                return len(time_order)
        this_week_assignments = sorted(
            this_week_assignments,
            key=lambda a: (_chair_num(a.chair), _time_index(a.time_slot))
        )

        # For front desk: build a spreadsheet-style grid Monday–Friday with only operation+patient
        if current_user.role == 'front_desk':
            # Pick a week to display: latest created week if exists, else all
            week = db.query(ScheduleWeekSchedule).order_by(ScheduleWeekSchedule.id.asc()).first()
            fd_week_label = week.week_label if week else None

            assignments_q = db.query(ScheduleAssignment).filter(
                ScheduleAssignment.week_id == week.id
            ).all() if week else []

            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            # Collect row keys as (time_slot, chair)
            row_keys_set = set()
            for a in assignments_q:
                row_keys_set.add((a.time_slot or '', a.chair or ''))
            # Sort rows by chair number then time order to match schedule page
            time_order = ['8:00–9:20', '9:20–10:40', '10:40–12:00', '13:00–14:20', '14:20–15:40', '15:40–17:00']
            def _chair_num(chair: str) -> int:
                import re
                m = re.search(r"(\d+)", chair)
                return int(m.group(1)) if m else 0
            def _time_index(ts: str) -> int:
                try:
                    return time_order.index(ts)
                except ValueError:
                    return len(time_order)
            row_keys = sorted(list(row_keys_set), key=lambda rc: (_chair_num(rc[1]), _time_index(rc[0])))

            # Build grid mapping day -> {(time, chair) -> cell_text}
            fd_grid = {d: {} for d in days}
            for a in assignments_q:
                cell = ''
                if a.operation and a.operation.name:
                    cell += a.operation.name
                if a.patient_name:
                    cell += (" - " if cell else '') + a.patient_name
                if a.patient_id:
                    cell += f" ({a.patient_id})"
                fd_grid.get(a.day, {})[(a.time_slot or '', a.chair or '')] = cell

            context_extra = {
                'fd_week_label': fd_week_label,
                'fd_grid_days': days,
                'fd_grid_rows': row_keys,
                'fd_grid': fd_grid
            }
        else:
            context_extra = {}
    elif current_user.role == 'student':
        # Get student's assignments
        student = db.query(StudentSchedule).filter(StudentSchedule.student_id == current_user.username).first()
        if student:
            # Find pairs where this student is either student1 or student2
            pairs = db.query(StudentPair).filter(
                (StudentPair.student1_id == student.id) | 
                (StudentPair.student2_id == student.id)
            ).all()
            
            # Derive student's primary pair and partner name for header display
            student_pair_id_value = None
            student_partner_name_value = None
            if pairs:
                primary_pair = pairs[0]
                student_pair_id_value = primary_pair.pair_id
                try:
                    if primary_pair.student1 and primary_pair.student1.student_id == current_user.username:
                        if primary_pair.student2:
                            student_partner_name_value = f"{primary_pair.student2.first_name} {primary_pair.student2.last_name}"
                    else:
                        if primary_pair.student1:
                            student_partner_name_value = f"{primary_pair.student1.first_name} {primary_pair.student1.last_name}"
                except Exception:
                    pass
            
            if pairs:
                pair_ids = [pair.id for pair in pairs]
                student_assignments = db.query(ScheduleAssignment).filter(
                    ScheduleAssignment.pair_id.in_(pair_ids)
                ).all()
            else:
                student_assignments = []
        else:
            student_assignments = []
        
        stats = {
            'total_assignments': len(student_assignments),
            'completed_assignments': len([a for a in student_assignments if a.status == 'completed']),
            'pending_assignments': len([a for a in student_assignments if a.status == 'assigned'])
        }
    
    context = {
        "request": request,
        "current_user": current_user,
        "stats": stats
    }
    
    if current_user.role in ['faculty', 'front_desk']:
        context["this_week_assignments"] = this_week_assignments
        if current_user.role == 'front_desk':
            context.update(context_extra)
    elif current_user.role == 'student':
        context["student_assignments"] = student_assignments
        context["student_pair_id"] = locals().get("student_pair_id_value")
        context["student_partner_name"] = locals().get("student_partner_name_value")
        
        # Create JSON data for JavaScript
        import json
        schedule_data_json = []
        print(f"DEBUG: Found {len(student_assignments)} student assignments")
        
        for assignment in student_assignments:
            # Determine partner name
            partner_name = None
            if assignment.pair:
                if assignment.pair.student1.student_id == current_user.username:
                    partner_name = f"{assignment.pair.student2.first_name} {assignment.pair.student2.last_name}"
                else:
                    partner_name = f"{assignment.pair.student1.first_name} {assignment.pair.student1.last_name}"
            
            schedule_data_json.append({
                "week": assignment.week.week_label if assignment.week else "Unknown",
                "day": assignment.day,
                "timeSlot": assignment.time_slot,
                "chair": assignment.chair,
                "operation": assignment.operation.name if assignment.operation else None,
                "patientName": assignment.patient_name,
                "patientId": assignment.patient_id,
                "partner": partner_name,
                "pairId": assignment.pair.pair_id if assignment.pair else None,
                "status": assignment.status
            })
        
        json_string = json.dumps(schedule_data_json)
        print(f"DEBUG: JSON string length: {len(json_string)}")
        context["schedule_data_json"] = json_string
    
    return templates.TemplateResponse("dashboard.html", context)

@app.get("/logout")
async def logout():
    """Handle logout"""
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="access_token")
    return response

@app.get("/files", response_class=HTMLResponse)
async def file_management_page(
    request: Request, 
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """File management page"""
    if not current_user:
        return RedirectResponse(url="/login")
    
    if current_user.role not in ['admin', 'faculty']:
        return RedirectResponse(url="/dashboard")
    
    return templates.TemplateResponse("file_management.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/staff/students", response_class=HTMLResponse)
async def staff_students_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """Faculty view for students (reuses file management/student tools)."""
    if not current_user:
        return RedirectResponse(url="/login")
    if current_user.role not in ['admin', 'faculty']:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("file_management.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/schedule", response_class=HTMLResponse)
async def schedule_display_page(
    request: Request, 
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """Schedule display page"""
    if not current_user:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse("schedule_display.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/operation-tracking", response_class=HTMLResponse)
async def operation_tracking_page(
    request: Request, 
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """Operation tracking page"""
    if not current_user:
        return RedirectResponse(url="/login")
    
    if current_user.role not in ['admin', 'faculty', 'front_desk']:
        return RedirectResponse(url="/dashboard")
    
    return templates.TemplateResponse("operation_tracking.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/reports", response_class=HTMLResponse)
async def reports_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """Placeholder reports page (coming soon)."""
    if not current_user:
        return RedirectResponse(url="/login")
    if current_user.role not in ['admin', 'faculty']:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """Admin settings page (UI options)."""
    if not current_user:
        return RedirectResponse(url="/login")
    if current_user.role != 'admin':
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("admin_settings.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """Admin user management page"""
    if not current_user:
        return RedirectResponse(url="/login")
    if current_user.role != 'admin':
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("user_management.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/admin/users/", response_class=HTMLResponse)
async def admin_users_page_slash(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """Alias with trailing slash to prevent 404 when visiting /admin/users/."""
    if not current_user:
        return RedirectResponse(url="/login")
    if current_user.role != 'admin':
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("user_management.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/admin/users/add", response_class=HTMLResponse)
async def admin_users_add_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """Admin add-user page alias to registration with admin context."""
    if not current_user:
        return RedirectResponse(url="/login")
    if current_user.role != 'admin':
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("register.html", {
        "request": request,
        "current_user": current_user,
        "is_admin_context": True
    })

@app.get("/patient-assignment", response_class=HTMLResponse)
async def patient_assignment_page(
    request: Request, 
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """Patient assignment page"""
    if not current_user:
        return RedirectResponse(url="/login")
    
    if current_user.role not in ['admin', 'faculty', 'front_desk']:
        return RedirectResponse(url="/dashboard")
    
    return templates.TemplateResponse("patient_assignment.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/admin/students", response_class=HTMLResponse)
async def admin_students_page(
    request: Request, 
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """Admin students management page"""
    if not current_user:
        return RedirectResponse(url="/login")
    
    if current_user.role != 'admin':
        return RedirectResponse(url="/dashboard")
    
    return templates.TemplateResponse("file_management.html", {
        "request": request,
        "current_user": current_user,
        "students_only": True
    })

@app.get("/admin/pairs", response_class=HTMLResponse)
async def admin_pairs_page(
    request: Request, 
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """Admin pairs management page"""
    if not current_user:
        return RedirectResponse(url="/login")
    
    if current_user.role != 'admin':
        return RedirectResponse(url="/dashboard")
    
    return templates.TemplateResponse("file_management.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/admin/schedule", response_class=HTMLResponse)
async def admin_schedule_page(
    request: Request, 
    current_user: Optional[User] = Depends(get_current_user_from_session)
):
    """Admin schedule management page"""
    if not current_user:
        return RedirectResponse(url="/login")
    
    if current_user.role != 'admin':
        return RedirectResponse(url="/dashboard")
    
    return templates.TemplateResponse("file_management.html", {
        "request": request,
        "current_user": current_user
    })

# API Routes (existing)
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "admin_routes": "loaded", "debug_upload": "enabled"}

@app.post("/api/test")
def test_endpoint():
    return {"message": "Test endpoint working"}
