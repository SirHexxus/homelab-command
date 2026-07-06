# outputs.tf - Terraform Output Values
#
# These outputs display important information after VM creation.

output "vm_vmid" {
  description = "Proxmox VM ID"
  value       = proxmox_virtual_environment_vm.hephaestus.vm_id
}

output "vm_name" {
  description = "Name assigned to the VM"
  value       = proxmox_virtual_environment_vm.hephaestus.name
}

output "vm_node" {
  description = "Proxmox node running this VM"
  value       = proxmox_virtual_environment_vm.hephaestus.node_name
}

output "vm_network_config" {
  description = "Network configuration"
  value = {
    bridge     = local.network_config.bridge
    using_dhcp = local.network_config.dhcp
    static_ip  = local.network_config.ipv4
    gateway    = local.network_config.gateway
  }
}

output "ssh_key_path" {
  description = "SSH public key used for VM access"
  value       = var.ssh_public_key_file
}

output "deployment_instructions" {
  description = "Next steps after VM creation"
  value       = <<-EOT

    ============================================================
    Hephaestus VM Created Successfully!
    ============================================================

    Next steps:

    1. Wait 1-2 minutes for cloud-init to finish first boot
       (package update + qemu-guest-agent install)

    2. Static IP assigned: ${local.network_config.ipv4 != null ? local.network_config.ipv4 : "N/A (using DHCP)"}

    3. Verify SSH access:
       ssh ${var.vm_user}@10.0.50.30

    4. Run Ansible provisioning:
       cd infrastructure/hephaestus/ansible/
       ansible-playbook -i inventory.ini provision.yml --ask-vault-pass

    5. Verify Firecrawl is running:
       curl http://10.0.50.30:3002/

    ============================================================
    EOT
}
