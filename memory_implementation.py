# Set up AgentCore Memory for user preferences
# Implement conversation context management
# Add personalization based on user history
# Create memory hooks for automatic storage/retrieval
# Integrate memory with travel agent
#
# Original code taken from puria-izady/mastering-amazon-bedrock-agentcore
# notebooks. I converted it to python files and refactored code from python 3.10
# libraries to work with python 3.12 which required changes to dependency python
# modules and changes to Agentcore and cognito code.
#


#-------------------------------------------
# Import libraies
#-------------------------------------------
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType
#import time

#-------------------------------------------
# Assign Global Vars
#-------------------------------------------
REGION = "us-east-1"
MEMORY_NAME = "TravelMateMemory"
USER_ID = "travel_user_001"
SESSION_ID = f"travel_{datetime.now().strftime('%Y%m%d%H%M%S')}"
memory_state_file="./memory_info.json"

#------------------------------------------
# Load environment variables
#------------------------------------------
env = load_dotenv()
# Setup logging
logging.basicConfig(level=logging.INFO, filename="./newfile.log",format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("travel-memory")

logging.info("AgentCore Memory imports successful")


#-------------------------------------------
# Create Travel Memory Resource
#-------------------------------------------

logging.info(f"Creating AgentCore Memory for Travel Agent Memory Name: {MEMORY_NAME} Region: {REGION} User ID: {USER_ID}")

# Initialize Memory Client
client = MemoryClient(region_name=REGION)
logging.info("Memory client initialized")


#-------------------------------------------
# Define memory strategies for travel
# planning
#-------------------------------------------
strategies = [
    {
        StrategyType.USER_PREFERENCE.value: {
            "name": "TravelPreferences",
            "description": "Captures user travel preferences and behavior",
            "namespaces": ["travel/user/{actorId}/preferences"]
        }
    },
    {
        StrategyType.SEMANTIC.value: {
            "name": "TravelSemantic",
            "description": "Stores travel facts and trip information",
            "namespaces": ["travel/user/{actorId}/semantic"]
        }
    },
    {
        StrategyType.SUMMARY.value: {
            "name": "TravelSummary", 
            "description": "Maintains conversation summaries for context",
            "namespaces": ["travel/user/{actorId}/summary/{sessionId}"]
        }
    }
]

print("📋 Memory Strategies Defined:")
for strategy in strategies:
    strategy_type = list(strategy.keys())[0]
    strategy_info = strategy[strategy_type]
    print(f"  • {strategy_info['name']}: {strategy_info['description']}")

#-------------------------------------------
# Create memory resource
#-------------------------------------------
try:
    print("🚀 Creating memory resource...")
    memory = client.create_memory_and_wait(
        name=MEMORY_NAME,
        strategies=strategies,
        description="Memory for AI Travel Companion agent",
        event_expiry_days=365,  # Keep travel memories for 1 year
    )
    memory_id = memory['id']
    print(f"✅ Created memory: {memory_id}")

# If memory exist, get memory info    
except ClientError as e:
    if e.response['Error']['Code'] == 'ValidationException' and "already exists" in str(e):
        # If memory already exists, retrieve its ID
        memories = client.list_memories()
        memory_id = next((m['id'] for m in memories if m['id'].startswith(MEMORY_NAME)), None)
        print(f"Memory already exists. Using existing memory ID: {memory_id}")
    else:
        raise e

#-------------------------------------------
# Verify memory strategies are configured
# correctly
#-------------------------------------------
strategies_info = client.get_memory_strategies(memory_id)

print("🔍 Memory Strategies Verification:")
print("=" * 50)
for strategy in strategies_info:
    print(f"\n📌 {strategy['name']}")
    print(f"   Type: {strategy['type']}")
    print(f"   Description: {strategy['description']}")
    print(f"   Namespaces: {strategy['namespaces']}")

print(f"\n✅ {len(strategies_info)} strategies configured successfully")




#-------------------------------------------
# Seed initial travel preferences for
# demonstration
#-------------------------------------------
travel_interactions = [
    ("I prefer mid-range hotels, nothing too fancy but clean and comfortable.", "USER"),
    ("Noted! I'll focus on 3-4 star hotels with good reviews for cleanliness and comfort.", "ASSISTANT"),
    ("I'm vegetarian, so I need restaurants with good vegetarian options.", "USER"),
    ("Perfect! I'll make sure to recommend destinations and restaurants known for excellent vegetarian cuisine.", "ASSISTANT"),
    ("My budget is usually around $3000-5000 for a 10-day international trip.", "USER"),
    ("That's a great budget range! I can help you plan amazing trips within $3000-5000 for 10 days.", "ASSISTANT"),
    ("I love historical sites and museums, not so much into nightlife or beaches.", "USER"),
    ("Excellent! I'll focus on destinations rich in history and culture with world-class museums.", "ASSISTANT")
]

print("🌱 Seeding travel preferences...")
try:
    client.create_event(
        memory_id=memory_id,
        actor_id=USER_ID,
        session_id="preference_setup",
        messages=travel_interactions
    )
    print(f"✅ Seeded travel preferences for user: {USER_ID}")
    
except Exception as e:
    print(f"⚠️ Error seeding preferences: {e}")



#-------------------------------------------
# Test memory retrieval
#-------------------------------------------
print("🧪 Testing Memory Retrieval")
print("=" * 50)


# Try to retrieve memories
try:
    memories = client.retrieve_memories(
        memory_id=memory_id,
        namespace=f"travel/user/{USER_ID}/preferences",
        query="vegetarian food preferences",
        top_k=3
    )
    
    print(f"\n📚 Retrieved {len(memories)} memories:")
    for i, memory in enumerate(memories, 1):
        if isinstance(memory, dict):
            content = memory.get('content', {})
            if isinstance(content, dict):
                text = content.get('text', '')[:100] + "..."
                print(f"  {i}. {text}")
                
except Exception as e:
    print(f"⚠️ Memory retrieval test: {e}")
    print("This is normal - memories may take time to process")


#-------------------------------------------
# Save memory information for use in
# troubleshooting or state
#-------------------------------------------
memory_info = {
    "memory_id": memory_id,
    "memory_name": MEMORY_NAME,
    "region": REGION,
    "user_id": USER_ID,
    "session_id": SESSION_ID
}

# Save to file
with open(memory_state_file, 'w') as f:
    json.dump(memory_info, f, indent=2)

print("💾 Memory information saved to environments/memory_info.json")
print("\n📋 Memory Summary:")
print(f"  Memory ID: {memory_info['memory_id']}")
print(f"  User ID: {memory_info['user_id']}")
print(f"  Region: {memory_info['region']}")