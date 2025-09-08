# ==============================================================================
# ARQUIVO: gestao/views.py (ATUALIZADO)
# DESCRIÇÃO: Adiciona as views para editar e excluir clientes.
# ==============================================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta, date
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.db.models import F, Count, Q, Sum, DecimalField, Value
from django.db.models.functions import ExtractMonth, ExtractYear, Coalesce, TruncMonth
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Reserva, Acomodacao, Cliente, TipoAcomodacao, ItemEstoque, Frigobar, ItemFrigobar, FormaPagamento, Consumo, VagaEstacionamento, ConfiguracaoHotel, Gasto, GastoCategoria
from .forms import *
import json

# ==============================================================================
# === VIEW DO DASHBOARD                                                      ===
# ==============================================================================
def dashboard_view(request):
    # Visão Geral das Reservas
    total_reservas = Reserva.objects.count()
    reservas_confirmadas = Reserva.objects.filter(status='confirmada').count()
    reservas_checkin = Reserva.objects.filter(status='checkin').count()
    reservas_checkout = Reserva.objects.filter(status='checkout').count()
    reservas_canceladas = Reserva.objects.filter(status='cancelada').count()
    reservas_ativas = Reserva.objects.filter(data_checkin__lte=date.today(), data_checkout__gt=date.today()).order_by('data_checkin')
    
    # Ocupação e Análises
    total_acomodacoes = Acomodacao.objects.count()
    ocupacao_percentual = (reservas_checkin / total_acomodacoes) * 100 if total_acomodacoes > 0 else 0
    
    # Dados para Gráficos (distribuição por status)
    status_reservas = list(Reserva.objects.values('status').annotate(count=Count('status')))
    
    # Informações das Acomodações
    acomodacoes = Acomodacao.objects.all().order_by('numero')
    acomodacoes_disponiveis = acomodacoes.filter(status='disponivel')
    acomodacoes_ocupadas = acomodacoes.filter(status='ocupado')
    acomodacoes_manutencao = acomodacoes.filter(status='manutencao')
    
    # Listas de Reservas para exibição
    reservas_ativas_list = Reserva.objects.filter(status='checkin').order_by('data_checkout')
    proximas_reservas = Reserva.objects.filter(data_checkin__gt=date.today()).order_by('data_checkin')
    
    context = {
        'total_reservas': total_reservas,
        'reservas_confirmadas': reservas_confirmadas,
        'reservas_checkin': reservas_checkin,
        'reservas_checkout': reservas_checkout,
        'reservas_canceladas': reservas_canceladas,
        'taxa_ocupacao': f"{ocupacao_percentual:.2f}",
        'status_reservas': json.dumps(status_reservas),
        'acomodacoes_disponiveis': acomodacoes_disponiveis,
        'acomodacoes_ocupadas': acomodacoes_ocupadas,
        'acomodacoes_manutencao': acomodacoes_manutencao,
        'acomodacoes': acomodacoes,
        'reservas_ativas_list': reservas_ativas_list,
        'proximas_reservas': proximas_reservas,
    }
    return render(request, 'gestao/dashboard_completo.html', context)

# ==============================================================================
# === VIEW DO PAINEL DE GESTÃO DE CLIENTES                                   ===
# ==============================================================================
def cliente_dashboard_view(request):
    clientes = Cliente.objects.all().order_by('nome_completo')
    context = {
        'clientes': clientes,
    }
    return render(request, 'gestao/clientes_dashboard.html', context)

# View para a API de disponibilidade (sem alterações)
def consulta_disponibilidade_view(request):
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')

    if not data_inicio_str or not data_fim_str:
        return JsonResponse({'error': 'Datas de início e fim são obrigatórias.'}, status=400)

    try:
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Formato de data inválido. Use AAAA-MM-DD.'}, status=400)
    
    reservas_conflitantes = Reserva.objects.filter(
        data_checkin__lt=data_fim,
        data_checkout__gt=data_inicio,
        status__in=['confirmada', 'checkin']
    ).values_list('acomodacao_id', flat=True)
    
    acomodacoes_disponiveis = Acomodacao.objects.exclude(id__in=reservas_conflitantes).filter(status='disponivel')
    
    data = [{
        'id': ac.id,
        'numero': ac.numero,
        'tipo': ac.tipo.nome,
        'valor_diaria': f"{ac.valor_diaria:.2f}".replace('.', ',')
    } for ac in acomodacoes_disponiveis]
    
    return JsonResponse(data, safe=False)

# ==============================================================================
# === VIEWS PARA CLIENTES                                                    ===
# ==============================================================================

# LISTAR todos os clientes
def cliente_list_view(request):
    query = request.GET.get('q')
    clientes = Cliente.objects.all().order_by('nome_completo')
    
    if query:
        # Filtra os clientes por nome completo ou CPF
        clientes = clientes.filter(Q(nome_completo__icontains=query) | Q(cpf__icontains=query))
    
    context = {'clientes': clientes, 'query': query}
    return render(request, 'gestao/cliente_list.html', context)

# CRIAR um novo cliente
def cliente_create_view(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('cliente_list')
    else:
        form = ClienteForm()
    
    context = {'form': form, 'is_update': False}
    return render(request, 'gestao/cliente_form.html', context)

# ATUALIZAR (EDITAR) um cliente existente
def cliente_update_view(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('cliente_list')
    else:
        form = ClienteForm(instance=cliente)
    
    context = {
        'form': form,
        'cliente': cliente,
        'is_update': True,
    }
    return render(request, 'gestao/cliente_form.html', context)

# EXCLUIR um cliente (com confirmação)
def cliente_delete_view(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        return redirect('cliente_list')
    context = {'cliente': cliente}
    return render(request, 'gestao/cliente_confirm_delete.html', context)

# ==============================================================================
# === VIEWS PARA A GESTÃO DE TIPOS DE ACOMODAÇÃO E ACOMODAÇÕES               ===
# ==============================================================================

# CRUD para Tipos de Acomodação 
class TipoAcomodacaoListView(ListView):
    model = TipoAcomodacao
    template_name = 'gestao/tipo_acomodacao_list.html'
    context_object_name = 'tipos'

class TipoAcomodacaoCreateView(CreateView):
    model = TipoAcomodacao
    form_class = TipoAcomodacaoForm
    template_name = 'gestao/tipo_acomodacao_form.html'
    success_url = reverse_lazy('tipo_acomodacao_list')

class TipoAcomodacaoUpdateView(UpdateView):
    model = TipoAcomodacao
    form_class = TipoAcomodacaoForm
    template_name = 'gestao/tipo_acomodacao_form.html'
    success_url = reverse_lazy('tipo_acomodacao_list')

class TipoAcomodacaoDeleteView(DeleteView):
    model = TipoAcomodacao
    template_name = 'gestao/tipo_acomodacao_confirm_delete.html'
    success_url = reverse_lazy('tipo_acomodacao_list')
    context_object_name = 'tipo'

# CRUD para Acomodações 
class AcomodacaoListView(ListView):
    model = Acomodacao
    template_name = 'gestao/acomodacao_list.html'
    context_object_name = 'acomodacoes'

class AcomodacaoCreateView(CreateView):
    model = Acomodacao
    form_class = AcomodacaoForm
    template_name = 'gestao/acomodacao_form.html'
    success_url = reverse_lazy('acomodacao_list')

class AcomodacaoUpdateView(UpdateView):
    model = Acomodacao
    form_class = AcomodacaoForm
    template_name = 'gestao/acomodacao_form.html'
    success_url = reverse_lazy('acomodacao_list')

class AcomodacaoDeleteView(DeleteView):
    model = Acomodacao
    template_name = 'gestao/acomodacao_confirm_delete.html'
    success_url = reverse_lazy('acomodacao_list')
    context_object_name = 'acomodacao'

# ==============================================================================
# === VIEWS PARA A GESTÃO DE RESERVAS                                        ===
# ==============================================================================

class ReservaListView(ListView):
    model = Reserva
    template_name = 'gestao/reserva_list.html'
    context_object_name = 'reservas'
    ordering = ['-data_reserva']
    paginate_by = 20 # Opcional: Adiciona paginação para melhor performance

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        checkin_date = self.request.GET.get('checkin_date')
        
        if query:
            # Filtra por nome do cliente, CPF ou número da acomodação
            queryset = queryset.filter(
                Q(cliente__nome_completo__icontains=query) |
                Q(cliente__cpf__icontains=query) |
                Q(acomodacao__numero__icontains=query)
            )
        if checkin_date:
            try:
                # Tenta converter a data de string para um objeto de data
                checkin_date_obj = datetime.strptime(checkin_date, '%Y-%m-%d').date()
                queryset = queryset.filter(data_checkin=checkin_date_obj)
            except ValueError:
                # Ignora se o formato da data for inválido
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona a query de busca ao contexto para manter o campo preenchido
        context['query'] = self.request.GET.get('q', '')
        context['checkin_date'] = self.request.GET.get('checkin_date', '')
        return context

class ReservaDetailView(DetailView):
    model = Reserva
    template_name = 'gestao/reserva_detail.html'
    context_object_name = 'reserva'

class ReservaCreateView(CreateView):
    model = Reserva
    form_class = ReservaForm
    template_name = 'gestao/reserva_form.html'
    success_url = reverse_lazy('reserva_list')

    def form_valid(self, form):
        # Lógica adicional pode ser adicionada aqui se necessário
        return super().form_valid(form)

class ReservaUpdateView(UpdateView):
    model = Reserva
    form_class = ReservaForm
    template_name = 'gestao/reserva_form.html'
    success_url = reverse_lazy('reserva_list')

class ReservaDeleteView(DeleteView):
    model = Reserva
    template_name = 'gestao/reserva_confirm_delete.html'
    success_url = reverse_lazy('reserva_list')
    context_object_name = 'reserva'

# Ações de Check-in e Check-out 
def fazer_checkin(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    if reserva.status == 'confirmada':
        reserva.status = 'checkin'
        reserva.acomodacao.status = 'ocupado'
        
        # Lógica para estacionamento:
        try:
            vaga = reserva.acomodacao.vagaestacionamento
            vaga.disponivel = False
            vaga.save()
            messages.info(request, "Vaga de estacionamento associada foi marcada como ocupada.")
        except VagaEstacionamento.DoesNotExist:
            pass # Nenhuma vaga vinculada, então não faz nada
            
        reserva.save()
        reserva.acomodacao.save()
        messages.success(request, "Check-in realizado com sucesso! A acomodação está agora ocupada.")
    
    return redirect('reserva_detail', pk=reserva.pk)

def fazer_checkout(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    if reserva.status == 'checkin':
        # VERIFICAÇÃO FINANCEIRA: Só permite o check-out se o saldo devedor for zero.
        if reserva.saldo_devedor() > 0:
            messages.error(request, f"Não é possível fazer o check-out. Existe um saldo devedor de R$ {reserva.saldo_devedor():.2f}. Por favor, registe os pagamentos primeiro.")
            return redirect('reserva_detail', pk=reserva.pk)
        
        # Se estiver tudo pago, procede com o check-out.
        reserva.status = 'checkout'
        reserva.acomodacao.status = 'limpeza'  # Define o quarto para limpeza.
        
        # Lógica para estacionamento:
        try:
            vaga = reserva.acomodacao.vagaestacionamento
            vaga.disponivel = True
            vaga.save()
            messages.info(request, "Vaga de estacionamento associada foi marcada como disponível.")
        except VagaEstacionamento.DoesNotExist:
            pass # Nenhuma vaga vinculada, então não faz nada
        
        reserva.save()
        reserva.acomodacao.save()
        messages.success(request, "Check-out realizado com sucesso! A acomodação foi marcada para limpeza.")
    
    return redirect('reserva_detail', pk=reserva.pk)

# NOVA VIEW: Gera e exibe o contrato de check-in para impressão
def imprimir_contrato_checkin(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    context = {
        'reserva': reserva,
        'cliente': reserva.cliente,
        'acomodacao': reserva.acomodacao,
    }
    return render(request, 'gestao/contrato_checkin.html', context)

# ==============================================================================
# === VIEWS PARA A GESTÃO DE ESTOQUE                                         ===
# ==============================================================================

class ItemEstoqueListView(ListView):
    model = ItemEstoque
    template_name = 'gestao/item_estoque_list.html'
    context_object_name = 'itens'
    ordering = ['nome']

class ItemEstoqueCreateView(CreateView):
    model = ItemEstoque
    form_class = ItemEstoqueForm
    template_name = 'gestao/item_estoque_form.html'
    success_url = reverse_lazy('item_estoque_list')

class ItemEstoqueUpdateView(UpdateView):
    model = ItemEstoque
    form_class = ItemEstoqueForm
    template_name = 'gestao/item_estoque_form.html'
    success_url = reverse_lazy('item_estoque_list')

class ItemEstoqueDeleteView(DeleteView):
    model = ItemEstoque
    template_name = 'gestao/item_estoque_confirm_delete.html'
    success_url = reverse_lazy('item_estoque_list')
    context_object_name = 'item'

# ==============================================================================
# === VIEWS PARA FRIGOBAR E CONSUMO                                          ===
# ==============================================================================
def frigobar_detail_view(request, acomodacao_pk):
    """Exibe o conteúdo de um frigobar e permite abastecê-lo."""
    acomodacao = get_object_or_404(Acomodacao, pk=acomodacao_pk)
    # Garante que um frigobar exista para a acomodação, criando-o se necessário.
    frigobar, created = Frigobar.objects.get_or_create(acomodacao=acomodacao)
    form = AbastecerFrigobarForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        item_frigobar = form.save(commit=False)
        item_frigobar.frigobar = frigobar
        
        # Lógica para verificar se o item já existe e somar a quantidade
        item_existente = frigobar.itemfrigobar_set.filter(item=item_frigobar.item).first()
        if item_existente:
            item_existente.quantidade = F('quantidade') + item_frigobar.quantidade
            item_existente.save()
        else:
            item_frigobar.save()
            
        return redirect('frigobar_detail', acomodacao_pk=acomodacao.pk)

    context = {
        'acomodacao': acomodacao,
        'frigobar': frigobar,
        'form': form
    }
    return render(request, 'gestao/frigobar_detail.html', context)

def remover_item_frigobar(request, item_frigobar_pk):
    """Remove um item do frigobar."""
    item_frigobar = get_object_or_404(ItemFrigobar, pk=item_frigobar_pk)
    acomodacao_pk = item_frigobar.frigobar.acomodacao.pk
    if request.method == 'POST':
        item_frigobar.delete()
    return redirect('frigobar_detail', acomodacao_pk=acomodacao_pk)

def consumo_create_view(request, reserva_pk):
    """Regista um novo consumo para uma reserva."""
    reserva = get_object_or_404(Reserva, pk=reserva_pk)
    form = ConsumoForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        consumo = form.save(commit=False)
        consumo.reserva = reserva
        consumo.preco_unitario = consumo.item.preco_venda
        
        # Abater item do estoque
        item_estoque = consumo.item
        if item_estoque.quantidade >= consumo.quantidade:
            item_estoque.quantidade = F('quantidade') - consumo.quantidade
            item_estoque.save()
            consumo.save()
            
            # Atualizar valor do consumo na reserva
            reserva.valor_consumo = F('valor_consumo') + (consumo.quantidade * consumo.preco_unitario)
            reserva.save()
        else:
            # Adicionar uma mensagem de erro (futuramente)
            pass
            
        return redirect('reserva_detail', pk=reserva.pk)

    context = {
        'reserva': reserva,
        'form': form
    }
    return render(request, 'gestao/consumo_form.html', context)

# ==============================================================================
# === VIEWS PARA PAGAMENTOS                                                  ===
# ==============================================================================
class FormaPagamentoListView(ListView):
    model = FormaPagamento
    template_name = 'gestao/forma_pagamento_list.html'
    context_object_name = 'formas_pagamento'

class FormaPagamentoCreateView(CreateView):
    model = FormaPagamento
    form_class = FormaPagamentoForm
    template_name = 'gestao/forma_pagamento_form.html'
    success_url = reverse_lazy('forma_pagamento_list')

class FormaPagamentoUpdateView(UpdateView):
    model = FormaPagamento
    form_class = FormaPagamentoForm
    template_name = 'gestao/forma_pagamento_form.html'
    success_url = reverse_lazy('forma_pagamento_list')

class FormaPagamentoDeleteView(DeleteView):
    model = FormaPagamento
    template_name = 'gestao/forma_pagamento_confirm_delete.html'
    success_url = reverse_lazy('forma_pagamento_list')
    context_object_name = 'forma_pagamento'

def pagamento_create_view(request, reserva_pk):
    """Regista um novo pagamento para uma reserva."""
    reserva = get_object_or_404(Reserva, pk=reserva_pk)
    
    if request.method == 'POST':
        form = PagamentoForm(request.POST)
        if form.is_valid():
            pagamento = form.save(commit=False)
            pagamento.reserva = reserva
            pagamento.save()
            return redirect('reserva_detail', pk=reserva.pk)
    else:
        # Sugere o valor do saldo devedor como valor inicial do pagamento
        form = PagamentoForm(initial={'valor': reserva.saldo_devedor()})

    context = {
        'reserva': reserva,
        'form': form
    }
    return render(request, 'gestao/pagamento_form.html', context)

# ==============================================================================
# === VIEWS PARA ESTACIONAMENTO                                              ===
# ==============================================================================
class VagaEstacionamentoListView(ListView):
    model = VagaEstacionamento
    template_name = 'gestao/vaga_estacionamento_list.html'
    context_object_name = 'vagas'
    ordering = ['numero_vaga']

class VagaEstacionamentoCreateView(CreateView):
    model = VagaEstacionamento
    form_class = VagaEstacionamentoForm
    template_name = 'gestao/vaga_estacionamento_form.html'
    success_url = reverse_lazy('vaga_estacionamento_list')

class VagaEstacionamentoUpdateView(UpdateView):
    model = VagaEstacionamento
    form_class = VagaEstacionamentoForm
    template_name = 'gestao/vaga_estacionamento_form.html'
    success_url = reverse_lazy('vaga_estacionamento_list')

class VagaEstacionamentoDeleteView(DeleteView):
    model = VagaEstacionamento
    template_name = 'gestao/vaga_estacionamento_confirm_delete.html'
    success_url = reverse_lazy('vaga_estacionamento_list')
    context_object_name = 'vaga'

# ==============================================================================
# === VIEWS PARA FUNCIONÁRIOS                                                ===
# ==============================================================================
class FuncionarioListView(ListView):
    model = User
    template_name = 'gestao/funcionario_list.html'
    context_object_name = 'usuarios'
    ordering = ['username']

class FuncionarioCreateView(CreateView):
    model = User
    form_class = FuncionarioCreationForm
    template_name = 'gestao/funcionario_form.html'
    success_url = reverse_lazy('funcionario_list')

class FuncionarioUpdateView(UpdateView):
    model = User
    form_class = FuncionarioUpdateForm
    template_name = 'gestao/funcionario_form.html'
    success_url = reverse_lazy('funcionario_list')

def toggle_funcionario_status(request, pk):
    # Apenas superutilizadores podem ativar/desativar contas
    if not request.user.is_superuser:
        return redirect('funcionario_list') # ou mostrar uma mensagem de erro
        
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        # Impede que um superutilizador desative a sua própria conta
        if request.user.pk != user.pk:
            user.is_active = not user.is_active
            user.save()
    return redirect('funcionario_list')

# ==============================================================================
# === VIEW PARA CONFIGURAÇÕES DO HOTEL                                       ===
# ==============================================================================
def configuracao_hotel_view(request):
    # Usamos o ID=1 como padrão, pois só haverá uma linha de configuração.
    configuracao, created = ConfiguracaoHotel.objects.get_or_create(pk=1)
    
    if request.method == 'POST':
        # request.FILES é necessário para processar o upload do logo
        form = ConfiguracaoHotelForm(request.POST, request.FILES, instance=configuracao)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configurações do hotel salvas com sucesso!')
            return redirect('configuracao_hotel')
    else:
        form = ConfiguracaoHotelForm(instance=configuracao)
        
    return render(request, 'gestao/configuracao_hotel_form.html', {'form': form})

# ==========================================================
# === VIEW PARA O RELATÓRIO DE ACOMODAÇÕES               ===
# ==========================================================
def relatorio_acomodacoes_view(request):
    acomodacoes_ranking = Reserva.objects \
        .values('acomodacao__numero', 'acomodacao__tipo__nome') \
        .annotate(total_reservas=Count('acomodacao')) \
        .order_by('-total_reservas')

    reservas_finalizadas = Reserva.objects.filter(status='checkout').order_by('-data_checkout')

    relatorio_pagamentos = []
    for reserva in reservas_finalizadas:
        pagamentos = reserva.pagamentos.all().order_by('data_pagamento')
        consumos = reserva.consumos.all().order_by('data_consumo')
        
        total_pago = sum(p.valor for p in pagamentos)

        relatorio_pagamentos.append({
            'reserva': reserva,
            'pagamentos': pagamentos,
            'consumos': consumos,
            'total_pago': total_pago,
        })

    context = {
        'acomodacoes_ranking': acomodacoes_ranking,
        'relatorio_pagamentos': relatorio_pagamentos,
    }
    return render(request, 'gestao/relatorio_acomodacoes.html', context)

# ==========================================================
# === VIEW PARA O GESTÃO FINANCEIRA                      ===
# ==========================================================
def financeiro_dashboard_view(request):
    # --- Form de gasto (POST) ---
    if request.method == 'POST':
        gasto_form = GastoForm(request.POST)
        if gasto_form.is_valid():
            gasto_form.save()
            messages.success(request, 'Gasto adicionado com sucesso!')
            return redirect('financeiro')
    else:
        gasto_form = GastoForm()

    # --- Período (GET) ---
    # Default: mês atual
    today = timezone.localdate()
    month_start = today.replace(day=1)
    default_start = request.GET.get('start', month_start.strftime('%Y-%m-%d'))
    default_end = request.GET.get('end', today.strftime('%Y-%m-%d'))

    def parse_date(d):
        try:
            return datetime.strptime(d, '%Y-%m-%d').date()
        except Exception:
            return None

    start_date = parse_date(default_start) or month_start
    end_date = parse_date(default_end) or today
    end_date_plus1 = end_date + timedelta(days=1)  # para filtro __lt em DateTime/Date

    # --- QuerySets base ---
    pagamentos_qs = Pagamento.objects.all()
    gastos_qs = Gasto.objects.all()
    reservas_qs = Reserva.objects.filter(status__in=['checkin', 'checkout'])

    # Filtros por período
    # Pagamentos: data_pagamento (ajuste se for DateTimeField/DateField)
    pagamentos_qs = pagamentos_qs.filter(data_pagamento__gte=start_date, data_pagamento__lt=end_date_plus1)

    # Gastos: data_gasto
    gastos_qs = gastos_qs.filter(data_gasto__gte=start_date, data_gasto__lt=end_date_plus1)

    # Reservas: ajuste para o campo adequado (ex.: data_checkout, data_saida, data_fechamento).
    # >>> TROQUE 'data_checkout' para o seu campo de referência de competência <<<
    # Se você não tiver esse campo, comente o filtro por data e mantenha só o status.
    if hasattr(Reserva, 'data_checkout'):
        reservas_qs = reservas_qs.filter(data_checkout__gte=start_date, data_checkout__lt=end_date_plus1)
    # else: mantenha apenas o filtro por status

    # --- KPIs de Caixa (Entrou/ Saiu) e Competência ---
    total_entradas_caixa = pagamentos_qs.aggregate(
        total=Coalesce(Sum('valor'), Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)))
    )['total'] or 0

    despesas_total_periodo = gastos_qs.aggregate(
        total=Coalesce(
            Sum('valor'),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
        )
    )['total'] or 0

    lucro_caixa_periodo = total_entradas_caixa - despesas_total_periodo

    # Receita por categoria (competência, a partir das reservas)
    receita_quartos = reservas_qs.aggregate(
        total=Coalesce(
            Sum('valor_total_diarias'),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
        )
    )['total'] or 0

    receita_consumo = reservas_qs.aggregate(
        total=Coalesce(
            Sum('valor_consumo'),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
        )
    )['total'] or 0

    receita_outros = reservas_qs.aggregate(
        total=Coalesce(
            Sum('valor_extra'),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
        )
    )['total'] or 0

    total_receita_competencia = receita_quartos + receita_consumo + receita_outros

    # Nº de reservas no período (considerando status fechados)
    reservas_no_periodo = reservas_qs.count()

    # --- Séries para gráficos: Receita vs Despesa por mês ---
    # Baseada em pagamentos (caixa) e gastos (saídas)
    receitas_por_mes = (
        pagamentos_qs
        .annotate(periodo=TruncMonth('data_pagamento'))
        .values('periodo')
        .annotate(total=Coalesce(Sum('valor'), Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))))
        .order_by('periodo')
    )

    despesas_por_mes = (
        gastos_qs
        .annotate(periodo=TruncMonth('data_gasto'))
        .values('periodo')
        .annotate(total=Coalesce(Sum('valor'), Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))))
        .order_by('periodo')
    )

    # Mesclando meses
    mapa_receita = {item['periodo']: float(item['total']) for item in receitas_por_mes}
    mapa_despesa = {item['periodo']: float(item['total']) for item in despesas_por_mes}
    meses = sorted(set(mapa_receita.keys()) | set(mapa_despesa.keys()))

    fluxo_caixa_mensal = []
    for m in meses:
        r = mapa_receita.get(m, 0.0)
        d = mapa_despesa.get(m, 0.0)
        saldo = r - d
        # Label amigável: MM/AAAA
        label = f"{m.month:02d}/{m.year}"
        fluxo_caixa_mensal.append({
            "label": label,
            "receita": r,
            "despesa": d,
            "saldo": saldo,
        })

    # Mês com maior receita (caixa)
    mes_mais_vendido = None
    if fluxo_caixa_mensal:
        mes_mais_vendido = max(fluxo_caixa_mensal, key=lambda x: x['receita'])

    # Receita por categoria (pizza)
    receita_por_categoria = [
        {"label": "Quartos (acomodações)", "valor": float(receita_quartos)},
        {"label": "Consumo (frigobar)", "valor": float(receita_consumo)},
        {"label": "Outros", "valor": float(receita_outros)},
    ]

    context = {
        # Filtros
        "start": start_date,
        "end": end_date,

        # KPIs (caixa e competência)
        "total_entradas_caixa": float(total_entradas_caixa),
        "despesas_total_periodo": float(despesas_total_periodo),
        "lucro_caixa_periodo": float(lucro_caixa_periodo),

        "receita_quartos": float(receita_quartos),
        "receita_consumo": float(receita_consumo),
        "receita_outros": float(receita_outros),
        "total_receita_competencia": float(total_receita_competencia),

        "reservas_no_periodo": reservas_no_periodo,

        # Séries de gráficos (usaremos json_script no template)
        "fluxo_caixa_mensal": fluxo_caixa_mensal,
        "receita_por_categoria": receita_por_categoria,

        # Destaques
        "mes_mais_vendido": mes_mais_vendido,

        # Form de gastos
        "gasto_form": gasto_form,
    }
    return render(request, 'gestao/financeiro_dashboard.html', context)
