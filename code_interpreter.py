# Set up AgentCore Code Interpreter with Strands
# Create travel agent with analytical capabilities
# Test budget calculations and data analysis
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
from strands import Agent
from strands.models import BedrockModel
from strands_tools.code_interpreter import AgentCoreCodeInterpreter


#-------------------------------------------
# Assign Global Vars
#-------------------------------------------
REGION = 'us-east-1'
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
code_interpreter_state_file="./code_interpreter_config.json"

#-------------------------------------------
# Prompts
#-------------------------------------------
SYSTEM_PROMPT="You are a travel planning assistant with analytical capabilities. Use code to perform calculations and provide data-driven insights."



#-------------------------------------------
# Create agent with code interpreter
#-------------------------------------------

# Create tools and agent
code_interpreter = AgentCoreCodeInterpreter(region="us-east-1")
model = BedrockModel(model_id=MODEL_ID)

agent = Agent(
    model=model,
    tools=[code_interpreter.code_interpreter],
    system_prompt=SYSTEM_PROMPT
)

print("Agent created")

#-------------------------------------------
# Test Analytics Capabilities
#-------------------------------------------

# Test 1: Budget calculation
response = agent("Calculate a budget breakdown for a $3000, 7-day trip to Italy. Show amounts for flights, hotels, food, and activities.")
print("Budget Analysis:")
print(response.message['content'][0]['text'])

# Test 2: Cost comparison
response = agent("Compare cost per day for these trips: Japan $5000/10 days, Thailand $2000/14 days, France $4000/8 days. Which is most cost-effective?")
print("Cost Comparison:")
print(response.message['content'][0]['text'])

# Test 3: Currency and savings calculation
response = agent("If I save $200 per month for travel, how long to reach $4500? Also calculate compound interest at 3% annual rate.")
print("Savings Analysis:")
print(response.message['content'][0]['text'])

# Test 4: Statistical analysis
response = agent("Analyze these hotel prices per night: $120, $95, $180, $110, $150, $85, $200. Calculate mean, median, and recommend budget range.")
print("Price Analysis:")
print(response.message['content'][0]['text'])



#---------------------------------
# Save gateway information for
# state and trouble-shooting
#---------------------------------

config = {
    "code_interpreter": "configured",
    "capabilities": ["budget_analysis", "cost_comparison", "statistical_analysis"]
}

with open(code_interpreter_state_file, 'w') as f:
    json.dump(config, f)

print("✅ Code Interpreter integration complete")


