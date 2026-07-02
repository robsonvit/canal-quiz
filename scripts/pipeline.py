"""
pipeline.py
───────────
Orquestrador principal do Canal Quiz Shorts.
Executa todos os passos em sequência:

  1. Gerar pergunta curiosa + resposta via Groq AI (llama-3.3-70b)
  2. Gerar áudio TTS da pergunta e da resposta (edge-tts) + legendas SRT
  3. Buscar imagens relacionadas (pergunta + resposta) via Pexels
  4. Montar Short 1080×1920 com 3 atos (pergunta → countdown → resposta)
  5. Upload para o YouTube como Short (publicação imediata)

Uso:
    python scripts/pipeline.py
"""

import os
import sys
import json
import traceback

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
    print("       Modo Engenharia: Pergunta → Countdown → Resposta")
    print("═"*60)

    # ──────────────────────────────────────────────────────────────────────────
    # PASSO 1 — Gerar pergunta + resposta com Groq AI
    # ──────────────────────────────────────────────────────────────────────────
    _titulo(1, 5, "Gerando quiz com Groq AI (llama-3.3-70b)...")
    from scripts.gerar_quiz import gerar_quiz

    dados = gerar_quiz()
    quiz_json = os.path.join(OUTPUT_DIR, "quiz.json")

    with open(quiz_json, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    print(f"\n📋 Resumo do quiz:")
    print(f"   Tema      : {dados.get('tema', '?')}")
    print(f"   Pergunta  : {dados['pergunta_texto'][:70]}...")
    print(f"   Resposta  : {dados['resposta_texto']}")
    print(f"   Título    : {dados.get('titulo', '?')}")

    # ──────────────────────────────────────────────────────────────────────────
    # PASSO 2 — Gerar áudio TTS + legendas SRT
    # ──────────────────────────────────────────────────────────────────────────
    _titulo(2, 5, "Gerando áudio TTS (pt-BR-AntonioNeural) + legendas Groq Whisper...")
    from scripts.gerar_audio import gerar as gerar_audio

    audio_pergunta, audio_resposta, srt_path = gerar_audio(dados, OUTPUT_DIR)

    # ──────────────────────────────────────────────────────────────────────────
    # PASSO 3 — Buscar imagens no Pexels
    # ──────────────────────────────────────────────────────────────────────────
    _titulo(3, 5, "Buscando imagens relacionadas no Pexels...")
    from scripts.buscar_imagem import buscar_imagens

    img_pergunta, img_resposta = buscar_imagens(
        termos_pergunta=dados.get("termos_imagem_pergunta", ["curiosity", "question"]),
        termos_resposta=dados.get("termos_imagem_resposta", ["answer", "science"]),
        output_dir=OUTPUT_DIR,
    )
    print(f"✅ Imagem pergunta: {img_pergunta}")
    print(f"✅ Imagem resposta: {img_resposta}")

    # ──────────────────────────────────────────────────────────────────────────
    # PASSO 4 — Montar Short 1080×1920 com 3 atos
    # ──────────────────────────────────────────────────────────────────────────
    _titulo(4, 5, "Montando Short 1080×1920 (Pergunta → Countdown 3s → Resposta)...")
    from scripts.montar_video import montar_video

    video_final = montar_video(
        img_pergunta   = img_pergunta,
        img_resposta   = img_resposta,
        audio_pergunta = audio_pergunta,
        audio_resposta = audio_resposta,
        legendas_srt   = srt_path,
        output_dir     = OUTPUT_DIR,
        resposta_curta = dados.get("resposta_texto", "")[:60],
        countdown_s    = 3.0,
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
    for nome in ["quiz.json", "audio_pergunta.mp3", "audio_resposta.mp3", "legendas.srt"]:
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
