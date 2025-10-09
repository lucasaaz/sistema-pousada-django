# ==============================================================================
# ARQUIVO: pousada_project/gestao/admin.py
# DESCRIÇÃO: Regista os modelos para que apareçam no painel de administração.
# ==============================================================================
from django.contrib import admin
from .models import (
    ConfiguracaoHotel,
    Cliente,
    TipoAcomodacao,
    Acomodacao,
    VagaEstacionamento,
    ItemEstoque,
    Frigobar,
    ItemFrigobar,
    Reserva,
    Consumo,
    FormaPagamento,
    Pagamento,
    CategoriaGasto,
    Gasto,
)

# A forma mais simples de registar os modelos é usando admin.site.register
admin.site.register(ConfiguracaoHotel)
admin.site.register(Cliente)
admin.site.register(TipoAcomodacao)
admin.site.register(Acomodacao)
admin.site.register(VagaEstacionamento)
admin.site.register(ItemEstoque)
admin.site.register(Frigobar)
admin.site.register(ItemFrigobar)
admin.site.register(Reserva)
admin.site.register(Consumo)
admin.site.register(FormaPagamento)
admin.site.register(Pagamento)
admin.site.register(CategoriaGasto)
admin.site.register(Gasto)