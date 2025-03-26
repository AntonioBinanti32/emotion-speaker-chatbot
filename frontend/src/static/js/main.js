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

            const response = await fetch('/transcribe_audio', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            // Rimuovi il messaggio di caricamento
            removeLoadingMessage();

            if (data.text) {
                messageInput.value = data.text;
                sendMessage();
            } else {
                addMessage('Non sono riuscito a capire. Puoi riprovare?', 'bot');
                isWaitingForResponse = false;
            }
        } catch (error) {
            console.error('Errore nell\'invio dell\'audio:', error);
            removeLoadingMessage();
            showError('Si è verificato un errore nell\'elaborazione dell\'audio');
            isWaitingForResponse = false;
        }
    }

    function showLoadingMessage() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot loading-message';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'loading-indicator';

        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'dot';
            loadingIndicator.appendChild(dot);
        }

        contentDiv.appendChild(loadingIndicator);
        loadingDiv.appendChild(contentDiv);
        chatMessages.appendChild(loadingDiv);

        // Scroll to bottom
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
        const emotionMap = {
            'happy': 'felice',
            'sad': 'triste',
            'angry': 'arrabbiato',
            'fearful': 'spaventato',
            'surprised': 'sorpreso',
            'neutral': 'neutrale'
        };

        const emotionText = emotionMap[emotion] || emotion;

        // Aggiorna la classe per lo stile
        const emotionLabel = document.getElementById('emotion-label');
        emotionLabel.className = '';
        emotionLabel.classList.add(emotionText);

        return emotionText;
    }

    setTimeout(() => {
        messageInput.focus();
    }, 500);

    // Effetto spotlight che segue il cursore
document.addEventListener('DOMContentLoaded', function() {
    const spotlight = document.createElement('div');
    spotlight.classList.add('cursor-spotlight');
    document.body.appendChild(spotlight);

    document.addEventListener('mousemove', function(e) {
        spotlight.style.left = e.clientX + 'px';
        spotlight.style.top = e.clientY + 'px';
    });

    // Effetto animato per l'inizializzazione della chat
    const chatMessages = document.getElementById('chat-messages');
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

    function getEmotionText(emotion) {
    const emotionMap = {
        'happy': {text: 'felice', emoji: '😊'},
        'sad': {text: 'triste', emoji: '😢'},
        'angry': {text: 'arrabbiato', emoji: '😠'},
        'fearful': {text: 'spaventato', emoji: '😨'},
        'surprised': {text: 'sorpreso', emoji: '😲'},
        'neutral': {text: 'neutrale', emoji: '😐'}
    };

    const emotionInfo = emotionMap[emotion] || {text: emotion, emoji: '❓'};

    // Aggiorna la classe per lo stile
    const emotionLabel = document.getElementById('emotion-label');
    emotionLabel.className = '';
    emotionLabel.classList.add(emotionInfo.text);

    // Aggiorna il testo con emoji
    return `${emotionInfo.emoji} ${emotionInfo.text}`;
}

    // Sostituisci la funzione esistente
    window.showLoadingMessage = showLoadingMessage;
});
});