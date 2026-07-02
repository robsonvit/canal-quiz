"""
montar_video.py
───────────────
Monta o Short final 1080×1920 (9:16) para o YouTube no formato Quiz:

  ATO 1 — PERGUNTA (~5-8s)
    • Fundo de cor sólida dinâmica (sem imagem)
    • Áudio TTS da pergunta
    • Legendas na tela (amarelo neon, parte inferior)
    • Overlay "❓ DESAFIO RÁPIDO" no topo

  ATO 2 — COUNTDOWN (3s)
    • Fundo sólido continua, com overlay escurecido
    • Números 3 → 2 → 1 centralizados, animados
    • Texto "Você sabe a resposta?" acima do número
    • Música de suspense (volume alto)

  ATO 3 — RESPOSTA (~8-12s)
    • Vídeo vertical relacionado à resposta (do Pexels) em loop
    • Áudio TTS da resposta + curiosidade
    • Legendas na tela
    • Overlay "✅ RESPOSTA:" no topo com a resposta curta em caixa colorida
    • Música volta ao volume suave

Tudo montado via FFmpeg com filter_complex avançado.
"""

import os
import json
import subprocess
import re


# ─────────────────────────────────────────────────────────────────────────────
# Utilitários
# ─────────────────────────────────────────────────────────────────────────────
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
    """Escapa texto para uso seguro no drawtext do FFmpeg."""
    return (texto
            .replace("\\", "\\\\")
            .replace("'",  "\\'")
            .replace(":",  "\\:")
            .replace("%",  "\\%")
            .replace("[",  "\\[")
            .replace("]",  "\\]"))


def _concatenar_audios(audio1: str, audio2: str, silencio_s: float, output: str):
    """
    Concatena audio1 + silêncio de `silencio_s` segundos + audio2
    produzindo um único MP3 para o vídeo final.
    """
    silencio_path = output.replace(".mp3", "_silencio.mp3")

    # Gerar silêncio via FFmpeg
    cmd_silencio = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(silencio_s),
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        silencio_path,
    ]
    subprocess.run(cmd_silencio, capture_output=True, check=True)

    # Criar lista de concatenação
    lista_path = output.replace(".mp3", "_concat.txt")
    with open(lista_path, "w") as f:
        for p in [audio1, silencio_path, audio2]:
            f.write(f"file '{os.path.abspath(p).replace(chr(92), '/')}'\n")

    # Concatenar
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", lista_path,
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        output,
    ]
    subprocess.run(cmd_concat, capture_output=True, check=True)

    # Limpar temporários
    for f in [silencio_path, lista_path]:
        if os.path.exists(f):
            os.remove(f)


def _baixar_musica_fallback(dest: str):
    """Baixa música de fundo se não existir."""
    import requests
    urls = [
        "https://archive.org/download/ClassicalMusicPlaylist/Pachelbel_Canon_in_D.mp3",
        "https://archive.org/download/BaptistMusic/How%20Beautiful%20-%20piano%20instrumental%20cover%20with%20lyrics.mp3",
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    for url in urls:
        try:
            r = requests.get(url, headers=headers, stream=True, timeout=45)
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"🎵 Música baixada: {dest}")
            return
        except Exception as e:
            print(f"⚠️ Falha ao baixar música: {e}")
    raise RuntimeError("Não foi possível baixar música de fundo.")


# ─────────────────────────────────────────────────────────────────────────────
# Montagem principal
# ─────────────────────────────────────────────────────────────────────────────
def montar_video(
    video_resposta: str,
    audio_pergunta: str,
    audio_resposta: str,
    legendas_srt: str,
    output_dir: str = "output",
    resposta_curta: str = "",
    countdown_s: float = 3.0,
) -> str:
    """
    Monta o Short de Quiz com 3 atos:
      Ato 1: Fundo de cor sólida + áudio pergunta
      Ato 2: Fundo de cor sólida + Countdown 3s
      Ato 3: Vídeo resposta + áudio resposta

    Retorna o caminho do vídeo final.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path   = os.path.join(output_dir, "video_final.mp4")
    audio_final   = os.path.join(output_dir, "audio_final.mp3")
    musica_path   = os.path.join("data", "bg_music.mp3")

    # ── Duração dos atos ──────────────────────────────────────────────────────
    dur_pergunta = _duracao_audio(audio_pergunta)
    dur_resposta = _duracao_audio(audio_resposta)
    dur_total    = dur_pergunta + countdown_s + dur_resposta
    dur_ato1     = dur_pergunta + countdown_s

    print(f"⏱️  Duração: pergunta={dur_pergunta:.1f}s | countdown={countdown_s:.0f}s | resposta={dur_resposta:.1f}s | total={dur_total:.1f}s")

    # ── Concatenar áudios ─────────────────────────────────────────────────────
    print("🔊 Concatenando áudios (pergunta + silêncio + resposta)...")
    _concatenar_audios(audio_pergunta, audio_resposta, countdown_s, audio_final)

    # ── Baixar música de fundo se necessário ──────────────────────────────────
    if not os.path.exists(musica_path):
        os.makedirs("data", exist_ok=True)
        print("🎵 Baixando música de fundo...")
        _baixar_musica_fallback(musica_path)

    # ── Configuração de legendas ──────────────────────────────────────────────
    srt_escaped = _escape_srt_path(legendas_srt)
    subtitle_style = ",".join([
        "Fontname=Arial",
        "FontSize=20",
        "Bold=1",
        "PrimaryColour=&H00FFFF00",   # Amarelo neon
        "OutlineColour=&H00000000",
        "BackColour=&H80000000",
        "BorderStyle=4",              # Caixa com fundo
        "Outline=2",
        "Shadow=2",
        "Alignment=10",               # Inferior centro (para portrait)
        "MarginV=120",
    ])

    # ── Texto do countdown (3 → 2 → 1) ───────────────────────────────────────
    t0  = dur_pergunta           # Início do countdown
    t1  = dur_pergunta + 1.0     # Muda para 2
    t2  = dur_pergunta + 2.0     # Muda para 1
    t3  = dur_pergunta + 3.0     # Fim do countdown

    resposta_esc = _escape_drawtext(resposta_curta[:50] if resposta_curta else "")

    # ── Criar vídeo visual (concatenando Ato 1 e Ato 3) ──────────────────────
    print("🎨 Gerando fundo de cor sólida para a pergunta...")
    bg_color_vid = os.path.join(output_dir, "bg_color.mp4")
    # Gerar cor #1b263b (Dark Blue)
    cmd_color = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=#1b263b:s=1080x1920:d={dur_ato1}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        bg_color_vid,
    ]
    subprocess.run(cmd_color, capture_output=True, check=True)

    print("🎬 Processando e cortando o vídeo da resposta...")
    video_resp_loop = os.path.join(output_dir, "vid_r_loop.mp4")
    # Usa stream_loop no vídeo da resposta e garante a duração exata do Ato 3
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

    # ── Ato 2: Overlay do countdown + overlays de texto ──────────────────────
    filtros_drawtext = [
        # TOPO - Ato 1: Label "❓ DESAFIO RÁPIDO"
        (
            "drawtext=fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ":text='DESAFIO RAPIDO'"
            ":fontsize=50:fontcolor=white:bordercolor=black:borderw=3"
            ":x=(W-text_w)/2:y=80"
            f":enable='lt(t,{t0:.2f})'"
        ),
        # Overlay escuro no Ato 2 (countdown)
        (
            "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.5:t=fill"
            f":enable='between(t,{t0:.2f},{t3:.2f})'"
        ),
        # Número 3
        (
            "drawtext=fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ":text='3'"
            ":fontsize=280:fontcolor=white:bordercolor=red:borderw=8"
            ":x=(W-text_w)/2:y=(H-text_h)/2"
            f":enable='between(t,{t0:.2f},{t1:.2f})'"
        ),
        # Número 2
        (
            "drawtext=fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ":text='2'"
            ":fontsize=280:fontcolor=white:bordercolor=orange:borderw=8"
            ":x=(W-text_w)/2:y=(H-text_h)/2"
            f":enable='between(t,{t1:.2f},{t2:.2f})'"
        ),
        # Número 1
        (
            "drawtext=fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ":text='1'"
            ":fontsize=280:fontcolor=white:bordercolor=green:borderw=8"
            ":x=(W-text_w)/2:y=(H-text_h)/2"
            f":enable='between(t,{t2:.2f},{t3:.2f})'"
        ),
        # Texto "Voce sabe?" acima do número
        (
            "drawtext=fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ":text='Voce sabe a resposta?'"
            ":fontsize=42:fontcolor=yellow:bordercolor=black:borderw=3"
            ":x=(W-text_w)/2:y=200"
            f":enable='between(t,{t0:.2f},{t3:.2f})'"
        ),
        # TOPO - Ato 3: Label "RESPOSTA"
        (
            "drawtext=fontfile=/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ":text='RESPOSTA'"
            ":fontsize=50:fontcolor=black:bordercolor=white:borderw=2"
            ":box=1:boxcolor=green@0.9:boxborderw=15"
            ":x=(W-text_w)/2:y=80"
            f":enable='gte(t,{t3:.2f})'"
        ),
    ]

    # Adiciona legendas SRT por último no filter
    filtros_str = ",".join(filtros_drawtext)
    filtros_str += f",subtitles='{srt_escaped}':force_style='{subtitle_style}'"

    cmd_final = [
        "ffmpeg", "-y",
        "-i", video_raw,
        "-i", audio_final,
        "-stream_loop", "-1", "-i", musica_path,
        "-t", str(dur_total),
        "-filter_complex", (
            f"[0:v]{filtros_str}[v];"
            "[1:a]volume=1.0[voice];"
            "[2:a]volume=0.12[bg];"
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
