import os
import tempfile
import zipfile
from pathlib import Path
from django.http import FileResponse, HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import geopandas as gpd
from osgeo import ogr, osr.

+

class LayerViewSet(viewsets.ModelViewSet):
    # ... código existente ...
    
    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """
        Exportar capa en diferentes formatos
        Formatos soportados: geojson, shapefile, kml, gpkg
        """
        layer = self.get_object()
        export_format = request.query_params.get('format', 'geojson').lower()
        
        try:
            # Obtener features como GeoDataFrame
            features = layer.features.all()
            
            if not features.exists():
                return Response(
                    {'error': 'La capa no tiene features para exportar'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Convertir a GeoDataFrame
            gdf = self._layer_to_geodataframe(layer, features)
            
            if export_format == 'geojson':
                return self._export_geojson(layer, gdf)
            elif export_format == 'shapefile':
                return self._export_shapefile_complete(layer, gdf)
            elif export_format == 'kml':
                return self._export_kml(layer, gdf)
            elif export_format == 'gpkg':
                return self._export_geopackage(layer, gdf)
            else:
                return Response(
                    {'error': f'Formato no soportado: {export_format}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _layer_to_geodataframe(self, layer, features):
        """Convertir features a GeoDataFrame"""
        from shapely import wkt
        import pandas as pd
        
        data = []
        for feature in features:
            geom = wkt.loads(feature.geom.wkt)
            properties = feature.properties or {}
            properties['geometry'] = geom
            data.append(properties)
        
        gdf = gpd.GeoDataFrame(data, crs=f'EPSG:{layer.srid}')
        return gdf
    
    def _export_geojson(self, layer, gdf):
        """Exportar a GeoJSON"""
        geojson = gdf.to_json()
        
        response = HttpResponse(geojson, content_type='application/geo+json')
        response['Content-Disposition'] = f'attachment; filename="{layer.name}.geojson"'
        return response
    
    def _export_shapefile_complete(self, layer, gdf):
        """
        Exportar Shapefile COMPLETO con todos los archivos necesarios
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / layer.name
            shp_path = str(base_path) + '.shp'
            
            # 1. Escribir Shapefile base (.shp, .shx, .dbf)
            gdf.to_file(shp_path, driver='ESRI Shapefile', encoding='utf-8')
            
            # 2. Crear archivo .prj (Sistema de coordenadas)
            self._create_prj_file(str(base_path) + '.prj', layer.srid)
            
            # 3. Crear archivo .cpg (Codificación)
            self._create_cpg_file(str(base_path) + '.cpg')
            
            # 4. Crear índice espacial (.sbn, .sbx) si hay muchos features
            if gdf.shape[0] > 100:
                self._create_spatial_index(shp_path)
            
            # 5. Crear metadata XML (.shp.xml)
            self._create_shapefile_metadata(
                str(base_path) + '.shp.xml',
                layer,
                gdf
            )
            
            # 6. Comprimir todo en ZIP
            zip_path = Path(tmpdir) / f'{layer.name}.zip'
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Agregar todos los archivos generados
                for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.sbn', '.sbx', '.shp.xml']:
                    file_path = str(base_path) + ext
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
            
            # 7. Retornar ZIP
            response = FileResponse(
                open(zip_path, 'rb'),
                content_type='application/zip'
            )
            response['Content-Disposition'] = f'attachment; filename="{layer.name}_shapefile.zip"'
            return response
    
    def _create_prj_file(self, prj_path, srid):
        """Crear archivo .prj con la proyección"""
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(srid)
        
        with open(prj_path, 'w') as f:
            f.write(srs.ExportToWkt())
    
    def _create_cpg_file(self, cpg_path):
        """Crear archivo .cpg con codificación UTF-8"""
        with open(cpg_path, 'w') as f:
            f.write('UTF-8')
    
    def _create_spatial_index(self, shp_path):
        """Crear índice espacial (.sbn, .sbx) usando OGR"""
        try:
            driver = ogr.GetDriverByName('ESRI Shapefile')
            dataSource = driver.Open(shp_path, 1)  # 1 = write mode
            
            if dataSource:
                layer = dataSource.GetLayer()
                # Crear índice espacial
                dataSource.ExecuteSQL(f'CREATE SPATIAL INDEX ON {layer.GetName()}')
                dataSource = None  # Cerrar
        except Exception as e:
            # Si falla, no es crítico
            pass
    
    def _create_shapefile_metadata(self, xml_path, layer, gdf):
        """Crear metadata ISO 19139 en XML"""
        from datetime import datetime
        
        xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<metadata xml:lang="es">
  <idinfo>
    <citation>
      <citeinfo>
        <origin>SMGI System</origin>
        <pubdate>{datetime.now().strftime("%Y%m%d")}</pubdate>
        <title>{layer.name}</title>
      </citeinfo>
    </citation>
    <descript>
      <abstract>{layer.description or "Sin descripción"}</abstract>
      <purpose>Datos geoespaciales exportados desde SMGI</purpose>
    </descript>
    <spdom>
      <bounding>
        <westbc>{gdf.total_bounds[0]}</westbc>
        <eastbc>{gdf.total_bounds[2]}</eastbc>
        <northbc>{gdf.total_bounds[3]}</northbc>
        <southbc>{gdf.total_bounds[1]}</southbc>
      </bounding>
    </spdom>
  </idinfo>
  <dataqual>
    <lineage>
      <procstep>
        <procdesc>Exportado desde SMGI el {datetime.now().isoformat()}</procdesc>
      </procstep>
    </lineage>
  </dataqual>
  <spdoinfo>
    <direct>Vector</direct>
    <ptvctinf>
      <sdtsterm>
        <sdtstype>{layer.geometry_type}</sdtstype>
        <ptvctcnt>{gdf.shape[0]}</ptvctcnt>
      </sdtsterm>
    </ptvctinf>
  </spdoinfo>
  <spref>
    <horizsys>
      <planar>
        <planci>
          <coordrep>
            <absres>0.000001</absres>
            <ordres>0.000001</ordres>
          </coordrep>
        </planci>
      </planar>
      <geodetic>
        <horizdn>WGS84</horizdn>
        <ellips>WGS84</ellips>
      </geodetic>
    </horizsys>
  </spref>
  <eainfo>
    <detailed>
      <enttyp>
        <enttypl>{layer.name}</enttypl>
        <enttypd>{layer.description or "Sin descripción"}</enttypd>
      </enttyp>
      {''.join([f'''
      <attr>
        <attrlabl>{col}</attrlabl>
        <attrdef>{gdf[col].dtype}</attrdef>
      </attr>''' for col in gdf.columns if col != 'geometry'])}
    </detailed>
  </eainfo>
  <distinfo>
    <distrib>
      <cntinfo>
        <cntorgp>
          <cntorg>SMGI System</cntorg>
        </cntorgp>
      </cntinfo>
    </distrib>
    <stdorder>
      <digform>
        <digtinfo>
          <formname>Shapefile</formname>
        </digtinfo>
      </digform>
    </stdorder>
  </distinfo>
  <metainfo>
    <metd>{datetime.now().strftime("%Y%m%d")}</metd>
    <metc>
      <cntinfo>
        <cntorgp>
          <cntorg>SMGI System</cntorg>
        </cntorgp>
      </cntinfo>
    </metc>
    <metstdn>FGDC Content Standards for Digital Geospatial Metadata</metstdn>
    <metstdv>FGDC-STD-001-1998</metstdv>
  </metainfo>
</metadata>'''
        
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
    
    def _export_kml(self, layer, gdf):
        """Exportar a KML"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kml', delete=False) as tmp:
            gdf.to_file(tmp.name, driver='KML')
            tmp.flush()
            
            response = FileResponse(
                open(tmp.name, 'rb'),
                content_type='application/vnd.google-earth.kml+xml'
            )
            response['Content-Disposition'] = f'attachment; filename="{layer.name}.kml"'
            return response
    
    def _export_geopackage(self, layer, gdf):
        """Exportar a GeoPackage"""
        with tempfile.NamedTemporaryFile(suffix='.gpkg', delete=False) as tmp:
            gdf.to_file(tmp.name, layer=layer.name, driver='GPKG')
            
            response = FileResponse(
                open(tmp.name, 'rb'),
                content_type='application/geopackage+sqlite3'
            )
            response['Content-Disposition'] = f'attachment; filename="{layer.name}.gpkg"'
            return response
