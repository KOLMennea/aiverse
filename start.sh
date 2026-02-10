#!/bin/bash

# Lance AIVERSE: serveur + bots traders

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════╗"
echo "║       🌐 AIVERSE - IA Economy         ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"

cd "$(dirname "$0")"

# Install deps
echo -e "${BLUE}[1/3] Installation des dépendances...${NC}"
pip install -q -r api/requirements.txt
pip install -q httpx

# Start server
echo -e "${BLUE}[2/3] Démarrage du serveur AIVERSE...${NC}"
cd api
python server.py &
SERVER_PID=$!
cd ..

sleep 2

# Check server
if curl -s http://localhost:8080 > /dev/null; then
    echo -e "${GREEN}✓ Serveur AIVERSE démarré sur http://localhost:8080${NC}"
else
    echo "❌ Échec du démarrage du serveur"
    exit 1
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 AIVERSE est en ligne!${NC}"
echo ""
echo "📡 API: http://localhost:8080"
echo "📖 Docs: http://localhost:8080/docs"
echo ""
echo "Commandes utiles:"
echo "  curl http://localhost:8080/state    # État du monde"
echo "  curl http://localhost:8080/companies # Entreprises"
echo "  curl http://localhost:8080/leaderboard # Classement"
echo ""
echo -e "${BLUE}[3/3] Lancer des bots traders? (y/n)${NC}"
read -r answer

if [[ "$answer" == "y" ]]; then
    echo "🤖 Lancement de 5 bots traders..."
    cd agents
    python trader_bot.py &
    BOTS_PID=$!
    cd ..
fi

echo ""
echo "Appuyez sur Ctrl+C pour arrêter..."

# Wait
wait $SERVER_PID
