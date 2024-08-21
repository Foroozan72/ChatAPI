from django.contrib import admin
from .models import ChatRoom, Message 

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('user1', 'user2', 'created_at')
    search_fields = ('user1__username', 'user2__username')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'chatroom', 'date_sent', 'text_content')
    list_filter = ('chatroom', 'sender')
    search_fields = ('sender__username', 'text_content')
    ordering = ('date_sent',)

