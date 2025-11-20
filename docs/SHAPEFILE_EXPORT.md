# Exportación de Shapefiles

## Descripción

El sistema ahora soporta exportación de datos geoespaciales a formatos estándar:
- **Shapefile** (.zip con .shp, .shx, .dbf, .prj, .cpg)
- **GeoJSON** (.geojson)

## API Endpoints

### 1. Exportar Capa

**POST** `/api/v1/geodata/layers/{id}/export/`
```json
{
  "format": "shapefile",
  "filename": "mi_capa_personalizada",
  "crs": "EPSG:4326"
}
```

Opciones de `format`:
- `shapefile`: Solo Shapefile
- `geojson`: Solo GeoJSON
- `both`: Ambos formatos

**Respuesta:**
```json
{
  "success": true,
  "message": "Exportación completada exitosamente",
  "files": [
    {
      "format": "shapefile",
      "filename": "mi_capa_20251111_123456.zip",
      "size": 15234,
      "download_url": "http://localhost:8000/api/v1/geodata/download/mi_capa_20251111_123456.zip"
    }
  ]
}
```

### 2. Descarga Directa

**GET** `/api/v1/geodata/layers/{id}/download/shapefile/`
**GET** `/api/v1/geodata/layers/{id}/download/geojson/`

Descarga directa del archivo generado.

### 3. Exportar Dataset (múltiples capas)

**POST** `/api/v1/geodata/datasets/{id}/export/`

Exporta todas las capas de un dataset en un solo ZIP.

## Uso con cURL
```bash
# 1. Login
TOKEN=$(curl -X POST http://localhost:8000/api/v1/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq -r '.access')

# 2. Exportar capa
curl -X POST http://localhost:8000/api/v1/geodata/layers/1/export/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"format": "shapefile", "filename": "mi_exportacion"}'

# 3. Descarga directa
curl -X GET http://localhost:8000/api/v1/geodata/layers/1/download/shapefile/ \
  -H "Authorization: Bearer $TOKEN" \
  -o mi_capa.zip
```

## Uso Programático
```python
from apps.geodata.exporters import ShapefileExporter, GeoJSONExporter
from apps.geodata.models import Layer

# Obtener capa
layer = Layer.objects.get(id=1)

# Exportar a Shapefile
exporter = ShapefileExporter(output_dir='data/exports/shapefiles')
shp_path = exporter.export_layer(layer, filename='mi_capa')

# Exportar a GeoJSON
geojson_exporter = GeoJSONExporter(output_dir='data/exports/geojson')
geojson_path = geojson_exporter.export_layer(layer, filename='mi_capa')
```

## Archivos Generados

### Shapefile (.zip contiene):
- `*.shp`: Geometrías
- `*.shx`: Índice espacial
- `*.dbf`: Atributos
- `*.prj`: Sistema de coordenadas
- `*.cpg`: Codificación de caracteres
- `*_metadata.txt`: Metadata adicional

### GeoJSON:
- Formato estándar GeoJSON
- Incluye metadata en el objeto
- Compatible con todos los sistemas GIS

## Integración en el Cloud

Los archivos exportados se pueden subir automáticamente a:
- AWS S3
- Google Cloud Storage
- Azure Blob Storage

Ver documentación de integración cloud para detalles.
