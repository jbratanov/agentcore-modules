#-------------------------------------------
# Verify environment setup
#-------------------------------------------
import json
import os
#from cognito_config import setup_cognito_oauth
import boto3
import requests
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
#-------------------------------------------
# Assign Global Vars
#-------------------------------------------
# Set these in your environment before running:
#   export CLIENT_ID="your-client-id"
#   export CLIENT_SECRET="your-client-secret"
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
TOKEN_URL = "https://agentcore-ebfb2a42.auth.us-east-1.amazoncognito.com/oauth2/token"
REGION = 'us-east-1'
OPENAPI_SPECS_DIR='./openapi_specs/'
GATEWAY_NAME = "TravelMateGateway"
GATEWAY_MCP_URL="https://travelmategateway-pty1mg4ase.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
weather_target_name="WeatherSearch"
currency_target_name="ExchangeRate"
aviationstack_target_name="FlightSearch"
#-------------------------------------------
# Test Gateway Tools
#-------------------------------------------
client = GatewayClient(region_name=REGION)
print("🧪 Testing Gateway Tools")
print("=" * 40)

# Get access token for testing
access_token = client.get_access_token_for_cognito({
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "TravelMateGateway/invoke",
    "token_endpoint": TOKEN_URL
})

print(f"✅ Access token obtained: {access_token[:20]}...")




#-------------------------------------------
# Test gateway tool function
#-------------------------------------------
def test_gateway_tool(tool_name, arguments):

    print("tool_name= ", tool_name)
    print("arguments= ", arguments)
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(GATEWAY_MCP_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            print(f"✅ {tool_name} - Success")
            result = response.json()
            print(f"   Response: {str(result)[:200]}...")
            return result
        else:
            print(f"❌ {tool_name} - Failed ({response.status_code})")
            print(f"   Error: {response.text[:200]}...")
            return None
    except Exception as e:
        print(f"❌ {tool_name} - Exception: {str(e)}")
        return None




#-------------------------------------------
# Test weather for Rome
#-------------------------------------------
print("\n🌤️ Testing Weather API:")
weather_result = test_gateway_tool(f"{weather_target_name}___getCurrentWeather", {
    "q": "Rome,IT",
    "units": "metric"
})


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
        print("🔍 Searching for ExchangeRate API key provider...")
        response = agentcore_client.list_api_key_credential_providers(maxResults=100)
        
        providers = response.get('credentialProviders', [])
        exchangerate_provider = None
        
        # Find the provider that starts with "ExchangeRate-ApiKey"
        for provider in providers:
            if provider['name'].startswith('ExchangeRate-ApiKey'):
                exchangerate_provider = provider
                break
        
        if not exchangerate_provider:
            print("❌ ExchangeRate API key provider not found")
            return None
        
        provider_name = exchangerate_provider['name']
        print(f"✅ Found provider: {provider_name}")
        
        # Step 2: Get the credential provider details
        provider_response = agentcore_client.get_api_key_credential_provider(name=provider_name)
        
        print(f"   ARN: {provider_response['credentialProviderArn']}")
        
        # Step 3: Extract the secret ARN
        secret_arn = provider_response['apiKeySecretArn']['secretArn']
        print(f"   Secret ARN: {secret_arn}")
        
        # Step 4: Retrieve the actual API key from Secrets Manager
        print("\n🔐 Retrieving API key from Secrets Manager...")
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
        
        print("✅ Successfully retrieved API key")
        print(f"\n🎉 ExchangeRate API Key: {api_key}")
        
        return api_key
        
    except Exception as e:
        print(f"❌ Error retrieving API key: {e}")
        return None

exchange_rate_apikey = json.loads(get_exchangerate_api_key())["api_key_value"]



#-------------------------------------------
# Test currency conversion
#-------------------------------------------
print("\n💱 Testing Currency API:")
currency_result = test_gateway_tool(f"{currency_target_name}___convertCurrency", {
    "api_key": exchange_rate_apikey,
    "from_currency": "USD",
    "to_currency": "EUR"
})



#-------------------------------------------
# Test flight search (may have limited
# results with free tier)
#-------------------------------------------
print("\n✈️ Testing Flight API:")
flight_result = test_gateway_tool(f"{aviationstack_target_name}___getFlights", {
    "dep_iata": "JFK",
    "arr_iata": "FCO",
    "limit": 5
})
