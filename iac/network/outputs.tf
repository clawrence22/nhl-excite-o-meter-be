output "vpc_id" {
  description = "VPC ID."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs for ALB."
  value       = [for s in aws_subnet.public : s.id]
}

output "private_app_subnet_ids" {
  description = "Private app subnet IDs for ECS services."
  value       = [for s in aws_subnet.private_app : s.id]
}

output "private_db_subnet_ids" {
  description = "Private DB subnet IDs for RDS subnet group in DB repo."
  value       = [for s in aws_subnet.private_db : s.id]
}

output "nat_eip" {
  description = "NAT EIP public IP, useful for temporary allow-listing if needed."
  value       = aws_eip.nat.public_ip
}

output "service_connect_namespace_arn" {
  description = "Cloud Map HTTP namespace ARN for ECS Service Connect."
  value       = aws_service_discovery_http_namespace.ecs_service_connect.arn
}

output "service_connect_namespace_name" {
  description = "Cloud Map HTTP namespace name for ECS Service Connect."
  value       = aws_service_discovery_http_namespace.ecs_service_connect.name
}
