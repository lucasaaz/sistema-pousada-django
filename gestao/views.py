# ==============================================================================
# ARQUIVO: gestao/views.py (ATUALIZADO)
# DESCRIÇÃO: Adiciona as views para editar e excluir clientes.
# ==============================================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from datetime import datetime, timedelta, date
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.db.models import F, Count, Q, Sum, DecimalField, Value
from django.core.paginator import Paginator
from django.db.models.functions import ExtractMonth, ExtractYear, Coalesce, TruncMonth
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Reserva, Acomodacao, Cliente, TipoAcomodacao, ItemEstoque, Frigobar, ItemFrigobar, FormaPagamento, Consumo, VagaEstacionamento, ConfiguracaoHotel, Gasto, CategoriaGasto
from .forms import *
import json

# ==============================================================================
# === VIEW DO DASHBOARD                                                      ===
# ==============================================================================
@login_required
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
    acomodacoes_limpeza = acomodacoes.filter(status='limpeza')
    acomodacoes_manutencao = acomodacoes.filter(status='manutencao')
    
    # Listas de Reservas para exibição
    reservas_ativas_list = Reserva.objects.filter(status='checkin').order_by('data_checkout')
    proximas_reservas = Reserva.objects.filter(data_checkin__gte=date.today()).order_by('data_checkin')
    
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
        'acomodacoes_limpeza' : acomodacoes_limpeza,
        'acomodacoes_manutencao': acomodacoes_manutencao,
        'acomodacoes': acomodacoes,
        'reservas_ativas_list': reservas_ativas_list,
        'proximas_reservas': proximas_reservas,
    }
    return render(request, 'gestao/dashboard_completo.html', context)

# ==============================================================================
# === VIEW DO PAINEL DE GESTÃO DE CLIENTES                                   ===
# ==============================================================================
@login_required
def cliente_dashboard_view(request):
    clientes = Cliente.objects.all().order_by('nome_completo')
    context = {
        'clientes': clientes,
    }
    return render(request, 'gestao/clientes_dashboard.html', context)

# View para a API de disponibilidade (sem alterações)
@login_required
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
@login_required
@permission_required('gestao.view_cliente', raise_exception=True)
def cliente_list_view(request):
    # Lógica de busca
    query = request.GET.get('q')
    clientes_list = Cliente.objects.all().order_by('nome_completo')

    if query:
        clientes_list = clientes_list.filter(
            Q(nome_completo__icontains=query) |
            Q(cpf__icontains=query)
        )

    # Lógica de Paginação
    paginator = Paginator(clientes_list, 15)  # Mostra 15 clientes por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj
    }
    return render(request, 'gestao/cliente_list.html', context)

# CRIAR um novo cliente
@login_required
@permission_required('gestao.add_cliente', raise_exception=True)
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
@login_required
@permission_required('gestao.change_cliente', raise_exception=True)
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
@login_required
@permission_required('gestao.delete_cliente', raise_exception=True)
def cliente_delete_view(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        return redirect('cliente_list')
    context = {'cliente': cliente}
    return render(request, 'gestao/cliente_confirm_delete.html', context)

# ==============================================================================
# === VIEWS PARA A GESTÃO DE TIPOS DE ACOMODAÇÃO                             ===
# ==============================================================================

# CRUD para Tipos de Acomodação
class TipoAcomodacaoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_tipoacomodacao'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = TipoAcomodacao
    template_name = 'gestao/tipo_acomodacao_list.html'
    context_object_name = 'page_obj'
    paginate_by = 10

    def get_queryset(self):
        # O annotate(num_acomodacoes=Count(...)) calcula o número de quartos para cada tipo
        # de forma eficiente, evitando múltiplas consultas ao banco de dados.
        queryset = super().get_queryset().annotate(
            num_acomodacoes=Count('acomodacoes')
        ).order_by('nome')
        
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(nome__icontains=query)
        
        return queryset

# ... (Create, Update, Delete para TipoAcomodacao continuam iguais)
class TipoAcomodacaoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'gestao.add_tipoacomodacao'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = TipoAcomodacao
    form_class = TipoAcomodacaoForm
    template_name = 'gestao/tipo_acomodacao_form.html'
    success_url = reverse_lazy('tipo_acomodacao_list')

class TipoAcomodacaoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'gestao.change_tipoacomodacao'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = TipoAcomodacao
    form_class = TipoAcomodacaoForm
    template_name = 'gestao/tipo_acomodacao_form.html'
    success_url = reverse_lazy('tipo_acomodacao_list')

class TipoAcomodacaoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_tipoacomodacao'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = TipoAcomodacao
    template_name = 'gestao/tipo_acomodacao_confirm_delete.html'
    success_url = reverse_lazy('tipo_acomodacao_list')
    context_object_name = 'tipo'

# ==============================================================================
# === VIEWS PARA ACOMODAÇÃO                                                  ===
# ==============================================================================
class AcomodacaoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_acomodacao'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = Acomodacao
    template_name = 'gestao/acomodacao_list.html'
    context_object_name = 'page_obj'  # O template espera 'page_obj' para paginação
    paginate_by = 10  # Define quantos itens por página

    def get_queryset(self):
        # Começa com a query base, otimizando com select_related
        queryset = super().get_queryset().select_related('tipo').order_by('numero')
        
        # Pega os parâmetros do formulário de filtro
        query = self.request.GET.get('q')
        status = self.request.GET.get('status')

        # Aplica o filtro de busca textual, se houver
        if query:
            queryset = queryset.filter(
                Q(numero__icontains=query) | Q(tipo__nome__icontains=query)
            )
        
        # Aplica o filtro de status, se houver
        if status:
            queryset = queryset.filter(status=status)
            
        return queryset

    def get_context_data(self, **kwargs):
        # Pega o contexto existente
        context = super().get_context_data(**kwargs)
        # Adiciona os status_choices ao contexto para usar no dropdown do template
        context['status_choices'] = Acomodacao.STATUS_CHOICES
        return context

# ... (Create, Update, Delete para Acomodacao continuam iguais)
class AcomodacaoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'gestao.add_acomodacao'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = Acomodacao
    form_class = AcomodacaoForm
    template_name = 'gestao/acomodacao_form.html'
    success_url = reverse_lazy('acomodacao_list')

class AcomodacaoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'gestao.change_acomodacao'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = Acomodacao
    form_class = AcomodacaoForm
    template_name = 'gestao/acomodacao_form.html'
    success_url = reverse_lazy('acomodacao_list')

class AcomodacaoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_acomodacao'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = Acomodacao
    template_name = 'gestao/acomodacao_confirm_delete.html'
    success_url = reverse_lazy('acomodacao_list')
    context_object_name = 'acomodacao'

# ==============================================================================
# === VIEWS PARA RESERVAS                                                    ===
# ==============================================================================

class ReservaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_reserva'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = Reserva
    template_name = 'gestao/reserva_list.html'
    context_object_name = 'reservas'
    ordering = ['-data_reserva']
    paginate_by = 20 

    def get_queryset(self):
        # Otimiza a consulta para já buscar os dados relacionados de uma vez
        queryset = super().get_queryset().select_related('cliente', 'acomodacao')

        # Pega o parâmetro de ordenação da URL. O padrão é ordenar pela data de reserva mais recente.
        ordering = self.request.GET.get('ordering', '-data_reserva')
        
        # Uma lista de campos permitidos para ordenação (para segurança)
        allowed_ordering_fields = ['data_checkin', '-data_checkin', 'data_checkout', '-data_checkout']
        if ordering in allowed_ordering_fields:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-data_reserva') # Fallback para o padrão  

        query = self.request.GET.get('q')
        status = self.request.GET.get('status')
        checkin_date = self.request.GET.get('checkin_date')
        
        if query:
            # Filtra por nome do cliente, CPF ou número da acomodação
            queryset = queryset.filter(
                Q(cliente__nome_completo__icontains=query) |
                Q(cliente__cpf__icontains=query) |
                Q(acomodacao__numero__icontains=query)
            )
        
        # Aplica o filtro de status, se houver
        if status:
            queryset = queryset.filter(status=status)

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
        # Passa a ordenação atual para o template, para que saibamos qual link criar
        context['current_ordering'] = self.request.GET.get('ordering', '-data_reserva')
        # Pega as opções de status do modelo e envia para o template
        context['status_choices'] = Reserva.STATUS_CHOICES
        return context

class ReservaDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = 'gestao.view_reserva'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = Reserva
    template_name = 'gestao/reserva_detail.html'
    context_object_name = 'reserva'

class ReservaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'gestao.add_reserva'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = Reserva
    form_class = ReservaForm
    template_name = 'gestao/reserva_form.html'
    success_url = reverse_lazy('reserva_list')

    def form_valid(self, form):
        # Lógica adicional pode ser adicionada aqui se necessário
        return super().form_valid(form)

class ReservaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'gestao.change_reserva'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = Reserva
    form_class = ReservaForm
    template_name = 'gestao/reserva_form.html'
    success_url = reverse_lazy('reserva_list')

class ReservaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_reserva'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = Reserva
    template_name = 'gestao/reserva_confirm_delete.html'
    success_url = reverse_lazy('reserva_list')
    context_object_name = 'reserva'

# Ações de Check-in e Check-out 
@login_required
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

@login_required
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

# Gera e exibe o contrato de check-in para impressão
@login_required
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

class ItemEstoqueListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_itemestoque'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = ItemEstoque
    template_name = 'gestao/item_estoque_list.html'
    context_object_name = 'page_obj'
    paginate_by = 15 # Itens por página

    def get_queryset(self):
        queryset = super().get_queryset().order_by('nome')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(nome__icontains=query)
        return queryset

class ItemEstoqueCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'gestao.add_itemestoque'
    raise_exception = True  # Mostra erro 403 se não tiver permissão
    model = ItemEstoque
    form_class = ItemEstoqueForm
    template_name = 'gestao/item_estoque_form.html'
    success_url = reverse_lazy('item_estoque_list')

class ItemEstoqueUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'gestao.change_itemestoque'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = ItemEstoque
    form_class = ItemEstoqueForm
    template_name = 'gestao/item_estoque_form.html'
    success_url = reverse_lazy('item_estoque_list')

class ItemEstoqueDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_itemestoque'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = ItemEstoque
    template_name = 'gestao/item_estoque_confirm_delete.html'
    success_url = reverse_lazy('item_estoque_list')
    context_object_name = 'item'

# ==============================================================================
# === VIEWS PARA FRIGOBAR E CONSUMO                                          ===
# ==============================================================================
@login_required
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

@login_required
@permission_required('gestao.delete_itemfrigobar', raise_exception=True)
def remover_item_frigobar(request, item_frigobar_pk):
    """Remove um item do frigobar."""
    item_frigobar = get_object_or_404(ItemFrigobar, pk=item_frigobar_pk)
    acomodacao_pk = item_frigobar.frigobar.acomodacao.pk
    if request.method == 'POST':
        item_frigobar.delete()
    return redirect('frigobar_detail', acomodacao_pk=acomodacao_pk)

@login_required
@permission_required('gestao.add_itemfrigobar', raise_exception=True)
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
# === VIEWS PARA FORMA DE PAGAMENTOS                                         ===
# ==============================================================================
class FormaPagamentoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_formapagamento'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = FormaPagamento
    template_name = 'gestao/forma_pagamento_list.html'
    context_object_name = 'page_obj' # Usa page_obj para a paginação
    paginate_by = 10 # Define 10 itens por página
    ordering = ['nome'] # Opcional: Garante a ordem alfabética

class FormaPagamentoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'gestao.add_formapagamento'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = FormaPagamento
    form_class = FormaPagamentoForm
    template_name = 'gestao/forma_pagamento_form.html'
    success_url = reverse_lazy('forma_pagamento_list')

class FormaPagamentoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'gestao.change_formapagamento'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = FormaPagamento
    form_class = FormaPagamentoForm
    template_name = 'gestao/forma_pagamento_form.html'
    success_url = reverse_lazy('forma_pagamento_list')

class FormaPagamentoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_formapagamento'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = FormaPagamento
    template_name = 'gestao/forma_pagamento_confirm_delete.html'
    success_url = reverse_lazy('forma_pagamento_list')
    context_object_name = 'forma_pagamento'

# ==============================================================================
# === VIEWS PARA PAGAMENTOS                                                  ===
# ==============================================================================
@login_required
@permission_required('gestao.add_pagamento', raise_exception=True)
def pagamento_create_view(request, reserva_pk):
    """Regista um novo pagamento para uma reserva."""
    reserva = get_object_or_404(Reserva, pk=reserva_pk)
    
    if request.method == 'POST':
        form = PagamentoForm(request.POST)
        if form.is_valid():
            pagamento = form.save(commit=False)
            pagamento.reserva = reserva
            pagamento.save()
            messages.success(request, f"Pagamento de R$ {pagamento.valor} registado com sucesso!")
            return redirect('reserva_detail', pk=reserva.pk)
    else:
        # Sugere o valor do saldo devedor como valor inicial do pagamento
        form = PagamentoForm(initial={'valor': reserva.saldo_devedor()})

    context = {
        'form': form,
        'reserva': reserva,
    }
    return render(request, 'gestao/pagamento_form.html', context)

class PagamentoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'gestao.change_pagamento'
    raise_exception = True

    model = Pagamento
    form_class = PagamentoForm
    template_name = 'gestao/pagamento_form.html'

    def get_success_url(self):
        # Volta para a página de detalhes da reserva após editar
        return reverse_lazy('reserva_detail', kwargs={'pk': self.object.reserva.pk})

class PagamentoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_pagamento'
    raise_exception = True

    model = Pagamento
    template_name = 'gestao/pagamento_confirm_delete.html'

    def get_success_url(self):
        # Volta para a página de detalhes da reserva após excluir
        return reverse_lazy('reserva_detail', kwargs={'pk': self.object.reserva.pk})

# ==============================================================================
# === VIEWS PARA ESTACIONAMENTO                                              ===
# ==============================================================================
class VagaEstacionamentoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_vagaestacionamento'
    raise_exception = True  # Mostra erro 403 se não tiver permissão

    model = VagaEstacionamento
    template_name = 'gestao/vaga_estacionamento_list.html'
    context_object_name = 'page_obj'
    paginate_by = 10 # Define 10 vagas por página

    def get_queryset(self):
        # Otimiza a consulta para buscar a acomodação vinculada de uma vez
        queryset = super().get_queryset().select_related('acomodacao_vinculada').order_by('numero_vaga')
        
        # Pega os parâmetros do formulário de filtro da URL
        query = self.request.GET.get('q')
        disponivel = self.request.GET.get('disponivel')

        # Aplica o filtro de busca textual, se houver
        if query:
            queryset = queryset.filter(
                Q(numero_vaga__icontains=query) | 
                Q(acomodacao_vinculada__numero__icontains=query)
            )
        
        # Aplica o filtro de disponibilidade, se houver
        if disponivel in ['true', 'false']:
            queryset = queryset.filter(disponivel=(disponivel == 'true'))
            
        return queryset

class VagaEstacionamentoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'gestao.add_vagaestacionamento'
    raise_exception = True  # Mostra erro 403 se não tiver permissão
    
    model = VagaEstacionamento
    form_class = VagaEstacionamentoForm
    template_name = 'gestao/vaga_estacionamento_form.html'
    success_url = reverse_lazy('vaga_estacionamento_list')

class VagaEstacionamentoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'gestao.change_vagaestacionamento'
    raise_exception = True  # Mostra erro 403 se não tiver permissão
    
    model = VagaEstacionamento
    form_class = VagaEstacionamentoForm
    template_name = 'gestao/vaga_estacionamento_form.html'
    success_url = reverse_lazy('vaga_estacionamento_list')

class VagaEstacionamentoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_vagaestacionamento'
    raise_exception = True  # Mostra erro 403 se não tiver permissão
    
    model = VagaEstacionamento
    template_name = 'gestao/vaga_estacionamento_confirm_delete.html'
    success_url = reverse_lazy('vaga_estacionamento_list')
    context_object_name = 'vaga'

# ==============================================================================
# === VIEWS PARA FUNCIONÁRIOS                                                ===
# ==============================================================================
class FuncionarioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_funcionario'
    raise_exception = True  # Mostra erro 403 se não tiver permissão
    
    model = User
    template_name = 'gestao/funcionario_list.html'
    context_object_name = 'usuarios'
    ordering = ['username']

class FuncionarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'gestao.add_vagaestacionamento'
    raise_exception = True  # Mostra erro 403 se não tiver permissão
    
    model = User
    form_class = FuncionarioCreationForm
    template_name = 'gestao/funcionario_form.html'
    success_url = reverse_lazy('funcionario_list')

class FuncionarioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'gestao.change_vagaestacionamento'
    raise_exception = True  # Mostra erro 403 se não tiver permissão
    
    model = User
    form_class = FuncionarioUpdateForm
    template_name = 'gestao/funcionario_form.html'
    success_url = reverse_lazy('funcionario_list')

@login_required
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
# === VIEWS PARA CONFIGURAÇÕES DO HOTEL                                      ===
# ==============================================================================
@login_required
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
# === VIEWS PARA O RELATÓRIO DE ACOMODAÇÕES              ===
# ==========================================================
@login_required
def relatorio_acomodacoes_view(request):
    # --- 1. Lógica para o Ranking de Acomodações (Gráfico) ---
    
    # Filtra apenas por reservas concluídas ('checkout') para um ranking mais preciso
    acomodacoes_ranking = Reserva.objects.filter(status='checkout') \
        .values('acomodacao__numero') \
        .annotate(total_reservas=Count('id')) \
        .order_by('-total_reservas')[:10]  # Limita aos 10 primeiros

    # Prepara os dados no formato que o Chart.js espera
    ranking_labels = [f"Quarto {item['acomodacao__numero']}" for item in acomodacoes_ranking]
    ranking_data = [item['total_reservas'] for item in acomodacoes_ranking]
    
    # Converte os dados para uma string JSON segura para ser usada no template
    ranking_data_json = json.dumps({
        'labels': ranking_labels,
        'data': ranking_data,
    })

    # --- 2. Lógica para o Extrato de Pagamentos ---

    # Query base: todas as reservas com check-out, ordenadas pela data mais recente
    reservas_finalizadas = Reserva.objects.filter(status='checkout').order_by('-data_checkout')

    # Pega os parâmetros de filtro da URL
    query = request.GET.get('q')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Aplica filtro de busca textual
    if query:
        reservas_finalizadas = reservas_finalizadas.filter(
            Q(cliente__nome_completo__icontains=query) | Q(cliente__cpf__icontains=query)
        )
        
    # Aplica filtro de data de início
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        reservas_finalizadas = reservas_finalizadas.filter(data_checkout__gte=start_date)
        
    # Aplica filtro de data de fim
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        reservas_finalizadas = reservas_finalizadas.filter(data_checkout__lte=end_date)
        
    # Monta a estrutura de dados completa para o extrato
    relatorio_pagamentos = []
    for reserva in reservas_finalizadas:
        pagamentos = reserva.pagamentos.all()
        consumos = reserva.consumos.all()
        total_pago = sum(p.valor for p in pagamentos)
        
        relatorio_pagamentos.append({
            'reserva': reserva,
            'pagamentos': pagamentos,
            'consumos': consumos,
            'total_pago': total_pago,
        })
    
    # --- 3. Lógica de Paginação ---

    # Pagina a lista de extratos já montada
    paginator = Paginator(relatorio_pagamentos, 5)  # Mostra 5 extratos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- 4. Contexto para o Template ---

    context = {
        'ranking_data_json': ranking_data_json, # Dados do gráfico
        'page_obj': page_obj,                   # Dados paginados para o extrato
    }
    return render(request, 'gestao/relatorio_acomodacoes.html', context)

# ==========================================================
# === VIEWS PARA O GESTÃO FINANCEIRA                     ===
# ==========================================================
@login_required
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

    def normalize_date(dt):
        """Converte datetime ou date para date"""
        if isinstance(dt, datetime):
            return dt.date()  # remove hora
        return dt

    # Mesclando meses
    mapa_receita = {item['periodo']: float(item['total']) for item in receitas_por_mes}
    mapa_despesa = {item['periodo']: float(item['total']) for item in despesas_por_mes}
    meses = sorted(
        set(normalize_date(k) for k in mapa_receita.keys()) |
        set(normalize_date(k) for k in mapa_despesa.keys())
    )

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

    # ESTA CONSULTA: busca os 5 gastos mais recentes
    gastos_recentes = Gasto.objects.order_by('-data_gasto')[:5]

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

        # 
        'gastos_recentes': gastos_recentes,
    }

    return render(request, 'gestao/financeiro_dashboard.html', context)

# ==========================================================
# === VIEWS PARA GASTO                                   ===
# ==========================================================

class GastoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'gestao.change_gasto'
    raise_exception = True

    model = Gasto
    form_class = GastoForm
    template_name = 'gestao/gasto_form.html'
    success_url = reverse_lazy('financeiro') # Volta para o painel financeiro

class GastoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_gasto'
    raise_exception = True
    
    model = Gasto
    template_name = 'gestao/gasto_confirm_delete.html'
    success_url = reverse_lazy('financeiro') # Volta para o painel financeiro

# ==========================================================
# === VIEWS PARA CATEGORIAS DE GASTO                     ===
# ==========================================================

class CategoriaGastoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_categoriagasto'
    raise_exception = True  # Mostra erro 403 se não tiver permissão
    
    model = CategoriaGasto
    template_name = 'gestao/categoria_gasto_list.html'
    context_object_name = 'page_obj'
    paginate_by = 10
    ordering = ['nome']

class CategoriaGastoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'gestao.add_categoriagasto'
    raise_exception = True  # Mostra erro 403 se não tiver permissão
    
    model = CategoriaGasto
    form_class = CategoriaGastoForm
    template_name = 'gestao/categoria_gasto_form.html'
    success_url = reverse_lazy('categoria_gasto_list')

class CategoriaGastoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'gestao.change_categoriagasto'
    raise_exception = True  # Mostra erro 403 se não tiver permissão
    
    model = CategoriaGasto
    form_class = CategoriaGastoForm
    template_name = 'gestao/categoria_gasto_form.html'
    success_url = reverse_lazy('categoria_gasto_list')

class CategoriaGastoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_categoriagasto'
    raise_exception = True  # Mostra erro 403 se não tiver permissão
    
    model = CategoriaGasto
    template_name = 'gestao/categoria_gasto_confirm_delete.html'
    success_url = reverse_lazy('categoria_gasto_list')