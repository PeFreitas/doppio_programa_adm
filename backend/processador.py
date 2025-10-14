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




def _buscar_e_atualizar_linha_existente(dados):
    if not all([gspread_client, dados.get('id_sheets'), GOOGLE_SHEET_ID]): return False
    try:
        logging.info("Iniciando verificação de duplicatas (lógica final)...")
        sheet_gid = dados['id_sheets'].split('gid=')[-1]
        worksheet = gspread_client.open_by_key(GOOGLE_SHEET_ID).get_worksheet_by_id(int(sheet_gid))
        
        all_data = worksheet.get_all_values()
        if not all_data: return False

        header = all_data[0]
        data_rows = all_data[1:]

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
            fornecedor_planilha = row_data[conta_idx]
            valor_planilha_bruto = row_data[valor_idx]
            vencimento_planilha = row_data[vencimento_idx]
            
            valor_planilha_decimal = _normalize_valor_to_decimal(valor_planilha_bruto)

            # A verificação de duplicata com os 3 campos obrigatórios
            if (fornecedor_planilha == fornecedor_chave and
                valor_planilha_decimal is not None and
                valor_chave_decimal is not None and
                valor_planilha_decimal == valor_chave_decimal and
                vencimento_planilha == vencimento_chave):
                
                logging.info(f"Linha duplicada encontrada na posição {index + 2}. Verificando campos para complementar.")
                
                # Mapeia todos os campos que podem ser preenchidos
                mapeamento_colunas = {
                    'Meio Pagto': dados.get('meio_pagamento'),
                    'Nro NF': dados.get('numero_nota'),
                    'Data de Emissão da nota': dados.get('emissao'),
                    'Data do pagamento': dados.get('pagamento')
                }
                
                células_para_atualizar = []
                for coluna, novo_valor in mapeamento_colunas.items():
                    # Só tenta atualizar se um novo valor foi enviado
                    if novo_valor:
                        try:
                            col_idx = header.index(coluna)
                            # E a regra de ouro: só atualiza se a célula estiver VAZIA
                            if str(row_data[col_idx]).strip() == '':
                                célula = gspread.Cell(row=index + 2, col=col_idx + 1, value=novo_valor)
                                células_para_atualizar.append(célula)
                        except (ValueError, IndexError):
                            logging.warning(f"Coluna '{coluna}' não encontrada na planilha. Ignorando.")
                            pass
                
                if células_para_atualizar:
                    worksheet.update_cells(células_para_atualizar, value_input_option='USER_ENTERED')
                    logging.info(f"{len(células_para_atualizar)} célula(s) foram preenchidas na linha existente.")
                else:
                    logging.info("Nenhuma célula em branco precisou ser preenchida.")

                return True # Indica que uma duplicata foi encontrada e tratada

        logging.info("Nenhuma linha duplicada correspondente foi encontrada.")
        return False # Indica que nenhuma duplicata foi encontrada

    except Exception as e:
        logging.error(f"Erro ao buscar/atualizar no Google Sheets: {e}", exc_info=True)
        return False



def _adicionar_nova_linha_sheets(dados):
    try:
        logging.info("Criando nova linha na planilha...")
        sheet_gid = dados['id_sheets'].split('gid=')[-1]
        worksheet = gspread_client.open_by_key(GOOGLE_SHEET_ID).get_worksheet_by_id(int(sheet_gid))
        
        # Estrutura base da linha. Os valores correspondem às colunas:
        # Conta, Meio Pagto, Nro NF, Valor, Data de Emissão da nota, Data de vencimento, Data do pagamento
        linha_base = {
            'Conta': dados.get('nome_padronizado', ''),
            'Meio Pagto': dados.get('meio_pagamento', 'BOLETO'),
            'Nro NF': '',
            'Valor': dados.get('valor_formatado_brl', ''),
            'Data de Emissão da nota': '',
            'Data de vencimento': dados.get('vencimento', ''),
            'Data do pagamento': ''
        }

        # Preenche os campos específicos de NOTA ou COMPROVANTE
        if dados.get('numero_nota'): # Se for uma Nota Fiscal
            logging.info("É uma NOTA FISCAL. Preenchendo campos de NF e Emissão.")
            linha_base['Nro NF'] = dados.get('numero_nota', '')
            linha_base['Data de Emissão da nota'] = dados.get('emissao', '')
        elif dados.get('pagamento'): # Se for um Comprovante
            logging.info("É um COMPROVANTE. Preenchendo campo de Data do pagamento.")
            linha_base['Data do pagamento'] = dados.get('pagamento', '')

        # Pega o cabeçalho para garantir a ordem correta das colunas
        header = worksheet.row_values(1)
        
        # Monta a lista final na ordem exata do cabeçalho da planilha
        linha_para_adicionar = [linha_base.get(coluna, '') for coluna in header]

        worksheet.append_row(linha_para_adicionar, value_input_option='USER_ENTERED')
        logging.info("Nova linha adicionada com sucesso.")
        return True
    except Exception as e:
        logging.error(f"Erro ao adicionar nova linha no Google Sheets: {e}", exc_info=True)
        return False
    
    
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

# --- SUBSTITUA A FUNÇÃO DE OCR PELA VERSÃO FINAL E CORRETA ---

def _extrair_texto_pdf_com_ocr(caminho_pdf):
    """Converte PDF para imagem e extrai texto com Tesseract."""
    try:
        # --- CORREÇÃO DEFINITIVA ---
        # Como o Poppler já está no PATH do sistema, não precisamos
        # especificar o caminho manualmente. A biblioteca o encontrará sozinha.
        logging.info("Poppler está no PATH. Deixando a biblioteca encontrá-lo automaticamente.")
        
        # Chamamos a função sem o argumento 'poppler_path'
        imagens = convert_from_path(caminho_pdf)
        
        texto_completo = ""
        for img in imagens:
            texto_completo += pytesseract.image_to_string(img, lang='por') + "\n"
        
        logging.info("--- TEXTO BRUTO EXTRAÍDO DO PDF ---")
        logging.info(texto_completo)
        logging.info("------------------------------------")
        return texto_completo
        
    except Exception as e:
        # A mensagem de erro agora será a original da biblioteca, que é mais precisa.
        logging.error(f"Erro durante o processo de OCR: {e}", exc_info=True)
        return ""


def _analisar_texto_bruto_comprovante(texto):
    """
    Analisa o texto bruto usando uma abordagem híbrida:
    - Usa thefuzz para encontrar o fornecedor mais provável no texto todo.
    - Usa regex para extrair com precisão o valor e a data.
    """
    dados = {'fornecedor': '', 'valor': '', 'vencimento': '', 'pagamento': ''}
    logging.info("Iniciando análise de OCR com lógica híbrida (thefuzz + regex).")

    # 1. ENCONTRAR O FORNECEDOR COM THEFUZZ
    nomes_conhecidos = list(mapeamento_fornecedores.keys())
    melhor_match = process.extractOne(texto, nomes_conhecidos, score_cutoff=85)
    
    if melhor_match:
        nome_encontrado = melhor_match[0]
        dados['fornecedor'] = nome_encontrado
        logging.info(f"Fornecedor encontrado com a biblioteca thefuzz: '{nome_encontrado}' com score {melhor_match[1]}")

    # 2. EXTRAIR O VALOR COM REGEX (VERSÃO CORRIGIDA)
    valores_encontrados = re.findall(r'R\$\s*([\d.,]+)', texto)
    if valores_encontrados:
        # CORREÇÃO: Apenas captura o valor como texto, sem o manipular.
        # A função de normalização cuidará da conversão.
        dados['valor'] = valores_encontrados[-1].strip()
        logging.info(f"Valor encontrado com regex: R$ {dados['valor']}")

    # 3. EXTRAIR A DATA DE PAGAMENTO COM REGEX
    datas_encontradas = re.findall(r'(\d{2}/\d{2}/\d{4})', texto)
    if datas_encontradas:
        dados['pagamento'] = datas_encontradas[-1]
        logging.info(f"Data de pagamento encontrada com regex: {dados['pagamento']}")

    # 4. REGRA DE VENCIMENTO (FALLBACK)
    if not dados.get('vencimento') and dados.get('pagamento'):
        logging.info("Data de vencimento não encontrada. Usando a data do pagamento como fallback.")
        dados['vencimento'] = dados['pagamento']
        
    logging.info(f"Dados extraídos pelo OCR (lógica híbrida): {dados}")
    return dados


def analisar_comprovante_ocr(lista_caminhos_pdf, dados_parciais):
    """
    Função orquestradora que processa múltiplos PDFs e agrega os resultados
    com base nas regras de negócio (maior valor, data mais tardia).
    """
    dados_agregados = {
        'fornecedor': '',
        'valor': None,
        'pagamento': None
    }

    logging.info(f"Iniciando análise de {len(lista_caminhos_pdf)} documento(s) com lógica de agregação.")

    for caminho_pdf in lista_caminhos_pdf:
        texto_extraido = _extrair_texto_pdf_com_ocr(caminho_pdf)
        if not texto_extraido:
            continue

        dados_do_pdf_atual = _analisar_texto_bruto_comprovante(texto_extraido)

        if not dados_agregados.get('fornecedor') and dados_do_pdf_atual.get('fornecedor'):
            dados_agregados['fornecedor'] = dados_do_pdf_atual['fornecedor']

        valor_atual_decimal = _normalize_valor_to_decimal(dados_do_pdf_atual.get('valor'))
        if valor_atual_decimal is not None:
            if dados_agregados['valor'] is None or valor_atual_decimal > dados_agregados['valor']:
                dados_agregados['valor'] = valor_atual_decimal
                logging.info(f"Novo maior valor encontrado: {valor_atual_decimal}")

        data_atual_str = dados_do_pdf_atual.get('pagamento')
        if data_atual_str:
            try:
                data_atual_obj = datetime.strptime(data_atual_str, "%d/%m/%Y")
                if dados_agregados['pagamento'] is None or data_atual_obj > dados_agregados['pagamento']:
                    dados_agregados['pagamento'] = data_atual_obj
                    logging.info(f"Nova data de pagamento mais tardia encontrada: {data_atual_str}")
            except ValueError:
                logging.warning(f"Formato de data inválido encontrado: '{data_atual_str}'. Ignorando.")

    # --- PREPARAÇÃO DOS DADOS FINAIS (COM A CORREÇÃO) ---

    # CORREÇÃO: Usa a função _format_decimal_to_brl para formatar o valor para o frontend.
    valor_final_str = _format_decimal_to_brl(dados_agregados['valor'])

    pagamento_final_str = ""
    if dados_agregados['pagamento'] is not None:
        pagamento_final_str = dados_agregados['pagamento'].strftime("%d/%m/%Y")
        
    dados_finais = {
        'fornecedor': dados_parciais.get('fornecedor') or dados_agregados.get('fornecedor'),
        'meio_pagamento': dados_parciais.get('meio_pagamento'),
        'valor': dados_parciais.get('valor') or valor_final_str,
        'vencimento': dados_parciais.get('vencimento') or pagamento_final_str,
        'pagamento': dados_parciais.get('pagamento') or pagamento_final_str,
    }
    
    logging.info(f"Dados finais agregados a serem enviados para o frontend: {dados_finais}")
    return {'status': 'SUCESSO', 'dados': dados_finais}
