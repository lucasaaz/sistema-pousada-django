# ==============================================================================
# ARQUIVO: hotel_project/gestao/models.py
# DESCRIÇÃO: Define todas as tabelas e relacionamentos do banco de dados.
# ==============================================================================
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum

# Módulo: Configurações da Pousada/Hotel
class ConfiguracaoHotel(models.Model):
    nome = models.CharField(max_length=100, help_text="Nome do Hotel/Pousada")
    endereco = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='logos/', null=True, blank=True)
    
    def __str__(self):
        return self.nome

# Módulo: Clientes
class Cliente(models.Model):
    nome_completo = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, unique=True, help_text="Formato: 000.000.000-00")
    email = models.EmailField(unique=True, null=True, blank=True)
    telefone = models.CharField(max_length=20)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_completo

# Módulo: Acomodações
class TipoAcomodacao(models.Model):
    nome = models.CharField(max_length=50, unique=True, help_text="Ex: Suíte Master, Quarto Simples")
    descricao = models.TextField(blank=True)

    def __str__(self):
        return self.nome

class Acomodacao(models.Model):
    STATUS_CHOICES = (
        ('disponivel', 'Disponível'),
        ('ocupado', 'Ocupado'),
        ('manutencao', 'Em Manutenção'),
        ('limpeza', 'Limpeza'),
    )
    numero = models.CharField(max_length=10, unique=True)
    tipo = models.ForeignKey(TipoAcomodacao, on_delete=models.PROTECT)
    valor_diaria = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.TextField(null=True, blank=True)
    capacidade = models.PositiveIntegerField(default=1, help_text="Número máximo de hóspedes.") # NOVO CAMPO
    qtd_camas = models.PositiveIntegerField(default=1, help_text="Quantidade de camas no quarto.") # NOVO CAMPO
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disponivel')

    def __str__(self):
        return f"{self.tipo.nome} - Nº {self.numero}"

# Módulo: Estacionamento
class VagaEstacionamento(models.Model):
    numero_vaga = models.CharField(max_length=10, unique=True)
    disponivel = models.BooleanField(default=True)
    # Vínculo opcional, uma vaga pode ser de uma acomodação específica
    acomodacao_vinculada = models.OneToOneField(Acomodacao, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Vaga {self.numero_vaga}"

# Módulo: Estoque e Frigobar
class ItemEstoque(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    quantidade = models.PositiveIntegerField(default=0)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.nome} ({self.quantidade} un.)"

class Frigobar(models.Model):
    acomodacao = models.OneToOneField(Acomodacao, on_delete=models.CASCADE, related_name='frigobar')
    itens = models.ManyToManyField(ItemEstoque, through='ItemFrigobar')

    def __str__(self):
        return f"Frigobar da Acomodação {self.acomodacao.numero}"

class ItemFrigobar(models.Model):
    frigobar = models.ForeignKey(Frigobar, on_delete=models.CASCADE)
    item = models.ForeignKey(ItemEstoque, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)

# Módulo: Reservas
class Reserva(models.Model):
    STATUS_CHOICES = (
        ('confirmada', 'Confirmada'),
        ('checkin', 'Check-in Realizado'),
        ('checkout', 'Check-out Realizado'),
        ('cancelada', 'Cancelada'),
    )
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='reservas')
    acomodacao = models.ForeignKey(Acomodacao, on_delete=models.CASCADE, related_name='reservas')
    data_checkin = models.DateField()
    data_checkout = models.DateField()
    data_reserva = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmada')
    
    # Valores calculados no checkout
    valor_total_diarias = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    valor_consumo = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    valor_extra = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, help_text="Taxas ou valores adicionais.")
    valor_total_pago = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Reserva de {self.cliente.nome_completo} para {self.acomodacao.numero}"
    
    def save(self, *args, **kwargs):
        """
        Sobrescreve o método save() para calcular o valor total das diárias
        sempre que uma reserva é criada ou editada.
        """
        self.valor_total_diarias = self.calcular_total_diarias()
        super().save(*args, **kwargs)

    # Modulo: Cálculo de valores da reserva
    def calcular_total_diarias(self):
        """Calcula o valor total das diárias com base nas datas."""
        if self.data_checkin and self.data_checkout:
            num_dias = (self.data_checkout - self.data_checkin).days
            return num_dias * self.acomodacao.valor_diaria
        return 0

    def total_a_pagar(self):
        """Calcula o valor total da reserva (diárias + consumo - desconto + extras)."""
        return self.valor_total_diarias + self.valor_consumo - self.desconto + self.valor_extra

    def total_pago(self):
        """Calcula o total de pagamentos já efetuados para esta reserva."""
        return self.pagamentos.aggregate(Sum('valor'))['valor__sum'] or 0

    def saldo_devedor(self):
        """Calcula o saldo que ainda falta pagar."""
        return self.total_a_pagar() - self.total_pago()

# Módulo: Consumo durante a estadia
class Consumo(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='consumos')
    item = models.ForeignKey(ItemEstoque, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, help_text="Preço do item no momento do consumo")
    data_consumo = models.DateTimeField(auto_now_add=True)

    def total(self):
        return self.quantidade * self.preco_unitario

# Módulo: Pagamentos
class FormaPagamento(models.Model):
    nome = models.CharField(max_length=50, unique=True, help_text="Ex: Dinheiro, Cartão de Crédito, PIX")
    
    def __str__(self):
        return self.nome

class Pagamento(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='pagamentos')
    forma_pagamento = models.ForeignKey(FormaPagamento, on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_pagamento = models.DateTimeField(default=timezone.now)

# Módulo: Funcionários (usa o sistema de usuários do Django)
# O controle de acesso é feito via Grupos e Permissões no painel /admin.
# Ex: Grupo "Recepcionista", Grupo "Gerente"

# Módulo: Gestão financeira
class GastoCategoria(models.Model):
    """Categorias para agrupar diferentes tipos de gastos (limpeza, manutenção, etc.)."""
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome

class Gasto(models.Model):
    descricao = models.CharField(max_length=255)
    categoria = models.ForeignKey(GastoCategoria, on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_gasto = models.DateField(default=timezone.now, db_index=True)  # <= index

    def __str__(self):
        return f"Gasto de R$ {self.valor} em {self.data_gasto.strftime('%d/%m/%Y')} ({self.categoria.nome})"

































































































# # gestao/models.py
# from django.db import models
# from django.contrib.auth.models import User

# # Módulo: Configurações
# class ConfiguracaoHotel(models.Model):
#     nome_hotel = models.CharField(max_length=100)
#     endereco = models.CharField(max_length=255)
#     telefone = models.CharField(max_length=20)
#     email = models.EmailField()
#     logo = models.ImageField(upload_to='logos/', null=True, blank=True)

# # Módulo: Clientes
# class Cliente(models.Model):
#     nome_completo = models.CharField(max_length=150)
#     cpf = models.CharField(max_length=14, unique=True)
#     email = models.EmailField(unique=True)
#     telefone = models.CharField(max_length=20)
#     data_nascimento = models.DateField()
#     data_cadastro = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return self.nome_completo

# # Módulo: Acomodações
# class TipoAcomodacao(models.Model):
#     nome = models.CharField(max_length=100)

#     def __str__(self):
#         return self.nome

# class Acomodacao(models.Model):
#     STATUS_CHOICES = (
#         ('disponivel', 'Disponível'),
#         ('ocupado', 'Ocupado'),
#         ('manutencao', 'Em Manutenção'),
#     )
#     numero = models.CharField(max_length=10)
#     tipo = models.ForeignKey(TipoAcomodacao, on_delete=models.PROTECT)
#     valor_diaria = models.DecimalField(max_digits=10, decimal_places=2)
#     descricao = models.TextField(null=True, blank=True)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disponivel')

#     def __str__(self):
#         return f"{self.tipo.nome} - {self.numero}"

# # Módulo: Estacionamento
# class VagaEstacionamento(models.Model):
#     numero_vaga = models.CharField(max_length=10, unique=True)
#     # Vínculo pode ser opcional
#     acomodacao_vinculada = models.OneToOneField(Acomodacao, on_delete=models.SET_NULL, null=True, blank=True)
#     status = models.CharField(max_length=20, default='disponivel') # disponivel, ocupado

# # Módulo: Estoque e Frigobar
# class ItemEstoque(models.Model):
#     nome = models.CharField(max_length=100)
#     descricao = models.TextField(blank=True)
#     quantidade = models.PositiveIntegerField(default=0)
#     preco_venda = models.DecimalField(max_digits=10, decimal_places=2)

#     def __str__(self):
#         return self.nome

# class Frigobar(models.Model):
#     acomodacao = models.OneToOneField(Acomodacao, on_delete=models.CASCADE)
#     itens = models.ManyToManyField(ItemEstoque, through='ItemFrigobar')

# class ItemFrigobar(models.Model):
#     frigobar = models.ForeignKey(Frigobar, on_delete=models.CASCADE)
#     item = models.ForeignKey(ItemEstoque, on_delete=models.CASCADE)
#     quantidade = models.PositiveIntegerField()

# # Módulo: Reservas
# class Reserva(models.Model):
#     STATUS_CHOICES = (
#         ('confirmada', 'Confirmada'),
#         ('checkin', 'Check-in'),
#         ('checkout', 'Check-out'),
#         ('cancelada', 'Cancelada'),
#     )
#     cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
#     acomodacao = models.ForeignKey(Acomodacao, on_delete=models.CASCADE)
#     data_checkin = models.DateField()
#     data_checkout = models.DateField()
#     data_reserva = models.DateTimeField(auto_now_add=True)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmada')
#     valor_total_diarias = models.DecimalField(max_digits=10, decimal_places=2, default=0)
#     desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
#     valor_extra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
#     valor_final_pago = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

# # Módulo: Consumo
# class Consumo(models.Model):
#     reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='consumos')
#     item = models.ForeignKey(ItemEstoque, on_delete=models.CASCADE)
#     quantidade = models.PositiveIntegerField()
#     data_consumo = models.DateTimeField(auto_now_add=True)

# # Módulo: Pagamentos
# class FormaPagamento(models.Model):
#     nome = models.CharField(max_length=50) # Dinheiro, Cartão, Pix

#     def __str__(self):
#         return self.nome

# class Pagamento(models.Model):
#     reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE)
#     forma_pagamento = models.ForeignKey(FormaPagamento, on_delete=models.PROTECT)
#     valor = models.DecimalField(max_digits=10, decimal_places=2)
#     data_pagamento = models.DateTimeField(auto_now_add=True)

# # Módulo: Funcionários (usa o User do Django)
# # O controle de acesso (Admin/Usuário) é feito pelos grupos e permissões do Django.