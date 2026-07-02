"""
buscar_midia.py
───────────────
Busca e processa mídias no Pexels para o Short de Quiz:
  - Pergunta: Não baixa imagem (agora usamos fundo de cor sólida no montar_video)
  - Resposta: Busca múltiplos VÍDEOS verticais relacionados à resposta

Os vídeos são convertidos para 1080×1920 (9:16 portrait) via FFmpeg,
cortados em no máximo 5 segundos cada, e concatenados para gerar
um único arquivo `resposta.mp4` diversificado.
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
def _buscar_videos_pexels(termos: list[str], max_videos: int = 3) -> list[dict]:
    """
    Tenta encontrar múltiplos vídeos disponíveis no Pexels.
    Filtra por orientação portrait.
    Retorna lista de dicts com {id, url, termo}.
    """
    headers = {"Authorization": PEXELS_API_KEY}
    videos_encontrados = []
    ids_usados = set()

    for termo in termos:
        try:
            params = {
                "query": termo,
                "per_page": 15,
                "orientation": "portrait",
                "size": "large"
            }
            resp = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=20)
            resp.raise_for_status()

            videos = resp.json().get("videos", [])
            random.shuffle(videos)

            for video in videos:
                if len(videos_encontrados) >= max_videos:
                    return videos_encontrados

                vid = video.get("id")
                if vid in ids_usados:
                    continue

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
                    videos_encontrados.append({"id": vid, "url": best_file, "termo": termo})
                    ids_usados.add(vid)

        except Exception as e:
            print(f"  ⚠️  Erro na busca Pexels Vídeo ('{termo}'): {e}")
            continue

    return videos_encontrados

# ─────────────────────────────────────────────────────────────────────────────
# Download e processamento FFmpeg → 1080×1920 e 5s max
# ─────────────────────────────────────────────────────────────────────────────
def _baixar_midia(url: str, destino: str):
    """Baixa a mídia da URL para o destino."""
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def _processar_video_portrait_5s(input_path: str, output_path: str):
    """
    Converte vídeo para 1080×1920 (portrait) via FFmpeg sem som, cortado para 5s.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-t", "5", # Corta em 5 segundos no máximo
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
    Busca e processa até 3 vídeos portrait para a resposta do Quiz.
    A pergunta usará fundo de cor sólida, então não baixamos mídia pra ela.

    Retorna:
        caminho_video_resposta (vídeo final concatenado)
    """
    vid_dir = os.path.join(output_dir, "imagens")
    tmp_dir = os.path.join(output_dir, "tmp_img")
    os.makedirs(vid_dir, exist_ok=True)
    os.makedirs(tmp_dir, exist_ok=True)

    video_resposta_final = os.path.join(vid_dir, "resposta.mp4")

    # ── Vídeo da RESPOSTA ────────────────────────────────────────────────────
    print(f"  🔍 Buscando VÍDEOS da RESPOSTA: {termos_resposta}")
    videos_r = _buscar_videos_pexels(termos_resposta + termos_pergunta, max_videos=3)

    if not videos_r:
        print("⚠️  Nenhum vídeo encontrado. Gerando fallback (vídeo com cor sólida preta)...")
        # Gera 10 segundos de vídeo preto
        cmd_fallback = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=10",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            video_resposta_final,
        ]
        subprocess.run(cmd_fallback, capture_output=True)
        return video_resposta_final

    videos_processados = []
    
    for i, v in enumerate(videos_r):
        tmp_raw = os.path.join(tmp_dir, f"raw_resposta_{v['id']}.mp4")
        tmp_proc = os.path.join(tmp_dir, f"proc_resposta_{v['id']}.mp4")
        
        print(f"  ⏳ Baixando vídeo {i+1}...")
        _baixar_midia(v["url"], tmp_raw)
        
        print(f"  🎬 Processando vídeo {i+1} para 9:16 (max 5s)...")
        _processar_video_portrait_5s(tmp_raw, tmp_proc)
        
        videos_processados.append(tmp_proc)
        os.remove(tmp_raw)

    if len(videos_processados) == 1:
        # Só achou 1, renomeia e retorna
        os.rename(videos_processados[0], video_resposta_final)
    else:
        print("✂️  Concatenando vídeos de resposta...")
        lista_path = os.path.join(tmp_dir, "lista_videos.txt")
        with open(lista_path, "w") as f:
            for p in videos_processados:
                f.write(f"file '{os.path.abspath(p).replace(chr(92), '/')}'\n")

        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", lista_path,
            "-c", "copy",
            video_resposta_final,
        ]
        subprocess.run(cmd_concat, capture_output=True, check=True)
        
        # Limpeza
        os.remove(lista_path)
        for p in videos_processados:
            os.remove(p)

    print(f"✅ Vídeo resposta processado: {video_resposta_final}")
    return video_resposta_final

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
