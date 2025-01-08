import ollama
import selfcord
import os
import json
import asyncio
import sys
import threading
from colorama import init, Fore, Back, Style
from datetime import datetime
from collections import deque

# Initialize colorama for Windows support
init()

token = os.environ['TOKEN']

# Define the specific guild ID
GUILD_ID = '1163962884049616946'
# Define colors for different elements of your output
INFO_COLOR = Fore.CYAN
ERROR_COLOR = Fore.RED
SUCCESS_COLOR = Fore.GREEN
RESET_COLOR = Style.RESET_ALL

# Initialize the Ollama client
client = ollama.Client(host='http://127.0.0.1:11434')


format_d = 'Positive\nConfidence: 97.3\nWord: love\nReason: Love is beautiful.'

# Define the query data
query_data = (
    'You are tasked with analyzing chat messages to determine their category: HARMFUL, POSITIVE, or NEUTRAL.',
    'Always consider the entire message content for analysis. If no specific word stands out, use the entire message as the "word."',
    'Respond with the category and a confidence percentage. Use the format: Positive\nConfidence: 97.3\nWord: love\nReason: Love is beautiful.',
    'If the message is "test", respond with "Word: test". If the message is a single character or symbol, use it as the "word."',
    'Provide a reason for your analysis. Use Urban Dictionary if needed.',
    'Do not acknowledge anything other than the three categories. Use common sense if the content is not a traditional word.',
    'Analyze the content even if it is not a single word. Use the entire content as "Word/Words" if necessary.'
)

# Join the tuple into a single string
query_data_str = "\n".join(query_data)

class MyClient(selfcord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_queue = asyncio.Queue()  # Queue to hold incoming messages
        self.is_analyzing = asyncio.Event()  # Event to control analysis state
        self.is_analyzing.set()  # Initially, we are ready to analyze

    async def on_ready(self):
        print(f'{INFO_COLOR}Logged in as {self.user} (ID: {self.user.id}){RESET_COLOR}')
        print('------')
        self.current_channel = self.get_channel(1312660237999935580)
        
        if self.current_channel:
            print(f"{INFO_COLOR}DEBUG: Now chatting in #{self.current_channel.name}{RESET_COLOR}")
            await self.print_last_10_messages(self.current_channel)
        else:
            print(f"{ERROR_COLOR}DEBUG: Could not find the specified channel{RESET_COLOR}")
        
        # Start processing messages in the queue
        asyncio.create_task(self.process_message_queue())
        
        input_thread_obj = threading.Thread(target=input_thread, args=(self, [self.current_channel]), daemon=True)
        input_thread_obj.start()

    async def log_message(self, message, action, before=None, getSome=None):
        if message.guild and message.guild.id == int(GUILD_ID):
            # Ignore messages from the specified channel
            if message.channel.id == 1261882179630399489 or message.channel.id == 1163962884829741101:
                return  # Skip logging for this channel
            
            try:
                user_id = '494048155286110208'
                guild = message.guild
                me = guild.me

                user = me.display_name
                if 'afk' in (user).lower() and f'<@{user_id}>' in message.content or f'<@!{user_id}>' in message.content:
                    # Reply when the user is mentioned
                    print("Me = ", user)
                    try:
                        emoji = selfcord.PartialEmoji(name='Clown', id=913436864273338398, animated=True)
                        await message.reply(f'not rn {emoji}')
                    except Exception as e:
                        print("Error:", e)
            except Exception as e:
                print("Error: ", e)
                
            print(f"DEBUG: Adding message to queue: {message.content[:50]}...")  # Truncate for brevity
            await self.message_queue.put((message, action))
        
            # If getSome is provided, return formatted logs for print_last_10_messages
            if getSome:
                return await self._format_log_message(getSome, None, None, getSome)
            else:
                log_message, created_timestamp, edited_timestamp, _ = await self._format_log_message(message, action, before, None)
                return log_message, created_timestamp, edited_timestamp

    async def _format_log_message(self, message, action, before=None, getSome=None):
        log_message = f"#{message.channel.name} | {message.author}: {message.content}\n"
        created_timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        edited_timestamp = message.edited_at.strftime('%Y-%m-%d %H:%M:%S') if message.edited_at else "Never"
        highest_role = "Community"  # default
        if hasattr(message.author, 'roles'):  # Check if it's a Member object
            highest_role = max(message.author.roles, key=lambda r: r.position).name if message.author.roles else "No Role"
        
        if action == "edit" and before:
            log_message += f"Original: {before.content}\n"
        
        return log_message, created_timestamp, edited_timestamp, highest_role
    
    async def analyze_message(self, message):
        user_input = message.content  
        highest_role = "Community"  # default
        if hasattr(message.author, 'roles'):  # Check if it's a Member object
            highest_role = max(message.author.roles, key=lambda r: r.position).name if message.author.roles else "No Role"
        query_convo = [
            {'role': 'system', 'content': query_data_str},
            {'role': 'tool', 'content': f"{highest_role} | {message.author.name}:"},
            {'role': 'user', 'content': f"CONTENT FROM THE USER THAT YOU MUST ANALYSE:\n {user_input}"}
        ]
        return await asyncio.to_thread(client.chat, model="llama3.2:1b", messages=query_convo)

    async def process_message_queue(self):
        while True:
            message, action = await self.message_queue.get()
            if message is None:
                break  # Exit if None is received (for graceful shutdown)

            # Here, log or analyze the message as needed
            log_message, created_timestamp, edited_timestamp, highest_role = await self._format_log_message(message, action)
            log_entry = f"""
    ¤: {highest_role}\n" (User ID: {message.author.id})
        {action}: Created at {created_timestamp}, Edited at {edited_timestamp}
        ${log_message}\n"""
            
            # Print or log this to console or file
            print(log_entry)  # For debugging, comment out or log to file in production
            with open('log.txt', 'a', encoding='utf-8') as f:
                f.write(log_entry)


            # Now perform analysis
            self.is_analyzing.clear()
            try:
                response = await self.analyze_message(message)
                #print("DEBUG:",response)
                if response and 'message' in response:
                    analysis = response['message']['content']
                    # Here you might want to log or handle this analysis result instead of printing
                    #For now, I'll comment out the print statements:
                    print(f"https://discord.com/channels/{GUILD_ID}/{message.channel.id}/{message.id}")
                    print("Analysis of: ", log_entry)
                    print("Analysis Result:", analysis)
                else:
                    print("No valid response from Ollama.")
                    pass
            except Exception as e:
                print("Error during analysis:", e)
                pass
            finally:
                self.is_analyzing.set()

    async def fetch_message_info(self, message):
        """Fetches and returns message information without logging."""
        created_timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        edited_timestamp = message.edited_at.strftime('%Y-%m-%d %H:%M:%S') if message.edited_at else "Never"
        highest_role = "No Role"  # default
        if hasattr(message.author, 'roles'):  # Check if it's a Member object
            highest_role = max(message.author.roles, key=lambda r: r.position).name if message.author.roles else "No Role"
        
        return {
            "log_message": f"#{message.channel.name} | {message.author}: {message.content}\n",
            "created_timestamp": created_timestamp,
            "edited_timestamp": edited_timestamp,
            "highest_role": highest_role
        }

    async def print_last_10_messages(self, channel):
        print(f"{INFO_COLOR}Fetching last 10 messages from channel: {channel.name}{RESET_COLOR}")  # Debug statement
        try:
            msgs = []  # Initialize a list to collect messages
            async for msg in channel.history(limit=10):
                print("DEBUG: ", msg.author)
                info = await self.fetch_message_info(msg)
                msgs.append(f"""
¤: {info['highest_role']} 
(User ID: {msg.author.id})
    History: Created at {info['created_timestamp']}, Edited at {info['edited_timestamp']}
    ${info['log_message']}\n""")  # Collect messages

            print("\n--- Context of Last 10 Messages ---")
            msgs.reverse()

            for msg in msgs:  # Reverse the order of messages
                print(f"{INFO_COLOR}{msg}{RESET_COLOR}")  # Print each message in reverse order
        except Exception as e:
            print(f"{ERROR_COLOR}Error fetching messages: {e}{RESET_COLOR}")  # Print any errors that occur

    async def on_message(self, message):
        await self.log_message(message, "receive")

    async def on_message_edit(self, before, after):
        await self.log_message(after, "edit", before)

def input_thread(client, current_channel):
    pending_message = ""
    
    while True:
        # This will create a blinking cursor effect
        sys.stdout.write("\r> ")
        sys.stdout.flush()
        # Wait for input without blocking the event loop
        user_input = input()
        
        if user_input.startswith('/channel '):
            channel_id = user_input.split(' ', 1)[1]
            try:
                channel = client.get_channel(int(channel_id))
                if channel and channel.guild.id == int(GUILD_ID):
                    current_channel[0] = channel
                    print(f"\rNow chatting in #{channel.name}")
                    asyncio.run_coroutine_threadsafe(client.print_last_10_messages(channel), client.loop)  # Print last 10 messages on channel change
                else:
                    print(f"\r{ERROR_COLOR}Invalid channel ID or not in guild {GUILD_ID}{RESET_COLOR}")
            except ValueError:
                print(f"\r{ERROR_COLOR}Invalid channel ID format{RESET_COLOR}")
            continue

        if user_input.startswith('/afk'):
            try:
                guild = client.get_guild(int(GUILD_ID))
                if guild:
                    me = guild.me
                    new_nickname = "KS [AFK]" if "AFK" not in me.display_name else "KS"
                    asyncio.run_coroutine_threadsafe(me.edit(nick=new_nickname), client.loop)  # Update nickname
                    print(f"\r{SUCCESS_COLOR}Nickname updated to {new_nickname}{RESET_COLOR}")
                else:
                    print(f"\r{ERROR_COLOR}Could not find the guild with ID {GUILD_ID}{RESET_COLOR}")
            except Exception as e:
                print(f"\r{ERROR_COLOR}Error updating nickname: {e}{RESET_COLOR}")
        
        if user_input:  # Only proceed if input is not empty
            if user_input.upper() == "YES" and pending_message:
                if current_channel[0]:
                    asyncio.run_coroutine_threadsafe(current_channel[0].send(pending_message), client.loop)
                    pending_message = ""
                else:
                    print(f"\r{ERROR_COLOR}No channel selected to send message{RESET_COLOR}")
            else:
                if pending_message:  # If there was a pending message and user didn't confirm
                    print(f"\r{ERROR_COLOR}Message ignored: {pending_message}{RESET_COLOR}")
                
                # Ask for confirmation
                pending_message = user_input
                sys.stdout.write(f"\rAre you sure? (Type 'YES' to confirm or anything else to cancel): {pending_message}\n> ")
                sys.stdout.flush()
        else:
            # Reset the cursor to the beginning of the line without creating a newline
            sys.stdout.write("\r")
            sys.stdout.flush()

async def main():
    client = MyClient()
    await client.start(token)

if __name__ == "__main__":
    asyncio.run(main())