# Сначала импортируем модели, которые НЕ зависят от других (TenantModel)
from app.core.tenants.models import TenantModel
from app.core.users.models import UserModel
from app.core.auth.models import UserSession
from app.core.sections.models import SectionModel
from app.core.permissions.models import PermissionModel
from app.core.roles.models import RoleModel
from app.core.doctypes.models import DoctypeModel

__all__ = [
    "TenantModel",
    "UserModel",
    "UserSession",
    "SectionModel",
    "PermissionModel",
    "RoleModel",
    "DoctypeModel",
]
# """
# Ядро платформы (не бизнес-домен).

# ⚠️ Этот файл импортируется в main.py через `import app.core`
# для регистрации всех моделей в SQLAlchemy Base.registry.
# Не удаляйте импорты моделей.
# """

# # Импорт моделей для регистрации в Base.registry.mappers
# from app.core.auth import models as _auth_models  # noqa: F401
# from app.core.tenants import models as _tenant_models  # noqa: F401
# from app.core.users import models as _user_models  # noqa: F401
# from app.core.roles import models as _role_models  # noqa: F401
# from app.core.sections import models as _section_models  # noqa: F401
# from app.core.permissions import models as _permission_models  # noqa: F401
# from app.core.domains import models as _domain_models  # noqa: F401
# from app.core.doctypes import models as _doctype_models  # noqa: F401
# from app.core.notes import models as _notes_models  # noqa: F401
# from app.core.events import models as _events_models  # noqa: F401

# __all__: list[str] = []