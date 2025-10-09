# processador.py (versão final com logs detalhados)

import logging
import os
import re
from datetime import datetime

# Imports para o OCR
import pytesseract
from PIL import Image

# Imports para as APIs do Google
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURAÇÃO DAS APIS DO GOOGLE ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
CREDENCIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')

try:
    creds = Credentials.from_service_account_file(CREDENCIALS_FILE, scopes=SCOPES)
    gspread_client = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)
    logging.info("Credenciais do Google carregadas com sucesso no processador.")
except FileNotFoundError:
    logging.error(f"ERRO CRÍTICO: O arquivo de credenciais '{CREDENCIALS_FILE}' não foi encontrado. As funções do Google não funcionarão.")
    creds = gspread_client = drive_service = None
except Exception as e:
    logging.error(f"ERRO CRÍTICO ao carregar credenciais do Google: {e}")
    creds = gspread_client = drive_service = None


# --- DICIONÁRIO DE FORNECEDORES ---
# (O dicionário completo que já tínhamos vai aqui)
mapeamento_fornecedores = {
    "cadeg": "MELHOR COMPRA DA CADEG", "rio de janeiro refrescos ltda": "RJ REFRESROS", "rio quality": "RIO QUALITY",
    "nossos sabores": "NOSSOS SABORES", "cafez": "CAFEZ COMERCIO VAREJISTA DE CAFÉ", "cafez varejista": "CAFEZ COMERCIO VAREJISTA DE CAFÉ",
    "choconata": "CHOCONATA IND DE ALIMENTOS", "atelier dos sabores": "ATELIER DOS SABORES", "atelier": "ATELIER DOS SABORES",
    "brigadeiro": "ATELIER DOS SABORES", "brigadeiro industria": "ATELIER DOS SABORES", "brasfruto": "BRASFRUTO - AÇAÍ",
    "centralrj": "CENTRAL RJ", "kiko": "CRHISTIAN BECKER", "pgto kiko": "CRHISTIAN BECKER", "crhistian becker": "CRHISTIAN BECKER",
    "daniel santiago": "DON SANTIAGO", "gt": "GUSTAVO TREMONTI", "pgto gt": "GUSTAVO TREMONTI", "gustavo tremonti": "GUSTAVO TREMONTI",
    "illy": "ILLY", "nobredo": "NOBREDO", "peruchi sorvetes": "OGGI", "peruchi": "OGGI", "oggi": "OGGI",
    "quebra nozes": "QUEBRA NOZES IND E COM DE ALIM LTDA", "audax": "AUDAX CONTABILIDADE (TLKG e DOPPIO BUFFET)",
    "cartão": "CARTÃO DE CRÉDITO EMPRESARIAL", "cartão de crédito": "CARTÃO DE CRÉDITO EMPRESARIAL", "clube dos sabores": "CLUBE DOS SABORES",
    "cmd": "CMD - MENSALIDADE SISTEMA BEMATECH (TOTVS CHEF)", "cmd automação": "CMD - MENSALIDADE SISTEMA BEMATECH (TOTVS CHEF)",
    "outros": "OUTROS", "di brownie": "DI BROWNIE", "mj de moraes": "MJ DE MORAES",
    "sindrio": "SINDICATO DE BARES E RESTAURANTES DO RJ (SINDRIO)", "sindicato dos trab": "SINDICATO DE BARES E RESTAURANTES DO RJ (SINDRIO)",
    "sigabam": "SINDICATO DOS GARÇONS DO RJ (SIGABAM)", "sindicato dos garçons": "SINDICATO DOS GARÇONS DO RJ (SIGABAM)",
    "tkn rio": "TKN RIO (ALUGUEL MAQ. DE GELO)", "máquina de gelo": "TKN RIO (ALUGUEL MAQ. DE GELO)", "tortamania": "TORTAMANIA",
    "tudo legal": "TUDO LEGAL", "internet": "VIVO INTERNET", "telefonica brasil": "VIVO INTERNET", "zona zen": "ZONA ZEN",
    "encontro são conrrado": "ZONA ZEN", "fgts doppio": "GFD (FGTS DIGITAL) - DOPPIO BUFFET", "das doppio": "DAS (Simples) - DOPPIO BUFFET",
    "simples doppio": "DAS (Simples) - DOPPIO BUFFET", "fgts tlkg": "GFD (FGTS DIGITAL) - TLKG", "dctf doppio": "DCTFWeb DOPPIO BUFFET",
    "dctf tlkg": "DCTFWeb TLKG", "icms tlkg": "ICMS TLKG", "riopar": "RIOPAR (VT) - boleto", "vt boleto": "RIOPAR (VT) - boleto",
    "aluguel shopping": "CONDOMÍNIO/ALUGUEL BARRASHOPPING", "aluguel": "CONDOMÍNIO/ALUGUEL BARRASHOPPING",
    "parcelamento dctf tlkg": "PARCELAMENTO DCTFWeb TLKG - FEV25 - ATRASADO", "parcelamento": "PARCELAMENTO DCTFWeb TLKG - FEV25 - ATRASADO",
    "funcionarios": "FUNCIONARIOS", "maran": "MARAN COMERCIO DESCARTAVEIS", "maran com descart": "MARAN COMERCIO DESCARTAVEIS",
    "frozen": "FROZEN BISTRÔ", "bruno jose fischer": "FROZEN BISTRÔ", "bruno fischer": "FROZEN BISTRÔ",
    "alexandre ferreira": "BIA BOLOS", "alexandre": "BIA BOLOS", "bia bolos": "BIA BOLOS",
    "retirada socios": "RETIRADA SOCIOS", "si tecnologia": "SUISSE", "barra marapendi": "BARRA MARAPENDI", "marapendi": "BARRA MARAPENDI",
}


def analisar_texto_bruto(texto):
    """ Versão Final com Logs - Detetive especialista em boletos. """
    logging.info("Iniciando análise do texto bruto...")
    dados = {'fornecedor': '', 'vencimento': '', 'valor': '', 'emissao': '', 'numero_nota': ''}
    regex_data = r'\d{2}/\d{2}/\d{2,4}'
    regex_valor = r'(\d{1,3}(?:\.\d{3})*,\d{2})'
    
    datas_encontradas_str = sorted(list(set(re.findall(regex_data, texto))))
    datas_encontradas_obj = [datetime.strptime(d, "%d/%m/%Y") for d in datas_encontradas_str]

    if datas_encontradas_obj:
        logging.info(f"Datas (únicas e ordenadas) encontradas: {datas_encontradas_str}")
        dados['emissao'] = min(datas_encontradas_obj).strftime("%d/%m/%Y")
        logging.info(f"  -> Data de EMISSÃO definida como a menor data: '{dados['emissao']}'")
        dados['vencimento'] = max(datas_encontradas_obj).strftime("%d/%m/%Y")
        logging.info(f"  -> Data de VENCIMENTO definida como a maior data: '{dados['vencimento']}'")

    for i, linha in enumerate(texto.split('\n')):
        if not linha.strip(): continue
        linha_lower = linha.lower()

        if not dados['fornecedor']:
            for apelido, nome_oficial in mapeamento_fornecedores.items():
                if apelido in linha_lower and len(apelido) > 3:
                    dados['fornecedor'] = linha.strip().replace('“', '')
                    logging.info(f"  -> Fornecedor encontrado por correspondência de apelido ('{apelido}'): '{dados['fornecedor']}'")
                    break
        
        if 'r$' in linha_lower and not dados['valor']:
            match = re.search(regex_valor, linha, re.IGNORECASE)
            if match:
                dados['valor'] = match.group(1)
                logging.info(f"  -> VALOR encontrado pela chave 'R$': '{dados['valor']}'")

        if dados['emissao'] and dados['emissao'] in linha and not dados['numero_nota']:
            linha_sem_data = linha.replace(dados['emissao'], '').strip()
            numeros_restantes = re.findall(r'\b\d+/?\d*\b', linha_sem_data)
            if numeros_restantes:
                dados['numero_nota'] = numeros_restantes[0]
                logging.info(f"  -> NÚMERO da nota isolado na linha da emissão: '{dados['numero_nota']}'")
                
    logging.info(f"Análise finalizada. Dados brutos extraídos: {dados}")
    return dados


def padronizar_dados(dados_extraidos):
    """ Recebe os dados brutos extraídos do OCR e os padroniza. """
    logging.info(f"Iniciando padronização para o fornecedor: '{dados_extraidos.get('fornecedor')}'")
    nome_bruto = dados_extraidos.get('fornecedor', '').lower().strip()
    data_bruta = dados_extraidos.get('vencimento', '')
    
    nome_padronizado = "NÃO SEI"
    for apelido, nome_oficial in mapeamento_fornecedores.items():
        if apelido in nome_bruto:
            nome_padronizado = nome_oficial
            logging.info(f"  -> Nome do fornecedor padronizado para: '{nome_padronizado}'")
            break
            
    id_drive, id_sheets = None, None
    try:
        if data_bruta:
            data_obj = datetime.strptime(data_bruta, "%d/%m/%Y")
            chave_drive = f"DRIVE_ID_MONTH_{data_obj.month}"
            chave_sheets = f"SHEETS_ID_MONTH_{data_obj.month}"
            id_drive = os.getenv(chave_drive)
            id_sheets = os.getenv(chave_sheets)
            logging.info(f"  -> Mês {data_obj.month} identificado. IDs: Drive='{id_drive}', Sheets='{id_sheets}'")
    except Exception as e:
        logging.error(f"Não foi possível processar a data para obter IDs: {data_bruta}. Erro: {e}")

    return {"nome_padronizado": nome_padronizado, "id_drive": id_drive, "id_sheets": id_sheets, **dados_extraidos}


def extrair_dados_do_arquivo(caminho_arquivo):
    """ Função principal que gerencia o processo de OCR para uma imagem. """
    logging.info(f"FUNÇÃO 'extrair_dados_do_arquivo' INICIADA para o arquivo: '{caminho_arquivo}'")
    
    # Adicionando uma verificação extra para ver se o arquivo existe antes de tentar abrir
    if not os.path.exists(caminho_arquivo):
        logging.error(f"  -> O arquivo temporário não foi encontrado no caminho: {caminho_arquivo}")
        return {}

    try:
        logging.info("  -> Tentando abrir a imagem com a biblioteca PIL...")
        imagem = Image.open(caminho_arquivo)
        logging.info("  -> Imagem aberta com sucesso.")
        
        logging.info("  -> CHAMANDO TESSERACT (pytesseract) para extrair o texto...")
        texto_completo = pytesseract.image_to_string(imagem, lang='por')
        logging.info("  -> Tesseract finalizou a execução.")
        
        logging.info(f"--- TEXTO BRUTO EXTRAÍDO ---\n{texto_completo}\n-----------------------------")
        
        dados_brutos = analisar_texto_bruto(texto_completo)
        return dados_brutos
        
    except Exception as e:
        # Este log agora vai imprimir o erro completo, com a linha e o motivo.
        logging.error("ERRO CRÍTICO NO BLOCO TRY...EXCEPT de 'extrair_dados_do_arquivo'.", exc_info=True)
        # Adicionamos um print() como garantia extra, caso o logging falhe por algum motivo.
        print(f"!!! PRINT DE ERRO EM 'extrair_dados_do_arquivo': {e} !!!")
        return {}
    
# --- FUNÇÕES REAIS DO GOOGLE COM LOGS DETALHADOS ---

def adicionar_linha_sheets(dados_finais):
    logging.info(f"--- INICIANDO PROCESSO GOOGLE SHEETS ---")
    if not gspread_client: 
        logging.error("Cliente Google Sheets não inicializado. Verifique as credenciais.")
        return False
    
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    sheet_gid_str = dados_finais.get('id_sheets')
    
    if not sheet_id or not sheet_gid_str:
        logging.warning("Não foi possível adicionar ao Sheets: ID da planilha ou da aba não encontrado nos dados finais.")
        return False
        
    try:
        logging.info(f"Abrindo planilha com ID: {sheet_id}")
        spreadsheet = gspread_client.open_by_key(sheet_id)
        
        sheet_gid = sheet_gid_str.split('gid=')[-1]
        worksheet = spreadsheet.get_worksheet_by_id(int(sheet_gid))
        logging.info(f"Aba '{worksheet.title}' encontrada com sucesso.")
        
        linha_para_adicionar = [
            dados_finais.get('nome_padronizado'), dados_finais.get('numero_nota'),
            dados_finais.get('emissao'), dados_finais.get('vencimento'),
            dados_finais.get('valor')
        ]
        logging.info(f"  -> Adicionando linha: {linha_para_adicionar}")
        worksheet.append_row(linha_para_adicionar)
        logging.info("  -> SUCESSO: Linha adicionada na planilha!")
        return True
    except Exception as e:
        logging.error(f"  -> FALHA ao adicionar linha no Google Sheets: {e}")
        return False


def realizar_upload_drive(caminho_arquivo, nome_arquivo_original, dados_finais):
    logging.info(f"--- INICIANDO PROCESSO GOOGLE DRIVE ---")
    if not drive_service:
        logging.error("Serviço Google Drive não inicializado. Verifique as credenciais.")
        return False

    id_pasta_mes = dados_finais.get('id_drive')
    nome_fornecedor = dados_finais.get('nome_padronizado')

    if not id_pasta_mes or not nome_fornecedor or nome_fornecedor == "NÃO SEI":
        logging.warning(f"Upload cancelado. Motivo: ID da pasta do mês ('{id_pasta_mes}') ou nome do fornecedor ('{nome_fornecedor}') inválido.")
        return False
        
    try:
        # 1. Procurar se a subpasta do fornecedor já existe
        logging.info(f"Procurando por pasta '{nome_fornecedor}' dentro da pasta do mês (ID: {id_pasta_mes})")
        query = f"'{id_pasta_mes}' in parents and name = '{nome_fornecedor}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        
        id_pasta_final = None
        if not items:
            logging.info(f"  -> Pasta para '{nome_fornecedor}' não encontrada. Criando...")
            folder_metadata = {'name': nome_fornecedor, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [id_pasta_mes]}
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            id_pasta_final = folder.get('id')
            logging.info(f"  -> Pasta criada com ID: {id_pasta_final}")
        else:
            id_pasta_final = items[0].get('id')
            logging.info(f"  -> Pasta '{nome_fornecedor}' já existe. Usando ID: {id_pasta_final}")

        # 2. Fazer o upload do arquivo para a pasta final
        logging.info(f"Iniciando upload do arquivo '{nome_arquivo_original}' para a pasta de destino.")
        file_metadata = {'name': nome_arquivo_original, 'parents': [id_pasta_final]}
        media = MediaFileUpload(caminho_arquivo, mimetype='application/octet-stream', resumable=True)
        drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logging.info("  -> SUCESSO: Upload realizado para o Google Drive!")
        return True
    except Exception as e:
        logging.error(f"  -> FALHA no processo do Google Drive: {e}")
        return False