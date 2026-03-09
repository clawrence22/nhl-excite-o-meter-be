# Terraform Layout

This directory is split into two stacks:

- `iac/network` (run once): VPC, subnets, routes, NAT, IGW
- `iac/app` (run when app infra changes): ALB, ECS, IAM, CloudWatch

## 1) Run network stack once

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
- `private_db_subnet_ids` (for DB repo)
- `service_connect_namespace_arn` (for ECS Service Connect)

## 2) Run DB stack in your DB repo

Use network outputs (`vpc_id`, `private_db_subnet_ids`) there.
Capture DB outputs for app stack:

- `db_secret_arn`
- `db_resource_id`

App stack assumes IAM DB auth is always enabled.

## 3) Run app stack

```bash
cd iac/app
# edit terraform.tfvars
# edit backend.hcl with your S3 bucket + DynamoDB lock table
# fill vpc/subnet values from network outputs
# fill service_connect_namespace_arn from network outputs (if using Service Connect)
# fill db_secret_arn/db_resource_id from DB repo outputs
terraform init -backend-config=backend.hcl -migrate-state
terraform plan
terraform apply
```

After apply, use app output `ecs_service_security_group_id` in DB repo SG rules to allow inbound PostgreSQL (5432) from ECS tasks.
