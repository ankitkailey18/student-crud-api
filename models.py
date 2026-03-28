from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    grade = Column(Integer)
    enrollments = relationship("Enrollment", back_populates="student")
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="student_profile")

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    course_name = Column(String)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    teacher = relationship("User", back_populates="courses_teaching")
    enrollments = relationship("Enrollment", back_populates="course")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    role = Column(String, default="student")
    hashed_password = Column(String)
    email=Column(String,unique=True)
    is_verified=Column(Integer,default=0)
    student_profile = relationship("Student", back_populates="user")
    courses_teaching = relationship("Course", back_populates="teacher")

class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True)

class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")