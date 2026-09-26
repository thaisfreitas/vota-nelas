# Vota Nelas

Site suprapartidário para aumentar o número de mulheres eleitas nas eleições de 4 de outubro de 2026.

Mulheres são 52,8% do eleitorado e 17,2% da Câmara dos Deputados (TSE e Câmara, setembro de 2026). O Vota Nelas ajuda cada eleitora e eleitor a montar uma urna com mais mulheres, com os nomes e números oficiais do TSE, e a compartilhar essa escolha com as amigas.

Responsável: Thais Freitas (thaisfreitas31@gmail.com)

## O que o site faz

- **Monte sua urna com elas:** a pessoa escolhe o estado no mapa e uma mulher em cada cargo que quiser, na ordem da urna (e pode pular os outros): deputada federal, deputada estadual ou distrital, dois votos para o Senado, governadora e presidenta. No fim, recebe uma colinha com os números para levar à votação e enviar pelo WhatsApp.
- **A favor delas:** o site é suprapartidário, mas não é neutro sobre direitos. Um mapa de calor mostra quanto cada partido votou a favor das mulheres e da sociedade em 5 votações nominais da Câmara (fim da escala 6x1, igualdade salarial, urgência da criminalização da misoginia, PL do Veneno e PL da Devastação), do mais a favor ao mais contra. O card de quem já foi deputada mostra em quantas dessas votações ela votou a favor.
- **Voto em dobro:** explica a regra da EC 111/2021. Votos em deputadas federais contam em dobro na divisão dos fundos partidário e eleitoral.
- **Placar:** mostra a presença de mulheres na Câmara, no Senado, nas candidaturas de 2026 e no eleitorado.
- **Manifesto "Eu voto nelas":** contador de assinaturas. Não é pesquisa de voto e não guarda dados pessoais, só o estado.

## Como funciona

O site é uma página em HTML, CSS e JavaScript, sem build e sem framework, servida por um Worker do Cloudflare. O mesmo Worker tem a API do manifesto (`/api/manifesto`), que guarda as assinaturas num banco D1: só o estado e a data de cada uma. Um limite de 5 assinaturas por minuto por aparelho evita que alguém infle o contador, sem gravar o IP.

As candidatas vêm dos [dados abertos do TSE](https://dadosabertos.tse.jus.br/dataset/candidatos-2026). Um script em Python converte os arquivos do TSE em um JSON pequeno por estado, que a página carrega quando a pessoa escolhe onde vota.

Entram só mulheres com candidatura apta, ou seja, com o nome na urna e sem renúncia ou indeferimento definitivo. Candidaturas que ainda aguardam julgamento ou recurso também entram, porque os votos nelas são contados. Vices e suplentes ficam de fora.

As candidatas aparecem todas no mesmo formato, **em ordem de votação a favor das causas das mulheres**: primeiro as que mais votaram a favor nas 5 votações da Câmara. Quem não tem votos nessas votações entra pela porcentagem da bancada do seu partido; partidos sem deputados nessas votações ficam por último. Só os empates aparecem em ordem sorteada a cada visita. Cada uma tem um link para a sua página no DivulgaCandContas, do TSE.

## Estrutura

```
site/                      o que vai para o ar
  index.html               página completa (HTML, CSS e JS num arquivo só)
  dados/{UF}.json          candidatas de cada estado (gerado pelo script)
  dados/BR.json            candidatas a presidenta (gerado pelo script)
  fotos/{SQ}.jpg           fotos oficiais das candidatas, reduzidas (gerado pelo script)
  og.png, favicon.svg      imagem de compartilhamento e ícone
scripts/
  tse_para_json.py         converte os arquivos do TSE em site/dados/
  tse_fotos.py             extrai e reduz as fotos oficiais para site/fotos/
  votacoes_deputadas.py    votos na Câmara das candidatas que já foram deputadas e das bancadas de cada partido
  og.html, gerar_og.sh     fonte da og.png e script que gera a imagem
src/worker.js              Worker: serve site/ e a API do manifesto
migrations/                tabelas do manifesto no D1
tests/                     testes dos dados, do conversor, da API e do site (Playwright)
dados-tse/                 arquivos baixados do TSE (fora do git)
wrangler.jsonc             configuração do Worker, do D1 e do limitador no Cloudflare
```

## Rodar localmente

```bash
npm install
npm run dev
```

Depois, abra <http://localhost:4173>. O comando sobe o Worker com um banco D1 local (em `.wrangler/teste`, fora do git), então o manifesto funciona de verdade sem tocar nas assinaturas reais.

## Atualizar as candidatas

A situação das candidaturas muda até a véspera da eleição, então vale repetir estes passos algumas vezes.

1. Em <https://dadosabertos.tse.jus.br/dataset/candidatos-2026>, baixe pelo navegador dois arquivos (o servidor do TSE bloqueia download por linha de comando):
   - **Candidatos** → `consulta_cand_2026.zip`
   - **Candidatos - complementar** → `consulta_cand_complementar_2026.zip`. Desde 2024, é este arquivo que traz a situação da candidatura.
2. Coloque os dois na pasta `dados-tse/`.
3. Rode:

   ```bash
   python3 scripts/tse_para_json.py dados-tse/consulta_cand_2026.zip --complementar dados-tse/consulta_cand_complementar_2026.zip
   ```

   O script mostra quantas candidatas encontrou por estado, avisa quando um cargo não tem mulheres e alerta se o TSE usar uma situação de candidatura que ele não conhece.
4. Para as fotos oficiais, baixe também os itens **"XX - Fotos de candidatos"** (27 estados e BR) para `dados-tse/fotos/` e rode:

   ```bash
   python3 scripts/tse_fotos.py dados-tse/fotos
   ```

   O script pega só as fotos das candidatas do site, reduz cada uma (sem cortar nem retocar) para `site/fotos/`, marca em `site/dados/` quem tem foto e mostra quantas candidatas de cada cargo têm foto. Usa o `sips`, que vem no macOS.
5. Para os votos na Câmara (card das candidatas e mapa de calor dos partidos), rode:

   ```bash
   python3 scripts/votacoes_deputadas.py dados-tse/consulta_cand_2026.zip --complementar dados-tse/consulta_cand_complementar_2026.zip
   ```

   O sentido "a favor das mulheres" de cada votação fica em `FAVORAVEL`, no começo do script. A conta dos partidos usa o partido de cada parlamentar no dia da votação (partidos que se fundiram entram na sigla de hoje, em `SUCESSOR`), conta obstrução como voto contra o projeto e deixa ausências e abstenções de fora. A tabela para conferência fica em `docs/votacoes-deputadas/partidos.md`.
6. Faça o commit de `site/dados/` e `site/fotos/` e publique.

Para conferir os números sem o arquivo complementar, use `--sem-situacao --saida /tmp/previa`. Esse resultado inclui candidaturas inaptas e não deve ser publicado.

## Testes

```bash
python3 -m unittest discover -s tests -v   # dados publicados e conversor do TSE
npm install && npx playwright test         # site e API no navegador, no desktop e no celular
```

Os testes rodam no GitHub Actions a cada push. A publicação é manual, pelo workflow **Deploy** (Actions → Deploy → Run workflow), e só acontece se todos os testes passarem. Antes de publicar, o deploy aplica no D1 as migrações novas de `migrations/`.

## Imagem de compartilhamento

A `site/og.png` é a imagem que aparece quando o link é enviado no WhatsApp. Para mudá-la, edite `scripts/og.html` e rode `sh scripts/gerar_og.sh` (precisa do Google Chrome instalado).

## Regras eleitorais seguidas

- Site de pessoa física (Lei 9.504, art. 57-C §1), com responsável identificada (art. 57-D).
- Sem impulsionamento pago, sem disparo em massa, sem enquetes.
- Todas as candidatas aptas, no mesmo formato, em ordem de votação a favor das causas das mulheres na Câmara (os votos dela ou, se não tiver, os da bancada do partido; empates em ordem sorteada).
- No dia da eleição (4/10, 0h–17h de Brasília), o envio pelo WhatsApp e novas assinaturas ficam pausados.

## Créditos

- Mapa do Brasil: [SVG Maps](https://github.com/VictorCazanave/svg-maps), de Victor Cazanave, licença CC BY 4.0.
- Dados: Tribunal Superior Eleitoral, Câmara dos Deputados, Senado Federal.
