import os
import re
import io
import string
import tempfile
from PyPDF2 import PdfReader, PdfWriter
from logger import get_logger

logger = get_logger()

class PDFProcessor:
    """
    Classe para processar arquivos PDF, incluindo extração de CPF de nomes de arquivos,
    união de PDFs com o mesmo CPF, e interação com o Dropbox.
    """
    
    def __init__(self, dropbox_handler):
        """
        Inicializa o processador de PDF.
        
        Args:
            dropbox_handler: Instância de DropboxHandler para operações com o Dropbox
        """
        self.dropbox_handler = dropbox_handler
        self.processed_cpfs = {}  # CPFs processados e quantidade de arquivos
        self.skipped_cpfs = 0     # Contagem de CPFs ignorados
        self.total_files = 0      # Total de arquivos encontrados
    
    def extract_cpf_from_filename(self, filename):
        """
        Extrai o CPF do nome do arquivo.
        
        Args:
            filename (str): Nome do arquivo
            
        Returns:
            str: CPF extraído ou None se não encontrado
        """
        # Padrões de CPF: 11 dígitos juntos ou com separadores
        # 00000000000, 000.000.000-00 ou 000 000 000 00
        cpf_pattern = r'\b(\d{3}[.\-\s]?\d{3}[.\-\s]?\d{3}[.\-\s]?\d{2}|\d{11})\b'
        
        match = re.search(cpf_pattern, filename)
        if match:
            # Extrair apenas os dígitos do CPF
            cpf = ''.join(c for c in match.group(1) if c.isdigit())
            return cpf
        
        return None
    
    def merge_pdfs(self, pdf_files):
        """
        Une múltiplos arquivos PDF em um único arquivo.
        
        Args:
            pdf_files (list): Lista de objetos de arquivo PDF para unir
            
        Returns:
            io.BytesIO: Objeto BytesIO contendo o PDF unido
        """
        logger.info(f"Unindo {len(pdf_files)} arquivos PDF")
        
        merger = PdfWriter()
        
        # Adiciona cada PDF ao merger
        for pdf_file in pdf_files:
            try:
                reader = PdfReader(pdf_file)
                if len(reader.pages) > 0:
                    for page in reader.pages:
                        merger.add_page(page)
                else:
                    logger.warning(f"PDF sem páginas detectado")
            except Exception as e:
                logger.error(f"Erro ao ler PDF: {str(e)}")
                # Continua tentando unir os PDFs restantes
                continue
            finally:
                # Retorna ao início do arquivo para futuras operações
                if hasattr(pdf_file, 'seek'):
                    pdf_file.seek(0)
        
        # Cria um objeto BytesIO para armazenar o PDF unido
        output = io.BytesIO()
        merger.write(output)
        output.seek(0)
        
        return output
    
    def process_pdfs_from_dropbox(self):
        """
        Processa arquivos PDF do Dropbox.
        
        Returns:
            bool: True se o processamento foi concluído com sucesso, False caso contrário
        """
        try:
            # Resetar estatísticas
            self.processed_cpfs = {}
            self.skipped_cpfs = 0
            self.total_files = 0
            
            # Obter as pastas necessárias
            source_folder = self.dropbox_handler.get_source_folder_path()
            output_folder = self.dropbox_handler.get_output_folder_path()
            processed_folder = self.dropbox_handler.get_processed_folder_path()
            
            if not source_folder or not output_folder or not processed_folder:
                logger.error("Falha ao configurar pastas necessárias do Dropbox")
                return False
            
            # Obter lista de arquivos PDF
            pdf_files = self.dropbox_handler.list_files()
            self.total_files = len(pdf_files)
            
            logger.info(f"Total de arquivos PDF encontrados: {self.total_files}")
            
            if not pdf_files:
                logger.info("Nenhum arquivo encontrado para processamento")
                return True
            
            # Agrupar arquivos por CPF
            cpf_groups = {}
            for pdf_file in pdf_files:
                filename = os.path.basename(pdf_file['path_display'])
                cpf = self.extract_cpf_from_filename(filename)
                
                if cpf:
                    if cpf not in cpf_groups:
                        cpf_groups[cpf] = []
                    cpf_groups[cpf].append(pdf_file)
            
            logger.info(f"Total de CPFs identificados: {len(cpf_groups)}")
            
            # Processar cada grupo de arquivos
            for cpf, files in cpf_groups.items():
                # Processar apenas CPFs com múltiplos arquivos
                if len(files) > 1:
                    # Download de todos os arquivos
                    downloaded_files = []
                    try:
                        for file in files:
                            file_path = file['path_display']
                            temp_file = self.dropbox_handler.download_file(file_path)
                            downloaded_files.append((temp_file, file_path))
                        
                        # Unir PDFs
                        if downloaded_files:
                            # Criar arquivo unido
                            merged_pdf = self.merge_pdfs([f[0] for f in downloaded_files])
                            
                            # Upload do arquivo unido
                            merged_filename = f"{cpf}_merged.pdf"
                            self.dropbox_handler.upload_file(
                                merged_pdf, 
                                f"{output_folder}/{merged_filename}"
                            )
                            
                            # Mover arquivos processados
                            for _, file_path in downloaded_files:
                                filename = os.path.basename(file_path)
                                self.dropbox_handler.move_file(
                                    file_path, 
                                    f"{processed_folder}/{filename}"
                                )
                            
                            # Adicionar às estatísticas
                            self.processed_cpfs[cpf] = len(files)
                            
                            # Limpeza de arquivos temporários
                            merged_pdf.close()
                            for temp_file, _ in downloaded_files:
                                if hasattr(temp_file, 'close'):
                                    temp_file.close()
                    except Exception as e:
                        logger.error(f"Erro ao processar CPF {cpf}: {str(e)}")
                        self.skipped_cpfs += 1
                        # Continuar com outros CPFs
                else:
                    # CPF com apenas um arquivo: ignorar
                    self.skipped_cpfs += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao processar PDFs: {str(e)}")
            return False
    
    def get_processing_stats(self):
        """
        Retorna estatísticas do último processamento.
        
        Returns:
            dict: Estatísticas de processamento
        """
        total_processed_files = sum(self.processed_cpfs.values())
        
        return {
            "message": f"Processamento concluído: {total_processed_files} arquivos processados",
            "success": True,
            "processed_cpfs": self.processed_cpfs,
            "skipped_cpfs": self.skipped_cpfs,
            "total_processed": total_processed_files,
            "total_files": self.total_files
        }
