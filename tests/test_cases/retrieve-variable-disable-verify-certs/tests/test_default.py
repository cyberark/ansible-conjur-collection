import testinfra.utils.ansible_runner
import os

testinfra_hosts = [os.environ['COMPOSE_PROJECT_NAME'] + '_ansible_1']

def test_retrieved_secret(host):
    secrets_file = host.file('/conjur_secrets.txt')

    assert secrets_file.exists

    result = host.check_output("cat /conjur_secrets.txt", shell=True)

    assert result == "test_secret_password"
