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


class ChatConsumer(AsyncWebsocketConsumer):

    # async def connect(self):
    #     try:
    #         logging.info("WebSocket connection initiated.")
            
    #         # Retrieve userid from URL
    #         user_id = self.scope['url_route']['kwargs']['userid']
    #         logging.info(f"User ID from URL: {user_id}")
            
    #         # Get User instance from the database
    #         User = get_user_model()
    #         self.user = await database_sync_to_async(User.objects.get)(id=user_id)
    #         logging.info(f"User instance retrieved: {self.user}")

    #         # Determine other user
    #         other_user_id = 1 if user_id == 2 else 2  # Example logic to determine other user
    #         self.other_user = await database_sync_to_async(User.objects.get)(id=other_user_id)
    #         logging.info(f"Other user instance: {self.other_user}")
            
    #         # Create a group name
    #         sorted_usernames = sorted([self.user.username, self.other_user.username])
    #         self.group_name = f"chat_{sorted_usernames[0]}_{sorted_usernames[1]}"
    #         logging.info(f"Group name created: {self.group_name}")
            
    #         # Add the WebSocket to the group
    #         await self.channel_layer.group_add(self.group_name, self.channel_name)
    #         logging.info(f"WebSocket added to group: {self.group_name}")
            
    #         # Accept the WebSocket connection
    #         await self.accept()
    #         logging.info("WebSocket connection accepted successfully.")
        
    #     except Exception as e:
    #         logging.error(f"Error during WebSocket connection: {e}")
    #         await self.close()
#################################################
    async def connect(self):
        try:
            logging.info("WebSocket connection initiated.")
            
            # Retrieve username from URL
            user_name = self.scope['url_route']['kwargs']['username']
            logging.info(f"Username from URL: {user_name}")
            
            # Get User instance from the database
            # User = get_user_model()
            # self.username = await database_sync_to_async(User.objects.get)(username=user_name)
            # print(self.username)
            # logging.info(f"User instance retrieved: {self.username}")
            
            # Determine other user
            # self.other_username = await database_sync_to_async(User.objects.get)(username='arezoo' if user_name == 'foroozan' else 'foroozan')
            # logging.info(f"Other user instance: {self.other_username}")
            
            # Create a group name
            # sorted_usernames = sorted([self.username.username, self.other_username.username])
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

#######################################################################################################################################
    # async def connect(self):
    #     try:
    #         logging.info("WebSocket connection initiated.")
            
    #         # Retrieve user ID from URL
    #         User = get_user_model()
    #         print("user1")
    #         # print(self.scope['url_route'])
    #         user_id = self.scope['url_route']['kwargs']['username']
    #         print(user_id)
    #         logging.info(f"UserId from URL: {user_id}")
            
        
    #         # Determine other user
    #         print("user2")
    #         other_user_id = 1 if user_id == 2 else 2  # Example logic to determine other user
    #         self.other_user = await database_sync_to_async(User.objects.get)(id=other_user_id)
    #         print(self.other_user.id)
    #         logging.info(f"Other user instance: {self.other_user}")
            
    #         # Create a group name
            
    #         self.group_name = "chat_group_name"
    #         logging.info(f"Group name created: {self.group_name}")
            
    #         # Add the WebSocket to the group
    #         await self.channel_layer.group_add(self.group_name, self.channel_name)
    #         logging.info(f"WebSocket added to group: {self.group_name}")
            


    #         await self.accept()
    #         logging.info("WebSocket connection accepted successfully.")
        
    #     except Exception as e:
    #         logging.error(f"Error during WebSocket connection: {e}")
    #         await self.close()


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

        # Optionally, perform any other cleanup tasks here
        # For example, notify other participants about the disconnection if needed.

        logging.info(f"WebSocket connection closed with code: {close_code}")

###############################################################
    # async def disconnect(self, close_code):
    #     try:
    #         # Remove the WebSocket from the group
    #         await self.channel_layer.group_discard(self.group_name, self.channel_name)
    #         logging.info(f"WebSocket disconnected from group: {self.group_name}")

    #     except Exception as e:
    #         logging.error(f"Error during WebSocket disconnection: {e}")

    #     # Optionally, perform any other cleanup tasks here
    #     # For example, notify other participants about the disconnection if needed.

    #     logging.info(f"WebSocket connection closed with code: {close_code}")

    async def receive(self, text_data=None):
        # print(text_data)
        if text_data:
            data = json.loads(text_data)
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

    # @database_sync_to_async
    # def get_or_create_chatroom(self, user_id, other_user_id):
    #     ChatRoom = apps.get_model('chat', 'ChatRoom')

    #     chatroom, created = ChatRoom.objects.get_or_create(
    #         user1=user_id, 
    #         user2_id=other_user_id
    #     )
    #     return chatroom

    # @database_sync_to_async
    # def get_or_create_chatroom(self, user_id, other_user_id):
    #     User = apps.get_model('auth', 'User')
    #     ChatRoom = apps.get_model('chat', 'ChatRoom')

    #     # Fetch User instances
    #     try:
    #         user1 = User.objects.get(id=user_id)
    #         user2 = User.objects.get(id=other_user_id)
    #     except User.DoesNotExist:
    #         raise ValueError("One or both users do not exist")

    #     # Ensure that user1 is always the smaller ID (to handle uniqueness properly)
    #     if user1.id > user2.id:
    #         user1, user2 = user2, user1

    #     # Create or get ChatRoom instance
    #     chatroom, created = ChatRoom.objects.get_or_create(
    #         user1=user1,
    #         user2=user2
    #     )
    #     return chatroom

    @database_sync_to_async   
    def save_message(self, content=None, audio_content=None, file_content=None):
        Message = apps.get_model('chat', 'Message')
        message = Message.objects.create(
            
            sender= "user1", #self.username,
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
        output_file = f'audio/audio_{self.username}.mp3'
        audio_segment.export(output_file, format='mp3', bitrate='128k')

        return output_file

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
            'sender': message.sender,
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
                'sender': message.sender,
                'date_sent': str(message.date_sent)
            }
        )