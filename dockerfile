FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY helix.config.example.yaml /app/helix.config.example.yaml
COPY deploy/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh \
  && mkdir -p /app/backend/markdown-files/instructions \
             /app/backend/markdown-files/rules \
             /app/backend/markdown-files/references

ENV PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=helix.settings \
    HELIX_ALLOWED_HOSTS=*

EXPOSE 8000
CMD ["/app/entrypoint.sh"]
