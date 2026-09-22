# APRAS-75 — landing page copy (draft for operator approval)

Written by the orchestrator at the operator's request ("Preciso que crie essa
landing page, com a maioria das features do apras"). Every string below is
grounded in a feature that exists in the product today, taken from the
navigation registry (`frontend/src/features/user-administration/access/routeAccess.ts`)
and the pt-BR locale. Nothing here promises something the system does not do.

**This is a draft, not an approval.** Once the operator signs it off, these
strings replace the `LANDING_COPY_TODO` marker in `pt.json` and `en.json`.

Note on vocabulary, which the project has been bitten by before: the copy says
"administrador" for the person who manages the system, and reserves "síndico"
for the office of the condominium. They are not the same thing.

---

## Hero

**Título (h1)**
> A administração do seu condomínio, inteira, num lugar só.

**Subtítulo**
> Portaria, reservas, assembleias, financeiro e patrimônio — do registro da
> ocorrência à prestação de contas, sem planilha solta e sem grupo de WhatsApp
> fazendo as vezes de sistema.

**Botão principal**
> Entrar

---

## Blocos de capacidade (quatro)

### 1. Operações do dia a dia
> Tarefas com responsável e prazo, livro de ocorrências, controle de
> encomendas, patrimônio e estoque, e cotações de compra comparadas lado a
> lado antes de decidir.

### 2. Acessos e segurança
> Portaria com registro de entrada e saída, autorizações de visitantes e
> prestadores, controle de acesso por papel e um monitor em tempo real para
> quem está na guarita.

### 3. Comunidade e convivência
> Comunicados para todos os moradores, reserva de espaços comuns, assembleias
> com votação registrada e uma central de documentos onde a ata não se perde.

### 4. Gestão e transparência
> Financeiro, infrações e suas regras, permissões por papel e histórico de
> quem fez o quê — para o síndico prestar contas com a informação na mão.

---

## Rodapé

> APRAS — administração de condomínios e associações de proprietários.
> Já é morador ou administrador? **Entrar**

---

## Open question for the operator

The hero's second sentence takes a position: it names the problem as spreadsheets
and WhatsApp standing in for a system. That is the argument most likely to land
with a síndico, and also the one most likely to read as a jab if a prospect
recognises their own current setup. Say the word and I soften it to a neutral
"tudo o que hoje está espalhado em planilhas e mensagens".

Two features are deliberately NOT sold on the landing: **assinatura/planos** and
**multi-condomínio**. Both are real, but a public page that leads with billing
sells the price before the product, and the multi-tenant capability matters to
an administrator managing several condominiums — a different audience from the
one this page is for. Tell me if you want either promoted.
