# ezansi-platform-core

## Getting the Rasberry Pi 5 ready for Ollma in container
```
sudo apt install -y podman podman-compose
podman --version
loginctl enable-linger $USER #This allows Podman containers to survive logout/reboot
podman pull docker.io/ollama/ollama
sudo podman run -d --name ollama -p 11434:11434 -v ollama-data:/root/.ollama --memory=6g --cpus=4 docker.io/ollama/ollama
```
