# 🎲 Bac Bo Analyzer

Sistema completo de análise de Bac Bo da Evolution Gaming, similar ao rnablack.

## Funcionalidades

- ✅ Captura WebSocket em tempo real
- ✅ Salva resultados no PostgreSQL
- ✅ Analisa padrões e streaks
- ✅ Gera sinais com confiança
- ✅ Interface web completa
- ✅ API REST para integração

## Padrões Analisados

| Padrão | Descrição | Confiança |
|--------|-----------|-----------|
| Streak 4+ | 4+ resultados iguais seguidos | 85% |
| Alternância | Padrão Banker/Player alternado | 75% |
| Viés estatístico | >60% de dominância | 70% |
| Padrão 2+2 | BBPP ou PPBB | 80% |

## Como Usar

### Localmente

```bash
pip install -r requirements.txt
python run.py
