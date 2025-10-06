# secret_broadcast

[![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org)
[![LICENSE](https://img.shields.io/badge/LICENSE-APACHE--2.0-GREEN?style=for-the-badge)](LICENSE)

Send encrypted webcam snapshots over Telegram to specific users.

## Setup

You will need a webcam that can be accessed via [OpenCV](https://pypi.org/project/opencv-python).

You will also need [uv](https://docs.astral.sh/uv/guides/install-python).

First create **.env**

```bash
cp --update=none .env-dev .env
```

Fill up **.env** with the relevant data; you will need your [Telegram bot API token](https://core.telegram.org/bots/api), a list of Telegram user Chat IDs (obtainable by first manually sending messages to your bot from each user, and then running `bot_get_updates(token)`), and a strong password for your encrypted images. The contents of **.env** _must_ be kept secret.

## Usage

```bash
uv run python src/main.py
```

## Is it secret? Is it safe?

No guarantees. If your bot conversation has been leaked, the messages still need to be decrypted individually.
