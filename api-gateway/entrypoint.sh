#!/bin/sh

envsubst '$WORKER_CONNECTIONS $API_GATEWAY_PORT $FRONTEND_PORT $STT_SERVICE_PORT $EMOTION_PREDICTOR_PORT $CHATBOT_SERVICE_PORT $TTS_SERVICE_PORT $CHESHIRE_CAT_PORT_INTERNAL' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Avvia nginx
exec nginx -g 'daemon off;'
# Avvia nginx
exec nginx -g 'daemon off;'