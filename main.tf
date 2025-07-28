# AWS Provider configuration
provider "aws" {
  region = "us-east-1"  # Change this to your desired region
}

# S3 bucket
resource "aws_s3_bucket" "demo_bucket" {
  bucket = "demo28july"
  
  tags = {
    Name        = "demo28july"
    Environment = "Dev"
    CreatedBy   = "Terraform"
  }
}

# Enable versioning
resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.demo_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "encryption" {
  bucket = aws_s3_bucket.demo_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "public_access_block" {
  bucket = aws_s3_bucket.demo_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable bucket logging
resource "aws_s3_bucket_logging" "logging" {
  bucket = aws_s3_bucket.demo_bucket.id

  target_bucket = aws_s3_bucket.demo_bucket.id
  target_prefix = "logs/"
}
