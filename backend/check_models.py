from app.core.database import Base
from backend.app.core.user.models import UserModel, UserSession

print("Таблицы в Base.metadata:")
for table_name in Base.metadata.tables.keys():
    print(f"  - {table_name}")

print(f"\nМодель UserModel: {UserModel.__tablename__}")
print(f"Модель UserSession: {UserSession.__tablename__}")