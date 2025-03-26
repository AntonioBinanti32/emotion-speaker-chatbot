document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const voiceButton = document.getElementById('voice-button');
    const chatMessages = document.getElementById('chat-messages');
    const emotionLabel = document.getElementById('emotion-label');
    const responseAudio = document.getElementById('response-audio');

    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;
    let isWaitingForResponse = false;

    // Effetto spotlight che segue il cursore
    const spotlight = document.createElement('div');
    spotlight.classList.add('cursor-spotlight');
    document.body.appendChild(spotlight);

    document.addEventListener('mousemove', function(e) {
        spotlight.style.left = e.clientX + 'px';
        spotlight.style.top = e.clientY + 'px';
    });

    // Effetto animato per l'inizializzazione della chat
    const firstMessage = chatMessages.querySelector('.message');
    if (firstMessage) {
        firstMessage.style.opacity = '0';
        firstMessage.style.transform = 'translateY(20px)';

        setTimeout(() => {
            firstMessage.style.transition = 'all 0.5s ease';
            firstMessage.style.opacity = '1';
            firstMessage.style.transform = 'translateY(0)';
        }, 300);
    }

    // Invio messaggio con tasto invio
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !isWaitingForResponse) {
            sendMessage();
        }
    });

    // Invio messaggio con bottone
    sendButton.addEventListener('click', function() {
        if (!isWaitingForResponse) {
            sendMessage();
        }
    });

    // Registrazione audio
    voiceButton.addEventListener('click', toggleRecording);

    function toggleRecording() {
        if (isRecording) {
            stopRecording();
        } else if (!isWaitingForResponse) {
            startRecording();
        }
    }

    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.addEventListener('dataavailable', event => {
                audioChunks.push(event.data);
            });

            mediaRecorder.addEventListener('stop', sendAudioToServer);

            mediaRecorder.start();
            isRecording = true;
            voiceButton.classList.add('recording');
            voiceButton.innerHTML = '<i class="fas fa-stop"></i>';
        } catch (err) {
            console.error('Errore durante l\'accesso al microfono:', err);
            showError('Impossibile accedere al microfono');
        }
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            isRecording = false;
            voiceButton.classList.remove('recording');
            voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';

            // Chiudi le tracce audio per rilasciare il microfono
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
    }

    async function sendAudioToServer() {
        if (isWaitingForResponse) return;

        isWaitingForResponse = true;
        try {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const formData = new FormData();
            formData.append('audio_data', audioBlob);

            showLoadingMessage();

            const response = await fetch('/transcribe_and_analyze_audio', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            // Rimuovi il messaggio di caricamento
            removeLoadingMessage();

            // Aggiorna l'etichetta dell'emozione con quella rilevata dall'audio
            emotionLabel.textContent = getEmotionText(data.emotion);

            // Se c'è un testo trascritto, mostralo come messaggio dell'utente
            if (data.text) {
                addMessage(data.text, 'user', true);

                // Se c'è una risposta dal chatbot, mostrala
                if (data.response) {
                    addMessage(data.response, 'bot', true);

                    // Riproduci l'audio della risposta se disponibile
                    if (data.audio_url) {
                        responseAudio.src = data.audio_url;
                        responseAudio.style.display = 'block';
                        responseAudio.play();
                    } else {
                        responseAudio.style.display = 'none';
                    }
                }
            } else {
                addMessage('Non sono riuscito a capire. Puoi riprovare?', 'bot');
            }
        } catch (error) {
            console.error('Errore nell\'invio dell\'audio:', error);
            removeLoadingMessage();
            showError('Si è verificato un errore nell\'elaborazione dell\'audio');
        } finally {
            isWaitingForResponse = false;
        }
    }

    function showLoadingMessage() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot loading-message';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content typing-indicator';

        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            contentDiv.appendChild(dot);
        }

        loadingDiv.appendChild(contentDiv);
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeLoadingMessage() {
        const loadingMessage = document.querySelector('.loading-message');
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }

    function showError(message) {
        addMessage(message, 'bot');
    }

    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message || isWaitingForResponse) return;

        isWaitingForResponse = true;

        // Aggiorna l'interfaccia
        sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        messageInput.disabled = true;
        voiceButton.disabled = true;

        // Aggiungi il messaggio dell'utente alla chat con timestamp
        addMessage(message, 'user', true);
        messageInput.value = '';

        try {
            // Mostra indicatore di caricamento
            showLoadingMessage();

            const formData = new FormData();
            formData.append('message', message);

            const response = await fetch('/send_message', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            // Rimuovi l'indicatore di caricamento
            removeLoadingMessage();

            // Aggiorna l'etichetta dell'emozione
            emotionLabel.textContent = getEmotionText(data.emotion);

            // Aggiungi la risposta del bot alla chat con timestamp
            addMessage(data.response, 'bot', true);

            // Riproduci l'audio se disponibile
            if (data.audio_url) {
                responseAudio.src = data.audio_url;
                responseAudio.style.display = 'block';
                responseAudio.play();
            } else {
                responseAudio.style.display = 'none';
            }
        } catch (error) {
            console.error('Errore nell\'invio del messaggio:', error);
            showError('Si è verificato un errore nella comunicazione con il server');
        } finally {
            // Ripristina l'interfaccia
            sendButton.innerHTML = '<i class="fas fa-paper-plane"></i> Invia';
            messageInput.disabled = false;
            voiceButton.disabled = false;
            messageInput.focus();
            isWaitingForResponse = false;
        }
    }

    function addMessage(content, sender, showTime = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        messageDiv.appendChild(contentDiv);

        // Aggiungi timestamp se richiesto
        if (showTime) {
            const timestamp = document.createElement('div');
            timestamp.className = 'message-timestamp';
            const now = new Date();
            timestamp.textContent = now.getHours().toString().padStart(2, '0') + ':' +
                                   now.getMinutes().toString().padStart(2, '0');
            messageDiv.appendChild(timestamp);
        }

        chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function getEmotionText(emotion) {
        // Mappa le emozioni inglesi in italiano con emoji
        const emotionMap = {
            'angry': {text: 'rabbia', emoji: '😠'},
            'disgust': {text: 'disgusto', emoji: '🤢'},
            'fearful': {text: 'paura', emoji: '😨'},
            'happy': {text: 'felicità', emoji: '😊'},
            'neutral': {text: 'neutro', emoji: '😐'},
            'sad': {text: 'tristezza', emoji: '😢'}
        };

        // Gestione emozioni numeriche
        if (typeof emotion === 'number' || !isNaN(parseInt(emotion))) {
            const numEmotion = parseInt(emotion);
            switch(numEmotion) {
                case 0: return emotionMap['angry'].text;
                case 1: return emotionMap['disgust'].text;
                case 2: return emotionMap['fearful'].text;
                case 3: return emotionMap['happy'].text;
                case 4: return emotionMap['neutral'].text;
                case 5: return emotionMap['sad'].text;
                default: return emotionMap['neutral'].text;
            }
        }

        const emotionInfo = emotionMap[emotion.toLowerCase()] || {text: 'neutro', emoji: '😐'};

        // Aggiorna la classe per lo stile
        emotionLabel.className = '';
        emotionLabel.classList.add(emotionInfo.text);

        // Ritorna il testo con emoji
        //return `${emotionInfo.emoji} ${emotionInfo.text}`;
        return `${emotionInfo.text}`;
    }

    setTimeout(() => {
        messageInput.focus();
    }, 500);
});