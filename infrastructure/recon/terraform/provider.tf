# provider.tf - Proxmox Provider Configuration
#
# Configures the Terraform provider for Proxmox VE for the recon detonation box.

terraform {
  required_version = ">= 1.0"

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "= 0.98.1"
    }
  }
}

provider "proxmox" {
  endpoint  = var.proxmox_endpoint
  api_token = "${var.proxmox_api_token_id}=${var.proxmox_api_token}"
  insecure  = var.proxmox_tls_insecure

  # SSH access to the node is required for snippet uploads
  # (proxmox_virtual_environment_file with source_raw).
  ssh {
    agent       = false
    username    = "root"
    private_key = file(pathexpand(var.proxmox_ssh_private_key_file))
  }
}
