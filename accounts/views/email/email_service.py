# utils/email_service.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_contribution_success_email(to_email, contributor_name, chapter_title):
    subject = f"🎉 Your contribution for {chapter_title} was submitted!"
    html_message = render_to_string("emails/contribution_success.html", {
        "name": contributor_name,
        "chapter": chapter_title,
    })
    plain_message = strip_tags(html_message)
    from_email = None  # uses DEFAULT_FROM_EMAIL from settings

    send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)
