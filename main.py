from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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