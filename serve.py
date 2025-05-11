"""
Servidor de produção universal - funciona no Windows E Linux
"""

import os
import sys
import platform
from dotenv import load_dotenv
from app import app, init_dropbox, init_pdf_processor
from logger import get_logger

# Configuração
load_dotenv()
logger = get_logger()
PORT = int(os.environ.get('PORT', 5000))

# Inicializar componentes
logger.info("Inicializando componentes...")
if not init_dropbox() or not init_pdf_processor():
    logger.error("FALHA na inicialização! Abortando.")
    sys.exit(1)
logger.info("Inicialização concluída com sucesso!")

if __name__ == '__main__':
    sistema = platform.system()
    
    # Detectar automaticamente o sistema
    if sistema == "Windows":
        # Usar Waitress no Windows
        try:
            from waitress import serve
            logger.info(f"Iniciando servidor Waitress na porta {PORT}")
            print(f"Servidor rodando em http://localhost:{PORT}")
            print("Pressione Ctrl+C para encerrar.")
            serve(app, host='0.0.0.0', port=PORT, threads=1)
        except ImportError:
            print("Erro: Waitress não está instalado. Instale com 'pip install waitress'")
            sys.exit(1)
    else:
        # Usar Gunicorn no Linux/Mac
        try:
            import gunicorn
            logger.info(f"Iniciando Gunicorn na porta {PORT}")
            print(f"Servidor rodando em http://localhost:{PORT}")
            print("Usando Gunicorn. Pressione Ctrl+C para encerrar.")
            os.system(f"gunicorn -w 4 -b 0.0.0.0:{PORT} app:app")
        except ImportError:
            print("Erro: Gunicorn não está instalado. Instale com 'pip install gunicorn'")
            sys.exit(1)