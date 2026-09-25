#!/usr/bin/env python3
"""Gera as artes de divulgação do Vota Nelas em docs/marketing/artes/png/.

Uso:
    python3 docs/marketing/artes/gerar.py          # todas
    python3 docs/marketing/artes/gerar.py story    # só as que têm "story" no nome

Cada arte é uma página HTML (cores e fontes do site) que o Chromium do
Playwright transforma em PNG (precisa de `npm install` na raiz do projeto). Formatos: feed do Instagram 1080x1350, stories e status
do WhatsApp 1080x1920, X 1600x900.
"""
import os
import subprocess
import sys
import tempfile

PASTA = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(PASTA, "png")
RAIZ = os.path.abspath(os.path.join(PASTA, "..", "..", ".."))

FONTES = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800'
          '&family=Figtree:wght@500;600;700&family=Share+Tech+Mono&display=swap">')

CSS = """
:root{--bg:#FBF7FA;--soft:#F4EAF2;--ink:#2B1330;--muted:#6E5A70;--vinho:#A3123F;--roxo:#5B2A86;--men:#CDBFCB;
  --display:"Bricolage Grotesque",sans-serif;--body:"Figtree",sans-serif;--mono:"Share Tech Mono",monospace}
.escuro{--bg:#1A0F1C;--soft:#2E1C31;--ink:#F6ECF4;--muted:#BFA9BE;--vinho:#F0527F;--roxo:#C39BEA;--men:#56435A}
*{box-sizing:border-box;margin:0}
html,body{width:var(--w);height:var(--h);overflow:hidden}
body{background:var(--bg);color:var(--ink);font-family:var(--body);display:flex;flex-direction:column;padding:var(--pad)}
.logo{display:flex;align-items:center;gap:.4em;font-family:var(--display);font-weight:800;font-size:var(--logo)}
.logo i{width:1.3em;height:1.3em;border-radius:50%;background:var(--vinho);color:var(--bg);display:grid;place-items:center;font-style:normal;font-size:.8em}
.logo em{font-style:normal;color:var(--vinho)}
.meio{flex:1;display:flex;flex-direction:column;justify-content:center}
h1{font-family:var(--display);font-weight:800;letter-spacing:-.02em;line-height:1.02}
.v{color:var(--vinho)}
.r{color:var(--roxo)}
.m{color:var(--muted)}
p{line-height:1.3}
.num{font-family:var(--display);font-weight:800;letter-spacing:-.04em;line-height:.9}
.rodape{display:flex;justify-content:space-between;align-items:flex-end;gap:1em;font-size:var(--rod);color:var(--muted);font-weight:600}
.url{font-family:var(--display);font-weight:800;color:var(--vinho);font-size:1.5em}
.cta{display:inline-block;background:var(--vinho);color:var(--bg);font-family:var(--display);font-weight:800;border-radius:999px;padding:.45em 1.1em}
.dots{display:grid;grid-template-columns:repeat(10,1fr);gap:var(--gap)}
.dots b{aspect-ratio:1;border-radius:50%;background:var(--men)}
.dots b.w{background:var(--vinho)}
.colinha{background:#1E2A24;border-radius:28px;padding:28px 32px;color:#D9E6C7;font-family:var(--body)}
.colinha .tela{background:#D9E6C7;color:#1B2A17;border-radius:14px;padding:18px 22px}
.colinha .l{display:flex;justify-content:space-between;align-items:center;padding:9px 0;font-weight:700;font-size:26px}
.colinha .d{display:flex;gap:6px}
.colinha .d i{width:30px;height:42px;border:2px solid #1B2A17;border-radius:4px;display:grid;place-items:center;font-style:normal;font-family:var(--mono);font-size:28px}
.passo{display:flex;gap:28px;align-items:flex-start}
.passo .n{flex:none;width:92px;height:92px;border-radius:50%;background:var(--vinho);color:var(--bg);display:grid;place-items:center;font-family:var(--display);font-weight:800;font-size:52px}
"""

FEED = dict(w=1080, h=1350, pad="84px", logo="44px", rod="26px", gap="12px")
STORY = dict(w=1080, h=1920, pad="250px 90px 250px", logo="50px", rod="28px", gap="14px")
X = dict(w=1600, h=900, pad="70px 90px", logo="40px", rod="26px", gap="10px")

LOGO = '<div class="logo"><i>✓</i>Vota <em>Nelas</em></div>'
RODAPE = ('<div class="rodape"><span>Iniciativa pessoal e suprapartidária</span>'
          '<span class="url">votanelas.com.br</span></div>')
# nos stories o endereço já está no botão: o rodapé fica só com a identificação
RODAPE_STORY = '<div class="rodape" style="justify-content:center"><span>Iniciativa pessoal e suprapartidária</span></div>'
CTA_STORY = '<div style="text-align:center;margin-bottom:36px"><span class="cta" style="font-size:52px">votanelas.com.br</span></div>'


def dots(n=17):
    return '<div class="dots">' + "".join(f'<b class="{"w" if i < n else ""}"></b>' for i in range(100)) + "</div>"


def colinha(linhas):
    corpo = "".join(
        f'<div class="l"><span>{cargo}</span><span class="d">{"".join("<i></i>" for _ in range(dig))}</span></div>'
        for cargo, dig in linhas)
    return f'<div class="colinha"><div style="font-weight:700;font-size:22px;margin-bottom:14px;letter-spacing:.08em">MINHA COLINHA</div><div class="tela">{corpo}</div></div>'


CONHECA = [
    ("Como votou na Câmara", "Para quem já foi deputada: PEC 6x1, igualdade salarial, misoginia, agrotóxicos e licenciamento ambiental."),
    ("Perfil, bens e contas", "Link oficial do TSE com bens declarados, certidões criminais e quem financia a campanha."),
    ("Como pesquisar", "Um guia com os caminhos oficiais para conhecer qualquer candidata."),
]


def lista_conheca(tam_titulo, tam_texto, gap):
    return f'<div style="display:grid;gap:{gap}px">' + "".join(
        f'<div class="passo"><div class="n" style="font-size:44px">✓</div><div><h1 style="font-size:{tam_titulo}px">{t}</h1>'
        f'<p class="m" style="font-size:{tam_texto}px;margin-top:8px">{d}</p></div></div>' for t, d in CONHECA) + "</div>"


LINHAS_URNA = [("Deputada federal", 4), ("Deputada estadual", 5), ("Senadora 1", 3), ("Senadora 2", 3),
               ("Governadora", 2), ("Presidenta", 2)]

ARTES = {
    # ---------- feed do Instagram (1080x1350) ----------
    "feed_01_52-e-17": (FEED, "", f"""{LOGO}
      <div class="meio">
        <div class="num v" style="font-size:230px">52,8%</div>
        <p style="font-size:44px;font-weight:700;margin:6px 0 40px">do eleitorado é de mulheres.</p>
        <div class="num r" style="font-size:230px">17,2%</div>
        <p style="font-size:44px;font-weight:700;margin-top:6px">da Câmara dos Deputados.</p>
        <p class="m" style="font-size:34px;margin-top:44px">A conta não fecha. Em 4 de outubro, dá para mudar isso.</p>
        <p class="m" style="font-size:22px;margin-top:24px">Fontes: TSE e Câmara dos Deputados, setembro de 2026.</p>
      </div>{RODAPE}"""),

    "feed_02_carrossel-1": (FEED, "", f"""{LOGO}
      <div class="meio">
        <h1 style="font-size:104px">Na urna você digita <span class="v">6 números.</span></h1>
        <h1 style="font-size:104px;margin-top:30px">E se quase todos forem de <span class="v">mulheres?</span></h1>
        <p class="m" style="font-size:36px;margin-top:50px">Arraste para ver como montar sua urna em 3 minutos →</p>
      </div>{RODAPE}"""),

    "feed_02_carrossel-2": (FEED, "", f"""{LOGO}
      <div class="meio" style="gap:58px">
        <div class="passo"><div class="n">1</div><div><h1 style="font-size:64px">Escolha seu estado</h1><p class="m" style="font-size:32px;margin-top:10px">No mapa ou na lista.</p></div></div>
        <div class="passo"><div class="n">2</div><div><h1 style="font-size:64px">Uma mulher em cada cargo que quiser</h1><p class="m" style="font-size:32px;margin-top:10px">Na ordem da urna. Onde não houver uma candidata que te represente, é só pular.</p></div></div>
        <div class="passo"><div class="n">3</div><div><h1 style="font-size:64px">Receba sua colinha</h1><p class="m" style="font-size:32px;margin-top:10px">Com os números, pronta para enviar a 3 amigas.</p></div></div>
      </div>{RODAPE}"""),

    "feed_02_carrossel-3": (FEED, "", f"""{LOGO}
      <div class="meio">
        <h1 style="font-size:78px;margin-bottom:50px">Conheça cada candidata <span class="v">antes de escolher.</span></h1>
        {lista_conheca(50, 30, 40)}
      </div>{RODAPE}"""),

    "feed_02_carrossel-4": (FEED, "", f"""{LOGO}
      <div class="meio">
        <h1 style="font-size:72px;margin-bottom:40px">Todas as candidatas aptas, de <span class="v">todos os partidos.</span></h1>
        <p style="font-size:36px;font-weight:600">Dados oficiais do TSE, em ordem sorteada a cada visita e no mesmo formato.</p>
        <p class="m" style="font-size:32px;margin-top:30px">Sem recomendar ninguém: quem escolhe é você.</p>
        <div style="margin-top:60px"><span class="cta" style="font-size:44px">votanelas.com.br</span></div>
      </div>{RODAPE}"""),

    "feed_03_voto-em-dobro": (FEED, "escuro", f"""{LOGO}
      <div class="meio">
        <div class="num v" style="font-size:340px">2×</div>
        <h1 style="font-size:70px;margin-top:10px">Votos em deputadas federais contam em dobro</h1>
        <p style="font-size:38px;font-weight:600;margin-top:24px">na divisão do Fundo Partidário e do Fundo Eleitoral.</p>
        <p class="m" style="font-size:28px;margin-top:40px">EC 111/2021. Muda só a divisão do dinheiro dos partidos: para eleger, cada voto continua contando uma vez.</p>
      </div>{RODAPE}"""),

    "feed_04_colinha": (FEED, "", f"""{LOGO}
      <div class="meio">
        <h1 style="font-size:84px">O celular não entra na cabine.</h1>
        <h1 class="v" style="font-size:84px;margin:10px 0 50px">A colinha em papel pode.</h1>
        {colinha(LINHAS_URNA)}
        <p class="m" style="font-size:30px;margin-top:34px">Monte a sua, anote ou imprima e leve no dia 4.</p>
      </div>{RODAPE}"""),

    "feed_05_conheca-a-candidata": (FEED, "escuro", f"""{LOGO}
      <div class="meio">
        <p class="v" style="font-size:32px;font-weight:700;letter-spacing:.12em">ANTES DE VOTAR</p>
        <h1 style="font-size:92px;margin:16px 0 50px">Conheça a candidata.</h1>
        {lista_conheca(50, 30, 40)}
        <p class="m" style="font-size:28px;margin-top:44px">Dados oficiais do TSE e da Câmara. O site não recomenda ninguém: quem escolhe é você.</p>
      </div>{RODAPE}"""),

    # ---------- stories do Instagram e status do WhatsApp (1080x1920) ----------
    "story_01_convite": (STORY, "", f"""{LOGO}
      <div class="meio">
        <h1 style="font-size:104px">Monte sua urna <span class="v">com mais mulheres.</span></h1>
        <p style="font-size:44px;font-weight:600;margin:40px 0 50px">6 números. 3 minutos. Uma colinha para levar no dia 4.</p>
        <div style="width:560px">{dots()}</div>
        <p class="m" style="font-size:34px;margin-top:26px">Se a Câmara tivesse 100 cadeiras, só 17 seriam de mulheres.</p>
      </div>
      {CTA_STORY}
      {RODAPE_STORY}"""),

    "story_02_manifesto": (STORY, "escuro", f"""{LOGO}
      <div class="meio">
        <p class="v" style="font-size:40px;font-weight:700;letter-spacing:.12em">MANIFESTO</p>
        <h1 style="font-size:170px;margin:20px 0 50px">Eu voto nelas.</h1>
        <p style="font-size:48px;font-weight:600">Assine o manifesto por mais mulheres na política.</p>
        <p class="m" style="font-size:38px;margin-top:40px">Não é pesquisa: não perguntamos em quem você vota e não guardamos nome, e-mail ou telefone. Só o seu estado.</p>
      </div>
      {CTA_STORY}
      {RODAPE_STORY}"""),

    "story_03_voto-em-dobro": (STORY, "", f"""{LOGO}
      <div class="meio">
        <p class="v" style="font-size:40px;font-weight:700;letter-spacing:.12em">VOCÊ SABIA?</p>
        <div class="num v" style="font-size:420px;margin:10px 0">2×</div>
        <h1 style="font-size:92px">Voto em deputada federal conta em dobro</h1>
        <p style="font-size:46px;font-weight:600;margin-top:34px">na divisão do dinheiro dos partidos (EC 111/2021).</p>
      </div>
      {CTA_STORY}
      {RODAPE_STORY}"""),

    "story_04_conheca-a-candidata": (STORY, "escuro", f"""{LOGO}
      <div class="meio">
        <p class="v" style="font-size:40px;font-weight:700;letter-spacing:.12em">ANTES DE VOTAR</p>
        <h1 style="font-size:120px;margin:20px 0 60px">Conheça a candidata.</h1>
        {lista_conheca(58, 36, 48)}
      </div>
      {CTA_STORY}
      {RODAPE_STORY}"""),

    # ---------- X (1600x900) ----------
    "x_01_52-e-17": (X, "", f"""{LOGO}
      <div class="meio" style="flex-direction:row;align-items:center;gap:80px">
        <div><div class="num v" style="font-size:200px">52,8%</div><p style="font-size:40px;font-weight:700">do eleitorado</p></div>
        <div><div class="num r" style="font-size:200px">17,2%</div><p style="font-size:40px;font-weight:700">da Câmara</p></div>
        <p class="m" style="font-size:38px;max-width:420px">Monte sua urna com mais mulheres em 3 minutos.</p>
      </div>{RODAPE}"""),

    "x_02_como-funciona": (X, "escuro", f"""{LOGO}
      <div class="meio">
        <h1 style="font-size:100px">Na urna, 6 números.<br><span class="v">A maioria de mulheres.</span></h1>
        <p style="font-size:40px;font-weight:600;margin-top:34px">Escolha seu estado, uma mulher nos cargos que quiser e receba sua colinha.</p>
      </div>{RODAPE}"""),

    "x_03_conheca-a-candidata": (X, "", f"""{LOGO}
      <div class="meio" style="flex-direction:row;align-items:center;gap:70px">
        <h1 style="font-size:96px;flex:0 0 560px">Conheça a candidata <span class="v">antes de votar.</span></h1>
        {lista_conheca(44, 26, 26)}
      </div>{RODAPE}"""),
}

# contagem regressiva para os stories: 26/9 (faltam 8 dias) até 3/10 (amanhã)
for faltam in range(8, 0, -1):
    titulo = "Amanhã é dia de votar." if faltam == 1 else f'Faltam <span class="v">{faltam} dias</span>.'
    if faltam == 1:
        apoio = "Sua colinha está pronta? Anote os números ou tire um print hoje."
    elif faltam % 2:
        apoio = "Antes de escolher, conheça a candidata: votos na Câmara, bens e contas."
    else:
        apoio = "Já montou sua urna com mais mulheres?"
    ARTES[f"story_contagem_{faltam:02d}"] = (STORY, "escuro" if faltam == 1 else "", f"""{LOGO}
      <div class="meio">
        <p class="m" style="font-size:44px;font-weight:700">Eleições · 4 de outubro</p>
        <h1 style="font-size:{150 if faltam == 1 else 190}px;margin:30px 0 60px">{titulo}</h1>
        <p style="font-size:52px;font-weight:600">{apoio}</p>
      </div>
      {CTA_STORY}
      {RODAPE_STORY}""")


def pagina(fmt, classe, corpo):
    vars_ = ";".join(f"--{k}:{v}{'px' if k in ('w', 'h') else ''}" for k, v in fmt.items())
    return (f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">{FONTES}<style>{CSS}</style></head>'
            f'<body class="{classe}" style="{vars_}">{corpo}</body></html>')


def main():
    os.makedirs(SAIDA, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        filtro = sys.argv[1] if len(sys.argv) > 1 else ""
        for nome, (fmt, classe, corpo) in ARTES.items():
            if filtro not in nome:
                continue
            html = os.path.join(tmp, f"{nome}.html")
            with open(html, "w", encoding="utf-8") as f:
                f.write(pagina(fmt, classe, corpo))
            png = os.path.join(SAIDA, f"{nome}.png")
            # renderiza com o Chromium do Playwright (já instalado para os testes)
            for tentativa in range(1, 4):
                try:
                    subprocess.run(["npx", "playwright", "screenshot", "--browser=chromium",
                                    f"--viewport-size={fmt['w']},{fmt['h']}", "--wait-for-timeout=1500",
                                    f"file://{html}", png],
                                   cwd=RAIZ, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
                    break
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                    print(f"  {nome}: falhou (tentativa {tentativa}), tentando de novo")
            else:
                sys.exit(f"não foi possível gerar {nome}")
            print("gerada:", os.path.relpath(png, os.path.dirname(os.path.dirname(PASTA))))


if __name__ == "__main__":
    main()
