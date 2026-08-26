# main.py
from fastapi import FastAPI
from pydantic import BaseModel, Field, EmailStr
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

app = FastAPI()

BANNED_WORDS = ["редиск", "бяк", "козявк"]


# Ваша модель данных
class Feedback(BaseModel):
    name: str = Field(min_length=2, max_length=10, description="Имя пользователя", examples=["Иван"])
    message: str = Field(min_length=10, max_length=500, description="Отзыв", examples=["Отлично, так держать!"])

    # Декоратор указывает, какое поле мы проверяем
    @field_validator("message")
    @classmethod
    def check_banned_words(cls, value: str) -> str:
        # Приводим весь текст к нижнему регистру
        lowered_message = value.lower()

        # Проверяем наличие запрещенных основ слов
        for banned in BANNED_WORDS:
            if banned in lowered_message:
                raise ValueError("Использование недопустимых слов")

        # Если всё хорошо, обязательно возвращаем валидное значение
        return value


# Кастомный обработчик ошибок валидации
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []

    for error in exc.errors():
        # Получаем имя поля (например, 'name' или 'message')
        field_name = error.get("loc")[-1]
        error_type = error.get("type")
        standard_msg = error.get("msg", "")
        # Формируем понятное сообщение в зависимости от типа ошибки
        if error_type == "value_error":
            # Очищаем технический текст "Value error, ", если он есть
            clean_msg = standard_msg.replace("Value error, ", "")
            msg = clean_msg
        elif error_type == "string_too_short":
            limit = error.get("ctx", {}).get("min_length")
            msg = f"Поле должно содержать минимум {limit} символа(ов)."
        elif error_type == "string_too_long":
            limit = error.get("ctx", {}).get("max_length")
            msg = f"Поле должно содержать максимум {limit} символа(ов)."
        elif error_type == "missing":
            msg = "Это поле обязательно для заполнения."
        else:
            msg = error.get("msg")  # Стандартное сообщение, если тип не обработан

        errors.append({"field": field_name, "message": msg})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status": "error", "detail": errors},
    )


# Модель для валидации тела запроса
class User(BaseModel):
    username: str
    user_info: str


# class Feedback(BaseModel):
#     name: str = Field(min_length=2, max_length=50)
#     message: str = Field(min_length=10, max_length=500)

# Фейковая база данных
fake_db = [
    {"username": "vasya", "user_info": "любит колбасу"},
    {"username": "katya", "user_info": "любит петь"},
]
feedback_db = [
    {"username": "vasya", "message": "любит колбасу"},
    {"username": "katya", "message": "отличео!"},
]


# Получение пользователя по параметру пути
@app.get("/users/{username}")
async def get_user(username: str):
    for user in fake_db:
        if user["username"] == username:
            return user
    return {"error": "User not found"}


# Получение списка пользователей с ограничением (параметр запроса)
@app.get("/users/")
async def read_users(limit: int = 10):
    return fake_db[:limit]


# Добавление нового пользователя (параметр тела запроса)
@app.post("/add_user", response_model=User)
async def add_user(user: User):
    fake_db.append({"username": user.username, "user_info": user.user_info})
    return user


@app.post("/feedback")
async def add_feedback(feedback: Feedback):
    feedback_db.append(feedback)
    # return feedback_db
    return {"message": f"Спасибо, {feedback.name}! Ваш отзыв сохранён."}
