from django.contrib import admin
from .models import Message

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'text', 'created_at']  # что показывать в таблице
    search_fields = ['text']                      # поиск по тексту