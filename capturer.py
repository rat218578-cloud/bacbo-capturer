#!/usr/bin/env python3
"""
Capturador Evolution Gaming para Railway.app
Com integração PostgreSQL (Neon)
"""

import json
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import requests
import psycopg2
from psycopg2.extras import Json
from urllib.parse import urlparse

# ========== CONFIGURAÇÕES ==========
CASINO_URL = "https://apostagreenbet.bet/casino/evolutionlive/bac-bo"

# Database URL (Neon PostgreSQL)
DATABASE_URL = "postgresql://neondb_owner:npg_9mWRy6lskeCT@ep-billowing-feather-apmnvtae-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# ========== CLASSE PRINCIPAL ==========
class BacBoDatabase:
    def __init__(self, db_url):
        self.db_url = db_url
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """Conecta ao banco de dados"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor()
            print("✅ Conectado ao PostgreSQL (Neon)")
        except Exception as e:
            print(f"❌ Erro ao conectar ao banco: {e}")
            raise
    
    def create_tables(self):
        """Cria tabelas automaticamente se não existirem"""
        
        # Tabela principal de rodadas
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS bacbo_rounds (
                id SERIAL PRIMARY KEY,
                round_number VARCHAR(50),
                result VARCHAR(20),
                player_dice INTEGER[],
                banker_dice INTEGER[],
                player_total INTEGER,
                banker_total INTEGER,
                all_dice INTEGER[],
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_json JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Índices para consultas rápidas
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bacbo_rounds_round_number 
            ON bacbo_rounds(round_number)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bacbo_rounds_timestamp 
            ON bacbo_rounds(timestamp)
        """)
        
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_bacbo_rounds_result 
            ON bacbo_rounds(result)
        """)
        
        # Tabela de estatísticas (opcional)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS bacbo_stats (
                id SERIAL PRIMARY KEY,
                total_rounds INTEGER DEFAULT 0,
                banker_wins INTEGER DEFAULT 0,
                player_wins INTEGER DEFAULT 0,
                tie_wins INTEGER DEFAULT 0,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
        print("✅ Tabelas criadas/verificadas com sucesso!")
    
    def save_round(self, round_data):
        """Salva uma rodada no banco de dados"""
        try:
            self.cursor.execute("""
                INSERT INTO bacbo_rounds (
                    round_number, result, player_dice, banker_dice, 
                    player_total, banker_total, all_dice, timestamp, raw_json
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                round_data.get('round_number'),
                round_data.get('result'),
                round_data.get('player_dice'),
                round_data.get('banker_dice'),
                round_data.get('player_total'),
                round_data.get('banker_total'),
                round_data.get('all_dice'),
                round_data.get('timestamp'),
                Json(round_data.get('raw_json', {}))
            ))
            self.conn.commit()
            
            # Atualiza estatísticas
            self.update_stats(round_data.get('result'))
            
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar rodada: {e}")
            self.conn.rollback()
            return False
    
    def update_stats(self, result):
        """Atualiza tabela de estatísticas"""
        try:
            # Verifica se já existe registro
            self.cursor.execute("SELECT id FROM bacbo_stats LIMIT 1")
            stats_exists = self.cursor.fetchone()
            
            if stats_exists:
                # Atualiza existente
                if result == 'Banker':
                    self.cursor.execute("""
                        UPDATE bacbo_stats 
                        SET total_rounds = total_rounds + 1,
                            banker_wins = banker_wins + 1,
                            last_update = CURRENT_TIMESTAMP
                    """)
                elif result == 'Player':
                    self.cursor.execute("""
                        UPDATE bacbo_stats 
                        SET total_rounds = total_rounds + 1,
                            player_wins = player_wins + 1,
                            last_update = CURRENT_TIMESTAMP
                    """)
                else:  # Tie
                    self.cursor.execute("""
                        UPDATE bacbo_stats 
                        SET total_rounds = total_rounds + 1,
                            tie_wins = tie_wins + 1,
                            last_update = CURRENT_TIMESTAMP
                    """)
            else:
                # Cria primeiro registro
                if result == 'Banker':
                    self.cursor.execute("""
                        INSERT INTO bacbo_stats (total_rounds, banker_wins, player_wins, tie_wins)
                        VALUES (1, 1, 0, 0)
                    """)
                elif result == 'Player':
                    self.cursor.execute("""
                        INSERT INTO bacbo_stats (total_rounds, banker_wins, player_wins, tie_wins)
                        VALUES (1, 0, 1, 0)
                    """)
                else:
                    self.cursor.execute("""
                        INSERT INTO bacbo_stats (total_rounds, banker_wins, player_wins, tie_wins)
                        VALUES (1, 0, 0, 1)
                    """)
            
            self.conn.commit()
        except Exception as e:
            print(f"⚠️ Erro ao atualizar estatísticas: {e}")
    
    def get_stats(self):
        """Retorna estatísticas atuais"""
        self.cursor.execute("""
            SELECT total_rounds, banker_wins, player_wins, tie_wins, last_update
            FROM bacbo_stats LIMIT 1
        """)
        result = self.cursor.fetchone()
        if result:
            return {
                'total_rounds': result[0],
                'banker_wins': result[1],
                'player_wins': result[2],
                'tie_wins': result[3],
                'last_update': result[4].isoformat() if result[4] else None
            }
        return None
    
    def get_last_rounds(self, limit=10):
        """Retorna últimas rodadas"""
        self.cursor.execute("""
            SELECT round_number, result, player_total, banker_total, 
                   player_dice, banker_dice, timestamp
            FROM bacbo_rounds 
            ORDER BY id DESC LIMIT %s
        """, (limit,))
        results = self.cursor.fetchall()
        return [
            {
                'round_number': r[0],
                'result': r[1],
                'player_total': r[2],
                'banker_total': r[3],
                'player_dice': r[4],
                'banker_dice': r[5],
                'timestamp': r[6].isoformat() if r[6] else None
            }
            for r in results
        ]
    
    def close(self):
        """Fecha conexão com o banco"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("🔌 Conexão com banco de dados fechada")


class RailwayEvolutionCapture:
    def __init__(self, db):
        self.results = []
        self.round_count = 0
        self.driver = None
        self.db = db
        
    def setup_driver(self):
        """Configura Chrome para Railway"""
        options = Options()
        
        # Configurações para ambiente headless
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1280,720')
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--disable-web-security')
        
        options.binary_location = '/usr/bin/chromium'
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=options)
            print("✅ Chrome driver iniciado com sucesso!")
        except Exception as e:
            print(f"❌ Erro ao iniciar Chrome: {e}")
            raise
    
    def inject_capture_script(self):
        """Injeta script de captura"""
        script = """
        window.__evoData = [];
        window.__roundCount = 0;
        
        const OriginalWS = window.WebSocket;
        window.WebSocket = function(url, protocols) {
            const ws = new OriginalWS(url, protocols);
            
            if (url.includes('evolution') || url.includes('evo')) {
                ws.addEventListener('message', function(e) {
                    try {
                        const data = JSON.parse(e.data);
                        if (data.type === 'bacbo.playerState' && data.args?.game?.result) {
                            window.__evoData.push({
                                timestamp: Date.now(),
                                data: data
                            });
                            window.__roundCount++;
                        }
                    } catch(e) {}
                });
            }
            return ws;
        };
        """
        self.driver.execute_script(script)
    
    def start(self):
        """Inicia captura contínua"""
        print(f"🎰 Iniciando captura no Railway...")
        print(f"📊 Banco de dados: PostgreSQL (Neon)")
        
        self.setup_driver()
        
        try:
            print(f"🌐 Abrindo {CASINO_URL}")
            self.driver.get(CASINO_URL)
            time.sleep(10)
            
            self.inject_capture_script()
            print("✅ Script injetado")
            
            # Mostra estatísticas iniciais
            stats = self.db.get_stats()
            if stats:
                print(f"\n📊 ESTATÍSTICAS ATUAIS:")
                print(f"   Total de rodadas: {stats['total_rounds']}")
                print(f"   Banker: {stats['banker_wins']} | Player: {stats['player_wins']} | Tie: {stats['tie_wins']}")
            
            last_count = 0
            print("\n🎧 Aguardando resultados do Bac Bo...\n")
            
            while True:
                try:
                    raw_data = self.driver.execute_script("return window.__evoData || []")
                    
                    for item in raw_data[last_count:]:
                        self.process_result(item)
                        last_count += 1
                    
                    # Mostra status
                    print(f"\r📊 Rodadas capturadas: {self.round_count} | Banco: OK", end="")
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"\n⚠️ Erro no loop: {e}")
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            print(f"\n\n✅ Captura finalizada!")
            print(f"📊 Total de rodadas capturadas: {self.round_count}")
            self.show_final_stats()
            
        except Exception as e:
            print(f"\n❌ Erro fatal: {e}")
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def process_result(self, item):
        """Processa e salva resultado no banco"""
        data = item.get('data', {})
        game = data.get('args', {}).get('game', {})
        
        if not game.get('result'):
            return
            
        # Extrai dados dos dados
        dice_values = [d['value'] for d in game.get('dice', [])]
        player_dice = dice_values[:2] if len(dice_values) >= 2 else []
        banker_dice = dice_values[2:4] if len(dice_values) >= 4 else []
        player_total = sum(player_dice) if player_dice else 0
        banker_total = sum(banker_dice) if banker_dice else 0
        
        round_data = {
            'round_number': game.get('number'),
            'result': game.get('result'),
            'player_dice': player_dice,
            'banker_dice': banker_dice,
            'player_total': player_total,
            'banker_total': banker_total,
            'all_dice': dice_values,
            'timestamp': datetime.now(),
            'raw_json': data
        }
        
        # Salva no banco
        if self.db.save_round(round_data):
            self.round_count += 1
            
            # Mostra resultado
            emoji = '🏦' if game.get('result') == 'Banker' else '👤' if game.get('result') == 'Player' else '🤝'
            print(f"\n{emoji} Rodada {round_data['round_number']}: {round_data['result']}")
            print(f"   Player: {player_dice} ({player_total}) | Banker: {banker_dice} ({banker_total})")
    
    def show_final_stats(self):
        """Mostra estatísticas finais"""
        stats = self.db.get_stats()
        if stats:
            print("\n" + "="*50)
            print("📊 ESTATÍSTICAS FINAIS")
            print("="*50)
            print(f"Total de rodadas: {stats['total_rounds']}")
            print(f"Banker: {stats['banker_wins']} ({stats['banker_wins']/stats['total_rounds']*100:.1f}%)")
            print(f"Player: {stats['player_wins']} ({stats['player_wins']/stats['total_rounds']*100:.1f}%)")
            print(f"Tie: {stats['tie_wins']} ({stats['tie_wins']/stats['total_rounds']*100:.1f}%)")
            
            # Últimas 5 rodadas
            print("\n🔄 ÚLTIMAS 5 RODADAS:")
            last_rounds = self.db.get_last_rounds(5)
            for r in last_rounds:
                print(f"   {r['round_number']}: {r['result']} (P:{r['player_total']} x B:{r['banker_total']})")

# ========== MAIN ==========
if __name__ == "__main__":
    print("="*60)
    print("🚀 BAC BO CAPTURER - POSTGRESQL EDITION")
    print("="*60)
    
    # Conecta ao banco
    db = BacBoDatabase(DATABASE_URL)
    
    # Inicia captura
    capturer = RailwayEvolutionCapture(db)
    
    try:
        capturer.start()
    except KeyboardInterrupt:
        print("\n👋 Encerrando...")
    finally:
        db.close()
