from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Message
from .serializers import MessageSerializer

# ViewSet для CRUD-операций (через REST-интерфейс)
class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

# Простой эндпоинт-приветствие (для проверки связи)
@api_view(['GET'])
def hello(request):
    return Response({
        'message': 'Привет от Django!',
        'status': 'ok'
    })