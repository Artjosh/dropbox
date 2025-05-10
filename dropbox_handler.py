import os
import io
import tempfile
from dropbox import Dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import WriteMode
from logger import get_logger
from config import (
    DROPBOX_BASE_FOLDER,
    DROPBOX_SOURCE_FOLDER_NAME,
    DROPBOX_OUTPUT_FOLDER_NAME,
    DROPBOX_PROCESSED_FOLDER_NAME,
    DROPBOX_SOURCE_PATH,
    DROPBOX_OUTPUT_PATH,
    DROPBOX_PROCESSED_PATH
)

logger = get_logger()

class DropboxHandler:
    """
    Class to handle all Dropbox operations including file listing, download, upload, and move.
    Supports automatic token refresh using app credentials and refresh token.
    """
    
    def __init__(self, app_key, app_secret, refresh_token):
        """
        Initialize the Dropbox client with app credentials and refresh token.
        This allows for automatic token refresh when tokens expire.
        
        Args:
            app_key (str): Dropbox API app key
            app_secret (str): Dropbox API app secret
            refresh_token (str): OAuth2 refresh token for automatic token renewal
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.refresh_token = refresh_token
        self.source_folder_path = None  # Will store the path where "COMPROVANTE DE PAGAMENTO" is found
        
        # Initialize Dropbox client with refresh token
        try:
            self.dbx = Dropbox(
                oauth2_refresh_token=refresh_token,
                app_key=app_key, 
                app_secret=app_secret
            )
            
            # Test the connection
            self.dbx.users_get_current_account()
            logger.info("Dropbox authentication successful")
        except AuthError as e:
            logger.error(f"Dropbox authentication failed: {str(e)}")
            raise
    
    def find_folder(self, folder_name, parent_path="", max_depth=5):
        """
        Recursively search for a folder with the given name in Dropbox.
        
        Args:
            folder_name (str): Name of the folder to find
            parent_path (str): Path to start searching from
            max_depth (int): Maximum recursion depth to search
            
        Returns:
            str: Full path to the folder if found, None otherwise
        """
        # Break recursion if we've gone too deep
        if max_depth <= 0:
            return None
            
        try:
            logger.info(f"Searching for folder '{folder_name}' in '{parent_path}'")
            
            # List contents of the current directory
            try:
                result = self.dbx.files_list_folder(parent_path)
                if not result:
                    logger.warning(f"No result returned when listing folder: {parent_path}")
                    return None
                
                subdirs = []
                    
                # Check if the folder exists in the current directory
                if hasattr(result, 'entries'):
                    for entry in result.entries:
                        if hasattr(entry, 'is_dir') and entry.is_dir and hasattr(entry, 'name'):
                            # If this is the folder we're looking for
                            if entry.name == folder_name and hasattr(entry, 'path_display'):
                                full_path = entry.path_display
                                logger.info(f"Found folder '{folder_name}' at '{full_path}'")
                                return full_path
                            # Otherwise, add to subdirs list for later recursion
                            if hasattr(entry, 'path_display'):
                                subdirs.append(entry.path_display)
                
                # Continue fetching if there are more results
                while hasattr(result, 'has_more') and result.has_more:
                    if hasattr(result, 'cursor'):
                        result = self.dbx.files_list_folder_continue(result.cursor)
                        if not result:
                            break
                            
                        if hasattr(result, 'entries'):
                            for entry in result.entries:
                                if hasattr(entry, 'is_dir') and entry.is_dir and hasattr(entry, 'name'):
                                    # If this is the folder we're looking for
                                    if entry.name == folder_name and hasattr(entry, 'path_display'):
                                        full_path = entry.path_display
                                        logger.info(f"Found folder '{folder_name}' at '{full_path}'")
                                        return full_path
                                    # Otherwise, add to subdirs list for later recursion
                                    if hasattr(entry, 'path_display'):
                                        subdirs.append(entry.path_display)
                    else:
                        break
                
                # Now recursively search all subdirectories
                for subdir in subdirs:
                    found_path = self.find_folder(folder_name, subdir, max_depth - 1)
                    if found_path:
                        return found_path
                        
            except ApiError as api_error:
                logger.error(f"API error when listing folder {parent_path}: {str(api_error)}")
                # If it's a path error and the path doesn't exist, just return None
                if api_error.error.is_path() and api_error.error.get_path().is_not_found():
                    return None
                # For other API errors, raise them to be handled by the caller
                raise
            
            logger.info(f"Folder '{folder_name}' not found in '{parent_path}'")
            return None
            
        except Exception as e:
            logger.error(f"Error searching for folder '{folder_name}': {str(e)}")
            return None
    
    def get_source_folder_path(self):
        """
        Find the source folder path within the specified base folder.
        DO NOT create it if it doesn't exist.
        
        Returns:
            str: Path to the source folder or None if not found
        """
        if self.source_folder_path:
            return self.source_folder_path
            
        # Use as configurações do config.py
        base_folder = DROPBOX_BASE_FOLDER
        folder_name = DROPBOX_SOURCE_FOLDER_NAME
        target_path = DROPBOX_SOURCE_PATH
        
        try:
            # Verifica se a pasta base existe
            try:
                self.dbx.files_get_metadata(base_folder)
            except ApiError:
                logger.error(f"Pasta base '{base_folder}' não encontrada no Dropbox. Esta pasta deve existir previamente.")
                return None
                
            # Verifica se a pasta alvo existe dentro da pasta base
            try:
                self.dbx.files_get_metadata(target_path)
                logger.info(f"Pasta de origem encontrada em: {target_path}")
                self.source_folder_path = target_path
                return target_path
            except ApiError:
                logger.error(f"Pasta '{folder_name}' não encontrada dentro de '{base_folder}'")
        except Exception as e:
            logger.error(f"Erro ao buscar pasta de origem: {str(e)}")
        
        # Se não encontrada, retorna None
        logger.error(f"Pasta '{folder_name}' não encontrada no Dropbox. Esta pasta deve existir em '{base_folder}'.")
        return None
    
    def get_parent_path(self, path):
        """
        Get the parent path of a given path.
        
        Args:
            path (str): Path to get parent from
            
        Returns:
            str: Parent path
        """
        # Handle root path
        if path == "/" or path == "":
            return "/"
            
        # If path ends with /, remove it
        if path.endswith("/"):
            path = path[:-1]
            
        # Get parent path
        parent = os.path.dirname(path)
        
        # If parent is empty, it means we're at the root
        if parent == "":
            return "/"
            
        return parent
    
    def list_files(self, folder_path=None, recursive=True):
        """
        Lista todos os arquivos PDF de uma pasta do Dropbox.
        
        Args:
            folder_path (str): Caminho para a pasta no Dropbox. Se None, usa a pasta de origem.
            recursive (bool): Se True, lista arquivos em subpastas também.
            
        Returns:
            list: Lista de dicionários com metadados de arquivo
        """
        if folder_path is None:
            folder_path = self.get_source_folder_path()
            
        logger.info(f"Buscando arquivos PDF em: {folder_path}")
        
        # Lista para armazenar os arquivos PDF encontrados
        pdf_files = []
        
        try:
            # Listar arquivos na pasta usando a API direta
            result = self.dbx.files_list_folder(
                folder_path,
                recursive=recursive,
                include_non_downloadable_files=False
            )
            
            # Processar os resultados iniciais
            if hasattr(result, 'entries'):
                for entry in result.entries:
                    # Verificar se tem os atributos necessários
                    if hasattr(entry, 'name') and hasattr(entry, 'path_display'):
                        # Verificar se é um arquivo PDF
                        if entry.name.lower().endswith('.pdf'):
                            # Adicionar à lista como dicionário
                            pdf_files.append({
                                'name': entry.name,
                                'path_display': entry.path_display
                            })
            
            # Continuar buscando se houver mais arquivos
            while hasattr(result, 'has_more') and result.has_more:
                if hasattr(result, 'cursor'):
                    result = self.dbx.files_list_folder_continue(result.cursor)
                    if not result:
                        break
                    
                    if hasattr(result, 'entries'):
                        for entry in result.entries:
                            # Verificar se tem os atributos necessários
                            if hasattr(entry, 'name') and hasattr(entry, 'path_display'):
                                # Verificar se é um arquivo PDF
                                if entry.name.lower().endswith('.pdf'):
                                    # Adicionar à lista como dicionário
                                    pdf_files.append({
                                        'name': entry.name,
                                        'path_display': entry.path_display
                                    })
                else:
                    break
            
            # Log do total de arquivos encontrados
            return pdf_files
            
        except Exception as e:
            logger.error(f"Erro ao listar arquivos PDF em {folder_path}: {str(e)}")
            return []
    
    def download_file(self, file_path):
        """
        Download a file from Dropbox to a temporary file.
        
        Args:
            file_path (str): Path to the file in Dropbox
            
        Returns:
            file: A file-like object containing the downloaded file
        """
        try:
            logger.info(f"Downloading file: {file_path}")
            download_result = self.dbx.files_download(file_path)
            
            if not download_result or len(download_result) < 2:
                logger.error(f"Invalid download result for file {file_path}")
                raise ValueError(f"Failed to download file {file_path}: Invalid response from Dropbox")
                
            metadata, response = download_result
            
            if not response or not hasattr(response, 'content'):
                logger.error(f"No content in response for file {file_path}")
                raise ValueError(f"Failed to download file {file_path}: No content in response")
            
            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file.write(response.content)
            temp_file.flush()
            temp_file.close()
            
            # Return an open file handle for reading
            return open(temp_file.name, 'rb')
        except ApiError as e:
            logger.error(f"Error downloading file {file_path}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading file {file_path}: {str(e)}")
            raise
    
    def upload_file(self, file_obj, destination_path):
        """
        Upload a file to Dropbox.
        
        Args:
            file_obj (file): File-like object to upload
            destination_path (str): Destination path in Dropbox
            
        Returns:
            object: Metadata of the uploaded file
        """
        try:
            logger.info(f"Uploading file to: {destination_path}")
            file_obj.seek(0)  # Ensure we're at the beginning of the file
            return self.dbx.files_upload(
                file_obj.read(),
                destination_path,
                mode=WriteMode.overwrite
            )
        except ApiError as e:
            logger.error(f"Error uploading file to {destination_path}: {str(e)}")
            raise
    
    def move_file(self, from_path, to_path):
        """
        Move a file within Dropbox.
        
        Args:
            from_path (str): Source path in Dropbox
            to_path (str): Destination path in Dropbox
            
        Returns:
            object: Metadata of the moved file
        """
        try:
            logger.info(f"Moving file from {from_path} to {to_path}")
            return self.dbx.files_move_v2(from_path, to_path, autorename=True)
        except ApiError as e:
            logger.error(f"Error moving file from {from_path} to {to_path}: {str(e)}")
            raise
    
    def create_folder_if_not_exists(self, folder_path):
        """
        Create a folder in Dropbox if it doesn't exist.
        
        Args:
            folder_path (str): Path to create in Dropbox
            
        Returns:
            bool: True if folder was created or already exists
        """
        try:
            # Check if folder exists
            self.dbx.files_get_metadata(folder_path)
            logger.info(f"Folder {folder_path} already exists")
            return True
        except ApiError as e:
            # If folder doesn't exist, create it
            if e.error.is_path() and e.error.get_path().is_not_found():
                try:
                    self.dbx.files_create_folder_v2(folder_path)
                    logger.info(f"Created folder: {folder_path}")
                    return True
                except ApiError as create_error:
                    logger.error(f"Error creating folder {folder_path}: {str(create_error)}")
                    raise
            else:
                logger.error(f"Error checking folder {folder_path}: {str(e)}")
                raise
                
    def get_output_folder_path(self):
        """
        Get the path for the output folder (USO_DO_ROBO).
        Must already exist in the same base folder as the source folder.
        
        Returns:
            str: Path to the output folder or None if not found
        """
        # Use as configurações do config.py
        base_folder = DROPBOX_BASE_FOLDER
        output_folder_name = DROPBOX_OUTPUT_FOLDER_NAME
        target_path = DROPBOX_OUTPUT_PATH
        
        try:
            # Verifica se a pasta base existe
            try:
                self.dbx.files_get_metadata(base_folder)
            except ApiError:
                logger.error(f"Pasta base '{base_folder}' não encontrada no Dropbox ao procurar pasta de saída.")
                return None
                
            # Verifica se a pasta alvo existe dentro da pasta base
            try:
                self.dbx.files_get_metadata(target_path)
                logger.info(f"Pasta de saída encontrada em: {target_path}")
                return target_path
            except ApiError:
                logger.error(f"Pasta '{output_folder_name}' não encontrada dentro de '{base_folder}'")
        except Exception as e:
            logger.error(f"Erro ao buscar pasta de saída: {str(e)}")
        
        logger.error(f"Pasta '{output_folder_name}' não encontrada no Dropbox. Esta pasta deve existir em '{base_folder}'.")
        return None
    
    def get_processed_folder_path(self):
        """
        Get the path for the processed folder (COMPROVANTES_DE_PAGAMENTO_PROCESSADOS).
        Will be created in the same base folder as the source and output folders.
        
        Returns:
            str: Path to the processed folder or None if it can't be created
        """
        # Use as configurações do config.py
        base_folder = DROPBOX_BASE_FOLDER
        processed_folder_name = DROPBOX_PROCESSED_FOLDER_NAME
        target_path = DROPBOX_PROCESSED_PATH
        
        try:
            # Verifica se a pasta base existe
            try:
                self.dbx.files_get_metadata(base_folder)
            except ApiError:
                logger.error(f"Pasta base '{base_folder}' não encontrada no Dropbox ao procurar/criar pasta de processados.")
                return None
                
            # Verifica se a pasta de processados já existe
            try:
                self.dbx.files_get_metadata(target_path)
                logger.info(f"Pasta de processados encontrada em: {target_path}")
                return target_path
            except ApiError as e:
                # Se a pasta não existir, tenta criá-la
                if e.error.is_path() and e.error.get_path().is_not_found():
                    try:
                        logger.info(f"Criando pasta de processados em: {target_path}")
                        self.dbx.files_create_folder_v2(target_path)
                        logger.info(f"Pasta criada com sucesso: {target_path}")
                        return target_path
                    except ApiError as create_error:
                        logger.error(f"Erro ao criar pasta de processados: {str(create_error)}")
                        return None
                else:
                    logger.error(f"Erro ao verificar pasta de processados: {str(e)}")
                    return None
        except Exception as e:
            logger.error(f"Erro ao procurar/criar pasta de processados: {str(e)}")
            
        return None
