#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para obter o refresh token do Dropbox para autenticação permanente.

Este script deve ser executado apenas uma vez manualmente para gerar um 
refresh token permanente que será usado pelo aplicativo para autenticação 
automática no Dropbox.
"""

import os
import webbrowser
import json
import requests
from dotenv import load_dotenv

# Carregar variáveis de ambiente, caso existam
load_dotenv()

# Usar as credenciais do arquivo .env
APP_KEY = os.environ.get('APP_KEY')
APP_SECRET = os.environ.get('APP_SECRET')

# URL de autorização Dropbox
AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
# URL para trocar o código por token
TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
# URL de redirecionamento - usar localhost para aplicações locais
REDIRECT_URI = "http://localhost"

def clear_screen():
    """Limpa a tela para melhor visibilidade das instruções."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_authorization_url():
    """
    Gera a URL de autorização para obter o código.
    
    Returns:
        str: URL de autorização completa
    """
    # Construir a URL com query parameters
    auth_url = f"{AUTH_URL}?client_id={APP_KEY}&response_type=code&redirect_uri={REDIRECT_URI}&token_access_type=offline"
    
    return auth_url

def exchange_code_for_token(auth_code):
    """
    Troca o código de autorização por um refresh token.
    
    Args:
        auth_code (str): Código de autorização obtido
        
    Returns:
        dict: Resposta contendo access_token e refresh_token
    """
    data = {
        'code': auth_code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI,
        'client_id': APP_KEY,
        'client_secret': APP_SECRET
    }
    
    print(f"\nEnviando solicitação para obter o token com o código: {auth_code}")
    response = requests.post(TOKEN_URL, data=data)
    
    if response.status_code != 200:
        print(f"Erro ao obter token: {response.status_code}")
        print(response.text)
        return None
    
    return response.json()

def save_refresh_token(token_data):
    """
    Salva o refresh token em um arquivo .env.
    
    Args:
        token_data (dict): Dados retornados da API contendo o refresh token
    """
    print("\nResposta da API:")
    print(json.dumps(token_data, indent=2))
    
    # Extrair o refresh token da resposta
    refresh_token = token_data.get('refresh_token')
    
    if not refresh_token:
        print("Erro: refresh_token não encontrado na resposta.")
        return False
    
    # Caminho para o arquivo .env
    env_path = '.env'
    
    # Verificar se o arquivo .env já existe
    if os.path.exists(env_path):
        # Ler o conteúdo atual
        with open(env_path, 'r', encoding='utf-8') as env_file:
            lines = env_file.readlines()
        
        # Filtrar linhas existentes para manter outras variáveis
        filtered_lines = [line for line in lines 
                         if not line.startswith('DROPBOX_API_REFRESH_TOKEN=')]
        
        # Adicionar o novo refresh token
        filtered_lines.append(f"DROPBOX_API_REFRESH_TOKEN={refresh_token}\n")
        
        # Escrever de volta ao arquivo
        with open(env_path, 'w', encoding='utf-8') as env_file:
            env_file.writelines(filtered_lines)
    else:
        # Criar novo arquivo .env
        with open(env_path, 'w', encoding='utf-8') as env_file:
            env_file.write(f"DROPBOX_API_REFRESH_TOKEN={refresh_token}\n")
    
    print(f"\nRefresh token salvo com sucesso no arquivo .env:")
    print(f"DROPBOX_API_REFRESH_TOKEN={refresh_token}")
    return True

def main():
    """Fluxo principal para obter e salvar o refresh token."""
    clear_screen()
    
    print("=" * 80)
    print("OBTENÇÃO DO REFRESH TOKEN DO DROPBOX".center(80))
    print("=" * 80)
    print("\nEste script ajudará você a obter um refresh token permanente para o Dropbox.")
    
    print("\nCredenciais do aplicativo:")
    print(f"  - App Key: {APP_KEY}")
    print(f"  - App Secret: {APP_SECRET}")
    
    if not APP_KEY or not APP_SECRET:
        print("\nERRO: Credenciais do Dropbox não configuradas.")
        print("Defina APP_KEY e APP_SECRET no arquivo .env")
        return
    
    print("\nVocê será redirecionado para a página de autorização do Dropbox.")
    print("Após autorizar o acesso, você será redirecionado para uma URL que não funciona (isso é normal).")
    print("COPIE o código da URL redirecionada.")
    
    # Obter a URL de autorização
    auth_url = get_authorization_url()
    
    print("\nURL de autorização:")
    print(auth_url)
    
    # Tentar abrir o navegador automaticamente
    print("\nAbrindo o navegador...")
    webbrowser.open(auth_url)
    
    print("\nApós autorizar, o navegador redirecionará para uma página que NÃO CARREGA.")
    print("Isso é NORMAL. Na barra de endereços, você verá algo como:")
    print("http://localhost/?code=XXXXXXXXXXXXXXX")
    
    # Aguardar entrada do usuário
    print("\nDigite APENAS o código que aparece após '?code=' na URL:")
    auth_code = input("Código: ").strip()
    
    print("\nObtendo refresh token...")
    
    # Trocar o código pelo refresh token
    token_data = exchange_code_for_token(auth_code)
    
    if not token_data:
        print("Falha ao obter o refresh token. Verifique o código e tente novamente.")
        return
    
    # Salvar o refresh token
    if save_refresh_token(token_data):
        print("\nProcesso concluído com sucesso!")
        print("A aplicação agora usará o refresh token para autenticação automática no Dropbox.")
    else:
        print("\nErro ao salvar o refresh token.")

if __name__ == "__main__":
    main() 