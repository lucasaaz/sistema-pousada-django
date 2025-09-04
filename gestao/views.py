# ==============================================================================
# ARQUIVO: hotel_project/gestao/views.py
# DESCRIÇÃO: Lógica principal do sistema (backend).
# ==============================================================================
from django.shortcuts import render
from django.http import JsonResponse
from datetime import datetime
from .models import Reserva, Acomodacao

# View de exemplo para o Dashboard
def dashboard_view(request):
    """
    Exibe a página principal com estatísticas rápidas.
    """
    # A lógica para buscar dados do banco seria inserida aqui.
    # Ex: número de check-ins, check-outs, taxa de ocupação, etc.
    context = {
        'total_reservas_hoje': 5, # Valor de exemplo
        'taxa_ocupacao': 75.5, # Valor de exemplo
    }
    return render(request, 'dashboard.html', context)

# View de exemplo para a consulta de disponibilidade de quartos (para ser usada com AJAX)
def consulta_disponibilidade_view(request):
    """
    Verifica quais acomodações estão disponíveis entre duas datas.
    """
    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')

    # Validação simples das datas
    if not data_inicio_str or not data_fim_str:
        return JsonResponse({'error': 'Datas de início e fim são obrigatórias.'}, status=400)

    try:
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Formato de data inválido. Use AAAA-MM-DD.'}, status=400)
    
    # Lógica para encontrar acomodações já reservadas no período
    reservas_conflitantes = Reserva.objects.filter(
        data_checkin__lt=data_fim,
        data_checkout__gt=data_inicio,
        status__in=['confirmada', 'checkin']
    ).values_list('acomodacao_id', flat=True)
    
    # Busca todas as acomodações que NÃO estão na lista de conflitantes
    acomodacoes_disponiveis = Acomodacao.objects.exclude(id__in=reservas_conflitantes).filter(status='disponivel')
    
    # Prepara os dados para enviar como JSON
    data = [{
        'id': ac.id,
        'numero': ac.numero,
        'tipo': ac.tipo.nome,
        'valor_diaria': f"{ac.valor_diaria:.2f}".replace('.', ',')
    } for ac in acomodacoes_disponiveis]
    
    return JsonResponse(data, safe=False)

# Outras views (CRUD de clientes, checkout, relatórios) seriam criadas aqui.
# Por exemplo: cliente_list_view, cliente_create_view, reserva_create_view, etc.


































































































# # gestao/views.py
# from django.shortcuts import render, get_object_or_404, redirect
# from django.http import JsonResponse
# from .models import Acomodacao, Reserva, Cliente
# from datetime import datetime

# # Exemplo de uma view para a Dashboard
# def dashboard(request):
#     # Lógica para buscar dados para a dashboard
#     num_checkins_hoje = Reserva.objects.filter(data_checkin=datetime.today().date()).count()
#     num_checkouts_hoje = Reserva.objects.filter(data_checkout=datetime.today().date()).count()
#     taxa_ocupacao = (Acomodacao.objects.filter(status='ocupado').count() / Acomodacao.objects.all().count()) * 100
    
#     context = {
#         'checkins_hoje': num_checkins_hoje,
#         'checkouts_hoje': num_checkouts_hoje,
#         'taxa_ocupacao': round(taxa_ocupacao, 2)
#     }
#     return render(request, 'dashboard.html', context)

# # Exemplo de uma view para consultar disponibilidade (usada por AJAX)
# def consulta_disponibilidade(request):
#     data_inicio_str = request.GET.get('data_inicio')
#     data_fim_str = request.GET.get('data_fim')
    
#     data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
#     data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
    
#     # Encontra acomodações que JÁ ESTÃO reservadas no período
#     reservas_conflitantes = Reserva.objects.filter(
#         data_checkin__lt=data_fim,
#         data_checkout__gt=data_inicio
#     ).values_list('acomodacao_id', flat=True)
    
#     # Busca todas as acomodações que NÃO ESTÃO na lista de conflitantes
#     acomodacoes_disponiveis = Acomodacao.objects.exclude(id__in=reservas_conflitantes)
    
#     # Prepara os dados para enviar como JSON
#     data = [{
#         'id': acomodacao.id,
#         'numero': acomodacao.numero,
#         'tipo': acomodacao.tipo.nome,
#         'valor_diaria': f"{acomodacao.valor_diaria:.2f}"
#     } for acomodacao in acomodacoes_disponiveis]
    
#     return JsonResponse(data, safe=False)

# # Exemplo de uma view para listar clientes
# def lista_clientes(request):
#     clientes = Cliente.objects.all()
#     return render(request, 'clientes/lista_clientes.html', {'clientes': clientes})

# # Exemplo de view para o processo de Check-in
# def fazer_checkin(request, reserva_id):
#     reserva = get_object_or_404(Reserva, id=reserva_id)
#     if reserva.status == 'confirmada':
#         reserva.status = 'checkin'
#         reserva.acomodacao.status = 'ocupado'
#         reserva.save()
#         reserva.acomodacao.save()
#         # Adicionar mensagem de sucesso
#     return redirect('pagina_detalhe_reserva', reserva_id=reserva.id)

# # ... Outras views para CRUD de clientes, acomodações, checkout, relatórios, etc.