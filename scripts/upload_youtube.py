"""
upload_youtube.py
─────────────────
Faz upload do Short de Quiz para o YouTube via YouTube Data API v3
usando credenciais OAuth 2.0 (refresh token).

  ✅ Publicação IMEDIATA (Shorts têm melhor alcance imediato)
  ✅ Título formatado para Short com emoji e #Shorts
  ✅ Descrição curta (≤ 500 chars)
  ✅ Tags incluem #Shorts, #Quiz, #Curiosidades
  ✅ categoryId=27 (Education) — melhor para quiz/curiosidades
  ✅ Sem thumbnail customizada (Shorts usam frame automático)
  ✅ containsSyntheticMedia=True (declara uso de IA/TTS)

Secrets necessários no GitHub:
  YOUTUBE_CLIENT_ID
  YOUTUBE_CLIENT_SECRET
  YOUTUBE_REFRESH_TOKEN
"""

import os
import re
import json

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


def _obter_credenciais() -> Credentials:
    """Constrói credenciais OAuth a partir dos secrets do ambiente."""
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    creds.refresh(Request())
    return creds


def _sanitizar_nome_arquivo(titulo: str) -> str:
    nome = re.sub(r'[\\/*?:"<>|#]', '', titulo)
    nome = re.sub(r'\s+', '_', nome.strip())
    nome = re.sub(r'_{2,}', '_', nome)
    nome = nome[:80].rstrip('_')
    return nome + ".mp4"


def _renomear_video(video_path: str, titulo: str) -> str:
    diretorio = os.path.dirname(video_path)
    novo_nome = _sanitizar_nome_arquivo(titulo)
    novo_path = os.path.join(diretorio, novo_nome)

    if os.path.exists(novo_path) and novo_path != video_path:
        os.remove(novo_path)

    os.rename(video_path, novo_path)
    print(f"   📁 Arquivo renomeado: {novo_nome}")
    return novo_path


def upload_youtube(
    video_path: str,
    metadata: dict,
) -> str:
    """
    Faz upload do Short de Quiz para o YouTube com publicação imediata.
    Retorna o ID do vídeo criado.

    video_path  → caminho do arquivo MP4 (1080×1920)
    metadata    → dict com titulo, descricao, tags, pergunta_texto, resposta_texto
    """
    creds   = _obter_credenciais()
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    # ── Metadados ─────────────────────────────────────────────────────────────
    titulo    = metadata.get("titulo", "🧠 Quiz Rápido #Shorts")[:100]
    descricao = metadata.get("descricao", "")[:500]
    tags      = metadata.get("tags", [])

    # Garante tags essenciais para o algoritmo
    tags_essenciais = ["Shorts", "Quiz", "Curiosidades", "Você Sabia"]
    for tag in tags_essenciais:
        if tag not in tags:
            tags = [tag] + tags

    # ── Renomear arquivo ──────────────────────────────────────────────────────
    if os.path.exists(video_path):
        video_path = _renomear_video(video_path, titulo)

    # ── Body da requisição ────────────────────────────────────────────────────
    body = {
        "snippet": {
            "title":                titulo,
            "description":          descricao,
            "tags":                 tags,
            "categoryId":           "27",      # Education — melhor para quiz/curiosidades
            "defaultLanguage":      "pt-BR",
            "defaultAudioLanguage": "pt-BR",
        },
        "status": {
            "privacyStatus":           "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids":             False,
            "containsSyntheticMedia":  True,   # Declara uso de IA (TTS + Groq)
        },
    }

    # ── Upload ────────────────────────────────────────────────────────────────
    print(f"📤 Iniciando upload do Short de Quiz para o YouTube...")
    print(f"   Título    : {titulo}")
    print(f"   Tags      : {len(tags)} tags")
    print(f"   Categoria : Education (27)")
    print(f"   Status    : Público imediato")

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,
    )

    request  = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"   Upload: {pct}%", end="\r")

    video_id = response.get("id", "")
    print(f"\n✅ Short publicado! ID: {video_id}")
    print(f"   📱 https://www.youtube.com/shorts/{video_id}")

    return video_id


if __name__ == "__main__":
    with open("output/quiz.json", encoding="utf-8") as f:
        data = json.load(f)
    upload_youtube("output/video_final.mp4", data)
