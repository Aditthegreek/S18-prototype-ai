# app.py

from flask import Flask, request, jsonify, render_template, make_response # Import make_response
import json
import time

app = Flask(__name__)

# --- HydroponicsAI Class ---
class HydroponicsAI:
    """
    A simulated AI for hydroponics system management, specifically adapted for
    an offshore, floating, two-floor vertical farm prototype with single overall sensors.
    It uses overall sensor data and plant information per floor to assess growth,
    recommend water level adjustments, and generate unified Arduino commands.
    """

    def __init__(self):
        """
        Initializes the AI with predefined thresholds and plant-specific data.
        These parameters are crucial for a prototype and can be refined
        with more data from your specific offshore environment.
        """
        # Define general thresholds for optimal conditions
        self.optimal_humidity_range = (50, 70)  # %
        self.optimal_water_level_range = (70, 90) # % of reservoir capacity

        # Define plant-specific ideal conditions (simplified for demonstration)
        self.plant_profiles = {
            "lettuce": {
                "ideal_humidity": 60,
                "ideal_water_level": 80,
                "growth_rate_factor": 1.0
            },
            "tomato": {
                "ideal_humidity": 65,
                "ideal_water_level": 85,
                "growth_rate_factor": 1.2
            },
            "basil": {
                "ideal_humidity": 55,
                "ideal_water_level": 75,
                "growth_rate_factor": 0.9
            },
        }

    def _get_plant_profile(self, plant_type: str) -> dict:
        """
        Retrieves the profile for a given plant type.
        """
        profile = self.plant_profiles.get(plant_type.lower())
        if not profile:
            print(f"Warning: Plant type '{plant_type}' not found. Using default thresholds.")
            return {
                "ideal_humidity": sum(self.optimal_humidity_range) / 2,
                "ideal_water_level": sum(self.optimal_water_level_range) / 2,
                "growth_rate_factor": 1.0
            }
        return profile

    def assess_overall_farm(self, humidity: float, water_level: float,
                            overall_plant_types: list[str], nutrients_given_ml: float,
                            nutrient_type: str) -> dict:
        """
        Assesses the overall farm conditions based on single set of sensor data
        and all plant types across the farm.

        Args:
            humidity (float): Overall current humidity percentage.
            water_level (float): Overall current water level percentage.
            overall_plant_types (list[str]): List of ALL plant types across all floors.
            nutrients_given_ml (float): Amount of nutrients given in milliliters (ml).
            nutrient_type (str): The type or brand of nutrient used.

        Returns:
            dict: Overall farm assessment, recommendations, and unified Arduino commands.
        """
        feedback = []
        suggestions = []
        arduino_commands = []
        growth_score = 0 # Max score is 2 now (humidity, water level)

        # Calculate average ideal water level for ALL plants across the farm
        if not overall_plant_types:
            feedback.append("No plant types specified for the farm. Using general optimal water level range.")
            avg_ideal_water_level = sum(self.optimal_water_level_range) / 2
        else:
            total_ideal_water_level = 0
            valid_plant_count = 0
            for p_type in overall_plant_types:
                profile = self._get_plant_profile(p_type)
                total_ideal_water_level += profile["ideal_water_level"]
                valid_plant_count += 1
            avg_ideal_water_level = total_ideal_water_level / valid_plant_count if valid_plant_count > 0 else sum(self.optimal_water_level_range) / 2
            feedback.append(f"Calculated average ideal water level for all plants in the farm: {avg_ideal_water_level:.1f}%")

        # --- Humidity Assessment ---
        if self.optimal_humidity_range[0] <= humidity <= self.optimal_humidity_range[1]:
            growth_score += 1
            feedback.append("Overall humidity is within optimal range.")
        elif humidity < self.optimal_humidity_range[0]:
            feedback.append("Overall humidity is too low. Plants might be stressed.")
            suggestions.append("Consider increasing overall humidity (e.g., misting, humidifier).")
        else:
            feedback.append("Overall humidity is too high. Risk of mold/disease, especially offshore.")
            suggestions.append("Ensure adequate overall ventilation/dehumidification.")

        # --- Water Level Assessment & Pump Commands ---
        water_level_buffer = 5 # % buffer for water level adjustments

        if water_level < (avg_ideal_water_level - water_level_buffer):
            feedback.append(f"Overall water level ({water_level:.1f}%) is low, below average ideal ({avg_ideal_water_level:.1f}%). Needs replenishment.")
            suggestions.append(f"Increase overall water level to around {avg_ideal_water_level:.1f}%.")
            arduino_commands.append("PUMP_ON") # Unified command
            water_adjustment_direction = "increase"
        elif water_level > (avg_ideal_water_level + water_level_buffer):
            feedback.append(f"Overall water level ({water_level:.1f}%) is high, above average ideal ({avg_ideal_water_level:.1f}%). Risk of root rot.")
            suggestions.append(f"Decrease overall water level to around {avg_ideal_water_level:.1f}%.")
            arduino_commands.append("VALVE_OPEN_DRAIN") # Unified command
            water_adjustment_direction = "decrease"
        else:
            growth_score += 1
            feedback.append(f"Overall water level ({water_level:.1f}%) is within optimal range for the farm.")
            arduino_commands.append("PUMP_OFF") # Ensure pump is off if level is good
            water_adjustment_direction = "stable"

        # --- Nutrient Assessment (based on ml and type, not PPM) ---
        feedback.append(f"Nutrients provided: {nutrients_given_ml} ml of '{nutrient_type}'.")
        suggestions.append("Always refer to the manufacturer's feeding chart for the specific nutrient type and plant growth stage.")
        suggestions.append("Regularly monitor the Electrical Conductivity (EC) of your nutrient solution to ensure proper concentration, as ml dosage can vary based on concentrate strength.")
        suggestions.append("Regularly check pH of the nutrient solution for optimal nutrient uptake.")


        # --- Overall Growth Status ---
        overall_growth_status = "Good"
        if growth_score == 2: # Max score is 2 now
            overall_growth_status = "Excellent"
        elif growth_score == 1:
            overall_growth_status = "Fair"
        else:
            overall_growth_status = "Poor"
            feedback.append("Multiple overall factors are suboptimal. Farm growth may be significantly impacted.")
            if not suggestions:
                suggestions.append("Review all overall environmental parameters and adjust as needed.")

        return {
            "current_humidity": humidity,
            "current_water_level": water_level,
            "nutrients_given_ml": nutrients_given_ml, # Changed to ml
            "nutrient_type": nutrient_type, # Added nutrient type
            "overall_growth_status": overall_growth_status,
            "feedback": feedback,
            "suggestions": suggestions,
            "water_adjustment_direction": water_adjustment_direction,
            "arduino_commands": arduino_commands
        }

    def assess_floor_plants(self, plant_types: list[str], floor_id: str) -> dict:
        """
        Provides feedback on plant types specific to a floor, without using floor-specific sensors.
        """
        feedback = []
        if not plant_types:
            feedback.append(f"No plants specified for {floor_id}.")
        else:
            feedback.append(f"Plants on {floor_id}: {', '.join(plant_types)}.")
            # You could add more specific feedback here if needed, e.g.,
            # "These plants generally prefer X humidity and Y nutrients."
        return {
            "floor_id": floor_id,
            "plant_types": plant_types,
            "feedback": feedback
        }


# --- Flask App Routes ---
ai_system = HydroponicsAI()

@app.route('/')
def index():
    """
    Serves the main HTML page with strong cache-control headers
    to prevent browser caching during development.
    """
    response = make_response(render_template('index.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/assess', methods=['POST'])
def assess():
    """
    Receives sensor data and plant types from the frontend,
    runs the AI assessment, and returns the results as JSON.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Get sensor data directly from the POST request
        overall_humidity = data.get("overall_humidity")
        overall_water_level = data.get("overall_water_level")
        overall_nutrients_ml = data.get("overall_nutrients_ml") # Changed to ml
        overall_nutrient_type = data.get("overall_nutrient_type") # Added nutrient type
        plant_types_per_floor = data.get("plant_types_per_floor", {})

        # Basic validation for required sensor data
        if any(val is None for val in [overall_humidity, overall_water_level, overall_nutrients_ml, overall_nutrient_type]):
            return jsonify({"error": "Missing sensor data (humidity, water level, nutrients ml, or nutrient type)."}), 400

        # Aggregate all plant types from all floors for overall assessment
        all_plant_types = []
        for floor_id, plants in plant_types_per_floor.items():
            all_plant_types.extend(plants)
        all_plant_types = list(set(all_plant_types)) # Remove duplicates

        # Perform overall farm assessment using the manual input data
        overall_assessment_result = ai_system.assess_overall_farm(
            humidity=overall_humidity,
            water_level=overall_water_level,
            overall_plant_types=all_plant_types,
            nutrients_given_ml=overall_nutrients_ml, # Changed to ml
            nutrient_type=overall_nutrient_type # Added nutrient type
        )

        # Perform per-floor plant type assessment (without sensor data)
        farm_assessment_per_floor = {}
        for floor_id, plants in plant_types_per_floor.items():
            farm_assessment_per_floor[floor_id] = ai_system.assess_floor_plants(plants, floor_id)

        # Prepare combined results
        combined_results = {
            "overall_assessment": overall_assessment_result,
            "farm_assessment_per_floor": farm_assessment_per_floor,
            "overall_arduino_commands": overall_assessment_result["arduino_commands"],
            "overall_suggestions": overall_assessment_result["suggestions"]
        }

        return jsonify(combined_results), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred during assessment: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
