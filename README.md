# agentcore-modules
## What each file does: 
### setup_agentcore_components.py
- You can you this program to setup AWS components required to run Agentcore. There's three example services (flights, weather and exchange rates) to use. You can change what works for you in playing with the code. Once AWS resources are created, you should validate in the AWS console or command line your resources exist. Remember to delete your resources from AWS to make sure you don't get charged for unused resources.

- Configures AWS resources for running agentcore_components_integration.py
  - Configures Agentcore Gateway
    - Setup AVIATIONSTACK_API_KEY for flight info from https://aviationstack.com/
    - Setup OPENWEATHERMAP_API_KEY for weather info from https://openweathermap.org/
    - Setup EXCHANGERATE_API_KEY for exchange rate info from exchangerate-api.com
  - Configures Cognito User Pools for Agentcore Gateway
  - Configure Agentcore Memory Strategies
    - User-preference strategy
    - Semantic strategy
    - Summarization strategy
  - Configure secrets manager for exchange rate API key info
  
### agentcore_component_integration
- The program uses the Agentcore services to validate all integrated AWS services work together, including using external API services through Agentcore Gateway as the MCP service. Whatever services you change setup_agentcore_components.py, will need to be configure in this code as well.

