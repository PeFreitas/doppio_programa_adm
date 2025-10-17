import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const Dashboard: React.FC = () => {
    const [vendasData, setVendasData] = useState([]);

    useEffect(() => {
        // Função para buscar os dados da sua API backend
        const fetchVendas = async () => {
            try {
                const response = await fetch('http://127.0.0.1:5000/relatorios/vendas-por-dia');
                const data = await response.json();
                setVendasData(data);
            } catch (error) {
                console.error("Erro ao buscar dados de vendas:", error);
            }
        };

        fetchVendas();
    }, []);

    return (
        <div className="dashboard-container" style={{ width: '100%', height: 400 }}>
            <h2>Vendas por Dia</h2>
            {/* ResponsiveContainer torna o gráfico responsivo */}
            <ResponsiveContainer>
                <BarChart
                    data={vendasData}
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="dia" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="totalVendas" fill="#c3073f" />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
};

export default Dashboard;