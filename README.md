# Bot Administrativo de Documentos via Telegram

Este projeto é um bot para Telegram que automatiza tarefas administrativas. Ele recebe documentos (imagens ou PDFs), extrai informações-chave usando OCR e as organiza em uma planilha do Google Sheets, além de fazer o backup do arquivo original no Google Drive.

---

## Funcionalidades

-   Recebe arquivos (JPG, PNG, PDF) através de uma conversa no Telegram.
-   Utiliza o Tesseract OCR para extrair texto de documentos.
-   Analisa o texto para encontrar dados específicos (ex: datas, valores, fornecedor).
-   Adiciona os dados extraídos como uma nova linha em uma planilha do Google Sheets.
-   Faz o upload do documento original para uma pasta específica no Google Drive.

---

## Pré-requisitos

Antes de começar, garanta que você tem os seguintes softwares instalados:

1.  **Python 3.8+**
2.  **Tesseract OCR**: Este projeto depende do Tesseract para a funcionalidade de OCR.
    -   **Windows**: Baixe e instale a partir [deste link](https://github.com/UB-Mannheim/tesseract/wiki). **Importante:** Durante a instalação, adicione o suporte ao idioma "Portuguese" & "Math" e adicione o Tesseract ao PATH do sistema.
    -   **macOS**: `brew install tesseract`
    -   **Linux (Debian/Ubuntu)**: `sudo apt-get install tesseract-ocr`

---

## Configuração do Projeto

Siga os passos abaixo para configurar e executar o projeto localmente.

### 1. Clone o Repositório
```bash
git clone <URL_DO_SEU_REPOSITORIO>
cd <NOME_DA_PASTA_DO_PROJETO>

### 2. Create a virtual environments (venv)
python -m venv venv

### 3. Configure Auto use venv in terminal 
Abra a Paleta de Comandos (Ctrl+Shift+P)
Python: Select Interpreter
Escolha o Ambiente Virtual do Projeto (Recommended)
   If don`t work, close VS Code, open powershell with admin and use this command 
   Set-ExecutionPolicy RemoteSigned
   After that, open VS Code again.~

### 4. Instalando as bibliotecas no ambiente virtual
pip install -r requirements.txt


npx webpack
npx sass src/styles/main.scss dist/main.css
