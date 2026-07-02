"""
montar_video.py
───────────────
Monta o Short final 1080×1920 (9:16) para o YouTube no formato Quiz:

  ATO 1 — PERGUNTA (~5-8s) + CTA (~5s)
    • Fundo de cor sólida dinâmica (sem imagem)
    • Áudio TTS da pergunta
    • Áudio TTS do CTA
    • Legendas na tela (amarelo puro com borda preta)
    • Overlay "❓ DESAFIO RÁPIDO" no topo

  ATO 2 — COUNTDOWN (10s)
    • Fundo sólido continua, com overlay escurecido
    • Números 10 → 1 centralizados, animados
    • Texto "Você sabe a resposta?" acima do número
    • Música de QUIZ (volume alto)

  ATO 3 — RESPOSTA (~8-12s)
    • Vídeo vertical relacionado à resposta (múltiplos vídeos do Pexels)
    • Áudio TTS da resposta + curiosidade
    • Legendas na tela
    • Overlay "✅ RESPOSTA:" no topo com a resposta curta em caixa colorida
    • Música volta ao volume suave
"""

import os
import json
import subprocess
import re

def _duracao_audio(audio_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        audio_path,
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    try:
        dados = json.loads(resultado.stdout)
        return float(dados["format"]["duration"])
    except Exception:
        raise RuntimeError(f"Não foi possível obter duração de: {audio_path}")


def _escape_srt_path(path: str) -> str:
    path = path.replace("\\", "/")
    path = re.sub(r"^([A-Za-z]):", r"\1\\:", path)
    return path


def _escape_drawtext(texto: str) -> str:
    return (texto
            .replace("\\", "\\\\")
            .replace("'",  "\\'")
            .replace(":",  "\\:")
            .replace("%",  "\\%")
            .replace("[",  "\\[")
            .replace("]",  "\\]"))


def _concatenar_audios(audio_p: str, audio_cta: str, silencio_s: float, audio_r: str, output: str):
    """
    Concatena Pergunta + CTA + Silêncio de 10s + Resposta
    """
    silencio_path = output.replace(".mp3", "_silencio.mp3")

    cmd_silencio = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(silencio_s),
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        silencio_path,
    ]
    subprocess.run(cmd_silencio, capture_output=True, check=True)

    lista_path = output.replace(".mp3", "_concat.txt")
    with open(lista_path, "w") as f:
        for p in [audio_p, audio_cta, silencio_path, audio_r]:
            f.write(f"file '{os.path.abspath(p).replace(chr(92), '/')}'\n")

    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", lista_path,
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        output,
    ]
    subprocess.run(cmd_concat, capture_output=True, check=True)

    for f in [silencio_path, lista_path]:
        if os.path.exists(f):
            os.remove(f)


def _baixar_musica_quiz(dest: str):
    """Baixa música estilo Quiz animado ou gera silêncio em caso de falha"""
    import requests
    url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
    try:
        print(f"🎵 Baixando música de quiz: {url}")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(url, headers=headers, stream=True, timeout=15)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        print(f"⚠️ Falha ao baixar música de quiz: {e}")
        print("🎵 Gerando áudio de silêncio como fallback para não quebrar o vídeo...")
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "60", "-c:a", "libmp3lame", dest]
        subprocess.run(cmd, capture_output=True)


def montar_video(
    video_resposta: str,
    audio_pergunta: str,
    audio_cta: str,
    audio_resposta: str,
    legendas_srt: str,
    output_dir: str = "output",
    resposta_curta: str = "",
    countdown_s: float = 10.0,
) -> str:
    """
    Monta o Short de Quiz com 3 atos principais:
      Ato 1: Fundo Sólido + audio_pergunta + audio_cta
      Ato 2: Fundo Sólido + Countdown 10s
      Ato 3: VídeosResposta + audio_resposta
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path   = os.path.join(output_dir, "video_final.mp4")
    audio_final   = os.path.join(output_dir, "audio_final.mp3")
    musica_path   = os.path.join("data", "quiz_music.mp3")

    dur_pergunta = _duracao_audio(audio_pergunta)
    dur_cta      = _duracao_audio(audio_cta)
    dur_resposta = _duracao_audio(audio_resposta)
    
    dur_ato1     = dur_pergunta + dur_cta
    dur_total    = dur_ato1 + countdown_s + dur_resposta

    print(f"⏱️  Duração: Pergunta+CTA={dur_ato1:.1f}s | Countdown={countdown_s:.0f}s | Resposta={dur_resposta:.1f}s | Total={dur_total:.1f}s")

    print("🔊 Concatenando áudios (pergunta + cta + silêncio + resposta)...")
    _concatenar_audios(audio_pergunta, audio_cta, countdown_s, audio_resposta, audio_final)

    if not os.path.exists(musica_path):
        os.makedirs("data", exist_ok=True)
        _baixar_musica_quiz(musica_path)

    srt_escaped = _escape_srt_path(legendas_srt)
    # Legenda amarela, SEM CAIXA, com sombra preta
    subtitle_style = ",".join([
        "Fontname=Arial",
        "FontSize=22",
        "Bold=1",
        "PrimaryColour=&H0000FFFF",   # Amarelo (BBGGRR)
        "OutlineColour=&H00000000",   # Borda Preta
        "BackColour=&H00000000",      # Sombra Preta
        "BorderStyle=1",              # 1=Outline+Shadow (Sem caixa cinza)
        "Outline=3",                  # Borda grossa
        "Shadow=3",                   # Sombra forte
        "Alignment=10",               # Inferior centro (para portrait)
        "MarginV=120",
    ])

    # ── Tempos do Ato 1 e Ato 2 ─────────────────────────────────────────────
    t_start_countdown = dur_ato1
    t_end_countdown   = dur_ato1 + countdown_s

    # ── Criar vídeo visual (Ato 1 e Ato 3) ───────────────────────────────────
    print("🎨 Gerando fundo de cor sólida para a pergunta e countdown...")
    bg_color_vid = os.path.join(output_dir, "bg_color.mp4")
    # Cor base: #1b263b
    cmd_color = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=#1b263b:s=1080x1920:d={dur_ato1 + countdown_s}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        bg_color_vid,
    ]
    subprocess.run(cmd_color, capture_output=True, check=True)

    print("🎬 Cortando o vídeo concatenado da resposta para caber exatamente no Ato 3...")
    video_resp_loop = os.path.join(output_dir, "vid_r_loop.mp4")
    cmd_resp_loop = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", video_resposta,
        "-t", str(dur_resposta),
        "-vf", "fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        video_resp_loop,
    ]
    subprocess.run(cmd_resp_loop, capture_output=True, check=True)

    print("✂️  Concatenando partes visuais...")
    lista_video = os.path.join(output_dir, "video_concat.txt")
    with open(lista_video, "w") as f:
        f.write(f"file '{os.path.abspath(bg_color_vid).replace(chr(92), '/')}'\n")
        f.write(f"file '{os.path.abspath(video_resp_loop).replace(chr(92), '/')}'\n")

    video_raw = os.path.join(output_dir, "video_raw.mp4")
    cmd_concat_video = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", lista_video,
        "-c", "copy",
        video_raw,
    ]
    subprocess.run(cmd_concat_video, capture_output=True, check=True)

    # ── Filtros Drawtext ─────────────────────────────────────────────────────
    filtros_drawtext = [
        # TOPO - Ato 1 e Countdown: Label "❓ DESAFIO RÁPIDO"
        (
            "drawtext=fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ":text='DESAFIO RAPIDO'"
            ":fontsize=50:fontcolor=white:bordercolor=black:borderw=3"
            ":x=(W-text_w)/2:y=80"
            f":enable='lt(t,{t_end_countdown:.2f})'"
        ),
        # Overlay escuro no Countdown
        (
            "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.5:t=fill"
            f":enable='between(t,{t_start_countdown:.2f},{t_end_countdown:.2f})'"
        ),
        # Texto "Voce sabe?" acima do número
        (
            "drawtext=fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ":text='Voce sabe a resposta?'"
            ":fontsize=42:fontcolor=yellow:bordercolor=black:borderw=3"
            ":x=(W-text_w)/2:y=200"
            f":enable='between(t,{t_start_countdown:.2f},{t_end_countdown:.2f})'"
        ),
        # TOPO - Ato 3: Label "RESPOSTA"
        (
            "drawtext=fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ":text='RESPOSTA'"
            ":fontsize=50:fontcolor=black:bordercolor=white:borderw=2"
            ":box=1:boxcolor=green@0.9:boxborderw=15"
            ":x=(W-text_w)/2:y=80"
            f":enable='gte(t,{t_end_countdown:.2f})'"
        )
    ]

    # Adicionar números dinamicamente (10 até 1)
    # Ex: Para contador de 10s
    cores = ["red", "orange", "yellow", "green", "cyan", "blue", "magenta", "red", "orange", "yellow"]
    for i in range(int(countdown_s)):
        numero = int(countdown_s) - i
        inicio = t_start_countdown + i
        fim    = inicio + 1.0
        cor_borda = cores[i % len(cores)]
        filtro_num = (
            "drawtext=fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            f":text='{numero}'"
            f":fontsize=280:fontcolor=white:bordercolor={cor_borda}:borderw=8"
            ":x=(W-text_w)/2:y=(H-text_h)/2"
            f":enable='between(t,{inicio:.2f},{fim:.2f})'"
        )
        filtros_drawtext.append(filtro_num)

    # Adiciona legendas SRT por último no filter
    filtros_str = ",".join(filtros_drawtext)
    filtros_str += f",subtitles='{srt_escaped}':force_style='{subtitle_style}'"

    # Volume do BG Music: baixo na pergunta (0.1), alto no countdown (0.5), baixo na resposta (0.1)
    # Aumenta durante o countdown para criar impacto.
    volume_expr = f"if(between(t,{t_start_countdown:.2f},{t_end_countdown:.2f}),0.5,0.1)"

    cmd_final = [
        "ffmpeg", "-y",
        "-i", video_raw,
        "-i", audio_final,
        "-stream_loop", "-1", "-i", musica_path,
        "-t", str(dur_total),
        "-filter_complex", (
            f"[0:v]{filtros_str}[v];"
            f"[2:a]volume='{volume_expr}':eval=frame[bg];"
            "[1:a]volume=1.0[voice];"
            "[voice][bg]amix=inputs=2:duration=first:dropout_transition=2[a]"
        ),
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-map_metadata", "-1",
        output_path,
    ]

    print("🎬 Montando vídeo final com FFmpeg...")
    resultado = subprocess.run(cmd_final, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"FFmpeg falhou na montagem final:\n{resultado.stderr[-1200:]}")

    # Limpar temporários
    for tmp in [bg_color_vid, video_resp_loop, video_raw, lista_video, audio_final]:
        if os.path.exists(tmp):
            os.remove(tmp)

    tamanho_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"✅ Short Quiz pronto: {output_path}  ({tamanho_mb:.1f} MB, {dur_total:.1f}s)")
    return output_path
