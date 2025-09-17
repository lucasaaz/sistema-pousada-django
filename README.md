# 🏨 Sistema de Gerenciamento de Hotéis e Pousadas

Um sistema web robusto e completo para a administração de hotéis, pousadas e outros estabelecimentos de hospedagem. Desenvolvido com Python, Django e SQLite, o projeto oferece uma solução integrada para gerenciar reservas, hóspedes, acomodações e operações diárias.

![Badge Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Badge Django](https://img.shields.io/badge/Django-4.x-green?logo=django)
![Badge SQLite](https://img.shields.io/badge/SQLite-3-blue?logo=sqlite)
![Badge License](https://img.shields.io/badge/License-MIT-brightgreen)


## ✨ Funcionalidades Principais

* **Dashboard Administrativo**: Visão geral com estatísticas de ocupação, check-ins/check-outs previstos e outras métricas importantes.
* **Gestão de Reservas**: Crie, edite, visualize e filtre reservas com um calendário de disponibilidade.
* **Controle de Hóspedes (CRM)**: Cadastro completo de clientes com histórico de hospedagens.
* **Gerenciamento de Acomodações**: Configure diferentes tipos de quartos (standard, luxo, etc.), defina preços e gerencie o status (disponível, ocupado, em manutenção).
* **Check-in e Check-out Simplificado**: Processe a entrada e saída de hóspedes de forma rápida, com cálculo automático de despesas.
* **Gestão Financeira**: Controle de pagamentos, registro de consumos extras e fechamento de contas.
* **Painel de Configurações**: Personalize informações do hotel, formas de pagamento, e outros parâmetros do sistema.

## 🛠️ Tecnologias Utilizadas

* **Backend**: Python, Django Framework
* **Banco de Dados**: SQLite 3 (padrão do Django para desenvolvimento)
* **Frontend**: HTML, CSS, JavaScript (com templates Django)
* **Controle de Versão**: Git

## ⚙️ Pré-requisitos

Antes de começar, garanta que você tenha os seguintes softwares instalados:

1.  **Python 3.8+**: [python.org](https://www.python.org/downloads/) (Lembre-se de marcar a opção "Add Python to PATH" durante a instalação).
2.  **Git**: [git-scm.com](https://git-scm.com/downloads) (Para clonar o repositório).

## 🚀 Guia de Instalação Local

Siga estes passos para configurar o ambiente de desenvolvimento em sua máquina.

1.  **Clone o Repositório**
    Abra seu terminal e clone o projeto:
    ```sh
    git clone <URL_DO_SEU_REPOSITORIO>
    cd nome-da-pasta-do-projeto
    ```

2.  **Crie e Ative o Ambiente Virtual**
    Isso mantém as dependências do projeto organizadas.
    ```sh
    # Criar o ambiente
    python -m venv venv

    # Ativar no Windows
    .\venv\Scripts\activate

    # Ativar no Linux ou macOS
    source venv/bin/activate
    ```

3.  **Instale as Dependências**
    Instale todas as bibliotecas necessárias com um único comando:
    ```sh
    pip install -r requirements.txt
    ```

4.  **Execute as Migrações do Banco de Dados**
    Este comando criará o arquivo do banco de dados SQLite (`db.sqlite3`) e as tabelas do sistema.
    ```sh
    python manage.py migrate
    ```

5.  **Crie um Superusuário**
    Crie o primeiro usuário administrador para acessar o painel de controle:
    ```sh
    python manage.py createsuperuser
    ```
    (Siga as instruções para definir o nome de usuário, e-mail e senha).

## ▶️ Executando o Sistema

1.  Com tudo pronto, inicie o servidor de desenvolvimento:
    ```sh
    python manage.py runserver
    ```
2.  Abra seu navegador e acesse a aplicação:
    * **Página Inicial**: `http://127.0.0.1:8000`
    * **Painel Administrativo**: `http://127.0.0.1:8000/admin`

## 🌐 Implantação (Deploy)

Para tornar o sistema acessível publicamente, você precisará implantá-lo em um servidor de hospedagem.

* **Recomendação de Banco de Dados**: Para produção, é altamente recomendável migrar de SQLite para um banco de dados mais robusto como **PostgreSQL** ou **MySQL**. O SQLite é excelente para desenvolvimento, mas pode não ser adequado para ambientes com muitos acessos simultâneos.
* **Provedor de Hospedagem**: Escolha um serviço que suporte Python/Django (Ex: Hostinger, DigitalOcean, PythonAnywhere, Heroku).
* **Ajustes de Segurança**: Em `settings.py`, certifique-se de que `DEBUG = False` e configure o `ALLOWED_HOSTS` com o seu domínio. A `SECRET_KEY` também deve ser única e mantida em segredo.
