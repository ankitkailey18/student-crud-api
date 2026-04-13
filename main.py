from fastapi.responses import HTMLResponse
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

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)
app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

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
async def register(request: Request, username: str, password: str, email: str, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already taken!")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters!")
    if not any(char.isdigit() for char in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number!")
    hashed = hash_password(password)
    exist = db.query(models.User).filter(models.User.email == email).first()
    if exist:
        raise HTTPException(status_code=400, detail="Email already exists!")
    user = models.User(username=username, hashed_password=hashed, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    student = models.Student(name=username, grade=0, user_id=user.id)
    db.add(student)
    db.commit()
    db.refresh(student)
    verification_token = create_verification_token(data={"sub": username})
    await send_email(
    to_email=email,
    subject="Verify your EduManager account",
    body=f"Click this link to verify your account: http://localhost:8000/verify?token={verification_token}")
    logger.info(f"New user registered: {username}")
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
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No user associated with this email!")
    reset_token = create_verification_token(data={"sub": user.username})
    await send_email(
    to_email=email,
    subject="Reset your EduManager password",
    body=f"Click this link to reset your password: http://localhost:8000/reset-password?token={reset_token}")
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

@app.post("/students")
def add_student(name: str, grade: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only admins and teachers can add students!")
    if name.strip() == "":
        raise HTTPException(status_code=400, detail="Name cannot be empty!")
    if grade < 0 or grade > 100:
        raise HTTPException(status_code=400, detail="Grade must be between 0 and 100!")
    student = models.Student(name=name, grade=grade)
    db.add(student)
    db.commit()
    db.refresh(student)
    logger.info(f"{user.username} added student: {name}")
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
    return student

@app.put("/students/{student_id}")
def update_student(student_id: int, name: str, grade: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
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
    db.commit()
    db.refresh(student)
    logger.info(f"{user.username} updated student {student_id}: name={name}, grade={grade}")
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
def create_course(course_name: str, teacher_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create courses!")
    teacher = db.query(models.User).filter(models.User.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found!")
    if teacher.role != "teacher":
        raise HTTPException(status_code=400, detail="This user is not a teacher!")
    course = models.Course(course_name=course_name, teacher_id=teacher_id)
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
    enrollment = models.Enrollment(student_id=student_id, course_id=course_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    logger.info(f"{user.username} enrolled {student.name} in {course.course_name}")
    return {"message": f"{student.name} enrolled in {course.course_name}!"}

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