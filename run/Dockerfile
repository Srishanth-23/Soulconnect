FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY soundscape_service.py .
CMD ["functions-framework","--target=app_entry","--port=8080"]
