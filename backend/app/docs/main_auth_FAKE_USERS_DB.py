from fastapi import FastAPI, Cookie, Response, HTTPException, status
from pydantic import BaseModel
import uuid
import bcrypt

app = FastAPI()

class User(BaseModel):
    name: str
    password: str

# Фейковая база данных (изначально пустая)
USERS_DB = {}

# Автоматически добавляем администратора при запуске сервера, 
# чтобы его хеш гарантированно подошел
def seed_admin():
    admin_password = "admin777"
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), salt)
    USERS_DB["admin"] = hashed_password.decode('utf-8')

seed_admin()

# Имитация активных сессий на сервере
sessions_storage = {}


# 1. Маршрут для регистрации новых пользователей
@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: User):
    # Проверяем, не занято ли имя
    if user.name in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует"
        )
    
    # Хешируем пароль по правильной схеме
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), salt)
    
    # Сохраняем строку-хеш в нашу базу данных
    USERS_DB[user.name] = hashed_password.decode('utf-8')
    
    return {"message": f"Пользователь {user.name} успешно зарегистрирован"}


# 2. Исправленный маршрут для логина
@app.post("/login")
async def login(user: User, response: Response):
    if user.name not in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль"
        )
    
    # Извлекаем сохраненный хеш и переводим в bytes
    stored_hash_bytes = USERS_DB[user.name].encode('utf-8')
    password_bytes = user.password.encode('utf-8')
    
    # Проверяем пароль
    if not bcrypt.checkpw(password_bytes, stored_hash_bytes):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль"
        )
    
    # Создаем сессию при успешном совпадении
    session_token = str(uuid.uuid4())
    sessions_storage[session_token] = {"name": user.name}
    
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax"
    )
    
    return {"message": f"Пользователь {user.name} успешно авторизован"}


@app.get("/user")
async def get_user(session_token: str | None = Cookie(default=None)):
    if not session_token or session_token not in sessions_storage:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Вы не авторизованы или сессия истекла"
        )
        
    return {"status": "Доступ разрешен", "user": sessions_storage[session_token]}


@app.post("/logout")
async def logout(response: Response, session_token: str | None = Cookie(default=None)):
    if session_token and session_token in sessions_storage:
        del sessions_storage[session_token]
        
    response.delete_cookie(key="session_token", httponly=True, samesite="lax")
    return {"message": "Вы успешно вышли из системы"}

