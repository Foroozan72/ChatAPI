from django.contrib import admin
from .models import  Message 

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'date_sent', 'text_content')
    list_filter = ( 'sender',)
    search_fields = ('sender__username', 'text_content')
    ordering = ('date_sent',)

