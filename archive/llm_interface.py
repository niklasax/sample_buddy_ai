import os
import logging
import json
from typing import Dict, List, Any
from langchain_community.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import numpy as np

def search_samples_with_llm(query: str, samples: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """
    Search for audio samples based on natural language query using LLM.
    
    Args:
        query: Natural language search query
        samples: Dictionary of audio samples with metadata
        
    Returns:
        List of matching sample dictionaries
    """
    logging.info(f"Searching samples with query: {query}")
    
    # Check if API key is available
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logging.warning("OpenAI API key not found. Using fallback search method.")
        return fallback_search(query, samples)
    
    try:
        # Initialize LLM
        llm = OpenAI(temperature=0.1)
        
        # Create a simplified representation of samples for the LLM
        sample_representations = []
        for sample_id, sample in samples.items():
            representation = {
                "id": sample_id,
                "name": sample.get("name", ""),
                "category": sample.get("category", "Unknown"),
                "mood": sample.get("mood", "Unknown")
            }
            
            # Add key features if available
            if "features" in sample:
                features = sample["features"]
                if isinstance(features, dict):
                    representation["spectral_centroid"] = features.get("spectral_centroid", 0)
                    representation["energy"] = features.get("energy", 0)
                    representation["tempo"] = features.get("tempo", 0)
            
            sample_representations.append(representation)
        
        # Create prompt
        prompt_template = """
        You are an expert audio engineer and sample librarian. Your task is to find the most relevant audio samples based on the user's query.
        
        Here's a list of available audio samples with their metadata:
        {samples}
        
        User's query: {query}
        
        Return a JSON array containing the IDs of the most relevant samples for this query. For example:
        ["sample_id_1", "sample_id_2", "sample_id_3"]
        
        Don't explain your reasoning, just return a valid JSON array of sample IDs.
        """
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["samples", "query"],
        )
        
        # Create chain
        chain = LLMChain(llm=llm, prompt=prompt)
        
        # Run chain
        result = chain.run({
            "samples": json.dumps(sample_representations[:20], indent=2),  # Limit to 20 samples to avoid token limits
            "query": query
        })
        
        # Parse results
        try:
            result = result.strip()
            # Handle if result starts or ends with ```json and ```
            if result.startswith("```json"):
                result = result.replace("```json", "", 1).strip()
            if result.endswith("```"):
                result = result[:-3].strip()
            
            sample_ids = json.loads(result)
            
            # Ensure it's a list
            if not isinstance(sample_ids, list):
                raise ValueError("Result is not a list")
            
            # Get full sample data for returned IDs
            matching_samples = []
            for sample_id in sample_ids:
                if sample_id in samples:
                    sample_data = samples[sample_id].copy()
                    matching_samples.append(sample_data)
            
            return matching_samples
        
        except Exception as e:
            logging.error(f"Error parsing LLM result: {str(e)}")
            logging.error(f"Raw result: {result}")
            return fallback_search(query, samples)
    
    except Exception as e:
        logging.error(f"Error using LLM for search: {str(e)}")
        return fallback_search(query, samples)

def fallback_search(query: str, samples: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """
    Fallback keyword-based search when LLM is unavailable.
    
    Args:
        query: Search query
        samples: Dictionary of audio samples
        
    Returns:
        List of matching sample dictionaries
    """
    query_terms = query.lower().split()
    matches = []
    
    for sample_id, sample in samples.items():
        score = 0
        
        # Check name
        name = sample.get("name", "").lower()
        for term in query_terms:
            if term in name:
                score += 3
        
        # Check category
        category = sample.get("category", "").lower()
        for term in query_terms:
            if term in category:
                score += 2
        
        # Check mood
        mood = sample.get("mood", "").lower()
        for term in query_terms:
            if term in mood:
                score += 2
        
        if score > 0:
            match = sample.copy()
            match["search_score"] = score
            matches.append(match)
    
    # Sort by score
    matches.sort(key=lambda x: x.get("search_score", 0), reverse=True)
    
    # Remove scores from results
    for match in matches:
        if "search_score" in match:
            del match["search_score"]
    
    return matches[:10]  # Return top 10 matches
