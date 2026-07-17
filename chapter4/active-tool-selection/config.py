"""Configuration for Active Tool Selection Agent."""
import os
from dotenv import load_dotenv

load_dotenv()

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Agent Configuration
AGENT_TEMPERATURE = 0.7
MAX_TOOL_REQUESTS = 5  # Maximum number of tool discovery iterations

# Semantic Routing Configuration
SIMILARITY_THRESHOLD = 0.15  # Minimum similarity score for tool matching
TOP_K_SERVERS = 3  # Number of top servers to search
TOP_K_TOOLS = 5  # Number of top tools to return per server
