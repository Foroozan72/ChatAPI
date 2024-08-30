from django.contrib.auth import get_user_model
import json
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.files.base import ContentFile
from django.apps import apps
from django.core.exceptions import ValidationError
from pydub import AudioSegment
import redis
import logging
from pydub.exceptions import PydubException



# {
#     "audio_content":"data:audio/wav;base64,<base64_encoded_audio_data_here>"
# }

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        try:
            logging.info("WebSocket connection initiated.")
            
            # Retrieve username from URL
            user_name = self.scope['url_route']['kwargs']['username']
            logging.info(f"Username from URL: {user_name}")
            
            self.group_name = f"chat_group_name"
            logging.info(f"Group name created: {self.group_name}")
            
            # Add the WebSocket to the group
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            logging.info(f"WebSocket added to group: {self.group_name}")
            
            # Accept the WebSocket connection (this is where the handshake completes)
            await self.accept()
            logging.info("WebSocket connection accepted successfully.")
        
        except Exception as e:
            logging.error(f"Error during WebSocket connection: {e}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            # Ensure self.group_name is defined before trying to discard the group
            if hasattr(self, 'group_name'):
                # Remove the WebSocket from the group
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
                logging.info(f"WebSocket disconnected from group: {self.group_name}")
            else:
                logging.warning("group_name was not set; skipping group discard.")

        except Exception as e:
            logging.error(f"Error during WebSocket disconnection: {e}")

        logging.info(f"WebSocket connection closed with code: {close_code}")

    async def receive(self, text_data=None):

        # print(text_data)
        if text_data:
            data = json.loads(text_data)
            print(data)
            content = data.get('content')
            audio_data = data.get('audio_content')
            file_data = data.get('file_content')

            message = None
            if content:
                print(content)
                message = await self.save_message(content)
                print(message)

            if audio_data:
                try:
                    audio_file = await self.process_audio_file(audio_data)
                    message = await self.save_message(None, audio_content=audio_file)
                except ValidationError as e:
                    await self.send_error(str(e))
                    return

            if file_data:
                try:
                    file_content = await self.save_file(file_data)
                    message = await self.save_message(None, file_content=file_content)
                except ValidationError as e:
                    await self.send_error(str(e))
                    return

            if message:
                await self.store_message_in_redis(message)
                await self.notify_participants(message)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def send_error(self, error_message):
        await self.send(json.dumps({'error': error_message}))

    @database_sync_to_async   
    def save_message(self, content=None, audio_content=None, file_content=None):
        User = get_user_model()
        user = User.objects.first()

        Message = apps.get_model('chat', 'Message')
        message = Message.objects.create(
            
            sender= user, #self.username,
            text_content=content,
            audio_content=audio_content,
            file_content=file_content
        )
        return message


    @database_sync_to_async
    def process_audio_file(self, audio_data):
        try:
            if ';base64,' not in audio_data:
                raise ValueError("Invalid audio data format")

            # Split the audio_data to get the base64 encoded part
            format, imgstr = audio_data.split(';base64,', 1)
            ext = format.split('/')[-1]

            # Add padding if needed
            missing_padding = len(imgstr) % 4
            if missing_padding:
                imgstr += '=' * (4 - missing_padding)

            # Decode the base64 data
            audio_bytes = base64.b64decode(imgstr)

            # Use ContentFile to handle the in-memory audio file
            audio_file = ContentFile(audio_bytes, name=f'audio.{ext}')

            # Load and process the audio file using pydub
            audio_segment = AudioSegment.from_file(audio_file)

            # Define output file path
            output_file = f'audio/audio_{self.username}.mp3'

            # Export the audio segment as an MP3 file
            audio_segment.export(output_file, format='mp3', bitrate='128k')

            return output_file

        except (ValueError, PydubException) as e:
            # Log or handle specific errors
            self.send_error(str(e))
            return None

    @database_sync_to_async
    def save_file(self, file_data):
        format, imgstr = file_data.split(';base64,')
        ext = format.split('/')[-1]
        file_content = ContentFile(base64.b64decode(imgstr), name=f'file_{self.username}.{ext}')

        return file_content

    @database_sync_to_async
    def store_message_in_redis(self, message):
        r = redis.Redis(host='127.0.0.1', port=6379, db=0)
        r.lpush(f'chat_{self.group_name}', json.dumps({
            'sender': message.sender.id,
            'text_content': message.text_content,
            'audio_url': message.audio_content.url if message.audio_content else None,
            'file_url': message.file_content.url if message.file_content else None,
            'date_sent': str(message.date_sent)
        }))

    async def notify_participants(self, message):
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'message': message.text_content,
                'sender': message.sender.id,
                'date_sent': str(message.date_sent)
            }
        )


        # from django.contrib.auth import get_user_model
        # User = get_user_model()
        # print(User)

        # current_user = self.scope["user"]
        # print(current_user.username)
        # print(current_user)