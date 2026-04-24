# 🎓 Student Management REST API

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-000000?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)

A production-ready **RESTful API** built with **FastAPI** and **PostgreSQL** featuring **JWT authentication**, **role-based access control**, **real email verification via Resend**, **course enrollment system**, and full CRUD operations.

🔗 **Live API:** [student-crud-api-production-e886.up.railway.app/docs](https://student-crud-api-production-e886.up.railway.app/docs)
📧 **Email Domain:** `noreply@edumanager.me`

---

## ⚡ Features

- ✅ Full CRUD — Create, Read, Update, Delete students and courses
- ✅ JWT Authentication — Access tokens (30 min) + Refresh tokens (7 days)
- ✅ Role-Based Access Control — Admin, Teacher, and Student permissions
- ✅ Real Email Verification — Verification emails sent via Resend from `noreply@edumanager.me`
- ✅ Password Reset — Forgot password flow with secure reset tokens emailed to users
- ✅ Course Enrollment System — Many-to-many student-course relationships
- ✅ Classmates Feature — Students can see who's in their courses
- ✅ Token Blacklisting — Logout immediately kills the token
- ✅ Password Hashing — Bcrypt for secure password storage
- ✅ Rate Limiting — Prevents brute force attacks on login/register
- ✅ Pagination, Search & Sorting — Efficient data retrieval
- ✅ Input Validation — Name, grade, email format, and password requirements
- ✅ Logging — All actions tracked in app.log
- ✅ CORS — Frontend-ready with cross-origin support
- ✅ Proper HTTP Error Codes — 400, 401, 403, 404, 429
- ✅ Deployed on Railway with PostgreSQL

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
| Resend + httpx | Transactional email delivery |
| SlowAPI | Rate limiting |
| Uvicorn | ASGI server |
| python-dotenv | Environment variable management |
| Railway | Cloud deployment |
| Namecheap | Custom domain (`edumanager.me`) |

---

## 📧 Email Integration

This API sends **real transactional emails** using [Resend](https://resend.com) with a custom domain:

- **Verification emails** — Sent on registration from `noreply@edumanager.me`
- **Password reset emails** — Sent when users request a password reset
- **Custom domain** — `edumanager.me` with DKIM, SPF, and DMARC configured
- **HTTP API** — Uses Resend's REST API via `httpx` (no SMTP ports needed, works on free-tier hosts)

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
RESEND_API_KEY=your-resend-api-key
FRONTEND_URL=http://localhost:8000
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
| `POST` | `/register` | Create account + sends verification email | Public |
| `GET` | `/verify` | Verify email via token link | Public |
| `POST` | `/forgot-password` | Sends password reset email | Public |
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
Register → Verification email sent to user
                    ↓
         User clicks link in email → Email verified
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
- **Real Email Verification** — Transactional emails via Resend with custom domain
- **DNS Authentication** — DKIM, SPF, and DMARC configured for email deliverability
- **Role-Based Access** — Students can only see their own data
- **Environment Variables** — All secrets stored as env vars, never in code
- **Input Validation** — Grade (0-100), non-empty names, email format, password (8+ chars with number)
- **CORS** — Configurable cross-origin access
- **HTTP Error Codes** — Proper 400, 401, 403, 404, 429 responses

---

## 👨‍💻 Author

**Ankit Kailey**
- GitHub: [@ankitkailey18](https://github.com/ankitkailey18)
- Portfolio: [ankitkailey18.github.io](https://ankitkailey18.github.io)