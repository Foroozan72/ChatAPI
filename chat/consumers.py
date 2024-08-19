import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.apps import apps

class ChatConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.username = self.scope['url_route']['kwargs']['username']
        self.group_name = f"chat_{self.username}"

        # Add the channel to the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Remove the channel from the group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        print("Received text data:", text_data)
        if text_data:
            data = json.loads(text_data)
            chatroom_id = data.get('chatroom_id')
            message_type = data.get('message_type')
            content = data.get('content')

            chatroom = await self.get_chatroom(chatroom_id)
            if chatroom:
                message = await self.save_message(chatroom, message_type, content)

                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'chat_message',
                        'message': message.content,
                        'sender': message.sender.username,
                        'message_type': message.message_type
                    }
                )

    

                

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def get_chatroom(self, chatroom_id):
        ChatRoom = apps.get_model('chat', 'ChatRoom')  # Lazy loading the model
        return ChatRoom.objects.filter(id=chatroom_id).first()

    @database_sync_to_async
    def save_message(self, chatroom, message_type, content):
        Message = apps.get_model('chat', 'Message')  # Lazy loading the model
        message = Message.objects.create(
            chatroom=chatroom,
            sender=self.scope["user"],
            message_type=message_type,
            content=content
        )
        return message

# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# from channels.db import database_sync_to_async
# from .models import ChatRoom, Message

# class ChatConsumer(AsyncWebsocketConsumer):
    
#     async def connect(self):
        
#         self.username = self.scope['url_route']['kwargs']['username']
#         self.group_name = f"chat_{self.username}"

#         # Add the channel to the group
#         await self.channel_layer.group_add(
#             self.group_name,
#             self.channel_name
#         )

#         await self.accept()

#     async def disconnect(self, close_code):
#         # Remove the channel from the group
#         await self.channel_layer.group_discard(
#             self.group_name,
#             self.channel_name
#         )

#     async def receive(self, text_data=None, bytes_data=None):
        
#         if text_data:
#             data = json.loads(text_data)
#             chatroom_id = data.get('chatroom_id')
#             message_type = data.get('message_type')
#             content = data.get('content')

#             chatroom = await self.get_chatroom(chatroom_id)
#             if chatroom:
#                 message = await self.save_message(chatroom, message_type, content)

#                 await self.channel_layer.group_send(
#                     self.group_name,
#                     {
#                         'type': 'chat_message',
#                         'message': message.content,
#                         'sender': message.sender.username,
#                         'message_type': message.message_type
#                     }
#                 )

#     async def chat_message(self, event):
#         await self.send(text_data=json.dumps(event))

#     @database_sync_to_async
#     def get_chatroom(self, chatroom_id):
#         return ChatRoom.objects.filter(id=chatroom_id).first()

#     @database_sync_to_async
#     def save_message(self, chatroom, message_type, content):
#         message = Message.objects.create(
#             chatroom=chatroom,
#             sender=self.scope["user"],
#             message_type=message_type,
#             content=content
#         )
#         return message
