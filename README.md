# Vota Nelas

Site suprapartidário para aumentar o número de mulheres eleitas nas eleições de 4 de outubro de 2026.

Responsável: Thais Freitas (thaisfreitas31@gmail.com)

## O que o site faz

- **Monte sua urna com elas:** a pessoa escolhe o estado no mapa e uma mulher para cada cargo, na ordem da urna (deputada federal, estadual/distrital, 2 votos para o Senado, governadora e presidenta). No fim, recebe uma colinha para enviar pelo WhatsApp.
- **Voto em dobro:** explica a regra da EC 111/2021 (votos em deputadas federais contam em dobro na divisão dos fundos partidário e eleitoral).
- **Manifesto "Eu voto nelas":** contador de assinaturas, sem pesquisa de voto e sem dados pessoais (só o estado).

## Estrutura

```
site/index.html   página completa (HTML, CSS e JS num arquivo só)
```

## Antes de ir para produção

- [ ] Trocar as candidatas de exemplo pelos dados oficiais do TSE (`consulta_cand_2026.zip`, Dados Abertos do TSE)
- [ ] Remover o aviso "Protótipo" do topo
- [ ] Trocar `SITE_URL` no script pelo domínio final
- [ ] Trocar o contador do manifesto (hoje usa o banco do protótipo no claude.ai) por Cloudflare Pages Functions + D1
- [ ] Testar em iPhone (Safari) e Android (Chrome)
- [ ] Revisão rápida com advogado(a) eleitoral

## Publicar no Cloudflare Pages

1. Registrar o domínio no Registro.br, no CPF da responsável.
2. Criar conta no Cloudflare (plano Free) e adicionar o domínio; colocar os servidores DNS do Cloudflare no painel do Registro.br.
3. Workers & Pages → Create → Pages → conectar este repositório (ou "Upload assets").
   - Build command: *(vazio)*
   - Build output directory: `site`
4. Em **Custom domains**, adicionar o domínio.

## Regras eleitorais seguidas

- Site de pessoa física (Lei 9.504, art. 57-C §1), com responsável identificada (art. 57-D).
- Sem impulsionamento pago, sem disparo em massa, sem enquetes.
- Todas as candidatas aptas, em ordem sorteada e no mesmo formato.
- No dia da eleição (4/10, 0h–17h de Brasília), envio pelo WhatsApp e novas assinaturas ficam pausados.

## Créditos

- Mapa do Brasil: [SVG Maps](https://github.com/VictorCazanave/svg-maps), de Victor Cazanave — licença CC BY 4.0.
- Dados: Tribunal Superior Eleitoral, Câmara dos Deputados, Senado Federal.
