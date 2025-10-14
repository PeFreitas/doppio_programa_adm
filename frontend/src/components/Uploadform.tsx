

import React, { useState, useRef } from 'react';

const Uploadform: React.FC = () => {
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [statusMessage, setStatusMessage] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showReset, setShowReset] = useState(false);
    
    const formRef = useRef<HTMLFormElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files) {
            setSelectedFiles(prevFiles => [...prevFiles, ...Array.from(event.target.files!)]);
        }
        if(fileInputRef.current) fileInputRef.current.value = '';
    };

    const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault();
        event.stopPropagation();
        if (event.dataTransfer.files) {
            setSelectedFiles(prevFiles => [...prevFiles, ...Array.from(event.dataTransfer.files)]);
        }
    };

    const handleRemoveFile = (index: number) => {
        setSelectedFiles(prevFiles => prevFiles.filter((_, i) => i !== index));
    };

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        
        if (selectedFiles.length === 0) {
            setStatusMessage('Erro: Por favor, selecione ao menos um arquivo.');
            return;
        }

        setIsSubmitting(true);
        setStatusMessage('Enviando, por favor aguarde...');

        // --- CORREÇÃO: Construir o FormData manualmente ---
        const formData = new FormData();
        const formElements = formRef.current!.elements as any;
        
        // 1. Adiciona os ficheiros do estado
        selectedFiles.forEach(file => formData.append('documento', file));

        // 2. Adiciona os outros campos do formulário
        formData.append('fornecedor', formElements.fornecedor.value);
        formData.append('meio_pagamento', formElements.meio_pagamento.value);
        formData.append('valor', formElements.valor.value);
        formData.append('vencimento', formElements.vencimento.value);
        formData.append('emissao', formElements.emissao.value);
        formData.append('numero_nota', formElements.numero_nota.value);
        // --- Fim da correção ---

        try {
            const response = await fetch('http://127.0.0.1:5000/upload', {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.detalhes || 'Ocorreu um erro.');

            setStatusMessage(`Sucesso: ${result.detalhes}`);
            setShowReset(true);
            setSelectedFiles([]); 
        } catch (error: any) {
            setStatusMessage(`Erro: ${error.message}`);
        } finally {
            setIsSubmitting(false);
        }
    };
    
    const handleReset = () => {
        setSelectedFiles([]);
        setStatusMessage('');
        setShowReset(false);
        formRef.current?.reset();
    };

    return (
        <div className="container">
            <h1>Envio de Notas Fiscais</h1>
            <form ref={formRef} onSubmit={handleSubmit}>
                <div className="form-group">
                    <label htmlFor="file-input">Selecione o(s) Documento(s)</label>
                    <div id="drop-zone" className="drop-zone" onClick={() => fileInputRef.current?.click()} onDragOver={e => { e.preventDefault(); e.stopPropagation(); }} onDrop={handleDrop}>
                        <p>Arraste e solte os arquivos aqui ou clique para selecionar.</p>
                        <input type="file" id="file-input" name="documento" accept="image/*,.pdf" multiple hidden onChange={handleFileChange} ref={fileInputRef} />
                    </div>
                    <ul id="file-list" className="file-list">
                        {selectedFiles.map((file, index) => (
                            <li key={index}>
                                {file.name}
                                <button type="button" onClick={() => handleRemoveFile(index)} className="remove-file-btn">×</button>
                            </li>
                        ))}
                    </ul>
                </div>
                <div className="form-group">
                    <label htmlFor="fornecedor">Fornecedor</label>
                    <input type="text" id="fornecedor" name="fornecedor" required />
                </div>
                <div className="form-group">
                    <label htmlFor="meio_pagamento">Meio de Pagamento</label>
                    <select id="meio_pagamento" name="meio_pagamento">
                        <option value="BOLETO">Boleto</option>
                        <option value="PIX">PIX</option>
                        <option value="CARTAO DE CREDITO">Cartão de Crédito</option>
                        <option value="TRANSFERENCIA">Transferência</option>
                        <option value="OUTROS">Outros</option>
                    </select>
                </div>
                <div className="form-group">
                    <label htmlFor="valor">Valor (R$)</label>
                    <input type="text" id="valor" name="valor" required />
                </div>
                <div className="form-group">
                    <label htmlFor="vencimento">Data de Vencimento</label>
                    <input type="date" id="vencimento" name="vencimento" required />
                </div>
                <div className="form-group">
                    <label htmlFor="emissao">Data de Emissão</label>
                    <input type="date" id="emissao" name="emissao" />
                </div>
                <div className="form-group">
                    <label htmlFor="numero_nota">Número da Nota/Documento</label>
                    <input type="text" id="numero_nota" name="numero_nota" />
                </div>
                {!showReset ? (
                    <button type="submit" id="submit-button" disabled={isSubmitting}>Enviar Dados</button>
                ) : (
                    <button type="button" id="reset-button-notas" onClick={handleReset}>Enviar Outra Nota</button>
                )}
                <div id="status-message" style={{ color: statusMessage.startsWith('Erro') ? 'lightcoral' : 'lightgreen' }}>
                    {statusMessage}
                </div>
            </form>
        </div>
    );
};

export default Uploadform;
