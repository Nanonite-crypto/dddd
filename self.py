import selfcord
import os
import json
import asyncio
import sys
import threading
from colorama import init, Fore
from datetime import datetime
from collections import deque

# Initialize colorama for Windows
init()

token = os.environ['TOKEN']

# Define the specific guild ID
GUILD_ID = '1163962884049616946'

class MyClient(selfcord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_history = deque(maxlen=10)  # Keep last 10 messages

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
        # Set the default channel here after the client is ready
        self.current_channel = self.get_channel(1312660237999935580)

        if self.current_channel:
            print(f"DEBUG: Now chatting in #{self.current_channel.name}")
            await self.print_last_10_messages(self.current_channel)  # Print last 10 messages on startup
        else:
            print("DEBUG: Could not find the specified channel")
        
        # Start the input thread after setting the channel
        input_thread_obj = threading.Thread(target=input_thread, args=(self, [self.current_channel]), daemon=True)
        input_thread_obj.start()

    
    async def log_message(self, message, action, before=None, getSome=None):

        if getSome:
            log_message = f"#{getSome.channel.name} | {getSome.author}: {getSome.content}\n"

            for attachment in getSome.attachments:
                if attachment.content_type:
                    if attachment.content_type.startswith('image/'):
                        log_message += f"Image Link (Attachment): {attachment.url}\n"
                    elif attachment.content_type.startswith('video/'):
                        log_message += f"Video Link (Attachment): {attachment.url}\n"
            
            if getSome.embeds:
                for embed in getSome.embeds:
                    embed_json = json.dumps(embed.to_dict(), indent=2)
                    log_message += f"Embed:\n{embed_json}\n"

            created_timestamp = getSome.created_at.strftime('%Y-%m-%d %H:%M:%S')
            edited_timestamp = getSome.edited_at.strftime('%Y-%m-%d %H:%M:%S') if getSome.edited_at else "Never"


            return log_message, created_timestamp, edited_timestamp
        
        # Check if the message is from the specific guild
        if message.guild and message.guild.id == int(GUILD_ID):
            highest_role = max(message.author.roles, key=lambda r: r.position)
            log_message = f"#{message.channel.name} | {message.author}: {message.content}\n"

            for attachment in message.attachments:
                if attachment.content_type:
                    if attachment.content_type.startswith('image/'):
                        log_message += f"Image Link (Attachment): {attachment.url}\n"
                    elif attachment.content_type.startswith('video/'):
                        log_message += f"Video Link (Attachment): {attachment.url}\n"
            
            if message.embeds:
                for embed in message.embeds:
                    embed_json = json.dumps(embed.to_dict(), indent=2)
                    log_message += f"Embed:\n{embed_json}\n"
            
            created_timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
            edited_timestamp = message.edited_at.strftime('%Y-%m-%d %H:%M:%S') if message.edited_at else "Never"
            
            if action == "Edited" and before:
                log_message += f"Original: {before.content}\n"

            # Now log the current message entry
            log_entry = f"""
¤: {highest_role.name}\n" (User ID: {message.author.id})
    {action}: Created at {created_timestamp}, Edited at {edited_timestamp}
    ${log_message}\n"""

            # Print the current log entry
            print(log_entry)

            with open('log.txt', 'a', encoding='utf-8') as f:
                f.write(log_entry)

            try:

                user_id = '494048155286110208'
                guild = message.guild
                me = guild.me

                user = me.display_name
                print("Me = ", user)
                if 'afk' in (user).lower() and f'<@{user_id}>' in message.content or f'<@!{user_id}>' in message.content:
                    # Reply when the user is mentioned
                    try:
                        emoji = selfcord.PartialEmoji(name='Clown', id=913436864273338398, animated=True)
                        await message.reply(f'not rn {emoji}')
                    except Exception as e:
                        print("Error:", e)
            except Exception as e:
                print("Error: ", e)
            

    async def print_last_10_messages(self, channel):
        print(f"Fetching last 10 messages from channel: {channel.name}")  # Debug statement
        try:
            messages = []  # List to hold messages
            async for msg in channel.history(limit=10):
                print("DEBUG: ", msg.author)
                log_message, created_timestamp, edited_timestamp = await self.log_message(msg, None, before=None, getSome=msg)
                messages.append(f"""
¤: |****| \n (User ID: {msg.author.id})
    History: Created at {created_timestamp}, Edited at {edited_timestamp}
    ${log_message}\n""")  # Collect messages

            print("\n--- Context of Last 10 Messages ---")
            messages.reverse()

            for msg in messages:  # Reverse the order of messages
                print(msg)  # Print each message in reverse order
        except Exception as e:
            print(f"Error fetching messages: {e}")  # Print any errors that occur

    async def on_message(self, message):
        await self.log_message(message, "New")

    async def on_message_edit(self, before, after):
        await self.log_message(after, "Edited", before)


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
                    print(f"\r{Fore.RED}Invalid channel ID or not in guild {GUILD_ID}{Fore.RESET}")
            except ValueError:
                print(f"\r{Fore.RED}Invalid channel ID format{Fore.RESET}")
            continue

        if user_input.startswith('/afk'):
            try:
                guild = client.get_guild(int(GUILD_ID))
                if guild:
                    me = guild.me
                    new_nickname = "KS [AFK]" if "AFK" not in me.display_name else "KS"
                    
                    # Use `await` instead of `asyncio.run_coroutine_threadsafe` 
                    # but you'll need to make `input_thread` async or use a different approach
                    asyncio.run_coroutine_threadsafe(me.edit(nick=new_nickname), client.loop) # This won't work directly in your thread context
                    print(f"\rNickname updated to {new_nickname}")
                else:
                    print(f"\r{Fore.RED}Could not find the guild with ID {GUILD_ID}{Fore.RESET}")
            except Exception as e:
                print(f"\r{Fore.RED}Error updating nickname: {e}{Fore.RESET}")
        
        if user_input:  # Only proceed if input is not empty
            if user_input.upper() == "YES" and pending_message:
                if current_channel[0]:
                    asyncio.run_coroutine_threadsafe(current_channel[0].send(pending_message), client.loop)
                    pending_message = ""
                else:
                    print(f"\r{Fore.RED}No channel selected to send message{Fore.RESET}")
            else:
                if pending_message:  # If there was a pending message and user didn't confirm
                    print(f"\r{Fore.RED}Message ignored: {pending_message}{Fore.RESET}")
                
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