import httpx
import os
import json
import logging

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_chat_response(text, emotion=None, environment=None):
    """Invia un messaggio a Cheshire Cat e restituisce la risposta."""
    cheshire_cat_url = os.getenv("CHESHIRE_CAT_URL", "http://cheshire-cat-core:80")

    payload = {
        "text": text,
        "user_id": "user",
    }

    if emotion:
        payload["metadata"] = {"emotion": emotion, "environment": environment}

    logger.info(f"Sending to Cheshire Cat: {json.dumps(payload)}")

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(
                f"{cheshire_cat_url}/message",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            response.raise_for_status()
            logger.info(f"Response status: {response.status_code}")

            data = response.json()

            if isinstance(data, dict):
                # Cerca la risposta in vari campi possibili
                content = data.get("content") or data.get("message") or data.get("output")
                if content:
                    return content

            logger.warning(f"Formato risposta inatteso: {data}")
            return "Non ho capito, puoi ripetere?"

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Error: {e.response.status_code} - {e}")
            return f"Errore di comunicazione: {e.response.status_code}"

        except Exception as e:
            logger.exception(f"Errore: {str(e)}")
            return f"Errore di comunicazione: {str(e)}"