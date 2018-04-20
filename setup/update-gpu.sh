# This script is only tested with ubuntu 14.04 LTS
sudo apt-get -y update && sudo apt-get dist-upgrade
sudo apt-get install emacs24-nox
sudo apt-get install unzip

pip install --upgrade pip
pip install kaggle-cli

sudo reboot

# Then for kaggle-cli to work, need to setup password and competition
