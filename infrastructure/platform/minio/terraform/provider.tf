# provider.tf - Proxmox Provider Configuration

terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "= 0.96.0"
    }
  }
  required_version = ">= 1.0"
}

provider "proxmox" {
  endpoint  = var.proxmox_endpoint
  api_token = "${var.proxmox_api_token_id}=${var.proxmox_api_token}"
  insecure  = var.proxmox_tls_insecure
}
