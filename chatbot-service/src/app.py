from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
import service
import os

PORT = int(os.getenv("CHATBOT_SERVICE_PORT", 5003))
CHESHIRE_CAT_URL = os.getenv("CHESHIRE_CAT_URL", "http://cheshire-cat-core:80")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

app = FastAPI(title="Chatbot Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    text: str
    emotion: str = None
    environment: str = None

class ChatResponse(BaseModel):
    response: str

@app.get("/api/chat/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        print(f"Sending to Cheshire Cat: {request}")
        response = await service.get_chat_response(request.text, request.emotion, request.environment)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)