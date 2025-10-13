# ==============================================================================
# ARQUIVO: pousada_project/gestao/admin.py
# DESCRIÇÃO: Regista os modelos para que apareçam no painel de administração.
# ==============================================================================
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
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

@admin.register(Cliente)
class ClienteAdmin(SimpleHistoryAdmin): 
    list_display = ('nome_completo', 'cpf', 'telefone', 'email', 'logradouro', 'data_cadastro',)
    search_fields = ('nome_completo', 'cpf')
    history_list_display = ['nome_completo', 'cpf', 'telefone', 'email', 'logradouro', 'data_cadastro',]
    history_change_list_template = "admin/simple_history/change_list.html"

@admin.register(Reserva)
class ReservaAdmin(SimpleHistoryAdmin): 
    list_display = ('id', 'cliente', 'acomodacao', 'placa_automovel', 'data_checkin', 'data_checkout', 'num_adultos', 'num_criancas_5', 'num_criancas_12', 'status', 'valor_total_diarias', 'valor_consumo', 'valor_total_pago',)
    list_filter = ('status', 'acomodacao__tipo')
    search_fields = ('cliente__nome_completo', 'acomodacao__numero')
    history_list_display = ['cliente', 'acomodacao', 'placa_automovel', 'data_checkin', 'data_checkout', 'num_adultos', 'num_criancas_5', 'num_criancas_12', 'status', 'valor_total_diarias', 'valor_consumo', 'valor_total_pago',]
    history_change_list_template = "admin/simple_history/change_list.html"

@admin.register(Acomodacao)
class AcomodacaoAdmin(SimpleHistoryAdmin): 
    list_display = ('nome_display', 'tipo', 'status', 'capacidade', 'qtd_camas', 'descricao',)
    list_filter = ('tipo', 'status')
    search_fields = ('numero', 'tipo__nome')
    history_list_display = ['nome_display', 'tipo', 'status', 'capacidade', 'qtd_camas', 'descricao',]
    history_change_list_template = "admin/simple_history/change_list.html"

@admin.register(TipoAcomodacao)
class TipoAcomodacaoAdmin(SimpleHistoryAdmin): 
    list_display = ('nome', 'descricao',)
    search_fields = ('nome',)
    history_list_display = ['nome', 'descricao',]
    history_change_list_template = "admin/simple_history/change_list.html"

@admin.register(Gasto)
class GastoAdmin(SimpleHistoryAdmin): 
    list_display = ('categoria', 'valor', 'data_gasto',)
    list_filter = ('categoria', 'data_gasto')
    search_fields = ('categoria__nome',)
    history_list_display = ['categoria', 'valor', 'data_gasto',]
    history_change_list_template = "admin/simple_history/change_list.html"

@admin.register(Consumo)
class ConsumoAdmin(SimpleHistoryAdmin): 
    list_display = ('reserva', 'item', 'quantidade', 'preco_unitario', 'data_consumo',)
    list_filter = ('data_consumo',)
    search_fields = ('reserva__id', 'item__nome')
    history_list_display = ['reserva', 'item', 'quantidade', 'preco_unitario', 'data_consumo',]
    history_change_list_template = "admin/simple_history/change_list.html"

@admin.register(Pagamento)
class PagamentoAdmin(SimpleHistoryAdmin):   
    list_display = ('reserva', 'forma_pagamento', 'valor', 'data_pagamento',)
    list_filter = ('forma_pagamento', 'data_pagamento')
    search_fields = ('reserva__id',)
    history_list_display = ['reserva', 'forma_pagamento', 'valor', 'data_pagamento',]
    history_change_list_template = "admin/simple_history/change_list.html"

@admin.register(ItemEstoque)
class ItemEstoqueAdmin(SimpleHistoryAdmin): 
    list_display = ('nome', 'descricao', 'quantidade', 'preco_venda',)
    search_fields = ('nome',)
    history_list_display = ['nome', 'descricao', 'quantidade', 'preco_venda',]
    history_change_list_template = "admin/simple_history/change_list.html"

@admin.register(FormaPagamento)
class FormaPagamentoAdmin(SimpleHistoryAdmin): 
    list_display = ('nome',)
    search_fields = ('nome',)
    history_list_display = ['nome',]
    history_change_list_template = "admin/simple_history/change_list.html"

@admin.register(CategoriaGasto)
class CategoriaGastoAdmin(SimpleHistoryAdmin): 
    list_display = ('nome',)
    search_fields = ('nome',)
    history_list_display = ['nome',]
    history_change_list_template = "admin/simple_history/change_list.html"

@admin.register(VagaEstacionamento)
class VagaEstacionamentoAdmin(SimpleHistoryAdmin): 
    list_display = ('numero_vaga', 'disponivel', 'acomodacao_vinculada',)
    list_filter = ('numero_vaga',)
    search_fields = ('numero_vaga',)
    history_list_display = ['numero_vaga', 'disponivel', 'acomodacao_vinculada',]
    history_change_list_template = "admin/simple_history/change_list.html"

@admin.register(Frigobar)
class FrigobarAdmin(SimpleHistoryAdmin): 
    list_display = ('acomodacao',)
    search_fields = ('acomodacao__numero',)
    history_list_display = ['acomodacao',]
    history_change_list_template = "admin/simple_history/change_list.html"
    
@admin.register(ItemFrigobar)
class ItemFrigobarAdmin(SimpleHistoryAdmin):     
    list_display = ('frigobar', 'item', 'quantidade',)
    search_fields = ('frigobar__acomodacao__numero', 'item__nome')
    history_list_display = ['frigobar', 'item', 'quantidade',]
    history_change_list_template = "admin/simple_history/change_list.html"

@admin.register(ConfiguracaoHotel)
class ConfiguracaoHotelAdmin(SimpleHistoryAdmin): 
    list_display = ('nome','endereco',)
    history_list_display = ['nome','endereco',]
    history_change_list_template = "admin/simple_history/change_list.html"
