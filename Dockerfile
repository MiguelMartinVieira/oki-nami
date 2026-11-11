# Dockerfile para Oki-Nami Dashboard
FROM python:3.12-slim

# Evitar escritura de bytecode de Python y buffering de stdout
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Instalar dependencias del sistema requeridas
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de configuración de dependencias
COPY Dashboard/requirements.txt pyproject.toml ./

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del proyecto
COPY . /app/

# Exponer el puerto de Streamlit
EXPOSE 8501

# Variables de entorno por defecto para Streamlit en headless mode
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ENABLE_STATIC_SERVING=true

# Comando por defecto para arrancar el Dashboard
CMD ["python", "Dashboard/run_dashboard.py"]
