FROM python:3.11-alpine

RUN adduser -D ctfuser

WORKDIR /app

RUN pip install --no-cache-dir Flask==3.0.0 Werkzeug==3.0.1 Flask-Limiter==3.5.0

COPY . .

RUN chown -R ctfuser:ctfuser /app

USER ctfuser

EXPOSE 1338

CMD ["python", "app.py"]
