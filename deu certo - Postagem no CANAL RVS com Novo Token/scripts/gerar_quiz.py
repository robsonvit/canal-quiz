"""
gerar_quiz.py
─────────────
Gera uma pergunta curiosa + resposta + curiosidade extra usando a API Groq
(llama-3.3-70b-versatile) no formato "Modo Engenharia" para YouTube Shorts.

Formato do Short:
  Ato 1 → Pergunta (voz + imagem relacionada)
  Ato 2 → Countdown 3 segundos (suspense)
  Ato 3 → Resposta + curiosidade extra (voz + imagem da resposta)

Temas: biologia, natureza, ciência, comportamento animal, corpo humano,
       fatos históricos curiosos, física do cotidiano.
"""

import os
import json
import random
import hashlib
from datetime import datetime, timezone

from groq import Groq

# ─────────────────────────────────────────────────────────────────────────────
# Banco de temas com pesos (para variar o conteúdo)
# ─────────────────────────────────────────────────────────────────────────────
TEMAS = [
    # (tema, peso, exemplos de termos de busca de imagem para pergunta)
    ("comportamento animal",    25, ["animal", "wildlife", "creature"]),
    ("biologia humana",         20, ["human body", "biology", "science"]),
    ("natureza curiosa",        20, ["nature", "plant", "forest"]),
    ("física do cotidiano",     10, ["physics", "experiment", "science"]),
    ("fatos históricos",        10, ["history", "ancient", "museum"]),
    ("astronomia",               8, ["space", "galaxy", "stars"]),
    ("química curiosa",          7, ["laboratory", "chemistry", "experiment"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# Tracking de perguntas usadas (evitar repetição)
# ─────────────────────────────────────────────────────────────────────────────
TRACKING_FILE = os.path.join("data", "perguntas_usadas.json")
DIAS_BLOQUEIO = 30  # Dias antes de reusar uma pergunta


def _carregar_tracking() -> dict:
    os.makedirs("data", exist_ok=True)
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}


def _salvar_tracking(tracking: dict):
    os.makedirs("data", exist_ok=True)
    with open(TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(tracking, f, ensure_ascii=False, indent=2)


def _hash_pergunta(texto: str) -> str:
    return hashlib.md5(texto.lower().strip().encode()).hexdigest()[:12]


def _marcar_usada(pergunta: str, tracking: dict):
    h = _hash_pergunta(pergunta)
    tracking[h] = datetime.now(timezone.utc).isoformat()


def _ja_foi_usada(pergunta: str, tracking: dict) -> bool:
    h = _hash_pergunta(pergunta)
    if h not in tracking:
        return False
    from datetime import timedelta
    ultimo = datetime.fromisoformat(tracking[h])
    return (datetime.now(timezone.utc) - ultimo).days < DIAS_BLOQUEIO


# ─────────────────────────────────────────────────────────────────────────────
# Seleção de tema com peso
# ─────────────────────────────────────────────────────────────────────────────
def _escolher_tema() -> tuple[str, list[str]]:
    temas   = [t[0] for t in TEMAS]
    pesos   = [t[1] for t in TEMAS]
    imagens = {t[0]: t[2] for t in TEMAS}
    tema    = random.choices(temas, weights=pesos, k=1)[0]
    return tema, imagens[tema]


# ─────────────────────────────────────────────────────────────────────────────
# Geração principal via Groq
# ─────────────────────────────────────────────────────────────────────────────
def gerar_quiz() -> dict:
    """
    Gera um quiz no formato Modo Engenharia.

    Retorna dict com:
        pergunta_texto, resposta_texto, curiosidade_texto,
        termos_imagem_pergunta, termos_imagem_resposta,
        tema, titulo, descricao, tags
    """
    client   = Groq(api_key=os.environ["GROQ_API_KEY"])
    tracking = _carregar_tracking()

    tema, termos_base = _escolher_tema()

    prompt = f"""Você é um criador de conteúdo viral para YouTube Shorts brasileiro.
Crie UMA pergunta curiosa e surpreendente sobre o tema: **{tema}**.

FORMATO OBRIGATÓRIO — responda APENAS o JSON abaixo, sem texto adicional:

{{
  "pergunta_texto": "Texto da pergunta. DEVE SER EXTREMAMENTE CURTA E DIRETA (MÁXIMO 10-15 PALAVRAS). Vá direto ao ponto, por exemplo: 'Qual o animal mais venenoso do mundo?' ou 'Qual planeta tem chova de diamantes?'. Não use introduções longas como 'Você sabia...'. Termine com '...você tem 3 segundos para responder!'",
  "resposta_texto": "Resposta direta e clara, 1 frase curta e impactante.",
  "curiosidade_texto": "Uma curiosidade extra relacionada, 2-3 frases que aprofundam a resposta. Tom científico mas acessível.",
  "termos_imagem_pergunta": ["termo1_ingles", "termo2_ingles"],
  "termos_imagem_resposta": ["termo1_ingles", "termo2_ingles"],
  "titulo": "Emoji + título curto para Short (máx 80 chars) com #Shorts no final",
  "descricao": "Descrição de até 300 chars para o YouTube com a pergunta e resposta resumidas. Use emojis. Inclua #Shorts #Quiz #Curiosidades",
  "tags": ["Shorts", "Quiz", "Curiosidades", "Você Sabia", "{tema}", "fatos curiosos", "biologia", "ciência", "conhecimento"]
}}

REGRAS:
- A pergunta DEVE SER OBJETIVA, DIRETA E CURTA (máx 15 palavras).
- A resposta deve ser verificável e factualmente correta
- Os termos de imagem devem ser em INGLÊS para busca no Pexels
- Tom: animado, direto, engajante
- Sem markdown fora do JSON
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=800,
    )

    content = response.choices[0].message.content.strip()

    # Extrair JSON da resposta
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    # Tentar localizar o JSON mesmo com texto antes/depois
    start = content.find("{")
    end   = content.rfind("}") + 1
    if start != -1 and end > start:
        content = content[start:end]

    try:
        dados = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Groq não retornou JSON válido: {e}\nResposta: {content[:300]}")

    # Verificar se a pergunta já foi usada recentemente
    if _ja_foi_usada(dados.get("pergunta_texto", ""), tracking):
        print("⚠️  Pergunta recente detectada, gerando nova tentativa...")
        return gerar_quiz()  # Tenta de novo (máx 1 nível de recursão)

    # Mesclar termos de imagem com os do tema base
    dados.setdefault("termos_imagem_pergunta", termos_base)
    dados.setdefault("termos_imagem_resposta", termos_base[:2])
    dados["tema"] = tema

    # Registrar como usada
    _marcar_usada(dados["pergunta_texto"], tracking)
    _salvar_tracking(tracking)

    palavras_p = len(dados["pergunta_texto"].split())
    palavras_r = len((dados["resposta_texto"] + " " + dados["curiosidade_texto"]).split())
    print(f"✅ Quiz gerado — tema: {tema}")
    print(f"   Pergunta  : {dados['pergunta_texto'][:70]}...")
    print(f"   Resposta  : {dados['resposta_texto'][:70]}")
    print(f"   Palavras  : pergunta={palavras_p} / resposta={palavras_r}")

    return dados


# ─────────────────────────────────────────────────────────────────────────────
# Teste local
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from dotenv import load_dotenv
    load_dotenv()

    os.makedirs("output", exist_ok=True)
    resultado = gerar_quiz()

    with open("output/quiz.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Quiz salvo em output/quiz.json")
    print(f"   Título: {resultado.get('titulo', '?')}")
