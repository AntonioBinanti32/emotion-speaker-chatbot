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

function createDebugDiv() {
    const div = document.createElement('div');
    div.id = 'debug-log';
    div.style.cssText = 'position:fixed; bottom:0; left:0; max-height:200px; width:100%; overflow-y:auto; ' +
                       'background:rgba(0,0,0,0.7); color:white; font-size:12px; z-index:10000; padding:5px;';
    document.body.appendChild(div);
    return div;
}

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
            console.log("Inizio registrazione audio");
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

        try {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const formData = new FormData();
            formData.append('audio_data', audioBlob);

            // Mostra messaggio di caricamento per l'elaborazione dell'audio (lato utente)
            showLoadingMessage('user');

            // FASE 1: Trascrizione e analisi dell'audio
            const analysisResponse = await fetch('/transcribe_and_analyze_audio', {
                method: 'POST',
                body: formData
            });

            const analysisData = await analysisResponse.json();

            // Rimuovi il messaggio di caricamento
            removeLoadingMessage();

            // Se c'è un testo trascritto, mostralo come messaggio dell'utente con etichette
            if (analysisData.text) {
                // Aggiorna l'etichetta dell'emozione
                emotionLabel.textContent = getEmotionText(analysisData.emotion);

                // Aggiungi il messaggio con le etichette di emozione e ambiente
                addMessage(analysisData.text, 'user', true,
                    {
                        emotion: analysisData.emotion,
                        confidence: analysisData.emotion_confidence,
                        probabilities: analysisData.emotion_probabilities  // Assicurati che questo campo sia presente
                    },
                    {
                        environment: analysisData.environment,
                        confidence: analysisData.environment_confidence,
                        detections: analysisData.environment_detections  // Assicurati che questo campo sia presente
                    });

                // FASE 2: Ottieni risposta chatbot
                // Mostra messaggio di caricamento per la risposta del bot
                showLoadingMessage('bot');

                const chatFormData = new FormData();
                chatFormData.append('message', analysisData.text);
                chatFormData.append('emotion', analysisData.emotion);
                chatFormData.append('environment', analysisData.environment);

                const chatResponse = await fetch('/get_chat_response', {
                    method: 'POST',
                    body: chatFormData
                });

                const chatData = await chatResponse.json();

                // Rimuovi il messaggio di caricamento
                removeLoadingMessage();

                // Mostra la risposta del chatbot
                if (chatData.response) {
                    addMessage(chatData.response, 'bot', true);

                    // Riproduci l'audio della risposta se disponibile
                    if (chatData.audio_url) {
                        checkAndPlayAudio(chatData.audio_url);
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

   // Funzione modificata per mostrare messaggi di caricamento specifici per utente o bot
    function showLoadingMessage(sender = 'bot') {
        console.log("Mostro indicatore di caricamento per:", sender);
        const loadingDiv = document.createElement('div');
        loadingDiv.className = `message ${sender} loading-message`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content typing-indicator';

        // Aggiungi la classe 'dot' agli span
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            dot.className = 'dot';
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

        try {
            // Aggiungi il messaggio dell'utente alla chat con timestamp
            // (inizialmente senza emozioni/ambiente)
            addMessage(message, 'user', true);
            messageInput.value = '';

            // FASE 1: Analisi dell'emozione e ambiente
            const analyzeFormData = new FormData();
            analyzeFormData.append('message', message);
            console.log("Invio messaggio per analisi:", message);
            /*const analyzeResponse = await fetch('/analyze_message', {
                method: 'POST',
                body: analyzeFormData
            });
            */
            const analyzeData = {emotion: "Unknown", environment: "Unknown"};

            // Aggiorna il messaggio dell'utente con le emoji
            updateLastUserMessage(
                { emotion: analyzeData.emotion},
                { environment: analyzeData.environment}
            );

            // Mostra indicatore di caricamento per la risposta del bot
            showLoadingMessage();

            // FASE 2: Richiesta della risposta del chatbot
            const chatFormData = new FormData();
            chatFormData.append('message', message);
            chatFormData.append('emotion', analyzeData.emotion);
            chatFormData.append('environment', analyzeData.environment);

            const chatResponse = await fetch('/get_chat_response', {
                method: 'POST',
                body: chatFormData
            });


            const chatData = await chatResponse.json();

            console.log("Risposta del chatbot:", chatData);

            // Rimuovi l'indicatore di caricamento
            removeLoadingMessage();

            // Aggiorna l'etichetta dell'emozione
            emotionLabel.textContent = getEmotionText(analyzeData.emotion);

            // Aggiungi la risposta del bot alla chat
            addMessage(chatData.response, 'bot', true);

            // Riproduci l'audio se disponibile
            if (chatData.audio_url) {
                checkAndPlayAudio(chatData.audio_url);
            } else {
                responseAudio.style.display = 'none';
            }
        } catch (error) {
            console.error('Errore nell\'invio del messaggio:', error);
            removeLoadingMessage();
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

    // Funzione per aggiornare l'ultimo messaggio dell'utente con emoji
    function updateLastUserMessage(emotion, environment) {
        const userMessages = document.querySelectorAll('.message.user');
        if (userMessages.length > 0) {
            const lastUserMessage = userMessages[userMessages.length - 1];

            // Rimuovi eventuali label esistenti
            const existingLabels = lastUserMessage.querySelector('.message-labels');
            if (existingLabels) {
                existingLabels.remove();
            }

            // Crea container per etichette
            const labelsContainer = document.createElement('div');
            labelsContainer.className = 'message-labels';

            // Aggiungi etichetta emozione
            if (emotion) {
                const emotionInfo = getEmotionInfo(emotion.emotion);
                console.log("Emozione:", emotionInfo);
                const emotionLabel = createLabel(
                    emotionInfo.emoji,
                    emotion.confidence,
                    emotionInfo.text,
                    emotion.probabilities
                );
                labelsContainer.appendChild(emotionLabel);
            }

            // Aggiungi etichetta ambiente
            if (environment) {
                const environmentInfo = getEnvironmentInfo(environment.environment);
                const environmentLabel = createLabel(
                    environmentInfo.emoji,
                    environment.confidence,
                    environmentInfo.text,
                    environment.detections
                );
                labelsContainer.appendChild(environmentLabel);
            }

            lastUserMessage.appendChild(labelsContainer);
        }
    }

    function addMessage(content, sender, showTime = false, emotion = null, environment = null) {
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
            timestamp.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
            messageDiv.appendChild(timestamp);
        }

        console.log("Emotion:", emotion);
        console.log("Environment:", environment);

        // Aggiungi container per le etichette di emozione e ambiente
        if (emotion || environment) {
            const labelsContainer = document.createElement('div');
            labelsContainer.className = 'message-labels';

            // Aggiungi etichetta emozione
            if (emotion) {
                const emotionInfo = getEmotionInfo(emotion.emotion || emotion);
                const emotionLabel = createLabel(
                    emotionInfo.emoji,
                    ((emotion.confidence || 0.5) * 100).toFixed(1) + '%',
                    emotionInfo.text,
                    emotion.probabilities
                );
                labelsContainer.appendChild(emotionLabel);
            }

            // Aggiungi etichetta ambiente
            if (environment) {
                const environmentInfo = getEnvironmentInfo(environment.environment || environment);
                const environmentLabel = createLabel(
                    environmentInfo.emoji,
                    ((environment.confidence || 0.5) * 100).toFixed(1) + '%',
                    environmentInfo.text,
                    environment.detections
                );
                labelsContainer.appendChild(environmentLabel);
            }

            messageDiv.appendChild(labelsContainer);
        }

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function createLabel(emoji, percentage, description, allProbabilities = null) {
        const label = document.createElement('div');
        label.className = 'message-label';

        // Emoji sempre visibile
        const emojiSpan = document.createElement('span');
        emojiSpan.className = 'label-emoji';
        emojiSpan.textContent = emoji;
        label.appendChild(emojiSpan);

        // Contenitore per probabilità (si mostra al passaggio del mouse)
        if (allProbabilities && Object.keys(allProbabilities).length > 0) {
            const detailsDiv = document.createElement('div');
            detailsDiv.className = 'label-details';

            // Titolo con emozione/ambiente principale
            const titleDiv = document.createElement('div');
            titleDiv.className = 'probability-title';
            titleDiv.textContent = `${description}: ${percentage}`;
            detailsDiv.appendChild(titleDiv);

            // Linea divisoria
            const divider = document.createElement('hr');
            detailsDiv.appendChild(divider);

            // Aggiungi tutte le probabilità
            for (const [key, prob] of Object.entries(allProbabilities)) {
                const probItem = document.createElement('div');
                probItem.className = 'probability-item';

                // Ottieni info per ogni chiave
                let itemText = key;
                let itemEmoji = '';

                try {
                    if (description.includes('rabbia') || description.includes('disgusto') || description.includes('paura') || description.includes('felicità') || description.includes('neutro') || description.includes('tristezza')) {
                        // Per emozioni
                        const emotionInfo = getEmotionInfo(key);
                        itemText = emotionInfo.text || key;
                        itemEmoji = emotionInfo.emoji || '';
                    } else {
                        // Per ambienti
                        const envInfo = getEnvironmentInfo(key);
                        itemText = envInfo.text || key;
                        itemEmoji = envInfo.emoji || '';
                    }
                } catch (e) {
                    console.log('Errore nel recuperare info:', key, e);
                }

                // Formatta la riga con emoji, testo e percentuale
                probItem.innerHTML = `<span>${itemEmoji} ${itemText}</span> <b>${(prob * 100).toFixed(1)}%</b>`;
                detailsDiv.appendChild(probItem);
            }

            // Debug
            console.log("Probabilities:", allProbabilities);

            label.appendChild(detailsDiv);
        }

        return label;
    }

    // Funzione per verificare e riprodurre l'audio con polling
    function checkAndPlayAudio(audioUrl) {
        if (!audioUrl) return;

        console.log("URL audio originale:", audioUrl);

        // Sostituisci l'URL completo con un percorso relativo
        const urlParts = audioUrl.split('/');
        const audioId = urlParts[urlParts.length - 1];
        const relativeAudioUrl = `/api/tts/audio/${audioId}`;

        console.log("URL audio convertito in percorso relativo:", relativeAudioUrl);
        responseAudio.style.display = 'none';

        // Mostra animazione di caricamento audio
        const audioContainer = document.getElementById('audio-container') || createAudioContainer();
        audioContainer.innerHTML = '<div class="audio-loading"><i class="fas fa-music"></i><div class="audio-wave"><span></span><span></span><span></span><span></span></div></div>';
        audioContainer.style.display = 'flex';

        // Funzione per verificare lo stato dell'audio
        async function pollAudioStatus() {
            try {
                const response = await fetch(relativeAudioUrl);

                if (response.status === 200) {
                    if (response.headers.get('content-type')?.includes('audio/')) {
                        // Audio pronto, riproduci
                        console.log("Audio pronto, riproduzione in corso");
                        responseAudio.src = relativeAudioUrl;
                        audioContainer.innerHTML = ''; // Rimuovi animazione
                        audioContainer.appendChild(responseAudio);
                        responseAudio.style.display = 'block';
                        responseAudio.play();
                        return true;
                    } else {
                        // Controlla se è in elaborazione o errore
                        const data = await response.json();
                        console.log("Risposta ricevuta:", data);

                        if (data.status === "processing") {
                            console.log("Audio in elaborazione, riprovo tra 1 secondo");
                            setTimeout(pollAudioStatus, 1000);
                            return false;
                        } else if (data.status === "error") {
                            // Gestisci l'errore
                            console.error("Errore dal server:", data.detail || "Errore sconosciuto");
                            audioContainer.innerHTML = '<div class="audio-error"><i class="fas fa-exclamation-circle"></i> Errore nella generazione audio</div>';
                            setTimeout(() => { audioContainer.style.display = 'none'; }, 3000);
                            return false;
                        } else {
                            console.error("Formato di risposta inaspettato:", data);
                            audioContainer.style.display = 'none';
                            return false;
                        }
                    }
                } else {
                    console.error("Errore nella richiesta:", response.status);
                    audioContainer.innerHTML = '<div class="audio-error"><i class="fas fa-exclamation-circle"></i> Errore: ' + response.status + '</div>';
                    setTimeout(() => { audioContainer.style.display = 'none'; }, 3000);
                    return false;
                }
            } catch (error) {
                console.error("Errore durante il controllo dell'audio:", error);
                setTimeout(pollAudioStatus, 2000); // Riprova con un intervallo più lungo in caso di errore
                return false;
            }
        }

        // Avvia il polling
        pollAudioStatus();
    }

    // Funzione per creare il container audio se non esiste
    function createAudioContainer() {
        const container = document.createElement('div');
        container.id = 'audio-container';
        container.style.display = 'none';
        container.style.alignItems = 'center';
        container.style.justifyContent = 'center';
        container.style.margin = '10px 0';

        // Trova dove inserire il container (dopo i messaggi della chat)
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.parentNode.insertBefore(container, chatMessages.nextSibling);

        return container;
    }

    function getEmotionInfo(emotion) {
        // Mappa le emozioni inglesi in italiano con emoji
        const emotionMap = {
            'angry': {text: 'rabbia', emoji: '😠'},
            'disgust': {text: 'disgusto', emoji: '🤢'},
            'fearful': {text: 'paura', emoji: '😨'},
            'happy': {text: 'felicità', emoji: '😊'},
            'neutral': {text: 'neutro', emoji: '😐'},
            'sad': {text: 'tristezza', emoji: '😢'}
        };

        return emotionMap[emotion.toLowerCase()] || {text: 'neutro', emoji: '😐'};
    }

    function getEnvironmentInfo(environment) {
        // Mappa gli ambienti con emoji
        const environmentMap = {
            'Speech': {text: 'Conversazione', emoji: '🗣️'},
            'Inside, small room': {text: 'Stanza piccola', emoji: '🏠'},
            'Inside, large room or hall': {text: 'Stanza grande', emoji: '🏢'},
            'Outside, urban or manmade': {text: 'Ambiente urbano', emoji: '🏙️'},
            'Outside, rural or natural': {text: 'Ambiente naturale', emoji: '🌳'},
            'Vehicle': {text: 'Veicolo', emoji: '🚗'},
            'Music': {text: 'Musica', emoji: '🎵'},
            'Silence': {text: 'Silenzio', emoji: '🔇'},
            'Water': {text: 'Acqua', emoji: '💧'},
            'Wind': {text: 'Vento', emoji: '💨'},
            'Animal': {text: 'Animale', emoji: '🐾'},
            'Noise': {text: 'Rumore', emoji: '📢'}
        };

        return environmentMap[environment] || {text: 'Ambiente sconosciuto', emoji: '❓'};
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