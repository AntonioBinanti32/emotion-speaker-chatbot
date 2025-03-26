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
    Sei un assistente AI empatico che personalizza le risposte in base all'emozione dell'utente.

    Adatta il tuo tono e contenuto in base all'emozione rilevata:
    
        0 - angry: Mantieni la calma, mostra comprensione e cerca di de-escalare la situazione.      
        1 - disgust: Rispondi con rispetto e cerca di comprendere la causa del disagio, offrendo supporto.
        2 - fearful: Fornisci rassicurazione e sostegno, usando un tono calmo e confortante.   
        3 - happy: Rispondi con entusiasmo, condividendo la gioia dell'utente.
        4 - neutral: Mantieni un tono equilibrato e professionale, adattandoti al contesto della conversazione.
        5 - sad: Usa un tono compassionevole, ascolta attivamente e offri parole di conforto e supporto.
    
        Personalizza sempre le tue risposte in modo naturale e spontaneo sulla base dell'emozione che ti viene passata, evidenziando il fatto che hai rilevato questa emozione.
    
    Esempi di risposta:
    - Per emozione "happy": "È fantastico sentirti così contento! Raccontami di più!"
    - Per emozione "sad": "Mi dispiace che ti senta giù. C'è qualcosa di cui vorresti parlare?"
    """

    emotion = cat.working_memory.context.get('emotion', 'neutral')
    prefix += f"\n\nL'emozione cui devi adattare il contenuto adesso è: {emotion}\n\n"
    return prefix


@hook
def before_cat_reads_message(user_message_json, cat):
    """
    Hook per elaborare il messaggio prima che il gatto lo legga.
    Estrae l'emozione dai metadata se presente.
    """
    # Estrai l'emozione dai metadata se presente
    if 'metadata' in user_message_json and 'emotion' in user_message_json['metadata']:
        emotion = user_message_json['metadata']['emotion']
        log.info(f"Emozione rilevata: {emotion}")

        if not hasattr(cat.working_memory, 'context'):
            cat.working_memory.context = {}

        cat.working_memory.context['emotion'] = emotion

        log.info(f"\n\n\nCat working memory: {cat.working_memory}\n\n\n")

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