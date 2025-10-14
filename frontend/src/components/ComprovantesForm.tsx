// frontend/src/components/ComprovantesForm.tsx

import React, { useState, useRef } from 'react';

interface OcrData {
    fornecedor?: string;
    valor?: string;
    vencimento?: string;
    pagamento?: string;
}

const ComprovantesForm: React.FC = () => {
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [statusMessage, setStatusMessage] = useState({ text: '', type: 'info' });
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showReset, setShowReset] = useState(false);
    const [isConfirmationStep, setIsConfirmationStep] = useState(false);
    const [ocrFilledFields, setOcrFilledFields] = useState<string[]>([]);
    
    const formRef = useRef<HTMLFormElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files) {
            setSelectedFiles(prev => [...prev, ...Array.from(event.target.files!)]);
        }
        if(fileInputRef.current) fileInputRef.current.value = '';
    };

    const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
        event.preventDefault();
        if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
            setSelectedFiles(prev => [...prev, ...Array.from(event.dataTransfer.files)]);
        }
    };

    const handleRemoveFile = (index: number) => {
        setSelectedFiles(prev => prev.filter((_, i) => i !== index));
    };

    const getFormData = () => {
        const formData = new FormData();
        const formElements = formRef.current!.elements as any;
        
        selectedFiles.forEach(file => formData.append('documento', file));

        formData.append('fornecedor', formElements.fornecedor.value);
        formData.append('meio_pagamento', formElements.meio_pagamento.value);
        formData.append('valor', formElements.valor.value);
        formData.append('vencimento', formElements.vencimento.value);
        formData.append('pagamento', formElements.pagamento.value);
        return formData;
    };

    const handleSubmit = async () => {
        if (selectedFiles.length === 0) {
            setStatusMessage({ text: 'Erro: Por favor, selecione ao menos um arquivo.', type: 'error' });
            return;
        }

        const formElements = formRef.current!.elements as any;
        const camposObrigatoriosPreenchidos = formElements.fornecedor.value && formElements.valor.value && formElements.vencimento.value;

        if (isConfirmationStep || camposObrigatoriosPreenchidos) {
            await enviarLancamentoFinal();
        } else {
            await analisarComOCR();
        }
    };

    const analisarComOCR = async () => {
        setIsSubmitting(true);
        setStatusMessage({ text: 'Analisando PDFs com OCR... Por favor, aguarde.', type: 'info' });
        try {
            const formData = getFormData();
            const response = await fetch('http://127.0.0.1:5000/analisar-comprovante', { method: 'POST', body: formData });
            const result: OcrData = await response.json();
            if (!response.ok) throw new Error((result as any).detalhes || 'Erro na análise.');
            
            const form = formRef.current!;
            const filled: string[] = [];
            if (!form.fornecedor.value && result.fornecedor) { form.fornecedor.value = result.fornecedor; filled.push('fornecedor'); }
            if (!form.valor.value && result.valor) { form.valor.value = result.valor; filled.push('valor'); }
            if (!form.vencimento.value && result.vencimento) { form.vencimento.value = result.vencimento.split('/').reverse().join('-'); filled.push('vencimento'); }
            if (!form.pagamento.value && result.pagamento) { form.pagamento.value = result.pagamento.split('/').reverse().join('-'); filled.push('pagamento'); }
            
            setOcrFilledFields(filled);
            setStatusMessage({ text: 'Análise concluída. Verifique e confirme os dados.', type: 'success' });
            setIsConfirmationStep(true);
        } catch (error: any) {
            setStatusMessage({ text: `Erro: ${error.message}`, type: 'error' });
        } finally {
            setIsSubmitting(false);
        }
    };
    
    const enviarLancamentoFinal = async () => {
        setIsSubmitting(true);
        setStatusMessage({ text: 'Enviando lançamento final para Sheets e Drive...', type: 'info' });
        try {
            const formData = getFormData();
            const response = await fetch('http://127.0.0.1:5000/upload', { method: 'POST', body: formData });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detalhes || 'Erro no envio.');

            setStatusMessage({ text: `Sucesso: ${result.detalhes}`, type: 'success' });
            setShowReset(true);
            setSelectedFiles([]);
        } catch (error: any) {
            setStatusMessage({ text: `Erro: ${error.message}`, type: 'error' });
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleReset = () => {
        setSelectedFiles([]);
        setStatusMessage({ text: '', type: 'info' });
        setShowReset(false);
        setIsConfirmationStep(false);
        setOcrFilledFields([]);
        formRef.current?.reset();
    };

    const getButtonText = () => {
        if (isConfirmationStep) return 'Confirmar e Enviar Lançamento';
        return 'Analisar Comprovantes';
    };

    return (
        <div className="container">
            <h1>Envio de Comprovantes</h1>
            <form ref={formRef} onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
                <div className="form-group">
                    <label htmlFor="comprovantes-file-input">Selecione o(s) Comprovante(s) (PDF)</label>
                    <div id="comprovantes-drop-zone" className="drop-zone" onClick={() => fileInputRef.current?.click()} onDragOver={e => e.preventDefault()} onDrop={handleDrop}>
                        <p>Arraste e solte os PDFs aqui ou clique.</p>
                        <input type="file" id="comprovantes-file-input" ref={fileInputRef} name="documento" accept=".pdf" multiple hidden onChange={handleFileChange} />
                    </div>
                    <ul id="comprovantes-file-list" className="file-list">
                        {selectedFiles.map((file, index) => (
                            <li key={index}>{file.name} <button type="button" className="remove-file-btn" onClick={() => handleRemoveFile(index)}>×</button></li>
                        ))}
                    </ul>
                </div>
                <div className="form-group">
                    <label htmlFor="comprovantes-fornecedor">Fornecedor (Opcional)</label>
                    <input type="text" id="comprovantes-fornecedor" name="fornecedor" className={ocrFilledFields.includes('fornecedor') ? 'ocr-filled' : ''}/>
                </div>
                <div className="form-group">
                    <label htmlFor="comprovantes-meio-pagamento">Meio de Pagamento</label>
                    <select id="comprovantes-meio-pagamento" name="meio_pagamento">
                        <option value="BOLETO">Boleto</option>
                        <option value="PIX">PIX</option>
                        <option value="CARTAO DE CREDITO">Cartão de Crédito</option>
                        <option value="TRANSFERENCIA">Transferência</option>
                        <option value="OUTROS">Outros</option>
                    </select>
                </div>
                <div className="form-group">
                    <label htmlFor="comprovantes-valor">Valor (R$) (Opcional)</label>
                    <input type="text" id="comprovantes-valor" name="valor" className={ocrFilledFields.includes('valor') ? 'ocr-filled' : ''} />
                </div>
                <div className="form-group">
                    <label htmlFor="comprovantes-vencimento">Data de Vencimento (Opcional)</label>
                    <input type="date" id="comprovantes-vencimento" name="vencimento" className={ocrFilledFields.includes('vencimento') ? 'ocr-filled' : ''} />
                </div>
                <div className="form-group">
                    <label htmlFor="comprovantes-pagamento">Data de Pagamento (Opcional)</label>
                    <input type="date" id="comprovantes-pagamento" name="pagamento" className={ocrFilledFields.includes('pagamento') ? 'ocr-filled' : ''} />
                </div>
                {!showReset ? (
                    <button type="submit" disabled={isSubmitting}>{getButtonText()}</button>
                ) : (
                    <button type="button" onClick={handleReset}>Enviar Outro Comprovante</button>
                )}
                <div id="comprovantes-status-message" style={{ color: statusMessage.type === 'error' ? 'lightcoral' : statusMessage.type === 'success' ? 'lightgreen' : 'lightblue' }}>
                    {statusMessage.text}
                </div>
            </form>
        </div>
    );
};

export default ComprovantesForm;
