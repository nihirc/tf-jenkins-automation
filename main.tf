terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"  # Updated to match the available version
    }
  }
}

provider "aws" {
  region = "us-east-1"  # You can modify this to your desired region
}

# S3 bucket and related resources
resource "aws_s3_bucket" "poc_bucket" {
  bucket = "julypoctoday"
}

# Enable versioning
resource "aws_s3_bucket_versioning" "poc_bucket_versioning" {
  bucket = aws_s3_bucket.poc_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "poc_bucket_encryption" {
  bucket = aws_s3_bucket.poc_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "poc_bucket_public_access_block" {
  bucket = aws_s3_bucket.poc_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
