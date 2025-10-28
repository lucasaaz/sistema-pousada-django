import boto3
import os
from django.conf import settings
from botocore.exceptions import NoCredentialsError, ClientError
from datetime import timedelta
from decimal import Decimal

#===================================================================================#
# ARQUIVO: gestao/utils.py                                                          #
# DESCRIÇÃO: Funções utilitárias para upload de arquivos ao S3 e outras operações.  #
#===================================================================================#

def upload_file_to_s3(file_obj, bucket_name, object_name):
    """
    Envia um arquivo para um bucket S3.
    Retorna a URL do arquivo se for bem-sucedido, None se falhar.
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_S3_REGION_NAME')
    )
    
    try:
        file_obj.seek(0)
        s3_client.upload_fileobj(
            file_obj,
            bucket_name,
            object_name,
            ExtraArgs={'ContentType': 'image/jpeg', 'ACL': 'public-read'}
        )
        
        # Constrói a URL
        region = os.getenv('AWS_S3_REGION_NAME')
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{object_name}"
        return url

    except (NoCredentialsError, ClientError) as e:
        print(f"Erro no upload para o S3: {e}")
        return None
    
#===================================================================================#
# Função para calcular a tarifa completa com base nas regras fornecidas             #
#===================================================================================#

def calcular_tarifa_completa(chave_de_preco, checkin_date, checkout_date, num_adultos, num_criancas_12):
    tarifas = {
        "quarto": {
            "semana": {"individual": 115, "casal": 220, "acrescimo": 115},
            "fim_de_semana": {"individual": 140, "casal": 250, "pacote_2_dias": 450, "acrescimo": 140}
        },
        "quarto_familia": {
            "semana": {"individual": 115, "casal": 220, "acrescimo": 115},
            "fim_de_semana": {"individual": 140, "casal": 250, "pacote_2_dias": 450, "acrescimo": 140}
        },
        "coletivo": {
            "semana": {"por_pessoa": 100},
            "fim_de_semana": {"por_pessoa": 115}
        },
        "chale": {
            "semana": {"individual": 140, "casal": 270, "pacote_2_dias": 500, "acrescimo": 100},
            "fim_de_semana": {"individual": 160, "casal": 320, "pacote_2_dias": 600, "acrescimo": 120}
        }
    }

    num_diarias = (checkout_date - checkin_date).days
    valor_total_calculado = 0
    print(f"\n--- Calculando Tarifa ---")
    print(f"Chave: {chave_de_preco}, Checkin: {checkin_date}, Checkout: {checkout_date}, Adultos: {num_adultos}, Crianças: {num_criancas_12}, Diárias: {num_diarias}")
    
    # --- LÓGICA DE CÁLCULO DIA A DIA ---
    for i in range(num_diarias):
        data_atual = checkin_date + timedelta(days=i)
        periodo = 'fim_de_semana' if data_atual.weekday() >= 4 else 'semana'
        
        regras_tipo = tarifas.get(chave_de_preco, {})
        regras_periodo = regras_tipo.get(periodo, {})
        
        valor_diaria = 0
        
        if chave_de_preco == 'coletivo':
            valor_por_pessoa = regras_periodo.get('por_pessoa', 0)
            valor_adultos = num_adultos * valor_por_pessoa
            valor_criancas = num_criancas_12 * (valor_por_pessoa * Decimal('0.5'))
            valor_diaria = valor_adultos + valor_criancas
        else:
            # --- LÓGICA REFINADA PARA ADULTOS E CRIANÇAS ---
            # 1. Define a tarifa base com base no número de ADULTOS
            if num_adultos >= 2:
                valor_diaria = regras_periodo.get('casal', 0)
                adultos_base = 2
            else: # 1 adulto ou 0
                valor_diaria = regras_periodo.get('individual', 0)
                adultos_base = 1

            # 2. Calcula os extras
            adultos_extras = num_adultos - adultos_base
            criancas_extras = num_criancas_12
            
            if adultos_extras > 0 or criancas_extras > 0:
                valor_acrescimo = regras_periodo.get('acrescimo', 0)
                
                # Soma o valor dos adultos extras (pagam 100%)
                if adultos_extras > 0:
                    valor_diaria += adultos_extras * valor_acrescimo
                
                # Soma o valor das crianças extras (pagam 50%)
                if criancas_extras > 0:
                    valor_diaria += criancas_extras * (valor_acrescimo * Decimal('0.5'))

        valor_total_calculado += valor_diaria

    # --- LÓGICA DE PACOTES (SOBRESCREVE O CÁLCULO SE APLICÁVEL) ---
    # Pacote se aplica apenas para 2 adultos, 0 crianças de 6-12 e 2 diárias
    if num_diarias == 2 and num_adultos == 2 and num_criancas_12 == 0:
        periodo_checkin = 'fim_de_semana' if checkin_date.weekday() >= 4 else 'semana'
        regras_tipo = tarifas.get(chave_de_preco, {})
        regras_periodo = regras_tipo.get(periodo_checkin, {})
        if "pacote_2_dias" in regras_periodo:
            valor_total_calculado = regras_periodo["pacote_2_dias"]
            
    print(f"Valor Total Final (antes de ajuste): {valor_total_calculado}")
    return valor_total_calculado, []