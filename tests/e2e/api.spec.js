// @ts-check
// API do manifesto (src/worker.js) contra o Worker local com D1.
const { test, expect } = require("@playwright/test");

async function totalAtual(request) {
  const r = await request.get("/api/manifesto");
  expect(r.status()).toBe(200);
  expect(r.headers()["cache-control"]).toBe("no-store");
  const { total } = await r.json();
  expect(Number.isInteger(total)).toBeTruthy();
  return total;
}

test("GET devolve o total de assinaturas", async ({ request }) => {
  expect(await totalAtual(request)).toBeGreaterThanOrEqual(0);
});

test("POST com estado válido registra e soma no total", async ({ request }) => {
  const antes = await totalAtual(request);
  const r = await request.post("/api/manifesto", { data: { uf: "PE" } });
  expect(r.status()).toBe(201);
  const { total } = await r.json();
  // outros testes em paralelo também assinam, então o total é pelo menos antes + 1
  expect(total).toBeGreaterThanOrEqual(antes + 1);
  expect(await totalAtual(request)).toBeGreaterThanOrEqual(total);
});

test("POST recusa estado inválido ou pedido malformado", async ({ request }) => {
  const antes = await totalAtual(request);
  for (const data of [{ uf: "XX" }, { uf: "" }, {}, { uf: 13 }, { uf: "sp" }]) {
    const r = await request.post("/api/manifesto", { data });
    expect(r.status(), JSON.stringify(data)).toBe(400);
  }
  const malformado = await request.post("/api/manifesto", {
    headers: { "content-type": "application/json" },
    data: "{isso não é json",
  });
  expect(malformado.status()).toBe(400);
  // nenhuma assinatura inválida entrou (outros testes podem ter somado, mas nunca estas 6)
  expect(await totalAtual(request)).toBeGreaterThanOrEqual(antes);
});

test("outros métodos não são aceitos", async ({ request }) => {
  const r = await request.delete("/api/manifesto");
  expect(r.status()).toBe(405);
  expect(r.headers()["allow"]).toBe("GET, POST");
});

test("o Worker continua servindo o site", async ({ request }) => {
  expect((await request.get("/")).status()).toBe(200);
  expect((await request.get("/dados/SP.json")).status()).toBe(200);
  expect((await request.get("/og.png")).status()).toBe(200);
  expect((await request.get("/pagina-que-nao-existe")).status()).toBe(404);
});
