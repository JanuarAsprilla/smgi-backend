"""
GeoJSON exporter for geodata.
"""
import json
import os
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GeoJSONExporter:
    """Exporta datos geoespaciales a formato GeoJSON."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Inicializa el exportador.
        
        Args:
            output_dir: Directorio de salida
        """
        self.output_dir = output_dir or 'data/exports'
        os.makedirs(self.output_dir, exist_ok=True)
    
    def export_layer(self, layer, filename: Optional[str] = None, 
                    pretty: bool = True) -> str:
        """
        Exporta una capa a GeoJSON.
        
        Args:
            layer: Layer model instance
            filename: Nombre del archivo
            pretty: Formatear JSON con indentación
        
        Returns:
            Ruta al archivo GeoJSON
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{layer.name.replace(' ', '_')}_{timestamp}.geojson"
        
        if not filename.endswith('.geojson'):
            filename += '.geojson'
        
        logger.info(f"Exportando layer {layer.name} a GeoJSON")
        
        # Construir GeoJSON
        features = []
        for feature in layer.features.filter(is_active=True):
            if feature.geometry:
                features.append({
                    'type': 'Feature',
                    'id': str(feature.id),
                    'geometry': json.loads(feature.geometry.json),
                    'properties': {
                        'feature_id': feature.feature_id,
                        **(feature.properties or {})
                    }
                })
        
        geojson = {
            'type': 'FeatureCollection',
            'name': layer.name,
            'crs': {
                'type': 'name',
                'properties': {
                    'name': f'EPSG:{layer.srid}'
                }
            },
            'features': features,
            'metadata': {
                'layer_name': layer.name,
                'description': layer.description,
                'layer_type': layer.layer_type,
                'geometry_type': layer.geometry_type,
                'total_features': len(features),
                'exported_at': datetime.now().isoformat(),
                'source': layer.data_source.name if layer.data_source else None
            }
        }
        
        # Guardar archivo
        output_path = os.path.join(self.output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(geojson, f, indent=2, ensure_ascii=False)
            else:
                json.dump(geojson, f, ensure_ascii=False)
        
        logger.info(f"GeoJSON exportado exitosamente: {output_path}")
        return output_path
    
    def export_features(self, features, filename: str, 
                       layer_name: str = "Features", 
                       pretty: bool = True) -> str:
        """
        Exporta un QuerySet de features a GeoJSON.
        
        Args:
            features: QuerySet de Feature
            filename: Nombre del archivo
            layer_name: Nombre para la colección
            pretty: Formatear JSON
        
        Returns:
            Ruta al archivo GeoJSON
        """
        if not filename.endswith('.geojson'):
            filename += '.geojson'
        
        logger.info(f"Exportando {features.count()} features a GeoJSON")
        
        # Construir GeoJSON
        feature_list = []
        for feature in features:
            if feature.geometry:
                feature_list.append({
                    'type': 'Feature',
                    'id': str(feature.id),
                    'geometry': json.loads(feature.geometry.json),
                    'properties': {
                        'feature_id': feature.feature_id,
                        'layer_id': feature.layer_id,
                        **(feature.properties or {})
                    }
                })
        
        geojson = {
            'type': 'FeatureCollection',
            'name': layer_name,
            'features': feature_list,
            'metadata': {
                'total_features': len(feature_list),
                'exported_at': datetime.now().isoformat()
            }
        }
        
        # Guardar
        output_path = os.path.join(self.output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(geojson, f, indent=2, ensure_ascii=False)
            else:
                json.dump(geojson, f, ensure_ascii=False)
        
        logger.info(f"GeoJSON exportado: {output_path}")
        return output_path
