#!/usr/bin/env python3
"""
Capturador Evolution Gaming para Railway.app
"""

import json
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import requests

# Configurações
CASINO_URL = "https://apostagreenbet.bet/casino/evolutionlive/bac-bo"
OUTPUT_DIR = "/app/data"
RESULTS_FILE = f"{OUTPUT_DIR}/bacbo_results.json"

# Cria diretório de dados
os.makedirs(OUTPUT_DIR, exist_ok=True)

class RailwayEvolutionCapture:
    def __init__(self):
        self.results = []
        self.round_count = 0
        self.driver = None
        
    def setup_driver(self):
        """Configura Chrome para Railway"""
        options = Options()
        
        # Configurações para ambiente headless (sem interface gráfica)
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1280,720')
        options.add_argument('--remote-debugging-port=9222')
        
        # Desativa features que podem causar problemas
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--disable-web-security')
        
        # Usa Chromium do sistema
        options.binary_location = '/usr/bin/chromium'
        
        # Configurações adicionais
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
        
        // Intercepta WebSocket
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
    
    def save_to_api(self, data):
        """Envia dados para um endpoint (opcional)"""
        webhook_url = os.environ.get('WEBHOOK_URL')
        if webhook_url:
            try:
                requests.post(webhook_url, json=data, timeout=5)
            except:
                pass
    
    def start(self):
        """Inicia captura contínua"""
        print(f"🎰 Iniciando captura no Railway...")
        print(f"📁 Dados salvos em: {RESULTS_FILE}")
        
        self.setup_driver()
        
        try:
            # Abre o cassino
            print(f"🌐 Abrindo {CASINO_URL}")
            self.driver.get(CASINO_URL)
            time.sleep(10)
            
            # Injeta script
            self.inject_capture_script()
            print("✅ Script injetado")
            
            # Loop de captura
            last_count = 0
            while True:
                try:
                    # Coleta dados
                    raw_data = self.driver.execute_script("return window.__evoData || []")
                    
                    # Processa novos dados
                    for item in raw_data[last_count:]:
                        self.process_result(item)
                        last_count += 1
                    
                    # Mostra status
                    print(f"\r📊 Rodadas: {self.round_count} | Eventos: {len(self.results)}", end="")
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"\n⚠️ Erro no loop: {e}")
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            print(f"\n\n✅ Captura finalizada!")
            print(f"📊 Total de rodadas: {self.round_count}")
            self.save_results()
            
        except Exception as e:
            print(f"\n❌ Erro fatal: {e}")
            self.save_results()
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def process_result(self, item):
        """Processa resultado do Bac Bo"""
        data = item.get('data', {})
        game = data.get('args', {}).get('game', {})
        
        if not game.get('result'):
            return
            
        # Extrai dados
        dice_values = [d['value'] for d in game.get('dice', [])]
        player_score = sum(dice_values[:2]) if len(dice_values) >= 2 else 0
        banker_score = sum(dice_values[2:]) if len(dice_values) >= 4 else 0
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'rodada': game.get('number'),
            'resultado': game.get('result'),
            'dados': dice_values,
            'player_score': player_score,
            'banker_score': banker_score,
            'raw': data
        }
        
        self.results.append(result)
        self.round_count += 1
        
        # Mostra resultado
        emoji = '🏦' if 'Banker' in result['resultado'] else '👤' if 'Player' in result['resultado'] else '🤝'
        print(f"\n{emoji} Rodada {result['rodada']}: {result['resultado']}")
        print(f"   Player: {dice_values[:2]} ({player_score}) | Banker: {dice_values[2:]} ({banker_score})")
        
        # Envia para webhook se configurado
        self.save_to_api(result)
        
        # Salva resultados
        self.save_results()
    
    def save_results(self):
        """Salva resultados em arquivo"""
        try:
            with open(RESULTS_FILE, 'w') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Erro ao salvar: {e}")

if __name__ == "__main__":
    print("="*60)
    print("🚀 BAC BO CAPTURER - RAILWAY EDITION")
    print("="*60)
    
    capturer = RailwayEvolutionCapture()
    capturer.start()
