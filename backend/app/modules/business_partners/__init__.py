"""
Домен: Business Partners (Контрагенты)

Публичный интерфейс домена. Другие домены импортируют ТОЛЬКО отсюда:
    from app.business_partners import company_service

Запрещено импортировать внутренние модули напрямую:
    from app.business_partners.companies.models import BpCompanyModel  # ❌
"""

from app.modules.business_partners.companies.service import company_service

__all__ = ["company_service"]