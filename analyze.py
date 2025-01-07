import ollama

# Initialize the Ollama client
client = ollama.Client(host='http://127.0.0.1:11434')

# Define the query data
format_d = 'Positive \nConfidence: 67.3 \nWord: love'
query_data = (
    'ONLY REPLY WITH EITHER HARMFUL, POSITIVE OR NEUTRAL WITH A PERCENTAGE OF CONFIDENCE! NOTHING ELSE',
    'DONT EVEN ACKNOWLEDGE ANYTHING ELSE BUT THOSE 3 WORDS. ANALYZE AND COME BACK WITH THE FOLLOWING FORMAT...',
    f'Example: {format_d}',
)

# Join the tuple into a single string
query_data_str = "\n".join(query_data)

# Define the conversation structure for the chat
query_convo = [
    {'role': 'system', 'content': query_data_str},  # Use the joined string here
]

def analyze_input(user_input):
    # Add user input to the conversation
    query_convo.append({'role': 'user', 'content': user_input})

    # Call the Ollama chat model
    response = client.chat(model="mistral", messages=query_convo)

    # Print the entire response for debugging
    print("Full Response:", response)

    # Check if the response is valid and access the content correctly
    if response and 'message' in response:
        analysis = response['message']['content']  # Access the content from the message
        print("Analysis Result:", analysis)
    else:
        print("No valid response from Ollama.")

if __name__ == "__main__":
    while True:
        user_input = input("Enter a message to analyze (or type 'exit' to quit): ")
        if user_input.lower() == 'exit':
            break
        analyze_input(user_input)