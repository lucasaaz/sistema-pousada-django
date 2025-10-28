# ==============================================================================
# ARQUIVO: hotel_project/gestao/models.py
# DESCRIÇÃO: Define todas as tabelas e relacionamentos do banco de dados.
# ==============================================================================
from django.db import models
from django.utils import timezone
from django.db.models import Sum
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords

# Módulo: Configurações da Pousada/Hotel
class ConfiguracaoHotel(models.Model):
    nome = models.CharField(max_length=100, help_text="Nome do Hotel/Pousada")
    endereco = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='logos/', null=True, blank=True)
    history = HistoricalRecords()
    
    def __str__(self):
        return self.nome

# Módulo: Clientes
class Cliente(models.Model):
    SEXO_CHOICES = (
        ('Masculino', 'Masculino'),
        ('Feminino', 'Feminino'),
        ('Outro', 'Outro'),
    )

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
    sexo = models.CharField(max_length=10, choices=SEXO_CHOICES, null=True, blank=True)
    history = HistoricalRecords()


    def __str__(self):
        return self.nome_completo

# Módulo: Tipo Acomodações
class TipoAcomodacao(models.Model):
    nome = models.CharField(max_length=50, unique=True, help_text="Ex: Suíte Master, Quarto Simples")
    descricao = models.TextField(blank=True)
    history = HistoricalRecords()

    chave_de_preco = models.CharField(
        max_length=50,
        help_text="Chave usada pela calculadora de tarifas (ex: 'quarto', 'chale', 'coletivo', 'quarto_familia'). Use apenas letras minúsculas e sem espaços."
    )

    def __str__(self):
        return self.nome

# Módulo: Acomodações
class Acomodacao(models.Model):
    STATUS_CHOICES = (
        ('disponivel', 'Disponível'),
        ('ocupado', 'Ocupado'),
        ('manutencao', 'Em Manutenção'),
        ('limpeza', 'Limpeza'),
    )
    numero = models.CharField(max_length=10, unique=True)
    tipo = models.ForeignKey(TipoAcomodacao, on_delete=models.PROTECT, related_name='acomodacoes')
    descricao = models.TextField(null=True, blank=True)
    capacidade = models.PositiveIntegerField(default=1, help_text="Número máximo de hóspedes.") 
    qtd_camas = models.PositiveIntegerField(default=1, help_text="Quantidade de camas no quarto.") 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disponivel')
    history = HistoricalRecords()

    @property
    def nome_display(self):
        # Se o número for o texto "1" ou o texto "2", é um Chalé
        if self.numero in ('1', '2'):
            return f"Chalé {self.numero}"
        # Para todos os outros casos ("01", "02", etc.), é um Quarto
        else:
            return f"Quarto {self.numero}"

    def __str__(self):
        return self.nome_display

# Módulo: Estacionamento
class VagaEstacionamento(models.Model):
    numero_vaga = models.CharField(max_length=10, unique=True)
    disponivel = models.BooleanField(default=True)
    # Vínculo opcional, uma vaga pode ser de uma acomodação específica
    acomodacao_vinculada = models.OneToOneField(Acomodacao, on_delete=models.SET_NULL, null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Vaga {self.numero_vaga}"

# Módulo: Estoque e Frigobar
class ItemEstoque(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    quantidade = models.PositiveIntegerField(default=0)
    preco_venda = models.DecimalField("Preço de Venda", max_digits=10, decimal_places=2)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.nome} ({self.quantidade} un.)"
    
class CompraEstoque(models.Model):
    item = models.ForeignKey(ItemEstoque, on_delete=models.PROTECT, related_name='compras')
    quantidade = models.PositiveIntegerField()
    preco_compra_unitario = models.DecimalField("Preço de Custo (Unitário)", max_digits=10, decimal_places=2)
    fornecedor = models.CharField("Fornecedor/Local da Compra", max_length=100, null=True, blank=True)
    data_compra = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    def __str__(self):
        return f"Compra de {self.quantidade}x {self.item.nome} em {self.data_compra.strftime('%d/%m/%Y')}"

    @property
    def preco_compra_total(self):
        return self.quantidade * self.preco_compra_unitario

class Frigobar(models.Model):
    acomodacao = models.OneToOneField(Acomodacao, on_delete=models.CASCADE, related_name='frigobar')
    itens = models.ManyToManyField(ItemEstoque, through='ItemFrigobar')
    history = HistoricalRecords()

    def __str__(self):
        return f"Frigobar da Acomodação {self.acomodacao.numero}"

class ItemFrigobar(models.Model):
    frigobar = models.ForeignKey(Frigobar, on_delete=models.CASCADE)
    item = models.ForeignKey(ItemEstoque, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    history = HistoricalRecords()

#  Módulo: Reservas em Grupo
class GrupoReserva(models.Model):
    nome_grupo = models.CharField("Nome do Grupo", max_length=150, help_text="Ex: Excursão Família Silva")
    cliente_responsavel = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='grupos_liderados')
    data_criacao = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True, null=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.nome_grupo

    class Meta:
        verbose_name = "Grupo de Reserva"
        verbose_name_plural = "Grupos de Reserva"

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
    data_checkin = models.DateTimeField()
    data_checkout = models.DateTimeField()
    data_reserva = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pre_reserva')
    num_adultos = models.PositiveIntegerField("N° Adultos", default=1, help_text="N° de adultos") 
    num_criancas_5 = models.PositiveIntegerField("N° Crianças até 5 anos", default=0, help_text="Crianças até 5 anos") 
    num_criancas_12 = models.PositiveIntegerField("N° Crianças de 6 a 12 anos", default=0, help_text="Crianças de 6 a 12 anos") 
    valor_total_diarias = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    placa_automovel = models.CharField(max_length=15, null=True, blank=True, verbose_name="Placa do Automóvel")
    tipo_tarifa = models.CharField(max_length=20,choices=[('diaria', 'Diária'), ('pacote', 'Pacote')],default='diaria')
    history = HistoricalRecords()
    
    # Valores calculados no checkout
    valor_consumo = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    valor_extra = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, help_text="Taxas ou valores adicionais.")
    valor_total_pago = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    grupo = models.ForeignKey(
        GrupoReserva, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reservas'
    )

    def __str__(self):
        return f"Reserva de {self.cliente.nome_completo} para {self.acomodacao.numero}"

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
    @property
    def status_color(self):
        status_map = {
            'cancelada': '#dc3545',   # Cinza (Bootstrap Secondary)
            'checkin': '#0dcaf0',     # Azul Claro (Bootstrap Info)
            'checkout': '#6c757d',    # Vermelho (Bootstrap Danger)
            'confirmada': '#198754',  # Verde (Bootstrap Success)
            'pre_reserva': '#ffc107', # Amarelo (Bootstrap Warning)
        }
        return status_map.get(self.status, '#6c757d') # Retorna cinza como padrão

# Módulo: Consumo durante a estadia
class Consumo(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='consumos')
    item = models.ForeignKey(ItemEstoque, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, help_text="Preço do item no momento do consumo")
    data_consumo = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def total(self):
        return self.quantidade * self.preco_unitario

# Módulo: Forma Pagamentos
class FormaPagamento(models.Model):
    nome = models.CharField(max_length=50, unique=True, help_text="Ex: Dinheiro, Cartão de Crédito, PIX")
    history = HistoricalRecords()
    
    def __str__(self):
        return self.nome

# Módulo: Pagamentos
class Pagamento(models.Model):
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='pagamentos', null=True, blank=True)
    forma_pagamento = models.ForeignKey(FormaPagamento, on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_pagamento = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    evento = models.ForeignKey(
        'Evento',
        on_delete=models.CASCADE,
        related_name='pagamentos',
        null=True,
        blank=True
    )

    def clean(self):
        reserva = getattr(self, "reserva", None)
        evento = getattr(self, "evento", None)

        if reserva and evento:
            raise ValidationError("O pagamento não pode estar associado a uma reserva e a um evento ao mesmo tempo.")

    def __str__(self):
        if self.reserva:
            return f"Pagamento de R$ {self.valor} para a Reserva #{self.reserva.pk}"
        elif self.evento:
            return f"Pagamento de R$ {self.valor} para o Evento '{self.evento.nome_evento}'"
        return f"Pagamento de R$ {self.valor}"

# Módulo: Funcionários (usa o sistema de usuários do Django)
# O controle de acesso é feito via Grupos e Permissões no painel /admin.
# Ex: Grupo "Recepcionista", Grupo "Gerente"

# Módulo: Categotias de Gastos e Controle Financeiro
class CategoriaGasto(models.Model):
    nome = models.CharField(max_length=100, unique=True, help_text="Ex: Alimentação, Limpeza, Manutenção")
    history = HistoricalRecords()

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
    data_gasto = models.DateField(default=timezone.now, db_index=True)  
    history = HistoricalRecords()
    
    evento = models.ForeignKey(
        'Evento', 
        on_delete=models.SET_NULL, # Se o evento for deletado, o gasto não é, apenas perde o vínculo
        null=True, 
        blank=True, 
        related_name='gastos'
    )

    def __str__(self):
        return f"Gasto de R$ {self.valor} em {self.data_gasto.strftime('%d/%m/%Y')} ({self.categoria.nome})"
    
# Módulo: Upload de Arquivos (ex: contratos assinados)
class ArquivoReserva(models.Model):
    reserva = models.ForeignKey("Reserva", on_delete=models.CASCADE, related_name="arquivos")
    arquivo = models.FileField(upload_to="arquivos_reservas/")
    criado_em = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Arquivo {self.id} da Reserva {self.reserva.id}"
    
# Módulo: Períodos Tarifários Especiais 
class PeriodoTarifario(models.Model):
    nome = models.CharField("Nome do Período", max_length=100, help_text="Ex: Réveillon 2025, Feriado de Tiradentes")
    data_inicio = models.DateField("Data de Início")
    data_fim = models.DateField("Data de Fim")
    percentual_ajuste = models.DecimalField(
        "Ajuste Percentual (%)", 
        max_digits=5, 
        decimal_places=2,
        help_text="Use valores positivos para acréscimos (ex: 20.00 para +20%) e negativos para descontos (ex: -10.00 para -10%)."
    )
    ativo = models.BooleanField("Ativo", default=True, help_text="Desmarque para desativar esta regra temporariamente.")

    acomodacoes = models.ManyToManyField(
        'Acomodacao', 
        blank=True, 
    )

    clientes = models.ManyToManyField(
        'Cliente',
        blank=True,
    )
    history = HistoricalRecords()

    def __str__(self):
        sinal = "+" if self.percentual_ajuste > 0 else ""
        return f"{self.nome} ({self.data_inicio.strftime('%d/%m')} a {self.data_fim.strftime('%d/%m')}) | {sinal}{self.percentual_ajuste}%"

    class Meta:
        verbose_name = "Período Tarifário"
        verbose_name_plural = "Períodos Tarifários"
        ordering = ['data_inicio']

# Módulo: Espaço
class Espaco(models.Model):
    TIPO_CHOICES = (
        ('espaco', 'Espaço Físico'),       # Para Salão de Festas, Área da Piscina, etc.
        ('item_servico', 'Item ou Serviço'), # Para Aluguel de Mesas, Cadeiras, etc.
    )

    # --- CAMPO ADICIONADO AQUI ---
    tipo = models.CharField("Tipo", max_length=20, choices=TIPO_CHOICES, default='espaco')
    
    nome = models.CharField("Nome do Espaço/Item", max_length=100, unique=True)
    descricao = models.TextField(blank=True, null=True)
    
    # --- HELP_TEXT ATUALIZADO ---
    capacidade = models.PositiveIntegerField(
        "Capacidade", 
        null=True, 
        blank=True,
        help_text="Para 'Espaços Físicos', informe a capacidade máxima de pessoas."
    )
    valor_base = models.DecimalField("Valor Base (R$)", max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)
    history = HistoricalRecords()
    

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Espaço ou Item Alugável"
        verbose_name_plural = "Espaços e Itens Alugáveis"

# Módulo: Evento
class Evento(models.Model):
    STATUS_CHOICES = (
        ('orcamento', 'Orçamento'),
        ('confirmado', 'Confirmado'),
        ('realizado', 'Realizado'),
        ('cancelado', 'Cancelado'),
    )
    nome_evento = models.CharField("Nome do Evento", max_length=150)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='eventos')
    espacos = models.ManyToManyField(Espaco, related_name='eventos', verbose_name="Espaços Selecionados")
    data_inicio = models.DateTimeField("Início do Evento")
    data_fim = models.DateTimeField("Fim do Evento")
    numero_convidados = models.PositiveIntegerField("Nº de Convidados", default=1)
    valor_negociado = models.DecimalField("Valor Total do Evento (R$)", max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='orcamento')
    data_registro = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField("Observações Adicionais", blank=True, null=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.nome_evento} - {self.cliente.nome_completo}"

    def total_custos(self):
        """ Calcula o total de custos extras (CustoEvento) """
        # 'self.custos' usa o related_name='custos' do CustoEvento
        total = self.custos.aggregate(total=Sum('valor'))['total']
        return total or 0

    def total_pagamentos(self):
        """ Calcula o total de pagamentos já feitos """
        # 'self.pagamentos' usa o related_name='pagamentos' do Pagamento
        total = self.pagamentos.aggregate(total=Sum('valor'))['total']
        return total or 0
    
    def total_a_pagar(self):
        """ Calcula o valor negociado MAIS os custos extras """
        # Garante que ambos são Decimais antes de somar
        return (self.valor_negociado or 0) + self.total_custos()

    def saldo_devedor(self):
        """ Calcula o saldo restante a ser pago """
        return self.total_a_pagar() - self.total_pagamentos()

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        ordering = ['-data_inicio']

class CustoEvento(models.Model):
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_custo = models.DateField("Data de Custo") 
    history = HistoricalRecords()

    evento = models.ForeignKey(
        'Evento', 
        on_delete=models.SET_NULL, # Se o evento for deletado, o custo não é, apenas perde o vínculo
        null=True, 
        blank=True, 
        related_name='custos'
    )

    def __str__(self):
        return f"Custo de R$ {self.valor} em {self.data_custo.strftime('%d/%m/%Y')}"