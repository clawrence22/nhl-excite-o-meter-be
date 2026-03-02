aws_region   = "us-east-1"
project_name = "nhl-excite-o-meter-network"
environment  = "prod"

vpc_cidr = "10.20.0.0/16"

public_subnet_cidrs      = ["10.20.0.0/24", "10.20.1.0/24"]
private_app_subnet_cidrs = ["10.20.10.0/24", "10.20.11.0/24"]
private_db_subnet_cidrs  = ["10.20.20.0/24", "10.20.21.0/24"]

# Optional override. Defaults to "${project_name}.local" when empty.
service_connect_namespace_name = ""
