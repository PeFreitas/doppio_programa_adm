// --- INÍCIO DO ARQUIVO APP.TS ---
console.log('[DEBUG] app.ts: O script foi carregado. Versão: final-debug');

document.addEventListener('DOMContentLoaded', () => {
    console.log('[DEBUG] DOMContentLoaded: O documento HTML foi totalmente carregado e analisado.');
    
    // --- LÓGICA DE NAVEGAÇÃO DO MENU (NÃO FOI ALTERADA) ---
    const navLinks = document.querySelectorAll('.nav-link');
    const contentSections = document.querySelectorAll('.content-section');
    navLinks.forEach(link => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            const clickedLink = event.currentTarget as HTMLElement;
            if (clickedLink.classList.contains('dropdown-toggle')) {
                clickedLink.parentElement?.classList.toggle('open');
                return;
            }
            const targetId = clickedLink.dataset.target;
            if (targetId) {
                navLinks.forEach(nav => nav.classList.remove('active'));
                clickedLink.classList.add('active');
                contentSections.forEach(section => section.classList.remove('active'));
                document.getElementById(targetId)?.classList.add('active');
            }
        });
    });
    
    // --- LÓGICA PARA O "FORMULÁRIO" DE NOTAS (NÃO FOI ALTERADA) ---
    const notasContainer = document.getElementById('upload-form-container');
    if (notasContainer) {
        console.log("[DEBUG] Container de NOTAS (id='upload-form-container') encontrado.");
        const dropZone = document.getElementById('drop-zone') as HTMLDivElement;
        const fileInput = document.getElementById('file-input') as HTMLInputElement;
        const fileListDisplay = document.getElementById('file-list') as HTMLUListElement;
        const statusMessage = document.getElementById('status-message') as HTMLDivElement;
        const submitButton = document.getElementById('submit-button') as HTMLButtonElement;
        const resetButton = document.getElementById('reset-button-notas') as HTMLButtonElement;
        let selectedFiles: File[] = [];

        if (!dropZone || !fileInput || !fileListDisplay || !statusMessage || !submitButton || !resetButton) {
            console.error("ERRO CRÍTICO: Um ou mais elementos do formulário de NOTAS não foram encontrados. Verifique os IDs no HTML.");
            return;
        }

        const updateNotasFileListUI = () => {
            fileListDisplay.innerHTML = '';
            selectedFiles.forEach((file, index) => {
                const li = document.createElement('li');
                li.textContent = file.name;
                const removeBtn = document.createElement('button');
                removeBtn.textContent = '×';
                removeBtn.className = 'remove-file-btn';
                removeBtn.type = 'button';
                removeBtn.onclick = () => { selectedFiles.splice(index, 1); updateNotasFileListUI(); };
                li.appendChild(removeBtn);
                fileListDisplay.appendChild(li);
            });
        };
        
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => {
            if (fileInput.files) {
                selectedFiles.push(...Array.from(fileInput.files));
                updateNotasFileListUI();
                fileInput.value = '';
            }
        });

        const preventDefaults = (e: Event) => { e.preventDefault(); e.stopPropagation(); };
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eName => dropZone.addEventListener(eName, preventDefaults));
        ['dragenter', 'dragover'].forEach(eName => dropZone.addEventListener(eName, () => dropZone.classList.add('drag-over')));
        ['dragleave', 'drop'].forEach(eName => dropZone.addEventListener(eName, () => dropZone.classList.remove('drag-over')));
        dropZone.addEventListener('drop', (e: DragEvent) => {
            if (e.dataTransfer?.files) {
                selectedFiles.push(...Array.from(e.dataTransfer.files));
                updateNotasFileListUI();
            }
        });

        submitButton.addEventListener('click', async () => {
            console.log("[DEBUG] Botão de Envio de NOTAS foi clicado!");

            const fornecedorInput = document.getElementById('fornecedor') as HTMLInputElement;
            const valorInput = document.getElementById('valor') as HTMLInputElement;
            const vencimentoInput = document.getElementById('vencimento') as HTMLInputElement;

            if (selectedFiles.length === 0) {
                statusMessage.textContent = 'Erro: Por favor, selecione ao menos um arquivo.';
                statusMessage.style.color = 'lightcoral';
                return;
            }
             if (!fornecedorInput.value || !valorInput.value || !vencimentoInput.value) {
                statusMessage.textContent = 'Erro: Preencha todos os campos obrigatórios (Fornecedor, Valor, Vencimento).';
                statusMessage.style.color = 'lightcoral';
                return;
            }

            submitButton.disabled = true;
            statusMessage.textContent = 'Enviando, por favor aguarde...';
            statusMessage.style.color = 'lightblue';

            const formData = new FormData();
            selectedFiles.forEach(file => formData.append('documento', file));
            formData.append('fornecedor', fornecedorInput.value);
            formData.append('meio_pagamento', (document.getElementById('meio_pagamento') as HTMLSelectElement).value);
            formData.append('valor', valorInput.value);
            formData.append('numero_nota', (document.getElementById('numero_nota') as HTMLInputElement).value);
            if (vencimentoInput.value) formData.set('vencimento', vencimentoInput.value.split('-').reverse().join('/'));
            const emissaoInput = document.getElementById('emissao') as HTMLInputElement;
            if (emissaoInput.value) formData.set('emissao', emissaoInput.value.split('-').reverse().join('/'));
            
            try {
                const response = await fetch('http://127.0.0.1:5000/upload', { method: 'POST', body: formData });
                const result = await response.json();
                if (!response.ok) throw new Error(result.detalhes || 'Ocorreu um erro.');
                
                statusMessage.textContent = `Sucesso: ${result.detalhes}`;
                statusMessage.style.color = 'lightgreen';
                
                submitButton.classList.add('hidden');
                resetButton.classList.remove('hidden');
            } catch (error) {
                statusMessage.textContent = `Erro: ${error.message}`;
                statusMessage.style.color = 'lightcoral';
                submitButton.disabled = false;
            }
        });

        resetButton.addEventListener('click', () => {
            console.log("[DEBUG] Botão RESET do formulário de NOTAS foi clicado.");
            (notasContainer as HTMLDivElement).querySelectorAll('input, select').forEach(el => (el as any).value = '');
            selectedFiles = [];
            updateNotasFileListUI();
            statusMessage.textContent = '';
            resetButton.classList.add('hidden');
            submitButton.classList.remove('hidden');
            submitButton.disabled = false;
        });
    } else {
        console.error("[ERRO] Container de NOTAS (id='upload-form-container') NÃO foi encontrado.");
    }

    // --- LÓGICA PARA O "FORMULÁRIO" DE COMPROVANTES (CÓDIGO NOVO E INTELIGENTE) ---
    const comprovantesContainer = document.getElementById('comprovantes-form-container');
    if (comprovantesContainer) {
        console.log("[DEBUG] Container de COMPROVANTES (id='comprovantes-form-container') encontrado.");
        const dropZone = document.getElementById('comprovantes-drop-zone') as HTMLDivElement;
        const fileInput = document.getElementById('comprovantes-file-input') as HTMLInputElement;
        const fileListDisplay = document.getElementById('comprovantes-file-list') as HTMLUListElement;
        const statusMessage = document.getElementById('comprovantes-status-message') as HTMLDivElement;
        const submitButton = document.getElementById('comprovantes-submit-button') as HTMLButtonElement;
        const resetButton = document.getElementById('reset-button-comprovantes') as HTMLButtonElement;
        let selectedFiles: File[] = [];
        let isConfirmationStep = false;

        if (!dropZone || !fileInput || !fileListDisplay || !statusMessage || !submitButton || !resetButton) {
            console.error("ERRO CRÍTICO: Um ou mais elementos do formulário de COMPROVANTES não foram encontrados. Verifique os IDs no HTML.");
            return;
        }

        const updateComprovantesFileListUI = () => {
            fileListDisplay.innerHTML = '';
            selectedFiles.forEach((file, index) => {
                const li = document.createElement('li');
                li.textContent = file.name;
                const removeBtn = document.createElement('button');
                removeBtn.textContent = '×';
                removeBtn.className = 'remove-file-btn';
                removeBtn.type = 'button';
                removeBtn.onclick = () => { selectedFiles.splice(index, 1); updateComprovantesFileListUI(); };
                li.appendChild(removeBtn);
                fileListDisplay.appendChild(li);
            });
        };

        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => {
            if (fileInput.files) {
                selectedFiles.push(...Array.from(fileInput.files));
                updateComprovantesFileListUI();
                fileInput.value = '';
            }
        });

        const preventDefaults = (e: Event) => { e.preventDefault(); e.stopPropagation(); };
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eName => dropZone.addEventListener(eName, preventDefaults));
        ['dragenter', 'dragover'].forEach(eName => dropZone.addEventListener(eName, () => dropZone.classList.add('drag-over')));
        ['dragleave', 'drop'].forEach(eName => dropZone.addEventListener(eName, () => dropZone.classList.remove('drag-over')));
        dropZone.addEventListener('drop', (e: DragEvent) => {
            if (e.dataTransfer?.files) {
                selectedFiles.push(...Array.from(e.dataTransfer.files));
                updateComprovantesFileListUI();
            }
        });
        
        // --- INÍCIO DA NOVA LÓGICA DO BOTÃO ---
        submitButton.addEventListener('click', async () => {
            console.log("[DEBUG] Botão de Envio de COMPROVANTES foi clicado!");

            if (selectedFiles.length === 0) {
                statusMessage.textContent = 'Erro: Por favor, selecione ao menos um arquivo.';
                statusMessage.style.color = 'lightcoral';
                return;
            }

            // --- Referências aos campos do formulário ---
            const fornecedorInput = document.getElementById('comprovantes-fornecedor') as HTMLInputElement;
            const meioPagamentoSelect = document.getElementById('comprovantes-meio-pagamento') as HTMLSelectElement;
            const valorInput = document.getElementById('comprovantes-valor') as HTMLInputElement;
            const vencimentoInput = document.getElementById('comprovantes-vencimento') as HTMLInputElement;
            const pagamentoInput = document.getElementById('comprovantes-pagamento') as HTMLInputElement;
            
            // --- Limpa o destaque verde dos campos a cada clique ---
            [fornecedorInput, valorInput, vencimentoInput, pagamentoInput].forEach(el => el.classList.remove('ocr-filled'));

            const camposObrigatoriosPreenchidos = fornecedorInput.value && valorInput.value && vencimentoInput.value;

            // Se for a etapa de confirmação, envia direto
            if (isConfirmationStep) {
                await enviarLancamentoFinal();
                return;
            }

            // Se tudo estiver preenchido, envia direto (Cenário A)
            if (camposObrigatoriosPreenchidos) {
                console.log("[DEBUG] Cenário A: Todos os campos obrigatórios preenchidos. Enviando diretamente.");
                submitButton.textContent = 'Enviar Lançamento';
                await enviarLancamentoFinal();
            } else {
                // Se faltar algo, analisa com OCR (Cenário B)
                console.log("[DEBUG] Cenário B: Faltam dados. Acionando análise OCR.");
                submitButton.textContent = 'Analisar Comprovantes';
                await analisarComOCR();
            }

            // --- Função para analisar com OCR ---
            async function analisarComOCR() {
                submitButton.disabled = true;
                statusMessage.textContent = 'Analisando PDFs com OCR... Por favor, aguarde.';
                statusMessage.style.color = 'lightblue';
                
                const formData = new FormData();
                selectedFiles.forEach(file => formData.append('documento', file));
                formData.append('fornecedor', fornecedorInput.value);
                formData.append('meio_pagamento', meioPagamentoSelect.value);
                formData.append('valor', valorInput.value);
                if (vencimentoInput.value) formData.set('vencimento', vencimentoInput.value.split('-').reverse().join('/'));
                if (pagamentoInput.value) formData.set('pagamento', pagamentoInput.value.split('-').reverse().join('/'));

                try {
                    const response = await fetch('http://127.0.0.1:5000/analisar-comprovante', { method: 'POST', body: formData });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.detalhes || 'Erro na análise.');

                    // Preenche apenas os campos que estavam vazios e destaca
                    if (!fornecedorInput.value && result.fornecedor) {
                        fornecedorInput.value = result.fornecedor;
                        fornecedorInput.classList.add('ocr-filled');
                    }
                    if (!valorInput.value && result.valor) {
                        valorInput.value = result.valor;
                        valorInput.classList.add('ocr-filled');
                    }
                    if (!vencimentoInput.value && result.vencimento) {
                        vencimentoInput.value = result.vencimento.split('/').reverse().join('-');
                        vencimentoInput.classList.add('ocr-filled');
                    }
                    if (!pagamentoInput.value && result.pagamento) {
                        pagamentoInput.value = result.pagamento.split('/').reverse().join('-');
                        pagamentoInput.classList.add('ocr-filled');
                    }

                    statusMessage.textContent = 'Análise concluída. Verifique e confirme os dados.';
                    statusMessage.style.color = 'lightgreen';
                    submitButton.textContent = 'Confirmar e Enviar Lançamento';
                    isConfirmationStep = true;
                } catch (error) {
                    statusMessage.textContent = `Erro: ${error.message}`;
                    statusMessage.style.color = 'lightcoral';
                } finally {
                    submitButton.disabled = false;
                }
            }

            // --- Função para o envio final (Sheets/Drive) ---
            async function enviarLancamentoFinal() {
                submitButton.disabled = true;
                statusMessage.textContent = 'Enviando lançamento final para Sheets e Drive...';
                statusMessage.style.color = 'lightblue';
                
                const formDataFinal = new FormData();
                selectedFiles.forEach(file => formDataFinal.append('documento', file));
                formDataFinal.append('fornecedor', fornecedorInput.value);
                formDataFinal.append('meio_pagamento', meioPagamentoSelect.value);
                formDataFinal.append('valor', valorInput.value);
                if (vencimentoInput.value) formDataFinal.set('vencimento', vencimentoInput.value.split('-').reverse().join('/'));
                if (pagamentoInput.value) formDataFinal.set('pagamento', pagamentoInput.value.split('-').reverse().join('/'));

                try {
                    const response = await fetch('http://127.0.0.1:5000/upload', { method: 'POST', body: formDataFinal });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.detalhes || 'Erro no envio.');
                    
                    statusMessage.textContent = `Sucesso: ${result.detalhes}`;
                    statusMessage.style.color = 'lightgreen';
                    
                    submitButton.classList.add('hidden');
                    resetButton.classList.remove('hidden');
                } catch (error) {
                    statusMessage.textContent = `Erro: ${error.message}`;
                    statusMessage.style.color = 'lightcoral';
                    submitButton.disabled = false;
                }
            }
        });
        // --- FIM DA NOVA LÓGICA DO BOTÃO ---

        resetButton.addEventListener('click', () => {
            console.log("[DEBUG] Botão RESET do formulário de COMPROVANTES foi clicado.");
            (comprovantesContainer as HTMLDivElement).querySelectorAll('input, select').forEach(el => {
                (el as any).value = '';
                el.classList.remove('ocr-filled'); // Limpa o destaque verde
            });
            selectedFiles = [];
            updateComprovantesFileListUI();
            statusMessage.textContent = '';
            resetButton.classList.add('hidden');
            submitButton.classList.remove('hidden');
            submitButton.disabled = false;
            submitButton.textContent = 'Enviar Comprovantes'; // Restaura o texto original do botão
            isConfirmationStep = false;
        });
    } else {
        console.error("[ERRO] Container de COMPROVANTES (id='comprovantes-form-container') NÃO foi encontrado.");
    }
});