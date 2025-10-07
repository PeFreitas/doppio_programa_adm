# app.py (versão completa e atualizada)

import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Importa TODAS as nossas funções do processador
from processador import extrair_dados_do_arquivo, padronizar_dados, adicionar_linha_sheets, realizar_upload_drive

# --- CONFIGURAÇÃO ---
load_dotenv()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO # Mude para logging.DEBUG para ver ainda mais detalhes
)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# --- FUNÇÕES DO BOT TELEGRAM ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Olá! Envie uma imagem (JPG, PNG) ou um PDF para iniciar o processamento.')

async def processar_documento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Recebi seu documento. Iniciando processamento... (Verifique os logs no terminal)')

    # 1. Baixar o arquivo do Telegram
    if update.message.document:
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name
    else:
        file_id = update.message.photo[-1].file_id
        file_name = f"{file_id}.jpg"
    
    new_file = await context.bot.get_file(file_id)
    
    caminho_temporario = os.path.join("temp_files", file_name)
    if not os.path.exists("temp_files"):
        os.makedirs("temp_files")
    await new_file.download_to_drive(caminho_temporario)
    
    # 2. Chamar nosso módulo de processamento
    dados_brutos_extraidos = extrair_dados_do_arquivo(caminho_temporario)

    if not dados_brutos_extraidos or not any(dados_brutos_extraidos.values()):
        await update.message.reply_text('Não consegui extrair informações do arquivo. Verifique a qualidade da imagem e os logs do terminal.')
        os.remove(caminho_temporario)
        return

    # 3. Chamar nosso "cérebro" para padronizar os dados
    dados_finais = padronizar_dados(dados_brutos_extraidos)

    # 4. Chamar as funções de integração com o Google (que agora têm logs)
    sucesso_sheets = adicionar_linha_sheets(dados_finais)
    sucesso_drive = realizar_upload_drive(caminho_temporario, file_name, dados_finais)

    # 5. Enviar a resposta final para o usuário
    if sucesso_sheets and sucesso_drive:
        resposta = (
            f"Processamento concluído com sucesso!\n\n"
            f"Fornecedor: *{dados_finais.get('nome_padronizado', 'N/A')}*\n"
            f"Valor: R$ {dados_finais.get('valor', 'N/A')}\n"
            f"Vencimento: {dados_finais.get('vencimento', 'N/A')}\n"
        )
        await update.message.reply_text(resposta, parse_mode='Markdown')
    else:
        await update.message.reply_text("Processamento concluído, mas houve uma falha ao salvar no Google Drive ou Sheets. Verifique os logs.")

    # 6. Limpar o arquivo temporário
    os.remove(caminho_temporario)


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.IMAGE | filters.PHOTO, processar_documento))
    application.run_polling()

if __name__ == '__main__':
    main()