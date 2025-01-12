import random
from django.core.mail import send_mail
from django.conf import settings

two_factor_code = {}

def generate_a2f_code():
    """Génère un code A2F à 6 chiffres."""
    return str(random.randint(100000, 999999))

def send_email(subject, message, recipient_email):
    try:
        sender = "Transcendence A2F code <noreply@votredomaine.com>"
        send_mail(
            subject,
            message,
            sender,
            [recipient_email],
            fail_silently=False,
        )
        print("E-mail envoyé avec succès à", recipient_email)
    except Exception as e:
        print("Erreur lors de l'envoi de l'e-mail:", e)

def delete_code(recipient_email):
    if recipient_email in two_factor_code:
        del two_factor_code[recipient_email]

def send_test_email(request):
    subject = 'A2F Code'
    a2f_code = generate_a2f_code()
    message = f'Your code: {a2f_code}'
    recipient_email = 'xodproo@gmail.com'
    send_email(subject, message, recipient_email)
    two_factor_code[recipient_email] = a2f_code
