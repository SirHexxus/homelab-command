# Ollama on Proxmox LXC: Complete Infrastructure-as-Code Setup

This directory contains production-grade Infrastructure as Code (IaC) for deploying Ollama AI inference in a Proxmox LXC container. The setup combines Terraform for infrastructure provisioning and Ansible for configuration management, giving you a fully automated, reproducible deployment.

## What You Get

When you run these scripts, you'll have:
- A secure, unprivileged LXC container optimized for AI inference
- Ollama with two models pre-downloaded and ready to use:
  - Mistral 7B (for general tasks and classification)
  - nomic-embed-text (for semantic search)
- Automatic service startup and restart on failure
- Systemd integration for easy management
- A maintenance playbook to keep everything up to date
- GPU support ready (for when you add the Arc B580)

## Prerequisites

Before starting, ensure you have:

### On Your Workstation
- Terraform >= 1.0 (install from terraform.io)
- Ansible >= 2.10 (install via `pip3 install ansible`)
- SSH key pair in ~/.ssh/id_rsa and ~/.ssh/id_rsa.pub (run `ssh-keygen` if you don't have one)
- Network access to your Proxmox host

### On Your Proxmox System
- An API token created in Proxmox UI (Datacenter → Permissions → API Tokens)
- Available resources:
  - 8 CPU cores (your Xeon E-2378 has 8, so you can allocate all)
  - 16GB RAM (conservative given your 62GB total)
  - 50GB storage space
  - At least one network bridge configured (usually vmbr0)
- Ubuntu 22.04 LXC template (if it's not available, download it through Proxmox UI)

## Quick Start

### Step 1: Prepare Configuration Files

The Terraform configuration needs your Proxmox credentials and settings. These are provided in `terraform.tfvars`, which is generated from a template to avoid accidentally committing secrets.

```bash
cd terraform/
cp terraform.tfvars.example terraform.tfvars
```

Now edit `terraform.tfvars` in your text editor and fill in:
- `proxmox_api_url`: The URL to your Proxmox API (usually `https://your-proxmox-ip:8006/api2/json`)
- `proxmox_api_token_id`: Your API token ID (format: `username@pam!tokenname`)
- `proxmox_api_token`: Your API token secret
- `proxmox_node`: The name of your Proxmox node (usually `pve`)

All other settings have sensible defaults for your hardware.

### Step 2: Create the Container with Terraform

From the `terraform/` directory, run:

```bash
# See what Terraform will create (without making changes)
terraform init
terraform plan

# Actually create the container
terraform apply
```

Terraform will output important information, including the container ID and network configuration. Make note of the container's IP address if using DHCP, or verify the static IP if you configured one.

**Note**: If you get an error about the template not existing, check your Proxmox host for available templates by running:
```bash
ssh root@proxmox-host
pveam available | grep ubuntu-22.04
```

Then update `lxc_template` in your `terraform.tfvars` with the correct template name.

### Step 3: Update Ansible Inventory

The Ansible inventory tells Ansible where to find the container and how to connect to it. Edit `ansible/inventory.ini` and replace `<CONTAINER_IP>` with the actual IP address from Terraform's output:

```ini
[ollama_containers]
ollama-01 ansible_host=192.168.1.100 ansible_user=root ansible_port=22
```

You can find the container IP by:
- Checking the Terraform output
- Looking in Proxmox UI: click the container, go to Status
- Running on Proxmox host: `lxc-ls -f | grep ollama`

### Step 4: Verify SSH Access

Before running Ansible, verify you can SSH into the container:

```bash
ssh -i ~/.ssh/id_rsa root@<CONTAINER_IP>
```

This should connect without asking for a password (SSH key was injected during container creation). If it fails, wait 30 seconds for the container to fully boot and try again.

### Step 5: Run Ansible Provisioning

From the root directory (containing both terraform/ and ansible/), run:

```bash
ansible-playbook -i ansible/inventory.ini ansible/provision.yml
```

This playbook will:
1. Update the container's OS and packages
2. Install Ollama
3. Download the three AI models (takes 10-15 minutes)
4. Start the Ollama service
5. Verify everything is working

The playbook output will show progress and status messages. If you see any errors, see the Troubleshooting section below.

### Step 6: Verify Installation

Once the playbook completes, test the installation:

```bash
# Query the API to see loaded models
curl http://<CONTAINER_IP>:11434/api/tags

# Test inference (should complete in 10-15 seconds with CPU)
curl http://<CONTAINER_IP>:11434/api/generate \
  -X POST \
  -d '{"model":"mistral:7b","prompt":"Hello, what is AI?","stream":false}' \
  | jq '.response'
```

## Usage

### Daily Operations

The Ollama service runs automatically. You don't need to do anything to use it. Your n8n workflows can call the API at `http://<CONTAINER_IP>:11434`.

Example n8n HTTP request configuration:
- Base URL: `http://<CONTAINER_IP>:11434/api`
- Endpoint: `/generate`
- Method: POST
- Body: `{"model":"mistral:7b","prompt":"...","stream":false}`

### Regular Maintenance

Run the update playbook weekly to keep everything current:

```bash
ansible-playbook -i ansible/inventory.ini ansible/update.yml
```

This updates the OS, Ollama binary, and checks system health.

### Adding GPU Support

When you purchase the Arc B580:

1. Install the GPU in your Proxmox host
2. Reboot Proxmox
3. In Proxmox UI, select the Ollama container
4. Go to Resources → Add Device
5. Select the GPU device (Intel Arc)
6. Save and restart the container

Then run the GPU setup playbook:

```bash
ansible-playbook -i ansible/inventory.ini ansible/gpu_enable.yml
```

This installs drivers and configures Ollama to use the GPU. Ollama auto-detects GPU on startup, so inference will immediately become 5-10x faster.

### Checking Container Status

From Proxmox host:
```bash
# See container list
lxc-ls -f

# Access container shell
lxc-exec ollama -- bash

# Check Ollama status
lxc-exec ollama -- systemctl status ollama

# View Ollama logs
lxc-exec ollama -- journalctl -u ollama -f
```

From your workstation:
```bash
ssh root@<CONTAINER_IP>
# Then use normal Linux commands
systemctl status ollama
journalctl -u ollama -f
ollama list
```

## Architecture

The setup uses three layers of automation working together:

**Terraform (Infrastructure Layer)**: Defines the container's resources (CPU, RAM, disk, network) and security settings. It's declarative, meaning you describe the desired state and Terraform ensures it exists.

**Ansible (Configuration Layer)**: Installs software, configures services, and performs tasks inside the container. It's procedural but idempotent, meaning running it multiple times produces the same result.

**Ollama (Application Layer)**: The actual LLM inference engine that serves models via HTTP API.

This separation of concerns means:
- You can modify infrastructure (resources) without touching configuration code
- You can change configuration without changing infrastructure
- Each layer can be tested and deployed independently
- Changes are documented in code, making your setup reproducible

## File Organization

```
.
├── ARCHITECTURE.md              # Detailed design document
├── README.md                    # This file
├── terraform/
│   ├── provider.tf             # Proxmox API configuration
│   ├── variables.tf            # Input variables (with descriptions)
│   ├── locals.tf               # Computed values
│   ├── main.tf                 # Container resource definition
│   ├── outputs.tf              # Information displayed after creation
│   ├── terraform.tfvars.example # Template (rename to terraform.tfvars)
│   └── .gitignore              # Don't commit tfvars or state
│
└── ansible/
    ├── inventory.ini           # Container IP and connection info
    ├── provision.yml           # Main provisioning playbook
    ├── update.yml              # Maintenance and update playbook
    ├── gpu_enable.yml          # GPU configuration (future use)
    └── templates/
        └── ollama.service.j2   # Systemd service template
```

## Troubleshooting

### "terraform apply" fails with Proxmox connection error

Check your terraform.tfvars:
- Verify `proxmox_api_url` is correct (usually `https://hostname:8006/api2/json`)
- Verify your API token ID and secret are correct
- Verify `proxmox_node` matches your actual node name (run `pvesh get /nodes` on Proxmox host)
- If you're using a self-signed certificate, ensure `proxmox_tls_insecure = true`

### "ansible-playbook" can't connect to container

Wait 30-60 seconds after Terraform finishes for the container to fully boot. Then:

```bash
# Test SSH access
ssh -i ~/.ssh/id_rsa root@<CONTAINER_IP>

# If that fails, check the container is running
lxc-ls -f | grep ollama

# If container is running, check SSH service
lxc-exec ollama -- systemctl status ssh

# If SSH isn't running, start it manually
lxc-exec ollama -- systemctl start ssh
```

### Ansible playbook seems stuck on "Pull Ollama models"

Model download is slow on the first run. Each model is 2-6GB. The playbook shows the download progress. You can check progress manually:

```bash
ssh root@<CONTAINER_IP>
journalctl -u ollama -f
```

If downloads seem stalled, check internet connectivity from the container:

```bash
lxc-exec ollama -- curl -I https://ollama.ai
```

### Models don't appear in "ollama list"

Check that the Ollama service is running and models finished downloading:

```bash
ssh root@<CONTAINER_IP>
systemctl status ollama
ollama list
# Check if directories exist
ls -la /var/lib/ollama/models/
```

If directories are empty, Ollama is still downloading or errored. Check logs:

```bash
journalctl -u ollama -n 50
```

### "curl" to API endpoint fails

Verify the service is running and listening:

```bash
# From container
lxc-exec ollama -- curl http://localhost:11434/api/tags

# From Proxmox host (if on same network)
curl http://<CONTAINER_IP>:11434/api/tags

# Check if port is open
lxc-exec ollama -- netstat -tlnp | grep 11434
```

### n8n can't reach Ollama

If n8n is on a different host:
- Verify network connectivity: `ping <CONTAINER_IP>` from n8n host
- Verify firewall isn't blocking port 11434
- Use container IP, not hostname
- For production, set up a reverse proxy (nginx) to handle HTTPS

If n8n is on the Proxmox host:
- Use `http://localhost:11434` with port forwarding: `lxc-attach ollama -- /bin/bash -c "nc -ln -p 11434 -e /bin/nc localhost 11434"`
- Or use the container IP address directly

### GPU not detected after running "gpu_enable.yml"

Check that GPU device passthrough is configured in Proxmox:

```bash
# Check if device exists in container
lxc-exec ollama -- ls -la /dev/dri/renderD128

# If it doesn't exist, GPU passthrough isn't configured
# Go to Proxmox UI and configure it manually
```

Then check drivers:

```bash
lxc-exec ollama -- apt list --installed | grep -i intel-gpu
lxc-exec ollama -- clinfo
```

## Advanced Configuration

### Changing Model List

Edit `ansible/inventory.ini` and modify the `ollama_models` list:

```ini
[ollama_containers:vars]
ollama_models:
  - mistral:7b
  - phi:3.5
  - neural-chat:7b
```

Then re-run the provision playbook:

```bash
ansible-playbook -i ansible/inventory.ini ansible/provision.yml
```

The new models will be downloaded and the old ones remain available.

### Using Different Container Resources

Edit `terraform/terraform.tfvars`:

```hcl
container_cpu_cores = 12       # More cores for faster inference
container_memory_mb = 32768    # 32GB RAM
container_disk_gb   = 100      # More space for larger models
```

Then re-apply Terraform:

```bash
cd terraform/
terraform apply
```

### Static IP vs DHCP

For production, use static IP. Edit `terraform/terraform.tfvars`:

```hcl
container_ip      = "192.168.1.100/24"
container_gateway = "192.168.1.1"
```

Then re-apply Terraform.

## Security Considerations

The current setup is appropriate for home lab / internal network use. For production or public internet exposure:

1. **Never expose port 11434 directly**. Use a reverse proxy (nginx) with authentication.
2. **Use HTTPS**. Configure nginx or Caddy in front of Ollama.
3. **Restrict access**. Use firewall rules to limit which IPs can connect.
4. **Keep updated**. Run the update playbook weekly.
5. **Monitor logs**. Set up centralized logging if running multiple services.
6. **Run in privileged mode only if necessary**. The current unprivileged setup is secure.

## Cost Analysis

- One-time setup: 2-4 hours (automation handles the rest)
- Monthly cost: $0 (runs on your existing hardware)
- Electricity: ~200W for container, marginal cost compared to Proxmox host
- GPU (optional): $250 for Arc B580 (one-time)
- Benefit: Unlimited local AI inference, no API costs

## Support and Debugging

If something goes wrong:

1. Check the ARCHITECTURE.md file for detailed design documentation
2. Review relevant logs (Terraform output, Ansible output, systemd journal)
3. Verify each layer independently (is Proxmox working? Is SSH working? Is Ollama running?)
4. Try running the playbooks again (they're idempotent, so re-running is safe)

For Ollama-specific issues, see the official Ollama documentation at https://ollama.ai.

## Next Steps

1. Configure n8n to call Ollama via HTTP requests
2. Test the complete Second Brain workflow
3. If performance is acceptable on CPU, consider adding the Arc B580 GPU later
4. Monitor Ollama resource usage and adjust allocation if needed
5. Schedule weekly runs of the update playbook

Good luck with your Ollama deployment!
