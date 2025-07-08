from flask import Flask, request
from flask_cors import CORS
import base64
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
CORS(app)

@app.route('/upload-photo', methods=['POST'])
def upload_photo():
    data = request.json
    image_data = base64.b64decode(data['image'].split(",")[1])
    filename = "captured_photo.png"

    with open(filename, "wb") as f:
        f.write(image_data)

    send_email(filename)
    return {"status": "photo received & emailed"}

def send_email(filename):
    sender = "your@gmail.com"
    password = "your_app_password"
    receiver = "target@gmail.com"

    msg = EmailMessage()
    msg['Subject'] = "📸 Smart Camera Photo"
    msg['From'] = sender
    msg['To'] = receiver
    msg.set_content("Smart camera just captured a photo.")

    with open(filename, 'rb') as f:
        msg.add_attachment(f.read(), maintype='image', subtype='png', filename=filename)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)

if __name__ == '__main__':
    app.run(debug=True)
