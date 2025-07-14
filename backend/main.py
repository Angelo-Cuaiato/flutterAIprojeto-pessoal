import os
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Conexão com o MongoDB
mongodb_url = os.getenv("MONGODB_URL")
mongo_client = AsyncIOMotorClient(mongodb_url)
db = mongo_client["chat_bot"]

app = FastAPI()

# Configuração do CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos de dados
class Message(BaseModel):
    role: str  # "user" ou "assistant"
    content: str

class ChatRequest(BaseModel):
    user_id: str
    messages: list[Message]

class ChatResponse(BaseModel):
    response: str

@app.get("/")
def read_root():
    return {"Status": "API do Bot Chat está online"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Chave da API da OpenAI não foi configurada")

    openai_client = OpenAI(api_key=api_key)

    user_id = request.user_id
    nome_usuario = None
    gostos_usuario = None

    # 1. Buscar nome e gostos do usuário na coleção usuarios
    usuario = await db.usuarios.find_one({"user_id": user_id})
    if usuario:
        nome_usuario = usuario.get("nome")
        gostos_usuario = usuario.get("gostos")

    # 2. Se não encontrar, buscar na última conversa salva
    if not nome_usuario or not gostos_usuario:
        ultima_conversa = await db.conversas.find_one(
            {"user_id": user_id},
            sort=[("_id", -1)]
        )
        if ultima_conversa:
            for msg in ultima_conversa.get("messages", []):
                if msg.get("role") == "system":
                    content = msg.get("content", "")
                    if not nome_usuario and "O nome do usuário é" in content:
                        nome_usuario = content.split("O nome do usuário é")[-1].split(".")[0].strip()
                    if not gostos_usuario and "O usuário gosta de" in content:
                        gostos_usuario = content.split("O usuário gosta de")[-1].split(".")[0].strip()

    # 3. Se o usuário informar nome ou gostos nesta conversa, salve/atualize no banco
    for msg in request.messages:
        if msg.role == "user":
            if "meu nome é" in msg.content.lower():
                nome_usuario = msg.content.lower().split("meu nome é")[-1].strip().split()[0]
                await db.usuarios.update_one(
                    {"user_id": user_id},
                    {"$set": {"nome": nome_usuario}},
                    upsert=True
                )
            if "eu gosto de" in msg.content.lower():
                gostos_usuario = msg.content.lower().split("eu gosto de")[-1].strip()
                await db.usuarios.update_one(
                    {"user_id": user_id},
                    {"$set": {"gostos": gostos_usuario}},
                    upsert=True
                )

    # --- RESPOSTA PERSONALIZADA DE BOAS-VINDAS ---
    # Se a última mensagem do usuário for um cumprimento e já tiver nome salvo, responda "Olá, NOME!"
    cumprimentos = ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"]
    ultima_msg = request.messages[-1].content.lower().strip()
    if nome_usuario and any(c in ultima_msg for c in cumprimentos):
        bot_response = f"Olá, {nome_usuario}! Como posso ajudar você hoje?"
        conversa_json = {
            "user_id": user_id,
            "messages": [msg.model_dump() for msg in request.messages],
            "bot_response": bot_response
        }
        await db.conversas.insert_one(conversa_json)
        return ChatResponse(response=bot_response)

    # 4. Monta o system_prompt incluindo nome/gostos se existirem
    info_extra = ""
    if nome_usuario:
        info_extra += f"O nome do usuário é {nome_usuario}. "
    if gostos_usuario:
        info_extra += f"O usuário gosta de {gostos_usuario}. "

    system_prompt = {
        "role": "system",
        "content": (
            info_extra +
            "Você é um assistente de IA especialista. Responda de forma clara, objetiva e educada às perguntas do usuário."
        )
    }
    history_for_api = [message.model_dump() for message in request.messages]
    openai_messages = [system_prompt] + history_for_api

    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=openai_messages,
        max_tokens=500,
        temperature=0.7
    )
    bot_response = response.choices[0].message.content
    if not bot_response:
        bot_response = "Desculpe, não consegui gerar uma resposta no momento."

    conversa_json = {
        "user_id": user_id,
        "messages": openai_messages,
        "bot_response": bot_response
    }
    await db.conversas.insert_one(conversa_json)

    return ChatResponse(response=bot_response)

@app.get("/api/conversa/{conversa_id}")
async def get_conversa(conversa_id: str):
    conversa = await db.conversas.find_one({"_id": ObjectId(conversa_id)})
    if not conversa:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    conversa["_id"] = str(conversa["_id"])
    return conversa

# Para executar o servidor:
# 1. Navegue até a pasta do projeto no terminal.
# 2. Instale as dependências: pip install -r requirements.txt
# 3. Execute o servidor: uvicorn main:app --reload --port 5000
# Para acessar a API, use o endereço: http://localhost:5000/api/chat