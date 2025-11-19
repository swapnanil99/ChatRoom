
from django.contrib import admin
from .models import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "room_name", "username", "message", "created_at")
    list_filter = ("room_name", "username")
    search_fields = ("room_name", "username", "message")


admin.site.site_header = "ChatRoom Command Center"
admin.site.site_title = "ChatRoom Admin"
admin.site.index_title = "Realtime Messaging Dashboard"
