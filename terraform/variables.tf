variable "region" {
  description = "AWS region for every resource"
  type        = string
  default     = "ap-south-1"
}

variable "project" {
  description = "Name prefix for every resource"
  type        = string
  default     = "shelfwise"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "One public subnet per availability zone (load balancers, NAT)"
  type        = list(string)
  default     = ["10.40.0.0/20", "10.40.16.0/20"]
}

variable "private_subnet_cidrs" {
  description = "One private subnet per availability zone (worker nodes)"
  type        = list(string)
  default     = ["10.40.128.0/20", "10.40.144.0/20"]
}

variable "kubernetes_version" {
  type    = string
  default = "1.31"
}

variable "node_instance_types" {
  type    = list(string)
  default = ["t3.medium"]
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "node_min_size" {
  type    = number
  default = 1
}

variable "node_max_size" {
  type    = number
  default = 3
}
