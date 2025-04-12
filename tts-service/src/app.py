from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import uuid
import torch
import torchaudio
import numpy as np
import logging
import uvicorn
from pydantic import BaseModel
from typing import Optional, List, Dict
import ChatTTS

# Configurazione
PORT = int(os.getenv("TTS_SERVICE_PORT", 5004))
AUDIO_DIR = "audio_files"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Text-to-Speech Service")

# Configurare CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Modelli dati
class TTSRequest(BaseModel):
    text: str
    emotion: Optional[str] = "neutral"
    speaker_id: Optional[str] = None


class TTSResponse(BaseModel):
    audio_id: str
    status: str = "success"


# Caricare il modello in memoria
try:
    logger.info("Caricamento del modello ChatTTS...")
    chat_tts = ChatTTS.Chat()
    chat_tts.load(compile=False)  # Utilizzo compile=False per compatibilità
    logger.info("Modello ChatTTS caricato con successo")

    # Memorizza gli speaker per riutilizzo
    speaker_cache: Dict[str, np.ndarray] = {}

except Exception as e:
    logger.error(f"Errore nel caricamento del modello ChatTTS: {e}")
    chat_tts = None

# Mappa delle emozioni ai parametri del modello
emotion_to_params = {
    "neutral": {"temperature": 0.3, "top_P": 0.7, "top_K": 20},
    "happy": {"temperature": 0.4, "top_P": 0.8, "top_K": 30, "prompt": "[oral_2][laugh_1]"},
    "sad": {"temperature": 0.2, "top_P": 0.6, "top_K": 15, "prompt": "[oral_1][break_3]"},
    "angry": {"temperature": 0.5, "top_P": 0.9, "top_K": 25, "prompt": "[oral_3]"},
    "fear": {"temperature": 0.3, "top_P": 0.7, "top_K": 20, "prompt": "[oral_1][break_2]"},
    "surprise": {"temperature": 0.4, "top_P": 0.8, "top_K": 30, "prompt": "[oral_3][break_1]"}
}


@app.get("/health")
async def health_check():
    if chat_tts is None:
        raise HTTPException(status_code=500, detail="Modello ChatTTS non caricato correttamente")
    return {"status": "healthy"}


@app.post("/synthesize", response_model=TTSResponse)
async def synthesize_speech(request: TTSRequest, background_tasks: BackgroundTasks):
    if chat_tts is None:
        raise HTTPException(status_code=500, detail="Modello ChatTTS non disponibile")

    try:
        # Generare un ID univoco per il file audio
        audio_id = str(uuid.uuid4())

        # Aggiungere il task di sintesi in background
        background_tasks.add_task(
            generate_audio,
            request.text,
            audio_id,
            request.emotion,
            request.speaker_id
        )

        return {"audio_id": audio_id, "status": "processing"}

    except Exception as e:
        logger.error(f"Errore durante la sintesi vocale: {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante la sintesi vocale: {str(e)}")


@app.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    audio_path = os.path.join(AUDIO_DIR, f"{audio_id}.wav")

    if not os.path.exists(audio_path):
        # Controlla se è ancora in elaborazione
        processing_path = os.path.join(AUDIO_DIR, f"{audio_id}.processing")
        if os.path.exists(processing_path):
            return {"status": "processing"}
        else:
            raise HTTPException(status_code=404, detail="Audio non trovato")

    return FileResponse(audio_path, media_type="audio/wav")


async def generate_audio(text: str, audio_id: str, emotion: str = "neutral", speaker_id: str = None):
    """Genera l'audio in background e salva il file."""
    try:
        # Crea un file di segnalazione per indicare che l'elaborazione è in corso
        processing_path = os.path.join(AUDIO_DIR, f"{audio_id}.processing")
        with open(processing_path, "w") as f:
            f.write("processing")

        # Normalizza l'emozione e usa quella predefinita se non disponibile
        emotion = emotion.lower() if emotion else "neutral"
        if emotion not in emotion_to_params:
            logger.warning(f"Emozione '{emotion}' non supportata, uso 'neutral'")
            emotion = "neutral"

        # Configura i parametri in base all'emozione
        emotion_params = emotion_to_params.get(emotion)

        params_infer_code = ChatTTS.Chat.InferCodeParams(
            temperature=emotion_params.get("temperature", 0.3),
            top_P=emotion_params.get("top_P", 0.7),
            top_K=emotion_params.get("top_K", 20),
        )

        # Se è stato specificato uno speaker_id, usa quello
        if speaker_id and speaker_id in speaker_cache:
            params_infer_code.spk_emb = speaker_cache[speaker_id]
        elif not speaker_id:
            # Genera un nuovo speaker e memorizzalo
            new_speaker = chat_tts.sample_random_speaker()
            speaker_id = str(uuid.uuid4())
            speaker_cache[speaker_id] = new_speaker
            params_infer_code.spk_emb = new_speaker

        # Inizializza params_refine_text solo se c'è un prompt
        params_refine_text = None
        if emotion_params.get("prompt"):
            params_refine_text = ChatTTS.Chat.RefineTextParams(
                prompt=emotion_params["prompt"]
            )

        # Genera l'audio con params_refine_text solo se non è None
        if params_refine_text:
            wavs = chat_tts.infer(
                [text],
                params_refine_text=params_refine_text,
                params_infer_code=params_infer_code
            )
        else:
            wavs = chat_tts.infer(
                [text],
                params_infer_code=params_infer_code
            )

        # Salva il file audio
        audio_path = os.path.join(AUDIO_DIR, f"{audio_id}.wav")
        torchaudio.save(
            audio_path,
            torch.from_numpy(wavs[0]).unsqueeze(0) if wavs[0].ndim == 1 else torch.from_numpy(wavs[0]),
            24000
        )

        # Rimuovi il file di segnalazione
        if os.path.exists(processing_path):
            os.remove(processing_path)

        logger.info(f"Audio generato con successo: {audio_id}")

    except Exception as e:
        logger.error(f"Errore durante la generazione dell'audio {audio_id}: {e}")
        # Rimuovi il file di segnalazione in caso di errore
        if os.path.exists(processing_path):
            os.remove(processing_path)

@app.get("/speakers")
async def get_speakers():
    speakers = list(speaker_cache.keys())
    return {"speakers": speakers, "count": len(speakers)}


if __name__ == "__main__":
    print(f"Avvio del servizio TTS sulla porta {PORT}")
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)