"""
API Root view.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse


@extend_schema(
    description='API Root - Lista de endpoints disponibles',
    responses={200: OpenApiResponse(description='Lista de endpoints del API')},
    tags=['API Root']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request, format=None):
    """
    API Root - Lista de endpoints disponibles.
    """
    base_url = request.build_absolute_uri('/api/v1/')
    
    return Response({
        'message': 'SMGI - Sistema de Monitoreo Geoespacial Inteligente API v1',
        'version': '1.0.0',
        'documentation': {
            'swagger': request.build_absolute_uri('/api/schema/swagger-ui/'),
            'redoc': request.build_absolute_uri('/api/schema/redoc/'),
        },
        'endpoints': {
            'users': base_url + 'users/',
            'geodata': base_url + 'geodata/',
            'agents': base_url + 'agents/',
            'monitoring': base_url + 'monitoring/',
            'alerts': base_url + 'alerts/',
            'automation': base_url + 'automation/',
            'notifications': base_url + 'notifications/',
        },
        'authentication': {
            'login': base_url + 'users/login/',
            'register': base_url + 'users/register/',
            'token_refresh': base_url + 'users/token/refresh/',
        }
    })
