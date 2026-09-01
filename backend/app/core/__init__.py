# Сначала импортируем модели, которые НЕ зависят от других (TenantModel)
from app.core.tenant.models import TenantModel

# Потом импортируем UserSession (он зависит от UserModel через ForeignKey)
from app.core.auth.models import UserSession

# Потом импортируем UserModel (он зависит от UserSession и TenantModel через relationship)
from app.core.user.models import UserModel

__all__ = ["TenantModel", "UserSession", "UserModel"]