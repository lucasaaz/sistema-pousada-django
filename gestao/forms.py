# ==============================================================================
# ARQUIVO: gestao/forms.py (NOVO FICHEIRO)
# DESCRIÇÃO: Define os formulários do sistema, seguindo as boas práticas do Django.
# ==============================================================================
from django import forms
from django.utils import timezone
from django.forms import ModelForm
from django_select2.forms import Select2Widget
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm
from .models import Cliente, Acomodacao, TipoAcomodacao, Reserva, ItemEstoque, ItemFrigobar, Consumo, FormaPagamento, Pagamento, VagaEstacionamento, ConfiguracaoHotel, Gasto, CategoriaGasto, ArquivoReserva, CompraEstoque

# Formulário para Clientes
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente

        # Campos que aparecerão no formulário
        fields = [
            'nome_completo', 'cpf', 'data_nascimento', 'sexo', 'email', 'telefone', 
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado','foto'
        ] # Atualizado 24.09.25
        # Adiciona classes do Bootstrap para estilizar os campos
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo do cliente'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '000.000.000-00'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sexo': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'cep': forms.TextInput(attrs={'class': 'form-control', 'id': 'cep-input'}),
            'logradouro': forms.TextInput(attrs={'class': 'form-control', 'id': 'logradouro-input'}),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'complemento': forms.TextInput(attrs={'class': 'form-control'}),
            'bairro': forms.TextInput(attrs={'class': 'form-control', 'id': 'bairro-input'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control', 'id': 'cidade-input'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'id': 'estado-input'}),
            'foto': forms.FileInput(attrs={'class': 'd-none'}),
        }

# Formulario para Tipos de Acomodação
class TipoAcomodacaoForm(forms.ModelForm):
    """Formulário para criar e editar Tipos de Acomodação."""
    class Meta:
        model = TipoAcomodacao
        fields = ['nome', 'descricao']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# Formulario para Acomodações
class AcomodacaoForm(forms.ModelForm):
    """Formulário para criar e editar Acomodações."""
    class Meta:
        model = Acomodacao
        fields = ['numero', 'tipo', 'status', 'descricao', 'capacidade', 'qtd_camas']
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'capacidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'qtd_camas': forms.NumberInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

# Formulario para Reservas
class ReservaForm(forms.ModelForm):

    # Crie um campo de texto normal que será o campo de busca visível
    cliente_busca = forms.CharField(
        label='Cliente',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite o nome ou CPF do cliente para buscar...',
            'autocomplete': 'off' # Impede o autocomplete padrão do navegador
        })
    )
    
    """Formulário para criar e editar Reservas."""
    class Meta:
        model = Reserva
        fields = ['valor_total_diarias', 'cliente_busca', 'cliente', 'acomodacao', 'placa_automovel', 'data_checkin', 'data_checkout', 'num_adultos', 'num_criancas_5', 'num_criancas_12', 'status'] # Atualizado 18.09.25
        widgets = {
            'valor_total_diarias': forms.NumberInput(attrs={'class': 'form-control', 'id': 'valor-total-input'}),
            'cliente': forms.HiddenInput(),
            'acomodacao': forms.Select(attrs={'class': 'form-select'}),
            'placa_automovel': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'AAA-1234'}),
            'data_checkin': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'data_checkout': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'num_adultos': forms.NumberInput(attrs={'class': 'form-control'}), # Atualizado 18.09.25
            'num_criancas_5': forms.NumberInput(attrs={'class': 'form-control'}), # Atualizado 18.09.25
            'num_criancas_12': forms.NumberInput(attrs={'class': 'form-control'}), # Atualizado 18.09.25
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_data_checkin(self):
        data = self.cleaned_data.get('data_checkin')
        # Se a data existir e for "ingênua", torna ela "ciente" do fuso horário
        if data and timezone.is_naive(data):
            # Assumindo que a hora digitada é no fuso horário do seu projeto (ex: America/Sao_Paulo)
            return timezone.make_aware(data)
        return data

    def clean_data_checkout(self):
        data = self.cleaned_data.get('data_checkout')
        if data and timezone.is_naive(data):
            return timezone.make_aware(data)
        return data
    
    def clean(self):
        """
        Validação customizada para garantir que a data de check-out é posterior
        à data de check-in e que não há conflitos de reserva.
        """
        cleaned_data = super().clean()
        data_checkin = cleaned_data.get("data_checkin")
        data_checkout = cleaned_data.get("data_checkout")
        acomodacao = cleaned_data.get("acomodacao")
        num_adultos = cleaned_data.get("num_adultos", 0)
        num_criancas_12 = cleaned_data.get("num_criancas_12", 0)

        num_pessoas = num_adultos + num_criancas_12
        
        # --- Validação de Capacidade ---
        if acomodacao and num_pessoas > acomodacao.capacidade:
            raise forms.ValidationError(
                f"O número de hóspedes ({num_pessoas}) excede a capacidade máxima da acomodação ({acomodacao.capacidade})."
            )

        if data_checkin and data_checkout and data_checkin >= data_checkout:
            raise forms.ValidationError("A data de check-out deve ser posterior à data de check-in.")
            
        if acomodacao and data_checkin and data_checkout:
            # Exclui a própria reserva da verificação (útil na edição)
            conflitos = Reserva.objects.filter(
                acomodacao=acomodacao,
                data_checkin__lt=data_checkout,
                data_checkout__gt=data_checkin,
            ).exclude(
                status='cancelada' # Ignora as canceladas
            ).exclude(
                pk=self.instance.pk # Continua ignorando a própria reserva na edição
            )

            if conflitos.exists():
                raise forms.ValidationError(f"A acomodação '{acomodacao}' já está reservada para este período.")
                
        return cleaned_data
    
# Formulario para Estoque
class ItemEstoqueForm(forms.ModelForm):
    """Formulário para criar e editar Itens de Estoque."""
    class Meta:
        model = ItemEstoque
        fields = ['nome', 'descricao', 'quantidade', 'preco_venda']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'preco_venda': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class CompraEstoqueForm(forms.ModelForm):
    class Meta:
        model = CompraEstoque
        fields = ['quantidade', 'preco_compra_unitario', 'fornecedor', 'data_compra']
        widgets = {
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
            'preco_compra_unitario': forms.NumberInput(attrs={'class': 'form-control'}),
            'fornecedor': forms.TextInput(attrs={'class': 'form-control'}),
            'data_compra': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

# Formulário específico para editar a quantidade de um item no frigobar
class ItemFrigobarUpdateForm(forms.ModelForm):
    """
    Formulário específico para editar a quantidade de um item no frigobar.
    """
    class Meta:
        model = ItemFrigobar
        fields = ['quantidade']
        widgets = {
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
# Formulario para Itens de Frigobar
class AbastecerFrigobarForm(forms.ModelForm):
    """Formulário para adicionar um item a um frigobar."""
    class Meta:
        model = ItemFrigobar
        fields = ['item', 'quantidade']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# Formulario para Consumos
class ConsumoForm(forms.ModelForm):
    """Formulário para registar um novo consumo a uma reserva."""
    class Meta:
        model = Consumo
        fields = ['item', 'quantidade']
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limita a escolha de itens para apenas aqueles que têm estoque > 0
        self.fields['item'].queryset = ItemEstoque.objects.filter(quantidade__gt=0)

# Formulario para editar um consumo existente
class ConsumoUpdateForm(forms.ModelForm):
    class Meta:
        model = Consumo
        fields = ['quantidade']
        widgets = {
            'quantidade': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
# Formulario para Pagamentos
class PagamentoForm(forms.ModelForm):
    class Meta:
        model = Pagamento
        fields = ['forma_pagamento', 'valor', 'data_pagamento']
        widgets = {
            'forma_pagamento': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control'}),
            'data_pagamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

# Formulários para Forma de Pagamentos
class FormaPagamentoForm(forms.ModelForm):
    class Meta:
        model = FormaPagamento
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PagamentoForm(forms.ModelForm):
    class Meta:
        model = Pagamento
        fields = ['forma_pagamento', 'valor']
        widgets = {
            'forma_pagamento': forms.Select(attrs={'class': 'form-select'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# Formulário para Vagas de Estacionamento
class VagaEstacionamentoForm(forms.ModelForm):
    class Meta:
        model = VagaEstacionamento
        fields = ['numero_vaga', 'disponivel', 'acomodacao_vinculada']
        widgets = {
            'numero_vaga': forms.TextInput(attrs={'class': 'form-control'}),
            'disponivel': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'acomodacao_vinculada': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Torna o campo de acomodação não obrigatório
        self.fields['acomodacao_vinculada'].required = False

# Formulários para Funcionários (Utilizadores do Sistema)
class FuncionarioCreationForm(UserCreationForm):
    # Adicionamos campos extras ao formulário de criação de utilizador padrão
    first_name = forms.CharField(max_length=30, required=True, help_text='Obrigatório.')
    last_name = forms.CharField(max_length=30, required=True, help_text='Obrigatório.')
    email = forms.EmailField(max_length=254, help_text='Obrigatório. Use um email válido.')
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'groups')

class FuncionarioUpdateForm(forms.ModelForm):
    # Formulário para editar um utilizador existente
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'groups', 'is_active']

# Formulário para Configurações do Hotel
class ConfiguracaoHotelForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoHotel
        fields = ['nome', 'endereco', 'logo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

# Formulários para Financeira
class CategoriaGastoForm(forms.ModelForm):
    class Meta:
        model = CategoriaGasto
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
        }

class GastoForm(ModelForm):
    class Meta:
        model = Gasto
        fields = ['descricao', 'valor', 'categoria']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
        }

# Formulário para Upload de Arquivos
class ArquivoReservaForm(forms.ModelForm):
    class Meta:
        model = ArquivoReserva
        fields = ["arquivo"]