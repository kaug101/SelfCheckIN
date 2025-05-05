
import base64
import hashlib
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

# Derive a strong encryption key from password + salt
def derive_key(password: str, salt: str) -> bytes:
    salt_bytes = hashlib.sha256(salt.encode()).digest()  # consistent per user
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt_bytes,
        iterations=100_000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

# Encrypt check-in text with derived key
def encrypt_checkin(plain_text: str, password: str, user_email: str) -> str:
    key = derive_key(password, user_email)
    cipher = Fernet(key)
    return cipher.encrypt(plain_text.encode()).decode()

# Decrypt check-in text with derived key
def decrypt_checkin(cipher_text: str, password: str, user_email: str) -> str:
    key = derive_key(password, user_email)
    cipher = Fernet(key)
    return cipher.decrypt(cipher_text.encode()).decode()
