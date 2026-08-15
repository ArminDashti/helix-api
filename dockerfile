FROM python:3.12-slim

WORKDIR /app

# unixODBC + Microsoft ODBC Driver 18 (required by pyodbc on Linux).
# python:3.12-slim is Debian 13; Microsoft still publishes the Debian 12 driver packages.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg ca-certificates \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && printf 'deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main\n' \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY helix.config.example.yaml /app/helix.config.example.yaml
COPY deploy/entrypoint.sh /app/entrypoint.sh

RUN sed -i 's/\r$//' /app/entrypoint.sh \
  && chmod +x /app/entrypoint.sh \
  && mkdir -p /app/backend/markdown-files/instructions \
             /app/backend/markdown-files/rules \
             /app/backend/markdown-files/references

ENV PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=helix.settings \
    HELIX_ALLOWED_HOSTS=*

EXPOSE 8000
CMD ["/app/entrypoint.sh"]
