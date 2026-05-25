#!/usr/bin/env python3
"""
Executor principal - Roda o capturer e a API simultaneamente
"""

import multiprocessing
import os
import sys
import time
import signal

def run_analyzer():
    """Executa o analisador de Bac Bo"""
    try:
        from bacbo_analyzer import BacBoAnalyzer
        analyzer = BacBoAnalyzer()
        analyzer.start()
    except Exception as e:
        print(f"❌ Erro no analisador: {e}")
        import traceback
        traceback.print_exc()

def run_api():
    """Executa a API web"""
    try:
        import uvicorn
        from api_signals import app
        port = int(os.environ.get("PORT", 8000))
        print(f"🌐 Iniciando API na porta {port}")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        print(f"❌ Erro na API: {e}")
        import traceback
        traceback.print_exc()

def signal_handler(signum, frame):
    """Trata sinais de término"""
    print("\n🛑 Recebido sinal de término. Encerrando processos...")
    for p in processes:
        if p.is_alive():
            p.terminate()
    sys.exit(0)

if __name__ == "__main__":
    print("="*60)
    print("🚀 BAC BO ANALYZER - COMPLETE EDITION")
    print("="*60)
    print(f"📁 Diretório: {os.getcwd()}")
    print(f"🐍 Python: {sys.version}")
    print("="*60)
    
    # Registra handler para sinais
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Inicia os processos
    processes = []
    
    # Processo do analisador
    p1 = multiprocessing.Process(target=run_analyzer, name="analyzer")
    p1.daemon = True
    p1.start()
    processes.append(p1)
    print("✅ Analisador iniciado")
    
    # Processo da API (aguarda um pouco para o banco conectar)
    time.sleep(3)
    p2 = multiprocessing.Process(target=run_api, name="api")
    p2.daemon = True
    p2.start()
    processes.append(p2)
    print("✅ API iniciada")
    
    print("\n🎯 Sistema completo rodando!")
    print("   - Capturando WebSocket da Evolution")
    print("   - Analisando padrões e gerando sinais")
    print("   - Servindo API na porta 8000")
    print("\n📊 Acesse: https://seu-app.railway.app/")
    print("\n⚠️  Pressione Ctrl+C para encerrar\n")
    
    # Aguarda os processos
    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        signal_handler(None, None)
