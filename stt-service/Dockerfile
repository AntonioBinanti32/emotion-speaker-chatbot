#TODO: Implementare
FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE ${STT_SERVICE_PORT}

CMD ["python", "src/app.py"]