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
    data_nascimento = models.DateField(null=True, blank=True) # Atualizado 18.09.25
    cep = models.CharField(max_length=9, null=True, blank=True, help_text="Formato: 00000-000") # Atualizado 18.09.25
    logradouro = models.CharField(max_length=255, null=True, blank=True, verbose_name="Rua/Logradouro") # Atualizado 18.09.25
    numero = models.CharField(max_length=20, null=True, blank=True) # Atualizado 18.09.25
    complemento = models.CharField(max_length=100, null=True, blank=True) # Atualizado 18.09.25
    bairro = models.CharField(max_length=100, null=True, blank=True) # Atualizado 18.09.25
    cidade = models.CharField(max_length=100, null=True, blank=True) # Atualizado 18.09.25
    estado = models.CharField(max_length=2, null=True, blank=True, verbose_name="UF") # Atualizado 18.09.25
    foto = models.URLField(max_length=1024, null=True, blank=True, verbose_name="Foto do Cliente")


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
    tipo = models.ForeignKey(TipoAcomodacao, on_delete=models.PROTECT, related_name='acomodacoes')
    valor_diaria = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.TextField(null=True, blank=True)
    capacidade = models.PositiveIntegerField(default=1, help_text="Número máximo de hóspedes.") 
    qtd_camas = models.PositiveIntegerField(default=1, help_text="Quantidade de camas no quarto.") 
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
    preco_venda = models.DecimalField("Preço de Venda", max_digits=10, decimal_places=2)

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
        ('pre_reserva', 'Pré-reserva'),
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pre_reserva')
    num_adultos = models.PositiveIntegerField("N° Adultos", default=1, help_text="N° de adultos") 
    num_criancas_5 = models.PositiveIntegerField("N° Crianças até 5 anos", default=0, help_text="Crianças até 5 anos") 
    num_criancas_12 = models.PositiveIntegerField("N° Crianças de 6 a 12 anos", default=0, help_text="Crianças de 6 a 12 anos") 
    
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
    @property
    def num_dias(self):
        """Calcula e retorna o número de dias (diárias) da reserva."""
        if self.data_checkin and self.data_checkout:
            delta = self.data_checkout - self.data_checkin
            return delta.days
        return 0

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

# Módulo: Categotias de Gastos e Controle Financeiro
class CategoriaGasto(models.Model):
    nome = models.CharField(max_length=100, unique=True, help_text="Ex: Alimentação, Limpeza, Manutenção")

    class Meta:
        verbose_name = "Categoria de Gasto"
        verbose_name_plural = "Categorias de Gastos"
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Gasto(models.Model):
    descricao = models.CharField(max_length=255)
    categoria = models.ForeignKey(CategoriaGasto, on_delete=models.PROTECT, related_name='gastos')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_gasto = models.DateField(default=timezone.now, db_index=True)  # <= index

    def __str__(self):
        return f"Gasto de R$ {self.valor} em {self.data_gasto.strftime('%d/%m/%Y')} ({self.categoria.nome})"
    
# Módulo: Upload de Arquivos (ex: contratos assinados)
class ArquivoReserva(models.Model):
    reserva = models.ForeignKey("Reserva", on_delete=models.CASCADE, related_name="arquivos")
    arquivo = models.FileField(upload_to="arquivos_reservas/")
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Arquivo {self.id} da Reserva {self.reserva.id}"