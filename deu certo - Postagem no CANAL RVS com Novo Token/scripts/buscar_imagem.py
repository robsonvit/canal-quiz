"""
buscar_imagem.py
────────────────
Busca e processa 2 imagens no Pexels para o Short de Quiz:
  - Imagem da PERGUNTA: relacionada ao tema/assunto questionado
  - Imagem da RESPOSTA: mostra visualmente a resposta correta

Cada imagem é convertida para 1080×1920 (9:16 portrait) via FFmpeg
com crop centrado para maximizar o impacto visual.
"""

import os
import json
import random
import subprocess
import requests
from datetime import datetime, timedelta, timezone


# ─────────────────────────────────────────────────────────────────────────────
# Configurações
# ─────────────────────────────────────────────────────────────────────────────
PEXELS_API_KEY  = os.environ.get("PEXELS_API_KEY", "")
PEXELS_PHOTO_URL = "https://api.pexels.com/v1/search"
IMG_DIR          = os.path.join("output", "imagens")


# ─────────────────────────────────────────────────────────────────────────────
# Busca no Pexels
# ─────────────────────────────────────────────────────────────────────────────
def _buscar_foto_pexels(termos: list[str], excluir_ids: set = None) -> dict | None:
    """
    Tenta cada termo da lista até encontrar uma foto disponível no Pexels.
    Retorna dict com {id, url_original, url_large} ou None se não encontrar.
    """
    excluir_ids = excluir_ids or set()
    headers     = {"Authorization": PEXELS_API_KEY}

    for termo in termos:
        try:
            params = {
                "query":    termo,
                "per_page": 15,
                "size":     "medium",
            }
            resp = requests.get(PEXELS_PHOTO_URL, headers=headers, params=params, timeout=20)
            resp.raise_for_status()

            fotos = resp.json().get("photos", [])
            random.shuffle(fotos)

            for foto in fotos:
                fid = foto.get("id")
                if fid in excluir_ids:
                    continue
                src = foto.get("src", {})
                url = src.get("original") or src.get("large2x") or src.get("large")
                if url:
                    print(f"  📸 Foto encontrada (ID {fid}) via termo: '{termo}'")
                    return {"id": fid, "url": url, "termo": termo}

        except Exception as e:
            print(f"  ⚠️  Erro na busca Pexels ('{termo}'): {e}")
            continue

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Download e processamento FFmpeg → 1080×1920
# ─────────────────────────────────────────────────────────────────────────────
def _baixar_imagem(url: str, destino: str):
    """Baixa a imagem da URL para o destino."""
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def _processar_portrait(input_path: str, output_path: str):
    """
    Converte imagem para 1080×1920 (portrait) via FFmpeg:
      1. Escala mantendo proporção até cobrir 1080×1920
      2. Crop centrado para 1080×1920
      3. Aplica leve blur (2px) nas bordas para suavizar
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "eq=brightness=-0.02:contrast=1.03:saturation=1.1"
        ),
        "-q:v", "2",
        output_path,
    ]
    resultado = subprocess.run(cmd, capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"FFmpeg falhou ao processar imagem:\n{resultado.stderr[-500:]}")


# ─────────────────────────────────────────────────────────────────────────────
# Interface pública
# ─────────────────────────────────────────────────────────────────────────────
def buscar_imagens(
    termos_pergunta: list[str],
    termos_resposta: list[str],
    output_dir: str = "output",
) -> tuple[str, str]:
    """
    Busca e processa 2 imagens portrait para o Short de Quiz.

    Retorna:
        (caminho_imagem_pergunta, caminho_imagem_resposta)
    """
    img_dir = os.path.join(output_dir, "imagens")
    tmp_dir = os.path.join(output_dir, "tmp_img")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(tmp_dir, exist_ok=True)

    ids_usados: set = set()

    # ── Imagem da PERGUNTA ────────────────────────────────────────────────────
    print(f"  🔍 Buscando imagem da PERGUNTA: {termos_pergunta}")
    foto_p = _buscar_foto_pexels(termos_pergunta, excluir_ids=ids_usados)

    if not foto_p:
        raise RuntimeError(f"Pexels: nenhuma imagem encontrada para pergunta. Termos: {termos_pergunta}")

    ids_usados.add(foto_p["id"])
    tmp_p  = os.path.join(tmp_dir, f"raw_pergunta_{foto_p['id']}.jpg")
    img_pergunta = os.path.join(img_dir, "pergunta.jpg")

    _baixar_imagem(foto_p["url"], tmp_p)
    _processar_portrait(tmp_p, img_pergunta)
    os.remove(tmp_p)
    print(f"✅ Imagem pergunta processada: {img_pergunta}")

    # ── Imagem da RESPOSTA ────────────────────────────────────────────────────
    print(f"  🔍 Buscando imagem da RESPOSTA: {termos_resposta}")
    foto_r = _buscar_foto_pexels(
        termos_resposta + termos_pergunta,  # fallback para termos da pergunta
        excluir_ids=ids_usados,
    )

    if not foto_r:
        # Fallback: usa a mesma imagem da pergunta com ajuste de cor diferente
        print("⚠️  Usando fallback: imagem da pergunta como base para resposta")
        img_resposta = os.path.join(img_dir, "resposta.jpg")
        cmd_fallback = [
            "ffmpeg", "-y",
            "-i", img_pergunta,
            "-vf", "hflip,eq=brightness=0.05:saturation=1.3",
            img_resposta,
        ]
        subprocess.run(cmd_fallback, capture_output=True)
    else:
        tmp_r = os.path.join(tmp_dir, f"raw_resposta_{foto_r['id']}.jpg")
        img_resposta = os.path.join(img_dir, "resposta.jpg")
        _baixar_imagem(foto_r["url"], tmp_r)
        _processar_portrait(tmp_r, img_resposta)
        os.remove(tmp_r)
        print(f"✅ Imagem resposta processada: {img_resposta}")

    return img_pergunta, img_resposta


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv
    load_dotenv()

    with open("output/quiz.json", encoding="utf-8") as f:
        data = json.load(f)

    p, r = buscar_imagens(
        data["termos_imagem_pergunta"],
        data["termos_imagem_resposta"],
    )
    print(f"\nPergunta : {p}")
    print(f"Resposta : {r}")
