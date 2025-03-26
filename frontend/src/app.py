#TODO: Implementare
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import httpx
import os
import uvicorn
from pydantic import BaseModel

# Configurazione
PORT = int(os.getenv("FRONTEND_PORT", 3000))
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8080")

app = FastAPI(title="Frontend Service")

# Configura i templates
templates = Jinja2Templates(directory="src/templates")

# Configura i file statici
app.mount("/static", StaticFiles(directory="src/static"), name="static")


class ChatRequest(BaseModel):
    text: str
    emotion: str = None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/send_message")
async def send_message(message: str = Form(...)):
    try:
        async with httpx.AsyncClient() as client:
            # Prima richiesta per rilevare l'emozione
            emotion_response = await client.post(
                f"{API_GATEWAY_URL}/api/emotion/predict",
                json={"text": message}
            )
            emotion_data = emotion_response.json()
            emotion = emotion_data.get("emotion", "neutral")

            # Seconda richiesta per ottenere la risposta del chatbot
            chat_response = await client.post(
                f"{API_GATEWAY_URL}/api/chat",
                json={"text": message, "emotion": emotion}
            )

            response_data = chat_response.json()

            # Opzionale: richiesta per convertire la risposta in voce
            tts_response = await client.post(
                f"{API_GATEWAY_URL}/api/tts/synthesize",
                json={"text": response_data["response"], "emotion": emotion}
            )

            audio_url = None
            if tts_response.status_code == 200:
                audio_url = f"{API_GATEWAY_URL}/api/tts/audio/{tts_response.json().get('audio_id', '')}"

            return {
                "response": response_data["response"],
                "emotion": emotion,
                "audio_url": audio_url
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transcribe_audio")
async def transcribe_audio(audio_data: bytes = Form(...)):
    try:
        async with httpx.AsyncClient() as client:
            # Invia l'audio al servizio STT
            files = {"audio_file": ("audio.wav", audio_data)}
            stt_response = await client.post(f"{API_GATEWAY_URL}/api/stt/transcribe", files=files)

            return stt_response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print(f"Starting frontend service on port: {PORT}")
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)