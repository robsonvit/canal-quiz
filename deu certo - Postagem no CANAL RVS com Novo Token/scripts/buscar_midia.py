"""
buscar_midia.py
───────────────
Busca e processa mídias no Pexels para o Short de Quiz:
  - Pergunta: Não baixa imagem (agora usamos fundo de cor sólida no montar_video)
  - Resposta: Busca um VÍDEO vertical relacionado à resposta

O vídeo é convertido para 1080×1920 (9:16 portrait) via FFmpeg
com crop centrado para maximizar o impacto visual.
"""

import os
import json
import random
import subprocess
import requests

# ─────────────────────────────────────────────────────────────────────────────
# Configurações
# ─────────────────────────────────────────────────────────────────────────────
PEXELS_API_KEY  = os.environ.get("PEXELS_API_KEY", "")
PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
OUT_DIR          = os.path.join("output", "imagens")

# ─────────────────────────────────────────────────────────────────────────────
# Busca no Pexels
# ─────────────────────────────────────────────────────────────────────────────
def _buscar_video_pexels(termos: list[str]) -> dict | None:
    """
    Tenta cada termo da lista até encontrar um vídeo disponível no Pexels.
    Filtra por orientação portrait.
    Retorna dict com {id, url, termo} ou None.
    """
    headers = {"Authorization": PEXELS_API_KEY}

    for termo in termos:
        try:
            params = {
                "query": termo,
                "per_page": 10,
                "orientation": "portrait",
                "size": "large"
            }
            resp = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=20)
            resp.raise_for_status()

            videos = resp.json().get("videos", [])
            random.shuffle(videos)

            for video in videos:
                vid = video.get("id")
                video_files = video.get("video_files", [])
                
                # Pega o arquivo com melhor qualidade vertical
                best_file = None
                for vf in video_files:
                    if vf.get("quality") == "hd" or vf.get("quality") == "uhd":
                        best_file = vf.get("link")
                        break
                
                if not best_file and video_files:
                    best_file = video_files[0].get("link")

                if best_file:
                    print(f"  🎥 Vídeo encontrado (ID {vid}) via termo: '{termo}'")
                    return {"id": vid, "url": best_file, "termo": termo}

        except Exception as e:
            print(f"  ⚠️  Erro na busca Pexels Vídeo ('{termo}'): {e}")
            continue

    return None

# ─────────────────────────────────────────────────────────────────────────────
# Download e processamento FFmpeg → 1080×1920
# ─────────────────────────────────────────────────────────────────────────────
def _baixar_midia(url: str, destino: str):
    """Baixa a mídia da URL para o destino."""
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def _processar_video_portrait(input_path: str, output_path: str):
    """
    Converte vídeo para 1080×1920 (portrait) via FFmpeg sem som.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-an", # Remove áudio do vídeo do pexels
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        output_path,
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"FFmpeg falhou ao processar vídeo:\n{resultado.stderr[-500:]}")

# ─────────────────────────────────────────────────────────────────────────────
# Interface pública
# ─────────────────────────────────────────────────────────────────────────────
def buscar_midias(
    termos_resposta: list[str],
    termos_pergunta: list[str],
    output_dir: str = "output",
) -> str:
    """
    Busca e processa 1 vídeo portrait para a resposta do Quiz.
    A pergunta usará fundo de cor sólida, então não baixamos mídia pra ela.

    Retorna:
        caminho_video_resposta
    """
    vid_dir = os.path.join(output_dir, "imagens")
    tmp_dir = os.path.join(output_dir, "tmp_img")
    os.makedirs(vid_dir, exist_ok=True)
    os.makedirs(tmp_dir, exist_ok=True)

    # ── Vídeo da RESPOSTA ────────────────────────────────────────────────────
    print(f"  🔍 Buscando VÍDEO da RESPOSTA: {termos_resposta}")
    video_r = _buscar_video_pexels(termos_resposta + termos_pergunta)

    video_resposta = os.path.join(vid_dir, "resposta.mp4")

    if not video_r:
        print("⚠️  Nenhum vídeo encontrado. Gerando fallback (vídeo com cor sólida preta)...")
        # Gera 10 segundos de vídeo preto
        cmd_fallback = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=10",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            video_resposta,
        ]
        subprocess.run(cmd_fallback, capture_output=True)
    else:
        tmp_r = os.path.join(tmp_dir, f"raw_resposta_{video_r['id']}.mp4")
        print(f"  ⏳ Baixando vídeo...")
        _baixar_midia(video_r["url"], tmp_r)
        print(f"  🎬 Processando vídeo para 9:16...")
        _processar_video_portrait(tmp_r, video_resposta)
        os.remove(tmp_r)
        print(f"✅ Vídeo resposta processado: {video_resposta}")

    return video_resposta

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv
    load_dotenv()

    with open("output/quiz.json", encoding="utf-8") as f:
        data = json.load(f)

    r = buscar_midias(
        data["termos_imagem_resposta"],
        data["termos_imagem_pergunta"]
    )
    print(f"Resposta : {r}")
