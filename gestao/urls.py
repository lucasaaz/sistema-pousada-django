# ==============================================================================
# ARQUIVO: hotel_project/gestao/urls.py
# DESCRIÇÃO: URLs específicas do app de gestão.
# ==============================================================================
from django.urls import path
from .views import dashboard_view, consulta_disponibilidade_view

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('api/consulta-disponibilidade/', consulta_disponibilidade_view, name='consulta_disponibilidade'),
    # Adicionar outras URLs aqui: /clientes, /reservas, /checkin, etc.
]