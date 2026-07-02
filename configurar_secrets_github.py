"""
configurar_secrets_github.py
────────────────────────────
Script auxiliar para configurar automaticamente os secrets do repositório
canal-quiz no GitHub usando a GitHub CLI (gh).

Uso:
    python configurar_secrets_github.py

Pré-requisito: `gh auth login` deve ter sido executado antes.
"""

import subprocess
import sys
import os

# ── Carrega variáveis do .env ──────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

REPO = "canal-quiz"  # Nome do repositório no GitHub

SECRETS = {
    "GROQ_API_KEY":          os.environ.get("GROQ_API_KEY", ""),
    "PEXELS_API_KEY":        os.environ.get("PEXELS_API_KEY", ""),
    "YOUTUBE_CLIENT_ID":     os.environ.get("YOUTUBE_CLIENT_ID", ""),
    "YOUTUBE_CLIENT_SECRET": os.environ.get("YOUTUBE_CLIENT_SECRET", ""),
    "YOUTUBE_REFRESH_TOKEN": os.environ.get("YOUTUBE_REFRESH_TOKEN", ""),
}


def configurar_secret(nome: str, valor: str):
    if not valor:
        print(f"⚠️  {nome}: vazio — pulando")
        return

    resultado = subprocess.run(
        ["gh", "secret", "set", nome, "--body", valor, "--repo", REPO],
        capture_output=True,
        text=True,
    )

    if resultado.returncode == 0:
        print(f"✅ {nome}: configurado com sucesso")
    else:
        print(f"❌ {nome}: falhou — {resultado.stderr.strip()}")


if __name__ == "__main__":
    print("🔐 Configurando secrets do repositório GitHub...")
    print(f"   Repositório: {REPO}\n")

    for nome, valor in SECRETS.items():
        configurar_secret(nome, valor)

    print("\n✅ Pronto! Verifique em:")
    print(f"   https://github.com/[usuario]/{REPO}/settings/secrets/actions")
