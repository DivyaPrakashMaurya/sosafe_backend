import os
import firebase_admin
from firebase_admin import credentials, messaging, firestore
from dotenv import load_dotenv

load_dotenv()

# Ensure serviceAccountKey.json is in the same folder
cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def send_fcm_notification(fcm_token: str, title: str, body: str, data_payload: dict = None):
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(sound='default', channel_id='emergency_channel')
            ),
            data=data_payload or {},
            token=fcm_token,
        )
        response = messaging.send(message)
        print(f"✅ FCM Notification sent: {response}")
        return True
    except Exception as e:
        print(f"❌ FCM Send Error: {e}")
        return False
