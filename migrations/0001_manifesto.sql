-- Assinaturas do manifesto "Eu voto nelas": só o estado e a data, sem dados pessoais.
CREATE TABLE assinaturas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  uf TEXT NOT NULL,
  criado_em TEXT NOT NULL
);

-- Total guardado à parte, para a página não precisar contar a tabela inteira.
CREATE TABLE totais (
  chave TEXT PRIMARY KEY,
  valor INTEGER NOT NULL
);

INSERT INTO totais (chave, valor) VALUES ('total', 0);
