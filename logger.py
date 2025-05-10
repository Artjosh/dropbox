import os
import logging
import locale
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Define log file path
LOG_FILE = 'workspace.log'

# Set locale to PT-BR for datetime formatting
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
    except:
        pass

# Nível de verbosidade para logs (ERROR = apenas erros, INFO = tudo)
LOG_LEVEL = logging.INFO  # Restaurado para INFO para manter mensagens importantes

def get_br_time():
    """
    Obtém o tempo atual no formato brasileiro
    """
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def setup_logger():
    """
    Configure um logger minimalista
    """
    # Remover todos os handlers padrão
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Criar o logger principal
    logger = logging.getLogger("pdf_processor")
    logger.setLevel(LOG_LEVEL)
    logger.propagate = False
    
    # Limpar handlers existentes
    if logger.handlers:
        logger.handlers = []
    
    # Criar handler para arquivo com rotação
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=1*1024*1024,  # 1MB
        backupCount=2,
        encoding='utf-8'
    )
    file_handler.setLevel(LOG_LEVEL)
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    
    # Formatadores simples
    file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', 
                                     datefmt='%d/%m/%Y %H:%M:%S')
    console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
    
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger():
    """
    Retorna a instância do logger
    """
    logger = logging.getLogger("pdf_processor")
    
    if not logger.handlers:
        return setup_logger()
    
    return logger

def log_execution_end(status="CONCLUIDO", detalhes=""):
    """
    Loga uma única linha informando o fim da execução
    """
    logger = get_logger()
    msg = f"FIM PROCESSAMENTO [{status}]"
    if detalhes:
        msg += f" - {detalhes}"
    logger.info(msg)  # Restaurado para info
