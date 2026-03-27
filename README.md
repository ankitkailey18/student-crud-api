# 🎓 Student Management API

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)

A fully functional **RESTful API** built with **FastAPI** and **SQLite** featuring **JWT authentication**, **role-based access control**, and full CRUD operations for managing students, courses, and users.

---

## ⚡ Features

- ✅ Full CRUD — Create, Read, Update, Delete students and courses
- ✅ JWT Authentication — Register, Login, Logout with access and refresh tokens
- ✅ Role-Based Access Control — Admin, Teacher, and Student permissions
- ✅ Token Blacklisting — Logout immediately kills the token
- ✅ Password Hashing — Bcrypt for secure password storage
- ✅ Refresh Tokens — Stay logged in without re-entering password
- ✅ Filter students by grade or name
- ✅ Real SQLite database with SQLAlchemy ORM
- ✅ Auto-generated API documentation
- ✅ Environment variables for secret key protection

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| FastAPI | Backend framework |
| SQLAlchemy | Database ORM |
| SQLite | Database |
| JWT (python-jose) | Authentication tokens |
| Passlib + Bcrypt | Password hashing |
| Pydantic | Data validation |
| Uvicorn | Server |
| python-dotenv | Environment variable management |

---

## 🔐 Role-Based Access

| Role | Add Student | Update Student | Delete Student | View Students | Promote Users |
|------|------------|----------------|----------------|---------------|---------------|
| Admin | ✅ | ✅ | ✅ | ✅ | ✅ |
| Teacher | ✅ | ✅ | ❌ | ✅ | ❌ |
| Student | ❌ | ❌ | ❌ | ✅ | ❌ |

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/ankitkailey18/student-crud-api.git
cd student-crud-api
```

### 2. Install dependencies
```bash
pip install fastapi uvicorn sqlalchemy python-jose passlib bcrypt python-multipart python-dotenv
```

### 3. Create a `.env` file
```
SECRET_KEY=your-secret-key-here
```

### 4. Create the first admin
```bash
python create_admin.py
```

### 5. Run the server
```bash
uvicorn main:app --reload
```

### 6. Visit API documentation
```
http://127.0.0.1:8000/docs
```

---

## 📡 API Routes

### Authentication
| Method | Route | Description | Access |
|--------|-------|-------------|--------|
| `POST` | `/register` | Create a new account | Public |
| `POST` | `/login` | Login and get tokens | Public |
| `POST` | `/refresh` | Get new access token | Public |
| `GET` | `/me` | Get current user info | Authenticated |
| `POST` | `/logout` | Blacklist current token | Authenticated |

### Students
| Method | Route | Description | Access |
|--------|-------|-------------|--------|
| `GET` | `/students` | Get all students | Public |
| `GET` | `/students/{id}` | Get student by ID | Public |
| `GET` | `/students/filter` | Filter students | Public |
| `POST` | `/students` | Add a new student | Admin, Teacher |
| `PUT` | `/students/{id}` | Update a student | Admin, Teacher |
| `DELETE` | `/students/{id}` | Delete a student | Admin only |

### Courses
| Method | Route | Description | Access |
|--------|-------|-------------|--------|
| `POST` | `/students/{id}/courses` | Add a course | Admin, Teacher |
| `GET` | `/students/{id}/courses` | Get student's courses | Public |

### User Management
| Method | Route | Description | Access |
|--------|-------|-------------|--------|
| `PUT` | `/users/{id}/role` | Change user role | Admin only |

---

## 🔑 Authentication Flow

```
Register → Login → Get Access Token + Refresh Token
                        ↓
         Use Access Token for all requests (30 min)
                        ↓
         Token expires → Use Refresh Token to get new one (7 days)
                        ↓
         Logout → Token blacklisted immediately
```

---

## 🔍 Filter Examples
```
GET /students/filter?grade=92
GET /students/filter?name=Ankit
GET /students/filter?grade=92&name=Ankit
```

---

## 📝 Request Examples

### Register
```json
POST /register?username=john&password=pass123
→ {"message": "User registered!", "username": "john", "role": "student"}
```

### Login
```json
POST /login
→ {"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}
```

### Add a Student (requires token)
```json
POST /students?name=Ankit&grade=92
→ {"name": "Ankit", "grade": 92, "id": 1}
```

---

## 👨‍💻 Author

**Ankit Kailey**
- GitHub: [@ankitkailey18](https://github.com/ankitkailey18)