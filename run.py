#!/usr/bin/env python3
"""
Executor principal - Roda o capturer e a interface web simultaneamente
"""

import multiprocessing
import os
import sys

def run_capturer():
    """Executa o capturer de dados"""
    from capturer import main as capturer_main
    capturer_main()

def run_web():
    """Executa a interface web"""
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("web_interface:app", host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Inicia os dois processos
    p1 = multiprocessing.Process(target=run_capturer)
    p2 = multiprocessing.Process(target=run_web)
    
    p1.start()
    p2.start()
    
    p1.join()
    p2.join()
