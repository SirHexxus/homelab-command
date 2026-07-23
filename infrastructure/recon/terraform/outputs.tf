# outputs.tf - Terraform Output Values

output "vm_vmid" {
  description = "Proxmox VM ID"
  value       = proxmox_virtual_environment_vm.recon.vm_id
}

output "vm_name" {
  description = "Name assigned to the VM"
  value       = proxmox_virtual_environment_vm.recon.name
}

output "vm_node" {
  description = "Proxmox node running this VM"
  value       = proxmox_virtual_environment_vm.recon.node_name
}

output "vm_network_config" {
  description = "Network configuration"
  value = {
    bridge     = local.network_config.bridge
    using_dhcp = local.network_config.dhcp
    static_ip  = local.network_config.ipv4
    gateway    = local.network_config.gateway
    vlan_tag   = local.network_config.vlan_tag
  }
}

output "deployment_instructions" {
  description = "Next steps after VM creation"
  value       = <<-EOT

    ============================================================
    Recon detonation box created (VLAN 66 — quarantined)
    ============================================================

    Static IP: ${local.network_config.ipv4 != null ? local.network_config.ipv4 : "N/A (DHCP)"}
    On-boot:   disabled (quarantine box — start it manually only when in use)

    ORDER OF OPERATIONS — do NOT skip:

    1. Open the provisioning egress window (pfSense):
         cd ../../network/pfsense/ansible
         ansible-playbook -i inventory.ini provision.yml \
           -e recon_provisioning_egress=true --tags recon --ask-vault-pass

    2. Wait ~1-2 min for cloud-init (qemu-guest-agent), then verify SSH
       (only reachable from the wired VLAN 10 workstation):
         ssh ${var.vm_user}@10.0.66.10

    3. Provision the toolchain:
         cd ../../../recon/ansible
         ansible-playbook -i inventory.ini provision.yml --ask-vault-pass

    4. CLOSE the egress window and snapshot BEFORE importing any site clone:
         cd ../../network/pfsense/ansible
         ansible-playbook -i inventory.ini provision.yml \
           -e recon_provisioning_egress=false --tags recon --ask-vault-pass
         # then snapshot the VM in Proxmox: "clean-provisioned"

    5. Only now import the site clone into /srv/recon and begin analysis.
    ============================================================
    EOT
}
