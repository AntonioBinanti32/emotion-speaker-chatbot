#TODO: Implementare
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
import tempfile
import os
import uvicorn
import logging
from pydantic import BaseModel
from typing import Optional

# Configurazione
PORT = int(os.getenv("STT_SERVICE_PORT", 5001))
MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")  # tiny, base, small, medium, large

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
"""
# Inizializzazione del modello Whisper
try:
    logger.info(f"Caricamento del modello Whisper '{MODEL_SIZE}'...")
    model = whisper.load_model(MODEL_SIZE)
    logger.info(f"Modello Whisper caricato con successo.")
except Exception as e:
    logger.error(f"Errore nel caricamento del modello Whisper: {e}")
    model = None
"""
# Inizializzazione del modello Whisper
try:
    logger.info(f"Caricamento del modello Whisper '{MODEL_SIZE}'...")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    logger.info(f"Modello Whisper caricato con successo.")
except Exception as e:
    logger.error(f"Errore nel caricamento del modello Whisper: {e}")
    model = None

app = FastAPI(title="Speech-to-Text Service")

LANGUAGE = os.getenv("WHISPER_LANGUAGE", "it")

# Configurare CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranscriptionResponse(BaseModel):
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None


@app.get("/health")
async def health_check():
    if model is None:
        raise HTTPException(status_code=500, detail="Modello Whisper non caricato correttamente")
    return {"status": "healthy"}


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(audio_file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(status_code=500, detail="Modello Whisper non disponibile")

    try:
        # Salva temporaneamente il file audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        logger.info(f"File audio temporaneo salvato in: {temp_file_path}")

        # Esegui la trascrizione
        #result = model.transcribe(temp_file_path, language=LANGUAGE)
        segments, info = model.transcribe(temp_file_path, language=LANGUAGE)
        text = " ".join([segment.text for segment in segments])
        result = {"text": text, "language": info.language}

        # Pulizia del file temporaneo
        os.unlink(temp_file_path)

        text = result.get("text", "").strip()
        language = result.get("language")

        logger.info(f"Trascrizione completata. Testo: {text[:50]}... Lingua: {language}")

        return {
            "text": text,
            "language": language,
            "confidence": 1.0
        }

    except Exception as e:
        logger.error(f"Errore durante la trascrizione: {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante la trascrizione: {str(e)}")


if __name__ == "__main__":
    print(f"Avvio del servizio STT sulla porta {PORT}")
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)