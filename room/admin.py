
from django.contrib import admin
from .models import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "room_name", "username", "message", "created_at")
    list_filter = ("room_name", "username")
    search_fields = ("room_name", "username", "message")
