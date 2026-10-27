# app/modules/sales/__init__.py
"""
Домен: Sales (Продажи)

Публичный интерфейс домена. Другие домены импортируют ТОЛЬКО отсюда:
    from app.modules.sales import goods_service

Запрещено импортировать внутренние модули напрямую:
    from app.modules.sales.goods.models import SalesGoodsModel  # ❌
"""

from app.modules.sales.goods.service import goods_service

__all__ = ["goods_service"]