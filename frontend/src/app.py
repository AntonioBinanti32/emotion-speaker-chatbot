#TODO: Implementare
from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import httpx
import os
import uvicorn
from pydantic import BaseModel
from datetime import datetime
import logging

# Configurazione
PORT = int(os.getenv("FRONTEND_PORT", 3000))
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:80")

app = FastAPI(title="Frontend Service")

# Configura i templates
templates = Jinja2Templates(directory="src/templates")

# Configura i file statici
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    text: str
    emotion: str = None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "now": datetime.now()
    })


@app.post("/send_message")
async def send_message(message: str = Form(...)):
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            # Prima richiesta per rilevare l'emozione
            logger.info(f"Inviando richiesta a {API_GATEWAY_URL}/api/emotion/predict/text per rilevare l'emozione del testo: {message} ")
            emotion_response = await client.post(
                f"{API_GATEWAY_URL}/api/emotion/predict/text",
                json={"text": message}
            )

            logger.info(f"Risposta ricevuta da emotion-predictor: {emotion_response.json()}")

            emotion_data = emotion_response.json()
            emotion = emotion_data.get("emotion", "neutral")

            # Seconda richiesta per ottenere la risposta del chatbot
            logger.info(f"Inviando richiesta a {API_GATEWAY_URL}/api/chat: Messaggio: {message},\nEmozione: {emotion}")
            chat_response = await client.post(
                f"{API_GATEWAY_URL}/api/chat",
                json={"text": message, "emotion": emotion}
            )

            logger.info(f"Risposta ricevuta da chatbot-service: {chat_response.json()}")

            response_data = chat_response.json()

            return {
                "response": response_data["response"],
                "emotion": emotion
            }

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


@app.post("/transcribe_and_analyze_audio")
async def transcribe_and_analyze_audio(audio_data: UploadFile = File(...)):
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            # Leggi il contenuto del file
            content = await audio_data.read()

            # Invia l'audio al servizio STT per trascrizione
            logger.info(f"Inviando richiesta a {API_GATEWAY_URL}/api/stt/transcribe per la trascrizione dell'audio")

            files_stt = {"audio_file": ("audio.wav", content, "audio/wav")}
            stt_response = await client.post(
                f"{API_GATEWAY_URL}/api/stt/transcribe",
                files=files_stt
            )

            logger.info(f"Risposta ricevuta da stt-service: {stt_response.json()}")

            # Invia l'audio al servizio emotion-predictor per l'analisi
            logger.info(f"Inviando richiesta a {API_GATEWAY_URL}/api/emotion/predict per rilevare l'emozione dell'audio")

            files_emotion = {"file": ("audio.wav", content, "audio/wav")}
            emotion_response = await client.post(
                f"{API_GATEWAY_URL}/api/emotion/predict",
                files=files_emotion
            )

            logger.info(f"Risposta ricevuta da emotion-predictor: {emotion_response.json()}")

            stt_data = stt_response.json()
            emotion_data = emotion_response.json()

            emotion = emotion_data.get("emotion", "neutral")
            transcribed_text = stt_data.get("text", "")

            logger.info(f"Trascrizione completata. Testo: {transcribed_text[:50]}... Emozione: {emotion}")

            # Se abbiamo testo trascritto, inviamolo al chatbot
            chat_response = None
            audio_url = None
            """
            if transcribed_text:
                chat_response_req = await client.post(
                    f"{API_GATEWAY_URL}/api/chat",
                    json={"text": transcribed_text, "emotion": emotion}
                )
                chat_response = chat_response_req.json()

                # Richiesta TTS
                tts_response = await client.post(
                    f"{API_GATEWAY_URL}/api/tts/synthesize",
                    json={"text": chat_response["response"], "emotion": emotion}
                )

                if tts_response.status_code == 200:
                    audio_url = f"{API_GATEWAY_URL}/api/tts/audio/{tts_response.json().get('audio_id', '')}"
            """
            return {
                "text": transcribed_text,
                "emotion": emotion,
                "confidence": emotion_data.get("confidence", 1.0),
                "response": chat_response["response"] if chat_response else None,
                "audio_url": audio_url
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
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
"""

if __name__ == "__main__":
    print(f"Starting frontend service on port: {PORT}")
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)