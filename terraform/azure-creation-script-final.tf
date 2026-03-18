variable "prefix" {
  default = "infoblox"
}

resource "azurerm_virtual_network" "vnet1" {
  name                = "WebProdEu_Vnet1"
  address_space       = ["10.10.0.0/16"]
  location            = "${data.azurerm_resource_group.main.location}"
  resource_group_name = "${data.azurerm_resource_group.main.name}"
}

resource "azurerm_virtual_network" "vnet2" {
  name                = "WebProdEu_Vnet2"
  address_space       = ["10.30.0.0/16"]
  location            = "${data.azurerm_resource_group.main.location}"
  resource_group_name = "${data.azurerm_resource_group.main.name}"
}

resource "azurerm_subnet" "subnet1" {
  name                 = "WebProdEu_Vnet_subnet1"
  resource_group_name  = "${data.azurerm_resource_group.main.name}"
  virtual_network_name = "${azurerm_virtual_network.vnet1.name}"
  address_prefixes     = ["10.10.1.0/24"]
}

resource "azurerm_subnet" "subnet2" {
  name                 = "WebProdEu_Vnet_subnet2"
  resource_group_name  = "${data.azurerm_resource_group.main.name}"
  virtual_network_name = "${azurerm_virtual_network.vnet2.name}"
  address_prefixes     = ["10.30.1.0/24"]
}

resource "azurerm_network_security_group" "nsg" {
  name                = "${var.prefix}-nsg"
  location            = "${data.azurerm_resource_group.main.location}"
  resource_group_name = "${data.azurerm_resource_group.main.name}"

  security_rule {
    name                       = "allin"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "allout"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_interface" "nic1" {
  name                = "WebprodEu1-nic"
  location            = "${data.azurerm_resource_group.main.location}"
  resource_group_name = "${data.azurerm_resource_group.main.name}"

  ip_configuration {
    name                          = "internal"
    subnet_id                     = "${azurerm_subnet.subnet1.id}"
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.10.1.100"
  }
}

resource "azurerm_network_interface" "nic2" {
  name                = "WebprodEu2-nic"
  location            = "${data.azurerm_resource_group.main.location}"
  resource_group_name = "${data.azurerm_resource_group.main.name}"

  ip_configuration {
    name                          = "internal"
    subnet_id                     = "${azurerm_subnet.subnet2.id}"
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.30.1.100"
  }
}

resource "azurerm_network_interface_security_group_association" "nsg_assoc1" {
  network_interface_id      = "${azurerm_network_interface.nic1.id}"
  network_security_group_id = "${azurerm_network_security_group.nsg.id}"
}

resource "azurerm_network_interface_security_group_association" "nsg_assoc2" {
  network_interface_id      = "${azurerm_network_interface.nic2.id}"
  network_security_group_id = "${azurerm_network_security_group.nsg.id}"
}

resource "azurerm_virtual_machine" "vm1" {
  name                  = "WebprodEu1"
  location              = "${data.azurerm_resource_group.main.location}"
  resource_group_name   = "${data.azurerm_resource_group.main.name}"
  network_interface_ids = ["${azurerm_network_interface.nic1.id}"]
  vm_size               = "Standard_D2s_v3"

  storage_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }

  storage_os_disk {
    name              = "WebprodEu1-osdisk"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  os_profile {
    computer_name  = "WebprodEu1"
    admin_username = "linuxuser"
    admin_password = "Infoblox123!"
  }

  os_profile_linux_config {
    disable_password_authentication = false
  }

  tags = {
    environment = "lab"
  }
}

resource "azurerm_virtual_machine" "vm2" {
  name                  = "WebprodEu2"
  location              = "${data.azurerm_resource_group.main.location}"
  resource_group_name   = "${data.azurerm_resource_group.main.name}"
  network_interface_ids = ["${azurerm_network_interface.nic2.id}"]
  vm_size               = "Standard_D2s_v3"

  storage_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }

  storage_os_disk {
    name              = "WebprodEu2-osdisk"
    caching           = "ReadWrite"
    create_option     = "FromImage"
    managed_disk_type = "Standard_LRS"
  }

  os_profile {
    computer_name  = "WebprodEu2"
    admin_username = "linuxuser"
    admin_password = "Infoblox123!"
  }

  os_profile_linux_config {
    disable_password_authentication = false
  }

  tags = {
    environment = "lab"
  }
}

resource "azurerm_virtual_network_peering" "peer_1_to_2" {
  name                         = "peer-Vnet1-to-Vnet2"
  resource_group_name          = "${data.azurerm_resource_group.main.name}"
  virtual_network_name         = "${azurerm_virtual_network.vnet1.name}"
  remote_virtual_network_id    = "${azurerm_virtual_network.vnet2.id}"
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
}

resource "azurerm_virtual_network_peering" "peer_2_to_1" {
  name                         = "peer-Vnet2-to-Vnet1"
  resource_group_name          = "${data.azurerm_resource_group.main.name}"
  virtual_network_name         = "${azurerm_virtual_network.vnet2.name}"
  remote_virtual_network_id    = "${azurerm_virtual_network.vnet1.id}"
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
}

resource "azurerm_private_dns_zone" "private_dns" {
  name                = "infolab.com"
  resource_group_name = "${data.azurerm_resource_group.main.name}"
}

resource "azurerm_private_dns_zone_virtual_network_link" "vnet1_link" {
  name                  = "vnet1-dns-link"
  resource_group_name   = "${data.azurerm_resource_group.main.name}"
  private_dns_zone_name = "${azurerm_private_dns_zone.private_dns.name}"
  virtual_network_id    = "${azurerm_virtual_network.vnet1.id}"
  registration_enabled  = false
}

resource "azurerm_private_dns_zone_virtual_network_link" "vnet2_link" {
  name                  = "vnet2-dns-link"
  resource_group_name   = "${data.azurerm_resource_group.main.name}"
  private_dns_zone_name = "${azurerm_private_dns_zone.private_dns.name}"
  virtual_network_id    = "${azurerm_virtual_network.vnet2.id}"
  registration_enabled  = false
}

resource "azurerm_private_dns_a_record" "dns_vm1" {
  name                = "azure-webprodeu1"
  zone_name           = "${azurerm_private_dns_zone.private_dns.name}"
  resource_group_name = "${data.azurerm_resource_group.main.name}"
  ttl                 = 300
  records             = ["10.10.1.100"]
}

resource "azurerm_private_dns_a_record" "dns_vm2" {
  name                = "azure-webprodeu2"
  zone_name           = "${azurerm_private_dns_zone.private_dns.name}"
  resource_group_name = "${data.azurerm_resource_group.main.name}"
  ttl                 = 300
  records             = ["10.30.1.100"]
}
