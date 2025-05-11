import os
import time  # Adicionando a importação de time
import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, Response, send_file
from dotenv import load_dotenv
from dropbox import Dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox_handler import DropboxHandler
from pdf_processor import PDFProcessor
from logger import setup_logger, log_execution_end, get_logger, get_br_time
from config import (
    DEBUG_FILES,
    PORT,
    DROPBOX_BASE_FOLDER,
    DROPBOX_SOURCE_FOLDER_NAME,
    DROPBOX_OUTPUT_FOLDER_NAME,
    DROPBOX_PROCESSED_FOLDER_NAME,
    DROPBOX_SOURCE_PATH,
    DROPBOX_OUTPUT_PATH,
    DROPBOX_PROCESSED_PATH
)
import threading
import time
import os.path
from flask_cors import CORS
import gzip
import io

# Variável global para controlar a inicialização do Dropbox
_dropbox_initialized = False

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
CORS(app)  # Habilitar CORS para permitir requisições do frontend Next.js

# Setup logger
logger = setup_logger()

# Initialize Dropbox handler - criar apenas uma instância global
dropbox_handler = None
pdf_processor = None  # Adiciona a inicialização de pdf_processor como None

# Caminho do arquivo de log
LOG_FILE_PATH = 'workspace.log'

def init_dropbox():
    """
    Inicializa o manipulador do Dropbox com as credenciais configuradas.
    Utiliza apenas o refresh token para autenticação.
    """
    global dropbox_handler
    
    # Obter credenciais de ambiente
    app_key = os.environ.get('APP_KEY')
    app_secret = os.environ.get('APP_SECRET')
    refresh_token = os.environ.get('DROPBOX_API_REFRESH_TOKEN')
    
    if not app_key or not app_secret:
        logger.error("APP_KEY ou APP_SECRET não configurados. Verifique as variáveis de ambiente no arquivo .env")
        return False
    
    if not refresh_token:
        logger.error("DROPBOX_API_REFRESH_TOKEN não configurado. Execute o script get_refresh_token.py para obter um token")
        return False
    
    try:
        # Inicializar com refresh token
        logger.info("Inicializando Dropbox com refresh token")
        dropbox_handler = DropboxHandler(app_key, app_secret, refresh_token)
        
        # Verificar pastas necessárias no Dropbox
        source_folder = dropbox_handler.get_source_folder_path()
        output_folder = dropbox_handler.get_output_folder_path()
        processed_folder = dropbox_handler.get_processed_folder_path()
        
        # Verificar se todas as pastas foram encontradas
        if not source_folder or not output_folder or not processed_folder:
            logger.error("Falha ao encontrar pastas necessárias no Dropbox")
            return False
        
        logger.info("Dropbox inicializado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao inicializar Dropbox: {str(e)}")
        return False

def init_pdf_processor():
    """
    Inicializa o processador de PDF.
    """
    global pdf_processor
    
    try:
        pdf_processor = PDFProcessor(dropbox_handler)
        logger.info("Processador de PDF inicializado com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao inicializar processador de PDF: {str(e)}")
        return False

# Função para verificar a chave de API
def check_api_key():
    api_key = request.headers.get('X-API-Key')
    expected_key = os.environ.get('API_SECRET')
    
    if not api_key or api_key != expected_key:
        return False
    return True

def tail_file(filename, n=10):
    """Retorna as últimas n linhas de um arquivo."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return lines[-n:] if len(lines) >= n else lines
    except Exception as e:
        logger.error(f"Erro ao ler arquivo {filename}: {e}")
        return []

def read_file_chunk(filename, start=0, length=1000):
    """Lê um trecho do arquivo a partir da linha start."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        end = min(start + length, len(lines))
        return {
            'lines': lines[start:end],
            'total_lines': len(lines),
            'start': start,
            'end': end
        }
    except Exception as e:
        logger.error(f"Erro ao ler arquivo {filename}: {e}")
        return {
            'lines': [],
            'total_lines': 0,
            'start': start,
            'end': start
        }

@app.route('/')
def home():
    """
    Home page with information about the PDF processing service.
    Content is loaded from content.md file.
    """
    dropbox_status = "Não Conectado" if not dropbox_handler else "Conectado"
    
    # Load content from markdown file
    try:
        import markdown
        with open('content.md', 'r', encoding='utf-8') as f:
            content = f.read()
        # Replace placeholder with actual API key
        content = content.replace('your-api-secret', os.environ.get('API_SECRET', 'your-api-secret'))
        # Convert markdown to HTML
        md_html = markdown.markdown(content, extensions=['fenced_code', 'tables'])
    except Exception as e:
        logger.error(f"Error loading content file: {str(e)}")
        md_html = "<p>Error loading content. Please check the content.md file.</p>"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF Processing Service</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            body {{ padding: 20px; font-family: Arial, sans-serif; }}
            .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: var(--bs-info); }}
            pre {{ padding: 15px; border-radius: 5px; overflow-x: auto; background-color: var(--bs-dark); }}
            code {{ background-color: var(--bs-secondary-bg); padding: 2px 4px; border-radius: 3px; }}
            .status-box {{ margin-bottom: 20px; }}
        </style>
    </head>
    <body data-bs-theme="dark">
        <div class="container">            
            <div class="content">
                {md_html}
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/stream-logs')
def stream_logs():
    """
    Endpoint para streaming de logs em tempo real usando Server-Sent Events (SSE).
    O cliente receberá atualizações sempre que o arquivo de log for modificado.
    """
    if not check_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    def generate():
        # Posição inicial no arquivo
        last_position = 0
        
        if os.path.exists(LOG_FILE_PATH):
            last_position = os.path.getsize(LOG_FILE_PATH)
        
        # Enviar mensagem de início
        yield f"data: {json.dumps({'event': 'connected', 'message': 'Conexão estabelecida'})}\n\n"
        
        while True:
            try:
                if not os.path.exists(LOG_FILE_PATH):
                    time.sleep(1)
                    continue
                
                current_position = os.path.getsize(LOG_FILE_PATH)
                
                if current_position > last_position:
                    with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
                        f.seek(last_position)
                        new_data = f.read()
                    
                    if new_data:
                        new_lines = new_data.splitlines()
                        for line in new_lines:
                            if line.strip():  # Ignorar linhas vazias
                                yield f"data: {json.dumps({'log': line})}\n\n"
                    
                    last_position = current_position
                
                time.sleep(0.5)  # Verificar a cada meio segundo
            
            except Exception as e:
                error_msg = f"Erro ao ler arquivo de log: {str(e)}"
                logger.error(error_msg)
                yield f"data: {json.dumps({'event': 'error', 'message': error_msg})}\n\n"
                time.sleep(5)  # Esperar um pouco mais em caso de erro
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/download-logs')
def download_logs():
    """
    Endpoint para download do arquivo de log completo.
    """
    if not check_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    if not os.path.exists(LOG_FILE_PATH):
        return jsonify({'error': 'Log file not found'}), 404
    
    return send_file(LOG_FILE_PATH, 
                    mimetype='text/plain', 
                    as_attachment=True, 
                    download_name=f'logs-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log')

@app.route("/process-pdfs", methods=["POST"])
def process_pdfs():
    """
    Endpoint to process PDFs with the same CPF in their filenames.
    Requires a valid API key for authentication.
    """
    # Verificar API Key
    if not check_api_key():
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Verificar se o processador está inicializado
    if not dropbox_handler or not pdf_processor:
        return jsonify({'error': 'Sistema não inicializado corretamente. Reinicie o servidor.'}), 500
    
    try:
        logger.info("INÍCIO PROCESSAMENTO")
        
        # Buscar e processar arquivos PDF
        if not pdf_processor.process_pdfs_from_dropbox():
            return jsonify({'error': 'Falha ao processar PDFs'}), 500
        
        result = pdf_processor.get_processing_stats()
        
        # Log resumido do resultado
        total_processed = sum(result['processed_cpfs'].values())
        total_skipped = result['skipped_cpfs']
        logger.info(f"Processamento concluído: {total_processed} CPFs processados, {total_skipped} ignorados. Total de arquivos: {result['total_files']}")
        
        # Incluir detalhes dos CPFs processados no log
        if result['processed_cpfs']:
            cpfs_list = ", ".join(result['processed_cpfs'].keys())
            logger.info(f"CPFs processados: {cpfs_list}")
        
        logger.info("FIM PROCESSAMENTO")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Erro ao processar PDFs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.after_request
def compress_response(response):
    """Comprime respostas JSON automaticamente com gzip."""
    # Comprimir apenas se o conteúdo for JSON e for grande o suficiente
    if (response.headers.get('Content-Type') == 'application/json' and
            len(response.data) > 1024):  # Comprimir se maior que 1KB
        
        # Criar buffer para compressão
        gzip_buffer = io.BytesIO()
        with gzip.GzipFile(mode='wb', fileobj=gzip_buffer) as f:
            f.write(response.data)
        
        # Substituir dados pela versão comprimida
        response.data = gzip_buffer.getvalue()
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = str(len(response.data))
        response.headers['Vary'] = 'Accept-Encoding'
    
    return response

# Inicializar serviços ao iniciar o aplicativo
if __name__ == '__main__':
    # Tentativas de inicialização
    max_retries = 3
    retry_delay = 5  # segundos
    
    for attempt in range(max_retries):
        if init_dropbox() and init_pdf_processor():
            break
        else:
            logger.warning(f"Tentativa {attempt + 1}/{max_retries} de inicialização falhou. Tentando novamente em {retry_delay} segundos...")
            time.sleep(retry_delay)
    else:
        logger.error(f"Falha em todas as {max_retries} tentativas de inicialização. Encerrando.")
        exit(1)
    
    # Iniciar servidor Flask
    port = int(os.environ.get('PORT', PORT))
    app.run(host='0.0.0.0', port=port, threaded=True)
