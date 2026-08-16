import os
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def get_font(size, bold=True, italic=True):
    # Try to find Arial Bold Italic
    font_paths = [
        "C:/Windows/Fonts/arialbi.ttf",  # Windows Arial Bold Italic
        "C:/Windows/Fonts/arialbd.ttf",  # Windows Arial Bold
        "C:/Windows/Fonts/arial.ttf",    # Windows Arial
        "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def draw_text_with_shadow(draw, x, y, text, font, fill="white", shadow_color="black", shadow_offset=(2,2)):
    draw.text((x+shadow_offset[0], y+shadow_offset[1]), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=fill)

def criar_tela_quiz(dados_quiz, output_dir="output", stage="normal"):
    # Dimensões da tela (Shorts)
    W, H = 1080, 1920
    
    # Carregar fundo estático fornecido pelo usuário
    fundo_path = os.path.join("FOTOS QUIZ", "FUNDO.png")
    if os.path.exists(fundo_path):
        img = Image.open(fundo_path).convert("RGBA")
        img = img.resize((W, H), Image.Resampling.LANCZOS)
    else:
        # Fallback caso o fundo não exista
        img = Image.new("RGBA", (W, H), "#0D2C99")
        
    draw = ImageDraw.Draw(img, "RGBA")
    
    # Logo do Show do Milhão (Se existir)
    logo_path = os.path.join("FOTOS QUIZ", "logo.png")
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail((600, 300), Image.Resampling.LANCZOS)
        logo_w, logo_h = logo.size
        img.paste(logo, ((W - logo_w) // 2, int(H * 0.05)), logo)
        
    # Se for stage="fundo", para por aqui.
    if stage == "fundo":
        out_path = os.path.join(output_dir, "frame_fundo.png")
        img.convert("RGB").save(out_path, "PNG")
        return out_path
    
    # Textos
    pergunta = dados_quiz.get("pergunta", "").upper()
    alternativas = [str(a).upper() for a in dados_quiz.get("alternativas", [])]
    correta_idx = int(dados_quiz.get("letra_correta", 1)) - 1  # 0 a 3
    # --- CAIXA DA PERGUNTA ---
    y_pergunta_box = int(H * 0.22)
    
    # Quebrar texto da pergunta
    font_pergunta = get_font(55)
    wrapper = textwrap.TextWrapper(width=26)
    linhas_pergunta = wrapper.wrap(pergunta)
    
    total_text_h = sum([draw.textbbox((0,0), linha, font=font_pergunta)[3] for linha in linhas_pergunta]) + (len(linhas_pergunta)-1)*10
    
    # Altura da caixa dinâmica baseada no texto
    h_pergunta_box = max(int(H * 0.20), total_text_h + 80)
    
    # Desenhar caixa vermelha da pergunta com bordas brancas
    draw.rectangle([(0, y_pergunta_box), (W, y_pergunta_box + h_pergunta_box)], fill="#A31010")
    draw.line([(0, y_pergunta_box), (W, y_pergunta_box)], fill="white", width=4)
    draw.line([(0, y_pergunta_box + h_pergunta_box), (W, y_pergunta_box + h_pergunta_box)], fill="white", width=4)
    
    start_y_texto = y_pergunta_box + (h_pergunta_box - total_text_h) // 2
    
    for i, linha in enumerate(linhas_pergunta):
        bbox = draw.textbbox((0,0), linha, font=font_pergunta)
        linha_w = bbox[2] - bbox[0]
        linha_h = bbox[3] - bbox[1]
        x_linha = (W - linha_w) // 2
        draw_text_with_shadow(draw, x_linha, start_y_texto, linha, font_pergunta, shadow_offset=(3,3))
        start_y_texto += linha_h + 10
        
    if stage == "pergunta":
        out_path = os.path.join(output_dir, "frame_pergunta.png")
        img.convert("RGB").save(out_path, "PNG")
        return out_path
        
    # --- CAIXAS DE ALTERNATIVAS ---
    y_alternativas_start = y_pergunta_box + h_pergunta_box + 80
    alt_height = 130
    alt_margin_y = 40
    alt_margin_x = 80
    
    font_alt = get_font(48)
    font_num = get_font(55)
    
    max_opts = 4
    if stage.startswith("opt"):
        max_opts = int(stage.replace("opt", ""))
    
    for i in range(min(max_opts, len(alternativas))):
        alt_text = alternativas[i]
        x0 = alt_margin_x
        y0 = y_alternativas_start + i * (alt_height + alt_margin_y)
        x1 = W - alt_margin_x
        y1 = y0 + alt_height
        
        is_correct = (i == correta_idx)
        bg_color = "#10A320" if (stage == "revelacao" and is_correct) else "#8B1515"
        
        draw.rounded_rectangle([(x0, y0), (x1, y1)], radius=20, fill=bg_color, outline="white", width=4)
        
        circle_radius = 45
        cx0 = x0 + 20
        cy0 = y0 + (alt_height - circle_radius*2) // 2
        cx1 = cx0 + circle_radius*2
        cy1 = cy0 + circle_radius*2
        draw.ellipse([(cx0, cy0), (cx1, cy1)], fill="white")
        
        numero_texto = str(i + 1)
        num_bbox = draw.textbbox((0,0), numero_texto, font=font_num)
        num_w = num_bbox[2] - num_bbox[0]
        num_h = num_bbox[3] - num_bbox[1]
        nx = cx0 + (circle_radius*2 - num_w) // 2
        ny = cy0 + (circle_radius*2 - num_h) // 2 - 10
        draw.text((nx, ny), numero_texto, font=font_num, fill="#22359C")
        
        alt_clean = alt_text
        if len(alt_clean) > 3 and alt_clean[1] == ')' or alt_clean[2] == ')':
            alt_clean = alt_clean.split(')', 1)[1].strip()
        elif len(alt_clean) > 3 and alt_clean[1] == '.' or alt_clean[2] == '.':
            alt_clean = alt_clean.split('.', 1)[1].strip()
            
        tx = cx1 + 30
        font_size = getattr(font_alt, "size", 48)
        ty = y0 + (alt_height - font_size) // 2 - 5
        draw_text_with_shadow(draw, tx, ty, alt_clean, font_alt, shadow_offset=(2,2))

    os.makedirs(output_dir, exist_ok=True)
    out_name = f"frame_{stage}.png"
    out_path = os.path.join(output_dir, out_name)
    img.convert("RGB").save(out_path, "PNG")
    return out_path

def gerar_todas_imagens(dados_quiz, output_dir="output"):
    caminhos = {}
    for stg in ["fundo", "pergunta", "opt1", "opt2", "opt3", "normal", "revelacao"]:
        caminhos[stg] = criar_tela_quiz(dados_quiz, output_dir, stage=stg)
    return caminhos

if __name__ == "__main__":
    import json
    with open("output/quiz.json", encoding="utf-8") as f:
        dados = json.load(f)
    print("Gerando frames...")
    gerar_todas_imagens(dados, "output")
    print("Frames gerados com sucesso!")
