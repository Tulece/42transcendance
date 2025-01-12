# views.py
from django.core.mail import send_mail
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render

# Ajoutez les paramètres de configuration SMTP pour Gmail directement ici (en production, vous devriez plutôt les mettre dans settings.py ou utiliser des variables d'environnement pour plus de sécurité)

settings.configure(
    EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
    EMAIL_HOST='smtp.gmail.com',
    EMAIL_PORT=587,
    EMAIL_USE_TLS=True,
    EMAIL_HOST_USER='42transcendencemailer@gmail.com',
    EMAIL_HOST_PASSWORD='Hackbyme123$$$',
)

def send_email(subject, message, recipient_email):
    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER, # requete db for user email
            [recipient_email],
            fail_silently=False,
        )
        print("E-mail envoyé avec succès à", recipient_email)
    except Exception as e:
        print("Erreur lors de l'envoi de l'e-mail:", e)

def send_test_email(request):
    subject = 'Test Email'
    message = 'Ceci est un e-mail de test.'
    recipient_email = 'xodproo@gmail.com' # test mail
    send_email(subject, message, recipient_email)
    return HttpResponse("E-mail envoyé avec succès.")
