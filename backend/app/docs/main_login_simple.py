from fastapi import FastAPI, Cookie, Response, HTTPException, status
from pydantic import BaseModel
import uuid

app = FastAPI()

# Pydantic-модель для валидации payload при логине
class User(BaseModel):
    name: str
    password: str

# 1. Фейковая база данных зарегистрированных пользователей
# В реальном проекте здесь будет запрос к PostgreSQL/SQLite, а пароли будут захешированы
USERS_DB = {
    "alex": "secret123",
    "maria": "qwerty2026",
    "admin": "admin777"
}

# Имитация активных сессий на сервере (токен -> данные пользователя)
sessions_storage = {}


@app.post("/login")
async def login(user: User, response: Response):
    # 2. Проверка: существует ли пользователь в нашей базе данных
    if user.name not in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь с таким именем не найден"
        )
    
    # 3. Проверка: совпадает ли введенный пароль с паролем из базы данных
    expected_password = USERS_DB[user.name]
    if user.password != expected_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный пароль"
        )
    
    # Если проверки пройдены — создаем сессию
    session_token = str(uuid.uuid4())
    sessions_storage[session_token] = {"name": user.name}
    
    # Устанавливаем куку
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


# 4. Маршрут для выхода (удаление куки и сессии)
@app.post("/logout")
async def logout(response: Response, session_token: str | None = Cookie(default=None)):
    # Если кука есть, удаляем сессию из памяти сервера
    if session_token and session_token in sessions_storage:
        del sessions_storage[session_token]
        
    # Удаляем куку на стороне клиента (браузера)
    response.delete_cookie(
        key="session_token",
        httponly=True,
        samesite="lax"
    )
    
    return {"message": "Вы успешно вышли из системы, cookie удалена"}
