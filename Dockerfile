FROM python:3.9.5-slim

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
ENTRYPOINT ["python", "main.py"]