# ==============================================================================
# ARQUIVO: gestao/urls.py (ATUALIZADO)
# DESCRIÇÃO: Adiciona os links para as novas páginas de clientes.
# ==============================================================================
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .views import (
    dashboard_view, 
    consulta_disponibilidade_view,
    cliente_list_view,
    cliente_create_view,
    cliente_update_view,     
    cliente_delete_view,     
)

urlpatterns = [
    # URLs do Dashboard
    path('', dashboard_view, name='dashboard'),
    path('api/consulta-disponibilidade/', consulta_disponibilidade_view, name='consulta_disponibilidade'),
    
    # URLs para Clientes
    path('clientes/', cliente_list_view, name='cliente_list'),
    path('clientes/adicionar/', cliente_create_view, name='cliente_add'),
    path('clientes/editar/<int:pk>/', cliente_update_view, name='cliente_edit'),      
    path('clientes/debug/upload-check/', views.upload_debug_view, name='cliente_upload_debug'),
    path('clientes/excluir/<int:pk>/', cliente_delete_view, name='cliente_delete'),   

    # URLs para Tipos de Acomodação
    path('tipos-acomodacao/', views.TipoAcomodacaoListView.as_view(), name='tipo_acomodacao_list'),
    path('tipos-acomodacao/adicionar/', views.TipoAcomodacaoCreateView.as_view(), name='tipo_acomodacao_add'),
    path('tipos-acomodacao/editar/<int:pk>/', views.TipoAcomodacaoUpdateView.as_view(), name='tipo_acomodacao_edit'),
    path('tipos-acomodacao/excluir/<int:pk>/', views.TipoAcomodacaoDeleteView.as_view(), name='tipo_acomodacao_delete'),

    # URLs para Acomodações
    path('acomodacoes/', views.AcomodacaoListView.as_view(), name='acomodacao_list'),
    path('acomodacoes/adicionar/', views.AcomodacaoCreateView.as_view(), name='acomodacao_add'),
    path('acomodacoes/editar/<int:pk>/', views.AcomodacaoUpdateView.as_view(), name='acomodacao_edit'),
    path('acomodacoes/excluir/<int:pk>/', views.AcomodacaoDeleteView.as_view(), name='acomodacao_delete'),

    # URLs para Reservas
    path('reservas/', views.ReservaListView.as_view(), name='reserva_list'),
    path('reservas/adicionar/', views.ReservaCreateView.as_view(), name='reserva_add'),
    path('reservas/<int:pk>/', views.ReservaDetailView.as_view(), name='reserva_detail'),
    path('reservas/editar/<int:pk>/', views.ReservaUpdateView.as_view(), name='reserva_edit'),
    path('reservas/cancelar/<int:pk>/', views.ReservaDeleteView.as_view(), name='reserva_delete'),
    path('select2/', include('django_select2.urls')),
    path('api/buscar-clientes/', views.buscar_clientes_view, name='api_buscar_clientes'),
    path('reservas/<int:pk>/cancelar-status/', views.cancelar_reserva_status_view, name='cancelar_reserva_status'), # ROTA PARA A AÇÃO DE CANCELAR O STATUS

    # URLs para as ações de check-in e check-out
    path('reservas/checkin/<int:pk>/', views.fazer_checkin, name='fazer_checkin'),
    path('reservas/checkout/<int:pk>/', views.fazer_checkout, name='fazer_checkout'),
    path('reservas/<int:pk>/imprimir-contrato/', views.imprimir_contrato_checkin, name='imprimir_contrato_checkin'),

    # URLs para Upload de Arquivos
    path("reserva/<int:reserva_id>/arquivos/", views.arquivos_reserva, name="arquivos_reserva"),
    path("arquivo/<int:arquivo_id>/abrir/", views.abrir_arquivo, name="abrir_arquivo"),

    # URLs para a Gestão de Estoque
    path('estoque/', views.ItemEstoqueListView.as_view(), name='item_estoque_list'),
    path('estoque/adicionar/', views.ItemEstoqueCreateView.as_view(), name='item_estoque_add'),
    path('estoque/editar/<int:pk>/', views.ItemEstoqueUpdateView.as_view(), name='item_estoque_edit'),
    path('estoque/excluir/<int:pk>/', views.ItemEstoqueDeleteView.as_view(), name='item_estoque_delete'),
    path('estoque/<int:item_pk>/compras/', views.compra_estoque_view, name='compra_estoque_list'),

    # URLs para Frigobar e Consumo
    path('acomodacoes/<int:acomodacao_pk>/frigobar/', views.frigobar_detail_view, name='frigobar_detail'),
    path('frigobar/remover-item/<int:item_frigobar_pk>/', views.remover_item_frigobar, name='remover_item_frigobar'),
    path('consumo/<int:pk>/excluir/', views.ConsumoDeleteView.as_view(), name='consumo_delete'),
    path('consumo/<int:pk>/editar/', views.ConsumoUpdateView.as_view(), name='consumo_edit'),
    path('reservas/<int:reserva_pk>/adicionar-consumo/', views.consumo_create_view, name='consumo_add'),
    path('item-frigobar/<int:pk>/editar/', views.ItemFrigobarUpdateView.as_view(), name='editar_item_frigobar'),
    path('item-frigobar/<int:item_frigobar_pk>/registrar-consumo/', views.registrar_consumo_view, name='registrar_consumo_frigobar'),

    # URLs para Pagamentos
    path('reserva/<int:reserva_pk>/pagamento/adicionar/', views.pagamento_create_view, name='pagamento_add'),
    path('pagamento/<int:pk>/editar/', views.PagamentoUpdateView.as_view(), name='pagamento_edit'),
    path('pagamento/<int:pk>/excluir/', views.PagamentoDeleteView.as_view(), name='pagamento_delete'),

    # URLs para Formas de Pagamento
    path('pagamentos/formas/', views.FormaPagamentoListView.as_view(), name='forma_pagamento_list'),
    path('pagamentos/formas/adicionar/', views.FormaPagamentoCreateView.as_view(), name='forma_pagamento_add'),
    path('pagamentos/formas/editar/<int:pk>/', views.FormaPagamentoUpdateView.as_view(), name='forma_pagamento_edit'),
    path('pagamentos/formas/excluir/<int:pk>/', views.FormaPagamentoDeleteView.as_view(), name='forma_pagamento_delete'),
    path('reservas/<int:reserva_pk>/adicionar-pagamento/', views.pagamento_create_view, name='pagamento_add'),

    # URLs para Vagas de Estacionamento
    path('estacionamento/', views.VagaEstacionamentoListView.as_view(), name='vaga_estacionamento_list'),
    path('estacionamento/adicionar/', views.VagaEstacionamentoCreateView.as_view(), name='vaga_estacionamento_add'),
    path('estacionamento/editar/<int:pk>/', views.VagaEstacionamentoUpdateView.as_view(), name='vaga_estacionamento_edit'),
    path('estacionamento/excluir/<int:pk>/', views.VagaEstacionamentoDeleteView.as_view(), name='vaga_estacionamento_delete'),

    # URLs para Funcionários
    path('funcionarios/', views.FuncionarioListView.as_view(), name='funcionario_list'),
    path('funcionarios/adicionar/', views.FuncionarioCreateView.as_view(), name='funcionario_add'),
    path('funcionarios/editar/<int:pk>/', views.FuncionarioUpdateView.as_view(), name='funcionario_edit'),
    path('funcionarios/status/<int:pk>/', views.toggle_funcionario_status, name='funcionario_toggle_status'),
    # URLs de Autenticação
    path('login/', auth_views.LoginView.as_view(template_name='gestao/login.html',redirect_authenticated_user=True), name='login'), # Redireciona se o utilizador já estiver logado
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'), # Para onde redirecionar após o logout

    # URLs para Configurações do Hotel
    path('configuracoes/hotel/', views.configuracao_hotel_view, name='configuracao_hotel'),

    # URLs para Relatórios
    path('relatorios/acomodacoes/', views.relatorio_acomodacoes_view, name='relatorio_acomodacoes'),

    # URL para o Dashboard Financeiro
    path('financeiro/', views.financeiro_dashboard_view, name='financeiro'),

    # URLs para Gerenciar Gastos
    path('gastos/<int:pk>/editar/', views.GastoUpdateView.as_view(), name='gasto_edit'),
    path('gastos/<int:pk>/excluir/', views.GastoDeleteView.as_view(), name='gasto_delete'),

    # URLs para Gerenciar Categorias de Gasto
    path('financeiro/categorias/', views.CategoriaGastoListView.as_view(), name='categoria_gasto_list'),
    path('financeiro/categorias/adicionar/', views.CategoriaGastoCreateView.as_view(), name='categoria_gasto_add'),
    path('financeiro/categorias/<int:pk>/editar/', views.CategoriaGastoUpdateView.as_view(), name='categoria_gasto_edit'),
    path('financeiro/categorias/<int:pk>/excluir/', views.CategoriaGastoDeleteView.as_view(), name='categoria_gasto_delete'),

    # URL para a API de verificação de duplicidade de CPF ou e-mail
    path('api/verificar-duplicidade/', views.verificar_duplicidade_view, name='api_verificar_duplicidade'),

    ## URL para debug de S3
    path('debug-s3/', views.debug_s3_view, name='debug_s3'),

    # URL para a API de geração de URL de upload
    path('api/gerar-url-upload/', views.gerar_url_upload_view, name='api_gerar_url_upload'),

    # URL para enviar e-mail de confirmação de reserva
    path('reservas/<int:pk>/enviar-email/', views.enviar_email_reserva_view, name='enviar_email_reserva'),

    # URL para a API de cálculo de tarifa
    path('api/calcular-tarifa/', views.calcular_tarifa_view, name='api_calcular_tarifa'),
]
