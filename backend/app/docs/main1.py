# main.py
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import load_config
from app.docs.logger import logger
from backend.app.core.user.models import UserMsg
from backend.app.core.user.models import User
from backend.app.core.user.models import UserAge

my_app = FastAPI()

config = load_config()

user1: User = User(
    id=1,
    name="John Doe",
    signup_ts="2017-06-01 12:22",
    friends=[1, 2, 3],
)
class UserAgeItem(BaseModel):
    username: str
    user_info: str

user2: UserAge = UserAge(name="John Gogin", age=40)

if config.debug:
    my_app.debug = True
else:
    my_app.debug = False

fake_db = [{"username": "vasya", "user_info": "любит колбасу"}, {"username": "katya", "user_info": "любит петь"}] 


# Обрабатываем GET-запрос, чтобы вернуть список пользователей 
@my_app.get('/users') 
async def get_all_users(): 
    return fake_db 

# Обрабатываем POST-запрос, чтобы добавить нового пользователя 
@my_app.post('/add_user') 
async def add_user(user_with_age: UserAgeItem): 
    fake_db.append({"username": user_with_age.username, "user_info": user_with_age.user_info}) 
    return fake_db
    # return {"message": "Юзер успешно добавлен в базу данных"}

@my_app.get("/db")
def get_db_info():
    logger.info(f"Connecting to database: {config.db.database_url}")
    return {"database_url": config.db.database_url}

@my_app.get("/user1")
def user1_info():
    logger.info(f"User 1 info: {user1.name}")
    return user1


@my_app.get("/log")
def read_root():
    logger.info("Handling request to root endpoint")
    return {"message": "Hello, World!"}


# 1. Создаем схему данных
class CalculationItem(BaseModel):
    var1: int
    var2: int


# Получаем абсолютный путь к папке, где лежит main.py
current_dir = os.path.dirname(os.path.abspath(__file__))
html_file_path = os.path.join(current_dir, "index.html")


@my_app.get("/")
async def root():
    # Проверяем, существует ли файл, чтобы выдать понятную ошибку в консоль
    if not os.path.exists(html_file_path):
        return {"error": f"Файл не найден по пути: {html_file_path}"}

    return FileResponse(html_file_path)


@my_app.post("/calculate")
# 2. Указываем схему в аргументах функции
async def calc(item: CalculationItem):
    result = item.var1 + item.var2
    return {"response": f"{item.var1} + {item.var2} = {result}"}

@my_app.post("/userage")
# 2. Указываем схему в аргументах функции
async def check_adult(user: UserAge):
    is_adult = user.age >= 18
    return {"name": user.name, "age": user.age, "is_adult": is_adult}

@my_app.get("/calcvars")
async def calcvars(var1: int, var2: int):
    return {"response": f"{var1} + {var2} = {var1 + var2}"}


@my_app.post("/usrmsg")
async def usrmsg(user: UserMsg):
    """
    Здесь мы можем с переменной user, которая содержит объект класса UserMsg с соответствующими полями,
    выполнить любую логику – например, сохранить информацию в базу данных, передать в другую функцию и т.д.
    """
    print(f"Мы получили от юзера {user.username} такое сообщение: {user.message}")
    return {"ответ": f"юзер {user.username} сказал: {user.message}"}
