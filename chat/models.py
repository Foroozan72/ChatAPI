from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
import mimetypes

def validate_audio_file(file):
    allowed_audio_types = ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/aac', 'audio/x-m4a']
    mime_type, _ = mimetypes.guess_type(file.name)
    
    if mime_type not in allowed_audio_types:
        raise ValidationError(f'Unsupported audio file type: {mime_type}. Allowed types are: {", ".join(allowed_audio_types)}')

def validate_file_size(file):
    max_size = 5 * 1024 * 1024  # 5 MB
    if file.size > max_size:
        raise ValidationError('File size must be under 5 MB.')

def validate_file_type(file):
    allowed_mime_types = {
        'application/pdf': 'PDF Document',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word Document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel Spreadsheet',
        'application/vnd.ms-powerpoint': 'PowerPoint Presentation',
        'application/zip': 'ZIP Archive',
        'application/x-rar-compressed': 'RAR Archive',
        'text/plain': 'Text File',
        'image/jpeg': 'JPEG Image',
        'image/png': 'PNG Image',
        'image/gif': 'GIF Image',
        'image/webp': 'WEBP Image',
        'video/mp4': 'MP4 Video',
        'video/x-matroska': 'MKV Video',
        'video/quicktime': 'MOV Video',
        'video/x-msvideo': 'AVI Video',
        'audio/mpeg': 'MP3 Audio',
        'audio/wav': 'WAV Audio',
        'audio/ogg': 'OGG Audio',
        'audio/aac': 'AAC Audio',
        'audio/x-m4a': 'M4A Audio'
    }
    
    mime_type, _ = mimetypes.guess_type(file.name)
    
    if mime_type not in allowed_mime_types:
        raise ValidationError(f'Unsupported file type: {mime_type}. Allowed types are: {", ".join(allowed_mime_types.values())}')



class Message(models.Model):
    # chatroom = models.ForeignKey(ChatRoom, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text_content = models.TextField(blank=True, null=True)
    audio_content = models.FileField(upload_to='audio/', blank=True, null=True, validators=[validate_audio_file, validate_file_size])
    file_content = models.FileField(upload_to='files/', blank=True, null=True, validators=[validate_file_type, validate_file_size])
    date_sent = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date_sent']  

    def __str__(self):
        return f'Message from {self.sender} '
