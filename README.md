# FinBank Cyber Digital Twin

A graph-backed enterprise cyber digital twin modeling banking infrastructure, identities, communication flows, and defensive security controls using Python, Pydantic, and NetworkX.

---

## Ingestion Pipeline & Architecture

```
scenario.json
      ↓
Python
      ↓
NetworkX
      ↓
        ┌──────────────┐
        │ FinBank Twin │
        └──────────────┘
              │
              ▼
        9 assets detected
        4 identities detected
        8 relationships detected
        4 controls detected
```

---

## Topology Overview

### 1. Assets (9 Detected)
- `asset-web-portal`: Online Banking Web Portal (DMZ)
- `asset-api-gateway`: Core Banking API Gateway (Application Zone)
- `asset-auth-service`: Identity & OAuth2 Provider (Application Zone)
- `asset-core-banking-db`: Production Financial Ledger Database (Data Secure Zone)
- `asset-payment-processor`: SWIFT / ACH Payment Clearing Microservice (Application Zone)
- `asset-admin-jumpbox`: Privileged Admin Bastion Host (Management Zone)
- `asset-corp-workstation`: Corporate Analyst Workstation (Corporate LAN)
- `asset-backup-vault`: Immutable Cold Backup Storage Vault (Cold Storage Zone)
- `asset-siem-server`: Central SIEM & Audit Collector (Management Zone)

### 2. Identities (4 Detected)
- `id-user-customer`: Retail Banking Customer (`customer`)
- `id-user-analyst`: Financial Operations Analyst (`staff`)
- `id-user-admin`: Lead Cloud Infrastructure Administrator (`administrator`)
- `id-svc-payment-app`: Core Payment Processing Service Account (`service_account`)

### 3. Relationships (8 Detected)
1. `id-user-customer` $\xrightarrow{\text{ACCESSES}}$ `asset-web-portal` (HTTPS:443)
2. `asset-web-portal` $\xrightarrow{\text{CONNECTS_TO}}$ `asset-api-gateway` (gRPC:50051)
3. `asset-api-gateway` $\xrightarrow{\text{AUTHENTICATES_VIA}}$ `asset-auth-service` (HTTPS:8443)
4. `asset-api-gateway` $\xrightarrow{\text{ROUTES_TO}}$ `asset-payment-processor` (HTTPS:8080)
5. `asset-payment-processor` $\xrightarrow{\text{EXECUTES_SQL}}$ `asset-core-banking-db` (TLS/TCP:5432)
6. `id-svc-payment-app` $\xrightarrow{\text{READS_WRITES}}$ `asset-core-banking-db` (TLS/TCP:5432)
7. `id-user-admin` $\xrightarrow{\text{LOGS_INTO}}$ `asset-admin-jumpbox` (SSH:22)
8. `asset-admin-jumpbox` $\xrightarrow{\text{MANAGES}}$ `asset-backup-vault` (HTTPS:443)

### 4. Security Controls (4 Detected)
- `ctrl-mfa`: FIDO2 / TOTP Multi-Factor Authentication (Covers: Auth Service, Admin Jumpbox)
- `ctrl-waf`: Cloud Web Application Firewall & DDoS Protection (Covers: Web Portal)
- `ctrl-edr`: Endpoint Detection & Response (Covers: Workstation, Jumpbox)
- `ctrl-db-enc`: AES-256 Column Encryption & Key Management (Covers: Core Banking Database)

---

## Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Running the Digital Twin
Run with default scenario (`scenarios/scenario.json`):
```bash
python main.py
```

Run with detailed entity breakdowns and security mappings:
```bash
python main.py --detail
```

Run against a custom scenario file:
```bash
python main.py path/to/custom_scenario.json
```

---

## Running Tests

Execute the automated pytest suite:
```bash
pytest -v
```
