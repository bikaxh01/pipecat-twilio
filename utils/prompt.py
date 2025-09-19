import functools
from datetime import datetime
from loguru import logger


async def create_dynamic_prompt(
    customer_name: str = "there", multimodel: bool = True
) -> str:
    """Create a dynamic prompt with the customer's name"""
    from model.model import organization

    try:
        # Use find_many() and await it to get the actual results
        prompts = await organization.find_many().to_list()

        if not prompts:
            # Fallback prompt if no prompts exist in database
            fallback_prompt = f"Hello {customer_name}! I'm Ananya from Toothsi. How can I help you today?"
            logger.warning("No prompts found in database, using fallback")
            return fallback_prompt

        prompt = ""
        if multimodel:
            prompt = prompts[0].prompt
        else:
            prompt = prompts[1].prompt
        logger.info(f"Using prompt from database for customer: {customer_name}")

        # Replace the {name} placeholder in the base prompt
        dynamic_prompt = prompt.replace("{name}", customer_name)
        return dynamic_prompt

    except Exception as e:
        logger.error(f"Error fetching prompt from database: {e}")
        # Fallback prompt if database operation fails
        fallback_prompt = (
            f"Hello {customer_name}! I'm Ananya from Toothsi. How can I help you today?"
        )
        return fallback_prompt


async def get_raw_prompt(multimodel: bool = True) -> str:
    """Get the raw prompt from database"""
    from model.model import organization

    try:
        # Use find_many() and await it to get the actual results
        prompts = await organization.find_many().to_list()

        if not prompts:
            logger.warning("No prompts found in database")
            return ""
        prompt = ""
        if multimodel:
            prompt = prompts[0].prompt
        else:
            prompt = prompts[1].prompt

        return prompt

    except Exception as e:
        logger.error(f"Error fetching prompt from database: {e}")
        return ""


async def save_raw_prompt(new_prompt: str, multimodel: bool = True) -> bool:
    """Save a new raw prompt to the database"""
    from model.model import organization

    try:
        # Get existing prompts
        prompts = await organization.find_many().to_list()

        if prompts:
            # Update existing prompt
            existing_prompt = prompts[0] if multimodel else prompts[1]
            existing_prompt.prompt = new_prompt
            existing_prompt.updated_at = datetime.utcnow()
            await existing_prompt.save()
            logger.info("Updated existing prompt in database")

        return True

    except Exception as e:
        logger.error(f"Error saving prompt to database: {e}")
        return False
