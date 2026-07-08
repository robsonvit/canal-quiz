"""
gerar_quiz.py
─────────────
Gera uma pergunta curiosa + resposta + curiosidade extra usando a API Groq
(llama-3.3-70b-versatile) no formato "Modo Engenharia" para YouTube Shorts.

Formato do Short:
  Ato 1 → Pergunta (voz + imagem relacionada)
  Ato 2 → Countdown 3 segundos (suspense)
  Ato 3 → Resposta + curiosidade extra (voz + imagem da resposta)

Temas: comportamento animal, biologia humana, natureza, física, história,
       astronomia, química, culinária, matemática, raciocínio lógico,
       geografia, filosofia, fenômenos da natureza, teorias, futebol.
"""

import os
import json
import random
import hashlib
from datetime import datetime, timezone, timedelta

from groq import Groq

# ─────────────────────────────────────────────────────────────────────────────
# Banco de temas com pesos (para variar o conteúdo)
# ─────────────────────────────────────────────────────────────────────────────
TEMAS = [
    # (tema, peso, exemplos de termos de busca de imagem para pergunta)
    ("comportamento animal",          10, ["animal", "wildlife", "creature"]),
    ("biologia humana",               10, ["human body", "biology", "anatomy"]),
    ("natureza curiosa",               8, ["nature", "plant", "forest"]),
    ("física do cotidiano",            7, ["physics", "experiment", "science"]),
    ("fatos históricos curiosos",      8, ["history", "ancient", "museum"]),
    ("astronomia e espaço",            8, ["space", "galaxy", "stars", "planet"]),
    ("química curiosa",                5, ["laboratory", "chemistry", "experiment"]),
    ("culinária e gastronomia",        7, ["food", "cooking", "kitchen", "chef"]),
    ("matemática e números",           7, ["mathematics", "numbers", "calculation"]),
    ("raciocínio lógico",              7, ["puzzle", "brain", "logic", "thinking"]),
    ("geografia mundial",              6, ["world map", "geography", "countries"]),
    ("história geral",                 6, ["history", "civilization", "ancient"]),
    ("filosofia básica",               4, ["philosophy", "thinking", "wisdom"]),
    ("física básica",                  5, ["physics", "science", "experiment"]),
    ("fenômenos da natureza",          6, ["nature", "lightning", "weather", "storm"]),
    ("teorias científicas curiosas",   4, ["science", "theory", "discovery"]),
    ("futebol e esporte",              7, ["football", "soccer", "stadium", "sport"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# Tracking de perguntas usadas (evitar repetição)
# ─────────────────────────────────────────────────────────────────────────────
TRACKING_FILE = os.path.join("data", "perguntas_usadas.json")
TEMAS_TRACKING_FILE = os.path.join("data", "temas_usados.json")
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


def _carregar_temas_tracking() -> dict:
    os.makedirs("data", exist_ok=True)
    if os.path.exists(TEMAS_TRACKING_FILE):
        with open(TEMAS_TRACKING_FILE, encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
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
    if h not in tracking:
        return False
    from datetime import timedelta
    ultimo = datetime.fromisoformat(tracking[h])
    return (datetime.now(timezone.utc) - ultimo).days < DIAS_BLOQUEIO


# ─────────────────────────────────────────────────────────────────────────────
# Seleção de tema com peso e bloqueio de repetição
# ─────────────────────────────────────────────────────────────────────────────
def _escolher_tema(temas_tracking: dict) -> tuple[str, list[str]]:
    hoje = datetime.now(timezone.utc).date()
    ontem = hoje - timedelta(days=1)
    
    str_hoje = hoje.isoformat()
    str_ontem = ontem.isoformat()
    
    temas_hoje = temas_tracking.get(str_hoje, [])
    temas_ontem = temas_tracking.get(str_ontem, [])
    
    temas_bloqueados = set(temas_hoje + temas_ontem)
    
    temas_disponiveis = [t for t in TEMAS if t[0] not in temas_bloqueados]
    
    # Se por algum motivo bloqueou todos (improvável), fallback para todos
    if not temas_disponiveis:
        print("⚠️ Aviso: Todos os temas bloqueados. Ignorando regras de bloqueio hoje.")
        temas_disponiveis = TEMAS

    temas   = [t[0] for t in temas_disponiveis]
    pesos   = [t[1] for t in temas_disponiveis]
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
    temas_tracking = _carregar_temas_tracking()

    tema, termos_base = _escolher_tema(temas_tracking)

    prompt = f"""Você é um criador de conteúdo viral para YouTube Shorts brasileiro.
Crie UMA pergunta curiosa e surpreendente sobre o tema: **{tema}**.

FORMATO OBRIGATÓRIO — responda APENAS o JSON abaixo, sem texto adicional:

{{
  "pergunta_texto": "Texto da pergunta. DEVE SER EXTREMAMENTE CURTA E DIRETA (MÁXIMO 10-15 PALAVRAS). Vá direto ao ponto. Exemplos por tema:\n- animal: 'Qual o animal mais venenoso do mundo?'\n- astronomia: 'Qual planeta tem chuva de diamantes?'\n- culinária: 'Qual o tempero mais caro do mundo?'\n- matemática: 'Qual número dividido por zero não tem resposta?'\n- raciocínio lógico: 'Se hoje é quarta, que dia será daqui a 100 dias?'\n- geografia: 'Qual país tem mais idiomas oficiais do mundo?'\n- história: 'Qual civilização inventou o papel?'\n- filosofia: 'Quem disse que só sei que nada sei?'\n- física: 'Por que o céu é azul e não verde?'\n- fenômenos: 'Por que os relâmpagos caem em lugares altos?'\n- futebol: 'Qual jogador ganhou mais Copas do Mundo?'\nNão use introduções longas como 'Você sabia...'. Termine com '...você tem 3 segundos para responder!'",
  "resposta_texto": "Resposta direta e clara, 1 frase curta e impactante.",
  "curiosidade_texto": "Uma curiosidade extra relacionada, 2-3 frases que aprofundam a resposta. Tom acessível e envolvente.",
  "termos_imagem_pergunta": ["termo1_ingles", "termo2_ingles"],
  "termos_imagem_resposta": ["termo1_ingles", "termo2_ingles"],
  "titulo": "Emoji + título curto para Short (máx 80 chars) com #Shorts no final",
  "descricao": "IMPORTANTE: A descrição DEVE COMEÇAR com a pergunta exata do vídeo (campo pergunta_texto, sem o final '...você tem 3 segundos para responder!'). Depois adicione a resposta e use emojis. Máx 400 chars. Inclua #Shorts #Quiz #Curiosidades no final.",
  "tags": ["Shorts", "Quiz", "Curiosidades", "Você Sabia", "{tema}", "fatos curiosos", "ciência", "conhecimento", "quiz brasil", "perguntas e respostas"]
}}

REGRAS:
- A pergunta DEVE SER OBJETIVA, DIRETA E CURTA (máx 15 palavras).
- A pergunta deve ser sobre o tema '{tema}' especificamente.
- A resposta deve ser verificável e factualmente correta.
- A DESCRIÇÃO DEVE COMEÇAR com a pergunta (sem o countdown final) — isso é crítico para SEO.
- Os termos de imagem devem ser em INGLÊS para busca no Pexels.
- Tom: animado, direto, engajante.
- Sem markdown fora do JSON.
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

    # Registrar como usada e atualizar tema do dia
    _marcar_usada(dados["pergunta_texto"], tracking)
    _salvar_tracking(tracking)
    
    hoje_str = datetime.now(timezone.utc).date().isoformat()
    if hoje_str not in temas_tracking:
        temas_tracking[hoje_str] = []
    temas_tracking[hoje_str].append(tema)
    _salvar_temas_tracking(temas_tracking)

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
