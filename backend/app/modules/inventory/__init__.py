# app/modules/inventory/__init__.py
"""
Домен: Inventory (Складское хозяйство)

Публичный интерфейс домена. Другие домены импортируют ТОЛЬКО отсюда:
    from app.modules.inventory import warehouse_service

Запрещено импортировать внутренние модули напрямую:
    from app.modules.inventory.warehouses.models import InvWarehouseModel  # ❌
"""

from app.modules.inventory.warehouses.service import warehouse_service

__all__ = ["warehouse_service"]