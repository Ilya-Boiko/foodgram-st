FROM python:3.12.3

WORKDIR /app

RUN pip install gunicorn==20.1.0

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

# Создаем директорию для статики
RUN mkdir -p /backend_static/static

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "backend.wsgi"]
