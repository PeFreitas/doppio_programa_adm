# backend/conta_azul_client.py
import requests
import os
from datetime import date

# Pega a chave da API do arquivo .env
API_KEY = os.getenv("CONTA_AZUL_API_KEY")
BASE_URL = "https://api.contaazul.com/v1"

def get_vendas_do_dia(data_busca: date):
    """
    Busca as vendas de um dia específico na API do Conta Azul.
    """
    headers = {'Authorization': f'Bearer {API_KEY}'}
    params = {'data_inicial': data_busca.strftime('%Y-%m-%d'), 'data_final': data_busca.strftime('%Y-%m-%d')}

    try:
        response = requests.get(f"{BASE_URL}/vendas", headers=headers, params=params)
        response.raise_for_status() # Lança um erro para respostas 4xx ou 5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar vendas no Conta Azul: {e}")
        return None

# Você criaria funções similares para buscar produtos, clientes, etc.
# E também funções para ENVIAR dados (POST, PUT).