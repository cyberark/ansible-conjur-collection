import testinfra.utils.ansible_runner
import os

testinfra_hosts = [os.environ['COMPOSE_PROJECT_NAME'] + '_ansible_1']

def test_retrieval_failed(host):
    secrets_file = host.file('/conjur_secrets.txt')

    assert not secrets_file.exists
