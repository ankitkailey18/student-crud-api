from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from auth import hash_password, verify_password, create_access_token, create_refresh_token, verify_token, create_verification_token
from sqlalchemy import asc, desc
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from starlette.requests import Request
import logging
from email_utils import send_email
import re
import os
import json
from datetime import date


logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request, exc):
    logger.warning(f"Rate limit exceeded from IP: {request.client.host}")
    return JSONResponse(status_code=429, content={"detail": "Too many requests! Try again later."})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    blacklisted = db.query(models.BlacklistedToken).filter(models.BlacklistedToken.token == token).first()
    if blacklisted:
        raise HTTPException(status_code=401, detail="Token has been blacklisted!")
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token!")
    username = payload.get("sub")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found!")
    return user

@app.get("/", response_class=HTMLResponse)
def serve_home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, username: str, password: str, email: str, major: str = None, year: str = None, phone: str = None, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken!")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters!")
    if not any(char.isdigit() for char in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number!")
    email = email.strip()
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format!")
    hashed = hash_password(password)
    exist = db.query(models.User).filter(models.User.email == email).first()
    if exist:
        raise HTTPException(status_code=400, detail="Email already exists!")
    user = models.User(username=username, hashed_password=hashed, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    last = db.query(models.Student).order_by(models.Student.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    banner_id = f"STU-{now.year}-{next_num:04d}"
    student = models.Student(name=username, grade=0, user_id=user.id, banner_id=banner_id, major=major, year=year, phone=phone, created_at=now)
    db.add(student)
    db.commit()
    db.refresh(student)
    verification_token = create_verification_token(data={"sub": username})
    await send_email(
        to_email=email,
        subject="Verify your EduManager account",
        body=f"Hi {username},\n\nWelcome to EduManager! Please verify your account by clicking the link below:\n\n<a href='{os.getenv('FRONTEND_URL')}/verify?token={verification_token}'>Click here to verify</a>\n\nThis link will expire in 24 hours.\n\nIf you did not create this account, please ignore this email.\n\nThanks,\nThe EduManager Team")
    logger.info(f"New user registered: {username} ({banner_id})")
    return {"message": "User registered! Verification email sent.", "username": user.username}

@app.get("/verify")
def verify_email(token: str, db: Session = Depends(get_db)):
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token!")
    username = payload.get("sub")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found!")
    user.is_verified = 1
    db.commit()
    logger.info(f"User verified: {username}")
    return {"message": f"{username} is now verified!"}

@app.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, email: str, db: Session = Depends(get_db)):
    email = email.strip()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No user associated with this email!")
    reset_token = create_verification_token(data={"sub": user.username})
    await send_email(
        to_email=email,
        subject="Reset your EduManager password",
        body=f"Hi {user.username},\n\nWe received a request to reset your password. Click the link below to set a new password:\n\n<a href='{os.getenv('FRONTEND_URL')}/reset-password?token={reset_token}'>Click here to reset your password</a>\n\nThis link will expire in 24 hours.\n\nIf you did not request this, please ignore this email.\n\nThanks,\nThe EduManager Team")
    logger.info(f"Password reset requested for: {user.username}")
    return {"message": "Password reset email sent!"}

@app.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=400, detail="Invalid or expired token!")
    username = payload.get("sub")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found!")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters!")
    if not any(char.isdigit() for char in new_password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number!")
    user.hashed_password = hash_password(new_password)
    db.commit()
    logger.info(f"Password reset successful for: {username}")
    return {"message": "Password reset successful!"}

@app.post("/login")
@limiter.limit("5/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for: {form_data.username}")
        raise HTTPException(status_code=401, detail="Invalid username or password!")
    if user.is_verified == 0:
        raise HTTPException(status_code=403, detail="Please verify your email first!")
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@app.post("/refresh")
def refresh(token: str, db: Session = Depends(get_db)):
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token!")
    username = payload.get("sub")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found!")
    new_access_token = create_access_token(data={"sub": user.username})
    return {"access_token": new_access_token, "token_type": "bearer"}

@app.get("/me")
def get_me(user = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "role": user.role}

@app.post("/logout")
def logout(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    blacklisted = models.BlacklistedToken(token=token)
    db.add(blacklisted)
    db.commit()
    logger.info("User logged out")
    return {"message": "Logged out successfully!"}

@app.put("/users/{user_id}/role")
def change_role(user_id: int, new_role: str, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can change roles!")
    new_role = new_role.lower()
    if new_role not in ["admin", "teacher", "student"]:
        raise HTTPException(status_code=400, detail="Role must be admin, teacher, or student!")
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found!")
    target_user.role = new_role
    db.commit()
    db.refresh(target_user)
    logger.info(f"Admin {user.username} changed {target_user.username}'s role to {new_role}")
    return {"message": f"{target_user.username} is now a {new_role}!", "username": target_user.username, "role": target_user.role}

@app.get("/users")
def get_all_users(role: str = None, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view all users!")
    query = db.query(models.User)
    if role is not None:
        query = query.filter(models.User.role == role.lower())
    users = query.all()
    result = []
    for u in users:
        result.append({
            "user_id": u.id,
            "username": u.username,
            "role": u.role
        })
    return result

@app.put("/change-password")
def change_password(current_password: str, new_password: str, user = Depends(get_current_user), db: Session = Depends(get_db)):
    from auth import pwd_context
    if not pwd_context.verify(current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect!")
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters!")
    user.hashed_password = pwd_context.hash(new_password)
    db.commit()
    logger.info(f"{user.username} changed their password")
    return {"message": "Password changed successfully!"}

@app.post("/logout-all")
def logout_all(user = Depends(get_current_user), db: Session = Depends(get_db)):
    from auth import pwd_context
    import secrets
    dummy = pwd_context.hash(secrets.token_hex(16))
    user.hashed_password = user.hashed_password
    db.commit()
    logger.info(f"{user.username} logged out from all devices")
    return {"message": "Signed out from all devices!"}

@app.post("/students")
def add_student(name: str, grade: int, major: str = None, year: str = None, phone: str = None, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only admins and teachers can add students!")
    if name.strip() == "":
        raise HTTPException(status_code=400, detail="Name cannot be empty!")
    if grade < 0 or grade > 100:
        raise HTTPException(status_code=400, detail="Grade must be between 0 and 100!")
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    last = db.query(models.Student).order_by(models.Student.id.desc()).first()
    next_num = (last.id + 1) if last else 1
    banner_id = f"STU-{now.year}-{next_num:04d}"
    student = models.Student(name=name, grade=grade, banner_id=banner_id, major=major, year=year, phone=phone, created_at=now)
    db.add(student)
    db.commit()
    db.refresh(student)
    logger.info(f"{user.username} added student: {name} ({banner_id})")
    return student

@app.get("/students")
def get_all_students(page: int = 1, limit: int = 10, search: str = None, sort: str = None, order: str = "asc", user = Depends(get_current_user), db: Session = Depends(get_db)):
    skip = (page - 1) * limit
    if user.role in ["admin", "teacher"]:
        query = db.query(models.Student)
    else:
        query = db.query(models.Student).filter(models.Student.user_id == user.id)
    if search is not None:
        query = query.filter(models.Student.name.contains(search))
    if sort is not None:
        sort = sort.lower()
        order = order.lower()
        if sort == "grade":
            sort_column = models.Student.grade
        elif sort == "name":
            sort_column = models.Student.name
        else:
            sort_column = models.Student.id
        if order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    return query.offset(skip).limit(limit).all()

@app.get("/students/{student_id}")
def get_student(student_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found!")
    if user.role == "student" and student.user_id != user.id:
        raise HTTPException(status_code=403, detail="You can only view your own data!")
    enrolled_courses = []
    for e in student.enrollments:
        enrolled_courses.append({
            "course_id": e.course.id,
            "course_name": e.course.course_name,
            "teacher": e.course.teacher.username
        })
    email = student.user.email if student.user else None
    is_verified = student.user.is_verified if student.user else 0
    role = student.user.role if student.user else "student"
    return {
        "id": student.id,
        "name": student.name,
        "banner_id": student.banner_id,
        "major": student.major,
        "year": student.year,
        "phone": student.phone,
        "email": email,
        "is_verified": is_verified,
        "role": role,
        "created_at": student.created_at.isoformat() if student.created_at else None,
        "enrolled_courses": enrolled_courses
    }

@app.put("/students/{student_id}")
def update_student(student_id: int, name: str, grade: int, major: str = None, year: str = None, phone: str = None, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only admins and teachers can update students!")
    if not name or name.strip() == "":
        raise HTTPException(status_code=400, detail="Name cannot be empty!")
    if grade < 0 or grade > 100:
        raise HTTPException(status_code=400, detail="Grade must be between 0 and 100!")
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found!")
    student.name = name
    student.grade = grade
    if major is not None: student.major = major
    if year is not None: student.year = year
    if phone is not None: student.phone = phone
    db.commit()
    db.refresh(student)
    logger.info(f"{user.username} updated student {student_id}: name={name}")
    return student

@app.delete("/students/{student_id}")
def delete_student(student_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete students!")
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found!")
    db.delete(student)
    db.commit()
    logger.info(f"Admin {user.username} deleted student {student_id}")
    return {"message": "Student deleted!"}

@app.post("/courses")
def create_course(course_name: str, teacher_id: int, description: str = None, course_code: str = None, color: str = None, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create courses!")
    teacher = db.query(models.User).filter(models.User.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found!")
    if teacher.role != "teacher":
        raise HTTPException(status_code=400, detail="This user is not a teacher!")
    course = models.Course(course_name=course_name, teacher_id=teacher_id, description=description, course_code=course_code or "", color=color or "#3498db")
    db.add(course)
    db.commit()
    db.refresh(course)
    logger.info(f"Admin {user.username} created course: {course_name}, teacher: {teacher.username}")
    return {"message": "Course created!", "course_name": course.course_name, "course_id": course.id, "teacher": teacher.username}

@app.get("/courses")
def get_all_courses(user = Depends(get_current_user), db: Session = Depends(get_db)):
    courses = db.query(models.Course).all()
    result = []
    for course in courses:
        result.append({
            "course_id": course.id,
            "course_name": course.course_name,
            "course_code": course.course_code or "",
            "description": course.description or "",
            "color": course.color or "#3498db",
            "teacher": course.teacher.username
        })
    return result

@app.get("/my-courses")
def get_my_courses(user = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found!")
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.student_id == student.id).all()
    my_courses = []
    for enrollment in enrollments:
        my_courses.append({
            "course_id": enrollment.course.id,
            "course_name": enrollment.course.course_name,
            "teacher": enrollment.course.teacher.username
        })
    return {"student": student.name, "courses": my_courses}

@app.post("/courses/{course_id}/enroll")
def enroll_student(course_id: int, student_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only admins and teachers can enroll students!")
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found!")
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found!")
    existing = db.query(models.Enrollment).filter(models.Enrollment.student_id == student_id, models.Enrollment.course_id == course_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Student is already enrolled in this course!")
    enrollment = models.Enrollment(student_id=student_id, course_id=course_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    logger.info(f"{user.username} enrolled {student.name} in {course.course_name}")
    return {"message": f"{student.name} enrolled in {course.course_name}!"}

@app.post("/courses/{course_id}/self-enroll")
def self_enroll(course_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found! Ask an admin to create your student profile.")
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found!")
    existing = db.query(models.Enrollment).filter(models.Enrollment.student_id == student.id, models.Enrollment.course_id == course_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="You are already enrolled in this course!")
    enrollment = models.Enrollment(student_id=student.id, course_id=course_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    logger.info(f"{user.username} self-enrolled in {course.course_name}")
    return {"message": f"Successfully enrolled in {course.course_name}!"}

@app.delete("/courses/{course_id}/self-unenroll")
def self_unenroll(course_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found!")
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.student_id == student.id, models.Enrollment.course_id == course_id).first()
    if not enrollment:
        raise HTTPException(status_code=400, detail="You are not enrolled in this course!")
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    db.delete(enrollment)
    db.commit()
    logger.info(f"{user.username} unenrolled from {course.course_name}")
    return {"message": f"Successfully unenrolled from {course.course_name}!"}

@app.get("/my-profile")
def get_my_profile(user = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
    enrolled_courses = []
    if student:
        for e in student.enrollments:
            enrolled_courses.append({
                "course_id": e.course.id,
                "course_name": e.course.course_name,
                "teacher": e.course.teacher.username
            })
    return {
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_verified": user.is_verified,
        "student_id": student.id if student else None,
        "banner_id": student.banner_id if student else None,
        "major": student.major if student else None,
        "year": student.year if student else None,
        "phone": student.phone if student else None,
        "created_at": student.created_at.isoformat() if student and student.created_at else None,
        "enrolled_courses": enrolled_courses
    }

@app.put("/my-profile")
def update_my_profile(major: str = None, year: str = None, phone: str = None, user = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found!")
    if major is not None: student.major = major
    if year is not None: student.year = year
    if phone is not None: student.phone = phone
    db.commit()
    db.refresh(student)
    logger.info(f"{user.username} updated their profile")
    return {"message": "Profile updated!"}

@app.get("/courses/{course_id}/students")
def get_course_students(course_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found!")
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.course_id == course_id).all()
    classmates = []
    for enrollment in enrollments:
        classmates.append({
            "student_id": enrollment.student.id,
            "name": enrollment.student.name
        })
    return {"course": course.course_name, "students": classmates}

@app.post("/courses/{course_id}/assignments")
def create_assignment(course_id: int, title: str, description: str, max_points: int, due_date: str, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only admins and teachers can create assignments!")
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found!")
    assignment = models.Assignment(title=title, description=description, max_points=max_points, due_date=date.fromisoformat(due_date), course_id=course_id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    logger.info(f"{user.username} created assignment: {title} in {course.course_name}")
    return {"message": "Assignment created!", "title": assignment.title, "max_points": assignment.max_points, "due_date": str(assignment.due_date), "course": course.course_name}

@app.get("/courses/{course_id}/assignments")
def get_assignments(course_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found!")
    assignments = db.query(models.Assignment).filter(models.Assignment.course_id == course_id).all()
    result = []
    for a in assignments:
        result.append({
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "max_points": a.max_points,
            "due_date": str(a.due_date)
        })
    return {"course": course.course_name, "assignments": result}

@app.post("/courses/{course_id}/attendance/bulk")
async def bulk_attendance(course_id: int, request: Request, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only admins and teachers can mark attendance!")
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found!")
    try:
        body = await request.json()
        attendance_date = body.get("attendance_date")
        entries = body.get("records", [])
    except:
        raise HTTPException(status_code=400, detail="Invalid request body!")
    att_date = date.fromisoformat(attendance_date)
    count = 0
    for entry in entries:
        sid = entry.get("student_id")
        status = entry.get("status", "present").lower()
        if status not in ["present", "absent", "late"]:
            continue
        student = db.query(models.Student).filter(models.Student.id == sid).first()
        if not student:
            continue
        existing = db.query(models.Attendance).filter(
            models.Attendance.student_id == sid,
            models.Attendance.course_id == course_id,
            models.Attendance.date == att_date
        ).first()
        if existing:
            existing.status = status
        else:
            attendance = models.Attendance(student_id=sid, course_id=course_id, date=att_date, status=status)
            db.add(attendance)
        count += 1
    db.commit()
    logger.info(f"{user.username} marked bulk attendance for {course.course_name}: {count} records")
    return {"message": f"Attendance recorded for {count} students!", "course": course.course_name, "date": str(att_date)}

@app.post("/courses/{course_id}/attendance")
def mark_attendance(course_id: int, student_id: int, status: str, attendance_date: str, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only admins and teachers can mark attendance!")
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found!")
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found!")
    status = status.lower()
    if status not in ["present", "absent", "late"]:
        raise HTTPException(status_code=400, detail="Status must be present, absent, or late!")
    attendance = models.Attendance(student_id=student_id, course_id=course_id, date=date.fromisoformat(attendance_date), status=status)
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    logger.info(f"{user.username} marked {student.name} as {status} in {course.course_name}")
    return {"message": f"{student.name} marked as {status}!", "student": student.name, "course": course.course_name, "date": str(attendance.date), "status": attendance.status}

@app.get("/courses/{course_id}/attendance")
def get_attendance(course_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found!")
    if user.role in ["admin", "teacher"]:
        records = db.query(models.Attendance).filter(models.Attendance.course_id == course_id).all()
    else:
        student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found!")
        records = db.query(models.Attendance).filter(models.Attendance.course_id == course_id, models.Attendance.student_id == student.id).all()
    result = []
    for r in records:
        result.append({
            "student_id": r.student_id,
            "student_name": r.student.name,
            "date": str(r.date),
            "status": r.status
        })
    return {"course": course.course_name, "attendance": result}

@app.post("/assignments/{assignment_id}/grade")
def grade_student(assignment_id: int, student_id: int, points_earned: float, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only admins and teachers can grade students!")
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found!")
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found!")
    if points_earned < 0 or points_earned > assignment.max_points:
        raise HTTPException(status_code=400, detail=f"Points must be between 0 and {assignment.max_points}!")
    submission = models.Submission(student_id=student_id, assignment_id=assignment_id, points_earned=points_earned)
    db.add(submission)
    db.commit()
    db.refresh(submission)
    logger.info(f"{user.username} graded {student.name}: {points_earned}/{assignment.max_points} on {assignment.title}")
    return {"message": "Grade recorded!", "student": student.name, "assignment": assignment.title, "points_earned": submission.points_earned, "max_points": assignment.max_points}

@app.get("/courses/{course_id}/grades")
def get_course_grades(course_id: int, student_id: int = None, user = Depends(get_current_user), db: Session = Depends(get_db)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found!")
    assignments = db.query(models.Assignment).filter(models.Assignment.course_id == course_id).all()
    if not assignments:
        return {"course": course.course_name, "grades": [], "average": 0}
    if user.role == "student":
        student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found!")
        student_id = student.id
    if not student_id:
        raise HTTPException(status_code=400, detail="student_id is required for admin/teacher!")
    grades = []
    total_earned = 0
    total_possible = 0
    for a in assignments:
        submission = db.query(models.Submission).filter(models.Submission.assignment_id == a.id, models.Submission.student_id == student_id).first()
        grades.append({
            "assignment": a.title,
            "max_points": a.max_points,
            "points_earned": submission.points_earned if submission else None,
            "due_date": str(a.due_date)
        })
        if submission:
            total_earned += submission.points_earned
            total_possible += a.max_points
    average = round((total_earned / total_possible) * 100, 2) if total_possible > 0 else 0
    return {"course": course.course_name, "grades": grades, "average": average}

# ── SUBMISSIONS ──────────────────────────────────────────────────

@app.post("/assignments/{assignment_id}/submit")
async def submit_assignment(assignment_id: int, request: Request, user = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found!")
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found!")
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.student_id == student.id, models.Enrollment.course_id == assignment.course_id).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="You are not enrolled in this course!")
    existing = db.query(models.Submission).filter(models.Submission.student_id == student.id, models.Submission.assignment_id == assignment_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already submitted this assignment!")
    body = await request.json()
    content = body.get("content", "")
    file_name = body.get("file_name", "")
    file_data = body.get("file_data", "")
    file_path = ""
    if file_data and file_name:
        import base64, os
        upload_dir = "uploads/submissions"
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"{student.id}_{assignment_id}_{file_name}"
        file_path = os.path.join(upload_dir, safe_name)
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(file_data))
    from datetime import datetime, timezone
    submission = models.Submission(student_id=student.id, assignment_id=assignment_id, content=content, file_name=file_name if file_data else None, file_path=file_path if file_data else None, status="submitted", submitted_at=datetime.now(timezone.utc))
    db.add(submission)
    db.commit()
    db.refresh(submission)
    logger.info(f"{user.username} submitted assignment {assignment.title}")
    return {"message": f"Assignment '{assignment.title}' submitted!"}

@app.get("/assignments/{assignment_id}/submissions")
def get_assignment_submissions(assignment_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only admins and teachers can view submissions!")
    assignment = db.query(models.Assignment).filter(models.Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found!")
    submissions = db.query(models.Submission).filter(models.Submission.assignment_id == assignment_id).all()
    return {"assignment": assignment.title, "submissions": [{
        "id": s.id,
        "student_id": s.student_id,
        "student_name": s.student.name,
        "content": s.content,
        "file_name": s.file_name,
        "status": s.status,
        "points_earned": s.points_earned,
        "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None
    } for s in submissions]}

@app.get("/assignments/{assignment_id}/my-submission")
def get_my_submission(assignment_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found!")
    submission = db.query(models.Submission).filter(models.Submission.student_id == student.id, models.Submission.assignment_id == assignment_id).first()
    if not submission:
        return {"submitted": False}
    return {
        "submitted": True,
        "content": submission.content,
        "file_name": submission.file_name,
        "status": submission.status,
        "points_earned": submission.points_earned,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None
    }

# ── ANNOUNCEMENTS ──────────────────────────────────────────────────

@app.post("/courses/{course_id}/announcements")
def create_announcement(course_id: int, title: str, body: str, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only admins and teachers can post announcements!")
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found!")
    from datetime import datetime, timezone
    ann = models.Announcement(title=title, body=body, course_id=course_id, author_id=user.id, created_at=datetime.now(timezone.utc))
    db.add(ann)
    db.commit()
    db.refresh(ann)
    logger.info(f"{user.username} posted announcement in {course.course_name}: {title}")
    return {"message": "Announcement posted!", "id": ann.id}

@app.get("/courses/{course_id}/announcements")
def get_course_announcements(course_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found!")
    anns = db.query(models.Announcement).filter(models.Announcement.course_id == course_id).order_by(models.Announcement.created_at.desc()).all()
    return [{"id": a.id, "title": a.title, "body": a.body, "author": a.author.username, "created_at": a.created_at.isoformat() if a.created_at else None} for a in anns]

@app.get("/announcements/feed")
def get_announcement_feed(user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role in ["admin"]:
        anns = db.query(models.Announcement).order_by(models.Announcement.created_at.desc()).limit(20).all()
    elif user.role == "teacher":
        teacher_courses = db.query(models.Course).filter(models.Course.teacher_id == user.id).all()
        course_ids = [c.id for c in teacher_courses]
        if not course_ids:
            return []
        anns = db.query(models.Announcement).filter(models.Announcement.course_id.in_(course_ids)).order_by(models.Announcement.created_at.desc()).limit(20).all()
    else:
        student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
        if not student:
            return []
        enrolled_ids = [e.course_id for e in student.enrollments]
        if not enrolled_ids:
            return []
        anns = db.query(models.Announcement).filter(models.Announcement.course_id.in_(enrolled_ids)).order_by(models.Announcement.created_at.desc()).limit(20).all()
    return [{"id": a.id, "title": a.title, "body": a.body, "author": a.author.username, "course": a.course.course_name, "created_at": a.created_at.isoformat() if a.created_at else None} for a in anns]

@app.delete("/announcements/{announcement_id}")
def delete_announcement(announcement_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only admins and teachers can delete announcements!")
    ann = db.query(models.Announcement).filter(models.Announcement.id == announcement_id).first()
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found!")
    db.delete(ann)
    db.commit()
    return {"message": "Announcement deleted!"}