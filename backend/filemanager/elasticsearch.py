from elasticsearch_dsl import connections
from django.conf import settings
import os

def configure_elasticsearch():
    """Configure Elasticsearch connection"""
    host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
    port = os.getenv('ELASTICSEARCH_PORT', '9200')
    connections.create_connection(
        alias='default',
        hosts=[f'{host}:{port}'],
        timeout=20
    ) 