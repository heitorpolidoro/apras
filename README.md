# APRAS — Aplicativo de Planejamento e Resoluções para Associações e Síndicos

<div>
<!-- GitHub CI & Sponsors -->
<a href="https://github.com/heitorpolidoro/apras/actions/workflows/ci.yml"><img src="https://github.com/heitorpolidoro/apras/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
<a href="https://github.com/sponsors/heitorpolidoro"><img src="https://img.shields.io/github/sponsors/heitorpolidoro?color=ea4aaa" alt="GitHub Sponsors"></a>
<br>

<!-- GitHub Stats -->

<a href="https://github.com/heitorpolidoro/apras/releases/latest"><img src="https://img.shields.io/github/v/release/heitorpolidoro/apras?label=Latest%20Version" alt="Latest Version"></a>
<img src="https://img.shields.io/github/release-date/heitorpolidoro/apras" alt="GitHub Release Date">
<img src="https://img.shields.io/github/commits-since/heitorpolidoro/apras/latest" alt="GitHub commits since latest release">
<img src="https://img.shields.io/github/last-commit/heitorpolidoro/apras" alt="GitHub last commit">
<br>

<!-- GitHub Activity -->

<a href="https://github.com/heitorpolidoro/apras/issues"><img src="https://img.shields.io/github/issues/heitorpolidoro/apras" alt="GitHub issues"></a>
<a href="https://github.com/heitorpolidoro/apras/pulls"><img src="https://img.shields.io/github/issues-pr/heitorpolidoro/apras" alt="GitHub pull requests"></a>
<br>

<!-- DeepSource -->

<a href="https://app.deepsource.com/gh/heitorpolidoro/apras/" target="_blank"><img alt="DeepSource" title="DeepSource" src="https://app.deepsource.com/gh/heitorpolidoro/apras.svg/?label=active+issues&show_trend=true"/></a>
<a href="https://app.deepsource.io/gh/heitorpolidoro/apras/"><img src="https://app.deepsource.com/gh/heitorpolidoro/apras.svg/?label=coverage" alt="DeepSource Coverage"></a>
<br>

<!-- SonarCloud -->

<a href="https://sonarcloud.io/summary/new_code?id=heitorpolidoro_apras"><img src="https://sonarcloud.io/api/project_badges/measure?project=heitorpolidoro_apras&metric=alert_status" alt="SonarCloud Quality Gate"></a>
<a href="https://sonarcloud.io/summary/new_code?id=heitorpolidoro_apras"><img src="https://sonarcloud.io/api/project_badges/measure?project=heitorpolidoro_apras&metric=coverage" alt="SonarCloud Coverage"></a>
<a href="https://sonarcloud.io/summary/new_code?id=heitorpolidoro_apras"><img src="https://sonarcloud.io/api/project_badges/measure?project=heitorpolidoro_apras&metric=security_rating" alt="SonarCloud Security Rating"></a>
<br>
<a href="https://sonarcloud.io/summary/new_code?id=heitorpolidoro_apras"><img src="https://sonarcloud.io/api/project_badges/measure?project=heitorpolidoro_apras&metric=bugs" alt="SonarCloud Bugs"></a>
<a href="https://sonarcloud.io/summary/new_code?id=heitorpolidoro_apras"><img src="https://sonarcloud.io/api/project_badges/measure?project=heitorpolidoro_apras&metric=vulnerabilities" alt="SonarCloud Vulnerabilities"></a>
<a href="https://sonarcloud.io/summary/new_code?id=heitorpolidoro_apras"><img src="https://sonarcloud.io/api/project_badges/measure?project=heitorpolidoro_apras&metric=code_smells" alt="SonarCloud Code Smells"></a>
<a href="https://sonarcloud.io/summary/new_code?id=heitorpolidoro_apras"><img src="https://sonarcloud.io/api/project_badges/measure?project=heitorpolidoro_apras&metric=sqale_rating" alt="SonarCloud Maintainability"></a>

</div>

O **APRAS** é o Aplicativo de Planejamento e Resoluções para Associações e Síndicos. O módulo atual cobre a gestão de tarefas da administração: criação, atribuição, acompanhamento de status, comentários e auditoria completa de alterações, com controle de acesso por papéis.

- **Frontend (produção):** https://apras-front.vercel.app
- **Backend (produção):** https://apras-back.vercel.app

## Funcionalidades

- **Gestão de tarefas** com categorias, prioridades, status e atribuição a usuários
- **Controle de acesso (RBAC)** com três papéis: Administrador, Diretor e Gerente
- **Auditoria** — todo histórico de alterações de uma tarefa é registrado e exibido na linha do tempo
- **Comentários** por tarefa
- **Internacionalização** (pt-BR e en) via i18next

## Tecnologias

### Backend

- **Linguagem:** Python 3.13
- **Framework:** FastAPI
- **ORM:** SQLModel (SQLAlchemy) com migrações via Alembic
- **Banco de Dados:** PostgreSQL 16
- **Autenticação:** JWT (PyJWT) + bcrypt, rate limiting com slowapi
- **Gerenciador de Pacotes:** uv

### Frontend

- **Framework:** React 19 (TypeScript)
- **Build Tool:** Vite
- **Estilização:** Tailwind CSS + Radix UI
- **Estado de servidor:** TanStack Query

## Execução local

### Docker Compose (tudo junto)

```bash
docker compose up --build
# backend  → http://localhost:8001
# frontend → http://localhost:3001
# postgres → localhost:5436
```

### Manual

```bash
# Backend
cd backend
uv sync --all-groups
uv run uvicorn app.main:app --reload --port 8001

# Frontend
cd frontend
npm install
npm run dev   # http://localhost:3000
```

As configurações de ambiente (banco de dados, chaves secretas, etc.) ficam em `backend/.env` e `frontend/.env.local` — veja o `CLAUDE.md` para os valores de desenvolvimento.

## Testes

```bash
# Backend (cobertura mínima: 90%)
cd backend && uv run pytest --cov=app tests/

# Frontend (cobertura mínima: 75%)
cd frontend && npm run test:coverage
```

## Deploy

O deploy é feito na **Vercel** (projetos `apras-front` e `apras-back`). Todo merge na branch `master` dispara automaticamente o deploy de produção dos dois projetos via integração Git. As migrações de banco rodam no GitHub Actions (`migrate.yml`) a cada push na `master`.

## Contribuição e Fluxo de Trabalho

Branches de feature (`feat/`), commits descritivos e Pull Requests para a branch principal (`master`). O CI (GitHub Actions) roda testes de backend e frontend com gates de cobertura, além de análise no SonarCloud e DeepSource — um PR só pode ser mergeado com todos os checks verdes.

## Segurança

Autenticação via JWT (HS256) e controle de acesso baseado em papéis (RBAC) — Administrador, Diretor e Gerente, com permissões distintas para tarefas e categorias. Credenciais sensíveis são gerenciadas via variáveis de ambiente.
