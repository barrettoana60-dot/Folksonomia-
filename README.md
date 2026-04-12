# Sistema Folksonomia Digital Inteligente

Projeto reestruturado com base no código original e no documento sobre adaptação da lógica do Prado.

## Arquivos
- `app.py`: aplicação Streamlit principal
- `semantic_engine.py`: motor semântico, reconciliação, ML e grafo
- `automation_pipeline.py`: CLI de automação
- `requirements.txt`: dependências

## Rodar
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Automação
```bash
python automation_pipeline.py --mode full
```
