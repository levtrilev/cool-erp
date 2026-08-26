# logger.py
import logging

def setup_logger():
    logger = logging.getLogger("my_app_logger")
    logger.setLevel(logging.DEBUG)

    # Создаем консольный обработчик
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # Задаем формат логов
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)

    # Добавляем обработчик к логгеру
    logger.addHandler(ch)
    
    return logger

logger: logging.Logger = setup_logger()
