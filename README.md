# Sistema de Gerenciamento de Hotéis e Pousadas

Este é um sistema completo desenvolvido em Python com o framework Django e banco de dados MySQL para a gestão de estabelecimentos hoteleiros.

## ⚙️ Pré-requisitos

1.  **Python 3.8+**: [https://www.python.org/downloads/](https://www.python.org/downloads/) (Marque "Add Python to PATH" na instalação).
2.  **XAMPP**: [https://www.apachefriends.org/index.html](https://www.apachefriends.org/index.html) (Inclui Apache e MySQL).
3.  **Git**: [https://git-scm.com/downloads](https://git-scm.com/downloads).

## 🚀 Instalação Local

### 1. Configuração do Banco de Dados

-   Abra o painel de controle do **XAMPP** e inicie os módulos **Apache** e **MySQL**.
-   Abra seu navegador e acesse `http://localhost/phpmyadmin`.
-   Clique em **"Novo"** no menu à esquerda.
-   Dê o nome ao banco de dados, por exemplo: `hotel_db`.
-   Escolha o agrupamento (collation) como `utf8mb4_general_ci` e clique em **"Criar"**.

### 2. Configuração do Projeto

-   Abra um terminal (Prompt de Comando, PowerShell ou Terminal).
-   Clone o repositório do projeto (se estiver no GitHub) ou descompacte os arquivos em uma pasta.
    ```sh
    git clone <URL_DO_REPOSITORIO>
    cd nome-da-pasta-do-projeto
    ```
-   Crie e ative um ambiente virtual. Isso isola as dependências do seu projeto.
    ```sh
    # Criar ambiente virtual
    python -m venv venv

    # Ativar no Windows
    .\venv\Scripts\activate

    # Ativar no Linux ou macOS
    source venv/bin/activate
    ```
-   Instale todas as bibliotecas Python necessárias com um único comando:
    ```sh
    pip install -r requirements.txt
    ```
    *(O `requirements.txt` deve conter `Django`, `mysqlclient`, etc.)*

### 3. Conectando o Projeto ao Banco de Dados

-   Abra o arquivo `hotel_project/settings.py` em um editor de código.
-   Localize a seção `DATABASES` e edite-a com as informações do seu MySQL no XAMPP. (Por padrão, o usuário é `root` e a senha é vazia).

    ```python
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'hotel_db',        # Nome do banco que você criou
            'USER': 'root',            # Usuário padrão do XAMPP
            'PASSWORD': '',            # Senha padrão do XAMPP (vazia)
            'HOST': '127.0.0.1',
            'PORT': '3306',
        }
    }
    ```

### 4. Finalizando a Instalação

-   No terminal, com o ambiente virtual ainda ativo, execute os seguintes comandos para criar as tabelas no banco de dados e criar um usuário administrador:
    ```sh
    # Cria as tabelas com base no arquivo models.py
    python manage.py migrate

    # Cria o primeiro usuário administrador do sistema
    python manage.py createsuperuser
    ```
    *(Siga as instruções para definir nome de usuário, email e senha).*

### 5. Executando o Sistema

-   Tudo pronto! Inicie o servidor de desenvolvimento local:
    ```sh
    python manage.py runserver
    ```
-   Abra seu navegador e acesse: **`http://127.0.0.1:8000`** para ver o sistema funcionando.
-   Para acessar o painel administrativo (útil para cadastros iniciais), acesse: **`http://127.0.0.1:8000/admin`**.

## 📝 Uso Básico

1.  **Primeiro Acesso**: Faça login com o usuário administrador que você criou.
2.  **Configurações Iniciais**: Pelo painel de admin, cadastre os dados do hotel, os tipos de acomodação, as formas de pagamento e os itens de estoque.
3.  **Cadastro**: Use a interface principal para cadastrar seus primeiros clientes e acomodações.
4.  **Criar Reserva**: Vá para a seção de Reservas, use o filtro de datas para verificar a disponibilidade e crie uma nova reserva, vinculando um cliente e uma acomodação.
5.  **Check-in / Check-out**: Gerencie o status da reserva diretamente pela lista de reservas, realizando o check-in na chegada do hóspede e o check-out na saída, momento em que o sistema calculará os consumos e o valor final.

## 🌐 Implantação em Hospedagem (Deploy)

Para acessar o sistema de qualquer lugar com internet, o projeto precisa ser implantado em um servidor de hospedagem que suporte Python/Django.

1.  **Escolha um Provedor**: Hostinger, DigitalOcean, PythonAnywhere, Heroku, etc.
2.  **Configuração**: O processo geralmente envolve:
    -   Enviar os arquivos do projeto para o servidor (via Git ou FTP).
    -   Configurar um banco de dados MySQL no servidor de hospedagem e atualizar o arquivo `settings.py`.
    -   Instalar as dependências do `requirements.txt`.
    -   Configurar um servidor de aplicação (como Gunicorn ou uWSGI) para servir o projeto Django.
    -   Configurar um servidor web (como Nginx ou Apache) para direcionar o tráfego para a aplicação.
3.  **Ajustes Finais**: Em `settings.py`, certifique-se de que `DEBUG = False` e configure o `ALLOWED_HOSTS` com o seu domínio.