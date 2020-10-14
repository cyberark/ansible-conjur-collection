#!/bin/bash
set -ex pipefail

main () {
    install_dockercompose
    install_modules
    install_galaxy_collections
}

install_dockercompose () {
    sudo curl -L "https://github.com/docker/compose/releases/download/1.27.4/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
}

install_modules () {
    pip3 install ansible --user
    pip3 install docker --user
    pip3 install docker-compose --user
}

install_galaxy_collections () {
    ansible-galaxy collection install community.general
}

deploy_conjur () {
    sudo chmod -R 777 /vagrant
    ansible-playbook /vagrant/conjur.yml
}

main "$@"
