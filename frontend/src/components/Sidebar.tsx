import React from 'react';

interface SidebarProps {
    onNavigate: (target: string) => void;
    activeSection: string;
}

const Sidebar: React.FC<SidebarProps> = ({ onNavigate, activeSection }) => {
    const [openDropdown, setOpenDropdown] = React.useState<string | null>(null);

    const handleDropdownToggle = (dropdown: string) => {
        setOpenDropdown(openDropdown === dropdown ? null : dropdown);
    };

    return (
        <nav className="sidebar">
            <div className="sidebar-header">
                <h1 className="logo">DO<span>PP</span>IO CAFÉ</h1>
            </div>
            <ul className="nav-menu">
                <li>
                    <a
                        href="#"
                        className={`nav-link ${activeSection === 'notas' ? 'active' : ''}`}
                        onClick={() => onNavigate('notas')}
                    >
                        Envio de Notas
                    </a>
                </li>
                <li>
                    <a
                        href="#"
                        className={`nav-link ${activeSection === 'comprovantes' ? 'active' : ''}`}
                        onClick={() => onNavigate('comprovantes')}
                    >
                        Envio de Comprovantes
                    </a>
                </li>
                <li>
                    <a
                        href="#"
                        className={`nav-link ${activeSection === 'notinhas' ? 'active' : ''}`}
                        onClick={() => onNavigate('notinhas')}
                    >
                        Envio de Notinhas
                    </a>
                </li>
                <li className={`nav-item-dropdown ${openDropdown === 'relatorios' ? 'open' : ''}`}>
                    <a href="#" className="nav-link dropdown-toggle" onClick={() => handleDropdownToggle('relatorios')}>
                        Relatórios
                    </a>
                    <ul className="submenu">
                        <li><a href="#" className="nav-link" onClick={() => onNavigate('dre')}>DRE</a></li>
                        <li><a href="#" className="nav-link" onClick={() => onNavigate('fluxo-caixa')}>Fluxo de Caixa</a></li>
                        <li><a href="#" className="nav-link" onClick={() => onNavigate('estoque')}>Controle de Estoque</a></li>
                        <li><a href="#" className="nav-link" onClick={() => onNavigate('vendas')}>Vendas de Produtos</a></li>
                    </ul>
                </li>
            </ul>
        </nav>
    );
};

export default Sidebar;