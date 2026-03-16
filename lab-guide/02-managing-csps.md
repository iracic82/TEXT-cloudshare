# Challenge 2: Managing Public Cloud Providers

## Universal DDI Management - The Backbone of Modern Network Services

Universal DDI Management is the industry's first and most comprehensive SaaS-based solution for managing critical DNS, DHCP, and IPAM services across hybrid and multicloud environments.

![UDDI Overview](./assets/Screenshot%202025-07-03%20at%2020.31.01.png)

### What It Does

- **Central Hub** - Single SaaS control plane for all network services across on-prem, AWS, Azure, GCP
- **Comprehensive Consolidation** - Unifies DNS, DHCP, and IP address management across Infoblox NIOS/NIOS-X, Amazon Route 53, Azure DNS, Google Cloud DNS
- **Streamlined Operation** - Eliminates silos and unifies policy across infrastructure

![Value Points](./assets/Screenshot%202025-07-03%20at%2020.35.07.png)

### Four Core Value Points

1. **Centralized Control** - Single interface for DNS/DHCP/IPAM across any environment
2. **Deep Integration** - Bridges traditional DNS with cloud-native platforms
3. **Operational Efficiency** - Reduces overhead, accelerates delivery
4. **Scalability and Flexibility** - Scales with your architecture

![Single Pane](./assets/Screenshot%202025-07-03%20at%2020.36.56.png)

---

## 1) Login to your cloud account consoles

You should already be signed in to both AWS and Azure consoles. Only re-authenticate if your session has expired.

Your credentials are available in the CloudShare environment details panel.

---

## 2) Cloud Discovery Overview (AWS & Azure)

**Infoblox Universal Asset Insights** automatically discovers and tracks cloud resources using native cloud APIs.

### AWS Discovery

Infoblox connects to AWS via a cross-account IAM role using a secure External ID. Discovered resources include:
- EC2 instances, VPCs, subnets
- Route tables, NAT and Internet Gateways
- Load Balancers (ALB, NLB)
- Route 53 Hosted Zones and Records
- Tags, regions, and metadata

![IAM Role](./assets/Screenshot%202025-07-09%20at%2008.54.34.png)
![IAM Policy](./assets/Screenshot%202025-07-09%20at%2008.54.22.png)

### Azure Discovery

Infoblox connects to Azure using a service principal with custom role assignment. Discovered resources include:
- Virtual Machines and NICs
- Virtual Networks, subnets, peerings
- Network Security Groups, DNS zones and records
- Resource groups, tags, and regional metadata

---

## 3) Onboarding AWS account onto Infoblox Portal

### Step 1: Retrieve Required Identifiers
You will need: Principal ID and External ID (from the Infoblox Portal).

### Step 2: Access the Infoblox Portal
Navigate to: **Configure → Networking → Discovery**

![Discovery Menu](./assets/Screenshot%202025-04-01%20at%2014.48.39.png)

### Step 3: Configure AWS Discovery
1. Select the **Cloud** tab
2. Click **Create AWS**

![Create AWS](./assets/Screenshot%202025-04-01%20at%2014.48.52.png)
![AWS Config](./assets/Screenshot%202025-04-01%20at%2014.49.02.png)

> **NOTE:** Gather External ID and Principal ID from the portal.

### Step 4: Deploy CloudFormation Stack

Open the AWS Console and navigate to CloudFormation. Create a new stack using the template URL from Infoblox.

![CloudFormation](./assets/Screenshot%202025-07-10%20at%2015.55.43.png)

### Step 5: Configure Stack Parameters

Provide a stack name and enter the External ID from the Infoblox Portal.

> **Note:** Leave the Account ID unchanged and COPY/PASTE External ID from the Infoblox Portal.

![Stack Params](./assets/Screenshot%202025-04-02%20at%2007.31.45.png)

### Step 6: Click "Next" on each page, keeping defaults

![Next](./assets/Screenshot%202025-04-02%20at%2007.32.00.png)

### Step 7: Click "Submit"

![Submit](./assets/Screenshot%202025-04-02%20at%2007.32.13.png)

### Step 8: Get the ARN

Wait for completion, then go to **Outputs** tab to get the ARN value.

![Outputs](./assets/Screenshot%202025-04-02%20at%2007.32.32.png)
![ARN](./assets/Screenshot%202025-04-02%20at%2007.32.54.png)
![ARN Value](./assets/Screenshot%202025-04-02%20at%2007.33.43.png)

### Step 9: Paste ARN in Infoblox Portal

Return to the Infoblox Portal, paste the ARN, and click **Next**.

![Paste ARN](./assets/Screenshot%202025-09-01%20at%2009.37.24.png)

### Step 10-11: Configure sync settings

![Sync Settings](./assets/Screenshot%202025-09-01%20at%2009.37.46.png)
![More Settings](./assets/Screenshot%202025-09-01%20at%2009.48.06.png)
![Final Settings](./assets/Screenshot%202025-09-01%20at%2009.38.50.png)

> **IMPORTANT:** The "Consolidate Public/Private Zone Data" toggle must remain **disabled** in this lab, since we are creating a new DNS View.

### Step 12: Save & Close

![Save](./assets/Screenshot%202025-10-25%20at%2021.34.35.png)

---

## 4) Onboarding Azure account onto Infoblox Portal

### Step 1: Create Azure Credentials
Navigate to: **Configure → Administration → Credentials**

![Credentials](./assets/Screenshot%202025-04-02%20at%2021.47.14.png)

### Step 2: Click Create → Microsoft Azure

![Create Azure](./assets/Screenshot%202025-04-02%20at%2021.47.48.png)

### Step 3: Fill in Azure credentials

Your Azure Tenant ID, Client ID, and Client Secret are available on the Ubuntu VM:

```bash
# These values are set during environment setup
# Check your environment details in CloudShare
```

> **IMPORTANT:** Don't forget to give it a Name at the top.

### Step 4-5: Configure Azure Discovery
Navigate to: **Configure → Networking → Discovery → Cloud → Create Azure**

### Step 6: Fill in Azure Subscription ID

```bash
# Available in your CloudShare environment details
```

![Azure Discovery](./assets/Screenshot%202025-04-02%20at%2022.01.10.png)

> **IMPORTANT:** Select "Type of Access" → Static, then under "Credentials" select the one you created.

### Step 7-9: Configure sync settings

![Sync Config](./assets/Screenshot%202025-04-02%20at%2022.09.04.png)
![More Config](./assets/Screenshot%202025-04-02%20at%2022.10.42.png)
![Save Config](./assets/Screenshot%202025-04-02%20at%2022.11.18.png)

> **IMPORTANT:** Keep "Consolidate Public/Private Zone Data" **disabled** for this lab.

---

## 5) UDDI Explore and Visibility of Assets

### Step 1: Verify Discovery Sync

Navigate to **Configure → Networking → Discovery** and confirm both AWS and Azure jobs are **Synced**.

> **NOTE:** It will take around 2 × sync job interval (~15 mins each) for the Discovery jobs to sync.

![Synced](./assets/Screenshot%202025-07-03%20at%2006.13.17.png)

### Step 2: Explore AWS DNS Zones

Go to **Configure → Networking → DNS → Zones** and select the AWS DNS view:

![AWS Zones](./assets/Screenshot%202025-07-03%20at%2006.14.04.png)

Validate zone `infolab.com` with records:
- `app1.infolab.com` → `10.20.0.100`
- `app2.infolab.com` → `10.20.2.100`
- `app3.infolab.com` → `10.20.3.100`

![AWS Records](./assets/Screenshot%202025-07-03%20at%2006.14.22.png)

Add a new record: **Create → Record → A Record**
- `app4.infolab.com` → `10.10.10.9`

![New Record](./assets/Screenshot%202025-07-03%20at%2006.14.46.png)
![Record Details](./assets/Screenshot%202025-07-03%20at%2006.15.46.png)

Switch to **AWS Console** → Route 53 → Hosted Zones → `infolab.com` and verify the new record synced.

> **IMPORTANT:** Make sure you are in the **EU-WEST-2** AWS Region (London).

![Route53](./assets/Screenshot%202025-07-03%20at%2006.48.01.png)
![Verify](./assets/Screenshot%202025-07-03%20at%2006.48.48.png)
![Synced Record](./assets/Screenshot%202025-07-03%20at%2006.18.01.png)

### Step 3: Explore Azure DNS Zones

Switch to the Azure DNS view: **Configure → Networking → DNS → Zones**

Validate zone `infolab.com` with:
- `azure-webprodeu1.infolab.com` → `10.10.1.100`
- `azure-webprodeu2.infolab.com` → `10.30.1.100`

![Azure DNS](./assets/Screenshot%202025-07-03%20at%2006.19.40.png)

### Step 4: Inspect IPAM Data

Navigate to **Configure → Networking → IPAM/DHCP** to see discovered cloud assets.

![IPAM](./assets/Screenshot%202025-07-03%20at%2007.01.10.png)
![IPAM Flat](./assets/Screenshot%202025-07-03%20at%2007.10.35.png)
![IPAM Details](./assets/Screenshot%202025-07-03%20at%2007.11.50.png)

Click any item for details:

![Drill Down](./assets/Screenshot%202025-07-03%20at%2007.14.57.png)

### Step 5: Asset Visibility Dashboard

Click **Monitor** in the left menu, then select the **Assets** tab.

![Monitor](./assets/Screenshot%202025-07-03%20at%2007.20.46.png)
![Assets](./assets/Screenshot%202025-07-03%20at%2007.17.10.png)
![Dashboard](./assets/Screenshot%202025-07-03%20at%2007.24.00.png)

Explore:
- Asset by Type (Server, Workstation, DNS)
- Zombie/Orphan/Ghost breakdown
- Assets with Missing Records
- Noncompliant Assets
- New Assets by Type
- Asset Locations

> **Pro Tip:** Click on any chart slice to drill down into filtered views.

---

## Next Challenge

Proceed to **[Challenge 3: Quiz](./03-quiz.md)**!
