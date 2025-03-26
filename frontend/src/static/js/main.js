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

    // Invio messaggio con tasto invio
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Invio messaggio con bottone
    sendButton.addEventListener('click', sendMessage);

    // Registrazione audio
    voiceButton.addEventListener('click', toggleRecording);

    function toggleRecording() {
        if (isRecording) {
            stopRecording();
        } else {
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
            voiceButton.textContent = '⏹️';
        } catch (err) {
            console.error('Errore durante l\'accesso al microfono:', err);
            alert('Impossibile accedere al microfono');
        }
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            isRecording = false;
            voiceButton.classList.remove('recording');
            voiceButton.textContent = '🎤';

            // Chiudi le tracce audio per rilasciare il microfono
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
    }

    async function sendAudioToServer() {
        try {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const formData = new FormData();
            formData.append('audio_data', audioBlob);

            addMessage('Trascrivendo l\'audio...', 'bot');

            const response = await fetch('/transcribe_audio', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.text) {
                messageInput.value = data.text;
                // Rimuovi il messaggio "Trascrivendo l'audio..."
                chatMessages.lastElementChild.remove();
                sendMessage();
            } else {
                addMessage('Non sono riuscito a capire. Puoi riprovare?', 'bot');
            }
        } catch (error) {
            console.error('Errore nell\'invio dell\'audio:', error);
            addMessage('Si è verificato un errore nell\'elaborazione dell\'audio', 'bot');
        }
    }

    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        // Aggiungi il messaggio dell'utente alla chat
        addMessage(message, 'user');
        messageInput.value = '';

        try {
            const formData = new FormData();
            formData.append('message', message);

            const response = await fetch('/send_message', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            // Aggiorna l'etichetta dell'emozione
            emotionLabel.textContent = getEmotionText(data.emotion);

            // Aggiungi la risposta del bot alla chat
            addMessage(data.response, 'bot');

            // Riproduci l'audio se disponibile
            if (data.audio_url) {
                responseAudio.src = data.audio_url;
                responseAudio.style.display = 'block';
                responseAudio.play();
            }
        } catch (error) {
            console.error('Errore nell\'invio del messaggio:', error);
            addMessage('Si è verificato un errore nella comunicazione con il server', 'bot');
        }
    }

    function addMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;

        messageDiv.appendChild(contentDiv);
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

        return emotionMap[emotion] || emotion;
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
});