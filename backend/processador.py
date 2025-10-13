# processador.py (Versão com Logs de Depuração)

import logging
import os
from datetime import datetime
from pathlib import Path
from decimal import Decimal, InvalidOperation

# Imports (permanecem os mesmos)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from thefuzz import process

# imports para OCR
import pytesseract
from pdf2image import convert_from_path
import re

# --- CONFIGURAÇÃO E INICIALIZAÇÃO (Permanece igual) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
creds = None
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=8080)
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())
try:
    gspread_client = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)
    logging.info("Credenciais do Google (OAuth 2.0) carregadas com sucesso.")
except Exception as e:
    logging.error(f"ERRO CRÍTICO ao carregar credenciais do Google: {e}", exc_info=True)
    creds = gspread_client = drive_service = None

# --- MAPEAMENTO DE FORNECEDORES ---
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


# --- FUNÇÕES DE MANIPULAÇÃO DE DADOS (Permanece igual) ---
def _normalize_valor_to_decimal(valor):
    if valor is None: return None
    try:
        valor_str = str(valor).replace('R$', '').strip().replace('.', '').replace(',', '.')
        return Decimal(valor_str)
    except (InvalidOperation, ValueError): return None

def _format_decimal_to_brl(valor_decimal):
    if valor_decimal is None: return ""
    formatted_brl = '{:,.2f}'.format(valor_decimal).replace(',', 'X').replace('.', ',').replace('X', '.')
    if formatted_brl.endswith('0'): return formatted_brl[:-1]
    return formatted_brl

def _padronizar_dados(dados_do_formulario):
    nome_bruto = dados_do_formulario.get('fornecedor', '').lower().strip()
    data_vencimento_str = dados_do_formulario.get('vencimento', '')
    nome_padronizado = "NÃO SEI"
    nomes_oficiais = list(set(mapeamento_fornecedores.values()))
    melhor_match = process.extractOne(nome_bruto, nomes_oficiais)
    if melhor_match and melhor_match[1] > 75: nome_padronizado = melhor_match[0]
    id_drive, id_sheets = None, None
    if data_vencimento_str:
        try:
            data_obj = datetime.strptime(data_vencimento_str, "%d/%m/%Y")
            id_drive = os.getenv(f"DRIVE_ID_MONTH_{data_obj.month}")
            id_sheets = os.getenv(f"SHEETS_ID_MONTH_{data_obj.month}")
        except ValueError: pass
    dados_padronizados = dados_do_formulario.copy()
    dados_padronizados['nome_padronizado'] = nome_padronizado
    dados_padronizados['id_drive'] = id_drive
    dados_padronizados['id_sheets'] = id_sheets
    valor_decimal = _normalize_valor_to_decimal(dados_do_formulario.get('valor'))
    dados_padronizados['valor_formatado_brl'] = _format_decimal_to_brl(valor_decimal)
    return dados_padronizados


# --- FUNÇÃO DE BUSCA E ATUALIZAÇÃO (VERSÃO FINAL E ROBUSTA) ---
def _buscar_e_atualizar_linha_existente(dados):
    if not all([gspread_client, dados.get('id_sheets'), GOOGLE_SHEET_ID]): return False
    try:
        logging.info("Iniciando verificação de duplicatas (método robusto)...")
        sheet_gid = dados['id_sheets'].split('gid=')[-1]
        worksheet = gspread_client.open_by_key(GOOGLE_SHEET_ID).get_worksheet_by_id(int(sheet_gid))
        
        # Usa get_all_values() para ler os dados brutos como texto
        all_data = worksheet.get_all_values()
        if not all_data: return False

        header = all_data[0]
        data_rows = all_data[1:]

        # Encontra o índice (posição) de cada coluna necessária
        try:
            conta_idx = header.index('Conta')
            valor_idx = header.index('Valor')
            vencimento_idx = header.index('Data de vencimento')
        except ValueError as e:
            logging.error(f"Coluna não encontrada no cabeçalho: {e}. Verifique os nomes das colunas na planilha.")
            return False

        fornecedor_chave = dados.get('nome_padronizado')
        valor_chave_decimal = _normalize_valor_to_decimal(dados.get('valor'))
        vencimento_chave = dados.get('vencimento')

        for index, row_data in enumerate(data_rows):
            # Acessa os dados da planilha pela posição da coluna
            fornecedor_planilha = row_data[conta_idx]
            valor_planilha_bruto = row_data[valor_idx]
            vencimento_planilha = row_data[vencimento_idx]
            
            valor_planilha_decimal = _normalize_valor_to_decimal(valor_planilha_bruto)

            if (fornecedor_planilha == fornecedor_chave and
                valor_planilha_decimal is not None and
                valor_chave_decimal is not None and
                valor_planilha_decimal == valor_chave_decimal and
                vencimento_planilha == vencimento_chave):
                
                logging.info(f"Linha duplicada encontrada na posição {index + 2}. Atualizando campos.")
                # ... (lógica de atualização permanece a mesma)
                mapeamento_colunas = { 'Meio Pagto': dados.get('meio_pagamento'), 'Nro NF': dados.get('numero_nota'), 'Data de Emissão da nota': dados.get('emissao') }
                células_para_atualizar = []
                for coluna, novo_valor in mapeamento_colunas.items():
                    try:
                        col_idx = header.index(coluna)
                        if (str(row_data[col_idx]).strip() == '') and novo_valor:
                            célula = gspread.Cell(row=index + 2, col=col_idx + 1, value=novo_valor)
                            células_para_atualizar.append(célula)
                    except (ValueError, IndexError): pass
                if células_para_atualizar:
                    worksheet.update_cells(células_para_atualizar, value_input_option='USER_ENTERED')
                return True

        logging.info("Nenhuma linha duplicada encontrada.")
        return False

    except Exception as e:
        logging.error(f"Erro ao buscar/atualizar no Google Sheets: {e}", exc_info=True)
        return False


# --- O RESTO DAS FUNÇÕES PERMANECE O MESMO ---
def _adicionar_nova_linha_sheets(dados):
    try:
        sheet_gid = dados['id_sheets'].split('gid=')[-1]
        worksheet = gspread_client.open_by_key(GOOGLE_SHEET_ID).get_worksheet_by_id(int(sheet_gid))
        linha_para_adicionar = [
            dados.get('nome_padronizado', ''),
            dados.get('meio_pagamento', 'BOLETO'),
            dados.get('numero_nota', ''),
            dados.get('valor_formatado_brl', ''),
            dados.get('emissao', ''),
            dados.get('vencimento', ''),
            ''
        ]
        worksheet.append_row(linha_para_adicionar, value_input_option='USER_ENTERED')
        return True
    except Exception as e: return False

def _executar_upload_drive(dados, caminhos_arquivos_locais, nomes_originais_arquivos):
    if not drive_service: return False
    id_pasta_mes = dados.get('id_drive')
    nome_fornecedor = dados.get('nome_padronizado')
    if not id_pasta_mes or not nome_fornecedor or nome_fornecedor == "NÃO SEI": return False
    try:
        query_pasta_fornecedor = f"'{id_pasta_mes}' in parents and name = '{nome_fornecedor}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = drive_service.files().list(q=query_pasta_fornecedor, fields="files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            folder_metadata = {'name': nome_fornecedor, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [id_pasta_mes]}
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            id_pasta_fornecedor = folder.get('id')
        else:
            id_pasta_fornecedor = items[0].get('id')
        data_formatada = datetime.strptime(dados['vencimento'], "%d/%m/%Y").strftime("%d-%m-%Y")
        valor_formatado = dados.get('valor_formatado_brl', '')
        prefixo_arquivo = f"{data_formatada} - R${valor_formatado}"
        for i, (caminho_local, nome_original) in enumerate(zip(caminhos_arquivos_locais, nomes_originais_arquivos)):
            parte_numero = i + 1
            extensao = Path(nome_original).suffix
            nome_final_arquivo = f"{prefixo_arquivo} - parte {parte_numero}{extensao}"
            file_metadata = {'name': nome_final_arquivo, 'parents': [id_pasta_fornecedor]}
            media = MediaFileUpload(caminho_local, mimetype='application/octet-stream', resumable=True)
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return True
    except Exception as e: return False

def processar_documento_com_dados_manuais(caminhos_arquivos, dados_formulario, nomes_originais_arquivos):
    if not creds: return {'status': 'ERRO', 'detalhes': 'Credenciais do Google não foram carregadas.'}
    dados_completos = _padronizar_dados(dados_formulario)
    if dados_completos.get('nome_padronizado') == "NÃO SEI" or not dados_completos.get('id_drive') or not dados_completos.get('id_sheets'):
        return {'status': 'ERRO', 'detalhes': 'Não foi possível identificar o fornecedor ou o mês de lançamento.'}
    linha_existe = _buscar_e_atualizar_linha_existente(dados_completos)
    sucesso_sheets = False
    mensagem_sheets = ""
    if linha_existe:
        sucesso_sheets = True
        mensagem_sheets = "Linha existente atualizada no Sheets"
    else:
        if _adicionar_nova_linha_sheets(dados_completos):
            sucesso_sheets = True
            mensagem_sheets = "Nova linha criada no Sheets"
        else:
            sucesso_sheets = False
    sucesso_drive = _executar_upload_drive(dados_completos, caminhos_arquivos, nomes_originais_arquivos)
    if sucesso_sheets and sucesso_drive:
        detalhes_sucesso = f'{mensagem_sheets} e {len(caminhos_arquivos)} arquivo(s) salvos no Drive.'
        return {'status': 'SUCESSO', 'detalhes': detalhes_sucesso}
    else:
        detalhes_erro = []
        if not sucesso_sheets: detalhes_erro.append("Google Sheets")
        if not sucesso_drive: detalhes_erro.append("Google Drive")
        return {'status': 'ERRO', 'detalhes': f'Falha em: {", ".join(detalhes_erro)}.'}


# --- FUNÇÕES DE OCR ---

def _extrair_texto_pdf_com_ocr(caminho_pdf):
    """Converte PDF para imagem e extrai texto com Tesseract."""
    try:
        poppler_path = os.getenv('POPPLER_PATH')
        imagens = convert_from_path(caminho_pdf, poppler_path=poppler_path)
        texto_completo = ""
        for img in imagens:
            texto_completo += pytesseract.image_to_string(img, lang='por') + "\n"
        logging.info("--- TEXTO BRUTO EXTRAÍDO DO PDF ---")
        logging.info(texto_completo)
        logging.info("------------------------------------")
        return texto_completo
    except Exception as e:
        logging.error(f"Erro durante o processo de OCR: {e}", exc_info=True)
        return ""

def _analisar_texto_bruto_comprovante(texto):
    """
    Analisa o texto bruto para extrair informações do comprovante com regras aprimoradas.
    """
    dados = {'fornecedor': '', 'valor': '', 'vencimento': '', 'pagamento': ''}
    texto_lower = texto.lower()
    
    # 1. Extração de Valor (mais específica)
    # [cite_start]Procura por "Valor: R$ 2.992,17" [cite: 8]
    match_valor = re.search(r'valor[:\s]*r\$\s*([\d.,]+)', texto_lower)
    if match_valor:
        dados['valor'] = match_valor.group(1).strip()
    
    # 2. Extração de Data de Pagamento (mais específica)
    # [cite_start]Procura por "data do debito", "data do pagamento", etc., seguido de uma data [cite: 14]
    match_pagamento = re.search(r'(?:data\s+d[oa]\s+d[eé]bito|pagamento)\s*(\d{2}/\d{2}/\d{4})', texto_lower)
    if match_pagamento:
        dados['pagamento'] = match_pagamento.group(1)
    else:
        # Fallback: pega a última data no formato DD/MM/YYYY se a busca específica falhar
        datas_encontradas = re.findall(r'\d{2}/\d{2}/\d{4}', texto)
        if datas_encontradas:
            dados['pagamento'] = datas_encontradas[-1]

    # 3. Extração de Fornecedor com regra de exclusão
    # [cite_start]O fornecedor é quem recebe, nunca a empresa que paga (TLKG) [cite: 3]
    try:
        # [cite_start]Encontra a seção "dados de quem recebeu" [cite: 4, 5]
        secao_recebedor = texto_lower.split('dados de quem')[1].split('recebeu')[1]
        
        # [cite_start]Dentro dessa seção, procura pela linha que começa com "Nome:" [cite: 6]
        match_fornecedor = re.search(r'nome[:\s]*([^\n]+)', secao_recebedor)
        if match_fornecedor:
            fornecedor = match_fornecedor.group(1).strip().upper()
            # Garante que o fornecedor extraído não é a própria empresa
            if 'tlkg' not in fornecedor.lower():
                dados['fornecedor'] = fornecedor
    except (IndexError, AttributeError):
        logging.warning("Não foi possível encontrar a seção 'Dados de quem recebeu' ou o campo 'Nome:'.")
        # Fallback: se a lógica acima falhar, tenta uma busca genérica
        match_fornecedor_generico = re.search(r'empresa[:\s]*([^\n]+)', texto_lower)
        if match_fornecedor_generico:
             fornecedor = match_fornecedor_generico.group(1).strip().upper()
             if 'tlkg' not in fornecedor.lower():
                dados['fornecedor'] = fornecedor

    # 4. NOVA REGRA: Se não houver data de vencimento, usar a data de pagamento
    if not dados.get('vencimento') and dados.get('pagamento'):
        logging.info("Data de vencimento não encontrada. Usando a data de pagamento como fallback.")
        dados['vencimento'] = dados['pagamento']
        
    logging.info(f"Dados extraídos pelo OCR: {dados}")
    return dados

def analisar_comprovante_ocr(lista_caminhos_pdf, dados_parciais):
    """
    Função orquestradora que processa múltiplos PDFs e agrega os resultados.
    """
    dados_agregados = {
        'fornecedor': '', 'valor': '', 'vencimento': '', 'pagamento': ''
    }

    # Itera sobre cada PDF enviado
    for caminho_pdf in lista_caminhos_pdf:
        texto_extraido = _extrair_texto_pdf_com_ocr(caminho_pdf)
        if not texto_extraido:
            continue # Pula para o próximo arquivo se este falhar

        dados_do_pdf_atual = _analisar_texto_bruto_comprovante(texto_extraido)

        # Atualiza os dados agregados, preenchendo apenas os campos vazios
        for campo, valor in dados_do_pdf_atual.items():
            if not dados_agregados.get(campo) and valor:
                dados_agregados[campo] = valor

    # Combina os resultados: dados do usuário têm prioridade máxima
    dados_finais = {
        'fornecedor': dados_parciais.get('fornecedor') or dados_agregados.get('fornecedor'),
        'meio_pagamento': dados_parciais.get('meio_pagamento'),
        'valor': dados_parciais.get('valor') or dados_agregados.get('valor'),
        'vencimento': dados_parciais.get('vencimento') or dados_agregados.get('vencimento'),
        'pagamento': dados_parciais.get('pagamento') or dados_agregados.get('pagamento'),
    }
    
    return {'status': 'SUCESSO', 'dados': dados_finais}