# Terraform Layout

This directory contains two stacks:
- `iac/network`: VPC, subnets, routes, NAT, IGW
- `iac/app`: ALB, ECS, IAM, CloudWatch

**1) Run Network Stack Once**
```bash
cd iac/network
# edit terraform.tfvars
# edit backend.hcl with your S3 bucket + DynamoDB lock table
terraform init -backend-config=backend.hcl -migrate-state
terraform plan
terraform apply
```

Capture outputs:
- `vpc_id`
- `public_subnet_ids`
- `private_app_subnet_ids`
- `private_db_subnet_ids`
- `service_connect_namespace_arn` (if using ECS Service Connect)

**2) Run DB Stack in Your DB Repo**
Use network outputs (`vpc_id`, `private_db_subnet_ids`).

Capture DB outputs for the app stack:
- `db_secret_arn`
- `db_resource_id`

App stack assumes IAM DB auth is enabled.

**3) Run App Stack**
```bash
cd iac/app
# edit terraform.tfvars
# edit backend.hcl with your S3 bucket + DynamoDB lock table
# fill vpc/subnet values from network outputs
# fill service_connect_namespace_arn from network outputs
# fill db_secret_arn/db_resource_id from DB repo outputs
terraform init -backend-config=backend.hcl -migrate-state
terraform plan
terraform apply
```

After apply, use `ecs_service_security_group_id` to allow inbound PostgreSQL (5432) from ECS tasks in the DB repo security group rules.
