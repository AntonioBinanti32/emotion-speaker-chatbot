#TODO: Implementare
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE ${FRONTEND_PORT}

CMD ["python", "src/app.py"]