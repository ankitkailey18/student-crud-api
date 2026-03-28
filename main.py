from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from auth import hash_password, verify_password, create_access_token, create_refresh_token, verify_token

models.Base.metadata.create_all(bind=engine)
app = FastAPI()
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
        return None
    payload = verify_token(token)
    if payload is None:
        return None
    username = payload.get("sub")
    user = db.query(models.User).filter(models.User.username == username).first()
    return user

@app.post("/register")
def register(username: str, password: str, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        return {"error": "Username already taken!"}
    hashed = hash_password(password)
    user = models.User(username=username, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    student = models.Student(name=username, grade=0, user_id=user.id)
    db.add(student)
    db.commit()
    db.refresh(student)
    return {"message": "User registered!", "username": user.username, "role": user.role, "student_id": student.id}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        return {"error": "Invalid username or password!"}
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@app.post("/refresh")
def refresh(token: str, db: Session = Depends(get_db)):
    payload = verify_token(token)
    if payload is None:
        return {"error": "Invalid or expired refresh token!"}
    username = payload.get("sub")
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return {"error": "User not found!"}
    new_access_token = create_access_token(data={"sub": user.username})
    return {"access_token": new_access_token, "token_type": "bearer"}

@app.get("/me")
def get_me(user = Depends(get_current_user)):
    if user is None:
        return {"error": "Not authenticated!"}
    return {"id": user.id, "username": user.username, "role": user.role}

@app.post("/logout")
def logout(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    blacklisted = models.BlacklistedToken(token=token)
    db.add(blacklisted)
    db.commit()
    return {"message": "Logged out successfully!"}

@app.put("/users/{user_id}/role")
def change_role(user_id: int, new_role: str, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return {"error": "Not authenticated!"}
    if user.role != "admin":
        return {"error": "Only admins can change roles!"}
    new_role = new_role.lower()
    if new_role not in ["admin", "teacher", "student"]:
        return {"error": "Role must be admin, teacher, or student!"}
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        return {"error": "User not found!"}
    target_user.role = new_role
    db.commit()
    db.refresh(target_user)
    return {"message": f"{target_user.username} is now a {new_role}!", "username": target_user.username, "role": target_user.role}

@app.get("/users")
def get_all_users(user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return {"error": "Not authenticated!"}
    if user.role != "admin":
        return {"error": "Only admins can view all users!"}
    users = db.query(models.User).all()
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
    if user is None:
        return {"error": "Not authenticated!"}
    if user.role not in ["admin", "teacher"]:
        return {"error": "Only admins and teachers can add students!"}
    student = models.Student(name=name, grade=grade)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

@app.get("/students")
def get_all_students(user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return {"error": "Not authenticated!"}
    if user.role in ["admin", "teacher"]:
        return db.query(models.Student).all()
    return db.query(models.Student).filter(models.Student.user_id == user.id).all()

@app.get("/students/filter")
def filter_students(grade: int = None, name: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Student)
    if grade is not None:
        query = query.filter(models.Student.grade == grade)
    if name is not None:
        query = query.filter(models.Student.name == name)
    return query.all()

@app.get("/students/{student_id}")
def get_student(student_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return {"error": "Not authenticated!"}
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student is None:
        return {"error": "Student not found!"}
    if user.role == "student" and student.user_id != user.id:
        return {"error": "You can only view your own data!"}
    return student

@app.put("/students/{student_id}")
def update_student(student_id: int, name: str, grade: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return {"error": "Not authenticated!"}
    if user.role not in ["admin", "teacher"]:
        return {"error": "Only admins and teachers can update students!"}
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student is None:
        return {"error": "Student not found!"}
    student.name = name
    student.grade = grade
    db.commit()
    db.refresh(student)
    return student

@app.delete("/students/{student_id}")
def delete_student(student_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return {"error": "Not authenticated!"}
    if user.role != "admin":
        return {"error": "Only admins can delete students!"}
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student is None:
        return {"error": "Student not found!"}
    db.delete(student)
    db.commit()
    return {"message": "Student deleted!"}

@app.post("/courses")
def create_course(course_name: str, teacher_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return {"error": "Not authenticated!"}
    if user.role != "admin":
        return {"error": "Only admins can create courses!"}
    teacher = db.query(models.User).filter(models.User.id == teacher_id).first()
    if not teacher:
        return {"error": "Teacher not found!"}
    if teacher.role != "teacher":
        return {"error": "This user is not a teacher!"}
    course = models.Course(course_name=course_name, teacher_id=teacher_id)
    db.add(course)
    db.commit()
    db.refresh(course)
    return {"message": "Course created!", "course_name": course.course_name, "course_id": course.id, "teacher": teacher.username}

@app.get("/courses")
def get_all_courses(user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return {"error": "Not authenticated!"}
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
    if user is None:
        return {"error": "Not authenticated!"}
    student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
    if not student:
        return {"error": "Student profile not found!"}
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
    if user is None:
        return {"error": "Not authenticated!"}
    if user.role not in ["admin", "teacher"]:
        return {"error": "Only admins and teachers can enroll students!"}
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        return {"error": "Course not found!"}
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        return {"error": "Student not found!"}
    enrollment = models.Enrollment(student_id=student_id, course_id=course_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return {"message": f"{student.name} enrolled in {course.course_name}!"}

@app.get("/courses/{course_id}/students")
def get_course_students(course_id: int, user = Depends(get_current_user), db: Session = Depends(get_db)):
    if user is None:
        return {"error": "Not authenticated!"}
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        return {"error": "Course not found!"}
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.course_id == course_id).all()
    classmates = []
    for enrollment in enrollments:
        classmates.append({
            "student_id": enrollment.student.id,
            "name": enrollment.student.name
        })
    return {"course": course.course_name, "students": classmates}