# app.py (Versão Completa e Corrigida)

import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Importa a nossa função principal do outro arquivo
from processador import processar_documento_completo

# --- CONFIGURAÇÃO INICIAL (Executada uma única vez) ---
# Carrega as variáveis do arquivo .env para o ambiente
load_dotenv()

# Configura o sistema de logs para nos dar informações no terminal
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO # Mude para logging.DEBUG para ver ainda mais detalhes
)

# Pega o token do bot do Telegram a partir das variáveis de ambiente
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# --- DEFINIÇÃO DAS FUNÇÕES DO BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Função chamada quando o usuário envia o comando /start."""
    await update.message.reply_text('Olá! Sou seu assistente administrativo. Envie um documento (imagem ou PDF) para que eu possa processá-lo.')

async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Função principal que lida com o recebimento de documentos."""
    logging.info("==========================================================")
    logging.info(">>> NOVO DOCUMENTO RECEBIDO. INICIANDO PROCESSAMENTO. <<<")
    
    await update.message.reply_text('Recebi seu documento. Iniciando processamento... Por favor, aguarde.')

    # 1. Baixar o arquivo do Telegram
    try:
        if update.message.document:
            file_id = update.message.document.file_id
            file_name = update.message.document.file_name
        else: # Se for enviado como foto
            file_id = update.message.photo[-1].file_id
            file_name = f"{file_id}.jpg"
        
        new_file = await context.bot.get_file(file_id)
        
        caminho_temporario = os.path.join("temp_files", file_name)
        if not os.path.exists("temp_files"):
            os.makedirs("temp_files")
        await new_file.download_to_drive(caminho_temporario)
        logging.info(f"Arquivo '{file_name}' baixado com sucesso.")
    except Exception as e:
        logging.error(f"Falha ao baixar o arquivo do Telegram: {e}", exc_info=True)
        await update.message.reply_text("Ocorreu um erro ao tentar baixar seu arquivo. Tente novamente.")
        return

    # 2. Chamar o orquestrador do processador.py
    # No futuro, aqui decidiremos qual bot é (NOTA_FISCAL ou COMPROVANTE)
    tipo_documento = 'NOTA_FISCAL'
    
    resultado = processar_documento_completo(caminho_temporario, tipo_documento)
    
    # 3. Reagir com base no resultado
    if resultado['status'] == 'SUCESSO':
        await update.message.reply_text(f"✅ Processamento concluído com sucesso! Detalhes: {resultado['detalhes']}")
    elif resultado['status'] == 'ENFILEIRAR':
        logging.info(f"Tarefa será enviada para a fila do RabbitMQ. Motivo: {resultado['motivo']}")
        # Aqui, no futuro, entrará o código para publicar no RabbitMQ
        await update.message.reply_text(f"⏳ Recebi seu documento, mas os dados parecem incompletos e ele foi colocado na fila para análise posterior. Motivo: {resultado['motivo']}")
    else: # Status de ERRO
        await update.message.reply_text(f"❌ Ocorreu um erro durante o processamento. Detalhes: {resultado['detalhes']}")
        
    # 4. Limpar o arquivo temporário
    os.remove(caminho_temporario)
    logging.info(">>> PROCESSAMENTO FINALIZADO. AGUARDANDO NOVO DOCUMENTO. <<<")
    logging.info("==========================================================")

def main():
    """Função que inicializa e roda o bot."""
    if not TELEGRAM_BOT_TOKEN:
        logging.critical("A variável de ambiente TELEGRAM_BOT_TOKEN não foi definida! O bot não pode iniciar.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Adiciona os "handlers", que decidem qual função chamar para cada tipo de mensagem
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.IMAGE | filters.PHOTO, processar_mensagem))

    # Inicia o bot
    logging.info("Bot iniciado. Aguardando mensagens...")
    application.run_polling()

if __name__ == '__main__':
    main()