FROM python:3.11.2-slim
WORKDIR /app

RUN python -m venv venv

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY *.py requirements.txt wor-guild-bot.json .

RUN ./venv/bin/pip install --no-cache-dir -r requirements.txt

CMD ["./venv/bin/python", "bot_interface.py"]