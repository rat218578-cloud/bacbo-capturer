#!/usr/bin/env python3
"""
BAC BO ANALYZER - Captura, Analisa e Gera Sinais
Versão COMPLETA - Funciona igual ao rnablack
"""

import json
import os
import time
import signal
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import psycopg2
from psycopg2.extras import Json, RealDictCursor

# ============================================================
# CONFIGURAÇÕES
# ============================================================
CASINO_URL = "https://apostagreenbet.bet/casino/evolutionlive/bac-bo"
DATABASE_URL = "postgresql://neondb_owner:npg_9mWRy6lskeCT@ep-billowing-feather-apmnvtae-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require"
CHROME_PROFILE_DIR = "./chrome_profile"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"

# ============================================================
# CLASSE PRINCIPAL
# ============================================================
class BacBoAnalyzer:
    def __init__(self):
        self.rounds = []
        self.signals = []
        self.db = None
        self.driver = None
        self.is_running = True
        self.round_count = 0
        self.signal_count = 0
        
        # Configura handlers de sinal
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handler para encerramento gracioso"""
        print("\n🛑 Recebido sinal de encerramento. Finalizando...")
        self.is_running = False
        
    def connect_db(self):
        """Conecta ao PostgreSQL com retry"""
        max_retries = 5
        for i in range(max_retries):
            try:
                self.db = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
                self.create_tables()
                print("✅ Conectado ao PostgreSQL")
                return True
            except Exception as e:
                print(f"⚠️ Tentativa {i+1}/{max_retries} falhou: {e}")
                time.sleep(3)
        
        print("❌ Não foi possível conectar ao banco de dados")
        return False
    
    def create_tables(self):
        """Cria todas as tabelas necessárias"""
        cur = self.db.cursor()
        
        # Tabela de rodadas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bacbo_rounds (
                id SERIAL PRIMARY KEY,
                round_number VARCHAR(50),
                result VARCHAR(20),
                player_dice INTEGER[],
                banker_dice INTEGER[],
                player_total INTEGER,
                banker_total INTEGER,
                sequence VARCHAR(500),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_json JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Índices para performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rounds_round_number ON bacbo_rounds(round_number)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rounds_timestamp ON bacbo_rounds(timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rounds_result ON bacbo_rounds(result)")
        
        # Tabela de sinais
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bacbo_signals (
                id SERIAL PRIMARY KEY,
                signal_type VARCHAR(20),
                confidence DECIMAL(5,2),
                message TEXT,
                pattern VARCHAR(200),
                streak INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Índices para sinais
        cur.execute("CREATE INDEX IF NOT EXISTS idx_signals_created_at ON bacbo_signals(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_signals_type ON bacbo_signals(signal_type)")
        
        # Tabela de estatísticas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bacbo_statistics (
                id SERIAL PRIMARY KEY,
                total_rounds INTEGER DEFAULT 0,
                banker_wins INTEGER DEFAULT 0,
                player_wins INTEGER DEFAULT 0,
                tie_wins INTEGER DEFAULT 0,
                banker_percent DECIMAL(5,2),
                player_percent DECIMAL(5,2),
                tie_percent DECIMAL(5,2),
                current_streak VARCHAR(20),
                streak_count INTEGER,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela de configuração
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bacbo_config (
                key VARCHAR(50) PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.db.commit()
        cur.close()
        print("✅ Tabelas criadas/verificadas")
    
    def setup_driver(self):
        """Configura o Chrome driver com opções otimizadas"""
        options = Options()
        
        # Configurações essenciais para ambiente headless
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument(f'--user-agent={USER_AGENT}')
        
        # Perfil persistente para manter login
        options.add_argument(f'--user-data-dir={os.path.abspath(CHROME_PROFILE_DIR)}')
        
        # Desativa detecção de automação
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Prefere Chromium do sistema (Docker) ou Chrome local
        if os.path.exists('/usr/bin/chromium'):
            options.binary_location = '/usr/bin/chromium'
        
        try:
            self.driver = webdriver.Chrome(options=options)
            print("✅ Chrome driver iniciado com sucesso")
            return True
        except Exception as e:
            print(f"❌ Erro ao iniciar Chrome driver: {e}")
            return False
    
    def login_and_navigate(self):
        """Navega até o jogo e aguarda login manual"""
        print(f"🌐 Abrindo {CASINO_URL}")
        self.driver.get(CASINO_URL)
        
        # Aguarda um pouco para a página carregar
        time.sleep(5)
        
        print("\n" + "="*60)
        print("⚠️  AÇÃO NECESSÁRIA: FAÇA LOGIN NO CASSINO")
        print("="*60)
        print("O navegador foi aberto. Por favor:")
        print("1. Faça login na sua conta do Aposta Green Bet")
        print("2. Navegue até o jogo Bac Bo se necessário")
        print("3. Aguarde o jogo carregar completamente")
        print("\n⏳ Pressione ENTER quando o jogo estiver visível...")
        input()
        
        # Tenta encontrar o iframe do jogo
        print("🔍 Procurando iframe do jogo...")
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    src = iframe.get_attribute('src')
                    if src and ('evolution' in src or '0d9472f6' in src):
                        self.driver.switch_to.frame(iframe)
                        print(f"✅ Switch para iframe: {src[:100]}")
                        return True
            except Exception as e:
                print(f"⚠️ Tentativa {attempt+1}: {e}")
            time.sleep(2)
        
        print("⚠️ Não foi possível encontrar o iframe do jogo")
        return False
    
    def inject_capture_script(self):
        """Injeta o script de captura e análise no navegador"""
        script = """
        // ============================================================
        // BAC BO ANALYZER - Script de Captura e Análise
        // ============================================================
        
        window.__rounds = [];
        window.__signals = [];
        window.__lastAnalysis = null;
        
        // Função para analisar sequência e gerar sinal
        function analyzePattern(history) {
            if (history.length === 0) return null;
            
            const last5 = history.slice(-5);
            const last10 = history.slice(-10);
            
            // Conta ocorrências
            const bankerCount = history.filter(r => r === 'Banker').length;
            const playerCount = history.filter(r => r === 'Player').length;
            const tieCount = history.filter(r => r === 'Tie').length;
            const total = history.length;
            
            const bankerPercent = total > 0 ? (bankerCount / total * 100).toFixed(1) : 0;
            const playerPercent = total > 0 ? (playerCount / total * 100).toFixed(1) : 0;
            
            // Verifica streaks atuais
            let currentStreak = 0;
            let streakType = null;
            for (let i = history.length - 1; i >= 0; i--) {
                if (!streakType) streakType = history[i];
                if (history[i] === streakType) currentStreak++;
                else break;
            }
            
            // Gera sinais baseado em padrões
            let signal = null;
            let confidence = 0;
            let message = "";
            let pattern = "";
            
            // Padrão 1: Streak longo (4+)
            if (currentStreak >= 4) {
                if (streakType === 'Banker') {
                    signal = 'Player';
                    confidence = 85;
                    message = `🔥 STREAK DETECTADA: ${currentStreak} Bankers seguidos! Próximo provável Player.`;
                    pattern = `streak_${currentStreak}_banker`;
                } else if (streakType === 'Player') {
                    signal = 'Banker';
                    confidence = 85;
                    message = `🔥 STREAK DETECTADA: ${currentStreak} Players seguidos! Próximo provável Banker.`;
                    pattern = `streak_${currentStreak}_player`;
                }
            }
            // Padrão 2: Alternância (Zigue-Zague)
            else if (last5.join('') === 'BankerPlayerBankerPlayerBanker') {
                signal = 'Player';
                confidence = 75;
                message = `🔄 PADRÃO ALTERNADO detectado! Sequência: ${last5.join(' → ')}. Próximo: Player.`;
                pattern = 'alternating_5';
            }
            else if (last5.join('') === 'PlayerBankerPlayerBankerPlayer') {
                signal = 'Banker';
                confidence = 75;
                message = `🔄 PADRÃO ALTERNADO detectado! Sequência: ${last5.join(' → ')}. Próximo: Banker.`;
                pattern = 'alternating_5';
            }
            // Padrão 3: Viés estatístico (>60%)
            else if (bankerPercent > 60 && total >= 10) {
                signal = 'Player';
                confidence = 70;
                message = `📊 VIÉS ESTATÍSTICO: Banker ${bankerPercent}% nas últimas ${total} rodadas. Próximo: Player.`;
                pattern = `bias_banker_${Math.round(bankerPercent)}`;
            }
            else if (playerPercent > 60 && total >= 10) {
                signal = 'Banker';
                confidence = 70;
                message = `📊 VIÉS ESTATÍSTICO: Player ${playerPercent}% nas últimas ${total} rodadas. Próximo: Banker.`;
                pattern = `bias_player_${Math.round(playerPercent)}`;
            }
            // Padrão 4: Padrão 2+2
            else if (last5.length >= 4) {
                const firstTwo = last5.slice(0,2);
                const nextTwo = last5.slice(2,4);
                if (firstTwo[0] === firstTwo[1] && nextTwo[0] === nextTwo[1] && firstTwo[0] !== nextTwo[0]) {
                    if (firstTwo[0] === 'Banker') {
                        signal = 'Banker';
                        confidence = 80;
                        message = `🎯 PADRÃO 2+2 detectado! Banker, Banker, Player, Player. Próximo: Banker.`;
                        pattern = '2plus2_banker';
                    } else {
                        signal = 'Player';
                        confidence = 80;
                        message = `🎯 PADRÃO 2+2 detectado! Player, Player, Banker, Banker. Próximo: Player.`;
                        pattern = '2plus2_player';
                    }
                }
            }
            
            if (signal) {
                const signalData = {
                    timestamp: Date.now(),
                    type: signal,
                    confidence: confidence,
                    message: message,
                    pattern: pattern,
                    streak: currentStreak,
                    banker_percent: bankerPercent,
                    player_percent: playerPercent,
                    total_rounds: total
                };
                window.__signals.push(signalData);
                console.log('%c📢 SINAL GERADO: ' + signal + ' (' + confidence + '% confiança)', 'color: #00ff00; font-size: 14px');
                console.log('   ' + message);
                return signalData;
            }
            
            return {
                status: "Analyzing",
                banker_percent: bankerPercent,
                player_percent: playerPercent,
                streak: currentStreak,
                streak_type: streakType,
                last_5: last5,
                last_10: last10
            };
        }
        
        // Intercepta WebSocket
        const OriginalWS = window.WebSocket;
        window.WebSocket = function(url, protocols) {
            const ws = new OriginalWS(url, protocols);
            
            if (url && (url.includes('evolution') || url.includes('evo') || url.includes('0d9472f6'))) {
                console.log('🔌 WebSocket conectado:', url.substring(0, 80));
                
                ws.addEventListener('message', function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        
                        // Captura resultado do Bac Bo
                        if (data.type === 'bacbo.playerState' && data.args && data.args.game && data.args.game.result) {
                            const game = data.args.game;
                            const result = game.result === 'Banker' ? 'Banker' : 
                                          game.result === 'Player' ? 'Player' : 'Tie';
                            
                            const diceValues = game.dice.map(d => d.value);
                            const playerScore = diceValues.slice(0,2).reduce((a,b)=>a+b,0);
                            const bankerScore = diceValues.slice(2,4).reduce((a,b)=>a+b,0);
                            
                            const roundData = {
                                timestamp: Date.now(),
                                round_number: game.number,
                                result: result,
                                player_dice: diceValues.slice(0,2),
                                banker_dice: diceValues.slice(2,4),
                                player_total: playerScore,
                                banker_total: bankerScore,
                                raw: data
                            };
                            
                            window.__rounds.push(roundData);
                            console.log(`🎲 Rodada ${game.number}: ${result} | P:${playerScore} (${diceValues.slice(0,2).join('+')}) B:${bankerScore} (${diceValues.slice(2,4).join('+')})`);
                            
                            // Gera análise e sinal
                            const history = window.__rounds.map(r => r.result);
                            const analysis = analyzePattern(history);
                            window.__lastAnalysis = analysis;
                            
                            // Dispara eventos para o Python
                            window.dispatchEvent(new CustomEvent('newRound', { detail: roundData }));
                            if (analysis && analysis.type) {
                                window.dispatchEvent(new CustomEvent('newSignal', { detail: analysis }));
                            }
                        }
                    } catch(e) {
                        console.warn('Erro ao processar mensagem WebSocket:', e);
                    }
                });
            }
            return ws;
        };
        
        console.log('%c✅ BAC BO ANALYZER INJECTED', 'color: #00ff00; font-size: 16px');
        console.log('🎰 Monitorando Bac Bo em tempo real...');
        """
        
        try:
            self.driver.execute_script(script)
            print("✅ Script de análise injetado")
            return True
        except Exception as e:
            print(f"❌ Erro ao injetar script: {e}")
            return False
    
    def monitor_events(self):
        """Monitora eventos JavaScript e salva no banco"""
        last_round_count = 0
        last_signal_count = 0
        last_stats_update = 0
        
        print("\n🎧 Monitorando eventos em tempo real...")
        print("-" * 60)
        
        while self.is_running:
            try:
                # Verifica se o driver ainda está vivo
                try:
                    self.driver.current_url
                except Exception:
                    print("⚠️ Driver perdido, tentando reconectar...")
                    break
                
                # Coleta novas rodadas
                rounds = self.driver.execute_script("return window.__rounds || []")
                new_rounds = rounds[last_round_count:]
                
                for round_data in new_rounds:
                    self.save_round(round_data)
                    self.round_count += 1
                    
                    # Exibe resultado formatado
                    emoji = '🏦' if round_data['result'] == 'Banker' else '👤' if round_data['result'] == 'Player' else '🤝'
                    print(f"\n{emoji} [{datetime.now().strftime('%H:%M:%S')}] Rodada {round_data['round_number']}: {round_data['result']}")
                    print(f"   Player: {round_data['player_dice']} = {round_data['player_total']}")
                    print(f"   Banker: {round_data['banker_dice']} = {round_data['banker_total']}")
                
                last_round_count = len(rounds)
                
                # Coleta novos sinais
                signals = self.driver.execute_script("return window.__signals || []")
                new_signals = signals[last_signal_count:]
                
                for signal in new_signals:
                    self.save_signal(signal)
                    self.signal_count += 1
                    
                    # Exibe sinal formatado
                    emoji = '🔴' if signal['type'] == 'Banker' else '🔵' if signal['type'] == 'Player' else '⚪'
                    print(f"\n{'='*50}")
                    print(f"📢 [{datetime.now().strftime('%H:%M:%S')}] SINAL: {emoji} {signal['type']}")
                    print(f"   Confiança: {signal['confidence']}%")
                    print(f"   {signal['message']}")
                    print(f"{'='*50}")
                
                last_signal_count = len(signals)
                
                # Atualiza estatísticas a cada 30 segundos
                if time.time() - last_stats_update > 30:
                    self.update_statistics()
                    last_stats_update = time.time()
                
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ Erro no monitoramento: {e}")
                time.sleep(5)
    
    def save_round(self, round_data):
        """Salva rodada no banco de dados"""
        try:
            cur = self.db.cursor()
            
            # Pega sequência atual para histórico
            cur.execute("SELECT result FROM bacbo_rounds ORDER BY id DESC LIMIT 20")
            history = [r['result'] for r in cur.fetchall()]
            history.reverse()
            history.append(round_data['result'])
            
            cur.execute("""
                INSERT INTO bacbo_rounds 
                (round_number, result, player_dice, banker_dice, player_total, banker_total, sequence, raw_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                round_data['round_number'],
                round_data['result'],
                round_data['player_dice'],
                round_data['banker_dice'],
                round_data['player_total'],
                round_data['banker_total'],
                ','.join(history[-30:]),
                Json(round_data.get('raw', {}))
            ))
            
            self.db.commit()
            cur.close()
            
        except Exception as e:
            print(f"❌ Erro ao salvar rodada: {e}")
            self.db.rollback()
    
    def save_signal(self, signal):
        """Salva sinal gerado no banco"""
        try:
            cur = self.db.cursor()
            cur.execute("""
                INSERT INTO bacbo_signals (signal_type, confidence, message, pattern, streak)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                signal['type'],
                signal['confidence'],
                signal['message'],
                signal.get('pattern', ''),
                signal.get('streak', 0)
            ))
            self.db.commit()
            cur.close()
            
        except Exception as e:
            print(f"❌ Erro ao salvar sinal: {e}")
            self.db.rollback()
    
    def update_statistics(self):
        """Atualiza tabela de estatísticas"""
        try:
            cur = self.db.cursor()
            
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN result = 'Banker' THEN 1 ELSE 0 END) as banker,
                    SUM(CASE WHEN result = 'Player' THEN 1 ELSE 0 END) as player,
                    SUM(CASE WHEN result = 'Tie' THEN 1 ELSE 0 END) as tie
                FROM bacbo_rounds
            """)
            stats = cur.fetchone()
            
            if stats and stats['total'] and stats['total'] > 0:
                total = stats['total']
                banker = stats['banker'] or 0
                player = stats['player'] or 0
                tie = stats['tie'] or 0
                
                # Pega streak atual
                cur.execute("SELECT result FROM bacbo_rounds ORDER BY id DESC LIMIT 10")
                last_results = [r['result'] for r in cur.fetchall()]
                
                streak_count = 0
                streak_type = None
                for r in last_results:
                    if not streak_type:
                        streak_type = r
                        streak_count = 1
                    elif r == streak_type:
                        streak_count += 1
                    else:
                        break
                
                cur.execute("""
                    INSERT INTO bacbo_statistics 
                    (total_rounds, banker_wins, player_wins, tie_wins, 
                     banker_percent, player_percent, tie_percent,
                     current_streak, streak_count, last_update)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE SET
                        total_rounds = EXCLUDED.total_rounds,
                        banker_wins = EXCLUDED.banker_wins,
                        player_wins = EXCLUDED.player_wins,
                        tie_wins = EXCLUDED.tie_wins,
                        banker_percent = EXCLUDED.banker_percent,
                        player_percent = EXCLUDED.player_percent,
                        tie_percent = EXCLUDED.tie_percent,
                        current_streak = EXCLUDED.current_streak,
                        streak_count = EXCLUDED.streak_count,
                        last_update = CURRENT_TIMESTAMP
                """, (
                    total, banker, player, tie,
                    round(banker/total*100, 2),
                    round(player/total*100, 2),
                    round(tie/total*100, 2),
                    streak_type, streak_count
                ))
                
                self.db.commit()
            
            cur.close()
            
        except Exception as e:
            print(f"⚠️ Erro ao atualizar estatísticas: {e}")
    
    def start(self):
        """Inicia o processo completo"""
        print("="*60)
        print("🎰 BAC BO ANALYZER - COMPLETE EDITION")
        print("="*60)
        print("📊 Funcionalidades:")
        print("   ✅ Captura WebSocket em tempo real")
        print("   ✅ Salva no PostgreSQL")
        print("   ✅ Analisa padrões e streaks")
        print("   ✅ Gera sinais com confiança")
        print("   ✅ Interface web para visualização")
        print("="*60)
        
        # Conecta ao banco
        if not self.connect_db():
            print("❌ Não foi possível conectar ao banco. Encerrando.")
            return
        
        # Inicia driver
        if not self.setup_driver():
            print("❌ Não foi possível iniciar o Chrome driver. Encerrando.")
            return
        
        try:
            # Navega e aguarda login
            if not self.login_and_navigate():
                print("❌ Não foi possível acessar o jogo. Encerrando.")
                return
            
            # Injeta script
            if not self.inject_capture_script():
                print("❌ Não foi possível injetar o script. Encerrando.")
                return
            
            # Monitora eventos
            self.monitor_events()
            
        except KeyboardInterrupt:
            print("\n\n✅ Captura finalizada pelo usuário!")
        except Exception as e:
            print(f"\n❌ Erro fatal: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.print_final_stats()
            if self.driver:
                self.driver.quit()
            if self.db:
                self.db.close()
    
    def print_final_stats(self):
        """Exibe estatísticas finais"""
        print("\n" + "="*60)
        print("📊 ESTATÍSTICAS FINAIS")
        print("="*60)
        print(f"Rodadas capturadas: {self.round_count}")
        print(f"Sinais gerados: {self.signal_count}")
        
        try:
            stats = self.db.cursor()
            stats.execute("SELECT * FROM bacbo_statistics ORDER BY id DESC LIMIT 1")
            data = stats.fetchone()
            if data:
                print(f"\nTotal no banco: {data['total_rounds']}")
                print(f"Banker: {data['banker_wins']} ({data['banker_percent']}%)")
                print(f"Player: {data['player_wins']} ({data['player_percent']}%)")
                print(f"Tie: {data['tie_wins']} ({data['tie_percent']}%)")
                if data['current_streak']:
                    print(f"Streak atual: {data['current_streak']} x{data['streak_count']}")
            stats.close()
        except:
            pass
        print("="*60)

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    analyzer = BacBoAnalyzer()
    analyzer.start()
