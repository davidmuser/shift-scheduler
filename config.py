"""Configuration settings for the shift scheduling system."""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    API_LOG_LEVEL = os.getenv("API_LOG_LEVEL", "info")
    
    DEFAULT_TIMEOUT_SECONDS = float(os.getenv("DEFAULT_TIMEOUT_SECONDS", 60))
    DEFAULT_TOP_K_SOLUTIONS = int(os.getenv("DEFAULT_TOP_K_SOLUTIONS", 5))
    
    WEIGHT_TIME_OFF_REQUESTS = float(os.getenv("WEIGHT_TIME_OFF_REQUESTS", 10.0))
    WEIGHT_SENIORITY = float(os.getenv("WEIGHT_SENIORITY", 5.0))
    WEIGHT_WEEKEND_BALANCE = float(os.getenv("WEIGHT_WEEKEND_BALANCE", 8.0))
    WEIGHT_OVERSTAFFING = float(os.getenv("WEIGHT_OVERSTAFFING", 3.0))
    WEIGHT_SKILL_MATCHING = float(os.getenv("WEIGHT_SKILL_MATCHING", 7.0))
    WEIGHT_WORKLOAD_BALANCE = float(os.getenv("WEIGHT_WORKLOAD_BALANCE", 6.0))
    WEIGHT_COMPENSATION = float(os.getenv("WEIGHT_COMPENSATION", 2.0))
    
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "json")


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    API_LOG_LEVEL = "debug"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    API_LOG_LEVEL = "info"


def get_config(env: str = None) -> Config:
    """
    Get configuration based on environment.
    
    Args:
        env: Environment name (development, production)
        
    Returns:
        Configuration object
    """
    if env is None:
        env = os.getenv("ENV", "development")
    
    if env == "production":
        return ProductionConfig()
    else:
        return DevelopmentConfig()
