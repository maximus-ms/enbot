docker start:
docker-compose up --build -d   #force to build

docker-compose logs -f

docker-compose down

docker save enbot-enbot > enbot_v0.0.2.tar