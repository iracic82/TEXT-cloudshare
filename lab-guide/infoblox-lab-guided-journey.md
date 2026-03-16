# Infoblox - Universal DNS Management Multi-Cloud

## Lab Overview

In this lab, you'll walk through how Infoblox Universal DDI (UDDI) delivers a centralized control plane for DNS management across multi-cloud environments—specifically AWS and Azure.

You'll simulate a real-world enterprise scenario where:

- Multiple VPCs and VNets span across AWS (eu-west-2) and Azure (northerneurope)
- DNS zones and records are managed in the Infoblox UDDI Portal
- Changes made in UDDI are synchronized bi-directionally to AWS Route 53 Private Hosted Zones and Azure Private DNS Zones
- Cross-cloud services and applications resolve consistently across platforms
- You gain consolidated visibility, auditing, and change tracking via Infoblox

### Key Learning Objectives

- Understand how Infoblox UDDI acts as a DNS Single Source of Truth
- Learn how DNS records are synced between UDDI, AWS Route 53, and Azure DNS
- See DNS records propagate in real time across clouds
- Validate name resolution across multi-cloud app stacks
- Experience operational simplicity with a unified DNS control plane

> **NOTE:** This environment is *real*! AWS and Azure Cloud Accounts have been created for each student. No bitcoin mining, please! :)

---

# Chapter 1: Review Architecture and Deploy Resources

In this section we will:
1. Review the cloud architecture
2. Login to your cloud account consoles
3. Deploy resources onto your cloud regions
4. Create your Infoblox Portal user

---

## 1) Review Cloud Architecture

First lets review the cloud architecture that has been provisioned for your Infoblox Lab experience.

Navigate to the Lab Diagram and review. This is what we're building today!

## 2) Login to your cloud account consoles

### AWS Console

1. Open the **AWS Console** VM in your CloudShare environment (click on the VM tab above).
2. Select **IAM Account** (not root) on the login screen.

![AWS Login](Screenshot_2025-07-12_at_11.23.29.png)

3. Enter the AWS Account ID, Username, and Password. Your AWS credentials are available in the CloudShare environment details panel.

> **Note:** Avoid the root account login — this lab is configured for IAM users only.

---

### Azure Console

1. Open a browser and navigate to https://portal.azure.com
2. Use the Azure credentials provided in your CloudShare environment details.
3. Skip the Microsoft Onboarding Tour if prompted.
4. Once logged in, use the top search bar to navigate to:
   - Virtual Network
   - Private DNS Zones
   - Resource groups

---

## 3) Deploy resources onto your cloud regions

Now that you've logged into both cloud consoles, it's time to deploy the infrastructure.

Switch to the **Ubuntu 22.04 LTS Server** tab in your CloudShare environment.

### Deploy AWS resources in EU

Core resources have already been provisioned using Terraform. Verify:

```bash
cd ~/infoblox-lab/Infoblox-PoC/terraform
terraform output
```

Set up the DNS infrastructure:

```bash
cd ~/infoblox-lab/Infoblox-PoC/terraform
terraform apply --auto-approve -target=aws_route53_zone.private_zone -target=aws_route53_record.dns_records
```

### Deploy Azure resources in North Europe

Azure resources have also been pre-deployed. Verify:

```bash
cd ~/infoblox-lab/Infoblox-PoC/terraform
terraform output
```

Set up Azure DNS infrastructure:

```bash
cd ~/infoblox-lab/Infoblox-PoC/terraform
terraform apply --auto-approve -target=azurerm_private_dns_zone.private_dns_azone -target=azurerm_private_dns_zone_virtual_network_link.eu_vnet_links -target=azurerm_private_dns_a_record.eu_dns_records
```

## 4) Create Admin User to your Infoblox Portal Dashboard

Your user account and sandbox tenant have already been created automatically when this environment started.

> **IMPORTANT:** If you've never accessed the Infoblox Portal before using the email address you used to start this lab, please follow the steps below to activate your account.

### Activate Your Account

1. Check the inbox of the email you used to register for the lab.
2. You will receive an email with subject **"Infoblox User Account Activation"**. Click **"Activate Account"**.

![Account Activation](Screenshot_2025-04-01_at_11.15.44.png)

3. Create a new password when prompted.

![Set Password](Screenshot_2025-04-01_at_11.19.01.png)

4. Once password is set, open a browser and go to https://portal.infoblox.com/
5. Log in with your credentials.

![Portal Access](Screenshot_2025-04-01_at_11.01.03.png)

6. In the upper-left corner, click the drop-down menu. Use **"Find Account"** to search for your sandbox. Your Sandbox ID can be found on the Ubuntu VM:

```bash
cat /opt/cloudshare-lab/state/sandbox_id.txt
```

![Find Account](Screenshot_2025-07-18_at_09.16.24.png)

---

### Troubleshooting: Forgot Password

1. Go to https://portal.infoblox.com/
2. Click **"Need Assistance"** at the bottom.

![Need Assistance](Screenshot_2025-04-01_at_10.52.47.png)

3. Select **"Forgot Password"**.

![Forgot Password](Screenshot_2025-04-01_at_10.52.57.png)

4. Check your email for **"Account Password Reset"** and click **"Reset Password"**.

![Reset Email](Screenshot_2025-04-01_at_11.42.21.png)

5. Set your new password, then return to step 4 above.

---

# Chapter 2: Managing Public Cloud Providers

## Universal DDI Management - The Backbone of Modern Network Services

Universal DDI Management is the industry's first and most comprehensive SaaS-based solution for managing critical DNS, DHCP, and IPAM services across hybrid and multicloud environments.

![UDDI Overview](Screenshot_2025-07-03_at_20.31.01.png)

### What It Does

- **Central Hub** - Single SaaS control plane for all network services
- **Comprehensive Consolidation** - Unifies DNS, DHCP, and IP address management across Infoblox NIOS/NIOS-X, Amazon Route 53, Azure DNS, Google Cloud DNS
- **Streamlined Operation** - Eliminates silos and unifies policy

![Value Points](Screenshot_2025-07-03_at_20.35.07.png)

### Four Core Value Points

1. **Centralized Control** - Single interface for DNS/DHCP/IPAM across any environment
2. **Deep Integration** - Bridges traditional DNS with cloud-native platforms
3. **Operational Efficiency** - Reduces overhead, accelerates delivery
4. **Scalability and Flexibility** - Scales with your architecture

![Single Pane](Screenshot_2025-07-03_at_20.36.56.png)

---

## Cloud Discovery Overview (AWS & Azure)

**Infoblox Universal Asset Insights** automatically discovers and tracks cloud resources using native cloud APIs.

### AWS Discovery

Infoblox connects to AWS via a cross-account IAM role using a secure External ID. Discovered resources include:
- EC2 instances, VPCs, subnets
- Route tables, NAT and Internet Gateways
- Load Balancers (ALB, NLB)
- Route 53 Hosted Zones and Records
- Tags, regions, and metadata

![IAM Role](Screenshot_2025-07-09_at_08.54.34.png)

![IAM Policy](Screenshot_2025-07-09_at_08.54.22.png)

### Azure Discovery

Infoblox connects to Azure using a service principal with custom role assignment. Discovered resources include:
- Virtual Machines and NICs
- Virtual Networks, subnets, peerings
- Network Security Groups, DNS zones and records
- Resource groups, tags, and regional metadata

---

## Onboarding AWS account onto Infoblox Portal

### Step 1: Retrieve Required Identifiers
You will need: Principal ID and External ID (from the Infoblox Portal).

### Step 2: Access the Infoblox Portal
Navigate to: **Configure → Networking → Discovery**

![Discovery Menu](Screenshot_2025-04-01_at_14.48.39.png)

### Step 3: Configure AWS Discovery
1. Select the **Cloud** tab
2. Click **Create AWS**

![Create AWS](Screenshot_2025-04-01_at_14.48.52.png)

![AWS Config](Screenshot_2025-04-01_at_14.49.02.png)

> **NOTE:** Gather External ID and Principal ID from the portal.

### Step 4: Deploy CloudFormation Stack

Open the AWS Console and navigate to CloudFormation.

![CloudFormation](Screenshot_2025-07-10_at_15.55.43.png)

### Step 5: Configure Stack Parameters

Provide a stack name and enter the External ID.

> **Note:** Leave the Account ID unchanged and COPY/PASTE External ID from the Infoblox Portal.

![Stack Params](Screenshot_2025-04-02_at_07.31.45.png)

### Step 6: Click "Next" on each page

![Next](Screenshot_2025-04-02_at_07.32.00.png)

### Step 7: Click "Submit"

![Submit](Screenshot_2025-04-02_at_07.32.13.png)

### Step 8: Get the ARN

Wait for completion, then go to **Outputs** tab.

![Outputs](Screenshot_2025-04-02_at_07.32.32.png)

![ARN](Screenshot_2025-04-02_at_07.32.54.png)

![ARN Value](Screenshot_2025-04-02_at_07.33.43.png)

### Step 9: Paste ARN in Infoblox Portal

Return to the Infoblox Portal, paste the ARN, and click **Next**.

![Paste ARN](Screenshot_2025-09-01_at_09.37.24.png)

### Step 10: Configure sync settings

![Sync Settings](Screenshot_2025-09-01_at_09.37.46.png)

![More Settings](Screenshot_2025-09-01_at_09.48.06.png)

![Final Settings](Screenshot_2025-09-01_at_09.38.50.png)

> **IMPORTANT:** The "Consolidate Public/Private Zone Data" toggle must remain **disabled** in this lab, since we are creating a new DNS View.

### Step 11: Save & Close

![Save](Screenshot_2025-10-25_at_21.34.35.png)

---

## Onboarding Azure account onto Infoblox Portal

### Step 1: Create Azure Credentials
Navigate to: **Configure → Administration → Credentials**

![Credentials](Screenshot_2025-04-02_at_21.47.14.png)

### Step 2: Click Create → Microsoft Azure

![Create Azure](Screenshot_2025-04-02_at_21.47.48.png)

### Step 3: Fill in Azure credentials

Fill in all required fields using the Azure Tenant ID, Client ID, and Client Secret from your CloudShare environment details.

> **IMPORTANT:** Don't forget to give it a Name at the top.

### Step 4: Configure Azure Discovery
Navigate to: **Configure → Networking → Discovery → Cloud → Create Azure**

![Azure Discovery](Screenshot_2025-04-02_at_22.01.10.png)

> **IMPORTANT:** Select "Type of Access" → Static, then under "Credentials" select the one you created.

### Step 5: Configure sync settings

![Sync Config](Screenshot_2025-04-02_at_22.09.04.png)

![More Config](Screenshot_2025-04-02_at_22.10.42.png)

> **IMPORTANT:** Keep "Consolidate Public/Private Zone Data" **disabled** for this lab.

### Step 6: Save & Close

![Save Config](Screenshot_2025-04-02_at_22.11.18.png)

---

## UDDI Explore and Visibility of Assets

### Verify Discovery Sync

Navigate to **Configure → Networking → Discovery** and confirm both jobs are **Synced**.

> **NOTE:** It will take around 2 × sync job interval (~15 mins each) for the Discovery jobs to sync.

![Synced](Screenshot_2025-07-03_at_06.13.17.png)

### Explore AWS DNS Zones

Go to **Configure → Networking → DNS → Zones** and select the AWS DNS view:

![AWS Zones](Screenshot_2025-07-03_at_06.14.04.png)

Validate zone `infolab.com` with records:
- `app1.infolab.com` → `10.20.0.100`
- `app2.infolab.com` → `10.20.2.100`
- `app3.infolab.com` → `10.20.3.100`

![AWS Records](Screenshot_2025-07-03_at_06.14.22.png)

Add a new record: **Create → Record → A Record**:  `app4.infolab.com` → `10.10.10.9`

![New Record](Screenshot_2025-07-03_at_06.14.46.png)

![Record Details](Screenshot_2025-07-03_at_06.15.46.png)

Switch to **AWS Console** → Route 53 → Hosted Zones → `infolab.com` and verify the new record synced.

> **IMPORTANT:** Make sure you are in the **EU-WEST-2** AWS Region (London).

![Route53](Screenshot_2025-07-03_at_06.48.01.png)

![Verify](Screenshot_2025-07-03_at_06.48.48.png)

![Synced Record](Screenshot_2025-07-03_at_06.18.01.png)

### Explore Azure DNS Zones

Switch to the Azure DNS view: **Configure → Networking → DNS → Zones**

Confirmed zone `infolab.com` with:
- `azure-webprodeu1.infolab.com` → `10.10.1.100`
- `azure-webprodeu2.infolab.com` → `10.30.1.100`

![Azure DNS](Screenshot_2025-07-03_at_06.19.40.png)

### Inspect IPAM Data

Navigate to **Configure → Networking → IPAM/DHCP**

![IPAM](Screenshot_2025-07-03_at_07.01.10.png)

![IPAM Flat](Screenshot_2025-07-03_at_07.10.35.png)

![IPAM Details](Screenshot_2025-07-03_at_07.11.50.png)

Click any item for details:

![Drill Down](Screenshot_2025-07-03_at_07.14.57.png)

### Asset Visibility Dashboard

Click **Monitor** in the left menu, then select the **Assets** tab.

![Monitor](Screenshot_2025-07-03_at_07.20.46.png)

![Assets](Screenshot_2025-07-03_at_07.17.10.png)

Explore asset classification, noncompliant assets, DNS visibility, IPAM coverage, and asset locations.

> **Pro Tip:** Click on any chart slice to drill down into filtered views.

![Dashboard](Screenshot_2025-07-03_at_07.24.00.png)

---

# Chapter 3: Quiz - Your Experience Matters

## What is the primary advantage of using Infoblox UDDI in a multi-cloud environment?

- A) It eliminates the need for cloud native DNS services in each cloud provider
- B) It provides a single pane of glass across on-prem and your multi-cloud environments for managing IPAM, DNS, and DHCP
- C) It auto-creates subnets in all VPCs/VNets
- D) It prevents the use of private IPs

> **Answer: B**
