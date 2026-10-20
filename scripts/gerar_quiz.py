"""
gerar_quiz.py
─────────────
Gera uma pergunta de quiz no estilo "Show do Milhão" usando a API Groq
para YouTube Shorts. O novo prompt garante competição, suspense e retenção.
"""

import os
import sys
if sys.stdout and hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
import json
import re
import random
import hashlib
from datetime import datetime, timezone, timedelta
import requests
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
8. REGRA DE HASHTAGS: Todas as hashtags (#) na descrição ou no título DEVEM estar OBRIGATORIAMENTE em LETRAS MINÚSCULAS (exemplo: #shorts #quiz #curiosidades #showdomilhao #ciencia). NUNCA utilize letras maiúsculas em nenhuma hashtag.
"""

def obter_modelos_gratuitos(api_key: str | None = None) -> list[str]:
    """
    Consulta dinamicamente a API da OpenRouter para obter a lista atualizada
    de modelos gratuitos disponíveis (pricing=0 ou sufixo ':free'),
    filtrando apenas modelos de texto/chat e priorizando os melhores.
    """
    modelos_fallback = [
        "openrouter/free",
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "nvidia/nemotron-3.5-lightning:free",
        "liquid/lfm-2.5-2.6b:free",
        "meta-llama/llama-3.3-70b-instruct:free",
    ]

    headers = {
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Canal Quiz"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])

        gratuitos = []
        for m in data:
            mid = m.get("id", "")
            pricing = m.get("pricing", {})
            is_free = mid.endswith(":free") or (
                str(pricing.get("prompt", "")).strip() in ("0", "0.0") and
                str(pricing.get("completion", "")).strip() in ("0", "0.0")
            )
            if not is_free:
                continue

            # Ignorar modelos de moderação, segurança ou embedding
            mid_lower = mid.lower()
            if any(ign in mid_lower for ign in ["safety", "guard", "moderation", "embed"]):
                continue

            # Verificar se gera texto
            arch = m.get("architecture", {})
            out_mod = arch.get("output_modalities", ["text"])
            if "text" not in out_mod:
                continue

            gratuitos.append(mid)

        # Priorização dos melhores modelos para JSON e língua portuguesa
        def prioridade(m_id: str) -> int:
            m_l = m_id.lower()
            if m_id == "openrouter/free": return 0
            if "gemini" in m_l: return 1
            if "gemma" in m_l: return 2
            if "llama" in m_l: return 3
            if "qwen" in m_l: return 4
            if "nemotron" in m_l: return 5
            if "minimax" in m_l: return 6
            return 10

        gratuitos.sort(key=prioridade)

        if "openrouter/free" not in gratuitos:
            gratuitos.insert(0, "openrouter/free")

        if gratuitos:
            print(f"🌐 OpenRouter: {len(gratuitos)} modelos gratuitos encontrados em tempo real.")
            return gratuitos

    except Exception as e:
        print(f"⚠️ Erro ao consultar modelos em tempo real na OpenRouter: {e}. Usando lista de fallback.")

    return modelos_fallback


def gerar_quiz() -> dict:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY não foi encontrada nas variáveis de ambiente.")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
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
  "descricao": "[DESCRIÇÃO COMEÇANDO COM A PERGUNTA. USE HASHTAGS OBRIGATORIAMENTE EM LETRAS MINÚSCULAS COMO #shorts #quiz #curiosidades. max 400 chars]",
  "tags": ["shorts", "quiz", "curiosidades", "{tema}"]
}}

LEMBRE-SE: Retorne APENAS o JSON."""

    modelos_gratuitos = obter_modelos_gratuitos(api_key)
    dados = None
    erros = []

    for idx, modelo in enumerate(modelos_gratuitos, start=1):
        print(f"🤖 [{idx}/{len(modelos_gratuitos)}] Testando modelo gratuito: {modelo}...")
        try:
            response = client.chat.completions.create(
                model=modelo,
                messages=[
                    {"role": "system", "content": "Você é um assistente prestativo e um roteirista criativo. Retorne apenas JSON válido sem texto adicional."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800,
            )

            if not response.choices or not response.choices[0].message:
                raise ValueError("Resposta sem escolhas/mensagem")

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Conteúdo da mensagem vazio ou nulo")

            content = content.strip()

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            start = content.find("{")
            end   = content.rfind("}") + 1
            if start != -1 and end > start:
                content = content[start:end]

            dados_tentativa = json.loads(content)

            # Validações dos campos obrigatórios
            if not dados_tentativa.get("pergunta"):
                raise ValueError("Campo 'pergunta' ausente")
            if not isinstance(dados_tentativa.get("alternativas"), list) or len(dados_tentativa["alternativas"]) != 4:
                raise ValueError("Campo 'alternativas' inválido (deve ser lista com 4 opções)")
            if "letra_correta" not in dados_tentativa:
                raise ValueError("Campo 'letra_correta' ausente")

            # Normalização de letra_correta para inteiro (1, 2, 3 ou 4)
            raw_lc = str(dados_tentativa.get("letra_correta", "1")).strip().upper()
            mapa_letras = {"A": 1, "B": 2, "C": 3, "D": 4, "1": 1, "2": 2, "3": 3, "4": 4}
            num_correta = 1
            for k, v in mapa_letras.items():
                if k in raw_lc:
                    num_correta = v
                    break
            dados_tentativa["letra_correta"] = num_correta

            # Normalização de hashtags para letras minúsculas (ex: #shorts #quiz)
            if "descricao" in dados_tentativa and isinstance(dados_tentativa["descricao"], str):
                dados_tentativa["descricao"] = re.sub(
                    r'#([A-Za-z0-9_À-ÿ]+)',
                    lambda m: '#' + m.group(1).lower(),
                    dados_tentativa["descricao"]
                )

            if "titulo" in dados_tentativa and isinstance(dados_tentativa["titulo"], str):
                dados_tentativa["titulo"] = re.sub(
                    r'#([A-Za-z0-9_À-ÿ]+)',
                    lambda m: '#' + m.group(1).lower(),
                    dados_tentativa["titulo"]
                )

            if "tags" in dados_tentativa and isinstance(dados_tentativa["tags"], list):
                dados_tentativa["tags"] = [str(t).lower() for t in dados_tentativa["tags"]]

            dados = dados_tentativa
            print(f"✨ Sucesso com o modelo: {modelo}")
            break

        except Exception as e:
            msg_erro = str(e)
            erros.append(f"{modelo}: {msg_erro}")
            print(f"⚠️  Falha no modelo {modelo}: {msg_erro[:150]}")
            continue

    if not dados:
        raise RuntimeError(
            f"Nenhum modelo gratuito da OpenRouter conseguiu gerar o quiz com sucesso.\n"
            f"Tentativas ({len(erros)}):\n" + "\n".join(erros[:5])
        )

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
    print(f"   CTA       : {dados.get('cta', '')[:70]}")

    return dados

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    os.makedirs("output", exist_ok=True)
    resultado = gerar_quiz()
    with open("output/quiz.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(f"\\n✅ Quiz salvo em output/quiz.json")
