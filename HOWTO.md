local run:
activate venv3.12
source setup_pythonpath.sh
python -m enbot

docker start:
docker-compose up --build -d   #force to build
docker-compose logs -f
docker-compose down
docker save enbot-enbot > enbot_v0.0.2.tar

create docker img for amd64 platform:
docker build --platform linux/amd64 -t enbot-enbot .
docker save enbot-enbot > enbot_v0.0.7.tar