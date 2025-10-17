// frontend/src/App.tsx

import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import UploadForm from './components/Uploadform';
import ComprovantesForm from './components/ComprovantesForm'; // <-- 1. Importe o novo componente
import './styles/main.scss';
import Dashboard from './components/Dashboard';

const App: React.FC = () => {
    const [activeSection, setActiveSection] = useState('notas');

    const handleNavigate = (target: string) => {
        setActiveSection(target);
    };

    return (
        <div className="app-container">
            <Sidebar onNavigate={handleNavigate} activeSection={activeSection} />
            <main className="main-content">
                {activeSection === 'notas' && (
                    <section id="notas" className="content-section active">
                        <UploadForm />
                    </section>
                )}
                {activeSection === 'comprovantes' && (
                     <section id="comprovantes" className="content-section active">
                        {/* 2. Substitua o h2 pelo novo componente */}
                        <ComprovantesForm />
                     </section>
                )}
                 {activeSection === 'dre' && (
                     <section id="dre" className="content-section active">
                        {/* Aqui estamos usando o componente Dashboard que você importou */}
                        <Dashboard />
                     </section>
                )}
            </main>
        </div>
    );
};

export default App;