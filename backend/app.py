import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Importa a sua função principal do processador
from processador import processar_documento_com_dados_manuais

# --- CONFIGURAÇÃO INICIAL ---
load_dotenv()
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)  # Permite requisições de origens diferentes (do seu frontend)

UPLOAD_FOLDER = 'temp_files'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



@app.route('/upload', methods=['POST'])
def upload_file():
    logging.info("==========================================================")
    logging.info(">>> NOVA REQUISIÇÃO RECEBIDA PELO BACKEND. <<<")
    
    # 1. Validação dos dados recebidos
    files = request.files.getlist('documento')
    if not files or files[0].filename == '':
        return jsonify({'status': 'ERRO', 'detalhes': 'Nenhum arquivo enviado.'}), 400
        
    dados_formulario = request.form.to_dict()
    logging.info(f"Dados do formulário recebidos: {dados_formulario}")
    logging.info(f"{len(files)} arquivo(s) recebido(s).")

    # 2. Salvar os arquivos temporariamente
    caminhos_temporarios = []
    nomes_originais = []
    try:
        for file in files:
            filename = secure_filename(file.filename)
            caminho_temporario = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(caminho_temporario)
            caminhos_temporarios.append(caminho_temporario)
            nomes_originais.append(filename)
        logging.info(f"Arquivos salvos temporariamente.")
    except Exception as e:
        logging.error(f"Erro ao salvar arquivos: {e}", exc_info=True)
        return jsonify({'status': 'ERRO', 'detalhes': f'Erro interno ao salvar arquivos: {e}'}), 500

    # 3. Chamar a lógica de processamento com a lista de arquivos
    resultado = processar_documento_com_dados_manuais(caminhos_temporarios, dados_formulario, nomes_originais)
    
    # 4. Limpar os arquivos temporários
    for caminho in caminhos_temporarios:
        os.remove(caminho)
    
    logging.info(">>> PROCESSAMENTO FINALIZADO. <<<")
    logging.info("==========================================================")

    # 5. Retornar a resposta para o front-end
    if resultado['status'] == 'SUCESSO':
        return jsonify(resultado), 200
    else:
        return jsonify(resultado), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)