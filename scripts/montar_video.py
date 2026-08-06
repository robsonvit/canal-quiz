"""
montar_video.py
───────────────
Monta o Short final 1080×1920 (9:16) para o YouTube no formato Quiz:

  ATO 1 — GANCHO CHAMATIVO (~5-8s)
    • Fundo de cor sólida dinâmica
    • Efeito sonoro de impacto no início (sfx_gancho.mp3)
    • Áudio TTS da pergunta
    • Legendas na tela (amarelo puro com borda preta)
    • Overlay "❓ DESAFIO RÁPIDO" no topo

  ATO 2 — COUNTDOWN (3s)
    • Fundo sólido continua, com overlay escurecido
    • Números 3 → 1 centralizados, animados
    • Texto "Você sabe a resposta?" acima do número
    • Música de QUIZ (volume alto)
    • Efeito sonoro de reveal (sfx_resposta.mp3) no fim do countdown

  ATO 3 — RESPOSTA (~8-12s)
    • Vídeo vertical relacionado à resposta (múltiplos vídeos do Pexels)
    • Áudio TTS da resposta + curiosidade
    • Legendas na tela
    • Overlay "✅ RESPOSTA:" no topo com a resposta curta em caixa colorida
    • Música volta ao volume suave

  ATO 4 — CTA DE INSCRIÇÃO (~4-6s)
    • Continua o vídeo do Pexels
    • Áudio TTS do CTA (apelo aleatório: superstição / história / promessa)
    • Legendas na tela
    • Overlay "🔔 SEGUE O CANAL!" no topo
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


def _concatenar_audios(
    audio_p: str,
    audio_r: str,
    audio_cta: str,
    silencio_s: float,
    output: str,
):
    """
    Concatena: Pergunta (gancho) + Silêncio countdown + Resposta + CTA
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

    cmd_concat = [
        "ffmpeg", "-y",
        "-i", audio_p,
        "-i", silencio_path,
        "-i", audio_r,
        "-i", audio_cta,
        "-filter_complex", "[0:a][1:a][2:a][3:a]concat=n=4:v=0:a=1[aout]",
        "-map", "[aout]",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        output,
    ]
    subprocess.run(cmd_concat, capture_output=True, check=True)

    if os.path.exists(silencio_path):
        os.remove(silencio_path)


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
        print("🎵 Gerando áudio de silêncio como fallback...")
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "60", "-c:a", "libmp3lame", dest]
        subprocess.run(cmd, capture_output=True)


def _baixar_sfx(dest: str, tipo: str):
    """
    Baixa efeitos sonoros gratuitos (domínio público) para o gancho e a revelação.
    tipo: 'gancho' ou 'resposta'
    """
    import requests

    # URLs de efeitos sonoros de domínio público (freesound via URLs diretas)
    urls = {
        "gancho": [
            # Woosh/swoosh dramático para o início do gancho
            "https://freesound.org/data/previews/320/320655_5260872-lq.mp3",
            "https://www.soundjay.com/misc/sounds/fail-buzzer-01.mp3",
        ],
        "resposta": [
            # Ding / reveal para a entrada da resposta
            "https://freesound.org/data/previews/411/411089_5121236-lq.mp3",
            "https://www.soundjay.com/misc/sounds/bell-ringing-05.mp3",
        ],
    }

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for url in urls.get(tipo, []):
        try:
            print(f"🔊 Baixando SFX ({tipo}): {url}")
            r = requests.get(url, headers=headers, timeout=10, stream=True)
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            # Verificar se o arquivo tem tamanho mínimo (evita HTML de erro)
            if os.path.getsize(dest) > 5000:
                print(f"✅ SFX ({tipo}) baixado: {dest}")
                return
            else:
                print(f"⚠️ Arquivo muito pequeno, tentando próxima URL...")
                os.remove(dest)
        except Exception as e:
            print(f"⚠️ Falha ao baixar SFX ({tipo}) de {url}: {e}")

    # Fallback: gera um beep curto via FFmpeg
    print(f"🔊 Gerando beep de fallback para SFX ({tipo})...")
    duracao = "0.3" if tipo == "gancho" else "0.5"
    freq    = "800"  if tipo == "gancho" else "1200"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency={freq}:duration={duracao}",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        dest,
    ]
    subprocess.run(cmd, capture_output=True)
    print(f"✅ Beep de fallback gerado: {dest}")


def _mixar_sfx_com_voz(voz_path: str, sfx_path: str, output_path: str, sfx_volume: float = 0.6):
    """
    Mixa o efeito sonoro com a narração da voz.
    O SFX toca no início, a voz aparece junto mas domina.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", voz_path,
        "-i", sfx_path,
        "-filter_complex",
        (
            f"[1:a]volume={sfx_volume}[sfx];"
            "[0:a][sfx]amix=inputs=2:duration=first:dropout_transition=1[aout]"
        ),
        "-map", "[aout]",
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        output_path,
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        print(f"⚠️ Falha ao mixar SFX: {resultado.stderr[-400:]}")
        # Fallback: usa a voz sem SFX
        import shutil
        shutil.copy2(voz_path, output_path)


def montar_video(
    video_resposta: str,
    audio_pergunta: str,
    audio_cta: str,
    audio_resposta: str,
    legendas_srt: str,
    output_dir: str = "output",
    resposta_curta: str = "",
    countdown_s: float = 3.0,
) -> str:
    """
    Monta o Short de Quiz com 4 atos:
      Ato 1: Fundo Sólido + gancho (pergunta com SFX de impacto)
      Ato 2: Fundo Sólido + Countdown 3s (com música alta)
      Ato 3: Vídeo Resposta + áudio da resposta
      Ato 4: Vídeo Resposta + CTA de inscrição (apelo aleatório)
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path   = os.path.join(output_dir, "video_final.mp4")
    audio_final   = os.path.join(output_dir, "audio_final.mp3")
    musica_path   = os.path.join("data", "quiz_music.mp3")
    sfx_gancho    = os.path.join("data", "sfx_gancho.mp3")
    sfx_resposta  = os.path.join("data", "sfx_resposta.mp3")
    audio_gancho_sfx = os.path.join(output_dir, "audio_gancho_sfx.mp3")

    # ── Baixar assets se necessários ─────────────────────────────────────────
    if not os.path.exists(musica_path):
        os.makedirs("data", exist_ok=True)
        _baixar_musica_quiz(musica_path)

    if not os.path.exists(sfx_gancho):
        os.makedirs("data", exist_ok=True)
        _baixar_sfx(sfx_gancho, "gancho")

    if not os.path.exists(sfx_resposta):
        os.makedirs("data", exist_ok=True)
        _baixar_sfx(sfx_resposta, "resposta")

    # ── Mixar efeito sonoro com o gancho (pergunta) ───────────────────────────
    print("🔊 Mixando efeito sonoro de impacto com o áudio do gancho...")
    _mixar_sfx_com_voz(audio_pergunta, sfx_gancho, audio_gancho_sfx, sfx_volume=0.5)

    # ── Calcular durações ─────────────────────────────────────────────────────
    dur_pergunta = _duracao_audio(audio_gancho_sfx)
    dur_resposta = _duracao_audio(audio_resposta)
    dur_cta      = _duracao_audio(audio_cta)

    dur_ato1     = dur_pergunta
    dur_ato3_4   = dur_resposta + dur_cta
    dur_total    = dur_ato1 + countdown_s + dur_ato3_4

    print(f"⏱️  Gancho={dur_pergunta:.1f}s | Countdown={countdown_s:.0f}s | Resposta={dur_resposta:.1f}s | CTA={dur_cta:.1f}s | Total={dur_total:.1f}s")

    # ── Concatenar áudios: gancho + silêncio countdown + resposta + CTA ───────
    print("🔊 Concatenando áudios (gancho + silêncio + resposta + CTA)...")
    _concatenar_audios(audio_gancho_sfx, audio_resposta, audio_cta, countdown_s, audio_final)

    import shutil
    import uuid
    import tempfile

    # Criar arquivo temporário de forma segura (funciona no Windows e Linux)
    temp_srt = os.path.join(tempfile.gettempdir(), f"legendas_{uuid.uuid4().hex}.srt")
    shutil.copy2(legendas_srt, temp_srt)

    # Escapar caminho absoluto para FFmpeg no Windows
    srt_escaped = temp_srt.replace('\\', '/').replace(':', '\\\\:')

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

    # ── Tempos dos atos ──────────────────────────────────────────────────────
    t_start_countdown = dur_ato1
    t_end_countdown   = dur_ato1 + countdown_s
    t_start_cta       = t_end_countdown + dur_resposta
    t_end_video       = dur_total

    # ── Criar vídeo de fundo sólido para gancho + countdown ──────────────────
    print("🎨 Gerando fundo de cor sólida para o gancho e countdown...")
    bg_color_vid = os.path.join(output_dir, "bg_color.mp4")
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

    # ── Criar vídeo da resposta (loop) para Ato 3 + Ato 4 (resposta + CTA) ───
    print("🎬 Cortando vídeo da resposta para o Ato 3+4...")
    video_resp_loop = os.path.join(output_dir, "vid_r_loop.mp4")
    cmd_resp_loop = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", video_resposta,
        "-t", str(dur_ato3_4),
        "-vf", "fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        video_resp_loop,
    ]
    subprocess.run(cmd_resp_loop, capture_output=True, check=True)

    # ── Concatenar partes visuais ─────────────────────────────────────────────
    print("✂️  Concatenando partes visuais (fundo sólido + vídeo)...")
    lista_video = os.path.join(output_dir, "video_concat.txt")
    with open(lista_video, "w", encoding="utf-8") as f:
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

    # Fonte baseada no SO
    if os.name == "nt":
        font_path = "C\\\\:/Windows/Fonts/arialbd.ttf"
    else:
        font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

    # ── Filtros Drawtext ──────────────────────────────────────────────────────
    filtros_drawtext = [
        # TOPO - Ato 1 (gancho) e Countdown: "DESAFIO RAPIDO"
        (
            f"drawtext=fontfile='{font_path}'"
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
        # "Voce sabe a resposta?" acima do número no countdown
        (
            f"drawtext=fontfile='{font_path}'"
            ":text='Voce sabe a resposta?'"
            ":fontsize=42:fontcolor=yellow:bordercolor=black:borderw=3"
            ":x=(W-text_w)/2:y=200"
            f":enable='between(t,{t_start_countdown:.2f},{t_end_countdown:.2f})'"
        ),
        # TOPO - Ato 3 (resposta): "RESPOSTA"
        (
            f"drawtext=fontfile='{font_path}'"
            ":text='RESPOSTA'"
            ":fontsize=50:fontcolor=black:bordercolor=white:borderw=2"
            ":box=1:boxcolor=green@0.9:boxborderw=15"
            ":x=(W-text_w)/2:y=80"
            f":enable='between(t,{t_end_countdown:.2f},{t_start_cta:.2f})'"
        ),
        # TOPO - Ato 4 (CTA de inscrição): "SEGUE O CANAL!"
        (
            f"drawtext=fontfile='{font_path}'"
            ":text='SEGUE O CANAL!'"
            ":fontsize=50:fontcolor=black:bordercolor=white:borderw=2"
            ":box=1:boxcolor=red@0.9:boxborderw=15"
            ":x=(W-text_w)/2:y=80"
            f":enable='gte(t,{t_start_cta:.2f})'"
        ),
    ]

    # Adicionar números do countdown dinamicamente (3 → 1)
    cores_countdown = ["red", "orange", "yellow"]
    for i in range(int(countdown_s)):
        numero    = int(countdown_s) - i
        inicio    = t_start_countdown + i
        fim       = inicio + 1.0
        cor_borda = cores_countdown[i % len(cores_countdown)]
        filtro_num = (
            f"drawtext=fontfile='{font_path}'"
            f":text='{numero}'"
            f":fontsize=280:fontcolor=white:bordercolor={cor_borda}:borderw=8"
            ":x=(W-text_w)/2:y=(H-text_h)/2"
            f":enable='between(t,{inicio:.2f},{fim:.2f})'"
        )
        filtros_drawtext.append(filtro_num)

    # Adiciona legendas SRT por último no filter
    filtros_str = ",".join(filtros_drawtext)
    filtros_str += f",subtitles='{srt_escaped}':force_style='{subtitle_style}'"

    # Volume da música BG: baixo no gancho (0.08), alto no countdown (0.5), suave na resposta/CTA (0.08)
    volume_expr = f"if(between(t,{t_start_countdown:.2f},{t_end_countdown:.2f}),0.5,0.08)"

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
    for tmp in [bg_color_vid, video_resp_loop, video_raw, lista_video, audio_final, audio_gancho_sfx, temp_srt]:
        if os.path.exists(tmp):
            os.remove(tmp)

    tamanho_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"✅ Short Quiz pronto: {output_path}  ({tamanho_mb:.1f} MB, {dur_total:.1f}s)")
    return output_path
