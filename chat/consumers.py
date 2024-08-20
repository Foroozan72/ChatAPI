import json
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.files.base import ContentFile
from django.apps import apps
from django.core.exceptions import ValidationError
from pydub import AudioSegment
import os

class ChatConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.username = self.scope['url_route']['kwargs']['username']
        self.chatroom_id = self.scope['url_route']['kwargs']['chatroom_id']
        self.group_name = f"chat_{self.chatroom_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None):
        if text_data:
            data = json.loads(text_data)
            chatroom_id = data.get('chatroom_id')
            content = data.get('content')  
            audio_data = data.get('audio_content') 
            file_data = data.get('file_content')  

            chatroom = await self.get_chatroom(chatroom_id)
            if chatroom:
                
                if content:
                    message = await self.save_message(chatroom, content)

                
                if audio_data:
                    try:
                        audio_file = await self.process_audio_file(audio_data)
                        message = await self.save_message(chatroom, None, audio_content=audio_file)
                    except ValidationError as e:
                        await self.send(json.dumps({'error': str(e)}))
                        return

                if file_data:
                    try:
                        file_content = await self.save_file(file_data)
                        message = await self.save_message(chatroom, None, file_content=file_content)
                    except ValidationError as e:
                        await self.send(json.dumps({'error': str(e)}))
                        return

                participants = await self.get_participants(chatroom)
                for participant in participants:
                    participant_group_name = f"chat_{participant.username}"

                    await self.channel_layer.group_send(
                        participant_group_name,
                        {
                            'type': 'chat_message',
                            'message': message.text_content,
                            'audio_url': message.audio_content.url if message.audio_content else None,
                            'file_url': message.file_content.url if message.file_content else None,
                            'sender': message.sender.username,
                            'date_sent': message.date_sent.isoformat()  
                        }
                    )

    async def chat_message(self, event):
        event['message']['date_sent'] = event['message']['date_sent'].isoformat()
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_chatroom(self, chatroom_id):
        ChatRoom = apps.get_model('chat', 'ChatRoom')
        return ChatRoom.objects.filter(id=chatroom_id).first()

    @database_sync_to_async
    def get_participants(self, chatroom):
        return [chatroom.user1, chatroom.user2]  

    @database_sync_to_async
    def save_message(self, chatroom, content, audio_content=None, file_content=None):
        Message = apps.get_model('chat', 'Message')
        message = Message.objects.create(
            chatroom=chatroom,
            sender=self.scope["user"],
            text_content=content,
            audio_content=audio_content,
            file_content=file_content
        )
        return message

    @database_sync_to_async
    def process_audio_file(self, audio_data):
        format, imgstr = audio_data.split(';base64,')
        ext = format.split('/')[-1]
        audio_file = ContentFile(base64.b64decode(imgstr), name=f'audio.{ext}')

        audio_segment = AudioSegment.from_file(audio_file)
        output_file = f'audio/audio_{self.scope["user"].username}.mp3'
        audio_segment.export(output_file, format='mp3', bitrate='128k')

        return output_file

    @database_sync_to_async
    def save_file(self, file_data):
        format, imgstr = file_data.split(';base64,')
        ext = format.split('/')[-1]
        file_content = ContentFile(base64.b64decode(imgstr), name=f'file_{self.scope["user"].username}.{ext}')
        
        return file_content