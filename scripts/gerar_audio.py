"""
gerar_audio.py
──────────────
Gera áudio MP3 com voz do Silvio Santos via Fish Audio API
para o Short de Quiz e produz arquivo SRT de legendas com gerador proporcional.

O áudio é gerado em 3 partes separadas (pergunta, CTA, resposta).
As legendas SRT são geradas para cada parte e concatenadas
com offset de tempo correto para sincronizar com o vídeo final.
"""

import os
import json
import requests

# ─────────────────────────────────────────────────────────────────────────────
# Configurações da voz
# ─────────────────────────────────────────────────────────────────────────────
FISH_VOICE_ID        = "c750998c83cf45aabcec7aee2538dba2" # Silvio Santos
PALAVRAS_POR_LEGENDA = 4
COUNTDOWN_DURACAO    = 3.0

def _segundos_para_hms(segundos: float) -> str:
    horas   = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs    = int(segundos % 60)
    ms      = int(round((segundos - int(segundos)) * 1000))
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{ms:03d}"

def _duracao_audio(audio_path: str) -> float:
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
        return 5.0

def _sintetizar(texto: str, output_file: str):
    """Sintetiza texto em MP3 com Fish Audio."""
    api_key = os.environ.get("FISH_API_KEY")
    if not api_key:
        raise ValueError("ERRO: FISH_API_KEY não foi encontrada nas variáveis de ambiente.")

    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "model": "s2.1-pro-free"
    }
    payload = {
        "text": texto,
        "reference_id": FISH_VOICE_ID,
        "format": "mp3" # garantindo formato
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        with open(output_file, 'wb') as f:
            f.write(response.content)
    else:
        raise RuntimeError(f"Erro na API Fish Audio: {response.status_code} - {response.text}")

def _gerar_srt_proporcional(texto: str, audio_path: str, offset_segundos: float = 0.0) -> list[str]:
    """Gera linhas SRT dividindo o texto matematicamente pelo tempo do áudio, sem depender de API externa."""
    duracao_total = _duracao_audio(audio_path)
    palavras = texto.strip().split()
    if not palavras:
        return [f"1\n{_segundos_para_hms(offset_segundos)} --> {_segundos_para_hms(offset_segundos + duracao_total)}\n \n"]
        
    linhas_srt = []
    idx = 1
    tempo_por_palavra = duracao_total / max(len(palavras), 1)
    
    for i in range(0, len(palavras), PALAVRAS_POR_LEGENDA):
        chunk = palavras[i: i + PALAVRAS_POR_LEGENDA]
        chunk_text = " ".join(chunk)
        chunk_start = offset_segundos + (i * tempo_por_palavra)
        chunk_end = offset_segundos + ((i + len(chunk)) * tempo_por_palavra)
        
        inicio = _segundos_para_hms(chunk_start)
        fim = _segundos_para_hms(chunk_end)
        linhas_srt.append(f"{idx}\n{inicio} --> {fim}\n{chunk_text}\n")
        idx += 1
        
    return linhas_srt

def gerar(dados_quiz: dict, output_dir: str = "output") -> tuple[str, str, str, str, str]:
    os.makedirs(output_dir, exist_ok=True)

    audio_gancho      = os.path.join(output_dir, "audio_gancho.mp3")
    audio_pergunta    = os.path.join(output_dir, "audio_pergunta.mp3")
    audio_opts        = [os.path.join(output_dir, f"audio_opt{i+1}.mp3") for i in range(4)]
    audio_tempo       = os.path.join(output_dir, "audio_tempo.mp3")
    audio_rev_curta   = os.path.join(output_dir, "audio_rev_curta.mp3")
    audio_explicacao  = os.path.join(output_dir, "audio_explicacao.mp3")
    audio_cta         = os.path.join(output_dir, "audio_cta.mp3")
    srt_path          = os.path.join(output_dir, "legendas.srt")

    # Textos
    texto_gancho = dados_quiz.get('gancho', '')
    texto_pergunta = dados_quiz.get('pergunta', '')
    textos_opts = [f"Opção {i+1}: {alt}." for i, alt in enumerate(dados_quiz.get('alternativas', []))]
    texto_tempo = "Tempo na tela!"
    correta_num = dados_quiz.get('letra_correta', 1)
    texto_rev_curta = f"A resposta certa é a número {correta_num}!"
    texto_explicacao = dados_quiz.get('explicacao', '')
    texto_cta = "Se você acertou, comente seu pix que vou mandar seu prêmio! E se gostava do Silvio, me segue para continuar o show do milhão!"

    print("🎙️ Sintetizando blocos TTS separados para sincronia...")
    _sintetizar(texto_gancho, audio_gancho)
    _sintetizar(texto_pergunta, audio_pergunta)
    for i, t_opt in enumerate(textos_opts):
        _sintetizar(t_opt, audio_opts[i])
    _sintetizar(texto_tempo, audio_tempo)
    _sintetizar(texto_rev_curta, audio_rev_curta)
    _sintetizar(texto_explicacao, audio_explicacao)
    _sintetizar(texto_cta, audio_cta)

    # Obter durações
    dur_gancho = _duracao_audio(audio_gancho)
    dur_pergunta = _duracao_audio(audio_pergunta)
    dur_opts = [_duracao_audio(a) for a in audio_opts]
    dur_tempo = _duracao_audio(audio_tempo)
    dur_countdown = 5.0
    dur_rev_curta = _duracao_audio(audio_rev_curta)
    dur_explicacao = _duracao_audio(audio_explicacao)
    
    # SFX paths
    sfx_noti = os.path.join("data", "sfx_notificacao.mp3")
    sfx_money = os.path.join("ADUIOS", "som dinheiro 2.mp3")
    sfx_opt = os.path.join("data", "sfx_opcao.mp3")
    sfx_correct = os.path.join("data", "sfx_resposta.mp3")

    d_noti = _duracao_audio(sfx_noti) if os.path.exists(sfx_noti) else 0.0
    d_money = _duracao_audio(sfx_money) if os.path.exists(sfx_money) else 0.0
    d_opt_sfx = _duracao_audio(sfx_opt) if os.path.exists(sfx_opt) else 0.0

    # Calcular offsets absolutos
    offset = 0.0
    offset += d_noti
    offset += dur_gancho
    offset += dur_pergunta
    for d in dur_opts:
        offset += d_opt_sfx
        offset += d
    offset += dur_tempo
    offset += dur_countdown
    offset += dur_rev_curta
    
    print("📝 Gerando legendas GANCHO (Legenda no meio da tela)...")
    linhas_gancho = _gerar_srt_proporcional(texto_gancho, audio_gancho, offset_segundos=d_noti)
    
    srt_gancho_path = os.path.join(output_dir, "legendas_gancho.srt")
    
    srt_gancho_blocks = []
    idx_g = 1
    for bloco in linhas_gancho:
        partes = bloco.split("\n")
        if len(partes) >= 2:
            partes[0] = str(idx_g)
            srt_gancho_blocks.append("\n".join(partes))
            idx_g += 1
            
    with open(srt_gancho_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(srt_gancho_blocks))

    # Daqui pra frente queremos legendas (Explicação + CTA)
    offset_explicacao = offset
    offset_cta = offset_explicacao + dur_explicacao

    print("📝 Gerando legendas EXPLICAÇÃO (Com legenda)...")
    linhas_explicacao = _gerar_srt_proporcional(texto_explicacao, audio_explicacao, offset_segundos=offset_explicacao)

    print("📝 Gerando legendas CTA (Com legenda)...")
    linhas_cta = _gerar_srt_proporcional(texto_cta, audio_cta, offset_segundos=offset_cta)

    # Renumerar blocos SRT base
    todas_linhas = [linhas_explicacao, linhas_cta]
    srt_content_blocks = []
    idx = 1
    for linhas_bloco in todas_linhas:
        for bloco in linhas_bloco:
            partes = bloco.split("\n")
            if len(partes) >= 2:
                partes[0] = str(idx)
                srt_content_blocks.append("\n".join(partes))
                idx += 1

    srt_content = "\n\n".join(srt_content_blocks)
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    return {
        "audio_gancho": audio_gancho,
        "audio_pergunta": audio_pergunta,
        "audio_opts": audio_opts,
        "audio_tempo": audio_tempo,
        "audio_rev_curta": audio_rev_curta,
        "audio_explicacao": audio_explicacao,
        "audio_cta": audio_cta,
        "legendas_srt": srt_path,
        "legendas_gancho_srt": srt_gancho_path,
        "dur_opts": dur_opts
    }

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    with open("output/quiz.json", encoding="utf-8") as f:
        data = json.load(f)
    gerar(data)
