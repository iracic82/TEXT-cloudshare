# CloudShare Creation Script - Azure Infrastructure for Infoblox Lab
# Runs automatically on each student's dedicated Azure subscription
# Paste this into a SEPARATE CloudShare Creation Script for Azure

# ── Variables ────────────────────────────────────────────────────────

variable "azure_vnets" {
  default = {
    Vnet1 = {
      resource_group = "WebProdEu1"
      vnet_name      = "WebProdEu_Vnet1"
      subnet_name    = "WebProdEu_Vnet_subnet1"
      instance_name  = "WebprodEu1"
      private_ip     = "10.10.1.100"
      vnet_cidr      = "10.10.0.0/16"
      subnet_cidr    = "10.10.1.0/24"
      enable_peering = true
    }
    Vnet2 = {
      resource_group = "WebProdEu2"
      vnet_name      = "WebProdEu_Vnet2"
      subnet_name    = "WebProdEu_Vnet_subnet2"
      instance_name  = "WebprodEu2"
      private_ip     = "10.30.1.100"
      vnet_cidr      = "10.30.0.0/16"
      subnet_cidr    = "10.30.1.0/24"
      enable_peering = true
    }
  }
}

# ── Resource Groups ──────────────────────────────────────────────────

resource "azurerm_resource_group" "rgs" {
  for_each = var.azure_vnets
  name     = each.value.resource_group
  location = "North Europe"
}

# ── Virtual Networks ─────────────────────────────────────────────────

resource "azurerm_virtual_network" "vnets" {
  for_each            = var.azure_vnets
  name                = each.value.vnet_name
  address_space       = [each.value.vnet_cidr]
  location            = "North Europe"
  resource_group_name = azurerm_resource_group.rgs[each.key].name
}

# ── Subnets ──────────────────────────────────────────────────────────

resource "azurerm_subnet" "subnets" {
  for_each             = var.azure_vnets
  name                 = each.value.subnet_name
  resource_group_name  = azurerm_resource_group.rgs[each.key].name
  virtual_network_name = azurerm_virtual_network.vnets[each.key].name
  address_prefixes     = [each.value.subnet_cidr]
}

# ── Network Interfaces ───────────────────────────────────────────────

resource "azurerm_network_interface" "nics" {
  for_each            = var.azure_vnets
  name                = "${each.value.instance_name}-nic"
  location            = "North Europe"
  resource_group_name = azurerm_resource_group.rgs[each.key].name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.subnets[each.key].id
    private_ip_address_allocation = "Static"
    private_ip_address            = each.value.private_ip
  }
}

# ── Network Security Group ───────────────────────────────────────────

resource "azurerm_network_security_group" "nsg" {
  for_each            = var.azure_vnets
  name                = "${each.value.instance_name}-nsg"
  location            = "North Europe"
  resource_group_name = azurerm_resource_group.rgs[each.key].name

  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "ICMP"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Icmp"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "10.0.0.0/8"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_interface_security_group_association" "nsg_assoc" {
  for_each                  = var.azure_vnets
  network_interface_id      = azurerm_network_interface.nics[each.key].id
  network_security_group_id = azurerm_network_security_group.nsg[each.key].id
}

# ── Virtual Machines ─────────────────────────────────────────────────

resource "azurerm_linux_virtual_machine" "vms" {
  for_each            = var.azure_vnets
  name                = each.value.instance_name
  resource_group_name = azurerm_resource_group.rgs[each.key].name
  location            = "North Europe"
  size                = "Standard_D2s_v4"
  admin_username      = "linuxuser"
  admin_password      = "Infoblox123!"
  disable_password_authentication = false

  network_interface_ids = [azurerm_network_interface.nics[each.key].id]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }
}

# ── VNet Peering ─────────────────────────────────────────────────────

resource "azurerm_virtual_network_peering" "peer_1_to_2" {
  name                      = "peer-Vnet1-to-Vnet2"
  resource_group_name       = azurerm_resource_group.rgs["Vnet1"].name
  virtual_network_name      = azurerm_virtual_network.vnets["Vnet1"].name
  remote_virtual_network_id = azurerm_virtual_network.vnets["Vnet2"].id
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
}

resource "azurerm_virtual_network_peering" "peer_2_to_1" {
  name                      = "peer-Vnet2-to-Vnet1"
  resource_group_name       = azurerm_resource_group.rgs["Vnet2"].name
  virtual_network_name      = azurerm_virtual_network.vnets["Vnet2"].name
  remote_virtual_network_id = azurerm_virtual_network.vnets["Vnet1"].id
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
}

# ── Azure Private DNS Zone + Records ─────────────────────────────────

resource "azurerm_private_dns_zone" "private_dns" {
  name                = "infolab.com"
  resource_group_name = azurerm_resource_group.rgs["Vnet1"].name
}

resource "azurerm_private_dns_zone_virtual_network_link" "vnet_links" {
  for_each              = var.azure_vnets
  name                  = "${each.key}-dns-link"
  resource_group_name   = azurerm_resource_group.rgs["Vnet1"].name
  private_dns_zone_name = azurerm_private_dns_zone.private_dns.name
  virtual_network_id    = azurerm_virtual_network.vnets[each.key].id
  registration_enabled  = false
}

resource "azurerm_private_dns_a_record" "dns_records" {
  for_each            = var.azure_vnets
  name                = "azure-${lower(each.value.instance_name)}"
  zone_name           = azurerm_private_dns_zone.private_dns.name
  resource_group_name = azurerm_resource_group.rgs["Vnet1"].name
  ttl                 = 300
  records             = [each.value.private_ip]
}

# ── Outputs ──────────────────────────────────────────────────────────

output "vnet_ids" {
  value = { for k, v in azurerm_virtual_network.vnets : k => v.id }
}

output "vm_private_ips" {
  value = { for k, v in var.azure_vnets : k => v.private_ip }
}

output "dns_records" {
  value = [for k, v in var.azure_vnets : "azure-${lower(v.instance_name)}.infolab.com => ${v.private_ip}"]
}
