# 🎓 Student CRUD API

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)

A fully functional **RESTful API** built with **FastAPI** and **SQLite** to manage student records with full CRUD operations.

---

## ⚡ Features

- ✅ Full CRUD — Create, Read, Update, Delete
- ✅ Filter students by grade or name
- ✅ Real SQLite database with SQLAlchemy
- ✅ Auto generated API documentation
- ✅ Data validation with Pydantic
- ✅ Error handling

---

## 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| FastAPI | Backend framework |
| SQLAlchemy | Database ORM |
| SQLite | Database |
| Pydantic | Data validation |
| Uvicorn | Server |

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/ankitkailey18/student-crud-api.git
cd student-crud-api
```

### 2. Install dependencies
```bash
pip install fastapi uvicorn sqlalchemy
```

### 3. Run the server
```bash
uvicorn main:app --reload
```

### 4. Visit API documentation
```
http://127.0.0.1:8000/docs
```

---

## 📡 API Routes

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/students` | Get all students |
| `GET` | `/students/{id}` | Get student by ID |
| `GET` | `/students/filter` | Filter students |
| `POST` | `/students` | Add a new student |
| `PUT` | `/students/{id}` | Update a student |
| `DELETE` | `/students/{id}` | Delete a student |

---

## 🔍 Filter Examples
```
# Filter by grade
GET /students/filter?grade=92

# Filter by name
GET /students/filter?name=Ankit

# Filter by both
GET /students/filter?grade=92&name=Ankit
```

---

## 📝 Request Examples

### Add a student
```json
{
  "name": "Ankit",
  "grade": 92
}
```

### Response
```json
{
  "id": 1,
  "name": "Ankit",
  "grade": 92
}
```

---

## 👨‍💻 Author
**Ankit Kailey**
- GitHub: [@ankitkailey18](https://github.com/ankitkailey18)