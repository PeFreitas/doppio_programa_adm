# backend/processador.py

import logging
import os
import io
from datetime import datetime
from pathlib import Path
from decimal import Decimal, InvalidOperation

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from thefuzz import process
import pytesseract
from pdf2image import convert_from_path
import re

# --- CONFIGURAÇÃO (sem alterações) ---
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

# --- MAPEAMENTO DE FORNECEDORES (sem alterações) ---
mapeamento_fornecedores = {
    "cadeg": "MELHOR COMPRA DA CADEG", "rio de janeiro refrescos ltda": "RJ REFRESROS", "rio de janeiro refrescos": "RJ REFRESROS", "rio quality": "RIO QUALITY", "nossos sabores": "NOSSOS SABORES", "cafez": "CAFEZ COMERCIO VAREJISTA DE CAFÉ", "cafez varejista": "CAFEZ COMERCIO VAREJISTA DE CAFÉ", "choconata": "CHOCONATA IND E COM DE ALIMENTOS", "atelier dos sabores": "ATELIER DOS SABORES", "atelier": "ATELIER DOS SABORES", "brigadeiro": "ATELIER DOS SABORES", "brigadeiro industria": "ATELIER DOS SABORES", "brasfruto": "BRASFRUTO - AÇAÍ", "centralrj": "CENTRAL RJ", "kiko": "CRHISTIAN BECKER", "pgto kiko": "CRHISTIAN BECKER", "crhistian becker": "CRHISTIAN BECKER", "daniel santiago": "DON SANTIAGO", "don santiago": "DON SANTIAGO", "gt": "GUSTAVO TREMONTI", "pgto gt": "GUSTAVO TREMONTI", "gustavo tremonti": "GUSTAVO TREMONTI", "illy": "ILLY", "nobredo": "NOBREDO", "peruchi sorvetes": "OGGI", "peruchi": "OGGI", "oggi": "OGGI", "quebra nozes": "QUEBRA NOZES IND E COM DE ALIM LTDA", "audax": "AUDAX CONTABILIDADE (TLKG e DOPPIO BUFFET)", "cartão": "CARTÃO DE CRÉDITO EMPRESARIAL", "cartão de crédito": "CARTÃO DE CRÉDITO EMPRESARIAL", "clube dos sabores": "CLUBE DOS SABORES", "cmd": "CMD - MENSALIDADE SISTEMA BEMATECH (TOTVS CHEF)", "cmd automação": "CMD - MENSALIDADE SISTEMA BEMATECH (TOTVS CHEF)", "outros": "OUTROS", "di brownie": "DI BROWNIE", "mj de moraes": "MJ DE MORAES", "sindrio": "SINDICATO DE BARES E RESTAURANTES DO RJ (SINDRIO)", "sindicato dos trab": "SINDICATO DE BARES E RESTAURANTES DO RJ (SINDRIO)", "sigabam": "SINDICATO DOS GARÇONS DO RJ (SIGABAM)", "sindicato dos garçons": "SINDICATO DOS GARÇONS DO RJ (SIGABAM)", "tkn rio": "TKN RIO (ALUGUEL MAQ. DE GELO)", "máquina de gelo": "TKN RIO (ALUGUEL MAQ. DE GELO)", "tortamania": "TORTAMANIA", "tudo legal": "TUDO LEGAL", "internet": "VIVO INTERNET", "telefonica brasil": "VIVO INTERNET", "zona zen": "ZONA ZEN", "encontro são conrrado": "ZONA ZEN", "fgts doppio": "GFD (FGTS DIGITAL) - DOPPIO BUFFET", "das doppio": "DAS (Simples) - DOPPIO BUFFET", "simples doppio": "DAS (Simples) - DOPPIO BUFFET", "fgts tlkg": "GFD (FGTS DIGITAL) - TLKG", "dctf doppio": "DCTFWeb DOPPIO BUFFET", "dctf tlkg": "DCTFWeb TLKG", "icms tlkg": "ICMS TLKG", "riopar": "RIOPAR (VT) - boleto", "vt boleto": "RIOPAR (VT) - boleto", "aluguel shopping": "CONDOMÍNIO/ALUGUEL BARRASHOPPING", "aluguel": "CONDOMÍNIO/ALUGUEL BARRASHOPPING", "parcelamento dctf tlkg": "PARCELAMENTO DCTFWeb TLKG - FEV25 - ATRASADO", "parcelamento": "PARCELAMENTO DCTFWeb TLKG - FEV25 - ATRASADO", "funcionarios": "FUNCIONARIOS", "maran": "MARAN COMERCIO DESCARTAVEIS", "maran com descart": "MARAN COMERCIO DESCARTAVEIS", "frozen": "FROZEN BISTRÔ", "bruno jose fischer": "FROZEN BISTRÔ", "bruno fischer": "FROZEN BISTRÔ", "alexandre ferreira": "BIA BOLOS", "alexandre": "BIA BOLOS", "bia bolos": "BIA BOLOS", "retirada socios": "RETIRADA SOCIOS", "si tecnologia": "SUISSE", "barra marapendi": "BARRA MARAPENDI", "marapendi": "BARRA MARAPENDI",
}


def _normalize_valor_to_decimal(valor):
    if valor is None: return None
    try:
        valor_str = str(valor).replace('R$', '').strip().replace('.', '').replace(',', '.')
        return Decimal(valor_str)
    except (InvalidOperation, ValueError): return None

def _format_decimal_to_brl(valor_decimal):
    if valor_decimal is None: return ""
    return '{:,.2f}'.format(valor_decimal).replace(',', 'X').replace('.', ',').replace('X', '.')

# --- ALTERAÇÃO 1: CORREÇÃO DA DATA DE PAGAMENTO ---
def _padronizar_dados(dados_do_formulario):
    nome_bruto = dados_do_formulario.get('fornecedor', '').lower().strip()
    
    # Pega todas as strings de data
    datas_str = {
        'vencimento': dados_do_formulario.get('vencimento', ''),
        'emissao': dados_do_formulario.get('emissao', ''),
        'pagamento': dados_do_formulario.get('pagamento', '') # Adicionado
    }

    # Itera sobre as datas para formatá-las
    for nome, data_str in datas_str.items():
        if data_str:
            try:
                # Tenta o formato AAAA-MM-DD primeiro
                data_obj = datetime.strptime(data_str, "%Y-%m-%d")
                # Se conseguir, converte para DD/MM/AAAA e atualiza o formulário
                dados_do_formulario[nome] = data_obj.strftime("%d/%m/%Y")
            except ValueError:
                # Se falhar, assume que já está em DD/MM/AAAA e não faz nada
                pass
    
    nome_padronizado = "NÃO SEI"
    nomes_oficiais = list(set(mapeamento_fornecedores.values()))
    melhor_match = process.extractOne(nome_bruto, nomes_oficiais)
    if melhor_match and melhor_match[1] > 75: nome_padronizado = melhor_match[0]
    
    id_drive, id_sheets = None, None
    data_vencimento_final = dados_do_formulario.get('vencimento')
    if data_vencimento_final:
        try:
            # Usa a data já formatada para encontrar o mês
            data_obj_vencimento = datetime.strptime(data_vencimento_final, "%d/%m/%Y")
            id_drive = os.getenv(f"DRIVE_ID_MONTH_{data_obj_vencimento.month}")
            id_sheets = os.getenv(f"SHEETS_ID_MONTH_{data_obj_vencimento.month}")
        except ValueError:
            logging.error(f"Erro final ao processar data de vencimento: '{data_vencimento_final}'.")

    dados_padronizados = dados_do_formulario.copy()
    dados_padronizados.update({
        'nome_padronizado': nome_padronizado, 'id_drive': id_drive, 'id_sheets': id_sheets,
        'valor_formatado_brl': _format_decimal_to_brl(_normalize_valor_to_decimal(dados_do_formulario.get('valor')))
    })
    return dados_padronizados

# --- FUNÇÕES DO GOOGLE SHEETS (sem alterações) ---
def _buscar_e_atualizar_linha_existente(dados):
    if not all([gspread_client, dados.get('id_sheets'), GOOGLE_SHEET_ID]): return False
    try:
        sheet_gid = dados['id_sheets'].split('gid=')[-1]
        worksheet = gspread_client.open_by_key(GOOGLE_SHEET_ID).get_worksheet_by_id(int(sheet_gid))
        all_data = worksheet.get_all_values()
        if not all_data: return False
        header = all_data[0]
        try:
            conta_idx, valor_idx, vencimento_idx = header.index('Conta'), header.index('Valor'), header.index('Data de vencimento')
        except ValueError: return False
        fornecedor_chave, valor_chave_decimal, vencimento_chave = dados.get('nome_padronizado'), _normalize_valor_to_decimal(dados.get('valor')), dados.get('vencimento')
        for index, row_data in enumerate(all_data[1:]):
            if len(row_data) <= max(conta_idx, valor_idx, vencimento_idx): continue
            if (row_data[conta_idx] == fornecedor_chave and _normalize_valor_to_decimal(row_data[valor_idx]) == valor_chave_decimal and row_data[vencimento_idx] == vencimento_chave):
                mapeamento = {'Meio Pagto': 'meio_pagamento', 'Nro NF': 'numero_nota', 'Data de Emissão da nota': 'emissao', 'Data do pagamento': 'pagamento'}
                celulas = []
                for col_nome, dado_chave in mapeamento.items():
                    if dados.get(dado_chave):
                        try:
                            col_idx = header.index(col_nome)
                            if len(row_data) <= col_idx or str(row_data[col_idx]).strip() == '':
                                celulas.append(gspread.Cell(row=index + 2, col=col_idx + 1, value=dados.get(dado_chave)))
                        except ValueError: pass
                if celulas: worksheet.update_cells(celulas, value_input_option='USER_ENTERED')
                return True
        return False
    except Exception: return False

def _adicionar_nova_linha_sheets(dados):
    if not all([gspread_client, dados.get('id_sheets'), GOOGLE_SHEET_ID]): return False
    try:
        sheet_gid = dados['id_sheets'].split('gid=')[-1]
        worksheet = gspread_client.open_by_key(GOOGLE_SHEET_ID).get_worksheet_by_id(int(sheet_gid))
        linha_base = {'Conta': dados.get('nome_padronizado', ''), 'Meio Pagto': dados.get('meio_pagamento', 'BOLETO'), 'Nro NF': dados.get('numero_nota', ''), 'Valor': dados.get('valor_formatado_brl', ''), 'Data de Emissão da nota': dados.get('emissao', ''), 'Data de vencimento': dados.get('vencimento', ''), 'Data do pagamento': dados.get('pagamento', '')}
        worksheet.append_row([linha_base.get(col, '') for col in worksheet.row_values(1)], value_input_option='USER_ENTERED')
        return True
    except Exception: return False

# --- ALTERAÇÃO 2: MECÂNICA DE UPLOAD INTELIGENTE ---
def _executar_upload_drive(dados, caminhos_arquivos_locais, nomes_originais_arquivos):
    if not all([drive_service, dados.get('id_drive'), dados.get('nome_padronizado') != "NÃO SEI"]): return 0
    
    uploads_bem_sucedidos = 0
    try:
        id_pasta_mes = dados['id_drive']
        nome_fornecedor = dados['nome_padronizado']
        query_pasta = f"'{id_pasta_mes}' in parents and name = '{nome_fornecedor}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results_pasta = drive_service.files().list(q=query_pasta, fields="files(id)").execute()
        id_pasta_fornecedor = results_pasta.get('files', [{}])[0].get('id') or drive_service.files().create(body={'name': nome_fornecedor, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [id_pasta_mes]}, fields='id').execute().get('id')
        
        prefixo_arquivo = f"{datetime.strptime(dados['vencimento'], '%d/%m/%Y').strftime('%d-%m-%Y')} - R${dados['valor_formatado_brl']}"

        # --- Início da nova lógica: Contar ficheiros existentes ---
        query_ficheiros_existentes = f"'{id_pasta_fornecedor}' in parents and name contains '{prefixo_arquivo}' and trashed = false"
        results_ficheiros = drive_service.files().list(q=query_ficheiros_existentes, fields="files(name)").execute()
        ficheiros_existentes = results_ficheiros.get('files', [])
        parte_inicial = len(ficheiros_existentes)
        logging.info(f"Encontrados {parte_inicial} ficheiros existentes com o mesmo prefixo. O novo upload começará da parte {parte_inicial + 1}.")
        # --- Fim da nova lógica ---
        
        for i, (caminho, nome_original) in enumerate(zip(caminhos_arquivos_locais, nomes_originais_arquivos)):
            if not os.path.exists(caminho):
                logging.warning(f"O ficheiro temporário {Path(caminho).name} não foi encontrado. A ignorar.")
                continue
            try:
                # O número da parte agora é baseado na contagem de ficheiros existentes
                parte_numero = parte_inicial + i + 1
                nome_final = f"{prefixo_arquivo} - parte {parte_numero}{Path(nome_original).suffix}"
                
                metadata = {'name': nome_final, 'parents': [id_pasta_fornecedor]}
                with open(caminho, 'rb') as f:
                    media = MediaIoBaseUpload(f, mimetype='application/octet-stream', resumable=True)
                    drive_service.files().create(body=metadata, media_body=media, fields='id').execute()
                
                uploads_bem_sucedidos += 1
                os.remove(caminho)
                logging.info(f"Upload e limpeza de '{Path(caminho).name}' como '{nome_final}' bem-sucedidos.")
            except Exception as e_file:
                logging.error(f"Erro no upload ou limpeza do ficheiro {nome_original}: {e_file}")
        
        return uploads_bem_sucedidos
    except Exception as e:
        logging.error(f"Erro geral no processo do Drive: {e}")
        return uploads_bem_sucedidos

# --- FUNÇÃO PRINCIPAL (sem alterações) ---
def processar_documento_com_dados_manuais(caminhos_arquivos, dados_formulario, nomes_originais_arquivos):
    if not creds: return {'status': 'ERRO', 'detalhes': 'Credenciais do Google não foram carregadas.'}
    dados_completos = _padronizar_dados(dados_formulario)
    if not all([dados_completos.get('nome_padronizado') != "NÃO SEI", dados_completos.get('id_drive'), dados_completos.get('id_sheets')]):
        return {'status': 'ERRO', 'detalhes': 'Não foi possível identificar o fornecedor ou o mês de lançamento.'}
    linha_existe = _buscar_e_atualizar_linha_existente(dados_completos)
    sucesso_sheets = True if linha_existe else _adicionar_nova_linha_sheets(dados_completos)
    if not sucesso_sheets: return {'status': 'ERRO', 'detalhes': 'Falha na operação com o Google Sheets.'}
    mensagem_sheets = "Linha existente atualizada no Sheets" if linha_existe else "Nova linha criada no Sheets"
    contagem_uploads = _executar_upload_drive(dados_completos, caminhos_arquivos, nomes_originais_arquivos)
    if contagem_uploads > 0:
        return {'status': 'SUCESSO', 'detalhes': f'{mensagem_sheets} e {contagem_uploads} arquivo(s) salvos no Drive.'}
    elif len(caminhos_arquivos) > 0:
        return {'status': 'ERRO', 'detalhes': f'A operação no Sheets foi concluída, mas falhou ao salvar {len(caminhos_arquivos)} arquivo(s) no Drive.'}
    else:
        return {'status': 'SUCESSO', 'detalhes': f'{mensagem_sheets}. Nenhum arquivo para salvar no Drive.'}

# --- FUNÇÕES DE OCR (sem alterações) ---
def _extrair_texto_pdf_com_ocr(caminho_pdf):
    try:
        return "".join(pytesseract.image_to_string(img, lang='por') + "\n" for img in convert_from_path(caminho_pdf))
    except Exception: return ""

def _analisar_texto_bruto_comprovante(texto):
    dados = {'fornecedor': '', 'valor': '', 'pagamento': ''}
    melhor_match = process.extractOne(texto, list(mapeamento_fornecedores.keys()), score_cutoff=85)
    if melhor_match: dados['fornecedor'] = melhor_match[0]
    valores = re.findall(r'R\$\s*([\d.,]+)', texto)
    if valores: dados['valor'] = valores[-1].strip()
    datas = re.findall(r'(\d{2}/\d{2}/\d{4})', texto)
    if datas: dados['pagamento'] = datas[-1]
    dados['vencimento'] = dados['pagamento']
    return dados

def analisar_comprovante_ocr(lista_caminhos_pdf, dados_parciais):
    dados_agregados = {'fornecedor': '', 'valor': None, 'pagamento': None}
    for caminho in lista_caminhos_pdf:
        texto = _extrair_texto_pdf_com_ocr(caminho)
        if texto:
            dados_pdf = _analisar_texto_bruto_comprovante(texto)
            if not dados_agregados.get('fornecedor') and dados_pdf.get('fornecedor'): dados_agregados['fornecedor'] = dados_pdf['fornecedor']
            valor_dec = _normalize_valor_to_decimal(dados_pdf.get('valor'))
            if valor_dec and (dados_agregados['valor'] is None or valor_dec > dados_agregados['valor']): dados_agregados['valor'] = valor_dec
            if dados_pdf.get('pagamento'):
                try:
                    data_obj = datetime.strptime(dados_pdf.get('pagamento'), "%d/%m/%Y")
                    if dados_agregados['pagamento'] is None or data_obj > dados_agregados['pagamento']: dados_agregados['pagamento'] = data_obj
                except ValueError: pass
        try: os.remove(caminho)
        except Exception as e: logging.error(f"Erro ao limpar ficheiro OCR temporário: {e}")
    pagamento_str = dados_agregados['pagamento'].strftime("%d/%m/%Y") if dados_agregados['pagamento'] else ""
    dados_finais = {
        'fornecedor': dados_parciais.get('fornecedor') or dados_agregados.get('fornecedor'),
        'meio_pagamento': dados_parciais.get('meio_pagamento'),
        'valor': dados_parciais.get('valor') or _format_decimal_to_brl(dados_agregados['valor']),
        'vencimento': dados_parciais.get('vencimento') or pagamento_str,
        'pagamento': dados_parciais.get('pagamento') or pagamento_str,
    }
    return {'status': 'SUCESSO', 'dados': dados_finais}
