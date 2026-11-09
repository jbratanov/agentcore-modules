# agentcore-modules
## What each file does: 
### setup_agentcore_components.py
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
    - 
- requirement files, example JSON API files for weather, travel and exchange rate sites
- Remove any hardcode values into vars, config files, secrets manager or environment variables
- breakdown modules which maybe redundant across files into packages

