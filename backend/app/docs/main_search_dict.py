# main.py
from fastapi import FastAPI
from pydantic import BaseModel, Field, EmailStr, PositiveInt
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

app = FastAPI()

class Event(BaseModel):
    name: str
    timestamp: datetime

class UserCreate(BaseModel):
    name: str
    email: str
    age: PositiveInt | None = Field(None, minimum = 0)
    is_subscribed: bool = False

    # Декоратор указывает, какое поле мы проверяем
    # @field_validator("age")
    # @classmethod
    # def check_age(cls, value: int) -> int:
    #     if value < 0 :
    #         raise ValueError("Возраст не может быть отрицательным!")

    #     # Если всё хорошо, обязательно возвращаем валидное значение
    #     return value

class Product(BaseModel):
    product_id: int
    name: str
    category: str
    price: float

# Фейковая база данных
sample_product_1 = {
    "product_id": 123,
    "name": "Smartphone",
    "category": "Electronics",
    "price": 599.99
}

sample_product_2 = {
    "product_id": 456,
    "name": "Phone Case",
    "category": "Accessories",
    "price": 19.99
}

sample_product_3 = {
    "product_id": 789,
    "name": "Iphone",
    "category": "Electronics",
    "price": 1299.99
}

sample_product_4 = {
    "product_id": 101,
    "name": "Headphones",
    "category": "Accessories",
    "price": 99.99
}

sample_product_5 = {
    "product_id": 202,
    "name": "Smartwatch",
    "category": "Electronics",
    "price": 299.99
}

sample_products = [sample_product_1, sample_product_2, sample_product_3, sample_product_4, sample_product_5]
# Создаем словарь для быстрого поиска по ID
products_dict: dict[int, Product] = {
    p["product_id"]: p for p in sample_products
}
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


@app.post("/events/")
async def create_event(event: Event):
    return event

@app.post("/create_user/")
async def create_user(user: UserCreate):
    return user

@app.get("/products/search")
async def get_product(keyword: str, category: str | None = None, limit: int | None = None) -> list[Product]:
    produst_list = []
    for product in sample_products:
        if keyword.lower() in product["name"].lower() and (category is None or product["category"] == category):
            produst_list.append(product)
    return produst_list[:limit]

@app.get("/product/{product_id}")
async def get_product(product_id: int) -> Product | str:
    # Поиск за O(1)
    if product := products_dict.get(product_id):
        return product
    return "Product not found"