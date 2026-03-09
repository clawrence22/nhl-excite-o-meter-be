terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "nhl-excite-o-meter-tf-state"
    key            = "nhl-excite-o-meter-be/prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "nhl-excite-o-meter-tf-state"
    encrypt        = true
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
