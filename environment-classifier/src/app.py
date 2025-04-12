from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import tensorflow_io as tfio
import uuid
from typing import Dict, List, Optional
import uvicorn
from pydantic import BaseModel

# Configurazione
PORT = int(os.getenv("ENV_CLASSIFIER_PORT", 5005))
MODEL_CACHE = "model_cache"
os.makedirs(MODEL_CACHE, exist_ok=True)

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Environment Audio Classifier")

# Configurare CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Modelli dati
class ClassificationResponse(BaseModel):
    environment: str
    confidence: float
    all_detections: Optional[Dict[str, float]] = None


# Caricare il modello YAMNet
try:
    logger.info("Caricamento del modello YAMNet...")
    model = hub.load('https://tfhub.dev/google/yamnet/1')
    logger.info("Modello YAMNet caricato con successo")

    # Mappa delle classi ambientali alle emoji
    environment_to_emoji = {
        "Speech": "🗣️",
        "Inside, small room": "🏠",
        "Inside, large room or hall": "🏢",
        "Outside, urban or manmade": "🏙️",
        "Outside, rural or natural": "🌳",
        "Vehicle": "🚗",
        "Music": "🎵",
        "Silence": "🔇",
        "Water": "💧",
        "Wind": "💨",
        "Animal": "🐾",
        "Noise": "📢"
    }

    # Mapping delle classi YAMNet alle nostre classi semplificate
    yamnet_to_environment = {
        'Speech': 'Speech',
        'Inside, small room': 'Inside, small room',
        'Inside, large room or hall': 'Inside, large room or hall',
        'Vehicle': 'Vehicle',
        'Car': 'Vehicle',
        'Bus': 'Vehicle',
        'Train': 'Vehicle',
        'Subway, metro, underground': 'Vehicle',
        'Traffic noise, roadway noise': 'Outside, urban or manmade',
        'Water tap, faucet': 'Water',
        'Sink (filling or washing)': 'Water',
        'Rain': 'Water',
        'Water': 'Water',
        'Stream': 'Water',
        'Wind': 'Wind',
        'Wind noise (microphone)': 'Wind',
        'Animal': 'Animal',
        'Domestic animals, pets': 'Animal',
        'Dog': 'Animal',
        'Cat': 'Animal',
        'Bird': 'Animal',
        'Music': 'Music',
        'Silence': 'Silence',
        'Quiet': 'Silence'
    }

except Exception as e:
    logger.error(f"Errore nel caricamento del modello YAMNet: {e}")
    model = None


@app.get("/health")
async def health_check():
    if model is None:
        raise HTTPException(status_code=500, detail="Modello YAMNet non caricato correttamente")
    return {"status": "healthy"}


@app.post("/classify", response_model=ClassificationResponse)
async def classify_environment(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(status_code=500, detail="Modello YAMNet non disponibile")

    try:
        # Leggi il file audio
        contents = await file.read()
        temp_path = f"/tmp/{uuid.uuid4()}.wav"
        with open(temp_path, "wb") as f:
            f.write(contents)

        # Carica e preelabora l'audio per YAMNet
        waveform, sample_rate = load_wav_16k_mono(temp_path)

        # Pulisci il file temporaneo
        os.remove(temp_path)

        # Esegui la classificazione
        scores, embeddings, spectrogram = model(waveform)
        scores_np = scores.numpy()

        # Ottieni le classi e le probabilità
        class_map = yamnet_model_metadata()
        top_indices = np.argsort(scores_np[0])[::-1][:10]  # Top 10 classi

        # Mappa le classi YAMNet alle nostre classi ambientali
        environment_scores = {}
        for i in top_indices:
            yamnet_class = class_map[i]
            environment = map_to_environment(yamnet_class)
            if environment and environment not in environment_scores:
                environment_scores[environment] = float(scores_np[0][i])
            elif environment in environment_scores:
                environment_scores[environment] = max(environment_scores[environment], float(scores_np[0][i]))

        # Se non è stato trovato nessun ambiente, usa "Outside, urban or manmade" come default
        if not environment_scores:
            environment_scores["Outside, urban or manmade"] = 0.5

        # Trova l'ambiente con la probabilità più alta
        top_environment = max(environment_scores.items(), key=lambda x: x[1])

        return {
            "environment": top_environment[0],
            "confidence": top_environment[1],
            "all_detections": environment_scores
        }

    except Exception as e:
        logger.error(f"Errore durante la classificazione dell'ambiente: {e}")
        raise HTTPException(status_code=500, detail=f"Errore: {str(e)}")


def load_wav_16k_mono(file_path):
    """Carica un file audio e lo converte a 16 kHz mono per YAMNet."""
    try:
        # Prima prova il decoder WAV standard
        file_contents = tf.io.read_file(file_path)
        try:
            wav, sample_rate = tf.audio.decode_wav(
                file_contents,
                desired_channels=1
            )
        except tf.errors.InvalidArgumentError:
            # Se il file non è WAV, usa ffmpeg per convertirlo
            import subprocess
            output_path = f"{file_path}_converted.wav"
            subprocess.run([
                "ffmpeg", "-y", "-i", file_path,
                "-ar", "16000", "-ac", "1", "-f", "wav",
                output_path
            ], check=True, capture_output=True)

            # Ora leggi il file convertito
            file_contents = tf.io.read_file(output_path)
            wav, sample_rate = tf.audio.decode_wav(
                file_contents,
                desired_channels=1
            )
            # Pulizia file temporaneo
            os.remove(output_path)

        wav = tf.squeeze(wav, axis=-1)
        sample_rate = tf.cast(sample_rate, dtype=tf.int64)

        # Resample a 16 kHz se necessario
        if sample_rate != 16000:
            target_rate = 16000
            wav = tfio.audio.resample(wav, sample_rate, target_rate)

        return wav, sample_rate
    except Exception as e:
        logger.error(f"Errore nel caricamento dell'audio: {e}")
        raise e


def yamnet_model_metadata():
    """Restituisce le etichette delle classi YAMNet."""
    # URL aggiornato o file locale (se disponibile)
    try:
        class_map_path = tf.keras.utils.get_file(
            'yamnet_class_map.csv',
            'https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv'
        )
        class_names = []
        with open(class_map_path) as csv_file:
            for row in csv_file:
                class_names.append(row.strip().split(',')[2])
        return class_names
    except:
        logger.warning("Impossibile scaricare la mappa delle classi. Utilizzando mappa interna.")
        # Versione cache delle classi più importanti se il download fallisce
        return list(yamnet_to_environment.keys())


def map_to_environment(yamnet_class):
    """Mappa una classe YAMNet a una delle nostre classi ambientali."""
    if yamnet_class in yamnet_to_environment:
        return yamnet_to_environment[yamnet_class]

    # Fallback per classi non mappate
    if "Inside" in yamnet_class:
        return "Inside, small room"
    elif "Outside" in yamnet_class or "Urban" in yamnet_class:
        return "Outside, urban or manmade"
    elif "Rural" in yamnet_class or "Nature" in yamnet_class or "Forest" in yamnet_class:
        return "Outside, rural or natural"

    return None


@app.get("/environments")
async def get_environments():
    """Restituisce l'elenco delle classi ambientali e le rispettive emoji."""
    return {
        "environments": environment_to_emoji
    }


if __name__ == "__main__":
    print(f"Avvio del servizio Environment Classifier sulla porta {PORT}")
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)