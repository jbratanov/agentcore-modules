#
#
# AWS Dependencies:
#   Agentcore Gateway setup
#   Agentcore Memory setup
#   Cognito User pool setup
#
#   
# Setup and Resource Discovery
# Retrieve existing Agentcore Gateway information from AWS
# Retrieve existing Agentcore Memory from AWS
# Retrieve existing cognito info used by Agentcore gateway
# Ensure OAuth Configuration
# Test Gateway Connectivity
# Test Oauth Token
# Test MCP endpoints work through Gateway for all targets configured
#---------------------------------------------------
# Test integration with use cases for:
#   - Gateway connectivity
#   - mcp access
#   - oauth configs
#   - secrets manager 
#   - Flight API
#   - Weather API
#   - ExchangeRate API
#---------------------------------------------------


#-------------------------------------------
# imports
#-------------------------------------------

import json
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
#from cognito_config import setup_cognito_oauth
import boto3
import requests
from bedrock_agentcore.memory import MemoryClient
import re

#-------------------------------------------
# Assign Global Vars
#-------------------------------------------
REGION = 'us-east-1'
OPENAPI_SPECS_DIR='./openapi_specs/'
MEMORY_NAME = "TravelMateMemory"
GATEWAY_NAME = "TravelMateGateway"


print("Resource Discovery:")
print("===================")
#-------------------------------------------
# Get existing gateway information
#-------------------------------------------

def get_gateway_info(
        gateway_name: str,
        region: str = REGION) -> dict:
    client = GatewayClient(region_name=region)
    gateways = client.client.list_gateways()['items']
    gateway_info = next((g for g in gateways if g['name'] == GATEWAY_NAME), None)
    if gateway_info:
        gateway_info = client.client.get_gateway(gatewayIdentifier=gateway_info['gatewayId'])
        print(f"Gateway: {gateway_info['gatewayId']}")
    else:
        raise Exception(f"Gateway {GATEWAY_NAME} not found")

    return(gateway_info)



#-------------------------------------------
# Get existing Memory information
#-------------------------------------------
def get_memory_info(
        memory_name: str,
        region: str = REGION) -> dict:
    memclient = MemoryClient(region_name=region)
    memories = memclient.list_memories()
    memory_id = next((m['id'] for m in memories if m['id'].startswith(MEMORY_NAME)), None)
    if memory_id != None:
        print(f"Memory: Memory exists. Using existing memory ID: {memory_id}")
    else:
        raise Exception(f"Memory {MEMORY_NAME} not found")        

    return(memories)

#memory = get_memory_info(MEMORY_NAME, REGION)


#-------------------------------------------
# Get existing Cognito information
#-------------------------------------------

def get_cognito_info_from_gateway(
    gateway_name: str,
    region: str = REGION,
) -> dict:
    """
    Retrieve Cognito OAuth configuration for an existing AgentCore Gateway.

    Queries the AgentCore Gateway by name to obtain its JWT authorizer config,
    then resolves the associated Cognito User Pool, app client, and token
    endpoint details from those identifiers.

    Args:
        gateway_name: The name of the AgentCore Gateway (e.g. "TravelMateGateway").
        region:       AWS region where the gateway and Cognito pool live.

    Returns:
        A dict matching the cognito_config.json schema:
        {
            "gateway_name": str,
            "authorizer_config": { "customJWTAuthorizer": { ... } },
            "client_info": {
                "client_id":      str,
                "client_secret":  str,
                "user_pool_id":   str,
                "token_endpoint": str,
                "scope":          str,
                "domain_prefix":  str,
            }
        }

    Raises:
        ValueError: If the gateway or a matching authorizer/client cannot be found.
        botocore.exceptions.ClientError: On AWS API failures.
    """
    
    bedrock_client = boto3.client("bedrock-agentcore-control", region_name=region)
    cognito_client = boto3.client("cognito-idp", region_name=region)

    # ------------------------------------------------------------------ #
    # 1. Find the gateway by name (paginate in case there are many)        #
    # ------------------------------------------------------------------ #
    gateway_id = None
    paginator_kwargs: dict = {}

    while True:
        response = bedrock_client.list_gateways(**paginator_kwargs)
        for gw in response.get("items", []):
            if gw.get("name") == gateway_name:
                gateway_id = gw["gatewayId"]
                break
        if gateway_id:
            break
        next_token = response.get("nextToken")
        if not next_token:
            break
        paginator_kwargs = {"nextToken": next_token}

    if not gateway_id:
        raise ValueError(f"Gateway '{gateway_name}' not found in region {region}.")

    # ------------------------------------------------------------------ #
    # 2. Fetch full gateway details                                        #
    #    Note: get_gateway uses 'gatewayIdentifier', not 'gatewayId'      #
    # ------------------------------------------------------------------ #
    gw_detail = bedrock_client.get_gateway(gatewayIdentifier=gateway_id)

    # Key is 'authorizerConfiguration' (not 'authorizerConfig')
    raw_auth = gw_detail.get("authorizerConfiguration", {})
    jwt_auth = raw_auth.get("customJWTAuthorizer", {})
    if not jwt_auth:
        raise ValueError(
            f"Gateway '{gateway_name}' has no customJWTAuthorizer configured. "
            f"authorizerType is: {gw_detail.get('authorizerType')}"
        )

    discovery_url: str = jwt_auth["discoveryUrl"]
    allowed_clients: list[str] = jwt_auth.get("allowedClients", [])
    client_id: str = allowed_clients[0] if allowed_clients else ""

    authorizer_config = {"customJWTAuthorizer": jwt_auth}

    # ------------------------------------------------------------------ #
    # 3. Derive the User Pool ID from the OIDC discovery URL               #
    #    Pattern: .../us-east-1_PoolId/.well-known/openid-configuration    #
    # ------------------------------------------------------------------ #
    match = re.search(
        r"cognito-idp\.[^/]+\.amazonaws\.com/([^/]+)/\.well-known",
        discovery_url,
    )
    if not match:
        raise ValueError(
            f"Could not extract User Pool ID from discovery URL: {discovery_url}"
        )
    user_pool_id: str = match.group(1)

    # ------------------------------------------------------------------ #
    # 4. Fetch app client details (secret + OAuth scopes)                  #
    # ------------------------------------------------------------------ #
    client_detail = cognito_client.describe_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=client_id,
    )["UserPoolClient"]

    client_secret: str = client_detail.get("ClientSecret", "")

    # Pick the first allowed OAuth scope; fall back to a sensible default.
    oauth_scopes: list[str] = client_detail.get("AllowedOAuthScopes", [])
    scope: str = oauth_scopes[0] if oauth_scopes else f"{gateway_name}/invoke"

    # ------------------------------------------------------------------ #
    # 5. Fetch the Cognito domain to build the token endpoint              #
    # ------------------------------------------------------------------ #
    pool_detail = cognito_client.describe_user_pool(UserPoolId=user_pool_id)
    domain_prefix: str = pool_detail["UserPool"].get("Domain", "")

    region_part = user_pool_id.split("_")[0]  # e.g. "us-east-1"
    token_endpoint = (
        f"https://{domain_prefix}.auth.{region_part}.amazoncognito.com/oauth2/token"
    )

    # ------------------------------------------------------------------ #
    # 6. Assemble and return                                               #
    # ------------------------------------------------------------------ #
    return {
        "gateway_name": gateway_name,
        "authorizer_config": authorizer_config,
        "client_info": {
            "client_id": client_id,
            "client_secret": client_secret,
            "user_pool_id": user_pool_id,
            "token_endpoint": token_endpoint,
            "scope": scope,
            "domain_prefix": domain_prefix,
        },
    }

    

#-------------------------------------------
# Ensure OAuth Configuration
#-------------------------------------------    
def ensure_oauth_flows(client_info, region=REGION):
    """Ensure Cognito client has client_credentials OAuth flow enabled"""
    cognito_client = boto3.client('cognito-idp', region_name=region)
    
    try:
        # Get current configuration
        response = cognito_client.describe_user_pool_client(
            UserPoolId=client_info['user_pool_id'],
            ClientId=client_info['client_id']
        )
        
        current_flows = response['UserPoolClient'].get('AllowedOAuthFlows', [])
        flows_enabled = response['UserPoolClient'].get('AllowedOAuthFlowsUserPoolClient', False)
        
        print(f"Current OAuth Flows: {current_flows}")
        print(f"OAuth Flows Enabled: {flows_enabled}")
        
        # Check if client_credentials is configured
        if 'client_credentials' not in current_flows or not flows_enabled:
            print("\n🔧 Fixing OAuth configuration...")
            
            cognito_client.update_user_pool_client(
                UserPoolId=client_info['user_pool_id'],
                ClientId=client_info['client_id'],
                AllowedOAuthFlows=['client_credentials'],
                AllowedOAuthScopes=[client_info['scope']],
                AllowedOAuthFlowsUserPoolClient=True
            )
            print("OAuth client_credentials flow enabled")
        else:
            print("OAuth already properly configured")
            
    except Exception as e:
        print(f"Error checking/updating OAuth config: {e}")
        raise

# Apply the fix
#print("Verifying OAuth Configuration...")
#print("=" * 60)
#ensure_oauth_flows(cognito_info['client_info'])



#-------------------------------------------
# Test Gateway Connectivity
#-------------------------------------------

def get_exchangerate_api_key(
        region: str = REGION):
    """Find and retrieve the ExchangeRate API key credential provider"""

    # Initialize the bedrock-agentcore-control client
    agentcore_client = boto3.client('bedrock-agentcore-control', region_name=REGION)
    secrets_client = boto3.client('secretsmanager', region_name=REGION)

    
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
        print("\nExchangeRate API Key: {api_key}")
        
        return api_key
        
    except Exception as e:
        print(f"Error retrieving API key: {e}")
        return None

#-------------------------------------------
# Test Oauth Token
#-------------------------------------------    
  
def test_oauth_token(cognito_info):
    """Test OAuth token retrieval from Cognito"""
    print("Testing OAuth Token Retrieval...")
    print("-" * 60)
    
    # Construct token endpoint from gateway info
    # Format: https://{domain}.auth.{region}.amazoncognito.com/oauth2/token
    token_endpoint = cognito_info['client_info']['token_endpoint']
    
    print(f"Token Endpoint: {token_endpoint}")
    print(f"Client ID: {cognito_info['client_info']['client_id']}")
    print(f"Scope: {cognito_info['client_info']['scope']}")
    
    try:
        response = requests.post(
            token_endpoint,
            data={
                "grant_type": "client_credentials",
                "client_id": cognito_info['client_info']['client_id'],
                "client_secret": cognito_info['client_info']['client_secret'],
                "scope": cognito_info['client_info']['scope']
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            print("Token retrieved successfully!")
            print(f"Token Type: {token_data.get('token_type')}")
            print(f"Expires In: {token_data.get('expires_in')} seconds")
            print(f"Access Token (first 20 chars): {token_data.get('access_token', '')[:20]}...")
            return token_data.get('access_token')
        else:
            print("Token retrieval failed!")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error: Token Response: {str(e)}")
        return None

def test_mcp_endpoint(gateway_info, access_token):
    """Test MCP endpoint connectivity"""
    print("\nTesting MCP Endpoint Connectivity...")
    print("-" * 60)

    mcp_endpoint = gateway_info['gatewayUrl']
    print(f"MCP Endpoint: {mcp_endpoint}")
    
    if not access_token:
        print("No access token available. Skipping MCP test.")
        return False
    
    try:
        # Test with tools/list method
        response = requests.post(
            mcp_endpoint,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "jsonrpc": "2.0",
                "id": "test-list-tools",
                "method": "tools/list",
                "params": {}
            }
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ MCP endpoint is accessible!")
            
            if 'result' in result and 'tools' in result['result']:
                tools = result['result']['tools']
                print(f"\n📋 Available Tools ({len(tools)}):")
                for tool in tools:
                    print(f"  • {tool.get('name', 'Unknown')}")
                return True
            else:
                print(f"Response: {json.dumps(result, indent=2)}")
                return True
        else:
            print("MCP endpoint test failed!")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_gateway_tool_call(gateway_info, access_token, tool_name, arguments):
    """Test a specific gateway tool call"""
    print(f"\nTesting Tool: {tool_name}")
    print("-" * 60)
    
    if not access_token:
        print("No access token available. Skipping tool test.")
        return None
    
    mcp_endpoint = gateway_info['gatewayUrl']
    
    try:
        response = requests.post(
            mcp_endpoint,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={
                "jsonrpc": "2.0",
                "id": f"test-{tool_name}",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
        )
        
        print(f"Arguments: {json.dumps(arguments, indent=2)}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("Tool call successful!")
            print("\nResult:")
            print(json.dumps(result, indent=2))
            return result
        else:
            print("Tool call failed!")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return None



def run_integration_test(gateway_info, cognito_info):
#---------------------------------------------------
# Test integration with use cases for:
#   - Gateway connectivity
#   - mcp access
#   - oauth configs
#   - secrets manager 
#   - Flight API
#   - Weather API
#   - ExchangeRate API
#---------------------------------------------------
    # Run all gateway tests
    print("GATEWAY CONNECTIVITY TESTS")
    #print(gateway_info)
    print("=" * 60)
    print(f"Gateway ID: {gateway_info['gatewayId']}")
    print()
    
    # Test 1: OAuth Token
    
    access_token = test_oauth_token(cognito_info)
    
    # Test 2: MCP Endpoint
    if access_token:
        mcp_success = test_mcp_endpoint(gateway_info, access_token)
        
        # Test 3: Sample Tool Calls
        if mcp_success:
            print("\n" + "=" * 60)
            print("Testing Sample Tool Calls")
            print("=" * 60)
            
            # Test flight search
            test_gateway_tool_call(
                gateway_info,
                access_token,
                "FlightSearch___getFlights",
                {
                    "dep_iata": "NYC",
                    "arr_iata": "LAX",
                }
            )
            
            # Test weather
            test_gateway_tool_call(
                gateway_info,
                access_token,
                "WeatherSearch___getCurrentWeather",
                {
                    "q": "Rome,IT",
                    "units": "metric"
                }
            )
            
            # Test currency conversion
            exchange_rate_apikey = json.loads(get_exchangerate_api_key(REGION))["api_key_value"]
            test_gateway_tool_call(
                gateway_info,
                access_token,
                "ExchangeRate___convertCurrency",
                {
                    #"amount": 100,
                    "api_key": exchange_rate_apikey,
                    "from_currency": "USD",
                    "to_currency": "EUR"
                }
    
    )
    
    print("\n" + "=" * 60)
    print("Gateway connectivity tests completed!")
    print("=" * 60)



#-------------------------------------------
# Main
#-------------------------------------------

def main():
    gateway_info = get_gateway_info(GATEWAY_NAME, REGION)
    get_memory_info(MEMORY_NAME, REGION)
    cognito_info = get_cognito_info_from_gateway(GATEWAY_NAME, region=REGION)
    if cognito_info:
        print(f"Cognito: Cognito client found {cognito_info['client_info']['client_id']}")
    print("Verifying OAuth Configuration...")
    print("=" * 60)
    ensure_oauth_flows(cognito_info['client_info'])
    run_integration_test(gateway_info, cognito_info)
if __name__ == "__main__":
    main()





  
    
    