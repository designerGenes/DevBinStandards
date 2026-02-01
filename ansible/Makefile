.PHONY: help ping setup check lint test-rpi5 test-zero

help:
	@echo "Ansible Playbook Commands:"
	@echo "  make ping          - Test connection to all hosts"
	@echo "  make setup         - Run full setup on all hosts"
	@echo "  make check         - Dry-run the playbook (check mode)"
	@echo "  make lint          - Lint the playbook with ansible-lint"
	@echo "  make test-rpi5     - Run setup on Raspberry Pi 5 hosts only"
	@echo "  make test-zero     - Run setup on Raspberry Pi Zero 2W hosts only"

ping:
	ansible all -i inventory.ini -m ping

setup:
	ansible-playbook -i inventory.ini playbook.yml

check:
	ansible-playbook -i inventory.ini playbook.yml --check --diff

lint:
	ansible-lint playbook.yml

test-rpi5:
	ansible-playbook -i inventory.ini playbook.yml --limit raspberry_pi_5

test-zero:
	ansible-playbook -i inventory.ini playbook.yml --limit raspberry_pi_zero_2w

# Run only specific tags (when implemented)
setup-docker:
	ansible-playbook -i inventory.ini playbook.yml --tags docker

setup-python:
	ansible-playbook -i inventory.ini playbook.yml --tags python

setup-neovim:
	ansible-playbook -i inventory.ini playbook.yml --tags neovim
