#friend_views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from pong.models import CustomUser, FriendRequest
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_friend_request(request, username):
    current_user = request.user
    target_user = get_object_or_404(CustomUser, username=username)
    if target_user == current_user:
        return Response({"message": "Vous ne pouvez pas vous envoyer une demande."}, status=status.HTTP_400_BAD_REQUEST)
    if FriendRequest.objects.filter(sender=current_user, receiver=target_user).exists():
        return Response({"message": "Demande déjà envoyée."}, status=status.HTTP_400_BAD_REQUEST)
    FriendRequest.objects.create(sender=current_user, receiver=target_user, status='pending')
    return Response({"message": "Demande envoyée avec succès."}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_friend_request(request, request_id):
    current_user = request.user
    friend_request = FriendRequest.objects.filter(sender=current_user, id=request_id, status='pending').first()
    if friend_request:
        friend_request.delete()
        return Response({"message": "Demande annulée."}, status=status.HTTP_200_OK)
    return Response({"message": "Aucune demande trouvée à annuler."}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_friend_request(request, request_id):
    current_user = request.user
    friend_request = FriendRequest.objects.filter(receiver=current_user, id=request_id, status='pending').first()
    if friend_request:
        friend_request.status = 'accepted'
        friend_request.save()
        sender = friend_request.sender
        current_user.friends.add(sender)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{sender.id}",
            {
                "type": "user_list",
                "username": current_user.username,
                "action": "added"
            }
        )
        async_to_sync(channel_layer.group_send)(
            f"user_{current_user.id}",
            {
                "type": "user_list",
                "username": sender.username,
                "action": "added"
            }
        )
        async_to_sync(channel_layer.group_send)(
            "chat_room",
            {"type": "broadcast_user_list"}
        )

        return Response({"message": "Demande acceptée."}, status=status.HTTP_200_OK)
    return Response({"message": "Aucune demande à accepter trouvée."}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decline_friend_request(request, request_id):
    current_user = request.user
    friend_request = FriendRequest.objects.filter(receiver=current_user, id=request_id, status='pending').first()
    if friend_request:
        friend_request.status = 'declined'
        friend_request.save()
        return Response({"message": "Demande refusée."}, status=status.HTTP_200_OK)
    return Response({"message": "Aucune demande à refuser trouvée."}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_friend(request, username):
    current_user = request.user
    friend_to_remove = get_object_or_404(CustomUser, username=username)
    
    if friend_to_remove not in current_user.friends.all():
        print(f"[DEBUG] ❌ {current_user.username} et {friend_to_remove.username} ne sont PAS amis en BDD.")
        return Response({"message": "Cet utilisateur n'est pas dans votre liste d'amis."}, status=status.HTTP_400_BAD_REQUEST)
    
    current_user.friends.remove(friend_to_remove)

    FriendRequest.objects.filter(sender=current_user, receiver=friend_to_remove).delete()
    FriendRequest.objects.filter(sender=friend_to_remove, receiver=current_user).delete()

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{friend_to_remove.id}",
        {
            "type": "user_list",
            "username": current_user.username,
            "action": "removed"
        }
    )
    async_to_sync(channel_layer.group_send)(
        f"user_{current_user.id}",
        {
            "type": "user_list",
            "username": friend_to_remove.username,
            "action": "removed"
        }
    )

    async_to_sync(channel_layer.group_send)(
        "chat_room",
        {"type": "broadcast_user_list"}
    )

    return Response({"message": "Ami supprimé."}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_friendship_status(request, username):
    current_user = request.user
    target_user = get_object_or_404(CustomUser, username=username)
    data = {
        "is_friend": False,
        "request_sent": False,
        "request_received": False,
        "friend_request_id": None,
    }
    pending_demand = FriendRequest.objects.filter(sender=current_user, receiver=target_user, status='pending').first()
    target_pending_demand = FriendRequest.objects.filter(sender=target_user, receiver=current_user, status='pending').first()
    if target_user in current_user.friends.all():
        data["is_friend"] = True
    else:
        if pending_demand:
            data["request_sent"] = True
            data["friend_request_id"] = pending_demand.id
        elif target_pending_demand:
            data["request_received"] = True
            data["friend_request_id"] = target_pending_demand.id 
    return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def received_friend_requests(request):
    current_user = request.user

    received_requests = FriendRequest.objects.filter(receiver=current_user, status='pending')
    data = [
        {
            "id": fr.id,
            "sender_username": fr.sender.username,
        }
        for fr in received_requests
    ]
    return Response(data, status=status.HTTP_200_OK)
