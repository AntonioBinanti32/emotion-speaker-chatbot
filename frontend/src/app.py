#TODO: Implementare
from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
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
            confidence = emotion_data.get("confidence", 1.0)

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
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Leggi il contenuto del file
            content = await audio_data.read()

            logger.info(f"Inviando richiesta a {API_GATEWAY_URL}/api/stt/transcribe per la trascrizione dell'audio")
            logger.info(
                f"Inviando richiesta a {API_GATEWAY_URL}/api/emotion/predict per rilevare l'emozione dell'audio")
            logger.info(
                f"Inviando richiesta a {API_GATEWAY_URL}/api/environment/classify per rilevare l'ambiente dell'audio")

            # Invia l'audio ai tre servizi in parallelo
            tasks = [
                client.post(f"{API_GATEWAY_URL}/api/stt/transcribe",
                            files={"audio_file": ("audio.wav", content, "audio/wav")}),
                client.post(f"{API_GATEWAY_URL}/api/emotion/predict",
                            files={"file": ("audio.wav", content, "audio/wav")}),
                client.post(f"{API_GATEWAY_URL}/api/environment/classify",
                            files={"file": ("audio.wav", content, "audio/wav")})
            ]

            import asyncio
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Gestisci le risposte
            stt_response, emotion_response, env_response = responses

            # Verifica eventuali errori
            for resp in responses:
                if isinstance(resp, Exception):
                    logger.error(f"Errore durante la richiesta parallela: {resp}")
                    raise HTTPException(status_code=500, detail=str(resp))

            # Estrai i dati
            stt_data = stt_response.json()
            emotion_data = emotion_response.json()
            environment_data = env_response.json()

            logger.info(f"Risposta ricevuta da stt-service: {stt_data}")
            logger.info(f"Risposta ricevuta da emotion-predictor: {emotion_data}")
            logger.info(f"Risposta ricevuta da environment-classifier: {environment_data}")


            # Restituisci i risultati della prima parte
            return {
                "text": stt_data.get("text", ""),
                "emotion": emotion_data.get("emotion", "neutral"),
                "environment": environment_data.get("environment", "Inside, small room"),
                "environment_confidence": environment_data.get("confidence", 1.0),
                "emotion_confidence": emotion_data.get("confidence", 1.0),
                "emotion_probabilities": emotion_data.get("probabilities", {}),
                "environment_detections": environment_data.get("all_detections", {})
            }
    except Exception as e:
        logger.error(f"Errore durante l'analisi dell'audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_chat_response")
async def get_chat_response(message: str = Form(...), emotion: str = Form(...), environment: str = Form(None)):
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            # Invia richiesta al chatbot
            chat_payload = {"text": message, "emotion": emotion}
            if environment:
                chat_payload["environment"] = environment

            logger.info(f"Inviando richiesta a {API_GATEWAY_URL}/api/chat: {chat_payload}")
            chat_response = await client.post(
                f"{API_GATEWAY_URL}/api/chat",
                json=chat_payload
            )

            response_data = chat_response.json()

            logger.info(f"Risposta ricevuta dal chatbot: {chat_response}")

            logger.info(f"Inviando richiesta a {API_GATEWAY_URL}/api/tts/synthesize: ", {"text": response_data["response"], "emotion": emotion})

            # Richiedi la sintesi vocale
            tts_response = await client.post(
                f"{API_GATEWAY_URL}/api/tts/synthesize",
                json={"text": response_data["response"], "emotion": emotion}
            )

            logger.info(f"Risposta ricevuta da tts-service per la sintetizzazione: {tts_response.json()}")

            audio_url = None
            if tts_response.status_code == 200:
                audio_url = f"{API_GATEWAY_URL}/api/tts/audio/{tts_response.json().get('audio_id', '')}"

            return {
                "response": response_data["response"],
                "audio_url": audio_url
            }
    except Exception as e:
        logger.error(f"Errore nel generare la risposta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tts/audio/{audio_id}")
async def proxy_audio(audio_id: str):
    try:
        logger.info(f"Proxy richiesta audio per id: {audio_id}")
        target_url = f"{API_GATEWAY_URL}/api/tts/audio/{audio_id}"
        logger.info(f"URL target: {target_url}")

        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.get(target_url)

            logger.info(
                f"Risposta da gateway: status={response.status_code}, content-type={response.headers.get('content-type')}")

            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if content_type.startswith('audio/'):
                    # Restituisci il file audio
                    return Response(
                        content=response.content,
                        media_type=content_type,
                        headers=dict(response.headers)
                    )
                else:
                    # Restituisci la risposta JSON (es. stato "processing")
                    return response.json()
            else:
                logger.error(f"Errore nella risposta dal gateway: {response.status_code} - {response.text}")
                return {"detail": response.text or "Errore nel recupero dell'audio"}

    except Exception as e:
        logger.error(f"Errore nel proxy dell'audio {audio_id}: {e}")
        return {"detail": str(e), "status": "error"}

if __name__ == "__main__":
    print(f"Starting frontend service on port: {PORT}")
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)