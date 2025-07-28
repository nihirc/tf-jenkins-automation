provider "aws" {
  region = "us-west-1"  # US West (N. California)
}

resource "aws_s3_bucket" "demo_bucket" {
  bucket = "pocdemo21stjuly1"

  # Force destroy is set to false for safety
  force_destroy = false

  tags = {
    Environment = "POC"
    CreatedDate = "2025-07-21"
  }
}

# Enable versioning
resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.demo_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption by default
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
