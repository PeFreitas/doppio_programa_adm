# processador.py (Versão para Web - Com OAuth 2.0)

import logging
import os
from datetime import datetime
from pathlib import Path
from thefuzz import process
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- NOVA SEÇÃO DE CONFIGURAÇÃO E INICIALIZAÇÃO ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constantes e Configurações
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
CLIENT_SECRET_FILE = 'client_secret.json' # Aponta para o novo arquivo
TOKEN_FILE = 'token.json' # Arquivo que será criado após a primeira execução
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')

creds = None
# O arquivo token.json armazena os tokens de acesso e atualização do usuário.
# Ele é criado automaticamente quando o fluxo de autorização é concluído pela primeira vez.
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

# Se não houver credenciais (válidas), permite que o usuário faça login.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=8080)
    # Salva as credenciais para a próxima execução
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

try:
    gspread_client = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)
    logging.info("Credenciais do Google (OAuth 2.0) carregadas com sucesso.")
except Exception as e:
    logging.error(f"ERRO CRÍTICO ao carregar credenciais do Google: {e}", exc_info=True)
    creds = gspread_client = drive_service = None

# --- DEFINIÇÕES DE NEGÓCIO E MAPEAMENTO (Sua lógica de negócio permanece aqui) ---
mapeamento_fornecedores = {
    "cadeg": "MELHOR COMPRA DA CADEG", "rio de janeiro refrescos ltda": "RJ REFRESROS", "rio de janeiro refrescos": "RJ REFRESROS",
    "rio quality": "RIO QUALITY", "nossos sabores": "NOSSOS SABORES", "cafez": "CAFEZ COMERCIO VAREJISTA DE CAFÉ",
    "cafez varejista": "CAFEZ COMERCIO VAREJISTA DE CAFÉ", "choconata": "CHOCONATA IND E COM DE ALIMENTOS",
    "atelier dos sabores": "ATELIER DOS SABORES", "atelier": "ATELIER DOS SABORES", "brigadeiro": "ATELIER DOS SABORES",
    "brigadeiro industria": "ATELIER DOS SABORES", "brasfruto": "BRASFRUTO - AÇAÍ", "centralrj": "CENTRAL RJ",
    "kiko": "CRHISTIAN BECKER", "pgto kiko": "CRHISTIAN BECKER", "crhistian becker": "CRHISTIAN BECKER",
    "daniel santiago": "DON SANTIAGO", "gt": "GUSTAVO TREMONTI", "pgto gt": "GUSTAVO TREMONTI",
    "gustavo tremonti": "GUSTAVO TREMONTI", "illy": "ILLY", "nobredo": "NOBREDO", "peruchi sorvetes": "OGGI",
    "peruchi": "OGGI", "oggi": "OGGI", "quebra nozes": "QUEBRA NOZES IND E COM DE ALIM LTDA",
    "audax": "AUDAX CONTABILIDADE (TLKG e DOPPIO BUFFET)", "cartão": "CARTÃO DE CRÉDITO EMPRESARIAL",
    "cartão de crédito": "CARTÃO DE CRÉDITO EMPRESARIAL", "clube dos sabores": "CLUBE DOS SABORES",
    "cmd": "CMD - MENSALIDADE SISTEMA BEMATECH (TOTVS CHEF)", "cmd automação": "CMD - MENSALIDADE SISTEMA BEMATECH (TOTVS CHEF)",
    "outros": "OUTROS", "di brownie": "DI BROWNIE", "mj de moraes": "MJ DE MORAES",
    "sindrio": "SINDICATO DE BARES E RESTAURANTES DO RJ (SINDRIO)", "sindicato dos trab": "SINDICATO DE BARES E RESTAURANTES DO RJ (SINDRIO)",
    "sigabam": "SINDICATO DOS GARÇONS DO RJ (SIGABAM)", "sindicato dos garçons": "SINDICATO DOS GARÇONS DO RJ (SIGABAM)",
    "tkn rio": "TKN RIO (ALUGUEL MAQ. DE GELO)", "máquina de gelo": "TKN RIO (ALUGUEL MAQ. DE GELO)",
    "tortamania": "TORTAMANIA", "tudo legal": "TUDO LEGAL", "internet": "VIVO INTERNET",
    "telefonica brasil": "VIVO INTERNET", "zona zen": "ZONA ZEN", "encontro são conrrado": "ZONA ZEN",
    "fgts doppio": "GFD (FGTS DIGITAL) - DOPPIO BUFFET", "das doppio": "DAS (Simples) - DOPPIO BUFFET",
    "simples doppio": "DAS (Simples) - DOPPIO BUFFET", "fgts tlkg": "GFD (FGTS DIGITAL) - TLKG",
    "dctf doppio": "DCTFWeb DOPPIO BUFFET", "dctf tlkg": "DCTFWeb TLKG", "icms tlkg": "ICMS TLKG",
    "riopar": "RIOPAR (VT) - boleto", "vt boleto": "RIOPAR (VT) - boleto",
    "aluguel shopping": "CONDOMÍNIO/ALUGUEL BARRASHOPPING", "aluguel": "CONDOMÍNIO/ALUGUEL BARRASHOPPING",
    "parcelamento dctf tlkg": "PARCELAMENTO DCTFWeb TLKG - FEV25 - ATRASADO", "parcelamento": "PARCELAMENTO DCTFWeb TLKG - FEV25 - ATRASADO",
    "funcionarios": "FUNCIONARIOS", "maran": "MARAN COMERCIO DESCARTAVEIS", "maran com descart": "MARAN COMERCIO DESCARTAVEIS",
    "frozen": "FROZEN BISTRÔ", "bruno jose fischer": "FROZEN BISTRÔ", "bruno fischer": "FROZEN BISTRÔ",
    "alexandre ferreira": "BIA BOLOS", "alexandre": "BIA BOLOS", "bia bolos": "BIA BOLOS",
    "retirada socios": "RETIRADA SOCIOS", "si tecnologia": "SUISSE", "barra marapendi": "BARRA MARAPENDI",
    "marapendi": "BARRA MARAPENDI",
}

# --- FUNÇÕES DE LÓGICA INTERNA (Helpers) ---

def _padronizar_dados(dados_do_formulario):
    """
    Padroniza o nome do fornecedor usando fuzzy matching para encontrar a
    correspondência mais provável e obtém os IDs do Drive e Sheets.
    """
    nome_bruto = dados_do_formulario.get('fornecedor', '').lower().strip()
    data_vencimento_str = dados_do_formulario.get('vencimento', '')

    # --- LÓGICA DE FUZZY MATCHING ---
    nome_padronizado = "NÃO SEI"
    
    # Pega a lista de todos os nomes de fornecedores oficiais e únicos
    nomes_oficiais = list(set(mapeamento_fornecedores.values()))
    
    # Usa a biblioteca thefuzz para encontrar a melhor correspondência
    # A função extractOne retorna uma tupla: (nome_encontrado, score_de_similaridade)
    melhor_match = process.extractOne(nome_bruto, nomes_oficiais)
    
    # Se a similaridade for maior que 75 (em uma escala de 0 a 100), consideramos um match
    if melhor_match and melhor_match[1] > 75:
        nome_padronizado = melhor_match[0]
        logging.info(f"Fornecedor encontrado por similaridade: '{nome_bruto}' -> '{nome_padronizado}' (Score: {melhor_match[1]})")
    else:
        logging.warning(f"Nenhum fornecedor compatível encontrado para '{nome_bruto}'. Score foi muito baixo: {melhor_match[1] if melhor_match else 'N/A'}")

    # --- LÓGICA DOS IDs (continua a mesma) ---
    id_drive, id_sheets = None, None
    if data_vencimento_str:
        try:
            data_obj = datetime.strptime(data_vencimento_str, "%d/%m/%Y")
            id_drive = os.getenv(f"DRIVE_ID_MONTH_{data_obj.month}")
            id_sheets = os.getenv(f"SHEETS_ID_MONTH_{data_obj.month}")
        except ValueError:
            logging.warning(f"Data de vencimento inválida: '{data_vencimento_str}'")

    # Retorna um novo dicionário com os dados padronizados
    dados_padronizados = dados_do_formulario.copy()
    dados_padronizados['nome_padronizado'] = nome_padronizado
    dados_padronizados['id_drive'] = id_drive
    dados_padronizados['id_sheets'] = id_sheets
    
    return dados_padronizados


def _adicionar_nova_linha_sheets(dados):
    """Adiciona uma nova linha na planilha do Google Sheets com a ordem correta."""
    if not all([gspread_client, dados.get('id_sheets'), GOOGLE_SHEET_ID]):
        logging.error("Adição no Sheets cancelada: Cliente, ID da Planilha ou GID do Mês não configurado.")
        return False
    try:
        logging.info("Adicionando nova linha ao Google Sheets...")
        sheet_gid = dados['id_sheets'].split('gid=')[-1]
        worksheet = gspread_client.open_by_key(GOOGLE_SHEET_ID).get_worksheet_by_id(int(sheet_gid))
        
        # --- ORDEM CORRIGIDA DAS COLUNAS ---
        # Ordem: Conta, Meio Pagto, Nro NF, Valor, Data Emissão, Data Vencimento, Data Pagamento
        linha_para_adicionar = [
            dados.get('nome_padronizado', ''),
            dados.get('meio_pagamento', 'BOLETO'),  # Pega o valor do form, se não existir, usa 'BOLETO'
            dados.get('numero_nota', ''),
            dados.get('valor', ''),
            dados.get('emissao', ''),
            dados.get('vencimento', ''),
            ''  # Deixa a coluna "Data do pagamento" em branco por enquanto
        ]
        
        worksheet.append_row(linha_para_adicionar, value_input_option='USER_ENTERED')
        logging.info(f"Linha adicionada com sucesso na aba '{worksheet.title}'.")
        return True
    except Exception as e:
        logging.error(f"Erro ao adicionar linha no Google Sheets: {e}", exc_info=True)
        return False



def _executar_upload_drive(dados, caminhos_arquivos_locais, nomes_originais_arquivos):
    """Faz o upload de múltiplos arquivos para a pasta correta no Google Drive."""
    if not drive_service:
        logging.error("Upload para o Drive cancelado: Serviço do Drive não inicializado.")
        return False

    id_pasta_mes = dados.get('id_drive')
    nome_fornecedor = dados.get('nome_padronizado')

    if not id_pasta_mes or not nome_fornecedor or nome_fornecedor == "NÃO SEI":
        logging.error("Upload cancelado: ID do mês ou nome do fornecedor inválido.")
        return False

    try:
        # 1. Encontrar ou criar a pasta do fornecedor (apenas uma vez)
        query_pasta_fornecedor = f"'{id_pasta_mes}' in parents and name = '{nome_fornecedor}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = drive_service.files().list(q=query_pasta_fornecedor, fields="files(id, name)").execute()
        items = results.get('files', [])
        
        if not items:
            logging.info(f"Pasta para o fornecedor '{nome_fornecedor}' não encontrada. Criando...")
            folder_metadata = {'name': nome_fornecedor, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [id_pasta_mes]}
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            id_pasta_fornecedor = folder.get('id')
        else:
            id_pasta_fornecedor = items[0].get('id')

        # 2. Montar o prefixo do nome do arquivo (apenas uma vez)
        data_formatada = datetime.strptime(dados['vencimento'], "%d/%m/%Y").strftime("%d-%m-%Y")
        valor_formatado = dados['valor']
        prefixo_arquivo = f"{data_formatada} - R${valor_formatado}"
        
        # 3. Iterar e fazer o upload de cada arquivo
        for i, (caminho_local, nome_original) in enumerate(zip(caminhos_arquivos_locais, nomes_originais_arquivos)):
            parte_numero = i + 1
            extensao = Path(nome_original).suffix
            nome_final_arquivo = f"{prefixo_arquivo} - parte {parte_numero}{extensao}"

            logging.info(f"Fazendo upload de '{nome_final_arquivo}' para a pasta ID: {id_pasta_fornecedor}")

            file_metadata = {'name': nome_final_arquivo, 'parents': [id_pasta_fornecedor]}
            media = MediaFileUpload(caminho_local, mimetype='application/octet-stream', resumable=True)
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        logging.info(f"Upload de {len(caminhos_arquivos_locais)} parte(s) para o Drive concluído com sucesso.")
        return True
    except Exception as e:
        logging.error(f"Erro no processo do Google Drive: {e}", exc_info=True)
        return False

# --- FUNÇÃO PRINCIPAL ORQUESTRADORA (Chamada pelo app.py) ---

def processar_documento_com_dados_manuais(caminhos_arquivos, dados_formulario, nomes_originais_arquivos):
    """
    Função principal que orquestra o processo para múltiplos arquivos:
    1. Padroniza os dados recebidos do formulário.
    2. Adiciona UMA nova linha no Google Sheets.
    3. Faz o upload de TODOS os arquivos para o Google Drive.
    """
    if not creds:
        return {'status': 'ERRO', 'detalhes': 'Credenciais do Google não foram carregadas.'}

    # Etapa 1: Padronizar dados e obter IDs
    dados_completos = _padronizar_dados(dados_formulario)
    
    # Validação mínima
    if dados_completos.get('nome_padronizado') == "NÃO SEI" or not dados_completos.get('id_drive') or not dados_completos.get('id_sheets'):
        return {'status': 'ERRO', 'detalhes': 'Não foi possível identificar o fornecedor ou o mês de lançamento. Verifique o nome e a data de vencimento.'}

    # Etapa 2: Salvar no Sheets (apenas uma linha)
    sucesso_sheets = _adicionar_nova_linha_sheets(dados_completos)
    
    # Etapa 3: Salvar no Drive (todos os arquivos)
    sucesso_drive = _executar_upload_drive(dados_completos, caminhos_arquivos, nomes_originais_arquivos)

    if sucesso_sheets and sucesso_drive:
        return {'status': 'SUCESSO', 'detalhes': f'Novo lançamento criado no Sheets e {len(caminhos_arquivos)} arquivo(s) salvos no Drive.'}
    else:
        # Constrói uma mensagem de erro mais detalhada
        detalhes_erro = []
        if not sucesso_sheets: 
            detalhes_erro.append("Google Sheets")
        if not sucesso_drive: 
            detalhes_erro.append("Google Drive")
        return {'status': 'ERRO', 'detalhes': f'Falha ao salvar o lançamento em: {", ".join(detalhes_erro)}.'}
    
    