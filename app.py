import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import re
import openai
import json
import requests  # Added requests library
from dotenv import load_dotenv  # Added to load environment variables

# Load environment variables from .env file
load_dotenv()

# Configure your OpenAI API key
openai.api_key = os.environ.get('OPENAI_API_KEY')

EMAIL_ACCOUNT = os.environ.get('EMAIL_ACCOUNT')
PASSWORD = os.environ.get('EMAIL_PASSWORD')

IMAP_SERVER = os.environ.get('IMAP_SERVER')
IMAP_PORT = int(os.environ.get('IMAP_PORT', 993))
SMTP_SERVER = os.environ.get('SMTP_SERVER')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))

PROGRESS_THRESHOLD = float(os.environ.get('PROGRESS_THRESHOLD', 0.8))  # Escalation threshold

# GitLab configuration
GITLAB_TOKEN = os.environ.get('GITLAB_TOKEN')
GITLAB_PROJECT_ID = os.environ.get('GITLAB_PROJECT_ID')
# Use environment variable or default value
GITLAB_BASE_URL = os.environ.get('GITLAB_BASE_URL')
GITLAB_URL = f'{GITLAB_BASE_URL}/api/v4/projects/{GITLAB_PROJECT_ID}/issues'

WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL')

processed_emails = []

def connect_imap():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, PASSWORD)
    mail.select('inbox')
    return mail

def extract_email_address(from_header):
    email_address = re.findall(r'<(.+?)>', from_header)
    return email_address[0] if email_address else from_header

def get_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in part.get("Content-Disposition", ""):
                return part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8')
    else:
        return msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8')

def check_new_mail(mail):
    result, data = mail.search(None, '(UNSEEN)')
    mail_ids = data[0].split()
    new_mails = []
    if mail_ids:
        for mail_id in mail_ids:
            result, msg_data = mail.fetch(mail_id, '(RFC822)')
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            subject = msg['subject']
            from_ = msg['from']
            message_id = msg['Message-ID']
            email_address = extract_email_address(from_)
            body = get_email_body(msg)
            to_header = msg['To']
            cc_header = msg['Cc'] if msg['Cc'] else ''
            if message_id not in processed_emails:
                new_mails.append((email_address, subject, message_id, mail_id, body, to_header, cc_header))
    return new_mails

def reply_email(mail, recipient, subject, body, message_id, mail_id, original_message, cc_list, issue_url=None):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ACCOUNT
    msg['To'] = recipient  # Reply only to the sender
    msg['Cc'] = cc_list  # Include CC addresses
    msg['Subject'] = f"Re: {subject}"
    
    # Include the reply body and the original message
    reply_body = f"{body}\n\n--- Previous message ---\n{original_message}"

    # Add a link to the GitLab issue if available
    if issue_url:
        msg.attach(MIMEText(f"\n\nYou can track your issue here: {issue_url} \n\n", 'plain'))

    msg.attach(MIMEText(reply_body, 'plain'))
    
    # Send the email
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_ACCOUNT, PASSWORD)
    
    # Send to sender and CCs
    all_recipients = [recipient] + cc_list.split(",") if cc_list else [recipient]
    server.sendmail(EMAIL_ACCOUNT, all_recipients, msg.as_string())
    server.quit()

    # Mark the email as read
    mail.store(mail_id, '+FLAGS', '\\Seen')
    processed_emails.append(message_id)

def truncate_conversation(conversation_history, max_tokens=3000):
    total_tokens = sum([len(msg['content']) for msg in conversation_history])
    while total_tokens > max_tokens:
        conversation_history.pop(0)  # Remove oldest messages until under the limit
        total_tokens = sum([len(msg['content']) for msg in conversation_history])
    return conversation_history

def get_response_from_chatgpt(user_message, conversation_history):
    conversation_history = truncate_conversation(conversation_history, max_tokens=3000)
    messages = [{"role": "system", "content": "Your name is Rick Astley, you help users, always ask the user to explain their problem in as much detail as possible, ask the user if you should escalate the problem to your support managers, sign your emails as 'support desk'"}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_message})

    while True:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages
            )
            chatgpt_response = response['choices'][0]['message']['content']
            return chatgpt_response
        except openai.error.RateLimitError as e:
            print(f"Rate limit reached: {e}. Waiting before retrying...")
            time.sleep(20)  # Wait 20 seconds before retrying

def calculate_escalation_probability(conversation_history):
    conversation_history = truncate_conversation(conversation_history, max_tokens=3000)
    messages = [
        {"role": "system", "content": "You are an AI that determines if the user's problem requires escalation. Analyze the messages below and give an escalation rate between 0 and 100. If the number exceeds 80, escalate to human support. If the user requests escalation, set the number above 80 directly."}
    ]
    messages.extend(conversation_history)

    while True:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages
            )
            escalation_response = response['choices'][0]['message']['content']
            print(escalation_response)

            match = re.search(r'(\d+)', escalation_response)

            try:
                if match:
                    number = match.group(1)
                    escalation_probability = float(number) / 100.0  # Convert to fraction
                else:
                    escalation_probability = 0.0  # Assume 0% if no number found
            except ValueError:
                escalation_probability = 0.0  # Assume 0% if conversion fails

            print(f"Escalation Probability: {escalation_probability}")
            return escalation_probability

        except openai.error.RateLimitError as e:
            print(f"Rate limit reached: {e}. Waiting before retrying...")
            time.sleep(20)  # Wait 20 seconds before retrying

def generate_summary(conversation_history):
    conversation_history = truncate_conversation(conversation_history, max_tokens=3000)
    messages = [
        {"role": "system", "content": "You are an AI that summarizes conversations. Summarize the exchanges below in one clear sentence for a support ticket."}
    ]
    messages.extend(conversation_history)

    while True:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages
            )
            summary = response['choices'][0]['message']['content']
            return summary
        except openai.error.RateLimitError as e:
            print(f"Rate limit reached: {e}. Waiting before retrying...")
            time.sleep(20)  # Wait 20 seconds before retrying

def send_webhook_notification(problem_description, summary, issue_url):
    payload = {
        "text": f"An issue has been escalated:\n\nConversation with the user:\n\n {problem_description}\n\nConversation summary: {summary}\n\nIssue link: {issue_url}"
    }
    requests.post(WEBHOOK_URL, json=payload)

def create_gitlab_issue(title, description, summary):
    # Issue data
    issue_data = {
        "title": title,
        "description": description +  "\n\n" + summary,
        "assignee_ids": [1],  # Replace with the assigned user's ID
        "labels": ["bug", "urgent"]
    }

    # Request headers
    headers = {
        'PRIVATE-TOKEN': GITLAB_TOKEN,
        'Content-Type': 'application/json'
    }

    # Send the request
    response = requests.post(GITLAB_URL, headers=headers, json=issue_data)

    # Check the response
    if response.status_code == 201:
        issue_url = response.json().get('web_url', 'Link not available')
        print("Issue created successfully:", issue_url)
        return issue_url
    else:
        print("Error creating issue:", response.json())
        return None

def save_conversation_history(filename, history):
    with open(filename, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def load_conversation_history(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def handle_mail(mail, email_address, subject, message_id, mail_id, body, to_header, cc_header):
    print(email_address)
    # if not email_address.endswith('@devoteam.com'):
    #     print(f"Ignored email from {email_address}, not a @devoteam.com address.")
    #     return
    print(email_address)
    if email_address.endswith(SUPPORT_EMAIL):
        print(f"Ignored email from {email_address}, {SUPPORT_EMAIL} address.")
        return
    
    history_filename = f"conversation_{email_address}.json"
    conversation_history = load_conversation_history(history_filename)
    conversation_history.append({"role": "user", "content": body})
    
    response = get_response_from_chatgpt(body, conversation_history)
    
    conversation_history.append({"role": "assistant", "content": response})
    save_conversation_history(history_filename, conversation_history)

    # Calculate escalation probability
    escalation_probability = calculate_escalation_probability(conversation_history)
    
    # Initialize issue_url to None
    issue_url = None
    
    if escalation_probability >= PROGRESS_THRESHOLD:
        # Generate a summary of the conversation
        summary = generate_summary(conversation_history)
        # Create a GitLab issue
        issue_url = create_gitlab_issue(f"Escalated issue from {email_address}", body, summary)
        # Send notification to the webhook with the message and summary
        send_webhook_notification(body, summary, issue_url)  # Now sends the summary too
    
    # Reply to the email only to the sender and keep the CCs
    reply_email(mail, email_address, subject, response, message_id, mail_id, body, cc_header, issue_url)

def monitor_inbox():
    while True:
        mail = connect_imap()
        new_mails = check_new_mail(mail)
        for email_address, subject, message_id, mail_id, body, to_header, cc_header in new_mails:
            handle_mail(mail, email_address, subject, message_id, mail_id, body, to_header, cc_header)
        time.sleep(10)

if __name__ == '__main__':
    monitor_inbox()