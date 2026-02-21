# Ollama on Proxmox LXC: Complete IaC Architecture Guide

## Overview

This document describes a production-grade Infrastructure as Code setup for deploying Ollama AI models in a Proxmox LXC container. The setup uses Terraform to provision the container and Ansible to configure it.

## Why This Architecture?

You're building a system with three distinct layers of automation:

1. **Terraform (Infrastructure Layer):** Handles Proxmox resource allocation. Creates the LXC container with correct capabilities (nesting, keyctl), resource limits (CPU, RAM, disk), and networking. This layer is declarative—it describes the desired state and Proxmox ensures it exists.

2. **Ansible (Configuration Management Layer):** Handles everything inside the container. Installs packages, configures systemd services, downloads AI models, and manages container lifecycle. This layer is idempotent—running it multiple times produces the same result.

3. **Ollama (Application Layer):** The actual LLM inference engine running inside the container, serving models via HTTP API to your n8n workflows.

```
Your Laptop/Workstation (Terraform Commands)
    ↓
    └─→ Proxmox API (Terraform Provider)
        ↓
        └─→ Physical Hardware (LXC Container Created)
            ↓
            └─→ Container OS (Ubuntu 22.04)
                ↓
                └─→ Ansible (Configuration Management)
                    ├─→ System Updates
                    ├─→ Package Installation
                    ├─→ Ollama Installation
                    ├─→ Model Downloads
                    ├─→ Service Management
                    └─→ GPU Driver Configuration (Future)
```

## Container Specifications

The LXC container we're creating has the following configuration:

- **Operating System:** Ubuntu 22.04 (lightweight, widely supported)
- **CPU Allocation:** 8 cores (matching your Xeon E-2378's capacity)
- **Memory:** 16GB RAM (leaves ~46GB free on host for other workloads)
- **Disk:** 50GB (enough for OS + all models with overhead)
- **Unprivileged Mode:** Yes (security best practice)
- **Special Features:** nesting=1, keyctl=1 (required for GPU passthrough, useful for future Docker support)

## Why These Settings Matter

**CPU Cores:** Your Xeon E-2378 has 8 physical cores. We allocate all 8 to the container because Ollama CPU inference is CPU-intensive and you want full utilization during batch processing.

**Memory:** 16GB is intentionally conservative. Your target models need:
- Mistral 7B (Q4_K_M): 4.5GB
- nomic-embed-text: 0.5GB
- System overhead: 2-3GB
- Total: ~7GB baseline, 16GB provides comfortable headroom

When you add the GPU later, 16GB ensures model weights stay in VRAM (critical for performance) rather than spilling to system RAM.

**Special Features:**
- `nesting=1`: Allows nested containerization. Useful if you later want Docker inside the LXC or run other container-based tools.
- `keyctl=1`: Required for GPU device passthrough to work correctly. Without this, GPU detection fails.

## Model Storage Strategy

Both models are pre-downloaded during Ansible provisioning. They're stored in `/root/.ollama/models/manifests/registry.ollama.ai/library/` inside the container.

Expected storage after models downloaded:
- Mistral 7B: ~4.5GB
- nomic-embed-text: ~0.5GB
- Total: ~5GB (well within 50GB disk)

## File Organization

Your working directory should look like this:

```
ollama-proxmox/
├── terraform/
│   ├── provider.tf           # Proxmox API configuration
│   ├── variables.tf          # Input variables (customizable)
│   ├── locals.tf             # Computed values (LXC spec constants)
│   ├── main.tf               # LXC container resource definition
│   ├── outputs.tf            # Container info output to console
│   ├── terraform.tfvars      # Your specific values (API key, etc.)
│   └── .gitignore            # Never commit tfvars or .tfstate
│
├── ansible/
│   ├── inventory.ini         # Container IP and access info
│   ├── group_vars/
│   │   └── ollama_containers.yml  # Model list, package versions
│   ├── roles/
│   │   ├── system_update/        # OS updates and base packages
│   │   ├── ollama_install/       # Ollama binary + service setup
│   │   ├── model_download/       # Pre-cache models
│   │   └── gpu_setup/            # GPU driver/monitoring (optional)
│   ├── provision.yml         # Main playbook (runs all roles)
│   ├── update.yml            # Maintenance playbook
│   └── gpu_enable.yml        # Optional: enable GPU support
│
└── README.md                 # Usage instructions
```

## Workflow: First Deployment

Here's how you'd use these tools for initial deployment:

**Step 1: Customize Variables**
Edit `terraform/terraform.tfvars` with your Proxmox API credentials and desired container name.

**Step 2: Plan & Apply Terraform**
Run `terraform plan` to preview the container creation, then `terraform apply` to create it. Terraform outputs the container's IP address automatically.

**Step 3: Update Inventory**
Copy the IP address from Terraform output into `ansible/inventory.ini`.

**Step 4: Run Ansible Provisioning**
Run `ansible-playbook -i inventory.ini provision.yml`. This installs Ollama, downloads all three models (takes 10-15 minutes depending on your network), and starts the service.

**Step 5: Verify**
Test the API: `curl http://<container-ip>:11434/api/tags` should list all three models.

## Workflow: Adding a GPU (Future)

When you purchase the Arc B580, the setup automatically handles it:

**Step 1: Add GPU to LXC (Manual via Proxmox UI)**
In Proxmox, pass through the GPU device to the container. This is a one-time Proxmox configuration (cannot be automated via Terraform currently).

**Step 2: Run GPU Setup Playbook**
Run `ansible-playbook -i inventory.ini gpu_enable.yml`. This installs drivers and verifies GPU detection.

**Step 3: Restart Ollama**
Ollama auto-detects GPU on startup. Run the playbook or manually restart the Ollama service.

**Step 4: Verify GPU is Used**
Test: `curl http://<container-ip>:11434/api/generate -X POST -d '{"model":"mistral:7b","prompt":"test","stream":false}' | jq .load_duration` should show significant improvement in milliseconds.

## Maintenance: Keeping Everything Updated

The `update.yml` playbook is designed to run regularly (weekly is a good cadence):

```bash
ansible-playbook -i inventory.ini update.yml
```

This playbook will:
- Update the OS and all packages
- Update the Ollama binary (important for bug fixes and new features)
- Run any necessary migrations
- Verify all services are running
- Report any issues

You can schedule this with a cron job on your host or manually run it before important work.

## Security Considerations

**What We're Doing Right:**
- Unprivileged LXC container (non-root isolation)
- Firewall rules (only port 11434 exposed to host network)
- Service runs as non-root user where possible
- Read-only model directories (prevents accidental modification)

**What You Should Do:**
- Never expose port 11434 directly to the internet. Use a reverse proxy (nginx, Caddy) or keep it on internal network only.
- For n8n access, use localhost forwarding: `ssh -L 11434:container-ip:11434 proxmox-host`
- Keep Ollama updated frequently (security patches are released regularly)
- Monitor model downloads carefully; large models can consume significant bandwidth

## Scaling Beyond This Setup

If you later want to:

- **Run multiple LXC containers:** Use Terraform variables to loop and create multiple containers with different models/configurations.
- **Add other services (PostgreSQL, Redis):** Create separate LXC containers and manage them with Ansible.
- **Implement clustering:** Use Ansible to deploy load balancers and model distribution across multiple containers.
- **Use a database for conversation history:** The setup already supports adding services via Ansible roles.

The patterns established here generalize to any Proxmox + Ansible workflow.

## Troubleshooting Reference

**Container won't start after Terraform apply:**
- Verify Proxmox has free resources (CPU, RAM, disk)
- Check Proxmox firewall rules aren't blocking LXC creation
- Review Proxmox logs: `journalctl -u pve-container@<vmid>.service`

**Ansible can't connect to container:**
- Verify container IP in Terraform output matches `inventory.ini`
- Check SSH is running in container: `lxc exec <container-name> -- systemctl status ssh`
- Verify SSH key is in `~/.ssh/` with correct permissions (600)

**Models aren't downloading:**
- Check internet connectivity: `lxc exec <container-name> -- curl -I https://ollama.ai`
- Verify disk space: `lxc exec <container-name> -- df -h`
- Check Ollama logs: `lxc exec <container-name> -- journalctl -u ollama -f`

**GPU not detected (future):**
- Verify device passthrough is configured in Proxmox LXC settings
- Check container sees device: `lxc exec <container-name> -- lspci`
- Verify drivers installed: `lxc exec <container-name> -- apt list --installed | grep -i gpu`
- Check Ollama GPU support: `lxc exec <container-name> -- ollama list | grep gpu`

---

This architecture gives you a foundation that's:
- **Reproducible:** Run it 100 times, get the same result
- **Testable:** Verify each layer independently
- **Maintainable:** Changes are documented in code
- **Scalable:** Patterns extend to other workloads
- **Learning-friendly:** Each file has clear explanations

Next sections contain the actual code files organized by purpose.
