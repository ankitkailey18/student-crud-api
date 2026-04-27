from sqlalchemy import Column, Integer, String, ForeignKey, Date, Float, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    grade = Column(Integer)
    enrollments = relationship("Enrollment", back_populates="student")
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="student_profile")
    attendance_records = relationship("Attendance", back_populates="student")
    submissions = relationship("Submission", back_populates="student")

class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    course_name = Column(String)
    course_code = Column(String, default="")
    color = Column(String, default="#3498db")
    teacher_id = Column(Integer, ForeignKey("users.id"))
    teacher = relationship("User", back_populates="courses_teaching")
    enrollments = relationship("Enrollment", back_populates="course")
    assignments = relationship("Assignment", back_populates="course")
    attendance_records = relationship("Attendance", back_populates="course")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    role = Column(String, default="student")
    hashed_password = Column(String)
    email = Column(String, unique=True)
    is_verified = Column(Integer, default=0)
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

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    max_points = Column(Integer, default=100)
    due_date = Column(Date)
    course_id = Column(Integer, ForeignKey("courses.id"))
    course = relationship("Course", back_populates="assignments")
    submissions = relationship("Submission", back_populates="assignment")

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    points_earned = Column(Float)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    student = relationship("Student", back_populates="submissions")
    assignment = relationship("Assignment", back_populates="submissions")

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    date = Column(Date)
    status = Column(String, default="present")
    student = relationship("Student", back_populates="attendance_records")
    course = relationship("Course", back_populates="attendance_records")