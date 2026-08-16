"""
pipeline.py
───────────
Orquestrador principal do Canal Quiz Shorts.
Executa todos os passos em sequência:

  1. Gerar pergunta curiosa + resposta + CTA de inscrição via Groq AI
  2. Gerar áudio TTS (gancho + resposta + CTA) e legendas SRT
  3. Buscar vídeos relacionados (resposta) via Pexels
  4. Montar Short 1080×1920 com 4 atos (gancho+SFX → countdown 3s → resposta → CTA)
  5. Upload para o YouTube como Short (publicação imediata)

Uso:
    python scripts/pipeline.py
"""

import os
import sys
import json
import traceback
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
sys.path.insert(0, ROOT_DIR)


def _titulo(passo: int, total: int, descricao: str):
    print(f"\n{'─'*60}")
    print(f" PASSO {passo}/{total}: {descricao}")
    print(f"{'─'*60}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "imagens"), exist_ok=True)

    print("\n" + "═"*60)
    print("  🧠  CANAL QUIZ — SHORTS PIPELINE")
    print("       Gancho + SFX → Countdown 3s → Resposta → CTA")
    print("═"*60)

    # ──────────────────────────────────────────────────────────────────────────
    # PASSO 1 — Gerar pergunta + resposta + CTA com Groq AI
    # ──────────────────────────────────────────────────────────────────────────
    _titulo(1, 5, "Gerando quiz + CTA com Groq AI (llama-3.3-70b)...")
    from scripts.gerar_quiz import gerar_quiz

    dados = gerar_quiz()
    quiz_json = os.path.join(OUTPUT_DIR, "quiz.json")

    with open(quiz_json, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    print(f"\n📋 Resumo do quiz:")
    print(f"✅ Quiz gerado — tema: {dados.get('tema', '?')}")
    print(f"   Pergunta  : {dados['pergunta'][:70]}...")
    print(f"   Correta   : {dados.get('letra_correta', '?')}")
    print(f"   CTA       : {dados.get('cta', '?')}")
    print(f"   Título    : {dados.get('titulo', '?')}")

    # ──────────────────────────────────────────────────────────────────────────
    # PASSO 2 — Gerar áudio TTS + legendas SRT
    # ──────────────────────────────────────────────────────────────────────────
    _titulo(2, 5, "Gerando áudios TTS detalhados (gancho, pergunta, opções, explicação, CTA)...")
    from scripts.gerar_audio import gerar as gerar_audio

    audios = gerar_audio(dados, OUTPUT_DIR)

    # ──────────────────────────────────────────────────────────────────────────
    # PASSO 3 — Buscar vídeo da resposta no Pexels
    # ──────────────────────────────────────────────────────────────────────────
    _titulo(3, 5, "Buscando vídeos para a resposta no Pexels...")
    from scripts.buscar_midia import buscar_midias

    video_resposta = buscar_midias(
        termos_resposta=dados.get("termos_imagem_resposta", ["answer", "science"]),
        termos_pergunta=dados.get("termos_imagem_pergunta", ["curiosity", "question"]),
        output_dir=OUTPUT_DIR,
    )
    print(f"✅ Vídeos de resposta concatenados: {video_resposta}")

    # ──────────────────────────────────────────────────────────────────────────
    # PASSO 4 — Montar Short 1080×1920
    # ──────────────────────────────────────────────────────────────────────────
    _titulo(4, 5, "Montando Short 1080×1920 (Show do Milhão com Pexels)...")
    from scripts.montar_video import montar_video

    video_final = montar_video(
        audios=audios,
        video_pexels=video_resposta,
        output_dir=OUTPUT_DIR,
    )

    # ──────────────────────────────────────────────────────────────────────────
    # PASSO 5 — Upload para o YouTube
    # ──────────────────────────────────────────────────────────────────────────
    _titulo(5, 5, "Publicando Short no YouTube...")

    if not os.environ.get("YOUTUBE_REFRESH_TOKEN"):
        print("⚠️  YOUTUBE_REFRESH_TOKEN não configurado.")
        print("   Configure os secrets no GitHub e rode novamente.")
        print(f"\n   Short salvo localmente em: {video_final}")
    else:
        from scripts.upload_youtube import upload_youtube
        video_id = upload_youtube(video_final, dados)
        print(f"\n🎉 SHORT DE QUIZ PUBLICADO COM SUCESSO!")
        print(f"   📱 https://www.youtube.com/shorts/{video_id}")

    # ── Resumo final ─────────────────────────────────────────────────────────
    print("\n" + "═"*60)
    print("  📁 Arquivos gerados:")
    for nome in ["quiz.json", "audio_pergunta.wav", "audio_cta.wav", "audio_resposta.wav", "legendas.srt"]:
        caminho = os.path.join(OUTPUT_DIR, nome)
        if os.path.exists(caminho):
            tamanho = os.path.getsize(caminho)
            print(f"     {nome:<28} {tamanho/1024:.0f} KB")

    for arq in os.listdir(OUTPUT_DIR):
        if arq.endswith(".mp4") and not arq.startswith("img_") and not arq.startswith("video_raw"):
            caminho = os.path.join(OUTPUT_DIR, arq)
            if os.path.exists(caminho):
                tamanho = os.path.getsize(caminho)
                print(f"     {arq:<28} {tamanho/1024/1024:.1f} MB")
                break

    print("═"*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        traceback.print_exc()
        sys.exit(1)
