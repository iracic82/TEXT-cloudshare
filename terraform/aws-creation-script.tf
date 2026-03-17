# CloudShare Creation Script - AWS Infrastructure for Infoblox Lab
# CloudShare manages the provider and region automatically

# ── Variables ────────────────────────────────────────────────────────

variable "eu_west_vpcs" {
  default = {
    VPC1 = {
      vpc_name    = "WebSvcsProdEu1"
      vpc_cidr    = "10.20.0.0/24"
      subnet_cidr = "10.20.0.0/24"
      private_ip  = "10.20.0.100"
      app_fqdn    = "app1.infolab.com"
      ec2_name    = "WebServerProdEu1"
    }
    VPC2 = {
      vpc_name    = "WebSvcsProdEu2"
      vpc_cidr    = "10.20.2.0/24"
      subnet_cidr = "10.20.2.0/24"
      private_ip  = "10.20.2.100"
      app_fqdn    = "app2.infolab.com"
      ec2_name    = "WebServerProdEu2"
    }
    VPC3 = {
      vpc_name    = "WebSvcsProdEu3"
      vpc_cidr    = "10.20.3.0/24"
      subnet_cidr = "10.20.3.0/24"
      private_ip  = "10.20.3.100"
      app_fqdn    = "app3.infolab.com"
      ec2_name    = "WebServerProdEu3"
    }
  }
}

# ── Data Sources ─────────────────────────────────────────────────────

data "aws_availability_zones" "available" {}

data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-kernel-5*"]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

data "aws_caller_identity" "current" {}

# ── IAM Access Key for Terraform on Ubuntu VM ────────────────────────

resource "aws_iam_user" "lab_user" {
  name = "infoblox-lab-user"
  tags = {
    Name = "Infoblox Lab Programmatic Access"
  }
}

resource "aws_iam_user_policy_attachment" "lab_user_admin" {
  user       = aws_iam_user.lab_user.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

resource "aws_iam_access_key" "lab_user_key" {
  user = aws_iam_user.lab_user.name
}

# ── VPCs ─────────────────────────────────────────────────────────────

resource "aws_vpc" "eu_vpcs" {
  for_each             = var.eu_west_vpcs
  cidr_block           = each.value.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = each.value.vpc_name
  }
}

# ── Subnets ──────────────────────────────────────────────────────────

resource "aws_subnet" "eu_subnets" {
  for_each          = var.eu_west_vpcs
  vpc_id            = aws_vpc.eu_vpcs[each.key].id
  cidr_block        = each.value.subnet_cidr
  availability_zone = data.aws_availability_zones.available.names[0]
  tags = {
    Name = "${each.value.vpc_name}-subnet"
  }
}

# ── Internet Gateways ────────────────────────────────────────────────

resource "aws_internet_gateway" "eu_igws" {
  for_each = var.eu_west_vpcs
  vpc_id   = aws_vpc.eu_vpcs[each.key].id
  tags = {
    Name = "${each.value.vpc_name}-IGW"
  }
}

# ── Route Tables ─────────────────────────────────────────────────────

resource "aws_route_table" "eu_rts" {
  for_each = var.eu_west_vpcs
  vpc_id   = aws_vpc.eu_vpcs[each.key].id
  tags = {
    Name = "${each.value.vpc_name}-RT"
  }
}

resource "aws_route_table_association" "eu_rt_assocs" {
  for_each       = var.eu_west_vpcs
  route_table_id = aws_route_table.eu_rts[each.key].id
  subnet_id      = aws_subnet.eu_subnets[each.key].id
}

resource "aws_route" "eu_igw_routes" {
  for_each               = var.eu_west_vpcs
  route_table_id         = aws_route_table.eu_rts[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.eu_igws[each.key].id
}

# ── Security Groups ──────────────────────────────────────────────────

resource "aws_security_group" "eu_sgs" {
  for_each = var.eu_west_vpcs
  name     = "${each.value.vpc_name}-sg"
  vpc_id   = aws_vpc.eu_vpcs[each.key].id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = ["10.0.0.0/8"]
  }
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "${each.value.vpc_name}-sg"
  }
}

# ── Key Pairs ────────────────────────────────────────────────────────

resource "tls_private_key" "eu_keys" {
  for_each  = var.eu_west_vpcs
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "eu_keypairs" {
  for_each   = var.eu_west_vpcs
  key_name   = "${each.value.vpc_name}-key"
  public_key = tls_private_key.eu_keys[each.key].public_key_openssh
}

# ── Network Interfaces ───────────────────────────────────────────────

resource "aws_network_interface" "eu_enis" {
  for_each        = var.eu_west_vpcs
  subnet_id       = aws_subnet.eu_subnets[each.key].id
  private_ips     = [each.value.private_ip]
  security_groups = [aws_security_group.eu_sgs[each.key].id]
  tags = {
    Name = "${each.value.ec2_name}-eni"
  }
}

# ── EC2 Instances ────────────────────────────────────────────────────

resource "aws_instance" "eu_instances" {
  for_each      = var.eu_west_vpcs
  ami           = data.aws_ami.amazon_linux_2.id
  instance_type = "t3a.micro"
  key_name      = aws_key_pair.eu_keypairs[each.key].key_name

  network_interface {
    network_interface_id = aws_network_interface.eu_enis[each.key].id
    device_index         = 0
  }

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y httpd
    systemctl start httpd
    systemctl enable httpd
    echo "<h1>${each.value.ec2_name}</h1>" > /var/www/html/index.html
  EOF

  tags = {
    Name = each.value.ec2_name
  }
}

# ── Elastic IPs ──────────────────────────────────────────────────────

resource "aws_eip" "eu_eips" {
  for_each                  = var.eu_west_vpcs
  domain                    = "vpc"
  instance                  = aws_instance.eu_instances[each.key].id
  associate_with_private_ip = each.value.private_ip
  depends_on                = [aws_internet_gateway.eu_igws]
}

# ── Transit Gateway ──────────────────────────────────────────────────

resource "aws_ec2_transit_gateway" "eu_tgw" {
  description = "EU-TGW"
  tags = {
    Name = "EU-TGW"
  }
}

resource "aws_ec2_transit_gateway_route_table" "eu_tgw_rt" {
  transit_gateway_id = aws_ec2_transit_gateway.eu_tgw.id
  tags = {
    Name = "EU-TGW-RouteTable"
  }
}

resource "aws_ec2_transit_gateway_vpc_attachment" "eu_tgw_attachments" {
  for_each           = var.eu_west_vpcs
  subnet_ids         = [aws_subnet.eu_subnets[each.key].id]
  transit_gateway_id = aws_ec2_transit_gateway.eu_tgw.id
  vpc_id             = aws_vpc.eu_vpcs[each.key].id

  appliance_mode_support = "enable"
  dns_support            = "enable"

  tags = {
    Name = "${each.value.vpc_name}-TGW-Attachment"
  }
}

resource "aws_route" "eu_tgw_routes" {
  for_each               = var.eu_west_vpcs
  route_table_id         = aws_route_table.eu_rts[each.key].id
  destination_cidr_block = "10.20.0.0/16"
  transit_gateway_id     = aws_ec2_transit_gateway.eu_tgw.id
}

resource "aws_ec2_transit_gateway_route" "eu_tgw_vpc_routes" {
  for_each                       = var.eu_west_vpcs
  transit_gateway_route_table_id = aws_ec2_transit_gateway_route_table.eu_tgw_rt.id
  destination_cidr_block         = each.value.vpc_cidr
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_vpc_attachment.eu_tgw_attachments[each.key].id
}

# ── Route53 Private Hosted Zone ──────────────────────────────────────
# NOTE: Students will create these manually during the lab via Terraform on the Ubuntu VM
# Uncomment if you want them pre-created:

# resource "aws_route53_zone" "private_zone" {
#   name = "infolab.com"
#   dynamic "vpc" {
#     for_each = aws_vpc.eu_vpcs
#     content {
#       vpc_id     = vpc.value.id
#       vpc_region = "eu-west-2"
#     }
#   }
#   tags = { Name = "InfobloxPrivateZone" }
# }

# resource "aws_route53_record" "dns_records" {
#   for_each = var.eu_west_vpcs
#   zone_id  = aws_route53_zone.private_zone.id
#   name     = each.value.app_fqdn
#   type     = "A"
#   ttl      = 300
#   records  = [each.value.private_ip]
# }

# ── Infoblox Discovery IAM Role ─────────────────────────────────────

resource "aws_iam_role" "infoblox_discovery" {
  name = "infoblox_discovery"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::171274298921:root"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = "placeholder-update-from-portal"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "infoblox_discovery_policy" {
  role       = aws_iam_role.infoblox_discovery.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

resource "aws_iam_role_policy" "infoblox_route53_write" {
  name = "InfobloxRoute53Write"
  role = aws_iam_role.infoblox_discovery.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "route53:ChangeResourceRecordSets",
          "route53:CreateHostedZone",
          "route53:DeleteHostedZone"
        ]
        Resource = "*"
      }
    ]
  })
}

# ── Outputs ──────────────────────────────────────────────────────────
# These outputs should be accessible in CloudShare

output "aws_access_key_id" {
  value     = aws_iam_access_key.lab_user_key.id
  sensitive = true
}

output "aws_secret_access_key" {
  value     = aws_iam_access_key.lab_user_key.secret
  sensitive = true
}

output "aws_account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  value = "eu-west-2"
}

output "infoblox_discovery_role_arn" {
  value = aws_iam_role.infoblox_discovery.arn
}

output "vpc_ids" {
  value = { for k, v in aws_vpc.eu_vpcs : k => v.id }
}

output "ec2_public_ips" {
  value = { for k, v in aws_eip.eu_eips : k => v.public_ip }
}

output "ec2_private_ips" {
  value = { for k, v in var.eu_west_vpcs : k => v.private_ip }
}

output "ssh_access" {
  value = [for k, v in aws_eip.eu_eips : "${var.eu_west_vpcs[k].ec2_name} => ssh ec2-user@${v.public_ip}"]
}
