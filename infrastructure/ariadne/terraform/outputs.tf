# outputs.tf - Terraform Output Values

# -----------------------------------------------------------------------------
# NGINX Proxy Manager
# -----------------------------------------------------------------------------

output "npm_vmid" {
  description = "Proxmox VM/Container ID for NPM"
  value       = proxmox_virtual_environment_container.npm.vm_id
}

output "npm_ip" {
  description = "Static IP assigned to NPM"
  value       = local.npm_network_config.ipv4
}

# -----------------------------------------------------------------------------
# Authelia
# -----------------------------------------------------------------------------

output "authelia_vmid" {
  description = "Proxmox VM/Container ID for Authelia"
  value       = proxmox_virtual_environment_container.authelia.vm_id
}

output "authelia_ip" {
  description = "Static IP assigned to Authelia"
  value       = local.authelia_network_config.ipv4
}

# -----------------------------------------------------------------------------
# Umami
# -----------------------------------------------------------------------------

output "umami_vmid" {
  description = "Proxmox VM/Container ID for Umami"
  value       = proxmox_virtual_environment_container.umami.vm_id
}

output "umami_ip" {
  description = "Static IP assigned to Umami"
  value       = local.umami_network_config.ipv4
}

# -----------------------------------------------------------------------------
# Next steps
# -----------------------------------------------------------------------------

output "deployment_instructions" {
  description = "Next steps after container creation"
  value       = <<-EOT

    ============================================================
    Ariadne Containers Created
    ============================================================

    NPM:      ${local.npm_network_config.ipv4} (VMID ${var.npm_vmid})
    Authelia: ${local.authelia_network_config.ipv4} (VMID ${var.authelia_vmid})
    Umami:    ${local.umami_network_config.ipv4} (VMID ${var.umami_vmid})

    Next steps (see Ariadne Design Doc §13 for full order):

    1. Wait 30-60 seconds for containers to boot

    2. Verify SSH access:
       ssh root@10.0.60.10   # NPM
       ssh root@10.0.60.11   # Authelia
       ssh root@10.0.50.18   # Umami

    3. Run Ansible provisioning:
       cd infrastructure/ariadne/ansible/
       ansible-playbook -i inventory.ini provision.yml

    4. Configure pfSense inbound NAT (80/443 → 10.0.60.10)
       (manual — pfSense UI, Firewall > NAT > Port Forward)

    5. After Umami is running, create the Umami database in Postgres:
       psql -h 10.0.50.14 -U postgres -c "CREATE DATABASE umami;"
       (Umami will initialise its own schema on first start)

    ============================================================
    EOT
}
