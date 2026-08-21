"""
gerar_quiz.py
─────────────
Gera uma pergunta de quiz no estilo "Show do Milhão" usando a API Groq
para YouTube Shorts. O novo prompt garante competição, suspense e retenção.
"""

import os
import json
import random
import hashlib
from datetime import datetime, timezone, timedelta
from openai import OpenAI

# ─────────────────────────────────────────────────────────────────────────────
# Banco de temas
# ─────────────────────────────────────────────────────────────────────────────
TEMAS = [
    ("comportamento animal",          1, ["animal", "wildlife", "creature"]),
    ("biologia humana",               1, ["human body", "biology", "anatomy"]),
    ("natureza curiosa",               1, ["nature", "plant", "forest"]),
    ("física do cotidiano",            1, ["physics", "experiment", "science"]),
    ("fatos históricos curiosos",      1, ["history", "ancient", "museum"]),
    ("astronomia e espaço",            1, ["space", "galaxy", "stars", "planet"]),
    ("química curiosa",                1, ["laboratory", "chemistry", "experiment"]),
    ("culinária e gastronomia",        1, ["food", "cooking", "kitchen", "chef"]),
    ("matemática e números",           1, ["mathematics", "numbers", "calculation"]),
    ("raciocínio lógico",              1, ["puzzle", "brain", "logic", "thinking"]),
    ("geografia mundial",              1, ["world map", "geography", "countries"]),
    ("história geral",                 1, ["history", "civilization", "ancient"]),
    ("filosofia básica",               1, ["philosophy", "thinking", "wisdom"]),
    ("física básica",                  1, ["physics", "science", "experiment"]),
    ("fenômenos da natureza",          1, ["nature", "lightning", "weather", "storm"]),
    ("teorias científicas curiosas",   1, ["science", "theory", "discovery"]),
    ("futebol e esporte",              1, ["football", "soccer", "stadium", "sport"]),
]

TRACKING_FILE = os.path.join("data", "perguntas_usadas.json")
TEMAS_TRACKING_FILE = os.path.join("data", "temas_usados.json")
DIAS_BLOQUEIO = 30

def _carregar_tracking() -> dict:
    os.makedirs("data", exist_ok=True)
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, encoding="utf-8") as f:
            try: return json.load(f)
            except Exception: return {}
    return {}

def _carregar_temas_tracking() -> dict:
    os.makedirs("data", exist_ok=True)
    if os.path.exists(TEMAS_TRACKING_FILE):
        with open(TEMAS_TRACKING_FILE, encoding="utf-8") as f:
            try: return json.load(f)
            except Exception: return {}
    return {}

def _salvar_tracking(tracking: dict):
    os.makedirs("data", exist_ok=True)
    with open(TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(tracking, f, ensure_ascii=False, indent=2)

def _salvar_temas_tracking(tracking: dict):
    os.makedirs("data", exist_ok=True)
    with open(TEMAS_TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(tracking, f, ensure_ascii=False, indent=2)

def _hash_pergunta(texto: str) -> str:
    return hashlib.md5(texto.lower().strip().encode()).hexdigest()[:12]

def _marcar_usada(pergunta: str, tracking: dict):
    h = _hash_pergunta(pergunta)
    tracking[h] = datetime.now(timezone.utc).isoformat()

def _ja_foi_usada(pergunta: str, tracking: dict) -> bool:
    h = _hash_pergunta(pergunta)
    if h not in tracking: return False
    ultimo = datetime.fromisoformat(tracking[h])
    return (datetime.now(timezone.utc) - ultimo).days < DIAS_BLOQUEIO

def _escolher_tema(temas_tracking: dict) -> tuple[str, list[str]]:
    hoje = datetime.now(timezone.utc).date()
    ontem = hoje - timedelta(days=1)
    
    str_hoje = hoje.isoformat()
    str_ontem = ontem.isoformat()
    
    temas_hoje = temas_tracking.get(str_hoje, [])
    temas_ontem = temas_tracking.get(str_ontem, [])
    
    temas_bloqueados = set(temas_hoje + temas_ontem)
    temas_disponiveis = [t for t in TEMAS if t[0] not in temas_bloqueados]
    
    if not temas_disponiveis:
        print("⚠️ Aviso: Todos os temas bloqueados. Ignorando regras de bloqueio hoje.")
        temas_disponiveis = TEMAS

    temas   = [t[0] for t in temas_disponiveis]
    pesos   = [t[1] for t in temas_disponiveis]
    imagens = {t[0]: t[2] for t in TEMAS}
    tema    = random.choices(temas, weights=pesos, k=1)[0]
    return tema, imagens[tema]


PROMPT_MESTRE = """# PROMPT MESTRE — ROTEIRISTA DE SHORTS DE QUIZ

Você é um roteirista especialista em criar **YouTube Shorts virais de quiz**, inspirados na dinâmica dos grandes programas brasileiros de perguntas e respostas.

O canal possui uma identidade inspirada na nostalgia dos grandes programas de perguntas e respostas brasileiros e presta uma homenagem à memória de **Silvio Santos**.

## REGRAS:
1. Comece com um gancho forte EXACTAMENTE assim: "Bem vindo ao show do milhão, você consegue responder a próxima pergunta valendo [VALOR] reais?". Onde [VALOR] é um prêmio atrativo (Ex: 1 milhão, 500 mil, etc).
2. A pergunta deve ter 4 alternativas curtas.
3. Não use alternativas absurdas e distribua a resposta correta de forma aleatória.
4. O campo "alternativas" deve ser UMA LISTA (array) com as 4 opções completas em texto.
5. Indique a resposta correta num campo "letra_correta" (1, 2, 3 ou 4).
6. A revelação e explicação devem ser diretas e curtas.
7. Termine com um CTA que estimule os comentários.
"""

def gerar_quiz() -> dict:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        default_headers={
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Canal Quiz"
        }
    )
    tracking = _carregar_tracking()
    temas_tracking = _carregar_temas_tracking()

    tema, termos_base = _escolher_tema(temas_tracking)

    prompt = f"""{PROMPT_MESTRE}
---
TEMA: {tema}

FORMATO OBRIGATÓRIO DE SAÍDA:
Você DEVE retornar APENAS um objeto JSON válido.
A estrutura do JSON deve ser exatamente esta:
{{
  "gancho": "Bem vindo ao show do milhão, você consegue responder a próxima pergunta valendo 1 milhão de reais?",
  "pergunta": "[A PERGUNTA EM SI]",
  "alternativas": [
    "[PRIMEIRA ALTERNATIVA]",
    "[SEGUNDA ALTERNATIVA]",
    "[TERCEIRA ALTERNATIVA]",
    "[QUARTA ALTERNATIVA]"
  ],
  "letra_correta": [NÚMERO DA ALTERNATIVA CORRETA: 1, 2, 3 ou 4],
  "explicacao": "[EXPLICAÇÃO CURTA E REVELAÇÃO DA RESPOSTA]",
  "cta": "[O CTA PARA O VÍDEO]",
  "titulo": "[TÍTULO DO SHORT, max 80 chars, em caixa alta, não revele a resposta]",
  "descricao": "[DESCRIÇÃO COMEÇANDO COM A PERGUNTA. USE HASHTAGS. max 400 chars]",
  "tags": ["Shorts", "Quiz", "Curiosidades", "{tema}"]
}}

LEMBRE-SE: Retorne APENAS o JSON."""

    response = client.chat.completions.create(
        model="google/gemini-2.5-flash",
        messages=[
            {"role": "system", "content": "Você é um assistente prestativo e um roteirista criativo."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.9,
        max_tokens=800,
    )

    content = response.choices[0].message.content.strip()

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    start = content.find("{")
    end   = content.rfind("}") + 1
    if start != -1 and end > start:
        content = content[start:end]

    try:
        dados = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Groq não retornou JSON válido: {e}\\nResposta: {content[:300]}")

    if _ja_foi_usada(dados.get("pergunta", ""), tracking):
        print("⚠️  Pergunta recente detectada, gerando nova tentativa...")
        return gerar_quiz()

    dados.setdefault("termos_imagem_pergunta", termos_base)
    dados.setdefault("termos_imagem_resposta", termos_base[:2])
    dados["tema"] = tema

    _marcar_usada(dados["pergunta"], tracking)
    _salvar_tracking(tracking)
    
    hoje_str = datetime.now(timezone.utc).date().isoformat()
    if hoje_str not in temas_tracking:
        temas_tracking[hoje_str] = []
    temas_tracking[hoje_str].append(tema)
    _salvar_temas_tracking(temas_tracking)

    print(f"✅ Quiz gerado — tema: {tema}")
    print(f"   Pergunta  : {dados['pergunta'][:70]}...")
    print(f"   CTA       : {dados['cta'][:70]}")

    return dados

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    os.makedirs("output", exist_ok=True)
    resultado = gerar_quiz()
    with open("output/quiz.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(f"\\n✅ Quiz salvo em output/quiz.json")
