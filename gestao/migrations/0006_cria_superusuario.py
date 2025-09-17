# gestao/migrations/00XX_cria_superusuario.py

from django.db import migrations
import os

def criar_superusuario(apps, schema_editor):
    """Cria um superutilizador lendo os dados das variáveis de ambiente."""
    User = apps.get_model('auth', 'User')
    
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

    # Só cria se o utilizador não existir
    if not User.objects.filter(username=username).exists():
        if username and email and password:
            User.objects.create_superuser(username, email, password)
            print(f"\nSuperutilizador '{username}' criado com sucesso.")
        else:
            print("\nVariáveis de ambiente do superutilizador não configuradas. A criação foi ignorada.")

class Migration(migrations.Migration):

    dependencies = [
        # Coloque aqui a última migração da sua app 'gestao'
        ('gestao', '0005_alter_gasto_categoria_delete_gastocategoria'),
        ('auth', '__latest__'), # Garante que as tabelas de utilizador existem
    ]

    operations = [
        migrations.RunPython(criar_superusuario),
    ]