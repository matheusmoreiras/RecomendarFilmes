FROM python:3.11.1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Roda o container
CMD ["flask", "--app", "apy", "run", "--host=0.0.0.0"]