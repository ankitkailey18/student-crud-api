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
    return {"message": "User registered!", "username": user.username}

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

@app.post("/students")
def add_student(name: str, grade: int, db: Session = Depends(get_db)):
    student = models.Student(name=name, grade=grade)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

@app.post("/students/{student_id}/courses")
def add_course(student_id: int, course_name: str, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student is None:
        return {"error": "No student found!"}
    course = models.Course(course_name=course_name, student_id=student_id)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

@app.get("/students/{student_id}/courses")
def get_courses(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student is None:
        return {"error": "Student not found!"}
    return student.courses

@app.get("/students")
def get_all_students(db: Session = Depends(get_db)):
    students = db.query(models.Student).all()
    return students

@app.get("/students/filter")
def filter_students(grade: int = None, name: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Student)
    if grade is not None:
        query = query.filter(models.Student.grade == grade)
    if name is not None:
        query = query.filter(models.Student.name == name)
    return query.all()

@app.get("/students/{student_id}")
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student is None:
        return {"error": "Student not found!"}
    return student

@app.put("/students/{student_id}")
def update_student(student_id: int, name: str, grade: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student is None:
        return {"error": "Student not found!"}
    student.name = name
    student.grade = grade
    db.commit()
    db.refresh(student)
    return student

@app.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student is None:
        return {"error": "Student not found!"}
    db.delete(student)
    db.commit()
    return {"message": "Student deleted!"}