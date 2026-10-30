#Set up AWS environment for AgentCore
#Validate development environment
#Configure basic authentication

#-------------------------------------------
# Verify environment setup
#-------------------------------------------
import os
import sys
import boto3
from dotenv import load_dotenv
import subprocess
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel

#-------------------------------------------
# Assign Global Vars
#-------------------------------------------
REGION = 'us-east-1'
TEST_AGENT_LOCALLY = True
model_id = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

#-------------------------------------------
# Load environment variables
#-------------------------------------------
load_dotenv()
print("✅ AgentCore Runtime imports successful")


#-------------------------------------------
# Create tools for travel project
# Define basic travel tools for our agent
#-------------------------------------------
@tool
def get_travel_preferences():
    """Get user's travel preferences from memory"""
    # Mock implementation - will be enhanced in Memory notebook
    return {
        "hotel_type": "mid-range",
        "food_preference": "vegetarian",
        "budget_range": "moderate"
    }

@tool
def calculate_budget(total_budget: int, days: int):
    """Calculate daily budget allocation for travel"""
    # Basic budget breakdown
    daily_budget = total_budget / days
    allocation = {
        "flights": total_budget * 0.24,  # 24%
        "hotels": total_budget * 0.36,   # 36%
        "food": total_budget * 0.20,     # 20%
        "activities": total_budget * 0.16, # 16%
        "buffer": total_budget * 0.04     # 4%
    }
    return {
        "daily_budget": daily_budget,
        "allocation": allocation
    }

@tool
def get_destination_info(destination: str):
    """Get basic information about a travel destination"""
    # Mock implementation - will be enhanced with real APIs
    destinations = {
        "rome": {
            "country": "Italy",
            "currency": "EUR",
            "language": "Italian",
            "attractions": ["Colosseum", "Vatican", "Trevi Fountain"]
        },
        "florence": {
            "country": "Italy",
            "currency": "EUR",
            "language": "Italian",
            "attractions": ["Uffizi Gallery", "Ponte Vecchio", "Duomo"]
        },
        "venice": {
            "country": "Italy",
            "currency": "EUR",
            "language": "Italian",
            "attractions": ["St. Mark's Square", "Grand Canal", "Doge's Palace"]
        }
    }
    return destinations.get(destination.lower(), {"error": "Destination not found"})

print("✅ Travel agent tools defined")

#-------------------------------------------
# Create Travel Agent with Bedrock Model
#-------------------------------------------
# Initialize Bedrock model for the agent
model = BedrockModel(model_id=model_id)

# Create the travel agent with system prompt
system_prompt = """
You are an AI Travel Companion specializing in planning trips to Italy.
Your expertise includes:
- Flight and hotel recommendations
- Budget optimization and allocation
- Destination information and attractions
- Personalized recommendations based on user preferences

Always ask clarifying questions to better understand the user's needs.
Be helpful, friendly, and provide detailed explanations for your recommendations.
Remember user preferences and reference them in future interactions.
"""

travel_agent = Agent(
    model=model,
    tools=[get_travel_preferences, calculate_budget, get_destination_info],
    system_prompt=system_prompt
)

print("✅ Travel agent created with Bedrock model")

#-------------------------------------------
# Test the agent locally before deploying
# to runtime
#-------------------------------------------
def test_travel_agent(user_input):
    """Test function for local agent invocation"""
    print(f"User: {user_input}")
    response = travel_agent(user_input)
    agent_response = response.message['content'][0]['text']
    print(f"Agent: {agent_response}")
    return agent_response


if TEST_AGENT_LOCALLY:
    print("---------------------\n")
    print("Testing Agent locally\n")
    print("---------------------\n")
    test_travel_agent("Hi, I want to plan a trip to Italy")
    # Test budget calculation
    test_travel_agent("I have a budget of $5000 for a 10-day trip. How should I allocate it?")
    # Test destination information
    test_travel_agent("Tell me about Rome and what I should see there")
else:
    print("Testing agent locally turned off\n")
