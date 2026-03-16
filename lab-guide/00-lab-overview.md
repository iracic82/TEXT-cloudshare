# Infoblox - Universal DNS Management Multi-Cloud

## Lab Overview

In this lab, you'll walk through how Infoblox Universal DDI (UDDI) delivers a centralized control plane for DNS management across multi-cloud environments—specifically AWS and Azure.

You'll simulate a real-world enterprise scenario where:

- Multiple VPCs and VNets span across AWS (eu-west-2) and Azure (northerneurope)
- DNS zones and records are managed in the Infoblox UDDI Portal
- Changes made in UDDI (e.g., new A/CNAME records, updates) are synchronized bi-directionally to AWS Route 53 Private Hosted Zones and Azure Private DNS Zones
- Cross-cloud services and applications resolve consistently across platforms
- You gain consolidated visibility, auditing, and change tracking across all platforms via Infoblox

### Key Learning Objectives

- Understand how Infoblox UDDI acts as a DNS Single Source of Truth
- Learn how DNS records are synced between UDDI, AWS Route 53, and Azure DNS
- See DNS records propagate in real time across clouds
- Validate name resolution across multi-cloud app stacks
- Experience operational simplicity with a unified DNS control plane

### Lab Environment

Your CloudShare lab environment includes:
- **Ubuntu VM** - Shell access for running Terraform and scripts
- **AWS Console** - Windows VM with browser access to your dedicated AWS account
- **Infoblox Portal** - Access via https://portal.infoblox.com/

> **NOTE:** This environment is *real*! AWS and Azure Cloud Accounts have been created for each student. No bitcoin mining, please! :)

### Challenges

1. [Review Architecture and Deploy Resources](./01-review-architecture-and-deploy-resources.md)
2. [Managing Public Cloud Providers](./02-managing-csps.md)
3. [Quiz - Your Experience Matters](./03-quiz.md)
