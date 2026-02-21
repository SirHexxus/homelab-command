# Whisper on Proxmox LXC: Speech-to-Text Infrastructure-as-Code

This directory contains Infrastructure as Code (IaC) for deploying OpenAI's Whisper speech-to-text model in a Proxmox LXC container. The setup uses faster-whisper for improved performance and exposes an OpenAI-compatible API for easy integration with n8n and other tools.

## What You Get

- A secure, unprivileged LXC container optimized for speech-to-text
- faster-whisper-server (Speaches) with OpenAI-compatible API
- Whisper "small" model pre-downloaded and ready to use
- Automatic service startup and restart on failure
- Systemd integration for easy management

## Prerequisites

### On Your Workstation
- Terraform >= 1.0
- Ansible >= 2.10
- SSH key pair in ~/.ssh/

### On Your Proxmox System
- API token created in Proxmox UI
- Ubuntu 22.04 LXC template available
- Available resources: 4 CPU cores, 8GB RAM, 20GB storage

## Quick Start

### Step 1: Configure Terraform

```bash
cd terraform/
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your Proxmox credentials
```

### Step 2: Create the Container

```bash
terraform init
terraform plan
terraform apply
```

### Step 3: Update Ansible Inventory

Edit `ansible/inventory.ini` and replace `<CONTAINER_IP>` with the actual IP from Terraform output.

### Step 4: Run Ansible Provisioning

```bash
ansible-playbook -i ansible/inventory.ini ansible/provision.yml
```

### Step 5: Verify Installation

```bash
# Health check
curl http://<CONTAINER_IP>:9000/health

# Test transcription
curl -X POST http://<CONTAINER_IP>:9000/v1/audio/transcriptions \
  -F "file=@audio.mp3" \
  -F "model=small"
```

## API Endpoints

The server exposes OpenAI-compatible endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/audio/transcriptions` | POST | Transcribe audio to text |
| `/v1/audio/translations` | POST | Translate audio to English |
| `/v1/models` | GET | List available models |
| `/health` | GET | Health check |

### Transcription Request

```bash
curl -X POST http://<IP>:9000/v1/audio/transcriptions \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.mp3" \
  -F "model=small" \
  -F "response_format=json"
```

### Response

```json
{
  "text": "The transcribed text appears here..."
}
```

## n8n Integration

Configure an HTTP Request node:
- **Method:** POST
- **URL:** `http://<CONTAINER_IP>:9000/v1/audio/transcriptions`
- **Body Type:** Form-Data
- **Parameters:**
  - `file`: Binary audio data
  - `model`: "small" (or tiny, base, medium, large-v3)
  - `response_format`: "json"

## Available Models

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| tiny | 75MB | Fastest | Low | Quick tests |
| base | 150MB | Fast | Basic | Simple audio |
| small | 500MB | Balanced | Good | **Default - recommended** |
| medium | 1.5GB | Slow | High | Important transcriptions |
| large-v3 | 3GB | Slowest | Best | Professional use |

To change the default model, edit `ansible/inventory.ini`:
```ini
whisper_model = "medium"
```

Then re-run the provision playbook.

## Maintenance

Run weekly to keep everything updated:

```bash
ansible-playbook -i ansible/inventory.ini ansible/update.yml
```

## File Organization

```
.
├── README.md
├── terraform/
│   ├── provider.tf
│   ├── variables.tf
│   ├── locals.tf
│   ├── main.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
└── ansible/
    ├── inventory.ini
    ├── provision.yml
    ├── update.yml
    ├── group_vars/
    │   └── whisper_containers.yml
    └── templates/
        ├── whisper-server.service.j2
        └── whisper-server.env.j2
```

## Troubleshooting

### Service won't start

```bash
ssh root@<CONTAINER_IP>
systemctl status whisper-server
journalctl -u whisper-server -f
```

### Model download fails

Check internet connectivity and disk space:
```bash
curl -I https://pypi.org
df -h
```

### Transcription returns errors

Verify the audio format. Supported formats: mp3, wav, m4a, webm, mp4, mpeg, mpga, oga, ogg, flac.

## Resource Usage

- **CPU:** Uses all allocated cores during transcription, idle otherwise
- **RAM:** ~2GB for small model, scales with model size
- **Disk:** ~500MB for small model plus OS (~5GB total)
