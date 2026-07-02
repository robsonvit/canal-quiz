"""
gerar_audio.py
──────────────
Gera áudio MP3 com voz grave masculina (pt-BR-AntonioNeural) via edge-tts
para o Short de Quiz e produz arquivo SRT de legendas via Groq Whisper.

O áudio é gerado em 2 partes separadas:
  - Parte 1: Texto da PERGUNTA (narrado antes do countdown)
  - Parte 2: Texto da RESPOSTA + CURIOSIDADE (narrado após o countdown)

As legendas SRT são geradas para cada parte separadamente e concatenadas
com offset de tempo correto para sincronizar com o vídeo final.
"""

import asyncio
import os
import json

import edge_tts
from groq import Groq


# ─────────────────────────────────────────────────────────────────────────────
# Configurações da voz
# ─────────────────────────────────────────────────────────────────────────────
VOZ                 = "pt-BR-AntonioNeural"   # Voz masculina natural do Brasil
PALAVRAS_POR_LEGENDA = 4                       # Blocos pequenos para tela mobile


# ─────────────────────────────────────────────────────────────────────────────
# Utilitários de tempo
# ─────────────────────────────────────────────────────────────────────────────
def _segundos_para_hms(segundos: float) -> str:
    horas   = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs    = int(segundos % 60)
    ms      = int(round((segundos - int(segundos)) * 1000))
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{ms:03d}"


def _duracao_mp3(audio_path: str) -> float:
    """Obtém duração do MP3 via mutagen (fallback: subprocess ffprobe)."""
    import subprocess, json as _json
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        audio_path,
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    try:
        dados = _json.loads(resultado.stdout)
        return float(dados["format"]["duration"])
    except Exception:
        return 5.0  # fallback seguro


# ─────────────────────────────────────────────────────────────────────────────
# Geração de áudio com edge-tts
# ─────────────────────────────────────────────────────────────────────────────
async def _sintetizar(texto: str, caminho_mp3: str):
    """Sintetiza texto em MP3 com voz masculina grave."""
    communicate = edge_tts.Communicate(texto, VOZ, rate="-8%", pitch="-4Hz")
    with open(caminho_mp3, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])


# ─────────────────────────────────────────────────────────────────────────────
# Transcrição com Groq Whisper → SRT
# ─────────────────────────────────────────────────────────────────────────────
def _transcrever_para_srt(audio_path: str, offset_segundos: float = 0.0) -> list[str]:
    """
    Transcreve MP3 com Groq Whisper e retorna linhas SRT
    com offset de tempo aplicado (para sincronizar com o vídeo).
    """
    cliente_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    try:
        with open(audio_path, "rb") as f:
            transcricao = cliente_groq.audio.transcriptions.create(
                file=("audio.mp3", f.read()),
                model="whisper-large-v3-turbo",
                response_format="verbose_json",
                language="pt",
            )

        segmentos = (
            transcricao.get("segments", [])
            if isinstance(transcricao, dict)
            else transcricao.segments
        )

        linhas_srt = []
        idx = 1

        for segment in segmentos:
            try:
                start = segment.start + offset_segundos
                end   = segment.end   + offset_segundos
                text  = segment.text
            except AttributeError:
                start = segment["start"] + offset_segundos
                end   = segment["end"]   + offset_segundos
                text  = segment["text"]

            palavras = text.strip().split()
            if not palavras:
                continue

            duracao_total    = (end - start)
            tempo_por_palavra = duracao_total / max(len(palavras), 1)

            for i in range(0, len(palavras), PALAVRAS_POR_LEGENDA):
                chunk       = palavras[i: i + PALAVRAS_POR_LEGENDA]
                chunk_text  = " ".join(chunk)
                chunk_start = start + (i * tempo_por_palavra)
                chunk_end   = start + ((i + len(chunk)) * tempo_por_palavra)

                inicio = _segundos_para_hms(chunk_start)
                fim    = _segundos_para_hms(chunk_end)
                linhas_srt.append(f"{idx}\n{inicio} --> {fim}\n{chunk_text}\n")
                idx += 1

        return linhas_srt

    except Exception as e:
        print(f"⚠️  Groq Whisper falhou: {e} — usando fallback")
        return [f"1\n{_segundos_para_hms(offset_segundos)} --> {_segundos_para_hms(offset_segundos + 5.0)}\n \n"]


# ─────────────────────────────────────────────────────────────────────────────
# Interface pública
# ─────────────────────────────────────────────────────────────────────────────
def gerar(dados_quiz: dict, output_dir: str = "output") -> tuple[str, str, str]:
    """
    Gera os áudios e o SRT unificado para o Short de Quiz.

    Fluxo:
      1. Sintetiza áudio da PERGUNTA → audio_pergunta.mp3
      2. Sintetiza áudio da RESPOSTA → audio_resposta.mp3
      3. Transcreve os dois com Groq Whisper com offset correto
      4. Cria SRT unificado (pergunta + gap de 3s de countdown + resposta)

    Retorna:
      (audio_pergunta_path, audio_resposta_path, srt_path)
    """
    os.makedirs(output_dir, exist_ok=True)

    audio_pergunta_path = os.path.join(output_dir, "audio_pergunta.mp3")
    audio_resposta_path = os.path.join(output_dir, "audio_resposta.mp3")
    srt_path            = os.path.join(output_dir, "legendas.srt")

    texto_pergunta = dados_quiz["pergunta_texto"]
    texto_resposta = dados_quiz["resposta_texto"] + " " + dados_quiz["curiosidade_texto"]

    # ── Passo 1: Sintetizar áudios ────────────────────────────────────────────
    print("🎙️  Sintetizando áudio da PERGUNTA com edge-tts...")
    asyncio.run(_sintetizar(texto_pergunta, audio_pergunta_path))
    print(f"✅ Áudio pergunta: {audio_pergunta_path}")

    print("🎙️  Sintetizando áudio da RESPOSTA com edge-tts...")
    asyncio.run(_sintetizar(texto_resposta, audio_resposta_path))
    print(f"✅ Áudio resposta: {audio_resposta_path}")

    # ── Passo 2: Calcular offset de tempo ─────────────────────────────────────
    duracao_pergunta = _duracao_mp3(audio_pergunta_path)
    COUNTDOWN_DURACAO = 3.0  # segundos de silêncio/countdown
    offset_resposta = duracao_pergunta + COUNTDOWN_DURACAO

    print(f"⏱️  Duração da pergunta : {duracao_pergunta:.1f}s")
    print(f"⏱️  Offset da resposta  : {offset_resposta:.1f}s (pergunta + 3s countdown)")

    # ── Passo 3: Gerar legendas SRT unificado ─────────────────────────────────
    print("📝 Transcrevendo PERGUNTA com Groq Whisper...")
    linhas_pergunta = _transcrever_para_srt(audio_pergunta_path, offset_segundos=0.0)

    print("📝 Transcrevendo RESPOSTA com Groq Whisper...")
    linhas_resposta = _transcrever_para_srt(audio_resposta_path, offset_segundos=offset_resposta)

    # Renumerar as linhas da resposta para continuar a numeração
    idx_base = len(linhas_pergunta) + 1
    linhas_resposta_renumeradas = []
    for idx_rel, bloco in enumerate(linhas_resposta):
        linhas = bloco.split("\n")
        linhas[0] = str(idx_base + idx_rel)  # Corrige índice SRT
        linhas_resposta_renumeradas.append("\n".join(linhas))

    srt_content = "\n".join(linhas_pergunta + linhas_resposta_renumeradas)

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    print(f"✅ Legendas SRT unificadas: {srt_path}")
    return audio_pergunta_path, audio_resposta_path, srt_path


if __name__ == "__main__":
    with open("output/quiz.json", encoding="utf-8") as f:
        data = json.load(f)
    gerar(data)
