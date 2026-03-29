# 🎓 Student Management REST API

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)

A production-ready **RESTful API** built with **FastAPI** and **PostgreSQL** featuring **JWT authentication**, **role-based access control**, **email verification**, **course enrollment system**, and full CRUD operations.

🔗 **Live API:** [https://student-crud-api-lhju.onrender.com/docs](https://student-crud-api-lhju.onrender.com/docs)

---

## ⚡ Features

- ✅ Full CRUD — Create, Read, Update, Delete students and courses
- ✅ JWT Authentication — Access tokens (30 min) + Refresh tokens (7 days)
- ✅ Role-Based Access Control — Admin, Teacher, and Student permissions
- ✅ Email Verification — Users must verify email before logging in
- ✅ Password Reset — Forgot password flow with secure reset tokens
- ✅ Course Enrollment System — Many-to-many student-course relationships
- ✅ Classmates Feature — Students can see who's in their courses
- ✅ Token Blacklisting — Logout immediately kills the token
- ✅ Password Hashing — Bcrypt for secure password storage
- ✅ Rate Limiting — Prevents brute force attacks on login/register
- ✅ Pagination, Search & Sorting — Efficient data retrieval
- ✅ Input Validation — Name, grade, and password requirements
- ✅ Logging — All actions tracked in app.log
- ✅ CORS — Frontend-ready with cross-origin support
- ✅ Proper HTTP Error Codes — 400, 401, 403, 404, 429
- ✅ Deployed on Render with PostgreSQL

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| FastAPI | Backend framework |
| SQLAlchemy | Database ORM |
| PostgreSQL | Production database |
| SQLite | Local development database |
| JWT (python-jose) | Authentication tokens |
| Passlib + Bcrypt | Password hashing |
| SlowAPI | Rate limiting |
| Uvicorn | ASGI server |
| python-dotenv | Environment variable management |
| Render | Cloud deployment |

---

## 🔐 Role-Based Access

| Role | Add Student | Update Student | Delete Student | View Students | Create Course | Enroll Students | Promote Users |
|------|------------|----------------|----------------|---------------|---------------|-----------------|---------------|
| Admin | ✅ | ✅ | ✅ | ✅ (all) | ✅ | ✅ | ✅ |
| Teacher | ✅ | ✅ | ❌ | ✅ (all) | ❌ | ✅ | ❌ |
| Student | ❌ | ❌ | ❌ | ✅ (own only) | ❌ | ❌ | ❌ |

---

## 🚀 Getting Started (Local Development)

### 1. Clone the repository
```bash
git clone https://github.com/ankitkailey18/student-crud-api.git
cd student-crud-api
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create a `.env` file
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./students.db
```

### 4. Run the server
```bash
uvicorn main:app --reload
```

### 5. Create the first admin
```bash
python create_admin.py
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
| `POST` | `/register` | Create account + email verification token | Public |
| `POST` | `/verify` | Verify email with token | Public |
| `POST` | `/forgot-password` | Get password reset token | Public |
| `POST` | `/reset-password` | Reset password with token | Public |
| `POST` | `/login` | Login and get access + refresh tokens | Public |
| `POST` | `/refresh` | Get new access token | Public |
| `GET` | `/me` | Get current user info | Authenticated |
| `POST` | `/logout` | Blacklist current token | Authenticated |

### User Management
| Method | Route | Description | Access |
|--------|-------|-------------|--------|
| `PUT` | `/users/{id}/role` | Change user role | Admin only |
| `GET` | `/users` | View all users (with role filter) | Admin only |

### Students
| Method | Route | Description | Access |
|--------|-------|-------------|--------|
| `POST` | `/students` | Add a new student | Admin, Teacher |
| `GET` | `/students` | Get students (paginated, searchable, sortable) | Authenticated |
| `GET` | `/students/{id}` | Get student by ID | Authenticated |
| `PUT` | `/students/{id}` | Update a student | Admin, Teacher |
| `DELETE` | `/students/{id}` | Delete a student | Admin only |

### Courses
| Method | Route | Description | Access |
|--------|-------|-------------|--------|
| `POST` | `/courses` | Create a course with assigned teacher | Admin only |
| `GET` | `/courses` | View all courses with teacher names | Authenticated |
| `GET` | `/my-courses` | View your enrolled courses | Authenticated |
| `POST` | `/courses/{id}/enroll` | Enroll a student in a course | Admin, Teacher |
| `GET` | `/courses/{id}/students` | View classmates in a course | Authenticated |

---

## 🔑 Authentication Flow

```
Register → Get verification token → Verify email
                                        ↓
                              Login → Access Token (30 min) + Refresh Token (7 days)
                                        ↓
                              Use Access Token for all requests
                                        ↓
                              Token expires → Use Refresh Token
                                        ↓
                              Logout → Token blacklisted immediately
```

---

## 🔍 Query Examples

```
GET /students?page=1&limit=10          → Pagination
GET /students?search=john              → Search by name
GET /students?sort=grade&order=desc    → Sort by grade (highest first)
GET /students?search=a&sort=name&page=1&limit=5  → Combined
GET /users?role=teacher                → Filter users by role
```

---

## 🛡️ Security Features

- **JWT Tokens** — Stateless authentication with expiration
- **Bcrypt Hashing** — Passwords never stored in plain text
- **Token Blacklisting** — Logout invalidates tokens immediately
- **Rate Limiting** — 5 req/min on login/register, 3 req/min on forgot-password
- **Email Verification** — Users must verify before accessing the system
- **Role-Based Access** — Students can only see their own data
- **Environment Variables** — SECRET_KEY and DATABASE_URL never in code
- **Input Validation** — Grade (0-100), non-empty names, password (8+ chars with number)
- **CORS** — Configurable cross-origin access
- **HTTP Error Codes** — Proper 400, 401, 403, 404, 429 responses

---

## 📝 Request Examples

### Register
```
POST /register?username=john&password=secure123&email=john@email.com
→ {"message": "User registered! Please verify your email.", "verification_token": "eyJ..."}
```

### Login
```
POST /login
→ {"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}
```

### Add a Student (requires token)
```
POST /students?name=John&grade=92
→ {"name": "John", "grade": 92, "id": 1, "user_id": null}
```

### Enroll in Course
```
POST /courses/1/enroll?student_id=1
→ {"message": "John enrolled in Data Structures!"}
```

---

## 👨‍💻 Author

**Ankit Kailey**
- GitHub: [@ankitkailey18](https://github.com/ankitkailey18)
- Portfolio: [ankitkailey18.github.io](https://ankitkailey18.github.io)