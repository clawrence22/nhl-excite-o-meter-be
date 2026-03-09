terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket       = "nhl-excite-o-meter-tf-state"
    key          = "nhl-excite-o-meter-net/prod/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
