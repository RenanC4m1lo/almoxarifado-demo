# 📦 Sistema de Almoxarifado

Sistema web completo de controle de estoque e movimentação de equipamentos, desenvolvido com Python (Flask) no backend e HTML/CSS/JavaScript puro no frontend.

Este é um projeto pessoal construído para resolver um problema real de gestão de estoque com múltiplas unidades/empresas, controle por código de barras, alertas automáticos e relatórios em PDF. Este repositório é a versão pública de demonstração (anonimizada e sem nenhum dado real), publicada no Render com PostgreSQL.

## 🔴 Demonstração ao vivo

**👉 https://almoxarifado-demo.onrender.com**

Dados e empresas são 100% fictícios. Logins de teste:

| Perfil | E-mail | Senha |
|--------|--------|-------|
| Super Admin (vê Matriz e Filial) | `superadmin@demo.com` | `demo123` |
| Admin — Matriz | `admin.matriz@demo.com` | `demo123` |
| Admin — Filial | `admin.filial@demo.com` | `demo123` |

> O banco gratuito do Render expira a cada 30 dias — se o login der erro, os dados de demonstração são recriados automaticamente no próximo acesso.

---

## 🚀 Funcionalidades

- 🔐 **Login e autenticação** com token JWT
- 🏢 **Multi-empresa** — estoques completamente separados por empresa, com isolamento auditado em todas as rotas do backend
- 🔄 **Trocar de empresa sem logout** — Super Admin pode alternar entre empresas direto pelo topbar
- 👥 **Controle de usuários** com perfis de acesso (Admin, Operador, Visitante)
- 🔧 **Gestão de equipamentos** com cadastro, edição e exclusão
- 👷 **Cadastro de Técnicos de Campo** — usado como lista de escolha no campo "Responsável" das movimentações
- 📷 **Código de barras** — cadastro e leitura de unidades individuais, com saída rápida por leitor
- 🔄 **Movimentações em lote** — saída, devolução e envio para manutenção de vários equipamentos de uma vez, misturando itens por nome (quantidade) e unidades específicas por código de barras na mesma operação, tudo numa transação só
- 🏭 **Gestão de fornecedores** por empresa
- ⚠️ **Alertas automáticos** de estoque baixo, gerados e resolvidos sem intervenção manual
- 📊 **Dashboard** com gráficos de status e movimentações por empresa, exportável em PDF
- 🔍 **Busca por texto** em todas as telas de listagem
- 📄 **Relatórios em PDF** de estoque, movimentações e materiais usados por técnico (com filtro de mês)
- 👤 **Super admin** com visão combinada entre todas as empresas

---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Frontend | HTML5, CSS3, JavaScript |
| Backend | Python 3.14 + Flask |
| Servidor de produção | Waitress (WSGI) |
| Banco de dados | PostgreSQL (nesta versão de demo; o projeto original roda em MySQL) |
| Autenticação | JWT (Flask-JWT-Extended) |
| Gráficos | Chart.js |
| PDF | ReportLab |

---

## 📁 Estrutura do Projeto

```
almoxarifado/
├── README.md
├── render.yaml                  # Deploy no Render
├── backend/
│   ├── app.py                   # Servidor Flask principal
│   ├── config.py                # Conexão com o banco (compatibilidade MySQL/Postgres)
│   ├── bootstrap_demo.py        # Popula a demo automaticamente num banco vazio
│   ├── requirements.txt
│   └── routes/
│       ├── auth.py              # Login, autenticação e troca de empresa
│       ├── usuarios.py          # Gestão de usuários
│       ├── equipamentos.py      # Gestão de equipamentos + manutenção em lote
│       ├── fornecedores.py      # Gestão de fornecedores
│       ├── movimentacoes.py     # Saídas e devoluções (individuais e em lote)
│       ├── alertas.py           # Alertas de estoque
│       ├── relatorios.py        # Geração de PDFs
│       ├── unidades.py          # Unidades por código de barras
│       ├── tecnicos.py          # Técnicos de campo
│       └── empresas.py          # Gestão de empresas
├── frontend/
│   ├── login.html
│   ├── dashboard.html
│   ├── equipamentos.html
│   ├── unidades.html
│   ├── movimentacoes.html
│   ├── fornecedores.html
│   ├── tecnicos.html
│   ├── relatorios.html
│   ├── usuarios.html
│   ├── css/style.css
│   └── js/
│       ├── config.js            # URL da API
│       └── main.js
└── banco/
    ├── schema.sql                # Script de criação do banco
    └── seed_demo.py               # Dados fictícios da demo
```

---

## ⚙️ Como rodar localmente

### Pré-requisitos

- Python 3.14+
- PostgreSQL (ou ajuste `backend/config.py` para MySQL)

### Passos

```
git clone https://github.com/RenanC4m1lo/almoxarifado-demo.git
cd almoxarifado-demo/backend
py -m pip install -r requirements.txt
```

Crie um arquivo `.env` dentro de `backend/` com:

```
DATABASE_URL=postgresql://usuario:senha@localhost/almoxarifado
JWT_SECRET_KEY=uma_chave_secreta_qualquer
CORS_ORIGINS=*
```

Depois:

```
py app.py
```

Em outro terminal, sirva o frontend:

```
cd ../frontend
py -m http.server 8080
```

E acesse `http://localhost:8080/login.html`. No primeiro boot com o banco vazio, `bootstrap_demo.py` cria as tabelas e popula os dados de demonstração automaticamente.

---

## 👤 Perfis de acesso

| Perfil | Permissões |
|--------|-----------|
| 👑 Super Admin | Acesso total a todas as empresas, pode trocar de empresa sem logout |
| 👑 Admin | Acesso total à sua empresa |
| ⚙️ Operador | Registrar saídas e devoluções |
| 👁️ Visitante | Apenas visualizar |

---

## 🏢 Sistema Multi-empresa

- Cada usuário pertence a uma empresa e só vê os dados dela
- O Super Admin pode selecionar qual empresa acessar no login, e trocar depois direto pelo topbar
- Equipamentos, movimentações e alertas são separados por empresa
- Cada empresa pode ter seus próprios fornecedores e usuários

---

## 📷 Código de Barras

- **Cadastro de unidades** — cada unidade física tem seu próprio código
- **Saída rápida** — aponte o leitor e registre a saída em segundos
- **Movimentações em lote** — no mesmo campo, digite o nome de um equipamento (por quantidade) ou escaneie/digite o código de uma unidade específica
- **Busca rápida** — encontre qualquer equipamento ou unidade pelo código

---

## 🔒 Destaques de engenharia

Pontos que exigiram mais atenção durante o desenvolvimento:

- **Isolamento entre empresas**: auditoria completa de todas as rotas do backend para garantir que nenhuma operação (leitura, edição, exclusão) misture dados entre empresas diferentes, nem aceite uma empresa vinda do corpo da requisição em vez da empresa de quem está logado.
- **Movimentações em lote transacionais**: saída/devolução/manutenção de vários itens numa única transação — se um item falhar (ex: estoque insuficiente), nada é gravado pela metade.
- **Alertas automáticos**: gerados e resolvidos sem intervenção manual, incluindo detecção de estoque já baixo ao abrir o sistema (não só em eventos novos).
- **Camada de compatibilidade de banco** (`backend/config.py`): o projeto original roda em MySQL; esta versão pública usa PostgreSQL no Render sem duplicar as rotas, emulando `cursor(dictionary=True)` e `.lastrowid` por cima do driver do Postgres.
- **Auto-recuperação da demo**: o banco gratuito do Render expira periodicamente; `bootstrap_demo.py` detecta um banco vazio e recria schema + dados fictícios automaticamente, sem intervenção manual.

---

## 📝 Licença

Projeto pessoal, publicado como parte do portfólio do autor.

---

Desenvolvido por **RenanC4m1lo** 🚀
