#!/usr/bin/env python3
"""
API Web para visualizar resultados e sinais do Bac Bo
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os
from typing import Optional, List

# ============================================================
# CONFIGURAÇÕES
# ============================================================
DATABASE_URL = "postgresql://neondb_owner:npg_9mWRy6lskeCT@ep-billowing-feather-apmnvtae-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require"

app = FastAPI(title="Bac Bo Analyzer API", description="API para resultados e sinais do Bac Bo")

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# FUNÇÕES DE BANCO
# ============================================================
def get_db():
    """Retorna conexão com o banco"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# ============================================================
# ENDPOINTS DA API
# ============================================================
@app.get("/health")
async def health_check():
    """Verifica saúde da API"""
    try:
        db = get_db()
        db.close()
        return {"status": "ok", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/api/stats")
async def get_stats():
    """Retorna estatísticas gerais"""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM bacbo_statistics ORDER BY id DESC LIMIT 1")
    stats = cur.fetchone()
    cur.close()
    db.close()
    
    if not stats:
        return {
            "total_rounds": 0,
            "banker_wins": 0,
            "player_wins": 0,
            "tie_wins": 0,
            "banker_percent": 0,
            "player_percent": 0,
            "tie_percent": 0,
            "current_streak": None,
            "streak_count": 0
        }
    
    return stats

@app.get("/api/rounds")
async def get_rounds(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    """Retorna últimas rodadas"""
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT id, round_number, result, player_dice, banker_dice, 
               player_total, banker_total, sequence, timestamp
        FROM bacbo_rounds 
        ORDER BY id DESC 
        LIMIT %s OFFSET %s
    """, (limit, offset))
    rounds = cur.fetchall()
    cur.close()
    db.close()
    return rounds

@app.get("/api/signals")
async def get_signals(limit: int = Query(50, ge=1, le=500)):
    """Retorna últimos sinais gerados"""
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT id, signal_type, confidence, message, pattern, streak, created_at
        FROM bacbo_signals 
        ORDER BY id DESC 
        LIMIT %s
    """, (limit,))
    signals = cur.fetchall()
    cur.close()
    db.close()
    return signals

@app.get("/api/last_result")
async def get_last_result():
    """Retorna o último resultado"""
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT round_number, result, player_total, banker_total, 
               player_dice, banker_dice, timestamp
        FROM bacbo_rounds 
        ORDER BY id DESC 
        LIMIT 1
    """)
    last = cur.fetchone()
    cur.close()
    db.close()
    return last or {}

@app.get("/api/sequence")
async def get_sequence(limit: int = Query(30, ge=1, le=100)):
    """Retorna sequência de resultados para análise"""
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT result FROM bacbo_rounds 
        ORDER BY id DESC 
        LIMIT %s
    """, (limit,))
    results = cur.fetchall()
    cur.close()
    db.close()
    
    sequence = [r['result'] for r in results]
    return {"sequence": sequence, "length": len(sequence)}

# ============================================================
# INTERFACE WEB COMPLETA
# ============================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bac Bo Analyzer - Sinais em Tempo Real</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
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
        }
        
        .header p {
            color: #888;
            margin-top: 10px;
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s;
        }
        
        .stat-card:hover { transform: translateY(-5px); }
        
        .stat-value { font-size: 2.5rem; font-weight: bold; margin: 10px 0; }
        .stat-label { color: #888; font-size: 0.9rem; text-transform: uppercase; }
        
        .stat-card.banker .stat-value { color: #4ade80; }
        .stat-card.player .stat-value { color: #60a5fa; }
        .stat-card.tie .stat-value { color: #fbbf24; }
        .stat-card.total .stat-value { color: #a78bfa; }
        
        /* Último Resultado */
        .last-result {
            background: linear-gradient(135deg, rgba(102,126,234,0.2) 0%, rgba(118,75,162,0.2) 100%);
            border-radius: 20px;
            padding: 30px;
            text-align: center;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .last-result-value { font-size: 3rem; font-weight: bold; margin: 10px 0; }
        .last-result-dice { display: flex; justify-content: center; gap: 20px; margin-top: 20px; flex-wrap: wrap; }
        .dice-group { background: rgba(0,0,0,0.3); border-radius: 15px; padding: 15px 25px; }
        .dice-label { font-size: 0.8rem; color: #888; margin-bottom: 5px; }
        
        /* Sinais */
        .signals-section {
            background: rgba(255,255,255,0.03);
            border-radius: 15px;
            margin-bottom: 30px;
            overflow: hidden;
        }
        
        .signals-header {
            padding: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            background: rgba(0,0,0,0.2);
        }
        
        .signal-card {
            border-left: 4px solid;
            margin: 15px;
            padding: 15px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            transition: all 0.3s;
        }
        
        .signal-card.banker { border-left-color: #4ade80; }
        .signal-card.player { border-left-color: #60a5fa; }
        .signal-card.tie { border-left-color: #fbbf24; }
        
        .signal-confidence { font-size: 1.2rem; font-weight: bold; margin-bottom: 5px; }
        .signal-message { color: #ccc; margin: 10px 0; }
        .signal-time { font-size: 0.75rem; color: #666; }
        
        /* Tabela de Rodadas */
        .rounds-table {
            background: rgba(255,255,255,0.03);
            border-radius: 15px;
            overflow: hidden;
        }
        
        .rounds-header {
            padding: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            background: rgba(0,0,0,0.2);
        }
        
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px 15px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.05); }
        th { background: rgba(0,0,0,0.3); color: #888; font-weight: 500; }
        tr:hover { background: rgba(255,255,255,0.03); }
        
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
        }
        .badge-banker { background: rgba(74,222,128,0.2); color: #4ade80; }
        .badge-player { background: rgba(96,165,250,0.2); color: #60a5fa; }
        .badge-tie { background: rgba(251,191,36,0.2); color: #fbbf24; }
        
        /* Sequência */
        .sequence-bar {
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
            text-align: center;
            font-family: monospace;
            font-size: 1.5rem;
            letter-spacing: 10px;
            overflow-x: auto;
            white-space: nowrap;
        }
        
        .auto-refresh { text-align: right; font-size: 0.8rem; color: #888; margin-top: 20px; }
        .loading { text-align: center; padding: 40px; color: #888; }
        
        @media (max-width: 768px) {
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .last-result-value { font-size: 2rem; }
            th, td { padding: 8px 10px; font-size: 0.8rem; }
            .sequence-bar { font-size: 1rem; letter-spacing: 5px; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🎲 Bac Bo Analyzer</h1>
        <p>Sinais em tempo real - Análise de padrões - Estatísticas</p>
    </div>
    
    <div class="stats-grid" id="stats"><div class="loading">Carregando estatísticas...</div></div>
    
    <div class="last-result" id="lastResult"><div class="loading">Carregando último resultado...</div></div>
    
    <div class="signals-section">
        <div class="signals-header"><h3>📢 Últimos Sinais</h3></div>
        <div id="signals"><div class="loading">Carregando sinais...</div></div>
    </div>
    
    <div class="rounds-table">
        <div class="rounds-header"><h3>📋 Histórico de Rodadas</h3></div>
        <div id="rounds"><div class="loading">Carregando rodadas...</div></div>
    </div>
    
    <div class="sequence-bar" id="sequence">Carregando sequência...</div>
    <div class="auto-refresh">🔄 Atualizando automaticamente a cada 5 segundos</div>
</div>

<script>
    const API_BASE = '';
    
    async function fetchStats() {
        const res = await fetch('/api/stats');
        return res.json();
    }
    
    async function fetchRounds(limit = 30) {
        const res = await fetch(`/api/rounds?limit=${limit}`);
        return res.json();
    }
    
    async function fetchSignals(limit = 20) {
        const res = await fetch(`/api/signals?limit=${limit}`);
        return res.json();
    }
    
    async function fetchLastResult() {
        const res = await fetch('/api/last_result');
        return res.json();
    }
    
    async function fetchSequence(limit = 30) {
        const res = await fetch(`/api/sequence?limit=${limit}`);
        return res.json();
    }
    
    function renderStats(stats) {
        const html = `
            <div class="stat-card total"><div class="stat-label">TOTAL DE RODADAS</div><div class="stat-value">${stats.total_rounds}</div></div>
            <div class="stat-card banker"><div class="stat-label">🏦 BANKER</div><div class="stat-value">${stats.banker_wins}</div><div style="font-size:0.8rem">${stats.banker_percent}%</div></div>
            <div class="stat-card player"><div class="stat-label">👤 PLAYER</div><div class="stat-value">${stats.player_wins}</div><div style="font-size:0.8rem">${stats.player_percent}%</div></div>
            <div class="stat-card tie"><div class="stat-label">🤝 TIE</div><div class="stat-value">${stats.tie_wins}</div><div style="font-size:0.8rem">${stats.tie_percent}%</div></div>
        `;
        document.getElementById('stats').innerHTML = html;
    }
    
    function renderLastResult(result) {
        if (!result || !result.round_number) {
            document.getElementById('lastResult').innerHTML = '<div class="loading">Aguardando primeira rodada...</div>';
            return;
        }
        
        const emoji = result.result === 'Banker' ? '🏦' : result.result === 'Player' ? '👤' : '🤝';
        const color = result.result === 'Banker' ? '#4ade80' : result.result === 'Player' ? '#60a5fa' : '#fbbf24';
        
        const html = `
            <div style="font-size:0.9rem; color:#888">ÚLTIMA RODADA</div>
            <div class="last-result-value" style="color:${color}">${emoji} ${result.result}</div>
            <div style="font-size:0.9rem">Rodada: ${result.round_number}</div>
            <div class="last-result-dice">
                <div class="dice-group"><div class="dice-label">👤 PLAYER</div><span>🎲 ${result.player_dice ? result.player_dice.join(' + ') : '-'}</span><span style="color:#60a5fa; margin-left:10px">${result.player_total || 0}</span></div>
                <div class="dice-group"><div class="dice-label">🏦 BANKER</div><span>🎲 ${result.banker_dice ? result.banker_dice.join(' + ') : '-'}</span><span style="color:#4ade80; margin-left:10px">${result.banker_total || 0}</span></div>
            </div>
            <div style="margin-top:15px; font-size:0.75rem; color:#666">${new Date(result.timestamp).toLocaleString('pt-BR')}</div>
        `;
        document.getElementById('lastResult').innerHTML = html;
    }
    
    function renderSignals(signals) {
        if (!signals.length) {
            document.getElementById('signals').innerHTML = '<div class="loading">Nenhum sinal gerado ainda...</div>';
            return;
        }
        
        const html = signals.map(s => `
            <div class="signal-card ${s.signal_type.toLowerCase()}">
                <div class="signal-confidence">🎯 ${s.signal_type} - ${s.confidence}% confiança</div>
                <div class="signal-message">📊 ${s.message}</div>
                <div class="signal-time">${new Date(s.created_at).toLocaleString('pt-BR')}</div>
            </div>
        `).join('');
        document.getElementById('signals').innerHTML = html;
    }
    
    function renderRounds(rounds) {
        if (!rounds.length) {
            document.getElementById('rounds').innerHTML = '<div class="loading">Nenhuma rodada registrada...</div>';
            return;
        }
        
        const html = `
            <table>
                <thead><tr><th>Rodada</th><th>Resultado</th><th>Dados Player</th><th>Dados Banker</th><th>Total</th><th>Data/Hora</th></tr></thead>
                <tbody>
                    ${rounds.map(r => {
                        const badgeClass = r.result === 'Banker' ? 'badge-banker' : r.result === 'Player' ? 'badge-player' : 'badge-tie';
                        const emoji = r.result === 'Banker' ? '🏦' : r.result === 'Player' ? '👤' : '🤝';
                        return `<tr>
                            <td>${r.round_number || '-'}</td>
                            <td><span class="badge ${badgeClass}">${emoji} ${r.result || '-'}</span></td>
                            <td>${r.player_dice ? r.player_dice.join(' + ') : '-'}</td>
                            <td>${r.banker_dice ? r.banker_dice.join(' + ') : '-'}</td>
                            <td>${r.player_total || 0} vs ${r.banker_total || 0}</td>
                            <td>${new Date(r.timestamp).toLocaleString('pt-BR')}</td>
                        </tr>`;
                    }).join('')}
                </tbody>
            </table>
        `;
        document.getElementById('rounds').innerHTML = html;
    }
    
    function renderSequence(sequenceData) {
        const seq = sequenceData.sequence || [];
        const emojis = seq.map(r => r === 'Banker' ? '🏦' : r === 'Player' ? '👤' : '🤝').join(' ');
        document.getElementById('sequence').innerHTML = emojis || 'Aguardando rodadas...';
    }
    
    async function refreshData() {
        try {
            const [stats, rounds, signals, lastResult, sequence] = await Promise.all([
                fetchStats(),
                fetchRounds(30),
                fetchSignals(20),
                fetchLastResult(),
                fetchSequence(30)
            ]);
            renderStats(stats);
            renderLastResult(lastResult);
            renderSignals(signals);
            renderRounds(rounds);
            renderSequence(sequence);
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
        }
    }
    
    refreshData();
    setInterval(refreshData, 5000);
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    """Interface web principal"""
    return HTML_TEMPLATE

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
