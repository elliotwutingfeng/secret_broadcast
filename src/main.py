"""
Copyright 2024 Wu Tingfeng <wutingfeng@outlook.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import base64
import datetime
import io
import json
import os
import pathlib
import time

import cv2
import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent.parent / ".env")

TOKEN = os.getenv("TOKEN")
CHAT_IDS = tuple(os.getenv("CHAT_IDS").split(","))
PASSWORD = os.getenv("PASSWORD")


def bot_get_updates(token: str) -> dict:
    """Grab all messages received by bot. Useful for obtaining chat_id for each user.

    Args:
        token (str): Telegram bot API token.

    Returns:
        dict: JSON response.
    """
    endpoint: str = f"https://api.telegram.org/bot{token}/getUpdates"
    return requests.post(endpoint, timeout=60).json()


def encrypt_file(password: str, file_bytes: bytes) -> bytes:
    """Encrypt `file_bytes` using Fernet recipe. Key is derived from `password` using Scrypt.

    Args:
        password (str): File password.
        file_bytes (bytes): Bytestring of plaintext file.

    Returns:
        bytes: JSON bytestring containing the Scrypt KDF parameters
        and the Fernet ciphertext.
    """
    salt = os.urandom(32)
    length = 32
    n, r, p = 2**17, 8, 1  # OWASP recommendations (February 2024)

    kdf = Scrypt(salt=salt, length=length, n=n, r=r, p=p)
    symmetric_key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))

    ciphertext = Fernet(symmetric_key).encrypt(file_bytes)
    encrypted_message: str = json.dumps(
        {
            "salt": base64.urlsafe_b64encode(salt).decode("utf-8"),
            "length": length,
            "n": n,
            "r": r,
            "p": p,
            "ciphertext_b64": base64.urlsafe_b64encode(ciphertext).decode("utf-8"),
        }
    ).encode("utf-8")

    return encrypted_message


def decrypt_file(password: str, file_bytes: bytes) -> bytes:
    """Decrypt `file_bytes` using Fernet recipe. Key is derived from `password` using Scrypt.

    Args:
        password (str): File password.
        file_bytes (bytes): JSON bytestring containing the Scrypt KDF parameters
        and the Fernet ciphertext.

    Returns:
        bytes: Bytestring of plaintext file.
    """
    encrypted_message = json.loads(file_bytes)

    salt: bytes = base64.urlsafe_b64decode(encrypted_message["salt"].encode("utf-8"))
    length = encrypted_message["length"]
    n, r, p = encrypted_message["n"], encrypted_message["r"], encrypted_message["p"]

    kdf: Scrypt = Scrypt(salt=salt, length=length, n=n, r=r, p=p)
    symmetric_key: bytes = base64.urlsafe_b64encode(
        kdf.derive(password.encode("utf-8"))
    )

    ciphertext: bytes = base64.urlsafe_b64decode(
        encrypted_message["ciphertext_b64"].encode("utf-8")
    )
    plaintext: bytes = Fernet(symmetric_key).decrypt(ciphertext)

    return plaintext


def encrypt_file_and_broadcast(
    filename: str,
    file_bytes: bytes,
    blurred_file_bytes: bytes,
    password: str,
    token: str,
    chat_ids: tuple[str],
    thumbnail: bool = False,
):
    """Encrypt and send file to all relevant users as defined by `chat_ids`.

    Args:
        filename (str): Name of plaintext file.
        file_bytes (bytes): Bytestring of plaintext file.
        blurred_file_bytes (bytes): Bytestring of plaintext file.
        password (str): File password.
        token (str): Telegram bot API token.
        chat_ids (tuple[str]): Telegram chat IDs of users to receive encrypted file.
        thumbnail (bool): Show blurred thumbnail in chat. Defaults to False.
    """
    encrypted_message = encrypt_file(password, file_bytes)
    files = {
        "document": (filename + ".txt", encrypted_message, "application/octet-stream"),
        "thumb": blurred_file_bytes if thumbnail else None,
    }

    endpoint: str = f"https://api.telegram.org/bot{token}/sendDocument"
    for chat_id in chat_ids:
        print(
            requests.post(
                endpoint,
                data={"chat_id": chat_id, "disable_notification": True},
                files=files,
                timeout=60,
            ).json()
        )


def capture_image() -> tuple[bytes, bytes]:
    """Take a photo with the webcam.

    Raises:
        Exception: Camera inaccessible.

    Returns:
        tuple[bytes, bytes]: JPG photo bytestring and blurred JPG photo bytestring.
    """
    camera = cv2.VideoCapture(0)
    if camera.isOpened():
        successful, frame = camera.read()
    else:
        successful = False
    if not successful:
        raise Exception("Camera inaccessible.")
    camera.release()
    _, img_encoded = cv2.imencode(
        ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 20]
    )  # Compress to save space

    blurred_frame = cv2.blur(frame, (60, 60))  # Apply blur
    _, blurred_img_encoded = cv2.imencode(
        ".jpg", blurred_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 20]
    )  # Compress to save space

    file_bytes: bytes = io.BytesIO(img_encoded).getbuffer().tobytes()
    blurred_file_bytes: bytes = io.BytesIO(blurred_img_encoded).getbuffer().tobytes()

    return file_bytes, blurred_file_bytes


if __name__ == "__main__":
    timestamp: str = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(seconds=time.localtime().tm_gmtoff))
    ).isoformat()
    filename: str = f"{timestamp}.jpg"
    file_bytes, blurred_file_bytes = capture_image()
    encrypt_file_and_broadcast(
        filename,
        file_bytes,
        blurred_file_bytes,
        PASSWORD,
        TOKEN,
        CHAT_IDS,
        thumbnail=False,
    )
