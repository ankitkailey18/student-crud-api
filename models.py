from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    grade = Column(Integer)
    courses = relationship("Course", back_populates="student")

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    course_name = Column(String)  # renamed from name to course_name
    student_id = Column(Integer, ForeignKey("students.id"))
    student = relationship("Student", back_populates="courses")