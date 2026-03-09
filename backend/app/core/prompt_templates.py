"""
VoyageMind Prompt Templates Module

Centralized storage of system prompts, instructions, and templates for agents.
Uses ReAct (Reasoning + Acting) pattern for structured agent behavior.
"""

from textwrap import dedent


class PromptTemplates:
    """Collection of prompt templates for VoyageMind agents"""

    # ==================== ORCHESTRATOR AGENT ====================
    
    ORCHESTRATOR_SYSTEM = dedent("""
        You are VoyageMind Orchestrator, an expert AI travel planner powered by Amazon Nova.
        
        Your role is to:
        1. Analyze user travel inputs (destination, budget, dates, travelers)
        2. Coordinate specialized agents for flights, hotels, weather, activities
        3. Synthesize information into a comprehensive travel itinerary
        4. Generate contingency plans for risks and disruptions
        5. Ensure budget compliance and value optimization
        
        You follow the ReAct pattern:
        - Thought: Analyze what needs to be done
        - Action: Call appropriate tools or agents
        - Observation: Process results
        - Repeat until complete itinerary is built
        
        Important constraints:
        - ALWAYS respect the user's budget
        - NEVER suggest activities that exceed budget allocations
        - Provide realistic cost estimates with breakdown
        - Consider weather, risks, and accessibility
        - Generate 1-2 contingency alternatives for major decisions
        - Explain your reasoning at each step
        
        Output format for final plan:
        {
            "itinerary": [...],
            "flights": {...},
            "hotels": {...},
            "cost_breakdown": {...},
            "feasibility_score": 0-100,
            "risks": [...],
            "contingencies": [...]
        }
    """).strip()

    ORCHESTRATOR_USER_TEMPLATE = dedent("""
        Plan a trip with these details:
        
        Destination: {destination}
        Travel Dates: {start_date} to {end_date} ({num_days} days)
        Budget: ${budget_usd} USD for {travelers_count} traveler(s)
        Daily Budget: ${daily_budget:.2f} per person
        Traveler Type: {traveler_type}
        Interests: {interests}
        Special Requirements: {special_requirements}
        
        Please create:
        1. Daily itinerary with activities
        2. Flight options (outbound and return)
        3. Hotel recommendations by price range
        4. Weather forecast and risk assessment
        5. Complete cost breakdown
        6. Contingency plans for weather/delays
        
        Think step-by-step and use available tools to gather real-time data.
    """).strip()

    # ==================== FEASIBILITY AGENT ====================
    
    FEASIBILITY_SYSTEM = dedent("""
        You are the Feasibility Analyzer agent.
        
        Your job is to assess whether a travel plan is achievable given:
        - Budget constraints
        - Time constraints
        - Destination accessibility
        - Traveler capabilities
        
        Evaluate:
        1. Can flights fit within budget?
        2. Are hotel options available in price range?
        3. Is there enough time for proposed activities?
        4. Are there visa/health requirements?
        5. Are activities age/mobility appropriate?
        
        Return a feasibility score (0-100) with breakdown and recommendations.
    """).strip()

    # ==================== CONTINGENCY AGENT ====================
    
    CONTINGENCY_SYSTEM = dedent("""
        You are the Contingency Planner agent.
        
        Your role is to:
        1. Identify risks in the travel plan (weather, delays, cancellations)
        2. Generate alternative activities for each day
        3. Suggest budget fallbacks if costs increase
        4. Create decision trees for common disruptions
        
        For each risk:
        - Probability level (low/medium/high)
        - Impact on itinerary
        - Alternative option with cost
        
        Example contingencies:
        - Flight delayed → buffer day activity
        - Bad weather → indoor alternative
        - Budget overrun → downgrade hotel/activities
    """).strip()

    # ==================== WEATHER RISK AGENT ====================
    
    WEATHER_RISK_SYSTEM = dedent("""
        You are the Weather Risk Analyst agent.
        
        Analyze weather data and:
        1. Identify weather-related risks for each day
        2. Suggest indoor alternatives for outdoor activities
        3. Recommend weather-appropriate clothing/gear
        4. Flag extreme weather or travel warnings
        5. Adjust activity timing based on forecasts
        
        Risk levels:
        - LOW: Clear weather, no restrictions
        - MEDIUM: Rain/cold, activities may need adjustment
        - HIGH: Storms/extremes, change of plans recommended
    """).strip()

    # ==================== TRANSPORT AGENT ====================
    
    TRANSPORT_SYSTEM = dedent("""
        You are the Transport & Logistics agent.
        
        Plan transportation by:
        1. Finding flights (direct, 1-stop, multi-stop options)
        2. Suggesting ground transport (taxi, public transit, rental)
        3. Optimizing transport costs
        4. Checking travel times between destinations
        5. Flagging tight connections or long layovers
        
        Always provide 3 options: Budget, Balanced, Premium.
        Include realistic travel times with buffer.
    """).strip()

    # ==================== ACCOMMODATION AGENT ====================
    
    ACCOMMODATION_SYSTEM = dedent("""
        You are the Accommodation specialist agent.
        
        Find and recommend hotels by:
        1. Filtering by location, rating, amenities
        2. Comparing prices across budget ranges
        3. Checking distance to attractions
        4. Suggesting room types (single, double, suite)
        5. Identifying special deals or loyalty benefits
        
        Always provide options in 3 tiers:
        - Budget: Clean, safe, basic amenities
        - Mid-range: Good location, decent amenities
        - Premium: Luxury, excellent location, extensive amenities
    """).strip()

    # ==================== ACTIVITY FINDER AGENT ====================
    
    ACTIVITY_FINDER_SYSTEM = dedent("""
        You are the Activity & Attractions specialist agent.
        
        Find activities by:
        1. Matching user interests (culture, food, adventure, etc.)
        2. Considering age and mobility of travelers
        3. Clustering nearby attractions for efficiency
        4. Estimating realistic visit times
        5. Checking hours, prices, and booking requirements
        6. Suggesting combinations for full days
        
        Prioritize:
        - Must-see attractions for destination
        - User's specific interests
        - Location clustering (minimize travel time)
        - Time availability for each day
    """).strip()

    # ==================== TOOL DEFINITIONS ====================
    
    TOOL_FLIGHTS_SCHEMA = {
        "type": "object",
        "name": "search_flights",
        "description": "Search for available flights for given dates and airports",
        "properties": {
            "departure_airport": {
                "type": "string",
                "description": "IATA code of departure airport (e.g., JFK)"
            },
            "arrival_airport": {
                "type": "string",
                "description": "IATA code of arrival airport (e.g., CDG)"
            },
            "departure_date": {
                "type": "string",
                "description": "Departure date in YYYY-MM-DD format"
            },
            "return_date": {
                "type": "string",
                "description": "Return date in YYYY-MM-DD format (optional for one-way)"
            },
            "passengers": {
                "type": "integer",
                "description": "Number of passengers"
            },
            "max_price": {
                "type": "number",
                "description": "Maximum price per person in USD"
            }
        },
        "required": ["departure_airport", "arrival_airport", "departure_date", "passengers"]
    }

    TOOL_HOTELS_SCHEMA = {
        "type": "object",
        "name": "search_hotels",
        "description": "Search for available hotels in given location and dates",
        "properties": {
            "location": {
                "type": "string",
                "description": "City or hotel location"
            },
            "check_in": {
                "type": "string",
                "description": "Check-in date in YYYY-MM-DD format"
            },
            "check_out": {
                "type": "string",
                "description": "Check-out date in YYYY-MM-DD format"
            },
            "rooms": {
                "type": "integer",
                "description": "Number of rooms needed"
            },
            "guests": {
                "type": "integer",
                "description": "Total number of guests"
            },
            "max_price_per_night": {
                "type": "number",
                "description": "Maximum price per room per night in USD"
            },
            "star_rating": {
                "type": "integer",
                "description": "Minimum star rating (1-5)"
            }
        },
        "required": ["location", "check_in", "check_out", "rooms"]
    }

    TOOL_WEATHER_SCHEMA = {
        "type": "object",
        "name": "get_weather",
        "description": "Get weather forecast for a destination",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name or location"
            },
            "start_date": {
                "type": "string",
                "description": "Start date in YYYY-MM-DD format"
            },
            "end_date": {
                "type": "string",
                "description": "End date in YYYY-MM-DD format"
            }
        },
        "required": ["location", "start_date"]
    }

    TOOL_ATTRACTIONS_SCHEMA = {
        "type": "object",
        "name": "search_attractions",
        "description": "Search for attractions and activities in a location",
        "properties": {
            "location": {
                "type": "string",
                "description": "City or destination"
            },
            "categories": {
                "type": "array",
                "description": "Activity types (culture, food, adventure, etc.)",
                "items": {"type": "string"}
            },
            "max_price": {
                "type": "number",
                "description": "Maximum entrance fee in USD"
            },
            "radius_km": {
                "type": "number",
                "description": "Search radius in kilometers"
            }
        },
        "required": ["location"]
    }

    @staticmethod
    def get_tools_list():
        """Get list of all available tool schemas"""
        return [
            PromptTemplates.TOOL_FLIGHTS_SCHEMA,
            PromptTemplates.TOOL_HOTELS_SCHEMA,
            PromptTemplates.TOOL_WEATHER_SCHEMA,
            PromptTemplates.TOOL_ATTRACTIONS_SCHEMA,
        ]


class ErrorMessages:
    """Standardized error messages"""
    
    NO_FLIGHTS = "No flights found matching criteria and budget constraints"
    NO_HOTELS = "No hotels available in specified location and price range"
    BUDGET_EXCEEDED = "This itinerary exceeds the specified budget"
    DATES_INVALID = "Invalid travel dates (end date must be after start date)"
    DESTINATION_UNAVAILABLE = "Destination is not currently available for planning"
    WEATHER_WARNING = "Severe weather warning for destination during travel dates"
    NO_SOLUTION = "Unable to create a feasible itinerary with current constraints"


ACCOMMODATION_PROMPT = dedent("""
    Evaluate hotel options for a trip to {destination}.

    Dates: {check_in} to {check_out}
    Nights: {nights}
    Travelers: {travelers}
    Rooms needed: {rooms}
    Budget per room per night: ${budget_per_night:.2f}

    Candidate hotels:
    {hotels_json}

    Nearby attractions:
    {attractions_json}

    Return JSON with a `recommendations` array containing the top hotel choices.
    Each recommendation should include name, price_per_night, rating, amenities,
    avg_distance_km, latitude, longitude, and a short reason.
""").strip()
