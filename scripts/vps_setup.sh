#!/usr/bin/env bash
# vps_setup.sh — Script de desplegado automático de Oki-Nami en el VPS

set -e

echo "🌊 Iniciando despliegue de Oki-Nami Dashboard..."

# 1. Comprobar instalación de Docker y Docker Compose
if ! command -v docker &> /dev/null; then
    echo "📦 Instalando Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
fi

# 2. Comprobar archivos requeridos
if [ ! -f ".env" ]; then
    echo "⚠️ Archivo .env no encontrado. Creando plantilla desde .env.example..."
    cp .env.example .env || touch .env
fi

if [ ! -f "credentials.json" ]; then
    echo "⚠️ ATENCIÓN: No se encuentra credentials.json en la raíz del VPS."
    echo "Por favor, sube tu archivo credentials.json de Google API a este directorio."
fi

# 3. Construir y arrancar contenedores Docker
echo "🚀 Levantando contenedores Docker (Dashboard + Caddy SSL)..."
docker compose down || true
docker compose up --build -d

echo "✅ ¡Despliegue completado con éxito!"
echo "📍 Comprueba el estado con: docker compose ps"
