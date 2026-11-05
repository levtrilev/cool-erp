# app/modules/__init__.py

def register_all_replication_handlers() -> None:
    """Явная регистрация всех обработчиков репликации при старте."""
    # Домен business_partners: реплика регионов из sales
    import app.modules.business_partners.regions_replica.handlers # pyright: ignore[reportUnusedImport]

    # Домен sales: реплика складов из inventory (когда появится)
    import app.modules.sales.warehouses_replica.handlers # pyright: ignore[reportUnusedImport]

    # Домен inventory: реплика товаров из sales (когда появится)
    import app.modules.inventory.goods_replica.handlers # pyright: ignore[reportUnusedImport]


