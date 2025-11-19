from django.db import models

class ChatMessage(models.Model):
    room_name = models.CharField(max_length=255)
    username = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]  

    def __str__(self):
        return f"[{self.room_name}] {self.username}: {self.message[:30]}"
