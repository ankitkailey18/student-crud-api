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

@app.get("/students/{student_id}")
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    return student
@app.put("/students/{student_id}")
def update_student(student_id: int, name: str, grade: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    student.name = name
    student.grade = grade
    db.commit()
    db.refresh(student)
    return student
@app.delete("/students/{student_id}")
@app.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    db.delete(student)
    db.commit()
    return {"message": "Student deleted!"}