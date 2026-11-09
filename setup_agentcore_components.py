#-------------------------------------------
# imports
#-------------------------------------------
import os
import json
from dotenv import load_dotenv
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
#from cognito_config import setup_cognito_oauth
import boto3
import requests

#-------------------------------------------
# Configuration from environment variables
#-------------------------------------------

REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID = os.environ.get("MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")

# Gateway configuration from environment
GATEWAY_ID = os.environ.get("GATEWAY_ID")
GATEWAY_MCP_ENDPOINT = os.environ.get("GATEWAY_MCP_ENDPOINT")
GATEWAY_TOKEN_ENDPOINT = os.environ.get("GATEWAY_TOKEN_ENDPOINT")
GATEWAY_OAUTH_CLIENT_ID = os.environ.get("GATEWAY_OAUTH_CLIENT_ID")
GATEWAY_OAUTH_CLIENT_SECRET = os.environ.get("GATEWAY_OAUTH_CLIENT_SECRET")
GATEWAY_OAUTH_SCOPE = os.environ.get("GATEWAY_OAUTH_SCOPE")

# Memory configuration from environment
MEMORY_ID = os.environ.get("MEMORY_ID")
MEMORY_USER_ID = os.environ.get("MEMORY_USER_ID", "default-user")
MEMORY_SESSION_ID = os.environ.get("MEMORY_SESSION_ID", "default-session")

#-------------------------------------------
# Assign Global Vars
#-------------------------------------------
OPENAPI_SPECS_DIR='./openapi_specs/'
GATEWAY_NAME = "TravelMateGateway"
MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
COMPONENT_CONFIG_FILE="./travelprogram_config.json"

#-------------------------------------------
# External API keys
#-------------------------------------------
api_keys = {
    "AVIATIONSTACK_API_KEY": os.getenv("AVIATIONSTACK_API_KEY"),
    "OPENWEATHERMAP_API_KEY": os.getenv("OPENWEATHERMAP_API_KEY"),
    "EXCHANGERATE_API_KEY": os.getenv("EXCHANGERATE_API_KEY")
}


#-------------------------------------------
# Load environment variables
#------------------------------------------
env = load_dotenv()

#-------------------------------------------
# Validate all required external API keys
#-------------------------------------------

print("API Key Validation:")
for key_name, key_value in api_keys.items():
    if key_value:
        print(f"{key_name}: {'*' * 8}{key_value[-4:]}")
    else:
        print(f"{key_name}: Not configured")

missing_keys = [k for k, v in api_keys.items() if not v]
if missing_keys:
    print(f"\nMissing API keys: {', '.join(missing_keys)}")
    print("Please configure these before proceeding.")
    raise ValueError("Missing required API keys")
else:
    print("\nAll API keys configured!")
    

#-------------------------------------------
# Review OpenAPI Specifications
#------------------------------------------

# Load and display OpenAPI specifications
def load_openapi_spec(filename):
    """Load OpenAPI specification from file"""
    with open(f"{OPENAPI_SPECS_DIR}{filename}", "r") as f:
        return json.load(f)

# Load all specifications
specs = {
    "Aviationstack (Flights)": load_openapi_spec("aviationstack.json"),
    "OpenWeatherMap (Weather)": load_openapi_spec("openweathermap.json"),
    "ExchangeRate-API (Currency)": load_openapi_spec("exchangerate.json")
}

print("OpenAPI Specifications Overview:")
print("=" * 50)

for api_name, spec in specs.items():
    print(f"\n{api_name}")
    print(f"   Base URL: {spec['servers'][0]['url']}")
    print("   Operations:")
    
    for path, methods in spec['paths'].items():
        for method, details in methods.items():
            if 'operationId' in details:
                print(f"     - {details['operationId']}: {details['summary']}")

#-------------------------------------------
# Create Agentcore Gateway
#------------------------------------------

# Initialize Gateway client

print(f"Creating AgentCore Gateway: {GATEWAY_NAME}")
print(f"Region: {REGION}")

client = GatewayClient(region_name=REGION)
print("Gateway client initialized")


#-------------------------------------------
# Set up OAuth with Cognito
#-------------------------------------------

# Set up Cognito OAuth
print("Setting up OAuth with Cognito...")
cognito_result = client.create_oauth_authorizer_with_cognito(GATEWAY_NAME)


print("OAuth configuration complete")
print(f"Client ID: {cognito_result['client_info']['client_id']}")
print(f"Scope: {cognito_result['client_info']['scope']}")


#-------------------------------------------
# Fix OAuth configuration for Cognito client
#-------------------------------------------
def activate_oauth(client_info):

    cognito_client = boto3.client('cognito-idp', region_name=REGION)
    
    try:
        cognito_client.update_user_pool_client(
            UserPoolId=client_info['user_pool_id'],
            ClientId=client_info['client_id'],
            AllowedOAuthFlows=['client_credentials'],
            AllowedOAuthScopes=[client_info['scope']],
            AllowedOAuthFlowsUserPoolClient=True
        )
        print("Fixed Cognito OAuth configuration")
    except Exception as e:
        print(f"Failed to fix OAuth config: {e}")
        raise

activate_oauth(cognito_result['client_info'])


#-------------------------------------------
# Create or get existing Gateway
#-------------------------------------------

print(f"Creating Gateway: {GATEWAY_NAME}...")

try:
    gateway = client.create_mcp_gateway(
        name=GATEWAY_NAME,
        role_arn=None,  # Auto-create
        authorizer_config=cognito_result['authorizer_config'],
        enable_semantic_search=True
    )
    print("Gateway created successfully!")
except:
    print(f"Gateway {GATEWAY_NAME} already exists, retrieving...")
    # Get existing gateway
    gateways = client.client.list_gateways()['items']
    gateway = next((g for g in gateways if g['name'] == GATEWAY_NAME), None)
    if gateway:
        gateway = client.client.get_gateway(gatewayIdentifier=gateway['gatewayId'])
        print("Retrieved existing gateway")
    else:
        raise Exception(f"Gateway {GATEWAY_NAME} not found")

print(f"MCP Endpoint: {gateway['gatewayUrl']}")
print(f"Gateway ID: {gateway['gatewayId']}")


#-------------------------------------------
# Add API Targets to Gateway
#-------------------------------------------

#
# Add Aviationstack target (Flight search)
#
print("✈️ Adding Aviationstack (Flight Search)...")

aviationstack_spec = specs["Aviationstack (Flights)"]
aviationstack_target = client.create_mcp_gateway_target(
    gateway=gateway,
    name="FlightSearch", 
    target_type="openApiSchema",
    target_payload={
        "inlinePayload": json.dumps(aviationstack_spec)
    },
    credentials={
        "api_key": api_keys["AVIATIONSTACK_API_KEY"],
        "credential_location": "QUERY_PARAMETER",
        "credential_parameter_name": "access_key"
    }
)

aviationstack_target_name = aviationstack_target['name']
print("Aviationstack target added")
print(f"   Available tool: {aviationstack_target_name}___getFlights")

#
# Add OpenWeatherMap target (Weather)
#
print("Adding OpenWeatherMap (Weather)...")

weather_spec = specs["OpenWeatherMap (Weather)"]
weather_target = client.create_mcp_gateway_target(
    gateway=gateway,
    name="WeatherSearch",
    target_type="openApiSchema",
    target_payload={
        "inlinePayload": json.dumps(weather_spec)
    },
    credentials={
        "api_key": api_keys["OPENWEATHERMAP_API_KEY"],
        "credential_location": "QUERY_PARAMETER",
        "credential_parameter_name": "appid"
    }
)

weather_target_name = weather_target['name']
print("OpenWeatherMap target added")
print(f"   Available tools: {weather_target_name}___getCurrentWeather, {weather_target_name}___getWeatherForecast")


#
# Add ExchangeRate-API target (Currency)
#
print("Adding ExchangeRate-API (Currency)...")

currency_spec = specs["ExchangeRate-API (Currency)"]
currency_target = client.create_mcp_gateway_target(
    gateway=gateway,
    name="ExchangeRate",
    target_type="openApiSchema",
    target_payload={
        "inlinePayload": json.dumps(currency_spec)
    },
    credentials={
        "api_key": api_keys["EXCHANGERATE_API_KEY"],
        "credential_location": "QUERY_PARAMETER",
        "credential_parameter_name": "api_key"
    }
)

currency_target_name = currency_target['name']
print("ExchangeRate-API target added")
print(f"   Available tools: {currency_target_name}___getExchangeRates, {currency_target_name}___convertCurrency")


#-------------------------------------------
# Test Gateway Tools
#-------------------------------------------

##-------------------------------------------
# Test weather API
##-------------------------------------------

print("Testing Gateway Tools")
print("=" * 40)

# Get access token for testing
access_token = client.get_access_token_for_cognito({
    "client_id": cognito_result['client_info']['client_id'],
    "client_secret": cognito_result['client_info']['client_secret'],
    "scope": cognito_result['client_info']['scope'],
    "token_endpoint": cognito_result['client_info']['token_endpoint']
})

print(f"Access token obtained: {access_token[:20]}...")

# Test gateway tool function

def test_gateway_tool(tool_name, arguments):
    """Test a gateway tool via MCP"""
    try:
        response = requests.post(
            f"{gateway['gatewayUrl']}/mcp",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
        )
        
        if response.status_code == 200:
            print(f"{tool_name} - Success")
            result = response.json()
            print(f"   Response: {str(result)[:200]}...")
            return result
        else:
            print(f"{tool_name} - Failed ({response.status_code})")
            print(f"   Error: {response.text[:200]}...")
            return None
    except Exception as e:
        print(f"{tool_name} - Exception: {str(e)}")
        return None


#-------------------------------------------
# Get and test Exchange Rate API
#-------------------------------------------

# Initialize the bedrock-agentcore-control client
agentcore_client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')
secrets_client = boto3.client('secretsmanager', region_name='us-east-1')

def get_exchangerate_api_key():
    """Find and retrieve the ExchangeRate API key credential provider"""
    try:
        # Step 1: List all providers to find the ExchangeRate one
        print("Searching for ExchangeRate API key provider...")
        response = agentcore_client.list_api_key_credential_providers(maxResults=100)
        
        providers = response.get('credentialProviders', [])
        exchangerate_provider = None
        
        # Find the provider that starts with "ExchangeRate-ApiKey"
        for provider in providers:
            if provider['name'].startswith('ExchangeRate-ApiKey'):
                exchangerate_provider = provider
                break
        
        if not exchangerate_provider:
            print("ExchangeRate API key provider not found")
            return None
        
        provider_name = exchangerate_provider['name']
        print(f"Found provider: {provider_name}")
        
        # Step 2: Get the credential provider details
        provider_response = agentcore_client.get_api_key_credential_provider(name=provider_name)
        
        print(f"   ARN: {provider_response['credentialProviderArn']}")
        
        # Step 3: Extract the secret ARN
        secret_arn = provider_response['apiKeySecretArn']['secretArn']
        print(f"   Secret ARN: {secret_arn}")
        
        # Step 4: Retrieve the actual API key from Secrets Manager
        print("\nRetrieving API key from Secrets Manager...")
        secret_response = secrets_client.get_secret_value(SecretId=secret_arn)
        
        # The secret value could be a string or JSON
        if 'SecretString' in secret_response:
            secret_value = secret_response['SecretString']
            
            # Try to parse as JSON first
            try:
                secret_json = json.loads(secret_value)
                # If it's JSON, look for common API key field names
                api_key = secret_json.get('api_key') or secret_json.get('apiKey') or secret_json.get('key')
                if not api_key:
                    # If no standard field, return the whole JSON
                    api_key = secret_value
            except json.JSONDecodeError:
                # If not JSON, it's likely just the raw API key string
                api_key = secret_value
        else:
            # Binary secret
            api_key = secret_response['SecretBinary']
        
        print("Successfully retrieved API key")
        print(f"\nExchangeRate API Key: {api_key}")
        
        return api_key
        
    except Exception as e:
        print(f"Error retrieving API key: {e}")
        return None

exchange_rate_apikey = json.loads(get_exchangerate_api_key())["api_key_value"]


#---------------------------------
# Save gateway information for
# config file
#---------------------------------
gateway_info = {
    "gateway_name": GATEWAY_NAME,
    "gateway_id": gateway['gatewayId'],
    "mcp_endpoint": gateway['gatewayUrl'],
    "region": REGION,
    "oauth_client_id": cognito_result['client_info']['client_id'],
    "oauth_client_secret": cognito_result['client_info']['client_secret'],
    "oauth_scope": cognito_result['client_info']['scope'],
    "available_tools": [
        f"{aviationstack_target_name}___getFlights",
        f"{weather_target_name}___getCurrentWeather",
        f"{weather_target_name}___getWeatherForecast",
        f"{currency_target_name}___getExchangeRates",
        f"{currency_target_name}___convertCurrency"
    ]
}

# Save gateway config to config file
with open(COMPONENT_CONFIG_FILE, 'w') as f:
    json.dump(gateway_info, f, indent=2)


print("\nGateway Summary:")
print(f"  Gateway ID: {gateway_info['gateway_id']}")
print(f"  MCP Endpoint: {gateway_info['mcp_endpoint']}")
print(f"  Available Tools: {len(gateway_info['available_tools'])}")
for tool in gateway_info['available_tools']:
    print(f"    - {tool}")


