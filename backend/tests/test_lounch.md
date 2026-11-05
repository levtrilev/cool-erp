# Все тесты
cd backend
pytest tests/ -v

# Только тесты регистрации новой организации
pytest tests/test_registration/test_new_tenant_registration.py -v

# Только тесты регистрации в существующую организацию
pytest tests/test_registration/test_existing_tenant_registration.py -v

# Только тесты контроля доступа
pytest tests/test_registration/test_access_control.py -v
pytest tests/test_registration/ -v --tb=short

# С подробным выводом
pytest tests/ -v -s

pytest tests/test_registration/ -v --tb=short
pytest tests/test_access_control/ -v --tb=short