# pong/templatetags/tournament_tags.py
from django import template

register = template.Library()

@register.simple_tag
def tournament_display_name(tournament, user):
    """
    Renvoie l'alias choisi pour le tournoi si défini, sinon le username.
    """
    participation = tournament.participations.filter(player=user).first()
    if participation and participation.tournament_alias:
        return participation.tournament_alias
    return user.username
