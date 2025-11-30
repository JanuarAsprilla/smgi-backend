"""
Tests for geodata app.
"""
from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon
from .models import DataSource, Layer, Feature, Dataset, SyncLog

User = get_user_model()


class DataSourceModelTest(TestCase):
    """Tests para el modelo DataSource."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
    
    def test_create_data_source(self):
        """Test crear DataSource."""
        ds = DataSource.objects.create(
            name='Test WFS',
            source_type='wfs',
            url='http://example.com/wfs',
            created_by=self.user
        )
        self.assertEqual(ds.name, 'Test WFS')
        self.assertEqual(ds.status, 'pending')
    
    def test_can_sync(self):
        """Test método can_sync."""
        ds = DataSource.objects.create(
            name='Test',
            source_type='wfs',
            url='http://example.com',
            status='active',
            created_by=self.user
        )
        self.assertTrue(ds.can_sync())


class LayerModelTest(TestCase):
    """Tests para el modelo Layer."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
    
    def test_create_layer(self):
        """Test crear Layer."""
        layer = Layer.objects.create(
            name='Test Layer',
            layer_type='vector',
            geometry_type='POINT',
            srid=4326,
            created_by=self.user
        )
        self.assertEqual(layer.name, 'Test Layer')
        self.assertEqual(layer.feature_count, 0)
    
    def test_has_data(self):
        """Test método has_data."""
        layer = Layer.objects.create(
            name='Test',
            geometry_type='POINT',
            created_by=self.user
        )
        self.assertFalse(layer.has_data())


class FeatureModelTest(TestCase):
    """Tests para el modelo Feature."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.layer = Layer.objects.create(
            name='Test Layer',
            geometry_type='POINT',
            srid=4326,
            created_by=self.user
        )
    
    def test_create_feature(self):
        """Test crear Feature con geometría."""
        point = Point(0, 0, srid=4326)
        feature = Feature.objects.create(
            layer=self.layer,
            geometry=point,
            properties={'name': 'Test Point'},
            created_by=self.user
        )
        self.assertIsNotNone(feature.geometry)
        self.assertEqual(feature.properties['name'], 'Test Point')


class LayerAPITest(APITestCase):
    """Tests para el API de Layer."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='analyst'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_list_layers(self):
        """Test listar layers."""
        Layer.objects.create(
            name='Test Layer',
            geometry_type='POINT',
            created_by=self.user
        )
        response = self.client.get('/api/v1/geodata/layers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_layer_unauthorized(self):
        """Test crear layer sin autenticación."""
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/v1/geodata/layers/', {
            'name': 'Test',
            'geometry_type': 'POINT'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
