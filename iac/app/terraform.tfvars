aws_region   = "us-east-1"
project_name = "nhl-excite-o-meter-be"
environment  = "prod"

app_image = "871806636838.dkr.ecr.us-east-1.amazonaws.com/nhl-excit-o-meter-be:637d89724d35369e7f832e2008757b529d5d66af"
flask_env = "production"

# Required from network stack outputs
vpc_id = "vpc-010c8bf40cdf46b38"

public_subnet_ids =["subnet-036d25c00629af481","subnet-0cc61dc319782a5dd",]
# Optional from network stack output (for ECS Service Connect integration)
service_connect_namespace_arn = "arn:aws:servicediscovery:us-east-1:871806636838:namespace/ns-6bvfavc37y2wydek"

# Required for backend ingress: allow frontend ECS service SG(s) to reach app_port.
frontend_security_group_ids = ["sg-0621ba9113601c153"]

db_iam_username = "app_iam"

# Required from DB repo outputs
# - db_secret_arn: Secrets Manager ARN with host/port/dbname/username/password
# - db_resource_id: RDS resource ID (db-...) for IAM auth policy
db_secret_arn  = "arn:aws:secretsmanager:us-east-1:871806636838:secret:nhl-excite-o-meter-prod/rds/app-runtime-vmq8eU"
db_resource_id = "db-SP4QWYTWROWXTHRRT6RRLGRYV4"
