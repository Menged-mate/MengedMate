import os
import firebase_admin
from firebase_admin import credentials, firestore, auth, db
import logging

logger = logging.getLogger(__name__)

def initialize_firebase():
    """
    Initialize Firebase Admin SDK using environment variables.
    """
    if firebase_admin._apps:
        return firebase_admin.get_app()

    project_id = os.getenv('FIREBASE_PROJECT_ID')
    private_key = os.getenv('FIREBASE_PRIVATE_KEY')
    client_email = os.getenv('FIREBASE_CLIENT_EMAIL')
    database_url = os.getenv('FIREBASE_DATABASE_URL')

    if not all([project_id, private_key, client_email]):
        logger.warning("Firebase environment variables are missing. Firebase features will be unavailable.")
        return None

    try:
        # Construct credentials from environment variables
        # Note: Private key might contain escaped newlines
        formatted_private_key = private_key.replace('\\n', '\n')
        
        cred_dict = {
            "type": "service_account",
            "project_id": project_id,
            "private_key": formatted_private_key,
            "client_email": client_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }

        cred = credentials.Certificate(cred_dict)
        
        options = {}
        if database_url:
            options['databaseURL'] = database_url

        app = firebase_admin.initialize_app(cred, options)
        logger.info(f"Firebase Admin SDK initialized for project: {project_id}")
        return app
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")
        return None

# Initialize on import
firebase_app = initialize_firebase()

def get_firestore_client():
    """Get Firestore client if initialized"""
    if firebase_admin._apps:
        return firestore.client()
    return None

def get_realtime_db_client():
    """Get Realtime Database client if initialized"""
    if firebase_admin._apps:
        return db.reference()
    return None

def get_auth_client():
    """Get Firebase Auth client if initialized"""
    if firebase_admin._apps:
        return auth
    return None
