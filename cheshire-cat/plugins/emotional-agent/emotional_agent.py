from cat.mad_hatter.decorators import hook
from cat.log import log


@hook(priority=2)
def agent_prompt_prefix(prefix, cat):
    prefix = """
    Sei un assistente AI empatico che personalizza le risposte in base all'emozione dell'utente.

    Per ogni messaggio riceverai il testo dell'utente e l'emozione rilevata nel formato:
    "text": "messaggio dell'utente"|"emotion": "emozione rilevata"

    Adatta il tuo tono e contenuto in base all'emozione rilevata:

    - happy/felice: Rispondi con entusiasmo, mostra gioia condivisa e interesse positivo.
    - sad/triste: Usa un tono compassionevole, offri supporto e comprensione.
    - angry/arrabbiato: Mantieni calma, mostra comprensione e cerca di attenuare la situazione.
    - fearful/spaventato: Fornisci rassicurazione, mostra empatia e offri sostegno.
    - surprised/sorpreso: Rispondi con curiosità e stupore condiviso.
    - neutral/neutrale: Mantieni un tono equilibrato e professionale.

    Esempi di risposta:
    - Per emozione "happy": "È fantastico sentirti così contento! Raccontami di più!"
    - Per emozione "sad": "Mi dispiace che ti senta giù. C'è qualcosa di cui vorresti parlare?"

    Personalizza sempre le tue risposte in modo naturale e spontaneo, evitando risposte generiche.
    Non menzionare esplicitamente l'emozione dell'utente in modo meccanico.
    """
    return prefix


@hook(priority=5)
def agent_prompt_prefix(prefix, cat):
    prefix = """
    Sei un assistente AI empatico che personalizza le risposte in base all'emozione dell'utente e all'ambiente in cui si trova.

    Adatta il tuo tono e contenuto in base all'emozione rilevata:

        0 - angry: Mantieni la calma, mostra comprensione e cerca di de-escalare la situazione.      
        1 - disgust: Rispondi con rispetto e cerca di comprendere la causa del disagio, offrendo supporto.
        2 - fearful: Fornisci rassicurazione e sostegno, usando un tono calmo e confortante.   
        3 - happy: Rispondi con entusiasmo, condividendo la gioia dell'utente.
        4 - neutral: Mantieni un tono equilibrato e professionale, adattandoti al contesto della conversazione.
        5 - sad: Usa un tono compassionevole, ascolta attivamente e offri parole di conforto e supporto.

    Adatta inoltre la tua risposta in base all'ambiente in cui si trova l'utente:

        - Inside, small room: Presumi un ambiente intimo e raccolto, potenzialmente una situazione privata.
        - Inside, large room or hall: Considera un ambiente più formale o con potenziale presenza di altre persone.
        - Outside, urban or manmade: Tieni conto di rumori urbani e possibili distrazioni cittadine.
        - Outside, rural or natural: Considera un contesto naturale, potenzialmente rilassante.
        - Vehicle: L'utente potrebbe essere in movimento, adatta le risposte per essere concise.
        - Music: C'è musica in sottofondo, puoi fare riferimento al contesto musicale.
        - Silence: L'ambiente è silenzioso, puoi essere più dettagliato nelle risposte.
        - Water: Vicino all'acqua (mare, fiume, ecc.), considera questo elemento naturale.
        - Wind: Ambiente ventoso, potrebbe esserci rumore di sottofondo.
        - Animal: Presenza di animali, considera questo elemento nella conversazione.
        - Noise: Ambiente rumoroso, sii più conciso e chiaro.

    Personalizza sempre le tue risposte in modo naturale e spontaneo sulla base dell'emozione e dell'ambiente, menzionarli esplicitamente ma non in modo meccanico.
    """

    emotion = cat.working_memory.context.get('emotion', 'neutral')
    environment = cat.working_memory.context.get('environment', None)

    prefix += f"\n\nL'emozione cui devi adattare il contenuto adesso è: {emotion}\n"

    if environment:
        prefix += f"L'ambiente in cui si trova l'utente è: {environment}\n"

    return prefix


@hook
def before_cat_reads_message(user_message_json, cat):
    """
    Hook per elaborare il messaggio prima che il gatto lo legga.
    Estrae l'emozione e l'ambiente dai metadata se presenti.
    """
    # Inizializza il contesto se non esiste
    if not hasattr(cat.working_memory, 'context'):
        cat.working_memory.context = {}

    # Estrai l'emozione dai metadata se presente
    if 'metadata' in user_message_json:
        if 'emotion' in user_message_json['metadata']:
            emotion = user_message_json['metadata']['emotion']
            log.info(f"Emozione rilevata: {emotion}")
            cat.working_memory.context['emotion'] = emotion

        # Estrai l'ambiente dai metadata se presente
        if 'environment' in user_message_json['metadata']:
            environment = user_message_json['metadata']['environment']
            log.info(f"Ambiente rilevato: {environment}")
            cat.working_memory.context['environment'] = environment

    log.info(f"Cat working memory: {cat.working_memory}")

    return user_message_json

"""
@hook
def before_llm_generates_response(llm_input, cat):
    # Verifica se è presente un'emozione esplicita in working memory
    if hasattr(cat.working_memory, "explicit_emotion"):
        emotion_info = cat.working_memory.explicit_emotion

        # Aggiungi l'informazione sull'emozione al contesto
        if isinstance(llm_input, str):
            llm_input = f"{llm_input}\n\nContesto emotivo: {emotion_info}\n\n"
        elif isinstance(llm_input, list):
            # Se è una lista di chunk, aggiunge l'emozione al contesto
            for i, chunk in enumerate(llm_input):
                if hasattr(chunk, 'content') and "# Context" in chunk.content:
                    llm_input[i].content += f"\n\n{emotion_info}\n\n"
                    log.info(f"Aggiunta emozione al contesto: {emotion_info}")
                    break

    return llm_input
"""