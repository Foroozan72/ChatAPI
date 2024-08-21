import json
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.files.base import ContentFile
from django.apps import apps
from django.core.exceptions import ValidationError
from pydub import AudioSegment
import redis

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.username = self.scope['url_route']['kwargs']['username']
        self.user = self.scope['user']
        self.chatroom_id = self.scope['url_route']['kwargs'].get('chatroom_id')

        if not self.chatroom_id:
            self.chatroom = await self.create_chatroom()
        else:
            self.chatroom = await self.get_or_create_chatroom()

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None):
        if text_data:
            data = json.loads(text_data)
            content = data.get('content')
            audio_data = data.get('audio_content')
            file_data = data.get('file_content')

            if self.chatroom:
                message = None
                if content:
                    message = await self.save_message(self.chatroom, content)

                if audio_data:
                    try:
                        audio_file = await self.process_audio_file(audio_data)
                        message = await self.save_message(self.chatroom, None, audio_content=audio_file)
                    except ValidationError as e:
                        await self.send_error(str(e))
                        return

                if file_data:
                    try:
                        file_content = await self.save_file(file_data)
                        message = await self.save_message(self.chatroom, None, file_content=file_content)
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
    def create_chatroom(self):
        ChatRoom = apps.get_model('chat', 'ChatRoom')
        other_user = self.get_other_user()
        return ChatRoom.objects.create(user1=self.user, user2=other_user)

    @database_sync_to_async
    def get_or_create_chatroom(self):
        ChatRoom = apps.get_model('chat', 'ChatRoom')
        other_user = self.get_other_user_from_chatroom_id(self.chatroom_id)
        chatroom = ChatRoom.objects.filter(
            user1=self.user, user2=other_user
        ).first() or ChatRoom.objects.filter(
            user1=other_user, user2=self.user
        ).first()

        if not chatroom:
            chatroom = ChatRoom.objects.create(user1=self.user, user2=other_user)

        return chatroom

    @database_sync_to_async
    def get_other_user_from_chatroom_id(self, chatroom_id):
        ChatRoom = apps.get_model('chat', 'ChatRoom')
        chatroom = ChatRoom.objects.get(id=chatroom_id)
        return chatroom.user1 if chatroom.user2 == self.user else chatroom.user2

    @database_sync_to_async
    def get_participants(self, chatroom):
        return [chatroom.user1, chatroom.user2]

    @database_sync_to_async
    def save_message(self, chatroom, content, audio_content=None, file_content=None):
        Message = apps.get_model('chat', 'Message')
        message = Message.objects.create(
            chatroom=chatroom,
            sender=self.user,
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
        output_file = f'audio/audio_{self.user.username}.mp3'
        audio_segment.export(output_file, format='mp3', bitrate='128k')

        return output_file

    @database_sync_to_async
    def save_file(self, file_data):
        format, imgstr = file_data.split(';base64,')
        ext = format.split('/')[-1]
        file_content = ContentFile(base64.b64decode(imgstr), name=f'file_{self.user.username}.{ext}')

        return file_content

    @database_sync_to_async
    def store_message_in_redis(self, message):
        r = redis.Redis(host='127.0.0.1', port=6379, db=0)
        r.lpush(f'chatroom_{self.chatroom_id}', json.dumps({
            'sender': message.sender.username,
            'text_content': message.text_content,
            'audio_url': message.audio_content.url if message.audio_content else None,
            'file_url': message.file_content.url if message.file_content else None,
            'date_sent': message.date_sent.isoformat()
        }))

    async def notify_participants(self, message):
        participants = await self.get_participants(self.chatroom)
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