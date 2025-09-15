from typing import Optional, List
from loguru import logger
from model.model import PincodeData


async def get_near_by_clinic_data(pincode: Optional[str] = None, city: Optional[str] = None) -> str:
    """
    Get nearby clinic data based on city and/or pincode
    
    Args:
        pincode: Optional pincode to search for
        city: Optional city name to search for
        
    Returns:
        String containing clinic information
    """
    try:
        from difflib import get_close_matches
        
        logger.info(f"🏥 Getting nearby clinic data for pincode: {pincode}, city: {city}")
        
        # If both pincode and city are provided, search for exact match
        if pincode and city:
            # First, try exact city match
            query_filter = {"pincode": pincode, "city": city}
            exact_results = await PincodeData.find(query_filter).to_list()
            
            if exact_results:
                logger.info(f"✅ Found exact match for pincode {pincode} and city {city}")
                return _format_clinic_results(exact_results, f"Exact match for pincode {pincode} in {city}")
            
            # If no exact match, try fuzzy search for city name
            logger.info(f"🔍 No exact city match found, trying fuzzy search for city: {city}")
            
            # Get all unique cities from database for fuzzy matching
            all_cities = await PincodeData.distinct("city")
            logger.info(f"📋 Available cities in database: {all_cities[:10]}...")  # Log first 10 cities
            
            # Find closest city match using fuzzy search
            city_matches = get_close_matches(
                city.title(),  # Convert to title case for matching
                [c.title() for c in all_cities if c],  # Convert all cities to title case
                n=3,  # Get top 3 matches
                cutoff=0.6  # Minimum similarity threshold
            )
            
            if city_matches:
                best_match = city_matches[0]
                logger.info(f"🎯 Best fuzzy match for '{city}': '{best_match}'")
                
                # Search with the best matching city
                fuzzy_query_filter = {"pincode": pincode, "city": best_match}
                fuzzy_results = await PincodeData.find(fuzzy_query_filter).to_list()
                
                if fuzzy_results:
                    return _format_clinic_results(fuzzy_results, f"Found match for pincode {pincode} in {best_match} (fuzzy match for '{city}')")
            
            # If still no match, return nearby clinics from the same pincode
            logger.info(f"🔍 No city match found, searching for any clinics in pincode {pincode}")
            pincode_only_results = await PincodeData.find({"pincode": pincode}).limit(5).to_list()
            
            if pincode_only_results:
                return _format_clinic_results(pincode_only_results, f"Found clinics in pincode {pincode} (city '{city}' not found)")
            
            return f"No clinics found for pincode {pincode} and city '{city}'. Please verify the pincode and city name."
        
        # If only city is provided, get 5 clinics from that city
        elif city and not pincode:
            # Try exact city match first
            exact_results = await PincodeData.find({"city": city}).limit(5).to_list()
            
            if exact_results:
                logger.info(f"✅ Found exact match for city: {city}")
                return _format_clinic_results(exact_results, f"Clinics in {city}")
            
            # Try fuzzy search for city
            logger.info(f"🔍 No exact city match found, trying fuzzy search for city: {city}")
            
            all_cities = await PincodeData.distinct("city")
            city_matches = get_close_matches(
                city.title(),
                [c.title() for c in all_cities if c],
                n=3,
                cutoff=0.6
            )
            
            if city_matches:
                best_match = city_matches[0]
                logger.info(f"🎯 Best fuzzy match for '{city}': '{best_match}'")
                
                fuzzy_results = await PincodeData.find({"city": best_match}).limit(5).to_list()
                
                if fuzzy_results:
                    return _format_clinic_results(fuzzy_results, f"Clinics in {best_match} (fuzzy match for '{city}')")
            
            return f"No clinics found for city '{city}'. Please check the city name spelling."
        
        # If only pincode is provided, get clinics for that pincode
        elif pincode and not city:
            results = await PincodeData.find({"pincode": pincode}).limit(5).to_list()
            
            if results:
                return _format_clinic_results(results, f"Clinics in pincode {pincode}")
            
            return f"No clinics found for pincode {pincode}. Please verify the pincode."
        
        # If neither is provided, return error
        else:
            return "Error: Please provide either city or pincode (or both) to search for nearby clinics."
    
    except Exception as e:
        logger.error(f"❌ Error getting nearby clinic data: {e}")
        return f"Error: Failed to get clinic data - {str(e)}"


def _format_clinic_results(results: List[PincodeData], header: str) -> str:
    """
    Format clinic results into a readable string
    
    Args:
        results: List of PincodeData objects
        header: Header text for the results
        
    Returns:
        Formatted string with clinic information
    """
    if not results:
        return "No clinic data found."
    
    result_text = f"{header}:\n\n"
    
    for i, data in enumerate(results, 1):
        result_text += f"{i}. Pincode: {data.pincode}\n"
        result_text += f"   City: {data.city}\n"
        result_text += f"   Home Scan Available: {data.home_scan}\n"
        
        if data.clinic_1:
            result_text += f"   Clinic 1: {data.clinic_1}\n"
        if data.clinic_2:
            result_text += f"   Clinic 2: {data.clinic_2}\n"
        
        result_text += "\n"
    
    return result_text.strip()
    