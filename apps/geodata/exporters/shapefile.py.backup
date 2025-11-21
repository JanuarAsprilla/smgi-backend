"""
Shapefile exporter usando pyshp.
"""
import os
import shutil
import tempfile
import zipfile
import shapefile
from datetime import datetime
from typing import Optional
from django.contrib.gis.geos import GEOSGeometry
import logging

logger = logging.getLogger(__name__)


class ShapefileExporter:
    """Exporta datos geoespaciales a formato Shapefile."""
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or tempfile.mkdtemp()
        os.makedirs(self.output_dir, exist_ok=True)
    
    def export_layer(self, layer, filename: Optional[str] = None) -> str:
        """Exporta una capa a Shapefile."""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{layer.name.replace(' ', '_')}_{timestamp}"
        
        logger.info(f"Exportando layer {layer.name} a shapefile")
        
        features = layer.features.filter(is_active=True)
        
        if not features.exists():
            raise ValueError(f"No hay features activos en la capa {layer.name}")
        
        temp_dir = tempfile.mkdtemp()
        shp_path = os.path.join(temp_dir, filename)
        
        try:
            w = shapefile.Writer(shp_path)
            
            first_feature = features.first()
            if not first_feature or not first_feature.geometry:
                raise ValueError("No hay geometrías válidas")
            
            geom = GEOSGeometry(first_feature.geometry.json)
            geom_type = geom.geom_type.upper()
            
            if geom_type == 'POINT':
                w.shapeType = shapefile.POINT
            elif geom_type == 'LINESTRING':
                w.shapeType = shapefile.POLYLINE
            elif geom_type in ['POLYGON', 'MULTIPOLYGON']:
                w.shapeType = shapefile.POLYGON
            else:
                w.shapeType = shapefile.POINT
            
            if first_feature.properties:
                for key, value in first_feature.properties.items():
                    if isinstance(value, int):
                        w.field(key[:10], 'N', size=19)
                    elif isinstance(value, float):
                        w.field(key[:10], 'F', size=19, decimal=8)
                    else:
                        w.field(key[:10], 'C', size=254)
            
            w.field('feature_id', 'C', size=254)
            
            for feature in features:
                if not feature.geometry:
                    continue
                
                geom = GEOSGeometry(feature.geometry.json)
                
                if geom.geom_type == 'Point':
                    w.point(geom.x, geom.y)
                elif geom.geom_type == 'LineString':
                    coords = list(geom.coords)
                    w.line([coords])
                elif geom.geom_type == 'Polygon':
                    exterior = list(geom[0].coords)
                    w.poly([exterior])
                elif geom.geom_type == 'MultiPolygon':
                    if len(geom) > 0:
                        exterior = list(geom[0][0].coords)
                        w.poly([exterior])
                
                record_values = []
                if first_feature.properties:
                    for key in first_feature.properties.keys():
                        value = feature.properties.get(key, '') if feature.properties else ''
                        record_values.append(value)
                
                record_values.append(feature.feature_id or '')
                w.record(*record_values)
            
            w.close()
            
            prj_path = f"{shp_path}.prj"
            with open(prj_path, 'w') as prj:
                if layer.srid == 4326:
                    prj.write('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]')
                else:
                    prj.write(f'PROJCS["Unknown",GEOGCS["GCS_Unknown",DATUM["D_Unknown",SPHEROID["Unknown",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]]')
            
            cpg_path = f"{shp_path}.cpg"
            with open(cpg_path, 'w') as cpg:
                cpg.write('UTF-8')
            
            zip_path = os.path.join(self.output_dir, f"{filename}.zip")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
                    file_path = f"{shp_path}{ext}"
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
                
                self._add_metadata_file(zipf, layer, filename)
            
            logger.info(f"Shapefile exportado: {zip_path}")
            return zip_path
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def export_features(self, features, filename: str, crs: str = "EPSG:4326") -> str:
        """Exporta features a Shapefile."""
        logger.info(f"Exportando {features.count()} features")
        
        if not features.exists():
            raise ValueError("No hay features")
        
        temp_dir = tempfile.mkdtemp()
        shp_path = os.path.join(temp_dir, filename)
        
        try:
            w = shapefile.Writer(shp_path)
            w.shapeType = shapefile.POINT
            
            w.field('feature_id', 'C', size=254)
            w.field('layer_id', 'N', size=19)
            
            first_feature = features.first()
            if first_feature and first_feature.properties:
                for key in list(first_feature.properties.keys())[:20]:
                    w.field(key[:10], 'C', size=254)
            
            for feature in features:
                if not feature.geometry:
                    continue
                
                geom = GEOSGeometry(feature.geometry.json)
                
                if geom.geom_type == 'Point':
                    w.point(geom.x, geom.y)
                elif geom.geom_type == 'LineString':
                    coords = list(geom.coords)
                    w.line([coords])
                elif geom.geom_type == 'Polygon':
                    exterior = list(geom[0].coords)
                    w.poly([exterior])
                
                record_values = [feature.feature_id or '', feature.layer_id or 0]
                
                if first_feature and first_feature.properties:
                    for key in list(first_feature.properties.keys())[:20]:
                        value = feature.properties.get(key, '') if feature.properties else ''
                        record_values.append(str(value)[:254])
                
                w.record(*record_values)
            
            w.close()
            
            with open(f"{shp_path}.prj", 'w') as prj:
                prj.write('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]')
            
            with open(f"{shp_path}.cpg", 'w') as cpg:
                cpg.write('UTF-8')
            
            zip_path = os.path.join(self.output_dir, f"{filename}.zip")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
                    file_path = f"{shp_path}{ext}"
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
            
            logger.info(f"Features exportados: {zip_path}")
            return zip_path
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def export_dataset(self, dataset, filename: Optional[str] = None) -> str:
        """Exporta dataset completo."""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{dataset.name.replace(' ', '_')}_{timestamp}"
        
        logger.info(f"Exportando dataset {dataset.name}")
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            exported_files = []
            
            for layer in dataset.layers.filter(is_active=True):
                layer_filename = f"{filename}_{layer.name.replace(' ', '_')}"
                layer_zip = self.export_layer(layer, layer_filename)
                
                with zipfile.ZipFile(layer_zip, 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                exported_files.append(layer.name)
            
            final_zip = os.path.join(self.output_dir, f"{filename}_complete.zip")
            
            with zipfile.ZipFile(final_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
                
                readme = self._generate_dataset_readme(dataset, exported_files)
                zipf.writestr('README.txt', readme)
            
            logger.info(f"Dataset exportado: {final_zip}")
            return final_zip
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _add_metadata_file(self, zipf, layer, filename):
        metadata = f"""Shapefile Metadata
===================

Layer: {layer.name}
Description: {layer.description or 'N/A'}
Type: {layer.get_layer_type_display()}
Geometry: {layer.get_geometry_type_display() if layer.geometry_type else 'N/A'}
SRID: {layer.srid}
Created: {layer.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Data Source: {layer.data_source.name if layer.data_source else 'N/A'}
Total Features: {layer.features.filter(is_active=True).count()}

Generated by: SMGI
"""
        zipf.writestr(f"{filename}_metadata.txt", metadata)
    
    def _generate_dataset_readme(self, dataset, layers):
        readme = f"""Dataset Export
==============

Dataset: {dataset.name}
Description: {dataset.description or 'N/A'}
Created: {dataset.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Layers:
"""
        for layer_name in layers:
            readme += f"- {layer_name}\n"
        
        readme += "\nGenerated by: SMGI\n"
        return readme
    
    def cleanup(self):
        if self.output_dir and os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir, ignore_errors=True)
