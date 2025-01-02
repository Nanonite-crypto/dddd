import ollama
import chromadb
import psycopg
import ast
from colorama import Fore
from tqdm import tqdm
from psycopg.rows import dict_row
import torch
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer
import soundfile as sf
import warnings
from playsound import playsound

client = chromadb.Client()

system_prompt = (
    'You are an AI assistant that has memory of every conversation you have ever had with this user. '
    'On every prompt from the user, the system has checked for any relevant messages you have had with the user. '
    'If any embedded previous conversations are attached, use them for context to responding to the user, '
    'if the context is relevant and useful to responding. If the recalled conversations are irrelevant, '
    'disregard speaking about them and respond normally as an AI assistant. Do not talk about recalling conversations. '
    'Just use any useful data from the previous conversations and respond normally as an intelligent AI assistant.'
)
convo = [{'role': 'system', 'content': system_prompt}]
DB_PARAMS = {
    'dbname': 'memory_agent',
    'user': 'ark',
    'password': 'Nicole',
    'host': 'localhost',
    'port': '5432'
}

torch.manual_seed(42)  # Set a fixed seed for consistent voice

device = "cuda" if torch.cuda.is_available() else "cpu"
torch.backends.cuda.matmul.allow_tf32 = True  # Better performance on Ampere GPUs
torch.backends.cudnn.allow_tf32 = True

tts_model = ParlerTTSForConditionalGeneration.from_pretrained(
    "parler-tts/parler-tts-mini-v1",
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,  # Use FP16 for GPU
    use_flash_attention_2=False  # Changed to False to disable Flash Attention
).to(device)
tts_tokenizer = AutoTokenizer.from_pretrained("parler-tts/parler-tts-mini-v1")

tts_enabled = True

def connect_db():
    conn = psycopg.connect(**DB_PARAMS)
    return conn

def fetch_conversations():
    conn = connect_db()
    with conn.cursor(row_factory=dict_row) as cursor:
        cursor.execute('SELECT * FROM conversations')
        conversations = cursor.fetchall()
    conn.close()
    return conversations

def store_conversations(prompt, response):
    conn = connect_db()
    with conn.cursor() as cursor:
        cursor.execute(
            'INSERT INTO conversations (timestamp, prompt, response) VALUES (CURRENT_TIMESTAMP, %s, %s)',  # Added comma between %s
            (prompt, response)
        )
        conn.commit()
    conn.close()


def remove_last_conversation():
    conn = connect_db()
    with conn.cursor() as cursor:
        cursor.execute('DELETE FROM conversations WHERE id = (SELECT MAX(id) FROM conversations)')
        conn.commit()
    conn.close()

def speak_response(text, description="Mira is a sophisticated British female voice, calm yet witty, with clear, measured enunciation, perfect for a high-tech AI assistant. Her tone is very low, yet cheerful."):
    if not tts_enabled:
        return
        
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with torch.cuda.amp.autocast(enabled=device=="cuda"):  # Automatic mixed precision
            description_tokens = tts_tokenizer(
                description,
                return_tensors="pt",
                padding=True,
                return_attention_mask=True
            ).to(device)
            
            prompt_tokens = tts_tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                return_attention_mask=True
            ).to(device)

            generation = tts_model.generate(
                attention_mask=description_tokens.attention_mask,
                input_ids=description_tokens.input_ids,
                prompt_input_ids=prompt_tokens.input_ids,
                prompt_attention_mask=prompt_tokens.attention_mask
            )
            
        audio_arr = generation.cpu().numpy().squeeze()
        sf.write("response.wav", audio_arr, tts_model.config.sampling_rate)
        playsound("response.wav")

def stream_response(prompt):
    response = ''
    client = ollama.Client(host='http://127.0.0.1:11434')
    stream = client.chat(
        model="llama3.2", 
        messages=convo, 
        stream=True
    )
    print(Fore.LIGHTGREEN_EX + "\nASSISTANT:")

    for chunk in stream:
        content = chunk['message']['content']
        response += content
        print(content, end='', flush=True)
    
    print("\n")
    store_conversations(prompt=prompt, response=response)
    convo.append({'role': 'assistant', 'content': response})
    
    speak_response(response)

def create_vector_db(conversations):
    vector_db_name = 'conversations'

    try:
        client.delete_collection(name=vector_db_name)
    except ValueError:
        pass

    vector_db = client.create_collection(name=vector_db_name)

    ollama_client = ollama.Client(host='http://127.0.0.1:11434')

    for c in conversations:
        serialized_convo = f'prompt: {c['prompt']} response: {c['response']}'
        response = ollama_client.embeddings(model='nomic-embed-text', prompt=serialized_convo)
        embedding = response['embedding']

        vector_db.add(
            ids=[str(c['id'])],
            embeddings=[embedding],
            documents=[serialized_convo]
        )

def retrieve_embeddings(queries, results_per_query=2):
    embeddings = set()
    ollama_client = ollama.Client(host='http://127.0.0.1:11434')
    for query in tqdm(queries, desc='Processing queries to vector database'):
        response = ollama_client.embeddings(model='nomic-embed-text', prompt=query)
        query_embedding = response['embedding']

        vector_db = client.get_collection(name='conversations')
        results = vector_db.query(query_embeddings=[query_embedding], n_results=results_per_query)
        best_embeddings = results['documents'][0]

        for best in best_embeddings:
            if best not in embeddings:
                if 'yes' in classify_embedding(query=query, context=best):
                    embeddings.add(best)

    return embeddings

def create_queries(prompt):
    query_msg = (
        'You are a first principle reasoning search query AI agent. '
        'Your list of search queries will be ran on an embedding database of all your conversations '
        'you have ever had with the user. With the first principles create a Python list of queries to '
        'search the embeddings database for any data that would be necessary to have access to in '
        'order to correctly respond to the prompt. Your response must be a Python list with no syntax errors. '
        'Do not explain anything and do not ever generate anything but a perfect syntax Python list'
    )
    query_convo = [
        {'role': 'system', 'content': query_msg},
        {'role': 'user', 'content': 'Write an email to my car insurance company and create a pursuasive request for them to lower my monthly rate.'},
        {'role': 'assistant', 'content': '["What is the users name?", "What is the users current auto insurance provider?", "What is the monthly rate the user currently pays for auto insurance?"]'},
        {'role': 'user', 'content': 'how can i convert the speak function in my llama3 python voice assistant to use pyttsx3 instead?'},
        {'role': 'assistant', 'content': '["Llama3 voice assistant", "Python voice assistant", "OpenAI TTS", "openai speak"]'},
        {'role': 'user', 'content': prompt}
    ]

    client = ollama.Client(host="http://localhost:11434")
    response = client.chat(
        model="llama3.2",
        messages=query_convo
    )
    print(Fore.YELLOW + f'\nVector database queries: {response["message"]["content"]} \n')

    try:
        queries = ast.literal_eval(response['message']['content'])
        if not isinstance(queries, list):
            return [prompt]  # Fallback if response is not a list
        return queries
    except:
        return [prompt]  # Fallback if parsing fails

def classify_embedding(query, context):
    classify_msg = (
        'You are an embedding classification AI agent. Your input will be a prompt and one embedded chunk of text. '
        'You will not respond as an AI assistant. You only respond "yes" or "no". '
        'Determine wether the context contains data that directly is related to the search query. '
        'If the context is seemingly exactly what the search query needs, respond "yes" if it is anything but directly '
        'related respond "no". Do Not respond "yes" unless the content is highly relevant to the search query.'
    )
    classify_convo = [
        {'role': 'system', 'content': classify_msg},
        {'role': 'user', 'content': f'SEARCH QUERY: What is the users name? \n\nEMBEDDED CONTEXT: You are nbuther. How can I help you?'},
        {'role': 'assistant', 'content': 'yes'},
        {'role': 'user', 'content': f'SEARCH QUERY: Llama3 Python Voice Assistant \n\nEMBEDDED CONTEXT: Siri is a voice assistant on Apple iOS and Mac OS.'},
        {'role': 'assistant', 'content': 'no'},
        {'role': 'user', 'content': f'SEARCH QUERY: {query} \n\nEMBEDDED CONTEXT: {context}'}
    ]

    client = ollama.Client(host='http://127.0.0.1:11434')
    response = client.chat(model="llama3.2", messages=classify_convo)

    return response['message']['content'].strip().lower()

def recall(prompt):
    queries = create_queries(prompt=prompt)
    embeddings = retrieve_embeddings(queries=queries)
    convo.append({'role': 'user', 'content': f'MEMORIES: {embeddings} \n\n USER PROMPT: {prompt}'})
    print(f'\n{len(embeddings)} message:response embeddings added for context.')

conversations = fetch_conversations()
create_vector_db(conversations=conversations)

while True:
    prompt = input(Fore.WHITE + 'USER: \n')
    if prompt[:7].lower() == '/recall':
        prompt = prompt[8:]
        recall(prompt=prompt)
        stream_response(prompt=prompt)
    elif prompt [:7].lower() == '/forget':
        remove_last_conversation()
        convo = convo[:-2]
        print('\n')
    elif prompt[:9].lower() == '/memorize':
        prompt = prompt[10:]
        store_conversations(prompt=prompt, response='Memory stored.')
        print('\n')
    elif prompt[:6].lower() == '/voice':
        tts_enabled = not tts_enabled
        print(f"\nVoice output {'enabled' if tts_enabled else 'disabled'}\n")
    else:
        convo.append({'role':'user', 'content': prompt})
        stream_response(prompt=prompt)
