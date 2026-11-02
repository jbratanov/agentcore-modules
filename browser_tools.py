# Set up AgentCore Browser Tools
# Implement web scraping for attractions
# Add review aggregation logic
# Create real-time research automation
# Integrate browser tools with travel agent
#
# Original code taken from puria-izady/mastering-amazon-bedrock-agentcore
# notebooks. I converted it to python files and refactored code from python 3.10
# libraries to work with python 3.12 which required changes to dependency python
# modules and changes to Agentcore and cognito code.
#


#-------------------------------------------
# imports
#-------------------------------------------
import json
from dotenv import load_dotenv
from strands import Agent
from strands.models import BedrockModel
from strands_tools.browser import AgentCoreBrowser


#-------------------------------------------
# Assign Global Vars
#-------------------------------------------
REGION = 'us-east-1'
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
browser_tools_state_file="./browser_tools_info.json"

#-------------------------------------------
# Load environment variables
#-------------------------------------------
load_dotenv()

#-------------------------------------------
# Initialize AgentCore Browser Tool
#-------------------------------------------
print("Initializing AgentCore Browser Tool...")

browser_tool = AgentCoreBrowser(region=REGION)

print(f"AgentCore Browser Tool initialized for region: {REGION}")

#-------------------------------------------
# Create Travel Agent with Browser Tools
#-------------------------------------------

model = BedrockModel(model_id=MODEL_ID)

travel_agent = Agent(
    model=model,
    tools=[browser_tool.browser],
    system_prompt="""You are an AI Travel Companion with web browsing capabilities.
    
    You can use the browser to:
    - Research attractions and points of interest
    - Find reviews and ratings for destinations
    - Gather local tips and travel information
    - Search for current travel information
    
    When users ask about destinations, use the browser to find current, accurate information.
    Provide helpful, detailed travel recommendations based on your research."""
)

print("Travel agent with browser tools created")


#-------------------------------------------
# Test Browser Tools Integration
#-------------------------------------------

# Test 1: Attraction research
print("Test 1: Attraction Research")
print("=" * 50)

prompt1 = "Goto https://www.ticketslouvre.com and find out how much a guided tour costs."
print(f"User: {prompt1}")

response1 = travel_agent(prompt1)
print(f"Agent: {response1.message['content'][0]['text']}")
print()


# Test 2: Review aggregation
print("Test 2: Review Research")
print("=" * 50)

prompt2 = "I would like to go to the Paris Opera tomorrow, what are the open slots available?"
print(f"User: {prompt2}")

response2 = travel_agent(prompt2)
print(f"Agent: {response2.message['content'][0]['text']}")
print()


#---------------------------------
# Save browser tools information
# for state and trouble-shooting
#---------------------------------

browser_tools_info = {
    "region": REGION,
    "model_id": MODEL_ID,
    "browser_tool_initialized": True,
    "integration_status": "configured"
}

# Save to file for next notebooks
with open(browser_tools_state_file, 'w') as f:
    json.dump(browser_tools_info, f, indent=2)

print("Browser tools information saved to backend/browser_tools_info.json")
print("\n Browser Tools Summary:")
print(f"  Region: {browser_tools_info['region']}")
print(f"  Model: {browser_tools_info['model_id']}")
print(f"  Browser Tool: {browser_tools_info['browser_tool_initialized']}")
print(f"  Status: {browser_tools_info['integration_status']}")










