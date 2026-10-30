from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
import os
import time
import json

#---------------------------------
# Initialize runtime deployment
#---------------------------------
boto_session = Session()
region = boto_session.region_name or "us-east-1"
runtime_state_file="./runtime_info.json"
TEST_AGENT = True

#---------------------------------
# Change to project root for
# AgentCore configuration
#---------------------------------
original_dir = os.getcwd()
os.chdir('./')
project_root = os.getcwd()

agentcore_runtime = Runtime()
agent_name = "travel_companion_basic"

print("🚀 Configuring AgentCore Runtime deployment...")
print(f"Agent Name: {agent_name}")
print(f"Region: {region}")
print(f"Project Root: {project_root}")

#---------------------------------
# Configure with paths relative
# to project root
#---------------------------------
configure_response = agentcore_runtime.configure(
    entrypoint="travel_agent.py",
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file="requirements.txt",
    region=region,
    agent_name=agent_name,
    container_runtime=None  # Force CodeBuild for cross-platform build
)

print("✅ Runtime configuration complete")
print("💡 Using CodeBuild for cross-platform ARM64 deployment")
configure_response


#---------------------------------
# Launch the agent to AgentCore
# Runtime
#---------------------------------
print("🚀 Launching agent to AgentCore Runtime...")
print("This may take 5-10 minutes...")

launch_result = agentcore_runtime.launch()
print("✅ Launch initiated")
print(f"Agent ARN: {launch_result.agent_arn}")
print(f"ECR URI: {launch_result.ecr_uri}")

#---------------------------------
# Check deployment status
#---------------------------------
print("⏳ Checking deployment status...")
status_response = agentcore_runtime.status()
status = status_response.endpoint['status']
end_status = ['READY', 'CREATE_FAILED', 'DELETE_FAILED', 'UPDATE_FAILED']

while status not in end_status:
    print(f"Status: {status}")
    time.sleep(30)  # Check every 30 seconds
    status_response = agentcore_runtime.status()
    status = status_response.endpoint['status']

print(f"\n🎉 Final Status: {status}")

if status == 'READY':
    print("✅ Agent successfully deployed to AgentCore Runtime!")
else:
    print("❌ Deployment failed. Check AWS console for details.")

# Return to original directory
os.chdir(original_dir)

#---------------------------------
# Test the deployed agent
#---------------------------------
if TEST_AGENT:
    if status == 'READY':
        print("🧪 Testing deployed Travel Agent")
        print("=" * 50)
    
        # Test basic interaction
        test_payload = {"prompt": "Hi, I want to plan a 10-day trip to Italy with a $5000 budget"}
        invoke_response = agentcore_runtime.invoke(test_payload)
    
        print(f"User: {test_payload['prompt']}")
        print(f"Agent: {invoke_response['response'][0]}")
    else:
        print("⚠️ Cannot test - deployment not ready")

    #---------------------------------
    # Test budget calculation
    # functionality
    #---------------------------------
    if status == 'READY':
        test_payload = {"prompt": "Can you help me allocate my $5000 budget for 10 days?"}
        invoke_response = agentcore_runtime.invoke(test_payload)
        
        print(f"\nUser: {test_payload['prompt']}")
        print(f"Agent: {invoke_response['response'][0]}")
    
    #---------------------------------
    # Test multi-turn conversation
    #---------------------------------
    if status == 'READY':
        print("🗣️ Testing Multi-turn Conversation")
        print("=" * 50)
    
        conversation = [
            "I want to visit Italy",
            "I prefer mid-range hotels and vegetarian food",
            "Tell me about Rome's attractions",
            "What about Florence?"
        ]
    
        for i, message in enumerate(conversation, 1):
            print(f"\n--- Turn {i} ---")
            test_payload = {"prompt": message}
            invoke_response = agentcore_runtime.invoke(test_payload)
    
            print(f"User: {message}")
            print(f"Agent: {invoke_response['response'][0][:200]}...")  # Truncate for readability


#---------------------------------
# Save runtime information for
# state and trouble-shooting
#---------------------------------

if status == 'READY':
    runtime_info = {
        "agent_name": agent_name,
        "agent_arn": launch_result.agent_arn,
        "agent_id": launch_result.agent_id,
        "ecr_uri": launch_result.ecr_uri,
        "region": region,
        "status": status
    }
    
    # Save to file
    with open(runtime_state_file, 'w') as f:
        json.dump(runtime_info, f, indent=2)
    
    print("💾 Runtime information saved to runtime_info.json")
    print("\n📋 Runtime Summary:")
    for key, value in runtime_info.items():
        print(f"  {key}: {value}")
else:
    print("⚠️ Runtime not ready - information not saved")
