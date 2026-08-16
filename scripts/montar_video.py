"""
montar_video.py
───────────────
Monta o Short final 1080×1920 (9:16) para o YouTube no formato Quiz:
Estilo "Show do Milhão"
"""

import os
import json
import subprocess
import re
import shutil
import uuid
import tempfile

def _duracao_audio(audio_path: str) -> float:
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", audio_path]
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

def _concatenar_audios(
    audio_p: str,
    audio_r: str,
    audio_cta: str,
    silencio_s: float,
    output: str,
):
    silencio_path = output.replace(".mp3", "_silencio.mp3")
    cmd_silencio = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(silencio_s), "-c:a", "libmp3lame", "-b:a", "128k", silencio_path
    ]
    subprocess.run(cmd_silencio, capture_output=True, check=True)

    cmd_concat = [
        "ffmpeg", "-y", "-i", audio_p, "-i", silencio_path, "-i", audio_r, "-i", audio_cta,
        "-filter_complex", "[0:a][1:a][2:a][3:a]concat=n=4:v=0:a=1[aout]",
        "-map", "[aout]", "-c:a", "libmp3lame", "-b:a", "128k", output
    ]
    subprocess.run(cmd_concat, capture_output=True, check=True)

    if os.path.exists(silencio_path):
        os.remove(silencio_path)

def _baixar_musica_quiz(dest: str):
    import requests
    # Música de suspense mais típica de quiz show
    url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"
    try:
        r = requests.get(url, stream=True, timeout=15)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "60", "-c:a", "libmp3lame", dest]
        subprocess.run(cmd, capture_output=True)

def _baixar_sfx(dest: str, tipo: str):
    import requests
    urls = {
        "gancho": ["https://freesound.org/data/previews/320/320655_5260872-lq.mp3"],
        "resposta": ["https://freesound.org/data/previews/411/411089_5121236-lq.mp3"],
    }
    for url in urls.get(tipo, []):
        try:
            r = requests.get(url, timeout=10, stream=True)
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            if os.path.getsize(dest) > 5000: return
            else: os.remove(dest)
        except Exception: pass

    duracao = "0.3" if tipo == "gancho" else "0.5"
    freq    = "800"  if tipo == "gancho" else "1200"
    cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duracao}", "-c:a", "libmp3lame", "-b:a", "128k", dest]
    subprocess.run(cmd, capture_output=True)

def _mixar_sfx_com_voz(voz_path: str, sfx_path: str, output_path: str, sfx_volume: float = 0.6):
    cmd = [
        "ffmpeg", "-y", "-i", voz_path, "-i", sfx_path,
        "-filter_complex", f"[1:a]volume={sfx_volume}[sfx];[0:a][sfx]amix=inputs=2:duration=first:dropout_transition=1[aout]",
        "-map", "[aout]", "-c:a", "libmp3lame", "-b:a", "128k", output_path
    ]
    if subprocess.run(cmd, capture_output=True).returncode != 0:
        shutil.copy2(voz_path, output_path)

def montar_video(
    audios: dict,
    video_pexels: str,
    output_dir: str = "output",
    countdown_s: float = 5.0,
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    output_path   = os.path.join(output_dir, "video_final.mp4")
    audio_final   = os.path.join(output_dir, "audio_final.mp3")
    musica_path   = os.path.join("data", "quiz_music.mp3")

    if not os.path.exists(musica_path): _baixar_musica_quiz(musica_path)

    # 1. Generate Images
    subprocess.run(["python", "scripts/gerar_imagens.py"], check=True)

    # 2. Extract paths and durations
    ag = audios["audio_gancho"]
    ap = audios["audio_pergunta"]
    aopts = audios["audio_opts"]
    at = audios["audio_tempo"]
    arc = audios["audio_rev_curta"]
    ae = audios["audio_explicacao"]
    acta = audios["audio_cta"]

    # SFX paths
    sfx_noti = os.path.join("data", "sfx_notificacao.mp3")
    sfx_money = os.path.join("ADUIOS", "som dinheiro 2.mp3")
    sfx_opt = os.path.join("data", "sfx_opcao.mp3")
    sfx_correct = os.path.join("data", "sfx_resposta.mp3") # using the existing sfx_resposta for correct

    dg = _duracao_audio(ag)
    dp = _duracao_audio(ap)
    dopts = audios["dur_opts"]
    dt = _duracao_audio(at)
    drc = _duracao_audio(arc)
    de = _duracao_audio(ae)
    dcta = _duracao_audio(acta)

    d_noti = _duracao_audio(sfx_noti)
    d_money = _duracao_audio(sfx_money)
    d_sfx_opt = _duracao_audio(sfx_opt)

    dur_revelacao_pexels = de + dcta

    # 3. Create Audio Track
    silence_path = os.path.join(output_dir, "silence.mp3")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", str(countdown_s), "-c:a", "libmp3lame", silence_path], capture_output=True, check=True)
    
    # concatena: noti, gancho, pergunta, (opt sfx + optX)*4, tempo, silence(5s), rev_curta, explicacao, cta
    inputs_audio = [sfx_noti, ag, ap]
    for ao in aopts:
        inputs_audio.extend([sfx_opt, ao])
    inputs_audio.extend([at, silence_path, arc, ae, acta])
    
    cmd_audio = ["ffmpeg", "-y"]
    for ia in inputs_audio:
        cmd_audio.extend(["-i", ia])
    cmd_audio.extend([
        "-filter_complex", f"{''.join(f'[{i}:a]' for i in range(len(inputs_audio)))}concat=n={len(inputs_audio)}:v=0:a=1[aout]",
        "-map", "[aout]", "-c:a", "libmp3lame", "-b:a", "128k", audio_final
    ])
    subprocess.run(cmd_audio, capture_output=True, check=True)

    # 4. Create Video Track
    # Sequence: 
    # fundo (d_noti + dg), pergunta (dp), opt1 (d_sfx_opt+dopts[0]), opt2 (d_sfx_opt+dopts[1]), opt3 (d_sfx_opt+dopts[2]), normal (d_sfx_opt+dopts[3] + dt + countdown_s), revelacao (drc)
    d_fundo_frame = d_noti + dg
    d_normal = d_sfx_opt + dopts[3] + dt + countdown_s
    d_rev_frame = drc

    # Generate Pexels loop
    video_resp_loop = os.path.join(output_dir, "vid_r_loop.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", video_pexels, "-t", str(dur_revelacao_pexels),
        "-vf", "fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p", video_resp_loop
    ], capture_output=True, check=True)

    # Concat images
    seq = [
        (os.path.join(output_dir, "frame_fundo.png"), d_fundo_frame),
        (os.path.join(output_dir, "frame_pergunta.png"), dp),
        (os.path.join(output_dir, "frame_opt1.png"), d_sfx_opt + dopts[0]),
        (os.path.join(output_dir, "frame_opt2.png"), d_sfx_opt + dopts[1]),
        (os.path.join(output_dir, "frame_opt3.png"), d_sfx_opt + dopts[2]),
        (os.path.join(output_dir, "frame_normal.png"), d_normal),
        (os.path.join(output_dir, "frame_revelacao.png"), d_rev_frame)
    ]
    
    cmd_video = ["ffmpeg", "-y"]
    for img, d in seq:
        cmd_video.extend(["-loop", "1", "-t", str(d), "-i", img])
    
    cmd_video.extend(["-i", video_resp_loop]) # 8th input
    
    n_inputs = len(seq) + 1
    cmd_video.extend([
        "-filter_complex", f"{''.join(f'[{i}:v]' for i in range(n_inputs))}concat=n={n_inputs}:v=1:a=0[v]",
        "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", 
        os.path.join(output_dir, "video_raw.mp4")
    ])
    subprocess.run(cmd_video, capture_output=True, check=True)
    video_raw = os.path.join(output_dir, "video_raw.mp4")

    # 5. Final Assembly (Countdown + Subtitles + Music)
    legendas_srt = audios["legendas_srt"]
    temp_srt = os.path.join(tempfile.gettempdir(), f"legendas_{uuid.uuid4().hex}.srt")
    shutil.copy2(legendas_srt, temp_srt)
    srt_escaped = temp_srt.replace("\\", "/").replace(":", "\\:")

    legendas_gancho_srt = audios["legendas_gancho_srt"]
    temp_gancho_srt = os.path.join(tempfile.gettempdir(), f"legendas_gancho_{uuid.uuid4().hex}.srt")
    shutil.copy2(legendas_gancho_srt, temp_gancho_srt)
    srt_gancho_escaped = temp_gancho_srt.replace("\\", "/").replace(":", "\\:")

    subtitle_style = ",".join([
        "Fontname=Arial", "FontSize=24", "Bold=1", "PrimaryColour=&H0000FFFF",
        "OutlineColour=&H00000000", "BackColour=&H00000000", "BorderStyle=1",
        "Outline=4", "Shadow=4", "Alignment=2", "MarginV=40",
    ])

    subtitle_style_centro = ",".join([
        "Fontname=Arial", "FontSize=28", "Bold=1", "PrimaryColour=&H0000FFFF",
        "OutlineColour=&H00000000", "BackColour=&H00000000", "BorderStyle=1",
        "Outline=4", "Shadow=4", "Alignment=10", "MarginV=0",
    ])

    font_path = "C\\:/Windows/Fonts/arialbd.ttf" if os.name == "nt" else "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    filtros_drawtext = []
    
    t_start_countdown = d_fundo_frame + dp + (d_sfx_opt * 4) + sum(dopts) + dt
    t_end_countdown = t_start_countdown + countdown_s
    cores_countdown = ["red", "yellow", "white"]
    
    for i in range(int(countdown_s)):
        numero = int(countdown_s) - i
        inicio = t_start_countdown + i
        fim = inicio + 1.0
        cor_borda = cores_countdown[i % len(cores_countdown)]
        filtros_drawtext.append(
            f"drawtext=fontfile='{font_path}':text='{numero}':fontsize=300:fontcolor=white:bordercolor={cor_borda}:borderw=10"
            f":x=(W-text_w)/2:y=(H-text_h)/2:enable='between(t,{inicio:.2f},{fim:.2f})'"
        )

    filtros_str = ",".join(filtros_drawtext) + f",subtitles='{srt_escaped}':force_style='{subtitle_style}',subtitles='{srt_gancho_escaped}':force_style='{subtitle_style_centro}'"
    volume_expr = f"if(between(t,{t_start_countdown:.2f},{t_end_countdown:.2f}),0.5,0.08)"

    t_end_gancho = d_noti + dg
    
    cmd_final = [
        "ffmpeg", "-y", "-i", video_raw, "-i", audio_final, "-stream_loop", "-1", "-i", musica_path, "-i", sfx_correct, "-i", sfx_money,
        "-filter_complex", (
            f"[0:v]{filtros_str}[v];"
            f"[2:a]volume='{volume_expr}':eval=frame[bg];"
            f"[3:a]adelay={int(t_end_countdown*1000)}|{int(t_end_countdown*1000)}[sfx];"
            f"[4:a]adelay={int(t_end_gancho*1000)}|{int(t_end_gancho*1000)}[sfx_m];"
            "[1:a]volume=1.0[voice];"
            "[voice][bg][sfx][sfx_m]amix=inputs=4:duration=first:dropout_transition=2[a]"
        ),
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        output_path
    ]

    resultado = subprocess.run(cmd_final, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"FFmpeg falhou na montagem final:\n{resultado.stderr[-1200:]}")

    for tmp in [video_raw, audio_final, silence_path, temp_srt, video_resp_loop]:
        if os.path.exists(tmp): os.remove(tmp)

    return output_path
