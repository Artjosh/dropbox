import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_SECRET = os.environ.get("API_SECRET", "")

# Dropbox Configuration
DROPBOX_ACCESS_TOKEN = os.environ.get("DROPBOX_ACCESS_TOKEN", "")

# Logging configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Debug configuration
DEBUG_FILES = False  # Controla se o debug de arquivos está ativado
DEBUG_FILE_PATH = "debug_files.log"  # Caminho para o arquivo de debug

# Configurações de pastas do Dropbox

# Pasta base para todas as operações
DROPBOX_BASE_FOLDER = "/aaaa"

# Nome da pasta de origem onde os PDFs serão buscados
DROPBOX_SOURCE_FOLDER_NAME = "COMPROVANTE DE PAGAMENTO"

# Nome da pasta de saída onde os PDFs mesclados serão salvos
DROPBOX_OUTPUT_FOLDER_NAME = "USO_DO_ROBO"

# Nome da pasta onde os PDFs processados serão movidos
DROPBOX_PROCESSED_FOLDER_NAME = "COMPROVANTES_DE_PAGAMENTO_PROCESSADOS"

# Caminho completo das pastas (para conveniência)
DROPBOX_SOURCE_PATH = f"{DROPBOX_BASE_FOLDER}/{DROPBOX_SOURCE_FOLDER_NAME}"
DROPBOX_OUTPUT_PATH = f"{DROPBOX_BASE_FOLDER}/{DROPBOX_OUTPUT_FOLDER_NAME}"
DROPBOX_PROCESSED_PATH = f"{DROPBOX_BASE_FOLDER}/{DROPBOX_PROCESSED_FOLDER_NAME}"

# Configurações da aplicação
PORT = 5000
API_KEY = "josh_box"  # Chave de API para autenticação

# Credenciais do Dropbox
# Estas credenciais são substituídas pelos valores definidos no arquivo .env, se disponíveis
DROPBOX_APP_KEY = "i3ufuxno7dxtj1b"
DROPBOX_APP_SECRET = "gqg9btwf9btk2hd"
DROPBOX_API_REFRESH_TOKEN = ""  # Será preenchido pelo script get_refresh_token.py
