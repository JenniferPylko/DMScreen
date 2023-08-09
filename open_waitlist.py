import sqlite3
import dotenv
import os
import requests

def send_invite_notification(email):
    subject = "Your Invitation to DMScreen Early Access is Here!"
    msg = """
    Hi there!

    The moment you've been waiting for has arrived! We're thrilled to extend an invitation to you to join the Early Access phase of DMScreen. Your spot in our community is now ready, and we can't wait for you to embark on this exciting adventure with us.

    As a Dungeon Master, you'll find DM Screen to be an invaluable companion, offering tools like our SRD chatbot, automatic note transcription, AI-generated NPCs, and so much more. We've carefully designed these features to help you run immersive and memorable campaigns.

    Here's how to get started:

    1. Visit https://dmscreen.net and click "Create Account"
    2. Enter your email address and create a password
    3. Click the link in the verification email we send you. If you don't see it, check your spam folder. If you still don't see it, please send a message on our Discord server.
    4. Explore the array of features and let your creativity flow!
    5. Don't hesitate to share your feedback, report bugs, or suggest new features through our Discord community.
    6. Join our Discord Server: https://discord.gg/eF5qBGXqvj

    Please remember, DM Screen is still in its Early Access phase. This means that while we've packed it with exciting tools, there might be occasional bugs or performance issues. Your feedback and patience as we fine-tune things are invaluable to us.

    There is no immediate need to upgrade to a paid tier, as all current functionality is available for free. But if you love what you see and wish to support our ongoing development, you can opt to upgrade.

    On behalf of the entire DM Screen team, we extend our heartfelt gratitude for your interest and patience while waiting for this invitation. We are confident that your contributions will help us shape an incredible tool for Dungeon Masters worldwide.

    Adventure awaits, and we're honored to have you join us on this journey.

    Warm regards,
    The DM Screen Team

    [Note: If you have any questions or need assistance, please don't hesitate to reply to this email or reach out through our Discord server. We're here to help!]
    """
    print("Sending invite to", email)
    return requests.post(
        "https://api.mailgun.net/v3/"+os.getenv("MAILGUN_DOMAIN")+"/messages" ,
        auth=("api", os.getenv("MAILGUN_API_KEY")),
        data={
            "from": "DM Assistant <mailgun@"+os.getenv("MAILGUN_DOMAIN")+">",
            "to": [email],
            "subject": subject,
            "text": msg
        })


dotenv.load_dotenv()

# Connect to database
conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()
c.execute("SELECT id,email FROM waitlist order by date_new ASC")
rows = c.fetchall()

# Get a count of existing users
c.execute("SELECT COUNT(*) FROM users")
user_count = c.fetchone()[0]
needed_users = int(os.getenv('MAX_USERS')) - user_count

conn.close()
for i, row in enumerate(rows):
    print(i, row[0], row[1])
    send_invite_notification(row[1])
    if i >= needed_users:
        break