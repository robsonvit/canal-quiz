"""
gerar_audio.py
──────────────
Gera áudio WAV com voz feminina (pf_dora) via Kokoro TTS
para o Short de Quiz e produz arquivo SRT de legendas via Groq Whisper.

O áudio é gerado em 3 partes separadas (pergunta, CTA, resposta).
As legendas SRT são geradas para cada parte e concatenadas
com offset de tempo correto para sincronizar com o vídeo final.

Estrutura do Short:
  Ato 1 → Gancho (pergunta TTS com efeito sonoro)
  Ato 2 → Countdown 3s (silêncio no áudio principal)
  Ato 3 → Resposta direta + curiosidade
  Ato 4 → CTA de inscrição (apelo aleatório brasileiro)
"""

import asyncio
import os
import json

from groq import Groq


# ─────────────────────────────────────────────────────────────────────────────
# Configurações da voz
# ─────────────────────────────────────────────────────────────────────────────
VOZ                  = "pf_dora"   # Voz feminina do Kokoro TTS
PALAVRAS_POR_LEGENDA = 4           # Blocos pequenos para tela mobile
COUNTDOWN_DURACAO    = 3.0         # segundos de countdown (era 10s)


# ─────────────────────────────────────────────────────────────────────────────
# Utilitários de tempo
# ─────────────────────────────────────────────────────────────────────────────
def _segundos_para_hms(segundos: float) -> str:
    horas   = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs    = int(segundos % 60)
    ms      = int(round((segundos - int(segundos)) * 1000))
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{ms:03d}"


def _duracao_wav(audio_path: str) -> float:
    """Obtém duração do arquivo de áudio via ffprobe."""
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
# Geração de áudio com Kokoro TTS
# ─────────────────────────────────────────────────────────────────────────────
async def _sintetizar(texto: str, caminho_wav: str):
    """Sintetiza texto em WAV com Kokoro TTS."""
    from kokoro import KPipeline
    import soundfile as sf
    import numpy as np

    # 'p' para Português do Brasil
    pipeline = KPipeline(lang_code='p')
    
    # Speed 1.0
    generator = pipeline(texto, voice=VOZ, speed=1.0, split_pattern=r'\n+')
    
    audio_chunks = []
    for i, (gs, ps, audio) in enumerate(generator):
        audio_chunks.append(audio)
        
    if not audio_chunks:
        raise ValueError("Nenhum áudio gerado pelo Kokoro!")
        
    final_audio = np.concatenate(audio_chunks)
    sf.write(caminho_wav, final_audio, 24000)


# ─────────────────────────────────────────────────────────────────────────────
# Transcrição com Groq Whisper → SRT
# ─────────────────────────────────────────────────────────────────────────────
def _transcrever_para_srt(audio_path: str, offset_segundos: float = 0.0) -> list[str]:
    """
    Transcreve WAV com Groq Whisper e retorna linhas SRT
    com offset de tempo aplicado (para sincronizar com o vídeo).
    """
    cliente_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    try:
        with open(audio_path, "rb") as f:
            transcricao = cliente_groq.audio.transcriptions.create(
                file=("audio.wav", f.read()),
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
def gerar(dados_quiz: dict, output_dir: str = "output") -> tuple[str, str, str, str, str]:
    """
    Gera os áudios e o SRT unificado para o Short de Quiz.

    Fluxo:
      1. Sintetiza áudio da PERGUNTA (gancho) → audio_pergunta.wav
      2. Sintetiza áudio da RESPOSTA + curiosidade → audio_resposta.wav
      3. Sintetiza áudio do CTA de inscrição → audio_cta.wav
      4. Transcreve os três com Groq Whisper com offset correto
      5. Cria SRT unificado (pergunta + gap de 3s countdown + resposta + CTA)

    Retorna:
      (audio_pergunta_path, audio_cta_path, audio_resposta_path, srt_path)

    Nota: o CTA agora vem de dados_quiz["cta_inscricao"] (gerado pela IA
    com apelo aleatório: superstição, história ou promessa).
    """
    os.makedirs(output_dir, exist_ok=True)

    audio_pergunta_path = os.path.join(output_dir, "audio_pergunta.wav")
    audio_cta_path      = os.path.join(output_dir, "audio_cta.wav")
    audio_resposta_path = os.path.join(output_dir, "audio_resposta.wav")
    srt_path            = os.path.join(output_dir, "legendas.srt")

    texto_pergunta = dados_quiz["pergunta_texto"]
    texto_resposta = dados_quiz["resposta_texto"] + " " + dados_quiz["curiosidade_texto"]

    # CTA agora é gerado dinamicamente pela IA (superstição / história / promessa)
    texto_cta = dados_quiz.get(
        "cta_inscricao",
        "Me segue para não perder as próximas perguntas!"  # fallback seguro
    )

    # ── Passo 1: Sintetizar áudios ────────────────────────────────────────────
    print(f"🎙️  Sintetizando áudio do GANCHO com Kokoro TTS (Voz: {VOZ})...")
    asyncio.run(_sintetizar(texto_pergunta, audio_pergunta_path))
    print(f"✅ Áudio gancho (pergunta): {audio_pergunta_path}")

    print(f"🎙️  Sintetizando áudio da RESPOSTA com Kokoro TTS (Voz: {VOZ})...")
    asyncio.run(_sintetizar(texto_resposta, audio_resposta_path))
    print(f"✅ Áudio resposta: {audio_resposta_path}")

    print(f"🎙️  Sintetizando áudio do CTA com Kokoro TTS (Voz: {VOZ})...")
    print(f"   Texto CTA: {texto_cta}")
    asyncio.run(_sintetizar(texto_cta, audio_cta_path))
    print(f"✅ Áudio CTA: {audio_cta_path}")

    # ── Passo 2: Calcular offsets de tempo ────────────────────────────────────
    duracao_pergunta = _duracao_wav(audio_pergunta_path)
    duracao_resposta = _duracao_wav(audio_resposta_path)
    # O countdown (3s) vem depois da pergunta
    offset_resposta  = duracao_pergunta + COUNTDOWN_DURACAO
    # O CTA vem depois da resposta
    offset_cta       = offset_resposta + duracao_resposta

    print(f"⏱️  Duração da pergunta : {duracao_pergunta:.1f}s")
    print(f"⏱️  Countdown           : {COUNTDOWN_DURACAO:.0f}s")
    print(f"⏱️  Duração da resposta : {duracao_resposta:.1f}s")
    print(f"⏱️  Offset do CTA       : {offset_cta:.1f}s")

    # ── Passo 3: Gerar legendas SRT unificado ─────────────────────────────────
    print("📝 Transcrevendo GANCHO com Groq Whisper...")
    linhas_pergunta = _transcrever_para_srt(audio_pergunta_path, offset_segundos=0.0)

    print("📝 Transcrevendo RESPOSTA com Groq Whisper...")
    linhas_resposta = _transcrever_para_srt(audio_resposta_path, offset_segundos=offset_resposta)

    print("📝 Transcrevendo CTA com Groq Whisper...")
    linhas_cta = _transcrever_para_srt(audio_cta_path, offset_segundos=offset_cta)

    # Renumerar as linhas da resposta e do CTA
    idx_base = len(linhas_pergunta) + 1
    linhas_resposta_renumeradas = []
    for idx_rel, bloco in enumerate(linhas_resposta):
        linhas = bloco.split("\n")
        linhas[0] = str(idx_base + idx_rel)
        linhas_resposta_renumeradas.append("\n".join(linhas))

    idx_base += len(linhas_resposta)
    linhas_cta_renumeradas = []
    for idx_rel, bloco in enumerate(linhas_cta):
        linhas = bloco.split("\n")
        linhas[0] = str(idx_base + idx_rel)
        linhas_cta_renumeradas.append("\n".join(linhas))

    srt_content = "\n".join(
        linhas_pergunta
        + linhas_resposta_renumeradas
        + linhas_cta_renumeradas
    )

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    print(f"✅ Legendas SRT unificadas: {srt_path}")
    return audio_pergunta_path, audio_cta_path, audio_resposta_path, srt_path


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    with open("output/quiz.json", encoding="utf-8") as f:
        data = json.load(f)
    gerar(data)
