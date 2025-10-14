# backend/app.py

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from processador import analisar_comprovante_ocr, processar_documento_com_dados_manuais

# --- CONFIGURAÇÃO INICIAL ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

# --- CORREÇÃO: Usa o caminho absoluto para a pasta de uploads ---
# Isto garante que a pasta é encontrada de forma fiável, em qualquer máquina.
UPLOAD_FOLDER = os.path.abspath('temp_files')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/upload', methods=['POST'])
def upload_file():
    logging.info("==========================================================")
    logging.info(">>> NOVA REQUISIÇÃO DE UPLOAD RECEBIDA PELO BACKEND. <<<")
    
    files = request.files.getlist('documento')
    if not files or files[0].filename == '':
        return jsonify({'status': 'ERRO', 'detalhes': 'Nenhum arquivo enviado.'}), 400
        
    dados_formulario = request.form.to_dict()
    logging.info(f"Dados do formulário recebidos: {dados_formulario}")
    logging.info(f"{len(files)} arquivo(s) recebido(s).")

    caminhos_temporarios = []
    nomes_originais = []
    try:
        for file in files:
            filename = secure_filename(file.filename)
            caminho_temporario = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(caminho_temporario)
            caminhos_temporarios.append(caminho_temporario)
            nomes_originais.append(filename)
        logging.info(f"Arquivos salvos temporariamente em: {app.config['UPLOAD_FOLDER']}")
    except Exception as e:
        logging.error(f"Erro ao salvar arquivos: {e}", exc_info=True)
        return jsonify({'status': 'ERRO', 'detalhes': f'Erro interno ao salvar arquivos: {e}'}), 500

    # Chama a lógica principal do processador. A limpeza dos ficheiros é feita lá.
    resultado = processar_documento_com_dados_manuais(caminhos_temporarios, dados_formulario, nomes_originais)
    
    logging.info(">>> PROCESSAMENTO DE UPLOAD FINALIZADO. <<<")
    logging.info("==========================================================")

    if resultado['status'] == 'SUCESSO':
        return jsonify(resultado), 200
    else:
        return jsonify(resultado), 500


@app.route('/analisar-comprovante', methods=['POST'])
def analisar_comprovante_endpoint():
    logging.info(">>> REQUISIÇÃO DE ANÁLISE DE COMPROVANTE RECEBIDA <<<")
    
    files = request.files.getlist('documento')
    if not files:
        return jsonify({'status': 'ERRO', 'detalhes': 'Nenhum arquivo PDF enviado.'}), 400
    
    dados_parciais = request.form.to_dict()
    logging.info(f"Dados parciais recebidos: {dados_parciais}")

    caminhos_temporarios = []
    try:
        for file in files:
            filename = secure_filename(file.filename)
            caminho_temporario = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(caminho_temporario)
            caminhos_temporarios.append(caminho_temporario)
        logging.info(f"{len(caminhos_temporarios)} arquivo(s) salvos para análise OCR.")
    except Exception as e:
        return jsonify({'status': 'ERRO', 'detalhes': f'Erro ao salvar arquivos: {e}'}), 500
    
    # Chama a função do processador. A limpeza dos ficheiros é feita lá.
    resultado_ocr = analisar_comprovante_ocr(caminhos_temporarios, dados_parciais)
    
    logging.info(">>> ANÁLISE DE COMPROVANTE FINALIZADA. <<<")

    if resultado_ocr['status'] == 'SUCESSO':
        return jsonify(resultado_ocr['dados']), 200
    else:
        return jsonify({'detalhes': resultado_ocr['detalhes']}), 500
    
if __name__ == '__main__':
    app.run(debug=True, port=5000)