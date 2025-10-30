# apps/common/pagination.py
"""
SMGI Backend - Common Pagination
Sistema de Monitoreo Geoespacial Inteligente
Clases de paginación personalizadas reutilizables para el backend
"""
from rest_framework import pagination
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param, remove_query_param
from django.utils.translation import gettext_lazy as _
from rest_framework_gis.pagination import GeoJsonPagination


class CustomPageNumberPagination(pagination.PageNumberPagination):
    """
    Paginación personalizada basada en números de página.
    """
    # Tamaño de página por defecto
    page_size = 20
    
    # Parámetro para permitir que el cliente cambie el tamaño de página
    page_size_query_param = 'page_size'
    
    # Tamaño máximo de página permitido
    max_page_size = 1000
    
    # Parámetro para el número de página
    page_query_param = 'page'
    
    # Cadenas para identificar la última página
    last_page_strings = ('last',)
    
    def get_paginated_response(self, data):
        """
        Devuelve una respuesta paginada con metadatos personalizados.
        
        Args:
            data (List[Dict[str, Any]]): Lista de datos paginados.
            
        Returns:
            Response: Respuesta paginada con metadatos.
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'page_size': self.get_page_size(self.request),
            'current_page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'results': data
        })
    
    def get_next_link(self):
        """
        Obtiene el enlace a la siguiente página.
        
        Returns:
            Optional[str]: Enlace a la siguiente página o None.
        """
        if not self.page.has_next():
            return None
        url = self.request.build_absolute_uri()
        page_number = self.page.next_page_number()
        return replace_query_param(url, self.page_query_param, page_number)
    
    def get_previous_link(self):
        """
        Obtiene el enlace a la página anterior.
        
        Returns:
            Optional[str]: Enlace a la página anterior o None.
        """
        if not self.page.has_previous():
            return None
        url = self.request.build_absolute_uri()
        page_number = self.page.previous_page_number()
        if page_number == 1:
            return remove_query_param(url, self.page_query_param)
        return replace_query_param(url, self.page_query_param, page_number)
    
    def get_page_size(self, request):
        """
        Obtiene el tamaño de página desde la solicitud.
        
        Args:
            request (Request): Solicitud HTTP.
            
        Returns:
            int: Tamaño de página.
        """
        page_size = request.query_params.get(self.page_size_query_param)
        if page_size:
            try:
                page_size = int(page_size)
                if page_size > 0 and page_size <= self.max_page_size:
                    return page_size
            except ValueError:
                pass
        return self.page_size


class CustomLimitOffsetPagination(pagination.LimitOffsetPagination):
    """
    Paginación personalizada basada en límite y offset.
    """
    # Límite por defecto
    default_limit = 20
    
    # Parámetro para el límite
    limit_query_param = 'limit'
    
    # Parámetro para el offset
    offset_query_param = 'offset'
    
    # Límite máximo permitido
    max_limit = 1000
    
    def get_paginated_response(self, data):
        """
        Devuelve una respuesta paginada con metadatos personalizados.
        
        Args:
            data (List[Dict[str, Any]]): Lista de datos paginados.
            
        Returns:
            Response: Respuesta paginada con metadatos.
        """
        return Response({
            'count': self.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'limit': self.get_limit(self.request),
            'offset': self.get_offset(self.request),
            'current_page': (self.get_offset(self.request) // self.get_limit(self.request)) + 1,
            'total_pages': (self.count + self.get_limit(self.request) - 1) // self.get_limit(self.request),
            'results': data
        })
    
    def get_limit(self, request):
        """
        Obtiene el límite desde la solicitud.
        
        Args:
            request (Request): Solicitud HTTP.
            
        Returns:
            int: Límite.
        """
        limit = request.query_params.get(self.limit_query_param)
        if limit:
            try:
                limit = int(limit)
                if limit > 0 and limit <= self.max_limit:
                    return limit
            except ValueError:
                pass
        return self.default_limit
    
    def get_offset(self, request):
        """
        Obtiene el offset desde la solicitud.
        
        Args:
            request (Request): Solicitud HTTP.
            
        Returns:
            int: Offset.
        """
        offset = request.query_params.get(self.offset_query_param)
        if offset:
            try:
                return int(offset)
            except ValueError:
                pass
        return 0


class CustomCursorPagination(pagination.CursorPagination):
    """
    Paginación personalizada basada en cursores.
    """
    # Tamaño de página por defecto
    page_size = 20
    
    # Parámetro para el cursor
    cursor_query_param = 'cursor'
    
    # Campo de ordenamiento por defecto
    ordering = '-created'
    
    # Parámetro para permitir que el cliente cambie el tamaño de página
    page_size_query_param = 'page_size'
    
    # Tamaño máximo de página permitido
    max_page_size = 1000
    
    def get_paginated_response(self, data):
        """
        Devuelve una respuesta paginada con metadatos personalizados.
        
        Args:
            data (List[Dict[str, Any]]): Lista de datos paginados.
            
        Returns:
            Response: Respuesta paginada con metadatos.
        """
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'page_size': self.get_page_size(self.request),
            'current_page': self.cursor.offset // self.get_page_size(self.request) + 1,
            'total_pages': None, # Cursor pagination doesn't know total pages
            'results': data
        })
    
    def get_page_size(self, request):
        """
        Obtiene el tamaño de página desde la solicitud.
        
        Args:
            request (Request): Solicitud HTTP.
            
        Returns:
            int: Tamaño de página.
        """
        page_size = request.query_params.get(self.page_size_query_param)
        if page_size:
            try:
                page_size = int(page_size)
                if page_size > 0 and page_size <= self.max_page_size:
                    return page_size
            except ValueError:
                pass
        return self.page_size


class CustomGeoJSONPagination(GeoJsonPagination):
    """
    Paginación personalizada para respuestas GeoJSON.
    """
    # Tamaño de página por defecto
    page_size = 20
    
    # Parámetro para permitir que el cliente cambie el tamaño de página
    page_size_query_param = 'page_size'
    
    # Tamaño máximo de página permitido
    max_page_size = 1000
    
    def get_paginated_response(self, data):
        """
        Devuelve una respuesta GeoJSON paginada con metadatos personalizados.
        
        Args:
            data (List[Dict[str, Any]]): Lista de datos paginados en formato GeoJSON.
            
        Returns:
            Response: Respuesta GeoJSON paginada con metadatos.
        """
        return Response({
            'type': 'FeatureCollection',
            'features': data,
            'metadata': {
                'count': self.page.paginator.count,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'page_size': self.get_page_size(self.request),
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
            }
        })
    
    def get_page_size(self, request):
        """
        Obtiene el tamaño de página desde la solicitud.
        
        Args:
            request (Request): Solicitud HTTP.
            
        Returns:
            int: Tamaño de página.
        """
        page_size = request.query_params.get(self.page_size_query_param)
        if page_size:
            try:
                page_size = int(page_size)
                if page_size > 0 and page_size <= self.max_page_size:
                    return page_size
            except ValueError:
                pass
        return self.page_size
