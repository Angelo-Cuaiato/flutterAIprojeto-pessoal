# Bot Chat - Sistema de Chatbot

Sistema completo de chatbot com Flutter (frontend) e **Python FastAPI** (backend) integrado à API do OpenAI.

## Configuração

### 1. Backend (Python/FastAPI)
1. Navegue até a pasta `backend`
2. Edite o arquivo `.env` e adicione sua chave da API do OpenAI:
   ```
   OPENAI_API_KEY=sk-sua-chave-aqui
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute o backend:
   ```bash
   uvicorn main:app --reload
   ```

### 2. Frontend (Flutter)
1. Navegue até a pasta `bot_chat_flutter`
2. Execute os comandos:
   ```bash
   flutter pub get
   flutter run
   ```

## Estrutura do Projeto

- `bot_chat_flutter/` - Aplicação Flutter
- `backend/` - API Python com FastAPI
- `.env` - Arquivo com variáveis de ambiente (chave da API)

## Funcionalidades

- Interface de chat intuitiva
- Integração com OpenAI GPT-3.5-turbo
- Comunicação segura entre frontend e backend
- Configuração de ambiente para chaves da API
