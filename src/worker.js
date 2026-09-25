// Worker do Vota Nelas: serve o site estático (site/) e a API do manifesto.
//
// GET  /api/manifesto  -> { total }
// POST /api/manifesto  { uf } -> { total }
//
// Cada assinatura guarda só o estado e a data. Nada de nome, e-mail, telefone ou IP:
// o limitador de taxa usa o IP só para contar pedidos e não grava nada.

const UFS = new Set("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split(" "));

// dia da eleição (4/10/2026, 0h às 17h de Brasília): novas assinaturas pausadas, como na página
const INICIO_PAUSA = Date.UTC(2026, 9, 4, 3, 0);
const FIM_PAUSA = Date.UTC(2026, 9, 4, 20, 0);

function json(dados, status = 200) {
  return new Response(JSON.stringify(dados), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

async function total(env) {
  // o total fica numa linha própria: contar a tabela inteira a cada visita sairia caro no D1
  const linha = await env.DB.prepare("SELECT valor FROM totais WHERE chave = 'total'").first();
  return linha ? linha.valor : 0;
}

async function assinar(request, env) {
  const agora = Date.now();
  if (agora >= INICIO_PAUSA && agora < FIM_PAUSA) {
    return json({ erro: "dia_da_eleicao" }, 403);
  }

  const ip = request.headers.get("cf-connecting-ip") || "local";
  const { success } = await env.LIMITADOR.limit({ key: ip });
  if (!success) return json({ erro: "muitas_tentativas" }, 429);

  let uf;
  try {
    ({ uf } = await request.json());
  } catch {
    return json({ erro: "pedido_invalido" }, 400);
  }
  if (typeof uf !== "string" || !UFS.has(uf)) return json({ erro: "estado_invalido" }, 400);

  await env.DB.batch([
    env.DB.prepare("INSERT INTO assinaturas (uf, criado_em) VALUES (?, ?)").bind(uf, new Date(agora).toISOString()),
    env.DB.prepare("UPDATE totais SET valor = valor + 1 WHERE chave = 'total'"),
  ]);
  return json({ total: await total(env) }, 201);
}

async function manifesto(request, env) {
  if (request.method === "GET") return json({ total: await total(env) });
  if (request.method === "POST") return assinar(request, env);
  return new Response(null, { status: 405, headers: { allow: "GET, POST" } });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/manifesto") {
      try {
        return await manifesto(request, env);
      } catch (e) {
        console.error("erro na API do manifesto", e);
        return json({ erro: "erro_interno" }, 500);
      }
    }
    return env.ASSETS.fetch(request);
  },
};
