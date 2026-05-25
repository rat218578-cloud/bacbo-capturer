#!/usr/bin/env python3
"""
Interface Web para visualizar resultados do Bac Bo
Roda como um servidor FastAPI
"""

import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# ========== CONFIGURAÇÕES ==========
DATABASE_URL = "postgresql://neondb_owner:npg_9mWRy6lskeCT@ep-billowing-feather-apmnvtae-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require"

app = FastAPI(title="Bac Bo Results API", description="API para resultados do Bac Bo")

# ========== CONEXÃO COM BANCO ==========
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# ========== MODELOS ==========
class RoundResult(BaseModel):
    id: int
    round_number: Optional[str]
    result: Optional[str]
    player_dice: Optional[List[int]]
    banker_dice: Optional[List[int]]
    player_total: Optional[int]
    banker_total: Optional[int]
    all_dice: Optional[List[int]]
    timestamp: Optional[datetime]
    created_at: Optional[datetime]

class StatsResponse(BaseModel):
    total_rounds: int
    banker_wins: int
    player_wins: int
    tie_wins: int
    banker_percent: float
    player_percent: float
    tie_percent: float
    last_update: Optional[str]

# ========== ENDPOINTS DA API ==========
@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Retorna estatísticas gerais"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT total_rounds, banker_wins, player_wins, tie_wins, last_update 
        FROM bacbo_stats LIMIT 1
    """)
    stats = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if not stats or stats['total_rounds'] == 0:
        return StatsResponse(
            total_rounds=0,
            banker_wins=0,
            player_wins=0,
            tie_wins=0,
            banker_percent=0,
            player_percent=0,
            tie_percent=0,
            last_update=None
        )
    
    total = stats['total_rounds']
    return StatsResponse(
        total_rounds=total,
        banker_wins=stats['banker_wins'],
        player_wins=stats['player_wins'],
        tie_wins=stats['tie_wins'],
        banker_percent=round(stats['banker_wins'] / total * 100, 1),
        player_percent=round(stats['player_wins'] / total * 100, 1),
        tie_percent=round(stats['tie_wins'] / total * 100, 1),
        last_update=stats['last_update'].isoformat() if stats['last_update'] else None
    )

@app.get("/api/rounds", response_model=List[RoundResult])
async def get_rounds(limit: int = 50, offset: int = 0):
    """Retorna últimas rodadas"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, round_number, result, player_dice, banker_dice, 
               player_total, banker_total, all_dice, timestamp, created_at
        FROM bacbo_rounds 
        ORDER BY id DESC 
        LIMIT %s OFFSET %s
    """, (limit, offset))
    
    rounds = cur.fetchall()
    cur.close()
    conn.close()
    
    return rounds

@app.get("/api/last_result")
async def get_last_result():
    """Retorna o último resultado"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT round_number, result, player_total, banker_total, 
               player_dice, banker_dice, timestamp
        FROM bacbo_rounds 
        ORDER BY id DESC 
        LIMIT 1
    """)
    
    last = cur.fetchone()
    cur.close()
    conn.close()
    
    return last or {}

# ========== INTERFACE HTML ==========
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bac Bo Monitor - Resultados ao Vivo</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                min-height: 100vh;
                color: #fff;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }
            
            /* Header */
            .header {
                text-align: center;
                padding: 30px 0;
                border-bottom: 1px solid rgba(255,255,255,0.1);
                margin-bottom: 30px;
            }
            
            .header h1 {
                font-size: 2.5rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .header p {
                color: #888;
                margin-top: 10px;
            }
            
            /* Stats Cards */
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            
            .stat-card {
                background: rgba(255,255,255,0.05);
                border-radius: 15px;
                padding: 20px;
                text-align: center;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1);
                transition: transform 0.3s ease;
            }
            
            .stat-card:hover {
                transform: translateY(-5px);
            }
            
            .stat-value {
                font-size: 2.5rem;
                font-weight: bold;
                margin: 10px 0;
            }
            
            .stat-label {
                color: #888;
                font-size: 0.9rem;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .stat-card.banker .stat-value { color: #4ade80; }
            .stat-card.player .stat-value { color: #60a5fa; }
            .stat-card.tie .stat-value { color: #fbbf24; }
            .stat-card.total .stat-value { color: #a78bfa; }
            
            /* Último Resultado */
            .last-result {
                background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
                border-radius: 20px;
                padding: 30px;
                text-align: center;
                margin-bottom: 40px;
                border: 1px solid rgba(255,255,255,0.1);
            }
            
            .last-result-label {
                font-size: 0.9rem;
                color: #888;
                letter-spacing: 2px;
                margin-bottom: 10px;
            }
            
            .last-result-value {
                font-size: 3rem;
                font-weight: bold;
                margin: 10px 0;
            }
            
            .last-result-dice {
                display: flex;
                justify-content: center;
                gap: 20px;
                margin-top: 20px;
            }
            
            .dice-group {
                background: rgba(0,0,0,0.3);
                border-radius: 15px;
                padding: 15px 25px;
            }
            
            .dice-group span {
                font-size: 1.5rem;
                margin: 0 5px;
            }
            
            .dice-label {
                font-size: 0.8rem;
                color: #888;
                margin-bottom: 5px;
            }
            
            /* Tabela de Rodadas */
            .rounds-table {
                background: rgba(255,255,255,0.05);
                border-radius: 15px;
                overflow: hidden;
            }
            
            .rounds-table h3 {
                padding: 20px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }
            
            table {
                width: 100%;
                border-collapse: collapse;
            }
            
            th, td {
                padding: 12px 15px;
                text-align: center;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            
            th {
                background: rgba(0,0,0,0.3);
                color: #888;
                font-weight: 500;
            }
            
            tr:hover {
                background: rgba(255,255,255,0.03);
            }
            
            .badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.85rem;
                font-weight: 500;
            }
            
            .badge-banker {
                background: rgba(74, 222, 128, 0.2);
                color: #4ade80;
            }
            
            .badge-player {
                background: rgba(96, 165, 250, 0.2);
                color: #60a5fa;
            }
            
            .badge-tie {
                background: rgba(251, 191, 36, 0.2);
                color: #fbbf24;
            }
            
            .dice {
                font-family: monospace;
                font-size: 1.1rem;
            }
            
            /* Auto-refresh */
            .auto-refresh {
                text-align: right;
                font-size: 0.8rem;
                color: #888;
                margin-top: 20px;
            }
            
            /* Loading */
            .loading {
                text-align: center;
                padding: 40px;
                color: #888;
            }
            
            @media (max-width: 768px) {
                .stats-grid {
                    grid-template-columns: repeat(2, 1fr);
                }
                
                .last-result-value {
                    font-size: 2rem;
                }
                
                th, td {
                    padding: 8px 10px;
                    font-size: 0.85rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎲 Bac Bo Monitor</h1>
                <p>Resultados ao vivo - Atualização automática</p>
            </div>
            
            <!-- Stats Grid -->
            <div class="stats-grid" id="stats">
                <div class="loading">Carregando estatísticas...</div>
            </div>
            
            <!-- Último Resultado -->
            <div class="last-result" id="lastResult">
                <div class="last-result-label">ÚLTIMA RODADA</div>
                <div class="loading">Aguardando primeira rodada...</div>
            </div>
            
            <!-- Tabela de Rodadas -->
            <div class="rounds-table">
                <h3>📋 Histórico de Rodadas</h3>
                <div id="roundsList">
                    <div class="loading">Carregando rodadas...</div>
                </div>
            </div>
            
            <div class="auto-refresh">
                🔄 Atualizando automaticamente a cada 5 segundos
            </div>
        </div>
        
        <script>
            async function fetchStats() {
                const response = await fetch('/api/stats');
                return response.json();
            }
            
            async function fetchRounds(limit = 30) {
                const response = await fetch(`/api/rounds?limit=${limit}`);
                return response.json();
            }
            
            async function fetchLastResult() {
                const response = await fetch('/api/last_result');
                return response.json();
            }
            
            function renderStats(stats) {
                const html = `
                    <div class="stat-card total">
                        <div class="stat-label">TOTAL DE RODADAS</div>
                        <div class="stat-value">${stats.total_rounds}</div>
                    </div>
                    <div class="stat-card banker">
                        <div class="stat-label">🏦 BANKER</div>
                        <div class="stat-value">${stats.banker_wins}</div>
                        <div style="font-size:0.8rem">${stats.banker_percent}%</div>
                    </div>
                    <div class="stat-card player">
                        <div class="stat-label">👤 PLAYER</div>
                        <div class="stat-value">${stats.player_wins}</div>
                        <div style="font-size:0.8rem">${stats.player_percent}%</div>
                    </div>
                    <div class="stat-card tie">
                        <div class="stat-label">🤝 TIE</div>
                        <div class="stat-value">${stats.tie_wins}</div>
                        <div style="font-size:0.8rem">${stats.tie_percent}%</div>
                    </div>
                `;
                document.getElementById('stats').innerHTML = html;
            }
            
            function renderLastResult(result) {
                if (!result.round_number) {
                    document.getElementById('lastResult').innerHTML = `
                        <div class="last-result-label">ÚLTIMA RODADA</div>
                        <div style="padding:20px">Aguardando primeira rodada...</div>
                    `;
                    return;
                }
                
                const emoji = result.result === 'Banker' ? '🏦' : result.result === 'Player' ? '👤' : '🤝';
                const color = result.result === 'Banker' ? '#4ade80' : result.result === 'Player' ? '#60a5fa' : '#fbbf24';
                
                const html = `
                    <div class="last-result-label">ÚLTIMA RODADA</div>
                    <div class="last-result-value" style="color: ${color}">
                        ${emoji} ${result.result}
                    </div>
                    <div style="font-size:0.9rem; color:#888">Rodada: ${result.round_number}</div>
                    <div class="last-result-dice">
                        <div class="dice-group">
                            <div class="dice-label">👤 PLAYER</div>
                            <span>🎲 ${result.player_dice ? result.player_dice.join(' ') : '-'}</span>
                            <span style="color:#60a5fa; margin-left:10px">${result.player_total || 0}</span>
                        </div>
                        <div class="dice-group">
                            <div class="dice-label">🏦 BANKER</div>
                            <span>🎲 ${result.banker_dice ? result.banker_dice.join(' ') : '-'}</span>
                            <span style="color:#4ade80; margin-left:10px">${result.banker_total || 0}</span>
                        </div>
                    </div>
                    <div style="margin-top:15px; font-size:0.8rem; color:#666">
                        ${new Date(result.timestamp).toLocaleString('pt-BR')}
                    </div>
                `;
                document.getElementById('lastResult').innerHTML = html;
            }
            
            function renderRounds(rounds) {
                if (!rounds.length) {
                    document.getElementById('roundsList').innerHTML = '<div class="loading">Nenhuma rodada registrada ainda</div>';
                    return;
                }
                
                const table = `
                    <table>
                        <thead>
                            <tr>
                                <th>Rodada</th>
                                <th>Resultado</th>
                                <th>Dados Player</th>
                                <th>Dados Banker</th>
                                <th>Total</th>
                                <th>Data/Hora</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rounds.map(r => {
                                const badgeClass = r.result === 'Banker' ? 'badge-banker' : r.result === 'Player' ? 'badge-player' : 'badge-tie';
                                const emoji = r.result === 'Banker' ? '🏦' : r.result === 'Player' ? '👤' : '🤝';
                                return `
                                    <tr>
                                        <td>${r.round_number || '-'}</td>
                                        <td><span class="badge ${badgeClass}">${emoji} ${r.result || '-'}</span></td>
                                        <td class="dice">${r.player_dice ? r.player_dice.join(' + ') : '-'}</td>
                                        <td class="dice">${r.banker_dice ? r.banker_dice.join(' + ') : '-'}</td>
                                        <td>${r.player_total || 0} vs ${r.banker_total || 0}</td>
                                        <td>${new Date(r.timestamp).toLocaleString('pt-BR')}</td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                `;
                document.getElementById('roundsList').innerHTML = table;
            }
            
            async function refreshData() {
                try {
                    const [stats, rounds, lastResult] = await Promise.all([
                        fetchStats(),
                        fetchRounds(30),
                        fetchLastResult()
                    ]);
                    
                    renderStats(stats);
                    renderLastResult(lastResult);
                    renderRounds(rounds);
                } catch (error) {
                    console.error('Erro ao carregar dados:', error);
                }
            }
            
            // Atualiza a cada 5 segundos
            refreshData();
            setInterval(refreshData, 5000);
        </script>
    </body>
    </html>
    """

# ========== MAIN (executa junto com capturer) ==========
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
