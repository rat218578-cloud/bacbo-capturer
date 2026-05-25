FROM python:3.11-slim

# Instala dependências do sistema para Chrome e PostgreSQL
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    chromium \
    chromium-driver \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Instala Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY . .

# Define variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Expõe porta (se usar API)
EXPOSE 8000

# Comando para executar (USANDO PYTHON, não npm!)
CMD ["python", "capturer.py"]
