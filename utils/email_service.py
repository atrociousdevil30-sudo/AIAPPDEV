import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import render_template, current_app
from threading import Thread

def send_async_email(app, msg):
    with app.app_context():
        try:
            with smtplib.SMTP(
                current_app.config['MAIL_SERVER'],
                current_app.config['MAIL_PORT']
            ) as server:
                if current_app.config['MAIL_USE_TLS']:
                    server.starttls()
                server.login(
                    current_app.config['MAIL_USERNAME'],
                    current_app.config['MAIL_PASSWORD']
                )
                server.send_message(msg)
        except Exception as e:
            current_app.logger.error(f"Failed to send email: {str(e)}")

def send_email(subject, sender, recipients, text_body, html_body, attachments=None, sync=False):
    """Send an email asynchronously by default"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients) if isinstance(recipients, list) else recipients
    
    # Attach plain text and HTML versions
    part1 = MIMEText(text_body, 'plain')
    part2 = MIMEText(html_body, 'html')
    msg.attach(part1)
    msg.attach(part2)
    
    # Add attachments if any
    if attachments:
        for attachment in attachments:
            with open(attachment['path'], 'rb') as f:
                part = MIMEApplication(f.read(), Name=attachment['filename'])
                part['Content-Disposition'] = f'attachment; filename="{attachment["filename"]}"'
                msg.attach(part)
    
    if sync:
        send_async_email(current_app._get_current_object(), msg)
    else:
        Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

def send_resume_submission_confirmation(recipient_email, candidate_name):
    """Send confirmation email after resume submission"""
    subject = "Thank You for Submitting Your Resume"
    sender = current_app.config['MAIL_DEFAULT_SENDER']
    
    text_body = f"""
    Dear {candidate_name},
    
    Thank you for submitting your resume to SmartHire AI. 
    We have successfully received your application and our team will review it shortly.
    
    Next Steps:
    1. Our AI will analyze your resume
    2. You'll receive an email within 24-48 hours regarding the next steps
    3. If selected, you'll be invited for an AI-powered interview
    
    If you have any questions, please don't hesitate to contact us at {current_app.config['MAIL_DEFAULT_SENDER']}.
    
    Best regards,
    The SmartHire AI Team
    """
    
    html_body = render_template(
        'emails/resume_submission.html',
        candidate_name=candidate_name,
        support_email=current_app.config['MAIL_DEFAULT_SENDER']
    )
    
    send_email(subject, sender, recipient_email, text_body, html_body)

def send_interview_scheduled(recipient_email, candidate_name, interview_date, interview_link):
    """Send interview scheduling confirmation"""
    subject = "Your Interview Has Been Scheduled"
    sender = current_app.config['MAIL_DEFAULT_SENDER']
    
    text_body = f"""
    Dear {candidate_name},
    
    We are pleased to invite you for an interview with our AI-HR representative.
    
    Interview Details:
    Date: {interview_date.strftime('%B %d, %Y')}
    Time: {interview_date.strftime('%I:%M %p')} {current_app.config.get('TIMEZONE', 'UTC')}
    
    Please click the following link to join your interview:
    {interview_link}
    
    Important Notes:
    - The interview will be recorded for evaluation purposes
    - Please ensure you have a stable internet connection
    - Join 5 minutes before the scheduled time
    
    Best regards,
    The SmartHire AI Team
    """
    
    html_body = render_template(
        'emails/interview_scheduled.html',
        candidate_name=candidate_name,
        interview_date=interview_date,
        interview_link=interview_link,
        timezone=current_app.config.get('TIMEZONE', 'UTC')
    )
    
    send_email(subject, sender, recipient_email, text_body, html_body)

def send_interview_followup(recipient_email, candidate_name, next_steps):
    """Send follow-up email after interview"""
    subject = "Thank You for Your Interview"
    
    text_body = f"""
    Dear {candidate_name},
    
    We appreciate you taking the time to interview with us. Your insights and experience were valuable to our team.
    
    Next Steps:
    {next_steps}
    
    Best regards,
    The Hiring Team
    """
    
    html_body = render_template(
        'emails/interview_followup.html',
        candidate_name=candidate_name,
        next_steps=next_steps
    )
    
    send_email(
        subject=subject,
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=recipient_email,
        text_body=text_body,
        html_body=html_body
    )

def send_post_interview_update(recipient_email, candidate_name, position):
    """Send formal communication after interview completion"""
    subject = f"Update Regarding Your Application for {position}"
    
    text_body = f"""
    Dear {candidate_name},
    
    Thank you for completing your interview for the {position} position. We appreciate the time you've taken to participate in our hiring process.
    
    Our team is currently reviewing all candidates, and we will be in touch with you shortly regarding the next steps. A member of our HR team will reach out to you with an update on your application status.
    
    If you have any questions in the meantime, please don't hesitate to contact us.
    
    Best regards,
    The Hiring Team
    """
    
    html_body = render_template(
        'emails/post_interview_update.html',
        candidate_name=candidate_name,
        position=position
    )
    
    send_email(
        subject=subject,
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=recipient_email,
        text_body=text_body,
        html_body=html_body
    )
