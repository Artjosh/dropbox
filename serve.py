"""
Script para iniciar o servidor em modo de produção usando Waitress.
Indicado para ambientes de desenvolvimento local com requisitos de produção.
"""

import os
from waitress import serve
from app import app
from dotenv import load_dotenv
from logger import get_logger

# Configuração
load_dotenv()
logger = get_logger()
PORT = int(os.environ.get('PORT', 5000))

if __name__ == '__main__':
    logger.info(f"Iniciando servidor Waitress na porta {PORT}")
    print(f"Servidor rodando em http://localhost:{PORT}")
    print("Pressione Ctrl+C para encerrar.")
    
    # Iniciar servidor
    serve(app, host='0.0.0.0', port=PORT, threads=4) 