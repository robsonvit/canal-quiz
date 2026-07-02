"""
obter_token.py
──────────────
Script interativo para obter o YOUTUBE_REFRESH_TOKEN da conta do YouTube
(robsonalemanha2025@gmail.com) via OAuth 2.0.

Requer:
- client_secret.json (ou YOUTUBE_CLIENT_ID e SECRET no .env)
"""

import os
import sys
from dotenv import load_dotenv

import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("❌ ERRO: YOUTUBE_CLIENT_ID ou YOUTUBE_CLIENT_SECRET ausente no .env")
        sys.exit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "project_id": "canal-quiz-app",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"]
        }
    }

    print("\n🔐 ABRINDO NAVEGADOR PARA AUTENTICAÇÃO...")
    print("Por favor, faça login com a conta robsonalemanha2025@gmail.com")
    print("1. Escolha a conta de e-mail robsonalemanha2025@gmail.com")
    print("2. IMPORTANTE: Na tela seguinte, você DEVE selecionar o CANAL RVS.")
    print("   Se você não selecionar o canal específico, ele usará o canal padrão (Oração).\n")

    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_config(
        client_config, SCOPES
    )
    
    # Executa o servidor local forçando a tela de seleção de conta e permissão
    creds = flow.run_local_server(port=0, prompt='consent select_account')

    print("\n✅ SUCESSO! Cópia do Refresh Token abaixo:\n")
    print("═"*60)
    print(creds.refresh_token)
    print("═"*60)
    print("\n👉 Copie o valor acima e substitua no arquivo .env a variável YOUTUBE_REFRESH_TOKEN")
    print("👉 Não esqueça de também atualizar o secret no GitHub Actions!")

if __name__ == "__main__":
    main()
