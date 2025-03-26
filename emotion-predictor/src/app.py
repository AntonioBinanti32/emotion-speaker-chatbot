#TODO: verificare funzionamemto
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import tensorflow as tf
import numpy as np
import librosa
import joblib
import os
import tempfile
import uvicorn
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

# Configurazione
PORT = int(os.getenv("EMOTION_PREDICTOR_PORT", 5002))
MODEL_PATH = os.getenv("MODEL_PATH", "./model/emotion_classifier.h5")
SCALER_PATH = os.getenv("SCALER_PATH", "./model/scaler.pkl")

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Caricamento modello e scaler
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print(f"Modello caricato da: {MODEL_PATH}")
    print(f"Scaler caricato da: {SCALER_PATH}")
except Exception as e:
    print(f"Errore nel caricamento del modello o dello scaler: {e}")
    model = None
    scaler = None

app = FastAPI(title="Emotion Predictor Service")

# Configurare CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mappa delle emozioni
EMOTION_MAP = {
    0: "angry",
    1: "disgust",
    2: "fearful",
    3: "happy",
    4: "neutral",
    5: "sad"
}


class TextInput(BaseModel):
    text: str


class EmotionResponse(BaseModel):
    emotion: str
    confidence: float
    probabilities: Dict[str, float]


def extract_mel_features(audio_data, sr=16000):
    try:
        logger.info(f"Estrazione delle features dal file audio: {audio_data}")
        y, sr = librosa.load(audio_data, sr=sr, duration=3, offset=0.5)
        logger.info(f"Audio caricato con shape: {y.shape}")
        mel_spectrogram = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_fft=2048,
            hop_length=512,
            n_mels=128
        )

        # Conversione in decibel
        logger.info(f"Mel spectrogram shape: {mel_spectrogram.shape}")
        mel_spectrogram_db = librosa.power_to_db(mel_spectrogram, ref=np.max)

        expected_width = 94
        current_width = mel_spectrogram_db.shape[1]
        logger.info(f"Mel spectrogram shape dopo conversione in dB: {mel_spectrogram_db.shape}")
        if current_width < expected_width:
            # Padding se necessario
            logger.info(f"Padding del mel spectrogram da {current_width} a {expected_width}")
            pad_width = expected_width - current_width
            mel_spectrogram_db = np.pad(mel_spectrogram_db, ((0, 0), (0, pad_width)), mode='constant')
        elif current_width > expected_width:
            # Troncamento se necessario
            logger.info(f"Troncamento del mel spectrogram da {current_width} a {expected_width}")
            mel_spectrogram_db = mel_spectrogram_db[:, :expected_width]

        return mel_spectrogram_db

    except Exception as e:
        print(f"Errore durante l'estrazione delle features: {e}")
        return None


@app.get("/health")
async def health_check():
    if model is None or scaler is None:
        raise HTTPException(status_code=500, detail="Modello o scaler non caricati correttamente")
    return {"status": "healthy"}


@app.post("/predict", response_model=EmotionResponse)
async def predict_emotion(file: UploadFile = File(...)):
    if model is None or scaler is None:
        raise HTTPException(status_code=500, detail="Modello o scaler non caricati")

    try:
        # Salva temporaneamente il file audio
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name
            logger.info(f"File audio temporaneo salvato in: {temp_file_path}")

        # Estrai le features
        features = extract_mel_features(temp_file_path)
        os.unlink(temp_file_path)

        if features is None:
            raise HTTPException(status_code=400, detail="Impossibile estrarre le features dal file audio")

        # Reshape
        original_shape = features.shape
        features_reshaped = features.reshape(-1, features.shape[-1])

        # Applicazione dello scaler
        features_scaled = scaler.transform(features_reshaped)

        # Reshape alla forma originale
        features_scaled = features_scaled.reshape(original_shape)

        # Aggiunta delle dimensioni per batch e channel
        features_final = np.expand_dims(features_scaled, axis=0)  # Aggiungi dimensione batch
        features_final = np.expand_dims(features_final, axis=-1)  # Aggiungi dimensione channel

        # Predizione
        prediction = model.predict(features_final)
        predicted_class = np.argmax(prediction, axis=1)[0]

        probabilities = {EMOTION_MAP[i]: float(prediction[0][i]) for i in range(len(prediction[0]))}

        logger.info(f"Emozione predetta: {EMOTION_MAP.get(predicted_class, 'neutral')}")
        logger.info(f"Confidence: {float(prediction[0][predicted_class])}")
        logger.info(f"Probabilità: {probabilities}")


        return {
            "emotion": EMOTION_MAP.get(predicted_class, "neutral"),
            "confidence": float(prediction[0][predicted_class]),
            "probabilities": {EMOTION_MAP[i]: float(prediction[0][i]) for i in range(len(prediction[0]))}
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante la predizione: {str(e)}")


@app.post("/predict/text", response_model=EmotionResponse)
async def predict_emotion_from_text(input_data: TextInput):
    # Questo è un endpoint di fallback che restituisce neutrale
    # Poiché l'analisi delle emozioni dal testo richiederebbe un modello diverso
    return {
        "emotion": "neutral",
        "confidence": 1.0,
        "probabilities": {emotion: 0.0 for emotion in EMOTION_MAP.values()}
    }


if __name__ == "__main__":
    print(f"Avvio del servizio emotion-predictor sulla porta {PORT}")
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)