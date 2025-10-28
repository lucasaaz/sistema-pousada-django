# ==============================================================================
# ARQUIVO: gestao/views.py (ATUALIZADO)
# DESCRIÇÃO: Adiciona as views para editar e excluir clientes.
# ==============================================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.urls import reverse
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta, date
from django.http import FileResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views.decorators.http import require_POST
from django.db.models import F, Count, Q, Sum, DecimalField, Value, Avg, Case, When
from django.core.paginator import Paginator
from django.db.models.functions import Coalesce, TruncMonth, Lower
from django.db import models
from django.contrib.auth.models import User
from django.contrib import messages
from decimal import Decimal
from .utils import calcular_tarifa_completa
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging
from django.http import HttpResponseBadRequest
from django.views.decorators.http import require_POST
import boto3
from django.http import HttpResponse
import os
import uuid
from botocore.exceptions import ClientError
# logger for this module
logger = logging.getLogger(__name__)
from .models import Reserva, Acomodacao, Cliente, TipoAcomodacao, ItemEstoque, Frigobar, ItemFrigobar, FormaPagamento, Consumo, VagaEstacionamento, ConfiguracaoHotel, Gasto, CategoriaGasto, PeriodoTarifario, GrupoReserva, Espaco, Evento, CustoEvento, Pagamento
from .forms import *
from .utils import upload_file_to_s3
import json
import logging

# ==============================================================================
# === VIEW DO DASHBOARD                                                      ===
# ==============================================================================
@login_required
def dashboard_view(request):
    # Visão Geral das Reservas
    total_reservas = Reserva.objects.count()
    pre_reservas = Reserva.objects.filter(status='pre_reserva').count()
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
    proximas_reservas = Reserva.objects.filter(status='confirmada', data_checkin__gte=date.today()).order_by('data_checkin')
    proximas_prereservas = Reserva.objects.filter(status='pre_reserva').order_by('data_checkin')
    # proximas_reservas = Reserva.objects.filter(data_checkin__gte=date.today()).order_by('data_checkin')
  
    context = {
        'total_reservas': total_reservas,
        'pre_reservas': pre_reservas,
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
        'proximas_prereservas': proximas_prereservas,
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
            cliente = form.save(commit=False)
            
            # Pega a URL final da foto que o JavaScript colocou no campo oculto
            foto_url = request.POST.get('foto_dataurl')
            if foto_url:
                cliente.foto = foto_url
            
            cliente.save()
            messages.success(request, 'Cliente criadoo com sucesso!')

            action = request.POST.get('action')
            if action == 'save_and_reserve':
                reserva_url = f"{reverse('reserva_add')}?cliente_id={cliente.pk}"
                return redirect(reserva_url)
            return redirect('cliente_list')
    else:
        form = ClienteForm()
    
    return render(request, 'gestao/cliente_form.html', {'form': form})

# EDITAR um novo cliente
@login_required
@permission_required('gestao.change_cliente', raise_exception=True)
def cliente_update_view(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            nome_cliente = cliente.nome_completo
            cliente = form.save(commit=False)

            # Pega a URL da nova foto (se houver)
            foto_url = request.POST.get('foto_dataurl')
            if foto_url:
                cliente.foto = foto_url

            cliente.save()
            messages.success(request, f"Cliente '{nome_cliente}' foi atualizado com sucesso!")
            return redirect('cliente_list')
    else:
        form = ClienteForm(instance=cliente)

    context = {
        'form': form,
        'cliente': cliente,
        'object': cliente,
        'nascimento_para_js': cliente.data_nascimento.strftime('%Y-%m-%d') if cliente.data_nascimento else ''
    }
    return render(request, 'gestao/cliente_form.html', context)

# EXCLUIR um cliente (com confirmação)
@login_required
@permission_required('gestao.delete_cliente', raise_exception=True)
def cliente_delete_view(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        nome_cliente = cliente.nome_completo
        cliente.delete()
        messages.success(request, f"Cliente '{nome_cliente}' foi deletado com sucesso!")
        return redirect('cliente_list')
    context = {'cliente': cliente}
    return render(request, 'gestao/cliente_confirm_delete.html', context)

# API para verificar duplicidade de CPF ou e-mail
@login_required
def verificar_duplicidade_view(request):
    # Pega os dados que o JavaScript vai enviar
    field = request.GET.get('field')
    value = request.GET.get('value')
    cliente_id = request.GET.get('cliente_id') # ID do cliente sendo editado (se houver)

    # Verifica se os parâmetros necessários foram enviados
    if not field or not value:
        return JsonResponse({'is_taken': False})

    # Monta a query para buscar no banco
    query = {f'{field}__iexact': value}
    check = Cliente.objects.filter(**query)

    # Se estivermos editando um cliente, excluímos ele mesmo da busca
    if cliente_id:
        check = check.exclude(pk=cliente_id)

    # Se 'check.exists()' for True, significa que o valor já foi pego
    return JsonResponse({'is_taken': check.exists()})

@login_required
def gerar_url_upload_view(request):
    bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
    
    # Gera um nome de arquivo único para evitar conflitos
    # Ex: media/clientes_fotos/a8f5b2c1-3d7e-4b1f-8c7c-1b2d7e4b5a6c.jpg
    object_name = f"media/clientes_fotos/{uuid.uuid4()}.jpg"

    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_S3_REGION_NAME'),
        config=boto3.session.Config(signature_version='s3v4')
    )
    
    try:
        # Gera a URL pré-assinada que permite um 'PUT' request
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': bucket_name, 'Key': object_name, 'ContentType': 'image/jpeg'},
            ExpiresIn=3600  # A URL expira em 1 hora
        )
        
        # A URL final e permanente do arquivo após o upload
        final_url = f"https://{bucket_name}.s3.amazonaws.com/{object_name}"

        return JsonResponse({'presigned_url': presigned_url, 'final_url': final_url})

    except ClientError as e:
        return JsonResponse({'error': str(e)}, status=400)
    
#===============================================================================
# === VIEW PARA CÁLCULO DE TARIFA VIA API                                    ===
#===============================================================================

@login_required
def calcular_tarifa_view(request):
    try:
        # 1. Coleta e valida os dados da request
        acomodacao_id = request.GET.get('acomodacao_id')
        cliente_id = request.GET.get('cliente_id')
        checkin_str = request.GET.get('checkin')
        checkout_str = request.GET.get('checkout')
        
        if not all([acomodacao_id, cliente_id, checkin_str, checkout_str]):
            return JsonResponse({'error': 'Parâmetros faltando'}, status=400)

        num_adultos = int(request.GET.get('num_adultos', 0))
        num_criancas_12 = int(request.GET.get('num_criancas_12', 0))
        num_pessoas = num_adultos + num_criancas_12
        
        # 2. Converte e busca objetos no banco
        acomodacao = Acomodacao.objects.select_related('tipo').get(pk=acomodacao_id)
        cliente = Cliente.objects.get(pk=cliente_id)
        checkin_date = datetime.fromisoformat(checkin_str.replace('T', ' '))
        checkout_date = datetime.fromisoformat(checkout_str.replace('T', ' '))

        # 3. Validação de Capacidade
        if num_pessoas > acomodacao.capacidade:
            return JsonResponse({'error': f'Capacidade excedida ({acomodacao.capacidade} pessoas).'}, status=400)

        # 4. Cálculo da Tarifa Base
        chave_preco = acomodacao.tipo.chave_de_preco
        valor_total, detalhamento_base = calcular_tarifa_completa(
            chave_de_preco=chave_preco,
            checkin_date=checkin_date,
            checkout_date=checkout_date,
            num_adultos=num_adultos,
            num_criancas_12=num_criancas_12
        )
        detalhamento = detalhamento_base or []

        # --- LÓGICA DE PRIORIDADE CORRIGIDA ---
        # 5. Busca por Períodos Tarifários aplicáveis
        periodos_aplicaveis = PeriodoTarifario.objects.filter(
            ativo=True,
            data_inicio__lte=checkout_date.date(),
            data_fim__gte=checkin_date.date()
        )

        # 6. Aplica a regra com a maior prioridade
        periodo_final = None
        # Prioridade 1: Regra específica para o Cliente
        regra_cliente = periodos_aplicaveis.filter(clientes=cliente).order_by('-percentual_ajuste').first()
        if regra_cliente:
            periodo_final = regra_cliente
        else:
            # Prioridade 2: Regra específica para a Acomodação
            regra_acomodacao = periodos_aplicaveis.filter(acomodacoes=acomodacao).order_by('-percentual_ajuste').first()
            if regra_acomodacao:
                periodo_final = regra_acomodacao
            else:
                # Prioridade 3: Regra Geral
                regra_geral = periodos_aplicaveis.filter(clientes__isnull=True, acomodacoes__isnull=True).order_by('-percentual_ajuste').first()
                if regra_geral:
                    periodo_final = regra_geral

        # 7. Se uma regra foi encontrada, aplica o ajuste
        if periodo_final:
            ajuste = periodo_final.percentual_ajuste
            valor_total = valor_total * (1 + (ajuste / Decimal('100.0')))
            
            sinal = "+" if ajuste > 0 else ""
            detalhamento.append(f"Ajuste de {sinal}{ajuste}% ({periodo_final.nome})")

        return JsonResponse({
            'valor_total': f'{valor_total:.2f}',
            'detalhamento': detalhamento
        })

    except Exception as e:
        print(f"ERRO AO CALCULAR TARIFA: {e}")
        return JsonResponse({'error': str(e)}, status=400)

# ==============================================================================
# === VIEWS PARA A GESTÃO DE TIPOS DE ACOMODAÇÃO                             ===
# ==============================================================================

# CRUD para Tipos de Acomodação
class TipoAcomodacaoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_tipoacomodacao'
    raise_exception = True 

    model = TipoAcomodacao
    template_name = 'gestao/tipo_acomodacao_list.html'
    context_object_name = 'tipo_acomodacao'
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
class TipoAcomodacaoCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'gestao.add_tipoacomodacao'
    raise_exception = True 

    model = TipoAcomodacao
    form_class = TipoAcomodacaoForm
    template_name = 'gestao/tipo_acomodacao_form.html'
    success_url = reverse_lazy('tipo_acomodacao_list')
    success_message = "Tipo de Acomodação '%(nome)s' criada com sucesso!"

class TipoAcomodacaoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_tipoacomodacao'
    raise_exception = True 

    model = TipoAcomodacao
    form_class = TipoAcomodacaoForm
    template_name = 'gestao/tipo_acomodacao_form.html'
    success_url = reverse_lazy('tipo_acomodacao_list')
    success_message = "Tipo de Acomodação '%(nome)s' atualizada com sucesso!"

class TipoAcomodacaoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_tipoacomodacao'
    raise_exception = True 

    model = TipoAcomodacao
    template_name = 'gestao/tipo_acomodacao_confirm_delete.html'
    success_url = reverse_lazy('tipo_acomodacao_list')
    context_object_name = 'tipo'

    def form_valid(self, form):
        # Adiciona a mensagem de sucesso antes de o objeto ser deletado
        messages.success(self.request, f"Tipo de Acomodação '{self.object}' foi excluída com sucesso.")
        return super().form_valid(form)

# ==============================================================================
# === VIEWS PARA ACOMODAÇÃO                                                  ===
# ==============================================================================
class AcomodacaoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_acomodacao'
    raise_exception = True 

    model = Acomodacao
    template_name = 'gestao/acomodacao_list.html'
    context_object_name = 'acomodacoes' 
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
class AcomodacaoCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'gestao.add_acomodacao'
    raise_exception = True 

    model = Acomodacao
    form_class = AcomodacaoForm
    template_name = 'gestao/acomodacao_form.html'
    success_url = reverse_lazy('acomodacao_list')
    success_message = "Acomodação Nº %(numero)s criada com sucesso!"

class AcomodacaoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_acomodacao'
    raise_exception = True 

    model = Acomodacao
    form_class = AcomodacaoForm
    template_name = 'gestao/acomodacao_form.html'
    success_url = reverse_lazy('acomodacao_list')
    success_message = "Acomodação Nº %(numero)s atualizada com sucesso!"

class AcomodacaoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_acomodacao'
    raise_exception = True 

    model = Acomodacao
    template_name = 'gestao/acomodacao_confirm_delete.html'
    success_url = reverse_lazy('acomodacao_list')
    context_object_name = 'acomodacao'

    def form_valid(self, form):
        # Adiciona a mensagem de sucesso antes de o objeto ser deletado
        messages.success(self.request, f"Acomodação '{self.object}' foi excluída com sucesso.")
        return super().form_valid(form)

# ==============================================================================
# === VIEWS PARA RESERVAS                                                    ===
# ==============================================================================

class ReservaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_reserva'
    raise_exception = True 

    model = Reserva
    template_name = 'gestao/reserva_list.html'
    context_object_name = 'reservas'
    ordering = ['-data_reserva']
    paginate_by = 10  

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
        checkin_inicio = self.request.GET.get('checkin_inicio')
        checkin_fim = self.request.GET.get('checkin_fim') 
        
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

        # Se a data de início for fornecida, filtra a partir dela
        if checkin_inicio:
            try:
                data_inicio_obj = datetime.strptime(checkin_inicio, '%Y-%m-%d').date()
                queryset = queryset.filter(data_checkin__gte=data_inicio_obj)
            except (ValueError, TypeError):
                pass # Ignora data inválida

        # Se a data de fim for fornecida, filtra até ela
        if checkin_fim:
            try:
                data_fim_obj = datetime.strptime(checkin_fim, '%Y-%m-%d').date()
                queryset = queryset.filter(data_checkin__lte=data_fim_obj)
            except (ValueError, TypeError):
                pass # Ignora data inválida
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona a query de busca ao contexto para manter o campo preenchido
        context['query'] = self.request.GET.get('q', '')
        # Adiciona as datas para manter os campos preenchidos
        context['checkin_inicio'] = self.request.GET.get('checkin_inicio', '')
        context['checkin_fim'] = self.request.GET.get('checkin_fim', '')
        # Passa a ordenação atual para o template, para que saibamos qual link criar
        context['current_ordering'] = self.request.GET.get('ordering', '-data_reserva')
        # Pega as opções de status do modelo e envia para o template
        context['status_choices'] = Reserva.STATUS_CHOICES
        return context

class ReservaDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = 'gestao.view_reserva'
    raise_exception = True  

    model = Reserva
    template_name = 'gestao/reserva_detail.html'
    context_object_name = 'reserva'

class ReservaCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'gestao.add_reserva'
    raise_exception = True

    model = Reserva
    form_class = ReservaForm
    template_name = 'gestao/reserva_form.html'
    success_url = reverse_lazy('reserva_list')
    success_message = "Reserva para o cliente '%(cliente)s' criada com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        cliente_id = request.GET.get('cliente_id')
        grupo_id = request.GET.get('grupo_id')

        self.cliente_pre_selecionado = None
        self.grupo_pre_selecionado = None

        # Se vier um grupo_id, pré-seleciona o cliente responsável do grupo
        if grupo_id:
            try:
                self.grupo_pre_selecionado = GrupoReserva.objects.get(pk=grupo_id)
                # 👇 IMPORTANTE: Pré-seleciona o cliente responsável do grupo
                self.cliente_pre_selecionado = self.grupo_pre_selecionado.cliente_responsavel
            except GrupoReserva.DoesNotExist:
                pass

        # Se vier um cliente_id específico, sobrescreve
        if cliente_id:
            try:
                self.cliente_pre_selecionado = Cliente.objects.get(pk=cliente_id)
            except Cliente.DoesNotExist:
                pass

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()

        # Pré-preenche o cliente
        if self.cliente_pre_selecionado:
            cliente = self.cliente_pre_selecionado
            initial['cliente'] = cliente.pk
            initial['cliente_busca'] = cliente.nome_completo

        # 👇 CRÍTICO: Pré-preenche o grupo no campo hidden
        if self.grupo_pre_selecionado:
            initial['grupo'] = self.grupo_pre_selecionado.pk

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Adiciona a foto do cliente ao contexto
        if self.cliente_pre_selecionado and self.cliente_pre_selecionado.foto:
            context['cliente_foto_url'] = self.cliente_pre_selecionado.foto.url

        # Adiciona o grupo ao contexto para exibir no template
        if self.grupo_pre_selecionado:
            context['grupo_reserva'] = self.grupo_pre_selecionado

        return context
    
    def form_valid(self, form):
        # Salva a reserva
        response = super().form_valid(form)
        reserva = self.object # O objeto recém-criado

        # Verifica se a reserva pertence a um grupo
        if reserva.grupo:
            messages.success(self.request, f"Acomodação '{reserva.acomodacao.nome_display}' adicionada ao grupo com sucesso!")
            return redirect('grupo_reserva_detail', pk=reserva.grupo.pk)
        
        # Se não, continua com o comportamento padrão (usa o success_url e success_message da classe)
        return response

class ReservaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_reserva'
    raise_exception = True

    model = Reserva
    form_class = ReservaForm
    template_name = 'gestao/reserva_form.html'
    success_url = reverse_lazy('reserva_list')
    success_message = "Reserva para o cliente '%(cliente)s' atualizada com sucesso!"

    def get_initial(self):
        """
        Pré-popula o formulário com dados customizados. Esta é a forma correta.
        """
        initial = super().get_initial()
        reserva = self.get_object()
        
        if reserva.cliente:
            initial['cliente_busca'] = reserva.cliente.nome_completo
        
        # O Django cuidará do preenchimento das datas a partir da instância,
        # mas adicionamos explicitamente para garantir.
        initial['data_checkin'] = reserva.data_checkin
        initial['data_checkout'] = reserva.data_checkout
            
        return initial

    # ADICIONE ESTE MÉTODO PARA ENVIAR A FOTO
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reserva = self.get_object()
        
        # Se a reserva tem um cliente e esse cliente tem uma foto, envia a URL
        if reserva.cliente and reserva.cliente.foto:
            # cliente.foto é um URLField (string) - não usar .url
            context['cliente_foto_url'] = reserva.cliente.foto
        
        if reserva.data_checkin:
            context['checkin_para_js'] = reserva.data_checkin.strftime('%Y-%m-%dT%H:%M')
        if reserva.data_checkout:
            context['checkout_para_js'] = reserva.data_checkout.strftime('%Y-%m-%dT%H:%M')
              
        return context

class ReservaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_reserva'
    raise_exception = True  

    model = Reserva
    template_name = 'gestao/reserva_confirm_delete.html'
    success_url = reverse_lazy('reserva_list')
    context_object_name = 'reserva'

    def form_valid(self, form):
        # Adiciona a mensagem de sucesso antes de o objeto ser deletado
        messages.success(self.request, f"A reserva '{self.object.pk}' do cliente '{self.object.cliente}' foi excluída com sucesso.")
        return super().form_valid(form)

@login_required
def cancelar_reserva_status_view(request, pk):
    # Busca a reserva ou retorna um erro 404
    reserva = get_object_or_404(Reserva, pk=pk)
    
    # Altera o status para 'cancelada'
    reserva.status = 'cancelada'
    reserva.save()
    
    # Adiciona uma mensagem de sucesso para o usuário
    messages.success(request, f"A Reserva {reserva.pk} foi cancelada com sucesso.")
    
    # Redireciona de volta para a lista de reservas
    return redirect('reserva_list')

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

def buscar_clientes_view(request):
    # Pega o termo de busca que o JavaScript vai enviar via GET
    term = request.GET.get('term', '')
    
    # Filtra os clientes cujo nome completo OU CPF contenham o termo de busca
    # Usamos 'icontains' para busca case-insensitive (não diferencia maiúsculas/minúsculas)
    clientes = Cliente.objects.filter(
        Q(nome_completo__icontains=term) | Q(cpf__icontains=term)
    )[:10]  # Limita a 10 resultados para não sobrecarregar

    # Prepara os resultados no formato que o JavaScript vai usar
    results = []
    for cliente in clientes:
        results.append({
            'id': cliente.id,
            'text': f"{cliente.nome_completo}" # Mostra nome
        })

    return JsonResponse(results, safe=False)


# Debug endpoint: verifica o que foi recebido em um POST de upload (arquivo + dataurl)
@login_required
@require_POST
def upload_debug_view(request):
    """Retorna um JSON descrevendo os campos e arquivos recebidos na requisição POST.
    Útil para depurar se o cliente enviou `foto` (File) ou `foto_dataurl`.
    """
    try:
        keys = list(request.POST.keys())
        file_keys = list(request.FILES.keys())

        result = {
            'post_keys': keys,
            'file_keys': file_keys,
            'foto_received': False,
            'foto_name': None,
            'foto_size': None,
            'foto_content_type': None,
            'foto_dataurl_present': False,
            'foto_dataurl_length': 0,
            'foto_dataurl_head': None,
        }

        if 'foto' in request.FILES:
            f = request.FILES['foto']
            result['foto_received'] = True
            result['foto_name'] = getattr(f, 'name', None)
            try:
                result['foto_size'] = f.size
            except Exception:
                result['foto_size'] = None
            result['foto_content_type'] = getattr(f, 'content_type', None)

        foto_dataurl = request.POST.get('foto_dataurl')
        if foto_dataurl:
            result['foto_dataurl_present'] = True
            result['foto_dataurl_length'] = len(foto_dataurl)
            result['foto_dataurl_head'] = foto_dataurl[:256]

        return JsonResponse(result)
    except Exception as e:
        logging.exception('upload_debug_view failed: %s', e)
        return HttpResponseBadRequest('failed')


# =============================================================================
# === View para enviar e-mail com o contrato de check-in da reserva         ===
# =============================================================================   
@login_required
def enviar_email_reserva_view(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    destinatario_email = reserva.cliente.email
    
    if not destinatario_email:
        messages.error(request, "Este cliente não possui um e-mail cadastrado.")
        return redirect('reserva_detail', pk=reserva.pk)

    try:
        contexto_email = {
        'reserva': reserva,
        'cliente': reserva.cliente,
        'acomodacao': reserva.acomodacao,
    }
        html_content = render_to_string('gestao/contrato_checkin.html', contexto_email)
        
        assunto = f"Confirmação da sua Reserva na Pousada dos Azevedos - Reserva #{reserva.pk}"
        
        # Usamos o DEFAULT_FROM_EMAIL que está no settings.py
        remetente = settings.DEFAULT_FROM_EMAIL
        
        send_mail(
            assunto,
            'Aqui está o resumo da sua reserva.',
            remetente,
            [destinatario_email],
            fail_silently=False,
            html_message=html_content
        )
        
        messages.success(request, f"E-mail enviado com sucesso para {destinatario_email}!")

    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao enviar o e-mail: {e}")

    return redirect('reserva_detail', pk=reserva.pk)

# ==============================================================================
# === View para listar e fazer upload de arquivos relacionados a uma reserva ===
# ============================================================================== 

@login_required
def arquivos_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)

    if request.method == "POST":
        form = ArquivoReservaForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = form.save(commit=False)
            arquivo.reserva = reserva
            arquivo.save()
            return redirect("reserva_list")  # ou redirect de volta para a mesma página se preferir
    else:
        form = ArquivoReservaForm()

    # Usando related_name definido no model
    arquivos = reserva.arquivos.all()

    return render(request, "gestao/arquivos_reserva.html", {
        "reserva": reserva,
        "form": form,
        "arquivos": arquivos,
    })


def abrir_arquivo(request, arquivo_id):
    arquivo = get_object_or_404(ArquivoReserva, pk=arquivo_id)
    return FileResponse(arquivo.arquivo.open("rb"), as_attachment=False)

# ==============================================================================
# === View para Reserva em Grupos                                            ===
# ==============================================================================
class GrupoReservaDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = 'gestao.view_gruporeserva'
    raise_exception = True 

    model = GrupoReserva
    template_name = 'gestao/grupo_reserva_detail.html'
    context_object_name = 'grupo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        grupo = self.get_object()
        
        # Busca todas as reservas associadas a este grupo
        reservas_do_grupo = grupo.reservas.all().select_related('cliente', 'acomodacao')
        context['reservas_do_grupo'] = reservas_do_grupo
        
        # --- CÁLCULO DO RESUMO FINANCEIRO CONSOLIDADO ---
        total_diarias = sum(reserva.valor_total_diarias for reserva in reservas_do_grupo)
        total_consumo = sum(reserva.valor_consumo for reserva in reservas_do_grupo)
        
        # Busca o total de pagamentos de todas as reservas do grupo
        total_pago = Pagamento.objects.filter(reserva__in=reservas_do_grupo).aggregate(Sum('valor'))['valor__sum'] or 0
        
        total_a_pagar = total_diarias + total_consumo
        saldo_devedor = total_a_pagar - total_pago

        context['resumo_financeiro'] = {
            'total_diarias': total_diarias,
            'total_consumo': total_consumo,
            'total_a_pagar': total_a_pagar,
            'total_pago': total_pago,
            'saldo_devedor': saldo_devedor,
        }
        
        return context
    
class GrupoReservaListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_gruporeserva'
    raise_exception = True 

    model = GrupoReserva
    template_name = 'gestao/grupo_reserva_list.html'
    context_object_name = 'grupos'
    paginate_by = 15

class GrupoReservaCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'gestao.add_gruporeserva'
    raise_exception = True 

    model = GrupoReserva
    form_class = GrupoReservaForm
    template_name = 'gestao/grupo_reserva_form.html'
    success_url = reverse_lazy('grupo_reserva_list')
    success_message = "Grupo de Reserva '%(nome_grupo)s' criado com sucesso!"

class GrupoReservaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_gruporeserva'
    raise_exception = True 

    model = GrupoReserva
    form_class = GrupoReservaForm
    template_name = 'gestao/grupo_reserva_form.html' # Reutiliza o mesmo template do 'adicionar'
    success_url = reverse_lazy('grupo_reserva_list')
    success_message = "Grupo '%(nome_grupo)s' atualizado com sucesso!"

class GrupoReservaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_gruporeserva'
    raise_exception = True 

    model = GrupoReserva
    template_name = 'gestao/grupo_reserva_confirm_delete.html'
    success_url = reverse_lazy('grupo_reserva_list')
    success_message = "Grupo de Reserva '%(nome_grupo)s' foi excluído com sucesso."

    def form_valid(self, form):
        # Adiciona a mensagem de sucesso antes de o objeto ser deletado
        messages.success(self.request, f"Grupo de Reserva '{self.object}' foi excluído com sucesso.")
        return super().form_valid(form)

# ==============================================================================
# === View para o calendário de reservas                                     ===
# ==============================================================================

class CalendarioReservasView(LoginRequiredMixin, TemplateView):
    template_name = 'gestao/calendario.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Calendário de Reservas'
        context['status_choices'] = Reserva.STATUS_CHOICES
        
        # --- LÓGICA DE CORES ADICIONADA AQUI ---
        # Cria um mapa de status para cores
        status_colors = {}
        reserva_temp = Reserva()
        for status_key, status_value in Reserva.STATUS_CHOICES:
            reserva_temp.status = status_key
            status_colors[status_key] = reserva_temp.status_color
        
        context['status_colors'] = status_colors
        
        return context
    
@login_required
def reservas_calendario_api(request):
    
    # --- 1. CORES PARA EVENTOS ---
    EVENTO_STATUS_COLORS = {
        'orcamento': '#ffc107',  # Amarelo (Warning)
        'confirmado': '#198754', # Verde (Success)
        'realizado': '#6c757d',   # Cinza (Secondary)
        'cancelado': "#e00e0e",
    }
    DEFAULT_EVENTO_COLOR = '#ffc107' 

    # --- 2. LISTA DE EVENTOS DO CALENDÁRIO (Reservas + Eventos) ---
    eventos_api_list = []

    # Busca Reservas
    reservas = Reserva.objects.all().select_related('cliente', 'acomodacao')
    
    for reserva in reservas:
        eventos_api_list.append({
            'id': f"reserva_{reserva.pk}",
            'resourceId': f"acomodacao_{reserva.acomodacao.pk}", # Liga à linha da Acomodação
            'title': f"Res. {reserva.pk} - {reserva.cliente.nome_completo}",
            'start': reserva.data_checkin.isoformat(),
            'end': reserva.data_checkout.isoformat(),
            'color': reserva.status_color,
            'url': reverse('reserva_detail', args=[reserva.pk]),
            'extendedProps': {
                'tipo': 'reserva',
                'reserva_pk': reserva.pk,
                'status_display': reserva.get_status_display(),
                'checkin_fmt': reserva.data_checkin.strftime('%d/%m %H:%M'),
                'checkout_fmt': reserva.data_checkout.strftime('%d/%m %H:%M'),
                'hospedes_txt': f"{reserva.num_adultos} Adulto(s), {reserva.num_criancas_12} Criança(s)"
            }
        })

    # Busca Eventos 
    eventos_db = Evento.objects.all().select_related('cliente').prefetch_related('espacos')

    for evento in eventos_db:
        
        # << SUA IDEIA SENDO APLICADA >>
        # 1. Junta os nomes de todos os espaços em uma string
        espacos_nomes = list(evento.espacos.all().values_list('nome', flat=True))
        espacos_str = ", ".join(espacos_nomes) if espacos_nomes else "Nenhum espaço definido"

        eventos_api_list.append({
            'id': f"evento_{evento.pk}",
            'resourceId': 'EVENTOS_ROW', # << ID ESTÁTICO! Todos os eventos vão para esta linha
            'title': evento.nome_evento, # << TÍTULO SIMPLES (Nome do Evento)
            'start': evento.data_inicio.isoformat(),
            'end': evento.data_fim.isoformat(),
            'color': EVENTO_STATUS_COLORS.get(evento.status, DEFAULT_EVENTO_COLOR),
            'url': reverse('evento_detail', args=[evento.pk]),
            'extendedProps': {
                'tipo': 'evento',
                'evento_pk': evento.pk,
                'cliente_nome': evento.cliente.nome_completo,
                'espacos_str': espacos_str, # << NOVO: Passa a string de espaços
                'status_display': evento.get_status_display(),
                'checkin_fmt': evento.data_inicio.strftime('%d/%m %H:%M'),
                'checkout_fmt': evento.data_fim.strftime('%d/%m %H:%M'),
                'convidados_txt': f"{evento.numero_convidados} Convidado(s)"
            }
        })

    # --- 3. LISTA DE RECURSOS (Acomodações + 1 Linha de Evento) ---
    recursos = []
    
    # Adiciona Acomodações (igual a antes)
    acomodacoes = Acomodacao.objects.all().order_by(Lower('tipo__nome'), 'numero')
    for acomodacao in acomodacoes:
        recursos.append({
            'id': f"acomodacao_{acomodacao.pk}",
            'title': acomodacao.nome_display,
            'grouping': 'Acomodações' # Agrupa
        })

    # << SUA IDEIA SENDO APLICADA >>
    # Adiciona UMA ÚNICA LINHA ESTÁTICA para todos os eventos
    recursos.append({
        'id': 'EVENTOS_ROW',
        'title': 'Eventos',
        'grouping': 'Espaços de Evento' # Agrupa
    })
        
    return JsonResponse({'eventos': eventos_api_list, 'recursos': recursos})

# ==============================================================================
# === VIEWS PARA A GESTÃO DE ESTOQUE                                         ===
# ==============================================================================

class ItemEstoqueListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_itemestoque'
    raise_exception = True 

    model = ItemEstoque
    template_name = 'gestao/item_estoque_list.html'
    context_object_name = 'item_estoque'
    paginate_by = 10 # Itens por página

    def get_queryset(self):
        queryset = super().get_queryset().order_by('nome')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(nome__icontains=query)
        return queryset

class ItemEstoqueCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'gestao.add_itemestoque'
    raise_exception = True 
    model = ItemEstoque
    form_class = ItemEstoqueForm
    template_name = 'gestao/item_estoque_form.html'
    success_url = reverse_lazy('item_estoque_list')
    success_message = "Item de estoque '%(nome)s' criado com sucesso!"

class ItemEstoqueUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_itemestoque'
    raise_exception = True 

    model = ItemEstoque
    form_class = ItemEstoqueForm
    template_name = 'gestao/item_estoque_form.html'
    success_url = reverse_lazy('item_estoque_list')
    success_message = "Item de estoque '%(nome)s' atualizado com sucesso!"

class ItemEstoqueDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_itemestoque'
    raise_exception = True 

    model = ItemEstoque
    template_name = 'gestao/item_estoque_confirm_delete.html'
    success_url = reverse_lazy('item_estoque_list')
    context_object_name = 'item'
    
    def form_valid(self, form):
        # Adiciona a mensagem de sucesso antes de o objeto ser deletado
        messages.success(self.request, f"Item de Estoque '{self.object}' foi excluída com sucesso.")
        return super().form_valid(form)
    
@login_required
@permission_required('gestao.add_compraestoque', raise_exception=True)
def compra_estoque_view(request, item_pk):
    item_estoque = get_object_or_404(ItemEstoque, pk=item_pk)
    
    if request.method == 'POST':
        form = CompraEstoqueForm(request.POST)
        if form.is_valid():
            compra = form.save(commit=False)
            compra.item = item_estoque
            compra.save()
            
            # Atualiza a quantidade total do item no estoque
            item_estoque.quantidade += compra.quantidade
            item_estoque.save()
            
            messages.success(request, f"Compra de {compra.quantidade}x '{item_estoque.nome}' registrada com sucesso.")
            return redirect('compra_estoque_list', item_pk=item_estoque.pk)
    else:
        form = CompraEstoqueForm()

    # Pega o histórico de compras para exibir no relatório
    historico_compras = item_estoque.compras.all().order_by('-data_compra')
    
    context = {
        'form': form,
        'item_estoque': item_estoque,
        'historico_compras': historico_compras
    }
    return render(request, 'gestao/compra_estoque_form.html', context)

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
            item_existente.quantidade += item_frigobar.quantidade
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

class ItemFrigobarUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_itemfrigobar'
    raise_exception = True

    model = ItemFrigobar
    form_class = ItemFrigobarUpdateForm
    template_name = 'gestao/item_frigobar_form.html' # Criaremos este template a seguir
    success_message = "Quantidade do item atualizada com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Enviamos o 'item_frigobar' para o template para podermos usar o nome no título
        context['item_frigobar'] = self.object
        return context

    def get_success_url(self):
        # Volta para a página de detalhes do frigobar após salvar
        return reverse_lazy('frigobar_detail', kwargs={'acomodacao_pk': self.object.frigobar.acomodacao.pk})
    
@login_required
@permission_required('gestao.add_consumo', raise_exception=True)
def registrar_consumo_view(request, item_frigobar_pk):
    """
    Registra o consumo de UMA unidade de um item do frigobar,
    adicionando à conta do hóspede atual e diminuindo do estoque do frigobar.
    """
    item_frigobar = get_object_or_404(ItemFrigobar, pk=item_frigobar_pk)
    item_estoque = get_object_or_404(ItemEstoque, pk=item_frigobar.item.pk)
    acomodacao = item_frigobar.frigobar.acomodacao
    
    # Encontra a reserva ativa (com check-in feito) para esta acomodação
    reserva_ativa = Reserva.objects.filter(acomodacao=acomodacao, status='checkin').first()

    if request.method == 'POST':
        if not reserva_ativa:
            messages.error(request, "Não há uma reserva ativa (com check-in) nesta acomodação para registrar o consumo.")
        elif item_frigobar.quantidade <= 0:
            messages.warning(request, f"Estoque de '{item_frigobar.item.nome}' no frigobar já está zerado.")
        else:
            # Cria um novo registro de consumo para a reserva ativa
            Consumo.objects.create(
                reserva=reserva_ativa,
                item=item_frigobar.item,
                quantidade=1,
                preco_unitario=item_frigobar.item.preco_venda
            )
            
            # Diminui a quantidade no frigobar
            item_frigobar.quantidade -= 1
            item_frigobar.save()

            # Diminui a quantidade no estoque geral
            item_estoque.quantidade -= 1
            item_estoque.save()
            
            # Atualiza o valor total do consumo na reserva
            reserva_ativa.valor_consumo += item_frigobar.item.preco_venda
            reserva_ativa.save()
            
            messages.success(request, f"1x '{item_frigobar.item.nome}' registrado na conta da reserva {reserva_ativa.pk}.")
            
    return redirect('frigobar_detail', acomodacao_pk=acomodacao.pk)

@login_required
@permission_required('gestao.delete_itemfrigobar', raise_exception=True)
def remover_item_frigobar(request, item_frigobar_pk):
    """Remove um item do frigobar e exibe uma mensagem de sucesso."""
    item_frigobar = get_object_or_404(ItemFrigobar, pk=item_frigobar_pk)
    acomodacao_pk = item_frigobar.frigobar.acomodacao.pk
    
    if request.method == 'POST':
        # Guarda o nome do item antes de apagar, para usar na mensagem
        item_nome = item_frigobar.item.nome 
        
        item_frigobar.delete()
        
        # Adiciona a mensagem de sucesso
        messages.success(request, f"Item '{item_nome}' removido do frigobar com sucesso.")
        
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
            item_estoque.quantidade -= consumo.quantidade
            item_estoque.save()
            consumo.save()
            
            # Atualizar valor do consumo na reserva
            reserva.valor_consumo += (consumo.quantidade * consumo.preco_unitario)
            reserva.save()

            messages.success(request, f"{consumo.quantidade}x '{item_estoque.nome}' adicionado(s) à conta.")
        else:
            # Se não houver estoque, exibe uma mensagem de erro e não redireciona
            messages.error(request, f"Estoque insuficiente para '{item_estoque.nome}'. Disponível: {item_estoque.quantidade}.")
            
        return redirect('reserva_detail', pk=reserva.pk)

    context = {
        'reserva': reserva,
        'form': form
    }
    return render(request, 'gestao/consumo_form.html', context)

class ConsumoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_consumo'
    raise_exception = True

    model = Consumo
    form_class = ConsumoUpdateForm
    template_name = 'gestao/consumo_form.html' # Reutilizaremos o form, mas com contexto diferente
    context_object_name = 'consumo'
    success_message = "Consumo atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona 'is_editing' para o template saber a diferença
        context['is_editing'] = True
        return context

    def get_success_url(self):
        # Volta para a página de detalhes da reserva após a edição
        return reverse_lazy('reserva_detail', kwargs={'pk': self.object.reserva.pk})

    def form_valid(self, form):
        # Usa uma transação para garantir a integridade dos dados
        with transaction.atomic():
            # Pega o objeto antigo (antes de salvar) para saber a quantidade original
            consumo_antigo = self.get_object()
            quantidade_antiga = consumo_antigo.quantidade
            valor_antigo = consumo_antigo.total()

            # Salva o formulário para obter a nova quantidade
            consumo_novo = form.save(commit=False)
            nova_quantidade = consumo_novo.quantidade

            # Calcula a diferença para ajustar o estoque e o valor
            diferenca_quantidade = nova_quantidade - quantidade_antiga
            
            item_estoque = consumo_novo.item
            
            # Validação de estoque
            if diferenca_quantidade > 0 and item_estoque.quantidade < diferenca_quantidade:
                messages.error(self.request, f"Não foi possível aumentar o consumo. Estoque insuficiente para '{item_estoque.nome}'.")
                return self.form_invalid(form)

            # 1. Ajusta o estoque geral (subtrai a diferença)
            item_estoque.quantidade -= diferenca_quantidade
            item_estoque.save()
            
            # 2. Ajusta o valor do consumo na reserva
            valor_novo = nova_quantidade * consumo_novo.preco_unitario
            diferenca_valor = valor_novo - valor_antigo
            reserva = consumo_novo.reserva
            reserva.valor_consumo += diferenca_valor
            reserva.save()
            
            # Salva o consumo com a nova quantidade (chama o método padrão)
            return super().form_valid(form)

class ConsumoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_consumo'
    raise_exception = True

    model = Consumo
    template_name = 'gestao/consumo_confirm_delete.html'
    context_object_name = 'consumo'
    raise_exception = True

    def get_success_url(self):
        # Continua voltando para a página de detalhes da reserva
        return reverse_lazy('reserva_detail', kwargs={'pk': self.object.reserva.pk})

    def form_valid(self, form):
        # Pega o objeto de consumo que será deletado
        consumo = self.get_object()
        reserva = consumo.reserva
        item_estoque = consumo.item
        
        # Usa uma "transação" para garantir a segurança da operação
        with transaction.atomic():
            # --- CORREÇÃO APLICADA AQUI ---
            # 1. Devolve a quantidade ao estoque (cálculo em Python)
            item_estoque.quantidade += consumo.quantidade
            item_estoque.save()
            
            # 2. Abate o valor do consumo da reserva (cálculo em Python)
            reserva.valor_consumo -= consumo.total()
            reserva.save()

        messages.success(self.request, f"Consumo de '{item_estoque.nome}' foi removido com sucesso.")
        
        # Deixa a lógica padrão do DeleteView fazer a exclusão e o redirecionamento
        return super().form_valid(form)

# ==============================================================================
# === VIEWS PARA FORMA DE PAGAMENTOS                                         ===
# ==============================================================================
class FormaPagamentoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_formapagamento'
    raise_exception = True 

    model = FormaPagamento
    template_name = 'gestao/forma_pagamento_list.html'
    context_object_name = 'forma_pagamento' 
    paginate_by = 10 # Define 10 itens por página
    ordering = ['nome'] # Opcional: Garante a ordem alfabética

class FormaPagamentoCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'gestao.add_formapagamento'
    raise_exception = True 

    model = FormaPagamento
    form_class = FormaPagamentoForm
    template_name = 'gestao/forma_pagamento_form.html'
    success_url = reverse_lazy('forma_pagamento_list')
    success_message = "Forma de pagamento criado com sucesso!"

class FormaPagamentoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_formapagamento'
    raise_exception = True 

    model = FormaPagamento
    form_class = FormaPagamentoForm
    template_name = 'gestao/forma_pagamento_form.html'
    success_url = reverse_lazy('forma_pagamento_list')
    success_message = "Forma de pagamento atualizado com sucesso!"

class FormaPagamentoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_formapagamento'
    raise_exception = True 

    model = FormaPagamento
    template_name = 'gestao/forma_pagamento_confirm_delete.html'
    success_url = reverse_lazy('forma_pagamento_list')
    context_object_name = 'forma_pagamento'

    def form_valid(self, form):
        # Adiciona a mensagem de sucesso antes de o objeto ser deletado
        messages.success(self.request, f"Forma de Pagamento '{self.object}' foi excluída com sucesso.")
        return super().form_valid(form)

# ==============================================================================
# === VIEWS PARA PAGAMENTOS                                                  ===
# ==============================================================================

class PagamentoReservaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'gestao.add_pagamento'
    raise_exception = True

    model = Pagamento
    form_class = PagamentoForm
    template_name = 'gestao/pagamento_form.html'

    def get_initial(self):
        """ Pega a lógica do 'initial' da sua função original """
        reserva = get_object_or_404(Reserva, pk=self.kwargs['reserva_pk'])
        initial = super().get_initial()
        
        # Tenta sugerir o saldo devedor
        if hasattr(reserva, 'saldo_devedor'):
            initial['valor'] = reserva.saldo_devedor()
            
        return initial

    def get_context_data(self, **kwargs):
        """ Envia a 'reserva' para o template (para o botão "Cancelar") """
        context = super().get_context_data(**kwargs)
        context['reserva'] = get_object_or_404(Reserva, pk=self.kwargs['reserva_pk'])
        return context

    def form_valid(self, form):
        """ Pega a lógica de salvar e atualizar status da sua função original """
        reserva = get_object_or_404(Reserva, pk=self.kwargs['reserva_pk'])
        
        # Associa o pagamento à reserva ANTES de salvar
        form.instance.reserva = reserva
        
        # Adiciona a mensagem de sucesso
        messages.success(self.request, f"Pagamento de R$ {form.instance.valor} registado com sucesso!")

        # Lógica de atualização do status da reserva
        if reserva.status == 'pre_reserva':
            reserva.status = 'confirmada'
            reserva._change_reason = 'Status alterado para Confirmada devido ao registro de novo pagamento.'
            reserva.save()
            messages.info(self.request, "O status da reserva foi atualizado para 'Confirmada'.")
            
        # O super().form_valid() salva o 'form.instance' e redireciona
        return super().form_valid(form)

    def get_success_url(self):
        """ Redireciona de volta para a reserva_detail """
        return reverse_lazy('reserva_detail', kwargs={'pk': self.kwargs['reserva_pk']})

class PagamentoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_pagamento'
    raise_exception = True

    model = Pagamento
    form_class = PagamentoForm
    template_name = 'gestao/pagamento_form.html'
    success_message = "Pagamento no valor de R$ %(valor)s atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pagamento = self.get_object()
        
        if pagamento.reserva:
            # Envia a reserva para o template poder usar no link "Cancelar"
            context['reserva'] = pagamento.reserva
        elif pagamento.evento:
            # Envia o evento para o template poder usar no link "Cancelar"
            context['evento'] = pagamento.evento
        
        return context

    def get_success_url(self):
        pagamento = self.object 

        if pagamento.reserva:
            return reverse_lazy('reserva_detail', kwargs={'pk': pagamento.reserva.pk})
        elif pagamento.evento:
            return reverse_lazy('evento_detail', kwargs={'pk': pagamento.evento.pk})
        else:
            messages.warning(self.request, "Pagamento sem reserva ou evento associado.")
            return reverse_lazy('dashboard')

class PagamentoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_pagamento'
    raise_exception = True

    model = Pagamento
    template_name = 'gestao/pagamento_confirm_delete.html'
    
    def get_success_url(self):
        """
        Verifica qual é o "pai" do pagamento (Reserva ou Evento)
        e redireciona para a página de detalhes correta.
        """
        pagamento = self.object # O pagamento que está sendo (ou foi) deletado

        if pagamento.reserva:
            # 1. Se tem uma reserva, volte para a reserva
            return reverse_lazy('reserva_detail', kwargs={'pk': pagamento.reserva.pk})
        
        elif pagamento.evento:
            # 2. Se tem um evento, volte para o evento
            return reverse_lazy('evento_detail', kwargs={'pk': pagamento.evento.pk})
        
        else:
            # 3. Se não tem nenhum (é órfão), volte para um local seguro
            messages.warning(self.request, "Pagamento sem reserva ou evento associado.")
            return reverse_lazy('dashboard')
    
    def form_valid(self, form):
        # Adiciona a mensagem de sucesso antes de o objeto ser deletado
        messages.success(self.request, f"Pagamento no valor de R$ {self.object.valor} foi excluído com sucesso.")
        return super().form_valid(form)

# ==============================================================================
# === VIEWS PARA ESTACIONAMENTO                                              ===
# ==============================================================================

class VagaEstacionamentoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_vagaestacionamento'
    raise_exception = True 

    model = VagaEstacionamento
    template_name = 'gestao/vaga_estacionamento_list.html'
    context_object_name = 'vaga_estacionamento'
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

class VagaEstacionamentoCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'gestao.add_vagaestacionamento'
    raise_exception = True 
    
    model = VagaEstacionamento
    form_class = VagaEstacionamentoForm
    template_name = 'gestao/vaga_estacionamento_form.html'
    success_url = reverse_lazy('vaga_estacionamento_list')
    success_message = "Vaga de estacionamento criada com sucesso!"

class VagaEstacionamentoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_vagaestacionamento'
    raise_exception = True 
    
    model = VagaEstacionamento
    form_class = VagaEstacionamentoForm
    template_name = 'gestao/vaga_estacionamento_form.html'
    success_url = reverse_lazy('vaga_estacionamento_list')
    success_message = "Vaga de estacionamento atualizado com sucesso!"

class VagaEstacionamentoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_vagaestacionamento'
    raise_exception = True 
    
    model = VagaEstacionamento
    template_name = 'gestao/vaga_estacionamento_confirm_delete.html'
    success_url = reverse_lazy('vaga_estacionamento_list')
    context_object_name = 'vaga'

    def form_valid(self, form):
        # Adiciona a mensagem de sucesso antes de o objeto ser deletado
        messages.success(self.request, f"Vaga de estacionamento '{self.object}' foi excluída com sucesso.")
        return super().form_valid(form)

# ==============================================================================
# === VIEWS PARA FUNCIONÁRIOS                                                ===
# ==============================================================================
class FuncionarioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_funcionario'
    raise_exception = True 
    
    model = User
    template_name = 'gestao/funcionario_list.html'
    context_object_name = 'usuarios'
    ordering = ['username']

class FuncionarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'gestao.add_funcionario'
    raise_exception = True 
    
    model = User
    form_class = FuncionarioCreationForm
    template_name = 'gestao/funcionario_form.html'
    success_url = reverse_lazy('funcionario_list')
    success_message = "Funcionario(a) criado(a) com sucesso!"

class FuncionarioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_funcionario'
    raise_exception = True 
    
    model = User
    form_class = FuncionarioUpdateForm
    template_name = 'gestao/funcionario_form.html'
    success_url = reverse_lazy('funcionario_list')
    success_message = "Funcionario(a) atualilzado(a) com sucesso!"

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
    # --- 1. LÓGICA CORRIGIDA PARA O RANKING (GRÁFICO) ---
    # Busca a partir do modelo Acomodacao e conta as reservas com status 'checkout'
    acomodacoes_ranking = Acomodacao.objects.annotate(
        total_reservas=Count('reservas', filter=models.Q(reservas__status='checkout'))
    ).filter(total_reservas__gt=0).order_by('-total_reservas')[:10]

    # Usa a propriedade 'nome_display' que já tem a lógica de "Quarto" vs "Chalé"
    ranking_labels = [ac.nome_display for ac in acomodacoes_ranking]
    ranking_data = [ac.total_reservas for ac in acomodacoes_ranking]
    
    ranking_data_json = json.dumps({
        'labels': ranking_labels,
        'data': ranking_data,
    })

    # --- 2. LÓGICA OTIMIZADA PARA O EXTRATO DE PAGAMENTOS ---
    # Query base que será filtrada
    reservas_list = Reserva.objects.filter(status='checkout').select_related(
        'cliente', 'acomodacao'
    ).prefetch_related(
        'pagamentos__forma_pagamento', 'consumos__item'
    ).order_by('-data_checkout')

    # Pega os parâmetros de filtro da URL
    query = request.GET.get('q')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Aplica filtros diretamente no QuerySet (mais eficiente)
    if query:
        reservas_list = reservas_list.filter(
            Q(cliente__nome_completo__icontains=query) | 
            Q(cliente__cpf__icontains=query) | 
            Q(acomodacao__numero__icontains=query)
        )
        
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            # O filtro do extrato é sobre a data de check-out
            reservas_list = reservas_list.filter(data_checkout__gte=start_date)
        except (ValueError, TypeError):
            pass
        
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            reservas_list = reservas_list.filter(data_checkout__lte=end_date)
        except (ValueError, TypeError):
            pass

    # --- 3. MONTAGEM OTIMIZADA DO RELATÓRIO E PAGINAÇÃO ---
    # Agora paginamos o queryset, que é muito mais rápido
    paginator = Paginator(reservas_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Monta a estrutura de dados apenas para os itens da página atual
    relatorio_pagamentos = []
    for reserva in page_obj.object_list:
        total_pago = sum(p.valor for p in reserva.pagamentos.all())
        relatorio_pagamentos.append({
            'reserva': reserva,
            'pagamentos': reserva.pagamentos.all(),
            'consumos': reserva.consumos.all(),
            'total_pago': total_pago,
        })
    
    # --- 4. CONTEXTO PARA O TEMPLATE ---
    context = {
        'ranking_data_json': ranking_data_json,
        'page_obj': relatorio_pagamentos, # Enviamos a lista já processada
        'paginator': paginator, # Informações de paginação
        'object_list': page_obj.object_list # Para compatibilidade com a paginação
    }
    return render(request, 'gestao/relatorio_acomodacoes.html', context)

# ==========================================================
# === VIEWS PARA O GESTÃO FINANCEIRA                     ===
# ==========================================================

@login_required
def financeiro_dashboard_view(request):
    
    # --- Form de gasto (POST) --- 
    # (Sem alterações)
    if request.method == 'POST':
        gasto_form = GastoForm(request.POST)
        if gasto_form.is_valid():
            gasto_form.save()
            messages.success(request, 'Gasto adicionado com sucesso!')
            return redirect('financeiro') # Redireciona para a própria página (GET)
    else:
        # Garante que o form sempre tenha categorias (ou estará vazio se não houver)
        gasto_form = GastoForm()

    # --- 1. FILTRO DE PERÍODO (Simplificado) ---
    today = timezone.localdate()
    # Pega datas da URL ou usa o mês atual como padrão
    start_date_str = request.GET.get('start', today.replace(day=1).strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end', today.strftime('%Y-%m-%d'))
    
    # Converte datas, usando padrão em caso de erro
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        start_date = today.replace(day=1)
        start_date_str = start_date.strftime('%Y-%m-%d')
        
    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        end_date = today
        end_date_str = end_date.strftime('%Y-%m-%d')

    # --- 2. QUERIES BASE FILTRADAS PELO PERÍODO ---
    
    # Pagamentos (RECEITA) - Usando data_pagamento
    pagamentos_qs = Pagamento.objects.filter(
        data_pagamento__date__gte=start_date,
        data_pagamento__date__lte=end_date
    ).select_related('reserva', 'evento', 'forma_pagamento') # Inclui forma_pagamento

    # Gastos (DESPESA) - Usando data_gasto
    gastos_qs = Gasto.objects.filter(
        data_gasto__gte=start_date,
        data_gasto__lte=end_date
    ).select_related('categoria') # Inclui categoria

    # --- 3. CÁLCULO DOS KPIs (Request #2 - CORRIGIDO) ---
    
    total_recebido = pagamentos_qs.aggregate(
        total=Coalesce(Sum('valor'), Value(0, output_field=DecimalField()))
    )['total']
    
    total_despesas = gastos_qs.aggregate(
        total=Coalesce(Sum('valor'), Value(0, output_field=DecimalField()))
    )['total']
    
    lucro_liquido = total_recebido - total_despesas
    
    num_pagamentos = pagamentos_qs.count()
    ticket_medio = total_recebido / num_pagamentos if num_pagamentos > 0 else 0

    # Contas a Receber (Opcional - Mantendo comentado por enquanto)
    # reservas_devendo = Reserva.objects.filter(status__in=['confirmada', 'checkin']).annotate(...) # lógica complexa
    # eventos_devendo = Evento.objects.filter(status='confirmado').annotate(...) # lógica complexa
    # contas_a_receber = ...

    # --- 4. DADOS PARA GRÁFICOS ---

    # Gráfico 1: Fluxo de Caixa Mensal (Request #1 - CORRIGIDO)
    receitas_por_mes = (
        pagamentos_qs
        .annotate(periodo=TruncMonth('data_pagamento'))
        .values('periodo')
        .annotate(total_receita=Coalesce(Sum('valor'), Value(0, output_field=DecimalField())))
        .order_by('periodo')
    )
    despesas_por_mes = (
        gastos_qs
        .annotate(periodo=TruncMonth('data_gasto'))
        .values('periodo')
        .annotate(total_despesa=Coalesce(Sum('valor'), Value(0, output_field=DecimalField())))
        .order_by('periodo')
    )

    # Merge dos dados mensais (Formato {mes: {'receita': R, 'despesa': D}})
    fluxo_map = {}
    all_months = set()

    for item in receitas_por_mes:
        month_date = item['periodo'].date() if isinstance(item['periodo'], datetime) else item['periodo'] 

        all_months.add(month_date)
        if month_date not in fluxo_map:
            fluxo_map[month_date] = {'receita': 0, 'despesa': 0}
        fluxo_map[month_date]['receita'] = float(item['total_receita'])

    for item in despesas_por_mes:
        month_date = item['periodo'].date() if isinstance(item['periodo'], datetime) else item['periodo']

        all_months.add(month_date)
        if month_date not in fluxo_map:
            fluxo_map[month_date] = {'receita': 0, 'despesa': 0}
        fluxo_map[month_date]['despesa'] = float(item['total_despesa'])

    # Ordena os meses e formata para o gráfico
    fluxo_chart_data_list = []
    for month in sorted(list(all_months)):
        data = fluxo_map.get(month, {'receita': 0, 'despesa': 0})
        fluxo_chart_data_list.append({
            "label": month.strftime('%m/%Y'),
            "receita": data['receita'],
            "despesa": data['despesa'],
            "saldo": data['receita'] - data['despesa']
        })
    # Passa a lista diretamente, o JS vai extrair labels e datasets
    fluxo_chart_json = json.dumps(fluxo_chart_data_list) 

    # Gráfico 2: Receita por Origem (Request #3 - NOVO)
    # Usamos Case/When para categorizar cada pagamento
    receita_origem = pagamentos_qs.annotate(
        origem=Case(
            When(reserva__isnull=False, then=Value('Reservas')),
            When(evento__isnull=False, then=Value('Eventos')),
            # Adicione mais 'When' se tiver outras fontes (ex: consumo direto)
            default=Value('Outros'), # Fallback
            output_field=models.CharField(),
        )
    ).values('origem').annotate(
        total=Coalesce(Sum('valor'), Value(0, output_field=DecimalField()))
    ).order_by('origem')

    receita_origem_data = {
        'labels': [item['origem'] for item in receita_origem],
        'data': [float(item['total']) for item in receita_origem],
    }
    receita_origem_json = json.dumps(receita_origem_data)

    # Gráfico 3: Despesas por Categoria (Request #3 - NOVO)
    despesa_categoria = gastos_qs.values(
        'categoria__nome' # Agrupa pelo nome da categoria relacionada
    ).annotate(
        total=Coalesce(Sum('valor'), Value(0, output_field=DecimalField()))
    ).order_by('-total') # Ordena do maior para o menor

    despesa_categoria_data = {
        'labels': [item['categoria__nome'] or 'Sem Categoria' for item in despesa_categoria],
        'data': [float(item['total']) for item in despesa_categoria],
    }
    despesa_categoria_json = json.dumps(despesa_categoria_data)

    # Gráfico 4: Receita por Forma de Pagamento (Request #3 - NOVO)
    receita_forma_pag = pagamentos_qs.values(
        'forma_pagamento__nome' # Agrupa pelo nome da forma de pagamento relacionada
    ).annotate(
        total=Coalesce(Sum('valor'), Value(0, output_field=DecimalField()))
    ).order_by('-total') # Ordena do maior para o menor

    receita_forma_pag_data = {
        'labels': [item['forma_pagamento__nome'] or 'N/D' for item in receita_forma_pag],
        'data': [float(item['total']) for item in receita_forma_pag],
    }
    receita_forma_pag_json = json.dumps(receita_forma_pag_data)
    
    # --- 5. ÚLTIMOS GASTOS (Mantido) ---
    gastos_recentes = Gasto.objects.select_related('categoria').order_by('-data_gasto')[:5]

    print("DEBUG Fluxo JSON:", fluxo_chart_json)
    print("DEBUG Origem JSON:", receita_origem_json)
    print("DEBUG Categoria JSON:", despesa_categoria_json)
    print("DEBUG Forma Pag JSON:", receita_forma_pag_json)

    # --- 6. CONTEXTO ---
    context = {
        # Filtros
        "start_date": start_date_str, 
        "end_date": end_date_str,

        # KPIs Corrigidos
        "total_recebido": total_recebido,
        "total_despesas": total_despesas,
        "lucro_liquido": lucro_liquido,
        "ticket_medio": ticket_medio,
        
        # === PASSE OS DADOS PYTHON DIRETAMENTE ===
        "fluxo_chart_json": fluxo_chart_data_list, # << PASSA A LISTA
        "receita_origem_json": receita_origem_data, # << PASSA O DICIONÁRIO
        "despesa_categoria_json": despesa_categoria_data, # << PASSA O DICIONÁRIO
        "receita_forma_pag_json": receita_forma_pag_data, # << PASSA O DICIONÁRIO
        # === FIM DA ALTERAÇÃO ===

        # Formulário e Lista de Gastos
        "gasto_form": gasto_form,
        'gastos_recentes': gastos_recentes,
    }

    return render(request, 'gestao/financeiro_dashboard.html', context)

# ==========================================================
# === VIEWS PARA GASTO                                   ===
# ==========================================================

class GastoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_gasto'
    raise_exception = True

    model = Gasto
    form_class = GastoForm
    template_name = 'gestao/gasto_form.html'
    success_url = reverse_lazy('financeiro') # Volta para o painel financeiro
    success_message = "Gasto atualizado com sucesso!"

class GastoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_gasto'
    raise_exception = True
    
    model = Gasto
    template_name = 'gestao/gasto_confirm_delete.html'
    success_url = reverse_lazy('financeiro') # Volta para o painel financeiro

    def form_valid(self, form):
        # Adiciona a mensagem de sucesso antes de o objeto ser deletado
        messages.success(self.request, f"'{self.object}' foi excluída com sucesso.")
        return super().form_valid(form)

# ==========================================================
# === VIEWS PARA CATEGORIAS DE GASTO                     ===
# ==========================================================

class CategoriaGastoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_categoriagasto'
    raise_exception = True 
    
    model = CategoriaGasto
    template_name = 'gestao/categoria_gasto_list.html'
    context_object_name = 'categoria_gasto'
    paginate_by = 10
    ordering = ['nome']

class CategoriaGastoCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'gestao.add_categoriagasto'
    raise_exception = True 
    
    model = CategoriaGasto
    form_class = CategoriaGastoForm
    template_name = 'gestao/categoria_gasto_form.html'
    success_url = reverse_lazy('categoria_gasto_list')
    success_message = "Categoria '%(nome)s' criada com sucesso!"

class CategoriaGastoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_categoriagasto'
    raise_exception = True 
    
    model = CategoriaGasto
    form_class = CategoriaGastoForm
    template_name = 'gestao/categoria_gasto_form.html'
    success_url = reverse_lazy('categoria_gasto_list')
    success_message = "Categoria '%(nome)s' atualizada com sucesso!"

class CategoriaGastoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_categoriagasto'
    raise_exception = True 
    
    model = CategoriaGasto
    template_name = 'gestao/categoria_gasto_confirm_delete.html'
    success_url = reverse_lazy('categoria_gasto_list')

    def form_valid(self, form):
        # Adiciona a mensagem de sucesso antes de o objeto ser deletado
        messages.success(self.request, f"Categoria '{self.object}' foi excluída com sucesso.")
        return super().form_valid(form)

   
# ==========================================================
# === VIEWS PARA PERIODO TARIFARIO                       ===
# ==========================================================

class PeriodoTarifarioListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_periodotarifario'
    raise_exception = True

    model = PeriodoTarifario
    template_name = 'gestao/periodo_tarifario_list.html'
    context_object_name = 'periodos'
    paginate_by = 15 # Opcional: para paginação

class PeriodoTarifarioCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'gestao.add_periodotarifario'
    raise_exception = True

    model = PeriodoTarifario
    form_class = PeriodoTarifarioForm
    template_name = 'gestao/periodo_tarifario_form.html'
    success_url = reverse_lazy('periodo_tarifario_list')
    success_message = "Período '%(nome)s' criado com sucesso!"

class PeriodoTarifarioUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_periodotarifario'
    raise_exception = True

    model = PeriodoTarifario
    form_class = PeriodoTarifarioForm
    template_name = 'gestao/periodo_tarifario_form.html' 
    success_url = reverse_lazy('periodo_tarifario_list')
    success_message = "Período '%(nome)s' atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        periodo = self.get_object()
        
        # Envia as datas formatadas para o JavaScript
        if periodo.data_inicio:
            context['data_inicio_js'] = periodo.data_inicio.strftime('%Y-%m-%d')
        if periodo.data_fim:
            context['data_fim_js'] = periodo.data_fim.strftime('%Y-%m-%d')
            
        return context

class PeriodoTarifarioDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_periodotarifario'
    raise_exception = True
    
    model = PeriodoTarifario
    template_name = 'gestao/periodo_tarifario_confirm_delete.html' # Novo template de confirmação
    success_url = reverse_lazy('periodo_tarifario_list')

    def form_valid(self, form):
        messages.success(self.request, f"O período tarifário '{self.object.nome}' foi excluído com sucesso.")
        return super().form_valid(form)
    
# ==========================================================
# === VIEWS PARA ESPAÇO                                  ===
# ==========================================================

class EspacoListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_espaco'
    raise_exception = True

    model = Espaco
    template_name = 'gestao/espaco_list.html'
    context_object_name = 'espacos'
    paginate_by = 10

class EspacoCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'gestao.add_espaco'
    raise_exception = True

    model = Espaco
    form_class = EspacoForm
    template_name = 'gestao/espaco_form.html'
    success_url = reverse_lazy('espaco_list')
    success_message = "'%(nome)s' criado com sucesso!"

class EspacoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_espaco'
    raise_exception = True

    model = Espaco
    form_class = EspacoForm
    template_name = 'gestao/espaco_form.html' # Reutiliza o mesmo template do 'adicionar'
    success_url = reverse_lazy('espaco_list')
    success_message = "'%(nome)s' atualizado com sucesso!"

class EspacoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_espaco'
    raise_exception = True

    model = Espaco
    template_name = 'gestao/espaco_confirm_delete.html' # Novo template de confirmação
    success_url = reverse_lazy('espaco_list')
    success_message = "Espaço/Item '%(nome)s' foi excluído com sucesso."

    def form_valid(self, form):
        messages.success(self.request, f"O período tarifário '{self.object.nome}' foi excluído com sucesso.")
        return super().form_valid(form)

# ==========================================================
# === VIEWS PARA EVENTO                                  ===
# ==========================================================

class EventosDashboardView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'gestao.view_evento'
    raise_exception = True 

    model = Evento
    template_name = 'gestao/eventos_dashboard.html'
    context_object_name = 'eventos'
    paginate_by = 10

class EventoDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = 'gestao.view_evento'
    raise_exception = True 

    model = Evento
    template_name = 'gestao/evento_detail.html'
    context_object_name = 'evento'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento = self.get_object()
        
        # Busca todos os custos associados a este evento
        custos_do_evento = evento.custos.all().order_by('-data_custo')
        pagamentos_do_evento = evento.pagamentos.all().order_by('-data_pagamento')

        context['custos_do_evento'] = custos_do_evento
        context['pagamentos_do_evento'] = pagamentos_do_evento
        
        # Calcula o resumo financeiro do evento
        total_custo = custos_do_evento.aggregate(Sum('valor'))['valor__sum'] or 0
        total_pago = pagamentos_do_evento.aggregate(Sum('valor'))['valor__sum'] or 0

        total_a_pagar = evento.valor_negociado + total_custo
        saldo_devedor = total_a_pagar - total_pago
        
        context['resumo_financeiro'] = {
            'valor_negociado': evento.valor_negociado,
            'total_custo': total_custo,
            'total_a_pagar': total_a_pagar,
            'total_pago': total_pago,
            'saldo_devedor': saldo_devedor,
        }
        return context

class EventoCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'gestao.add_evento'
    raise_exception = True 

    model = Evento
    form_class = EventoForm
    template_name = 'gestao/evento_form.html'
    success_url = reverse_lazy('eventos_dashboard') # <- Redireciona para o dashboard de eventos
    success_message = "Evento '%(nome_evento)s' registrado com sucesso!"

class EventoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_evento'
    raise_exception = True 

    model = Evento
    form_class = EventoForm
    template_name = 'gestao/evento_form.html' # Reutiliza o mesmo template do 'registrar'
    success_url = reverse_lazy('eventos_dashboard')
    success_message = "Evento '%(nome_evento)s' atualizado com sucesso!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento = self.get_object()
        
        # Envia as datas formatadas para o JavaScript
        if evento.data_inicio:
            context['data_inicio_js'] = evento.data_inicio.strftime('%Y-%m-%dT%H:%M')
        if evento.data_fim:
            context['data_fim_js'] = evento.data_fim.strftime('%Y-%m-%dT%H:%M')
            
        return context

class EventoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_evento'
    raise_exception = True 

    model = Evento
    template_name = 'gestao/evento_confirm_delete.html' # Novo template de confirmação
    success_url = reverse_lazy('eventos_dashboard')
    success_message = "Evento '%(nome_evento)s' foi excluído com sucesso."

    def form_valid(self, form):
        nome_evento = self.object.nome_evento
        messages.success(self.request, f"O evento '{nome_evento}' foi excluído com sucesso.")
        return super().form_valid(form)
    
@login_required
@permission_required('gestao.view_evento', raise_exception=True)
def evento_relatorio_view(request):
    
    # --- 1. LÓGICA DE FILTRO POR DATA E BUSCA ---
    today = timezone.localdate()
    # Pega parâmetros da URL
    query = request.GET.get('q', '').strip() # Termo de busca
    start_date_str = request.GET.get('start_date', today.replace(day=1).strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end_date', today.strftime('%Y-%m-%d'))
    
    # Converte datas (com tratamento de erro básico)
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        start_date = today.replace(day=1)
        start_date_str = start_date.strftime('%Y-%m-%d')
        
    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        end_date = today
        end_date_str = end_date.strftime('%Y-%m-%d')

    # --- Query Base: Pagamentos de Eventos no Período ---
    # Começamos pelos pagamentos, pois o extrato é sobre eles
    pagamentos_base = Pagamento.objects.filter(
        evento__isnull=False, 
        data_pagamento__date__gte=start_date,
        data_pagamento__date__lte=end_date
    ).select_related(
        'evento__cliente', 
        'forma_pagamento'
    ).order_by('evento_id', '-data_pagamento') # Ordena para facilitar o agrupamento

    # Aplica filtro de busca (se houver)
    if query:
        pagamentos_base = pagamentos_base.filter(
            Q(evento__nome_evento__icontains=query) |
            Q(evento__cliente__nome_completo__icontains=query) |
            Q(evento__cliente__cpf__icontains=query) 
        )

    # --- 2. AGRUPAMENTO POR EVENTO E COLETA DE DADOS ---
    eventos_com_pagamentos = {} 
    
    for pag in pagamentos_base:
        evento_id = pag.evento_id
        if evento_id not in eventos_com_pagamentos:
            eventos_com_pagamentos[evento_id] = {
                'evento': pag.evento, 
                'pagamentos': [],
                'custos': [], 
                'total_pago': 0,
                'total_a_receber': 0,
                'saldo_devedor': 0,
                'total_custos_do_evento': 0 # <<< Adiciona campo para o total de custos
            }
        eventos_com_pagamentos[evento_id]['pagamentos'].append(pag)
        eventos_com_pagamentos[evento_id]['total_pago'] += pag.valor

    eventos_ids = list(eventos_com_pagamentos.keys())
    if eventos_ids:
        custos_eventos = CustoEvento.objects.filter(evento_id__in=eventos_ids).order_by('-data_custo')
        for custo in custos_eventos:
            if custo.evento_id in eventos_com_pagamentos:
                eventos_com_pagamentos[custo.evento_id]['custos'].append(custo)
        
        # Calcula totais para cada evento
        for evento_id in eventos_ids:
            evento_obj = eventos_com_pagamentos[evento_id]['evento']
            # === CALCULA E ARMAZENA O TOTAL DE CUSTOS ===
            total_custos_do_evento = sum(c.valor for c in eventos_com_pagamentos[evento_id]['custos'])
            eventos_com_pagamentos[evento_id]['total_custos_do_evento'] = total_custos_do_evento
            # === FIM DA ALTERAÇÃO ===
            
            total_a_receber_evento = (evento_obj.valor_negociado or 0) + total_custos_do_evento
            total_pago_evento = eventos_com_pagamentos[evento_id]['total_pago'] 

            eventos_com_pagamentos[evento_id]['total_a_receber'] = total_a_receber_evento
            eventos_com_pagamentos[evento_id]['saldo_devedor'] = total_a_receber_evento - total_pago_evento 

    lista_extrato = list(eventos_com_pagamentos.values())
    
    # --- 3. PAGINAÇÃO DO EXTRATO ---
    paginator = Paginator(lista_extrato, 5) # 5 eventos por página (ajuste se necessário)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # --- 4. CÁLCULO DOS KPIs E GRÁFICOS (BASEADO NOS FILTROS) ---
    # Recalcula alguns totais baseado nos pagamentos filtrados pela busca (se houver)
    pagamentos_filtrados_kpi = pagamentos_base # Usa o mesmo queryset já filtrado pela busca

    total_faturado_kpi = pagamentos_filtrados_kpi.aggregate(total=Sum('valor'))['total'] or 0

    # Para "Total a Receber", "Nº Eventos", "Média Convidados" e Rankings,
    # usamos os eventos únicos que tiveram pagamentos no período filtrado.
    eventos_unicos_ids = pagamentos_filtrados_kpi.values_list('evento_id', flat=True).distinct()
    eventos_filtrados_kpi = Evento.objects.filter(pk__in=eventos_unicos_ids)

    total_negociado_kpi = eventos_filtrados_kpi.aggregate(total=Sum('valor_negociado'))['total'] or 0
    total_custos_kpi = CustoEvento.objects.filter(evento__in=eventos_filtrados_kpi).aggregate(total=Sum('valor'))['total'] or 0
    total_a_receber_kpi = total_negociado_kpi + total_custos_kpi
    
    num_eventos_kpi = eventos_filtrados_kpi.count()
    media_convidados_kpi = eventos_filtrados_kpi.aggregate(media=Avg('numero_convidados'))['media'] or 0

    # Gráfico: Recebimento Mensal (usando pagamentos filtrados)
    faturamento_mensal = (
        pagamentos_filtrados_kpi.annotate(mes=TruncMonth('data_pagamento'))
        .values('mes').annotate(total=Sum('valor')).order_by('mes')
    )
    faturamento_chart_data = {
        'labels': [item['mes'].strftime('%m/%Y') for item in faturamento_mensal],
        'data': [float(item['total']) for item in faturamento_mensal],
    }

    # Gráfico: Receita por Categoria (usando totais recalculados)
    receita_categoria_data = {
        'labels': ['Valor Negociado (Contratos)', 'Custos Adicionais'],
        'data': [float(total_negociado_kpi), float(total_custos_kpi)],
    }

    # Gráficos: Rankings (usando eventos filtrados)
    espacos_ranking = (
        eventos_filtrados_kpi.filter(espacos__tipo='espaco')
        .values('espacos__nome').annotate(total=Count('id')).order_by('-total')[:5]
    )
    espacos_chart_data = {
        'labels': [item['espacos__nome'] for item in espacos_ranking if item['espacos__nome']],
        'data': [item['total'] for item in espacos_ranking if item['espacos__nome']],
    }
    itens_ranking = (
        eventos_filtrados_kpi.filter(espacos__tipo='item_servico')
        .values('espacos__nome').annotate(total=Count('id')).order_by('-total')[:5]
    )
    itens_chart_data = {
        'labels': [item['espacos__nome'] for item in itens_ranking if item['espacos__nome']],
        'data': [item['total'] for item in itens_ranking if item['espacos__nome']],
    }

    # --- 5. CONTEXTO PARA O TEMPLATE ---
    context = {
        'start_date': start_date_str,
        'end_date': end_date_str,
        'query': query, # Passa a query de volta para o formulário
        
        # KPIs (agora baseados nos filtros aplicados)
        'total_faturado': total_faturado_kpi,
        'total_a_receber': total_a_receber_kpi, 
        'num_eventos': num_eventos_kpi,
        'media_convidados': media_convidados_kpi,
        
        # Chart JSONs
        'faturamento_chart_json': json.dumps(faturamento_chart_data),
        'receita_categoria_json': json.dumps(receita_categoria_data),
        'espacos_chart_json': json.dumps(espacos_chart_data),
        'itens_chart_json': json.dumps(itens_chart_data), 
        
        # Extrato Paginado
        'page_obj': page_obj, # O objeto da página atual do Paginator
        'paginator': paginator, # O objeto Paginator (para controles de página)
        'object_list': page_obj.object_list # Para compatibilidade com template de paginação
    }
    return render(request, 'gestao/evento_relatorio.html', context)

# ==========================================================
# === VIEWS PARA ALTERAÇÃO DE STATUS DO EVENTO           ===
# ==========================================================

@login_required
@permission_required('gestao.change_evento', raise_exception=True)
@require_POST # Garante que só funciona com POST (formulário)
def confirmar_evento_status(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if evento.status == 'orcamento':
        evento.status = 'confirmado'
        evento.save()
        messages.success(request, f"O evento '{evento.nome_evento}' foi confirmado com sucesso!")
    else:
        messages.warning(request, "Ação inválida. O evento não está no status 'Orçamento'.")
    return redirect('evento_detail', pk=evento.pk)

@login_required
@permission_required('gestao.change_evento', raise_exception=True)
@require_POST
def realizar_evento_status(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    if evento.status == 'confirmado':
        # --- VERIFICAÇÃO DO SALDO ---
        if evento.saldo_devedor() <= 0:
            evento.status = 'realizado'
            evento.save()
            messages.success(request, f"O evento '{evento.nome_evento}' foi marcado como realizado!")
        else:
            messages.error(request, "Não é possível marcar como realizado. O evento ainda possui saldo devedor.")
        # --- FIM DA VERIFICAÇÃO ---
    else:
        messages.warning(request, "Ação inválida. O evento não está no status 'Confirmado'.")
    return redirect('evento_detail', pk=evento.pk)

@login_required
@permission_required('gestao.change_evento', raise_exception=True)
@require_POST
def cancelar_evento_status(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    # Permite cancelar se for Orçamento ou Confirmado
    if evento.status in ['orcamento', 'confirmado']:
        evento.status = 'cancelado'
        evento.save()
        messages.info(request, f"O evento '{evento.nome_evento}' foi cancelado.")
    # (Opcional: Descomente para permitir cancelar um evento Realizado)
    # elif evento.status == 'realizado':
    #     evento.status = 'cancelado'
    #     evento.save()
    #     messages.info(request, f"O evento '{evento.nome_evento}' foi cancelado.")
    else:
        messages.warning(request, f"Não é possível cancelar um evento com status '{evento.get_status_display()}'.")
    return redirect('evento_detail', pk=evento.pk)

# ==========================================================
# === VIEWS PARA CUSTO EVENTO                            ===
# ==========================================================

class CustoEventoCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'gestao.add_custo'
    raise_exception = True 

    model = CustoEvento
    form_class = CustoEventoForm
    template_name = 'gestao/custo_form.html'
    success_message = "Custo adicionado ao evento com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        # --- VERIFICAÇÃO DE STATUS ---
        evento = get_object_or_404(Evento, pk=self.kwargs['evento_pk'])
        if evento.status == 'orcamento':
            messages.error(request, "Não é possível adicionar custos a um evento que ainda é um orçamento. Confirme o evento primeiro.")
            return redirect('evento_detail', pk=evento.pk)
        # --- FIM DA VERIFICAÇÃO ---
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # 1. Busca o objeto do Evento usando a 'evento_pk' da URL
        evento = get_object_or_404(Evento, pk=self.kwargs['evento_pk'])
        
        # 2. Associa o evento ao custo ANTES de salvar no banco
        form.instance.evento = evento
        
        # 3. Adiciona a mensagem de sucesso (se não usar SuccessMessageMixin)
        # messages.success(self.request, self.success_message)
        
        # 4. Chama o método pai, que salva o objeto no banco
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        # Seu método aqui está CORRETO e é necessário para o botão "Cancelar"
        context = super().get_context_data(**kwargs)
        context['evento'] = get_object_or_404(Evento, pk=self.kwargs['evento_pk'])
        return context

    def get_success_url(self):
        # Seu método aqui está CORRETO
        return reverse_lazy('evento_detail', kwargs={'pk': self.kwargs['evento_pk']})

class CustoEventoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = 'gestao.change_custo'
    raise_exception = True

    model = CustoEvento
    form_class = CustoEventoForm
    template_name = 'gestao/custo_form.html'
    success_message = "Custo atualizado com sucesso!"

    def get_success_url(self):
        # CORREÇÃO: Pega o 'evento' a partir do 'custo' (self.object)
        # e retorna para a página de detalhe daquele evento.
        evento_pk = self.object.evento.pk
        return reverse_lazy('evento_detail', kwargs={'pk': evento_pk})

    def get_context_data(self, **kwargs):
        # CORREÇÃO: Adiciona o 'evento' ao contexto para o botão "Cancelar"
        context = super().get_context_data(**kwargs)
        context['evento'] = self.object.evento
        
        return context


class CustoEventoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_custo'
    raise_exception = True
    
    model = CustoEvento
    template_name = 'gestao/custo_confirm_delete.html'

    def get_success_url(self):
        # Pega o 'evento' a partir do 'custo' (self.object)
        # ANTES dele ser deletado.
        evento_pk = self.object.evento.pk
        return reverse_lazy('evento_detail', kwargs={'pk': evento_pk})

    def form_valid(self, form):
        messages.success(self.request, f"'{self.object}' foi excluído com sucesso.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        # Adicionar o 'evento' ao contexto para botões
        # de "Cancelar" na página de confirmação.
        context = super().get_context_data(**kwargs)
        context['evento'] = self.object.evento
        return context    

# ==========================================================
# === VIEWS PARA PAGAMENTO EVENTO                        ===
# ==========================================================

class PagamentoEventoCreateView(LoginRequiredMixin, CreateView):
    permission_required = 'gestao.add_pagamento'
    raise_exception = True

    model = Pagamento
    form_class = PagamentoEventoForm
    template_name = 'gestao/pagamento_form.html'
    success_message = "Pagamento adicionado ao evento com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        # --- VERIFICAÇÃO DE STATUS ---
        evento = get_object_or_404(Evento, pk=self.kwargs['evento_pk'])
        if evento.status == 'orcamento':
            messages.error(request, "Não é possível adicionar pagamentos a um evento que ainda é um orçamento. Confirme o evento primeiro.")
            return redirect('evento_detail', pk=evento.pk)
        # --- FIM DA VERIFICAÇÃO ---
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        # Associa o pagamento ao EVENTO
        evento = get_object_or_404(Evento, pk=self.kwargs['evento_pk'])
        form.instance.evento = evento
        return super().form_valid(form)
    
    def get_initial(self):
        """ Opcional: sugerir saldo devedor do evento """
        evento = get_object_or_404(Evento, pk=self.kwargs['evento_pk'])
        initial = super().get_initial()
        
        # Se você tiver um método 'saldo_devedor()' no seu modelo Evento:
        if hasattr(evento, 'saldo_devedor'):
            initial['valor'] = evento.saldo_devedor()
        return initial

    def get_context_data(self, **kwargs):
        # Envia o evento para o template (para o botão "Cancelar")
        context = super().get_context_data(**kwargs)
        context['evento'] = get_object_or_404(Evento, pk=self.kwargs['evento_pk'])
        return context

    def get_success_url(self):
        # Redireciona de volta para o EVENTO
        return reverse_lazy('evento_detail', kwargs={'pk': self.kwargs['evento_pk']})

class PagamentoEventoUpdateView(LoginRequiredMixin, UpdateView):
    permission_required = 'gestao.change_pagamento'
    raise_exception = True

    model = Pagamento
    form_class = PagamentoEventoForm
    template_name = 'gestao/pagamento_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['evento'] = self.object.evento
        return context
    
    def get_success_url(self):
        if self.object.evento:
            return reverse_lazy('evento_detail', kwargs={'pk': self.object.evento.pk})
        elif self.object.reserva:
            return reverse_lazy('reserva_detail', kwargs={'pk': self.object.reserva.pk})
        
        # Fallback
        messages.warning(self.request, "Pagamento sem evento ou reserva associado.")
        return reverse_lazy('eventos')

class PagamentoEventoDeleteView(LoginRequiredMixin, DeleteView):
    permission_required = 'gestao.delete_pagamento'
    raise_exception = True

    model = Pagamento
    template_name = 'gestao/pagamento_confirm_delete.html'
    
    def get_success_url(self):
        if self.object.evento:
            messages.success(self.request, f"Pagamento de R$ {self.object.valor} excluído do evento.")
            return reverse_lazy('evento_detail', kwargs={'pk': self.object.evento.pk})
        
        if self.object.reserva:
            messages.success(self.request, f"Pagamento de R$ {self.object.valor} excluído da reserva.")
            return reverse_lazy('reserva_detail', kwargs={'pk': self.object.reserva.pk})
        
        # Fallback: volta para lista de eventos
        messages.success(self.request, f"Pagamento de R$ {self.object.valor} excluído.")
        return reverse_lazy('eventos')


# ADICIONE ESTA NOVA VIEW DE DIAGNÓSTICO
def debug_s3_view(request):
    bucket_name = os.getenv('AWS_STORAGE_BUCKET_NAME')
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    region = os.getenv('AWS_S3_REGION_NAME')

    # Monta uma resposta HTML para vermos os resultados
    html = "<h1>Diagnóstico de Conexão S3</h1>"
    html += f"<p><b>Bucket a ser testado:</b> {bucket_name}</p>"
    html += f"<p><b>Região:</b> {region}</p>"
    html += f"<p><b>Access Key ID encontrada:</b> {'Sim' if access_key else 'NÃO'}</p>"
    
    if not all([bucket_name, access_key, secret_key, region]):
        html += "<p style='color: red;'><b>ERRO: Uma ou mais variáveis de ambiente da AWS não foram encontradas!</b></p>"
        return HttpResponse(html)

    try:
        # Tenta se conectar ao S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=boto3.session.Config(signature_version='s3v4')
        )
        
        # Tenta escrever um pequeno arquivo de teste
        test_content = "Teste de escrita bem-sucedido."
        test_key = "test-debug-file.txt"
        
        html += f"<p>Tentando escrever o arquivo '{test_key}' no bucket...</p>"
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content,
            ContentType='text/plain'
        )
        
        html += "<p style='color: green;'><b>SUCESSO! O arquivo de teste foi escrito no S3.</b></p>"
        html += "<p>Isso significa que as credenciais e permissões de escrita estão funcionando!</p>"
        
    except Exception as e:
        # Se qualquer erro ocorrer, exibe na tela
        html += f"<p style='color: red;'><b>FALHA NA CONEXÃO OU ESCRITA!</b></p>"
        html += f"<p><b>Mensagem de Erro do Boto3:</b></p>"
        html += f"<pre>{e}</pre>"

    return HttpResponse(html)