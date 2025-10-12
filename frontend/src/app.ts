document.addEventListener('DOMContentLoaded', () => {
    
    // --- LÓGICA DE NAVEGAÇÃO DO MENU (Permanece igual) ---
    const navLinks = document.querySelectorAll('.nav-link');
    const contentSections = document.querySelectorAll('.content-section');

    navLinks.forEach(link => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            navLinks.forEach(nav => nav.classList.remove('active'));
            contentSections.forEach(section => section.classList.remove('active'));
            const clickedLink = event.currentTarget as HTMLElement;
            clickedLink.classList.add('active');
            const targetId = clickedLink.dataset.target;
            if (targetId) {
                document.getElementById(targetId)?.classList.add('active');
            }
        });
    });

    // --- NOVA LÓGICA DE UPLOAD DE ARQUIVOS ---
    const form = document.getElementById('upload-form') as HTMLFormElement;
    if (!form) return;

    const dropZone = document.getElementById('drop-zone') as HTMLDivElement;
    const fileInput = document.getElementById('file-input') as HTMLInputElement;
    const fileListDisplay = document.getElementById('file-list') as HTMLUListElement;
    const statusMessage = document.getElementById('status-message') as HTMLDivElement;
    const submitButton = document.getElementById('submit-button') as HTMLButtonElement;

    // Array para gerenciar a lista de arquivos selecionados
    let selectedFiles: File[] = [];

    // Função para atualizar a lista de arquivos na tela
    const updateFileListUI = () => {
        fileListDisplay.innerHTML = ''; // Limpa a lista visual
        selectedFiles.forEach((file, index) => {
            const listItem = document.createElement('li');
            listItem.textContent = file.name;

            const removeBtn = document.createElement('button');
            removeBtn.textContent = '×';
            removeBtn.className = 'remove-file-btn';
            removeBtn.type = 'button';
            removeBtn.onclick = () => {
                selectedFiles.splice(index, 1); // Remove o arquivo do array
                updateFileListUI(); // Atualiza a tela
            };

            listItem.appendChild(removeBtn);
            fileListDisplay.appendChild(listItem);
        });
    };
    
    // Abre o seletor de arquivos ao clicar na área
    dropZone.addEventListener('click', () => fileInput.click());

    // Adiciona arquivos selecionados pelo clique
    fileInput.addEventListener('change', () => {
        if (fileInput.files) {
            selectedFiles.push(...Array.from(fileInput.files));
            updateFileListUI();
            fileInput.value = ''; // Reseta o input para permitir selecionar o mesmo arquivo novamente
        }
    });

    // --- Eventos de Drag and Drop ---
    const preventDefaults = (e: Event) => {
        e.preventDefault();
        e.stopPropagation();
    };
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    // Adiciona o efeito visual ao arrastar sobre a área
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('drag-over'), false);
    });

    // Remove o efeito visual ao sair da área
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('drag-over'), false);
    });

    // Adiciona arquivos soltos na área
    dropZone.addEventListener('drop', (e: DragEvent) => {
        const dt = e.dataTransfer;
        if (dt?.files) {
            selectedFiles.push(...Array.from(dt.files));
            updateFileListUI();
        }
    }, false);


    // --- Lógica de Submissão do Formulário ---
    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        if (selectedFiles.length === 0) {
            statusMessage.textContent = 'Erro: Por favor, selecione ao menos um arquivo.';
            statusMessage.style.color = 'lightcoral';
            return;
        }
        
        submitButton.disabled = true;
        statusMessage.textContent = 'Enviando, por favor aguarde...';
        statusMessage.style.color = 'lightblue';

        const formData = new FormData(form);
        formData.delete('documento'); // Remove a entrada padrão do input
        // Adiciona todos os arquivos da nossa lista gerenciada
        selectedFiles.forEach(file => {
            formData.append('documento', file);
        });
        
        // Formata as datas
        const vencimentoInput = document.getElementById('vencimento') as HTMLInputElement;
        const emissaoInput = document.getElementById('emissao') as HTMLInputElement;
        if (vencimentoInput.value) formData.set('vencimento', vencimentoInput.value.split('-').reverse().join('/'));
        if (emissaoInput.value) formData.set('emissao', emissaoInput.value.split('-').reverse().join('/'));
        
        try {
            const response = await fetch('http://127.0.0.1:5000/upload', { method: 'POST', body: formData });
            const result = await response.json();

            if (response.ok) {
                statusMessage.textContent = `Sucesso: ${result.detalhes}`;
                statusMessage.style.color = 'lightgreen';
                form.reset();
                selectedFiles = []; // Limpa a lista de arquivos
                updateFileListUI(); // Limpa a lista visual
            } else {
                throw new Error(result.detalhes || 'Ocorreu um erro desconhecido.');
            }
        } catch (error) {
            statusMessage.textContent = `Erro: ${error.message}`;
            statusMessage.style.color = 'lightcoral';
        } finally {
            submitButton.disabled = false;
        }
    });
});