resource "aws_s3_bucket" "secure_bucket" {
  bucket = "jj-secure-bucket-${data.aws_caller_identity.current.account_id}"  # Ensures unique bucket name
  force_destroy = false  # Protect against accidental deletion
}

# Enable versioning
resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.secure_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "encryption" {
  bucket = aws_s3_bucket.secure_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "public_access_block" {
  bucket = aws_s3_bucket.secure_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable logging
resource "aws_s3_bucket_logging" "logging" {
  bucket = aws_s3_bucket.secure_bucket.id
  target_bucket = aws_s3_bucket.secure_bucket.id  # Logs stored in same bucket
  target_prefix = "access-logs/"
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Note: The bucket policy will be automatically applied by CLOUDx enforcements
# as mentioned in the documentation. Do not manually specify the bucket policy.
