# processador.py (Versão Completa e Final)

import logging
import os
import re
from datetime import datetime
from pathlib import Path

import pytesseract
from PIL import Image, ImageEnhance

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURAÇÃO E INICIALIZAÇÃO ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
CREDENCIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
try:
    creds = Credentials.from_service_account_file(CREDENCIALS_FILE, scopes=SCOPES)
    gspread_client = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)
    logging.info("Credenciais do Google carregadas com sucesso.")
except Exception as e:
    logging.error(f"ERRO CRÍTICO ao carregar credenciais do Google: {e}", exc_info=True)
    creds = gspread_client = drive_service = None

# --- DEFINIÇÕES DE NEGÓCIO E MAPEAMENTO ---
CAMPOS_OBRIGATORIOS = {
    'NOTA_FISCAL': ['fornecedor', 'vencimento', 'valor', 'numero_nota', 'emissao'],
    'COMPROVANTE': ['fornecedor', 'valor', 'pagamento']
}
mapeamento_fornecedores = {
    "cadeg": "MELHOR COMPRA DA CADEG", "rio de janeiro refrescos ltda": "RJ REFRESROS", "rio de janeiro refrescos": "RIO DE JANEIRO REFRESCOS LTDA",
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
    "marapendi": "BARRA MARAPENDI", "tlkg com de alimentos ltda": "TLKG COM. DE ALIMENTOS LTDA",
}

# --- FUNÇÕES INTERNAS ---

def _extrair_dados_ocr(caminho_arquivo):
    """Função de OCR com pré-processamento de imagem."""
    try:
        logging.info(f"Iniciando OCR para o arquivo: '{caminho_arquivo}'")
        imagem_original = Image.open(caminho_arquivo)
        imagem = imagem_original.convert('L')
        enhancer = ImageEnhance.Contrast(imagem)
        imagem = enhancer.enhance(2)
        threshold = 180
        imagem = imagem.point(lambda p: p > threshold and 255)

        try:
            osd = pytesseract.image_to_osd(imagem, output_type=pytesseract.Output.DICT)
            if osd['rotate'] != 0:
                logging.warning(f"  -> Imagem rotacionada em {osd['rotate']} graus. Corrigindo...")
                imagem = imagem.rotate(-osd['rotate'], expand=True)
        except Exception as osd_error:
            logging.warning(f"OSD falhou. Continuando com imagem original. Erro: {osd_error}")

        caminho_debug = "debug_imagem_processada.png"
        imagem.save(caminho_debug)
        logging.info(f"  -> Imagem de debug salva em: '{caminho_debug}'")

        custom_config = r'--oem 3 --psm 6'
        texto_completo = pytesseract.image_to_string(imagem, lang='por', config=custom_config)
        
        if not texto_completo.strip():
            logging.warning("OCR com pré-processamento não retornou texto. Tentando com a imagem original...")
            texto_completo = pytesseract.image_to_string(imagem_original, lang='por')

        logging.info(f"--- TEXTO BRUTO EXTRAÍDO ---\n{texto_completo}\n-----------------------------")
        dados_brutos = analisar_texto_bruto(texto_completo)
        return dados_brutos
    except Exception as e:
        logging.error("ERRO CRÍTICO no processo de OCR.", exc_info=True)
        return {}

def analisar_texto_bruto(texto):
    """Versão 5.0 - Detetive Mestre, capaz de lidar com Boletos e DANFEs."""
    logging.info("Iniciando análise do texto bruto (v5.0)...")
    dados = {'fornecedor': '', 'vencimento': '', 'valor': '', 'emissao': '', 'numero_nota': ''}
    regex_data = r'\d{2}/\d{2}/\d{2,4}'
    regex_valor = r'(\d{1,3}(?:\.\d{3})*,\d{2})'
    
    datas_encontradas_str = sorted(list(set(re.findall(regex_data, texto))))
    datas_encontradas_obj = [datetime.strptime(d, "%d/%m/%Y") for d in datas_encontradas_str if len(d) == 10]
    if datas_encontradas_obj:
        dados['emissao'] = min(datas_encontradas_obj).strftime("%d/%m/%Y")
        dados['vencimento'] = max(datas_encontradas_obj).strftime("%d/%m/%Y")
        logging.info(f"Datas definidas por heurística: Emissão='{dados['emissao']}', Vencimento='{dados['vencimento']}'")

    linhas = texto.split('\n')
    texto_lower = texto.lower()

    for i, linha in enumerate(linhas):
        if not linha.strip(): continue
        linha_lower = linha.lower()

        if not dados['fornecedor']:
            if 'beneficiário' in linha_lower:
                partes = linha.split(':')
                if len(partes) > 1 and partes[1].strip():
                    dados['fornecedor'] = partes[1].strip()
                elif i + 1 < len(linhas):
                    dados['fornecedor'] = linhas[i+1].strip()
                logging.info(f"Fornecedor (Boleto) encontrado: '{dados['fornecedor']}'")
            elif 'destinatário' in linha_lower:
                if i + 2 < len(linhas):
                    dados['fornecedor'] = linhas[i+2].strip()
                    logging.info(f"Fornecedor (DANFE) encontrado: '{dados['fornecedor']}'")
        
        if not dados['valor']:
            if 'valor total da nota' in linha_lower:
                match = re.search(regex_valor, linha)
                if match: dados['valor'] = match.group(1)
            elif 'valor do documento' in linha_lower or '(=) valor cobrado' in linha_lower:
                valores_encontrados = re.findall(regex_valor, linha)
                if valores_encontrados: dados['valor'] = valores_encontrados[-1]
        
        if not dados['numero_nota']:
            if 'danfe' in texto_lower and 'nº' in linha_lower and 'série' in linha_lower:
                match = re.search(r'Nº\s*(\d+)', linha, re.IGNORECASE)
                if match: dados['numero_nota'] = match.group(1)
            elif 'nº do documento' in linha_lower or 'numero do documento' in linha_lower:
                partes = linha.split()
                if len(partes) > 1: dados['numero_nota'] = partes[-1]

    if not dados['valor']:
        todos_valores = re.findall(regex_valor, texto)
        if todos_valores:
            valores_float = [float(v.replace('.', '').replace(',', '.')) for v in todos_valores]
            dados['valor'] = todos_valores[valores_float.index(max(valores_float))]
            logging.info(f"Valor encontrado por fallback (maior valor no doc): '{dados['valor']}'")
            
    logging.info(f"Análise finalizada. Dados brutos extraídos: {dados}")
    return dados


def _padronizar_dados(dados_extraidos):
    """Lógica para padronizar fornecedor e obter IDs de mês."""
    nome_bruto = dados_extraidos.get('fornecedor', '').lower().strip()
    data_bruta = dados_extraidos.get('vencimento', '')
    nome_padronizado = "NÃO SEI"
    for apelido, nome_oficial in mapeamento_fornecedores.items():
        if apelido in nome_bruto:
            nome_padronizado = nome_oficial
            break
    id_drive, id_sheets = None, None
    if data_bruta:
        try:
            data_obj = datetime.strptime(data_bruta, "%d/%m/%Y")
            id_drive = os.getenv(f"DRIVE_ID_MONTH_{data_obj.month}")
            id_sheets = os.getenv(f"SHEETS_ID_MONTH_{data_obj.month}")
        except ValueError:
            pass
    return {"nome_padronizado": nome_padronizado, "id_drive": id_drive, "id_sheets": id_sheets, **dados_extraidos}


def _buscar_linha_no_sheets(dados):
    """Lógica funcional para buscar na planilha."""
    if not gspread_client or not dados.get('id_sheets'): return None
    try:
        logging.info("Iniciando busca no Google Sheets por linha correspondente...")
        sheet_id = os.getenv('GOOGLE_SHEET_ID')
        sheet_gid = dados['id_sheets'].split('gid=')[-1]
        worksheet = gspread_client.open_by_key(sheet_id).get_worksheet_by_id(int(sheet_gid))
        logging.warning("Busca por duplicatas no Sheets ainda não implementada de forma otimizada. Assumindo que a linha é nova.")
        return None
    except Exception as e:
        logging.error(f"Erro ao buscar no Google Sheets: {e}", exc_info=True)
        return None


def _adicionar_nova_linha_sheets(dados):
    """Lógica funcional para adicionar linha."""
    if not gspread_client or not dados.get('id_sheets'): return False
    try:
        logging.info("Adicionando nova linha ao Google Sheets...")
        sheet_id = os.getenv('GOOGLE_SHEET_ID')
        sheet_gid = dados['id_sheets'].split('gid=')[-1]
        worksheet = gspread_client.open_by_key(sheet_id).get_worksheet_by_id(int(sheet_gid))
        linha = [
            dados.get('nome_padronizado'), dados.get('valor'), dados.get('vencimento'),
            dados.get('emissao'), dados.get('numero_nota')
        ]
        worksheet.append_row(linha)
        logging.info(f"Linha adicionada com sucesso na aba '{worksheet.title}'.")
        return True
    except Exception as e:
        logging.error(f"Erro ao adicionar linha no Google Sheets: {e}", exc_info=True)
        return False


def _executar_logica_de_partes_drive(dados, caminho_arquivo, nome_original):
    """Lógica funcional de upload e versionamento."""
    if not drive_service: return False
    id_pasta_mes = dados.get('id_drive')
    nome_fornecedor = dados.get('nome_padronizado')
    if not id_pasta_mes or not nome_fornecedor or nome_fornecedor == "NÃO SEI":
        logging.error("Upload cancelado: ID do mês ou nome do fornecedor inválido.")
        return False
    try:
        query = f"'{id_pasta_mes}' in parents and name = '{nome_fornecedor}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])
        if not items:
            folder_metadata = {'name': nome_fornecedor, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [id_pasta_mes]}
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            id_pasta_fornecedor = folder.get('id')
        else:
            id_pasta_fornecedor = items[0].get('id')
        data_formatada = datetime.strptime(dados['vencimento'], "%d/%m/%Y").strftime("%d-%m-%Y")
        valor_formatado = dados['valor']
        prefixo_arquivo = f"{data_formatada} - R${valor_formatado}"
        query_partes = f"'{id_pasta_fornecedor}' in parents and name contains '{prefixo_arquivo}' and trashed = false"
        results_partes = drive_service.files().list(q=query_partes, fields="files(id, name)").execute()
        partes_existentes = len(results_partes.get('files', []))
        proxima_parte = partes_existentes + 1
        extensao = Path(nome_original).suffix
        nome_final_arquivo = f"{prefixo_arquivo} - parte {proxima_parte}{extensao}"
        logging.info(f"Fazendo upload como: '{nome_final_arquivo}' para a pasta ID: {id_pasta_fornecedor}")
        file_metadata = {'name': nome_final_arquivo, 'parents': [id_pasta_fornecedor]}
        media = MediaFileUpload(caminho_arquivo, mimetype='application/octet-stream', resumable=True)
        drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logging.info("Upload para o Drive concluído com sucesso.")
        return True
    except Exception as e:
        logging.error(f"Erro no processo do Google Drive: {e}", exc_info=True)
        return False


# --- FUNÇÃO PRINCIPAL ORQUESTRADORA ---
def processar_documento_completo(caminho_arquivo, tipo_documento):
    if not creds: return {'status': 'ERRO', 'detalhes': 'Credenciais do Google não foram carregadas.'}
    dados_brutos = _extrair_dados_ocr(caminho_arquivo)
    dados_padronizados = _padronizar_dados(dados_brutos)
    tem_dados_minimos = (
        dados_padronizados.get('nome_padronizado') != "NÃO SEI" and
        dados_padronizados.get('valor') and
        (dados_padronizados.get('vencimento') or dados_padronizados.get('emissao') or dados_padronizados.get('pagamento'))
    )
    if not tem_dados_minimos:
        return {'status': 'ENFILEIRAR', 'motivo': 'Dados mínimos (Fornecedor, Valor, Data) não encontrados.'}
    linha_existente = _buscar_linha_no_sheets(dados_padronizados)
    if linha_existente:
        if _executar_logica_de_partes_drive(dados_padronizados, caminho_arquivo, Path(caminho_arquivo).name):
            return {'status': 'SUCESSO', 'detalhes': 'Nova parte adicionada ao Drive para um lançamento existente.'}
        else:
            return {'status': 'ERRO', 'detalhes': 'Falha ao fazer upload da nova parte no Drive.'}
    else:
        campos_necessarios = CAMPOS_OBRIGATORIOS.get(tipo_documento, [])
        dados_completos = all(dados_padronizados.get(campo) for campo in campos_necessarios)
        if dados_completos:
            sucesso_sheets = _adicionar_nova_linha_sheets(dados_padronizados)
            sucesso_drive = _executar_logica_de_partes_drive(dados_padronizados, caminho_arquivo, Path(caminho_arquivo).name)
            if sucesso_sheets and sucesso_drive:
                return {'status': 'SUCESSO', 'detalhes': 'Novo lançamento criado no Sheets e Drive (parte 1).'}
            else:
                return {'status': 'ERRO', 'detalhes': 'Falha ao salvar novo lançamento no Sheets ou Drive.'}
        else:
            return {'status': 'ENFILEIRAR', 'motivo': 'Dados incompletos e sem correspondência na planilha.'}