from .url_loader import URLLayerLoader
import requests
from typing import Dict, Any


class ArcGISLoader(URLLayerLoader):
    """
    Loader for ArcGIS REST API layers.
    """
    
    def load(self) -> Dict[str, Any]:
        """
        Load layer from ArcGIS REST API.
        
        Returns:
            Dict containing layer metadata and features
        """
        try:
            # Fetch layer metadata
            metadata_url = f"{self.url}?f=json"
            response = requests.get(metadata_url, timeout=30)
            response.raise_for_status()
            
            metadata = response.json()
            
            # TODO: Implement feature fetching
            # This is a basic implementation that can be extended
            return {
                'metadata': metadata,
                'features': [],
                'type': 'arcgis'
            }
        except requests.RequestException as e:
            raise Exception(f"Error loading ArcGIS layer: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")
