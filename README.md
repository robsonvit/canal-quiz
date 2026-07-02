# 🧠 Canal Quiz — Shorts Automáticos

Automação de YouTube Shorts no formato **"Modo Engenharia"** (Quiz Visual Rápido).

## Como Funciona

```
Ato 1: PERGUNTA (~5-8s)
  → Voz masculina faz uma pergunta curiosa
  → Imagem relacionada ao tema
  → Legendas amarelas na tela

Ato 2: COUNTDOWN (3s)
  → Números 3 → 2 → 1 animados
  → Overlay "Você sabe a resposta?"
  → Suspense máximo

Ato 3: RESPOSTA (~8-12s)
  → Imagem da resposta aparece
  → Voz revela a resposta + curiosidade extra
  → Legendas na tela
```

## Por que viraliza?

- **Retenção garantida**: quem não sabe a resposta pausa o vídeo ou comenta
- **Engajamento alto**: comentários e pauses sinalizam qualidade para o algoritmo
- **Formato viciante**: sequência pergunta→suspense→revelação prende o usuário

## Tecnologias

| Ferramenta | Uso |
|-----------|-----|
| **Groq** (`llama-3.3-70b`) | Gera perguntas + respostas curiosas |
| **edge-tts** (`pt-BR-AntonioNeural`) | Síntese de voz masculina TTS |
| **Groq Whisper** | Legendas SRT sincronizadas |
| **Pexels API** | Imagens relacionadas à pergunta e resposta |
| **FFmpeg** | Montagem do vídeo + countdown animado + legendas |
| **YouTube Data API v3** | Upload automático como Short |
| **GitHub Actions** | Execução automática 3x/dia |

## Configuração

### 1. Instalar dependências locais

```bash
pip install -r requirements.txt
```

### 2. Configurar `.env`

```env
GROQ_API_KEY=sua_chave_groq
PEXELS_API_KEY=sua_chave_pexels
YOUTUBE_CLIENT_ID=seu_client_id
YOUTUBE_CLIENT_SECRET=seu_client_secret
YOUTUBE_REFRESH_TOKEN=seu_refresh_token
```

> O `YOUTUBE_REFRESH_TOKEN` é o mesmo do CANAL ORAÇÃO (mesmo app Google).

### 3. Testar localmente

```bash
python scripts/pipeline.py
```

O vídeo gerado estará em `output/video_final.mp4`.

### 4. Configurar Secrets no GitHub

No repositório GitHub, vá em **Settings → Secrets → Actions** e adicione:

| Secret | Valor |
|--------|-------|
| `GROQ_API_KEY` | Chave do Groq (já configurada no `.env` local) |
| `PEXELS_API_KEY` | Sua chave do Pexels |
| `YOUTUBE_CLIENT_ID` | Do app Google existente |
| `YOUTUBE_CLIENT_SECRET` | Do app Google existente |
| `YOUTUBE_REFRESH_TOKEN` | Mesmo token do CANAL ORAÇÃO |

## Estrutura

```
CANAL QUIZ/
├── scripts/
│   ├── gerar_quiz.py       ← Gera perguntas via Groq AI
│   ├── gerar_audio.py      ← TTS + legendas SRT (2 partes)
│   ├── buscar_imagem.py    ← Imagens Pexels (pergunta + resposta)
│   ├── montar_video.py     ← Monta vídeo 3 atos com countdown
│   ├── upload_youtube.py   ← Publica no YouTube
│   └── pipeline.py         ← Orquestra tudo
├── data/
│   └── perguntas_usadas.json  ← Anti-repetição (30 dias)
├── .github/workflows/
│   └── main.yml            ← Roda 3x/dia automaticamente
└── requirements.txt
```

## Temas dos Quizzes

A IA varia entre os seguintes temas (com pesos para diversidade):

- 🐾 Comportamento animal (25%)
- 🧬 Biologia humana (20%)
- 🌿 Natureza curiosa (20%)
- ⚗️ Física do cotidiano (10%)
- 🏛️ Fatos históricos (10%)
- 🌌 Astronomia (8%)
- 🔬 Química curiosa (7%)
